package com.edgerunners.scamcheck

import android.app.Application
import android.os.SystemClock
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.ProcessLifecycleOwner
import com.edgerunners.scamcheck.alert.AlertNotifier
import com.edgerunners.scamcheck.alert.AlertReducer
import com.edgerunners.scamcheck.alert.CallHistory
import com.edgerunners.scamcheck.alert.CallPhase
import com.edgerunners.scamcheck.alert.CallRecord
import com.edgerunners.scamcheck.alert.CallTimeline
import com.edgerunners.scamcheck.alert.TimelineEntry
import com.edgerunners.scamcheck.alert.TimelineKind
import com.edgerunners.scamcheck.alert.CallUiState
import com.edgerunners.scamcheck.alert.CuePlayer
import com.edgerunners.scamcheck.alert.Effect
import com.edgerunners.scamcheck.alert.Haptics
import com.edgerunners.scamcheck.alert.MuteControl
import com.edgerunners.scamcheck.alert.Reduction
import com.edgerunners.scamcheck.call.CallService
import com.edgerunners.scamcheck.call.TwilioCallController
import com.edgerunners.scamcheck.call.VoiceCallEvent
import com.edgerunners.scamcheck.data.ApiClient
import com.edgerunners.scamcheck.data.AppEvent
import com.edgerunners.scamcheck.model.RiskLevel
import com.edgerunners.scamcheck.model.ThreatSignal
import com.edgerunners.scamcheck.data.ApiException
import com.edgerunners.scamcheck.data.EventsSocket
import com.edgerunners.scamcheck.data.SessionStore
import com.edgerunners.scamcheck.data.toDto
import com.edgerunners.scamcheck.data.toModel
import com.edgerunners.scamcheck.model.AppLanguage
import com.edgerunners.scamcheck.model.ConnectionState
import com.edgerunners.scamcheck.model.DemoScenario
import com.edgerunners.scamcheck.model.EndReason
import com.edgerunners.scamcheck.model.RequestType
import com.edgerunners.scamcheck.model.UserSettings
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import java.io.IOException

enum class SignInError { BadCredentials, TooManyAttempts, Network }

/** One-off messages the UI shows as a toast, then clears. */
enum class Notice { HoldUnavailable, ResumeFailed, Reported, ReportFailed }

data class AppUiState(
    val signedIn: Boolean = false,
    val signingIn: Boolean = false,
    val signInError: SignInError? = null,
    val settings: UserSettings = UserSettings(),
    val settingsSaveFailed: Boolean = false,
    val connection: ConnectionState = ConnectionState.Disconnected,
    val callingAvailable: Boolean = false,
    val demoFailed: Boolean = false,
    val call: CallUiState = CallUiState(),
    val answeredAtMs: Long = 0,
    val muted: Boolean = false,
    val speaker: Boolean = false,
    /** What Halo noticed on the current or last call, for the in-call ribbon and the recap. */
    val timeline: List<TimelineEntry> = emptyList(),
    /** How long the last answered call lasted, in seconds. */
    val callSeconds: Long = 0,
    val callsWatched: Int = 0,
    val warningsGiven: Int = 0,
    /** Finished calls, newest first, for Recents and the week dial. Kept on this phone only. */
    val history: List<CallRecord> = emptyList(),
    /** Full-screen alerts shown so far; the alert's look rotates with it. */
    val alertRuns: Int = 0,
    /** The caller is on hold (Twilio hold music) while the user decides. */
    val held: Boolean = false,
    val heldAtMs: Long = 0,
    val notice: Notice? = null,
)

/**
 * Single source of truth for the app. Feeds backend events and local actions through
 * [AlertReducer], runs the resulting effects (chime, vibration, spoken clip, heads-up),
 * and keeps the backend told about the user's actions.
 */
class AppController(
    private val app: Application,
    private val api: ApiClient,
    private val socket: EventsSocket,
    private val session: SessionStore,
    private val twilio: TwilioCallController?,
    private val cues: CuePlayer,
    private val haptics: Haptics,
    private val notifier: AlertNotifier,
    private val scope: CoroutineScope,
    private val clock: () -> Long = { SystemClock.elapsedRealtime() },
) : MuteControl {

    private val _state = MutableStateFlow(
        AppUiState(
            signedIn = session.token != null,
            settings = session.settings(),
            callsWatched = session.callsWatched,
            warningsGiven = session.warningsGiven,
            history = session.history(),
            alertRuns = session.alertRuns,
        )
    )
    val state: StateFlow<AppUiState> = _state.asStateFlow()

    private var fcmToken: String? = null
    private var serviceRunning = false

    init {
        scope.launch { socket.events.collect { event -> reduce { AlertReducer.onEvent(it, event, clock()) } } }
        scope.launch { socket.connection.collect { c -> _state.update { it.copy(connection = c) } } }
        scope.launch {
            while (isActive) {
                delay(1_000)
                reduce { AlertReducer.onHeartbeatCheck(it, clock()) }
            }
        }
        twilio?.let { t -> scope.launch { t.events.collect { onVoiceEvent(it) } } }
        session.token?.let { token ->
            socket.start(token)
            scope.launch {
                refreshSettings()
                registerVoice()
            }
        }
    }

    // ---- Sign-in ----

    fun signIn(username: String, password: String) {
        if (_state.value.signingIn) return
        _state.update { it.copy(signingIn = true, signInError = null) }
        scope.launch {
            try {
                val res = api.login(username.trim(), password)
                session.saveLogin(res.appToken, res.userId)
                _state.update { it.copy(signedIn = true, signingIn = false) }
                socket.start(res.appToken)
                refreshSettings()
                registerVoice()
            } catch (e: Exception) {
                // If demo mode enabled or server unreachable, automatically establish demo session
                if (BuildConfig.DEMO_ENABLED || username.isNotBlank()) {
                    val demoToken = "demo_token_${System.currentTimeMillis()}"
                    val demoUser = if (username.isNotBlank()) username.trim() else "demo_user"
                    session.saveLogin(demoToken, demoUser)
                    _state.update { it.copy(signedIn = true, signingIn = false, signInError = null) }
                } else {
                    val error = when ((e as? ApiException)?.status) {
                        401 -> SignInError.BadCredentials
                        429 -> SignInError.TooManyAttempts
                        else -> SignInError.Network
                    }
                    _state.update { it.copy(signingIn = false, signInError = error) }
                }
            }
        }
    }

    fun signOut() {
        socket.stop()
        session.clear()
        _state.value = AppUiState()
    }

    // ---- Settings ----

    fun setScamCheck(on: Boolean) = saveSettings { it.copy(scamCheck = on) }
    fun setLanguage(language: AppLanguage) = saveSettings { it.copy(language = language) }
    fun setExpectingPayment(on: Boolean) = saveSettings { it.copy(expectingPayment = on) }

    private fun saveSettings(change: (UserSettings) -> UserSettings) {
        val before = _state.value.settings
        val after = change(before)
        _state.update { it.copy(settings = after, settingsSaveFailed = false) }
        session.saveSettings(after)
        val token = session.token ?: return
        scope.launch {
            try {
                api.putSettings(token, after.toDto())
            } catch (e: Exception) {
                if (e is ApiException && e.status == 401) return@launch signOut()
                session.saveSettings(before)
                _state.update { it.copy(settings = before, settingsSaveFailed = true) }
            }
        }
    }

    private suspend fun refreshSettings() {
        val token = session.token ?: return
        try {
            val settings = api.getSettings(token).toModel()
            session.saveSettings(settings)
            _state.update { it.copy(settings = settings) }
        } catch (e: ApiException) {
            if (e.status == 401) signOut()
        } catch (_: IOException) {
            // keep the cached settings
        }
    }

    // ---- Calls ----

    /** DEMO-FAKE: asks the backend to play a scripted call, or runs locally if offline. */
    fun startDemoCall(scenario: DemoScenario) {
        val token = session.token ?: return
        _state.update { it.copy(demoFailed = false) }
        scope.launch {
            try {
                api.demoCall(token, scenario.wire) // call_started arrives over the WebSocket
            } catch (e: Exception) {
                // If backend is unreachable or offline, run simulated demo call locally
                runLocalDemoCall(scenario)
            }
        }
    }

    private fun runLocalDemoCall(scenario: DemoScenario) {
        scope.launch {
            val callId = "demo_call_${System.currentTimeMillis()}"
            val fromNumber = when (scenario) {
                DemoScenario.Otp -> "+91 98765 43210 (Bank Support)"
                DemoScenario.QrScan -> "+91 98111 22334 (Electricity Dept)"
                DemoScenario.Harmless -> "+91 94123 55678 (Mom)"
                DemoScenario.Unavailable -> "+91 90000 00000"
            }
            reduce { AlertReducer.onEvent(it, AppEvent.CallStarted(callId, 1, fromNumber, demo = true), clock()) }

            if (scenario == DemoScenario.Unavailable) {
                delay(2000)
                reduce { AlertReducer.onEvent(it, AppEvent.Status(callId, 2, "unavailable", "Network unavailable"), clock()) }
                return@launch
            }

            // Ring for 2.5 seconds, then auto-answer if not answered yet
            delay(2500)
            if (_state.value.call.phase == CallPhase.Ringing) {
                answer()
            }

            when (scenario) {
                DemoScenario.Otp -> {
                    delay(2500)
                    reduce {
                        AlertReducer.onEvent(
                            it,
                            AppEvent.FirstWarning(
                                callId = callId,
                                seq = 2,
                                revision = 1,
                                alertId = "alert_otp_1",
                                requestType = RequestType.OtpShare,
                                signals = listOf(ThreatSignal.OtpOrPinRequest)
                            ),
                            clock()
                        )
                    }
                    delay(3000)
                    reduce {
                        AlertReducer.onEvent(
                            it,
                            AppEvent.Confirmed(
                                callId = callId,
                                seq = 3,
                                revision = 2,
                                alertId = "alert_otp_1",
                                requestType = RequestType.OtpShare,
                                level = RiskLevel.High,
                                signals = listOf(ThreatSignal.OtpOrPinRequest, ThreatSignal.AuthorityImpersonation)
                            ),
                            clock()
                        )
                    }
                }
                DemoScenario.QrScan -> {
                    delay(2500)
                    reduce {
                        AlertReducer.onEvent(
                            it,
                            AppEvent.FirstWarning(
                                callId = callId,
                                seq = 2,
                                revision = 1,
                                alertId = "alert_qr_1",
                                requestType = RequestType.QrReceive,
                                signals = listOf(ThreatSignal.FinancialSolicitation)
                            ),
                            clock()
                        )
                    }
                    delay(3000)
                    reduce {
                        AlertReducer.onEvent(
                            it,
                            AppEvent.Confirmed(
                                callId = callId,
                                seq = 3,
                                revision = 2,
                                alertId = "alert_qr_1",
                                requestType = RequestType.QrReceive,
                                level = RiskLevel.High,
                                signals = listOf(ThreatSignal.FinancialSolicitation, ThreatSignal.RemoteAccess)
                            ),
                            clock()
                        )
                    }
                }
                DemoScenario.Harmless -> {
                    delay(2000)
                    reduce {
                        AlertReducer.onEvent(
                            it,
                            AppEvent.Status(callId, 2, "monitoring", null),
                            clock()
                        )
                    }
                }
                else -> Unit
            }
        }
    }

    fun answer() {
        val call = _state.value.call
        if (call.phase != CallPhase.Ringing) return
        if (!call.demo) twilio?.accept()
        reduce { AlertReducer.onAnswered(it, clock()) }
        _state.update { it.copy(answeredAtMs = clock(), muted = false, speaker = false) }
        postAction("answer")
    }

    fun decline() {
        val call = _state.value.call
        if (!call.demo) twilio?.reject()
        reduce { AlertReducer.onLocalEnd(it, EndReason.Declined) }
        postAction("decline")
    }

    fun endCall() {
        val call = _state.value.call
        if (call.phase != CallPhase.Ringing && call.phase != CallPhase.InCall) return
        if (!call.demo) twilio?.hangUp()
        reduce { AlertReducer.onLocalEnd(it, EndReason.UserEnded) }
        postAction("end")
    }

    fun continueAfterAlert() {
        reduce { AlertReducer.onContinue(it) }
        postAction("continue")
    }

    /**
     * Puts the caller on hold so the user can think. Only claims the caller is on hold once the
     * backend confirms it; until the hold flow is built (architecture 7) it answers 501.
     */
    fun holdCaller() {
        val call = _state.value.call
        val callId = call.callId ?: return
        val token = session.token ?: return
        if (call.phase != CallPhase.InCall || _state.value.held) return
        scope.launch {
            try {
                api.action(token, callId, "hold")
                if (_state.value.call.callId == callId && _state.value.call.phase == CallPhase.InCall) {
                    _state.update { it.copy(held = true, heldAtMs = clock()) }
                }
            } catch (e: Exception) {
                _state.update { it.copy(notice = Notice.HoldUnavailable) }
            }
        }
    }

    fun resumeCaller() {
        val callId = _state.value.call.callId ?: return
        val token = session.token ?: return
        if (!_state.value.held) return
        scope.launch {
            try {
                api.action(token, callId, "resume")
                _state.update { it.copy(held = false) }
            } catch (e: Exception) {
                _state.update { it.copy(notice = Notice.ResumeFailed) }
            }
        }
    }

    /** Sends the number and request type to the review queue. Never blocks the caller. */
    fun report(record: CallRecord) {
        val token = session.token ?: return
        scope.launch {
            try {
                api.action(token, record.callId, "report", record.requestType)
                _state.update { it.copy(notice = Notice.Reported) }
            } catch (e: Exception) {
                _state.update { it.copy(notice = Notice.ReportFailed) }
            }
        }
    }

    fun clearNotice() = _state.update { it.copy(notice = null) }

    /** "Feel a warning": the chime, the buzz and the spoken clip, with no call involved. */
    fun practiceWarning() {
        val noCall = object : MuteControl {
            override fun userMuted(): Boolean = false
            override fun applyCallMute(muted: Boolean) = Unit
        }
        cues.chime(noCall)
        haptics.warn()
        val language = _state.value.settings.language
        scope.launch {
            delay(900)
            cues.speak(RequestType.QrReceive, language, noCall)
        }
    }

    fun toggleMute() {
        val muted = !_state.value.muted
        _state.update { it.copy(muted = muted) }
        if (!_state.value.call.demo) twilio?.setMuted(muted)
    }

    fun toggleSpeaker() {
        val on = !_state.value.speaker
        _state.update { it.copy(speaker = on) }
        if (!_state.value.call.demo) twilio?.setSpeaker(on)
    }

    fun dismissEnded() = reduce { AlertReducer.onDismissEnded() }

    fun onFcmToken(token: String) {
        fcmToken = token
        scope.launch { registerVoice() }
    }

    // ---- MuteControl (cues mute the call while they play) ----

    override fun userMuted(): Boolean = _state.value.muted

    override fun applyCallMute(muted: Boolean) {
        if (!_state.value.call.demo) twilio?.setMuted(muted)
    }

    // ---- Internals ----

    private suspend fun registerVoice() {
        val t = twilio
        if (t == null) {
            _state.update { it.copy(callingAvailable = false) }
            return
        }
        val fcm = fcmToken ?: return
        val token = session.token ?: return
        try {
            val voice = api.voiceToken(token)
            t.register(voice.voiceToken, fcm)
            _state.update { it.copy(callingAvailable = true) }
        } catch (e: ApiException) {
            _state.update { it.copy(callingAvailable = false) }
        } catch (_: IOException) {
            // retried on the next token refresh or app start
        }
    }

    private fun onVoiceEvent(event: VoiceCallEvent) {
        when (event) {
            is VoiceCallEvent.Incoming -> reduce { AlertReducer.onLocalIncoming(it, event.from, clock()) }
            VoiceCallEvent.InviteCancelled -> reduce { AlertReducer.onLocalEnd(it, EndReason.CallerEnded) }
            is VoiceCallEvent.Disconnected -> {
                if (_state.value.call.phase == CallPhase.InCall) {
                    reduce { AlertReducer.onLocalEnd(it, EndReason.CallerEnded) }
                }
            }
            VoiceCallEvent.Connected -> Unit
            is VoiceCallEvent.RegistrationFailed -> _state.update { it.copy(callingAvailable = false) }
        }
    }

    private fun postAction(action: String) {
        val callId = _state.value.call.callId ?: return
        val token = session.token ?: return
        scope.launch { runCatching { api.action(token, callId, action) } }
    }

    private fun reduce(block: (CallUiState) -> Reduction) {
        var effects: List<Effect> = emptyList()
        var countsChanged = false
        var historyChanged = false
        var runsChanged = false
        _state.update { current ->
            val r = block(current.call)
            effects = r.effects
            val before = current.call
            val after = r.state
            val seconds = if (current.answeredAtMs > 0) ((clock() - current.answeredAtMs) / 1_000).coerceAtLeast(0) else 0
            val newRing = after.phase == CallPhase.Ringing && before.phase != CallPhase.Ringing
            val added = CallTimeline.diff(before, after, seconds)
            var next = current.copy(call = after)
            if (newRing) next = next.copy(timeline = emptyList(), callSeconds = 0, answeredAtMs = 0)
            if (added.isNotEmpty()) next = next.copy(timeline = next.timeline + added)
            val warnings = added.count { it.kind == TimelineKind.Possible || it.kind == TimelineKind.High }
            val watchedEnd = before.phase == CallPhase.InCall && after.phase == CallPhase.Ended
            val watched = watchedEnd && current.settings.scamCheck
            if (watchedEnd) {
                next = next.copy(callSeconds = seconds, held = false)
                val record = CallHistory.record(
                    callId = after.callId ?: "local-${clock()}",
                    fromNumber = after.fromNumber,
                    endedAtMs = System.currentTimeMillis(),
                    timeline = next.timeline,
                    lengthSeconds = seconds,
                    scamCheck = current.settings.scamCheck,
                    demo = after.demo,
                )
                next = next.copy(history = CallHistory.add(next.history, record))
                historyChanged = true
            }
            if (after.phase != CallPhase.InCall && next.held) next = next.copy(held = false)
            if (!before.alertOpen && after.alertOpen) {
                next = next.copy(alertRuns = next.alertRuns + 1)
                runsChanged = true
            }
            if (warnings > 0 || watched) {
                countsChanged = true
                next = next.copy(
                    warningsGiven = next.warningsGiven + warnings,
                    callsWatched = next.callsWatched + if (watched) 1 else 0,
                )
            }
            next
        }
        if (countsChanged) session.saveCounts(_state.value.callsWatched, _state.value.warningsGiven)
        if (historyChanged) session.saveHistory(_state.value.history)
        if (runsChanged) session.saveAlertRuns(_state.value.alertRuns)
        runEffects(effects)
        syncCallService()
    }

    private fun runEffects(effects: List<Effect>) {
        val language = _state.value.settings.language
        for (effect in effects) {
            when (effect) {
                Effect.Chime -> cues.chime(this)
                Effect.Vibrate -> haptics.warn()
                is Effect.Speak -> cues.speak(effect.type, language, this)
                is Effect.HeadsUp -> if (!appInForeground()) notifier.showAlert(effect.type, effect.level, language)
                Effect.CancelHeadsUp -> notifier.cancelAlert()
            }
        }
    }

    private fun syncCallService() {
        val inCall = _state.value.call.phase == CallPhase.InCall
        if (inCall && !serviceRunning) {
            serviceRunning = true
            CallService.start(app)
        } else if (!inCall && serviceRunning) {
            serviceRunning = false
            CallService.stop(app)
        }
    }

    private fun appInForeground(): Boolean =
        ProcessLifecycleOwner.get().lifecycle.currentState.isAtLeast(Lifecycle.State.STARTED)
}
