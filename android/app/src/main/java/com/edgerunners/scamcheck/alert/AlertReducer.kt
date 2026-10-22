package com.edgerunners.scamcheck.alert

import com.edgerunners.scamcheck.data.AppEvent
import com.edgerunners.scamcheck.model.EndReason
import com.edgerunners.scamcheck.model.RequestType
import com.edgerunners.scamcheck.model.RiskLevel
import com.edgerunners.scamcheck.model.ThreatSignal

enum class CallPhase { Idle, Ringing, InCall, Ended }

/** What the in-call status line shows. There is no "safe" state. */
enum class Monitor { Starting, Listening, Checking, Unavailable, Off }

data class ActiveAlert(
    val id: String,
    val type: RequestType,
    val level: RiskLevel,
    val confirmed: Boolean,
    /** "What they said" chips. Shown only; the level comes from the event alone. */
    val signals: List<ThreatSignal> = emptyList(),
)

data class CallUiState(
    val callId: String? = null,
    val fromNumber: String? = null,
    val demo: Boolean = false,
    val phase: CallPhase = CallPhase.Idle,
    val monitor: Monitor = Monitor.Starting,
    val alert: ActiveAlert? = null,
    /** The full-screen alert is showing (only after a confirmed assessment). */
    val alertOpen: Boolean = false,
    val continued: Boolean = false,
    val lastSeq: Int = 0,
    val lastRevision: Int = -1,
    val endReason: EndReason? = null,
    val lastEventAtMs: Long = 0,
    val lastChimeAtMs: Map<RequestType, Long> = emptyMap(),
)

/** Side effects the controller performs after a state change. */
sealed interface Effect {
    data object Chime : Effect
    data object Vibrate : Effect
    data class Speak(val type: RequestType, val level: RiskLevel) : Effect
    data class HeadsUp(val type: RequestType, val level: RiskLevel) : Effect
    data object CancelHeadsUp : Effect
}

data class Reduction(val state: CallUiState, val effects: List<Effect> = emptyList())

/**
 * Pure state machine for one call's warnings. No Android, no I/O, so it is unit tested.
 *
 * Rules: ignore events for other calls or with an older event_seq; one chime per request
 * type per [CHIME_WINDOW_MS]; confirmed alerts open full screen; a cleared alert returns
 * quietly to Listening; [HEARTBEAT_TIMEOUT_MS] of silence means Protection unavailable.
 */
object AlertReducer {
    const val CHIME_WINDOW_MS = 20_000L
    const val HEARTBEAT_TIMEOUT_MS = 10_000L

    fun onEvent(state: CallUiState, event: AppEvent, nowMs: Long): Reduction {
        if (event is AppEvent.CallStarted) return onCallStarted(state, event, nowMs)
        if (event !is AppEvent.CallEvent) return Reduction(state)
        if (state.callId != event.callId || event.seq <= state.lastSeq) return Reduction(state)
        val base = state.copy(lastSeq = event.seq, lastEventAtMs = nowMs)
        return when (event) {
            is AppEvent.Status -> Reduction(base.copy(monitor = monitorFor(base, event.state)))
            is AppEvent.FirstWarning -> onFirstWarning(base, event, nowMs)
            is AppEvent.Confirmed -> onConfirmed(base, event)
            is AppEvent.Cleared -> onCleared(base, event)
            is AppEvent.CallEnded -> Reduction(
                base.copy(phase = CallPhase.Ended, endReason = event.reason, alertOpen = false),
                listOf(Effect.CancelHeadsUp),
            )
            is AppEvent.CallStarted -> Reduction(state)
        }
    }

    /** Twilio rang before the backend's call_started arrived: ring now, adopt the id later. */
    fun onLocalIncoming(state: CallUiState, fromNumber: String, nowMs: Long): Reduction =
        if (state.phase == CallPhase.Idle || state.phase == CallPhase.Ended) {
            Reduction(CallUiState(fromNumber = fromNumber, phase = CallPhase.Ringing, lastEventAtMs = nowMs))
        } else {
            Reduction(state)
        }

    fun onAnswered(state: CallUiState, nowMs: Long): Reduction =
        if (state.phase == CallPhase.Ringing) {
            Reduction(state.copy(phase = CallPhase.InCall, monitor = Monitor.Starting, lastEventAtMs = nowMs))
        } else {
            Reduction(state)
        }

    fun onContinue(state: CallUiState): Reduction = Reduction(
        state.copy(alert = null, alertOpen = false, continued = true, monitor = Monitor.Listening),
        listOf(Effect.CancelHeadsUp),
    )

    fun onLocalEnd(state: CallUiState, reason: EndReason): Reduction =
        if (state.phase == CallPhase.Ringing || state.phase == CallPhase.InCall) {
            Reduction(
                state.copy(phase = CallPhase.Ended, endReason = reason, alertOpen = false),
                listOf(Effect.CancelHeadsUp),
            )
        } else {
            Reduction(state)
        }

    fun onDismissEnded(): Reduction = Reduction(CallUiState())

    fun onHeartbeatCheck(state: CallUiState, nowMs: Long): Reduction {
        val quiet = nowMs - state.lastEventAtMs > HEARTBEAT_TIMEOUT_MS
        return if (state.phase == CallPhase.InCall && state.monitor != Monitor.Off &&
            state.monitor != Monitor.Unavailable && quiet
        ) {
            Reduction(state.copy(monitor = Monitor.Unavailable))
        } else {
            Reduction(state)
        }
    }

    private fun onCallStarted(state: CallUiState, event: AppEvent.CallStarted, nowMs: Long): Reduction {
        val adoptLocalRing = state.phase == CallPhase.Ringing && state.callId == null
        return if (adoptLocalRing) {
            Reduction(state.copy(callId = event.callId, demo = event.demo, lastSeq = event.seq, lastEventAtMs = nowMs))
        } else if (state.phase == CallPhase.Idle || state.phase == CallPhase.Ended) {
            Reduction(
                CallUiState(
                    callId = event.callId,
                    fromNumber = event.fromNumber,
                    demo = event.demo,
                    phase = CallPhase.Ringing,
                    lastSeq = event.seq,
                    lastEventAtMs = nowMs,
                )
            )
        } else {
            Reduction(state) // already busy with another call
        }
    }

    private fun monitorFor(state: CallUiState, wire: String): Monitor = when (wire) {
        "starting" -> Monitor.Starting
        "monitoring", "degraded" -> if (state.alert?.confirmed == false) Monitor.Checking else Monitor.Listening
        "unavailable" -> Monitor.Unavailable
        "off" -> Monitor.Off
        else -> state.monitor
    }

    private fun onFirstWarning(state: CallUiState, event: AppEvent.FirstWarning, nowMs: Long): Reduction {
        if (state.phase != CallPhase.InCall) return Reduction(state)
        val sameAlert = state.alert?.id == event.alertId
        val alert = if (sameAlert) {
            state.alert!!
        } else {
            ActiveAlert(event.alertId, event.requestType, RiskLevel.Possible, confirmed = false, signals = event.signals)
        }
        val lastChime = state.lastChimeAtMs[event.requestType]
        val chime = !sameAlert && (lastChime == null || nowMs - lastChime >= CHIME_WINDOW_MS)
        val next = state.copy(
            alert = alert,
            monitor = Monitor.Checking,
            lastChimeAtMs = if (chime) state.lastChimeAtMs + (event.requestType to nowMs) else state.lastChimeAtMs,
        )
        val effects = if (chime) {
            listOf(Effect.Chime, Effect.Vibrate, Effect.HeadsUp(event.requestType, RiskLevel.Possible))
        } else {
            emptyList()
        }
        return Reduction(next, effects)
    }

    private fun onConfirmed(state: CallUiState, event: AppEvent.Confirmed): Reduction {
        if (state.phase != CallPhase.InCall || event.revision <= state.lastRevision) return Reduction(state)
        val previous = state.alert
        val unchanged = previous != null && previous.confirmed && previous.id == event.alertId &&
            previous.level == event.level && previous.type == event.requestType
        val next = state.copy(
            alert = ActiveAlert(event.alertId, event.requestType, event.level, confirmed = true, signals = event.signals),
            alertOpen = true,
            monitor = if (state.monitor == Monitor.Unavailable) Monitor.Unavailable else Monitor.Listening,
            lastRevision = event.revision,
        )
        if (unchanged) return Reduction(next)
        return Reduction(
            next,
            listOf(Effect.Speak(event.requestType, event.level), Effect.Vibrate, Effect.HeadsUp(event.requestType, event.level)),
        )
    }

    private fun onCleared(state: CallUiState, event: AppEvent.Cleared): Reduction {
        if (event.revision <= state.lastRevision || state.alert?.id != event.alertId) {
            return Reduction(state)
        }
        return Reduction(
            state.copy(
                alert = null,
                alertOpen = false,
                lastRevision = event.revision,
                monitor = if (state.monitor == Monitor.Unavailable) Monitor.Unavailable else Monitor.Listening,
            ),
            listOf(Effect.CancelHeadsUp),
        )
    }
}
