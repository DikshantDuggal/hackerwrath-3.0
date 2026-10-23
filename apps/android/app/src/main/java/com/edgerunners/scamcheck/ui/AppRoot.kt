package com.edgerunners.scamcheck.ui

import android.app.Activity
import android.content.ActivityNotFoundException
import android.content.Context
import android.content.Intent
import android.content.res.Configuration
import android.net.Uri
import androidx.compose.animation.AnimatedContent
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.EnterTransition
import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.SideEffect
import androidx.compose.runtime.Stable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableLongStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalConfiguration
import androidx.compose.ui.graphics.luminance
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalView
import androidx.core.view.WindowCompat
import com.edgerunners.scamcheck.AppController
import com.edgerunners.scamcheck.AppUiState
import com.edgerunners.scamcheck.BuildConfig
import com.edgerunners.scamcheck.Notice
import com.edgerunners.scamcheck.R
import com.edgerunners.scamcheck.alert.ActiveAlert
import com.edgerunners.scamcheck.alert.CallHistory
import com.edgerunners.scamcheck.alert.CallPhase
import com.edgerunners.scamcheck.model.AppLanguage
import com.edgerunners.scamcheck.model.ConnectionState
import com.edgerunners.scamcheck.ui.screens.SignInScreen
import com.edgerunners.scamcheck.ui.spell.CircleScreen
import com.edgerunners.scamcheck.ui.spell.CircleSel
import com.edgerunners.scamcheck.ui.spell.ContactSheet
import com.edgerunners.scamcheck.ui.spell.ContactsTab
import com.edgerunners.scamcheck.ui.spell.DemoPeople
import com.edgerunners.scamcheck.ui.spell.DemoSheet
import com.edgerunners.scamcheck.ui.spell.EarScreen
import com.edgerunners.scamcheck.ui.spell.HomeTab
import com.edgerunners.scamcheck.ui.spell.KeypadSheet
import com.edgerunners.scamcheck.ui.spell.PauseScreen
import com.edgerunners.scamcheck.ui.spell.PracticeScreen
import com.edgerunners.scamcheck.ui.spell.RecentsTab
import com.edgerunners.scamcheck.ui.spell.RecoverySheet
import com.edgerunners.scamcheck.ui.spell.RecoveryStep
import com.edgerunners.scamcheck.ui.spell.SettingsSheet
import com.edgerunners.scamcheck.ui.spell.SpellAlertScreen
import com.edgerunners.scamcheck.ui.spell.SpellIncomingScreen
import com.edgerunners.scamcheck.ui.spell.SpellToast
import com.edgerunners.scamcheck.ui.spell.StoryScreen
import com.edgerunners.scamcheck.ui.spell.Tab
import com.edgerunners.scamcheck.ui.spell.TabsScreen
import com.edgerunners.scamcheck.ui.spell.alertOnNight
import com.edgerunners.scamcheck.ui.spell.rememberElapsed
import com.edgerunners.scamcheck.ui.theme.LocalReduceMotion
import com.edgerunners.scamcheck.ui.theme.Spell
import kotlinx.coroutines.delay
import java.util.Locale

private enum class Route { SignIn, Tabs, Practice, Incoming, InCall, Ended }

private enum class Sheet { Settings, Demo, Recovery, Keypad, Contact }

/** Where the user is inside the app, apart from the call (which the controller owns). */
@Stable
private class SpellNav {
    var tab by mutableStateOf(Tab.Home)
    var circleOpen by mutableStateOf(false)
    var circleSel by mutableStateOf(CircleSel.AddOut)
    var sheet by mutableStateOf<Sheet?>(null)
    var contactId by mutableStateOf<String?>(null)
    var practice by mutableStateOf(false)
    var toast by mutableStateOf<String?>(null)
    var selectedDay by mutableIntStateOf(6)
    var onlyWarnings by mutableStateOf(false)
    var openCallId by mutableStateOf<String?>(null)
    var query by mutableStateOf("")
    var dial by mutableStateOf("")
}

private fun routeFor(state: AppUiState, practice: Boolean): Route = when {
    !state.signedIn -> Route.SignIn
    state.call.phase == CallPhase.Ringing -> Route.Incoming
    state.call.phase == CallPhase.InCall -> Route.InCall
    state.call.phase == CallPhase.Ended -> Route.Ended
    practice -> Route.Practice
    else -> Route.Tabs
}

@Composable
fun AppRoot(state: AppUiState, controller: AppController) {
    Localized(state.settings.language) {
        val context = LocalContext.current
        val reduceMotion = LocalReduceMotion.current
        val nav = remember { SpellNav() }
        val route = routeFor(state, nav.practice)
        val notBuilt = context.getString(R.string.sb_not_built)

        // Toasts: one-off notices from the controller, and failed settings saves.
        LaunchedEffect(state.notice) {
            val notice = state.notice ?: return@LaunchedEffect
            nav.toast = context.getString(
                when (notice) {
                    Notice.HoldUnavailable -> R.string.sb_notice_hold_unavailable
                    Notice.ResumeFailed -> R.string.sb_notice_resume_failed
                    Notice.Reported -> R.string.sb_notice_reported
                    Notice.ReportFailed -> R.string.sb_notice_report_failed
                }
            )
            controller.clearNotice()
        }
        LaunchedEffect(state.settingsSaveFailed) {
            if (state.settingsSaveFailed) nav.toast = context.getString(R.string.home_save_failed)
        }
        // A call takes over the screen: close whatever was open.
        LaunchedEffect(route) {
            if (route == Route.Incoming || route == Route.InCall || route == Route.SignIn) {
                nav.sheet = null
                nav.practice = false
            }
        }
        val now by rememberMinuteClock()

        // Status and navigation bar icons: light over the dark call screens and most alert looks.
        val premium = Spell.colors.premium
        val alertShowing = state.call.alertOpen && state.call.phase == CallPhase.InCall && !state.held
        val lightAlert = alertShowing && !alertOnNight(state.alertRuns) && Spell.colors.bg.luminance() > 0.5f
        val darkScreen = when {
            alertShowing -> !lightAlert
            state.held -> premium
            else -> premium || route == Route.Incoming || route == Route.InCall || route == Route.Practice
        }
        val view = LocalView.current
        SideEffect {
            val window = (view.context as? Activity)?.window ?: return@SideEffect
            WindowCompat.getInsetsController(window, view).apply {
                isAppearanceLightStatusBars = !darkScreen
                isAppearanceLightNavigationBars = !darkScreen
            }
        }

        Surface(Modifier.fillMaxSize(), color = MaterialTheme.colorScheme.background) {
            Box(Modifier.fillMaxSize()) {
                AnimatedContent(targetState = route, transitionSpec = { screenTransition(reduceMotion) }, label = "screen") { screen ->
                    when (screen) {
                        Route.SignIn -> SignInScreen(state, controller::signIn)
                        Route.Incoming -> SpellIncomingScreen(state.call.fromNumber, state.settings.scamCheck, controller::answer, controller::decline)
                        Route.InCall -> EarScreen(
                            fromNumber = state.call.fromNumber,
                            answeredAtMs = state.answeredAtMs,
                            monitor = state.call.monitor,
                            scamOn = state.settings.scamCheck,
                            continued = state.call.continued,
                            alert = state.call.alert,
                            muted = state.muted,
                            speaker = state.speaker,
                            onMute = controller::toggleMute,
                            onSpeaker = controller::toggleSpeaker,
                            onEnd = controller::endCall,
                        )
                        Route.Ended -> StoryScreen(
                            reason = state.call.endReason,
                            timeline = state.timeline,
                            callSeconds = state.callSeconds,
                            scamOn = state.settings.scamCheck,
                            onOpenRecovery = { nav.sheet = Sheet.Recovery },
                            onBack = {
                                nav.sheet = null
                                controller.dismissEnded()
                            },
                        )
                        Route.Practice -> PracticeScreen(state.settings.language, controller::practiceWarning) { nav.practice = false }
                        Route.Tabs -> TabsScreen(
                            tab = nav.tab,
                            circleOpen = nav.circleOpen,
                            onTab = {
                                nav.tab = it
                                nav.circleOpen = false
                            },
                            onSettings = { nav.sheet = Sheet.Settings },
                            onKeypad = {
                                nav.dial = ""
                                nav.sheet = Sheet.Keypad
                            },
                        ) { tab ->
                            when {
                                nav.circleOpen -> CircleScreen(
                                    selected = nav.circleSel,
                                    onSelect = { nav.circleSel = it },
                                    onBack = { nav.circleOpen = false },
                                    onNotBuilt = { nav.toast = notBuilt },
                                )
                                tab == Tab.Home -> HomeTab(
                                    scamOn = state.settings.scamCheck,
                                    live = state.connection == ConnectionState.Connected,
                                    history = state.history,
                                    nowMs = now,
                                    selectedDay = nav.selectedDay,
                                    onSelectDay = { nav.selectedDay = it },
                                    onToggleScam = controller::setScamCheck,
                                    onLongPressGuardian = if (BuildConfig.DEMO_ENABLED) ({ nav.sheet = Sheet.Demo }) else null,
                                    onOpenRecents = { nav.tab = Tab.Recents },
                                    onOpenRecovery = { nav.sheet = Sheet.Recovery },
                                )
                                tab == Tab.Recents -> {
                                    // The newest warning starts open; "" means the user closed them all.
                                    val openId = nav.openCallId ?: state.history.firstOrNull { it.warned }?.callId
                                    RecentsTab(
                                    history = state.history,
                                    nowMs = now,
                                    onlyWarnings = nav.onlyWarnings,
                                    onFilter = { nav.onlyWarnings = it },
                                    openCallId = openId,
                                    onToggleOpen = { id -> nav.openCallId = if (openId == id) "" else id },
                                    onReport = controller::report,
                                    onNotBuilt = { nav.toast = notBuilt },
                                    onOpenRecovery = { nav.sheet = Sheet.Recovery },
                                    )
                                }
                                else -> ContactsTab(
                                    query = nav.query,
                                    onQuery = { nav.query = it },
                                    onOpenCircle = { sel ->
                                        nav.circleSel = sel
                                        nav.circleOpen = true
                                    },
                                    onOpenContact = { id ->
                                        nav.contactId = id
                                        nav.sheet = Sheet.Contact
                                    },
                                )
                            }
                        }
                    }
                }

                // The confirmed alert rises over the call screen; amber "checking" never does.
                val inCall = state.call.phase == CallPhase.InCall
                val alert = rememberLastNonNull(state.call.alert)
                AnimatedVisibility(
                    visible = state.call.alertOpen && inCall && !state.held,
                    enter = EnterTransition.None,
                    exit = fadeOut(tween(Motion.SHORT)),
                ) {
                    if (alert != null) {
                        val elapsed = rememberElapsed(state.answeredAtMs)
                        val askedAt = CallHistory.firstWarning(state.timeline)?.atSeconds
                        SpellAlertScreen(
                            alert = alert,
                            run = state.alertRuns,
                            askedAgoSeconds = if (askedAt != null) (elapsed - askedAt).coerceAtLeast(1) else 0,
                            onEndCall = controller::endCall,
                            onHold = controller::holdCaller,
                            onKeepTalking = controller::continueAfterAlert,
                        )
                    }
                }
                AnimatedVisibility(visible = state.held && inCall, enter = fadeIn(tween(Motion.MEDIUM)), exit = fadeOut(tween(Motion.SHORT))) {
                    PauseScreen(state.heldAtMs, alert?.type, controller::endCall, controller::resumeCaller)
                }

                // Sheets sit over the tabs and the after-call screen only.
                val sheets = route == Route.Tabs || route == Route.Ended
                SettingsSheet(
                    visible = sheets && nav.sheet == Sheet.Settings,
                    language = state.settings.language,
                    onLanguage = controller::setLanguage,
                    expecting = state.settings.expectingPayment,
                    onExpecting = { on ->
                        controller.setExpectingPayment(on)
                        nav.toast = context.getString(if (on) R.string.sb_toast_expect_on else R.string.sb_toast_expect_off)
                    },
                    demoEnabled = BuildConfig.DEMO_ENABLED,
                    onPractice = {
                        nav.sheet = null
                        nav.practice = true
                    },
                    onCircle = {
                        nav.sheet = null
                        nav.tab = Tab.Contacts
                        nav.circleSel = DemoPeople.TRUSTED_ID
                        nav.circleOpen = true
                    },
                    onDemo = { nav.sheet = Sheet.Demo },
                    onSignOut = {
                        nav.sheet = null
                        controller.signOut()
                    },
                    onDismiss = { nav.sheet = null },
                )
                DemoSheet(
                    visible = sheets && nav.sheet == Sheet.Demo,
                    failed = state.demoFailed,
                    onStart = { scenario ->
                        nav.sheet = null
                        controller.startDemoCall(scenario)
                    },
                    onDismiss = { nav.sheet = null },
                )
                RecoverySheet(
                    visible = sheets && nav.sheet == Sheet.Recovery,
                    onStep = { step ->
                        when (step) {
                            RecoveryStep.Helpline -> open(context, Intent(Intent.ACTION_DIAL, Uri.parse("tel:1930"))) { nav.toast = it }
                            RecoveryStep.ReportOnline -> open(context, Intent(Intent.ACTION_VIEW, Uri.parse("https://cybercrime.gov.in"))) { nav.toast = it }
                            RecoveryStep.Bank -> nav.toast = context.getString(R.string.sb_step_bank_toast)
                            RecoveryStep.Tell -> nav.toast = notBuilt // DEMO-FAKE: no trusted-person messaging yet
                        }
                    },
                    onDismiss = { nav.sheet = null },
                )
                KeypadSheet(
                    visible = sheets && nav.sheet == Sheet.Keypad,
                    dial = nav.dial,
                    onDigit = { if (nav.dial.length < 14) nav.dial += it },
                    onDelete = { nav.dial = nav.dial.dropLast(1) },
                    onCall = {
                        // DEMO-FAKE: the app can't place outgoing calls yet.
                        nav.toast = if (nav.dial.isEmpty()) context.getString(R.string.sb_type_number) else notBuilt
                        if (nav.dial.isNotEmpty()) nav.sheet = null
                    },
                    onDismiss = { nav.sheet = null },
                )
                ContactSheet(
                    visible = sheets && nav.sheet == Sheet.Contact,
                    contactId = nav.contactId,
                    onCall = {
                        nav.sheet = null
                        nav.toast = notBuilt // DEMO-FAKE: sample contacts can't be called
                    },
                    onCircle = { person ->
                        nav.sheet = null
                        if (person.circle != null) {
                            nav.circleSel = person.id
                            nav.circleOpen = true
                        } else {
                            nav.toast = notBuilt
                        }
                    },
                    onDismiss = { nav.sheet = null },
                )

                SpellToast(nav.toast, onGone = { nav.toast = null })
            }
        }
    }
}

/** Wall-clock time, refreshed every minute, for "today" and the week dial. */
@Composable
private fun rememberMinuteClock(): androidx.compose.runtime.State<Long> {
    val now = remember { mutableLongStateOf(System.currentTimeMillis()) }
    LaunchedEffect(Unit) {
        while (true) {
            delay(60_000)
            now.longValue = System.currentTimeMillis()
        }
    }
    return now
}

private fun open(context: Context, intent: Intent, onFail: (String) -> Unit) {
    try {
        context.startActivity(intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
    } catch (_: ActivityNotFoundException) {
        onFail(context.getString(R.string.sb_cant_open))
    }
}

/** Keeps the last alert on screen while the sheet animates away. */
@Composable
private fun rememberLastNonNull(value: ActiveAlert?): ActiveAlert? {
    val holder = remember { arrayOfNulls<ActiveAlert>(1) }
    if (value != null) holder[0] = value
    return holder[0]
}

/** Shows strings in the language chosen in Settings, whatever the phone's own language is. */
@Composable
private fun Localized(language: AppLanguage, content: @Composable () -> Unit) {
    val base = LocalContext.current
    val baseConfig = LocalConfiguration.current
    val config = remember(language, baseConfig) {
        Configuration(baseConfig).apply { setLocale(Locale(language.code)) }
    }
    val localized = remember(config) { base.createConfigurationContext(config) }
    CompositionLocalProvider(LocalContext provides localized, LocalConfiguration provides config) {
        content()
    }
}
