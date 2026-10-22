package com.edgerunners.scamcheck.ui.spell

import androidx.compose.foundation.layout.safeDrawingPadding
import android.os.SystemClock
import androidx.activity.compose.BackHandler
import androidx.compose.animation.core.Animatable
import androidx.compose.animation.core.CubicBezierEasing
import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.outlined.VolumeUp
import androidx.compose.material.icons.outlined.Call
import androidx.compose.material.icons.outlined.CallEnd
import androidx.compose.material.icons.outlined.ChevronRight
import androidx.compose.material.icons.outlined.Close
import androidx.compose.material.icons.outlined.MicOff
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableLongStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.RectangleShape
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.TransformOrigin
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.graphics.luminance
import androidx.compose.ui.hapticfeedback.HapticFeedbackType
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.platform.LocalHapticFeedback
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.clearAndSetSemantics
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.onLongClick
import androidx.compose.ui.semantics.paneTitle
import androidx.compose.ui.semantics.role
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.toggleableState
import androidx.compose.ui.state.ToggleableState
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.em
import androidx.compose.ui.unit.sp
import com.edgerunners.scamcheck.R
import com.edgerunners.scamcheck.alert.ActiveAlert
import com.edgerunners.scamcheck.alert.CallHistory
import com.edgerunners.scamcheck.alert.CallOutcome
import com.edgerunners.scamcheck.alert.Monitor
import com.edgerunners.scamcheck.alert.TimelineEntry
import com.edgerunners.scamcheck.model.AppLanguage
import com.edgerunners.scamcheck.model.EndReason
import com.edgerunners.scamcheck.model.RequestType
import com.edgerunners.scamcheck.model.RiskLevel
import com.edgerunners.scamcheck.ui.Motion
import com.edgerunners.scamcheck.ui.theme.AlertEntrance
import com.edgerunners.scamcheck.ui.theme.Edition
import com.edgerunners.scamcheck.ui.theme.LocalReduceMotion
import com.edgerunners.scamcheck.ui.theme.Spell
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

/** Seconds since [sinceMs] (elapsedRealtime), ticking once a second. */
@Composable
fun rememberElapsed(sinceMs: Long): Long {
    var now by remember { mutableLongStateOf(SystemClock.elapsedRealtime()) }
    LaunchedEffect(sinceMs) {
        while (true) {
            now = SystemClock.elapsedRealtime()
            delay(1_000)
        }
    }
    return if (sinceMs <= 0) 0 else ((now - sinceMs).coerceAtLeast(0) / 1_000)
}

@Composable
private fun langName(language: AppLanguage): String = stringResource(
    when (language) {
        AppLanguage.English -> R.string.sb_lang_name_en
        AppLanguage.Hindi -> R.string.sb_lang_name_hi
        AppLanguage.Punjabi -> R.string.sb_lang_name_pa
    }
)

// ---------- Incoming ----------

@Composable
fun SpellIncomingScreen(fromNumber: String?, scamOn: Boolean, onAnswer: () -> Unit, onDecline: () -> Unit) {
    val c = Spell.colors
    Column(
        Modifier.fillMaxSize().background(c.night).safeDrawingPadding().padding(start = 22.dp, end = 22.dp, top = 56.dp, bottom = 28.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(14.dp),
    ) {
        Text(stringResource(R.string.incoming_title), style = TextStyle(fontSize = 14.sp), color = c.nightMuted)
        Box(Modifier.weight(1f).fillMaxWidth(), contentAlignment = Alignment.Center) {
            EarGlow(c.earGlow)
            Column(horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(14.dp)) {
                Box(Modifier.size(196.dp)) {
                    GuardianBlob(Blob.Cookie, Modifier.fillMaxSize(), radius = 92f, stroke = c.earRing, strokeUnits = 1.4f, spin = Spin.Reverse)
                    GuardianBlob(Blob.Cookie, Modifier.fillMaxSize(), radius = 64f, color = if (scamOn) c.earFill else c.earOff, spin = Spin.Fast, highlight = 0.35f)
                    Icon(Icons.Outlined.Call, contentDescription = null, tint = c.onGuardian, modifier = Modifier.size(40.dp).align(Alignment.Center))
                }
                Display(stringResource(R.string.unknown_number), 30f, color = c.nightInk, align = TextAlign.Center)
                Text(fromNumber.orEmpty(), style = TextStyle(fontSize = 18.sp), color = c.nightMuted)
                Row(
                    Modifier.clip(RoundedCornerShape(999.dp)).background(c.nightCard).border(1.dp, c.nightLine, RoundedCornerShape(999.dp)).padding(horizontal = 14.dp, vertical = 9.dp),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    LiveDot(active = scamOn)
                    Text(stringResource(if (scamOn) R.string.scam_check_on else R.string.scam_check_off), style = TextStyle(fontSize = 14.sp, fontWeight = FontWeight.SemiBold), color = c.nightInk)
                }
            }
        }
        Row(horizontalArrangement = Arrangement.spacedBy(14.dp)) {
            SpellButton(stringResource(R.string.decline), onDecline, Modifier.weight(1f), background = c.hangUp, content = c.onGuardian, height = 64.dp)
            SpellButton(stringResource(R.string.answer), onAnswer, Modifier.weight(1f), background = c.accent, content = c.onAccent, height = 64.dp)
        }
    }
}

@Composable
private fun EarGlow(color: Color, size: Dp = 300.dp) {
    Box(Modifier.size(size).drawBehind { drawCircle(Brush.radialGradient(listOf(color, color.copy(alpha = 0f)))) })
}

// ---------- At your ear (in call) ----------

/**
 * The call screen. The phone is usually at the user's ear, so it says little: the guardian,
 * one status line, and a way to end the call. When someone asks for money it turns amber and buzzes.
 */
@Composable
fun EarScreen(
    fromNumber: String?,
    answeredAtMs: Long,
    monitor: Monitor,
    scamOn: Boolean,
    continued: Boolean,
    alert: ActiveAlert?,
    muted: Boolean,
    speaker: Boolean,
    onMute: () -> Unit,
    onSpeaker: () -> Unit,
    onEnd: () -> Unit,
) {
    val c = Spell.colors
    val seconds = rememberElapsed(answeredAtMs)
    val heard = monitor == Monitor.Checking
    val off = !scamOn || monitor == Monitor.Off
    val status = when {
        off -> stringResource(R.string.status_off)
        monitor == Monitor.Unavailable -> stringResource(R.string.status_unavailable)
        monitor == Monitor.Starting -> stringResource(R.string.status_starting)
        heard -> stringResource(heardText(alert?.type))
        continued -> stringResource(R.string.status_continued)
        else -> stringResource(R.string.sb_listening)
    }
    val sub = when {
        off -> null
        monitor == Monitor.Unavailable -> stringResource(R.string.status_unavailable_sub)
        heard -> stringResource(R.string.status_checking_sub)
        else -> stringResource(R.string.sb_ear_note)
    }
    Column(
        Modifier.fillMaxSize().background(c.night).safeDrawingPadding().padding(start = 22.dp, end = 22.dp, top = 56.dp, bottom = 28.dp),
        verticalArrangement = Arrangement.spacedBy(18.dp),
    ) {
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
            Text(fromNumber?.ifEmpty { null } ?: stringResource(R.string.unknown_number), style = TextStyle(fontSize = 14.sp), color = c.nightMuted)
            Text(clock(seconds), style = TextStyle(fontSize = 14.sp), color = c.nightMuted)
        }
        Box(Modifier.weight(1f).fillMaxWidth(), contentAlignment = Alignment.Center) {
            EarGlow(if (heard) c.warnGlow else c.earGlow)
            Column(horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(14.dp)) {
                Box(Modifier.size(196.dp)) {
                    GuardianBlob(Blob.Cookie, Modifier.fillMaxSize(), radius = 92f, stroke = if (heard) c.warnRing else c.earRing, strokeUnits = 1.4f, spin = Spin.Reverse)
                    GuardianBlob(
                        if (heard) Blob.Burst else if (monitor == Monitor.Unavailable) Blob.Soft else Blob.Cookie,
                        Modifier.fillMaxSize(),
                        radius = if (heard) 74f else 64f,
                        color = when {
                            heard -> c.warn
                            off || monitor == Monitor.Unavailable -> c.earOff
                            else -> c.earFill
                        },
                        spin = if (heard) Spin.Fast else Spin.Normal,
                        highlight = 0.35f,
                    )
                }
                Text(
                    status,
                    style = TextStyle(fontSize = 17.sp, fontWeight = FontWeight.Bold, lineHeight = 23.sp),
                    color = if (heard) c.warnSoft else c.nightInk,
                    textAlign = TextAlign.Center,
                    modifier = Modifier.semantics { liveRegion = LiveRegionMode.Polite },
                )
                if (heard) HapBars(Modifier.width(120.dp))
                if (sub != null) {
                    Body(sub, 14.sp, color = c.nightMuted, lineHeight = 1.5f, align = TextAlign.Center, modifier = Modifier.widthIn(max = 280.dp))
                }
            }
        }
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceEvenly, verticalAlignment = Alignment.CenterVertically) {
            NightToggle(Icons.Outlined.MicOff, stringResource(R.string.mute), muted, onMute)
            Box(
                Modifier.size(68.dp).clip(RoundedCornerShape(24.dp)).background(c.hangUp).press(onEnd, label = stringResource(R.string.end_call)),
                contentAlignment = Alignment.Center,
            ) { Icon(Icons.Outlined.CallEnd, contentDescription = stringResource(R.string.end_call), tint = c.onGuardian, modifier = Modifier.size(28.dp)) }
            NightToggle(Icons.AutoMirrored.Outlined.VolumeUp, stringResource(R.string.speaker), speaker, onSpeaker)
        }
    }
}

@Composable
private fun NightToggle(icon: androidx.compose.ui.graphics.vector.ImageVector, label: String, on: Boolean, onClick: () -> Unit) {
    val c = Spell.colors
    Column(horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(6.dp)) {
        Box(
            Modifier
                .size(52.dp)
                .clip(RoundedCornerShape(18.dp))
                .background(if (on) c.nightInk else c.nightCard)
                .border(1.dp, c.nightLine, RoundedCornerShape(18.dp))
                .press(onClick, role = Role.Switch)
                .semantics {
                    contentDescription = label
                    toggleableState = ToggleableState(on)
                },
            contentAlignment = Alignment.Center,
        ) { Icon(icon, contentDescription = null, tint = if (on) c.night else c.nightInk, modifier = Modifier.size(22.dp)) }
        Text(label, style = TextStyle(fontSize = 12.sp), color = c.nightMuted)
    }
}

private fun heardText(type: RequestType?): Int = when (type) {
    RequestType.OtpShare -> R.string.sb_heard_otp
    RequestType.PinReceive -> R.string.sb_heard_pin
    RequestType.RemoteAccess -> R.string.sb_heard_remote
    else -> R.string.sb_heard_qr
}

// ---------- The alert ----------

private data class AlertCopy(val word: Int, val premiumWord: Int, val line: Int, val question: Int, val yes: Int, val no: Int, val glyph: AskGlyph)

private fun copyFor(type: RequestType): AlertCopy = when (type) {
    RequestType.QrReceive -> AlertCopy(R.string.sb_word_qr, R.string.sb_pword_qr, R.string.sb_line_qr, R.string.sb_q_qr, R.string.sb_yes_qr, R.string.sb_no_qr, AskGlyph.Qr)
    RequestType.PinReceive -> AlertCopy(R.string.sb_word_pin, R.string.sb_pword_pin, R.string.sb_line_pin, R.string.sb_q_pin, R.string.sb_yes_qr, R.string.sb_no_qr, AskGlyph.Pin)
    RequestType.OtpShare -> AlertCopy(R.string.sb_word_otp, R.string.sb_pword_otp, R.string.sb_line_otp, R.string.sb_q_otp, R.string.sb_yes_otp, R.string.sb_no_otp, AskGlyph.Code)
    RequestType.RemoteAccess -> AlertCopy(R.string.sb_word_remote, R.string.sb_pword_remote, R.string.sb_line_remote, R.string.sb_q_remote, R.string.sb_yes_remote, R.string.sb_no_remote, AskGlyph.Install)
}

/** One alert's colours, every one from the app's palette: red for High risk, amber for Possible. */
private data class AlertSkin(
    val bg: Color,
    val glow: Color,
    val fg: Color,
    val muted: Color,
    val pill: Pair<Color, Color>,
    val word: Color,
    val badge: Pair<Color, Color>,
    val chip: Pair<Color, Color>,
    val line: Color?,
    val eyebrow: Color,
    val card: Color,
    val cardLine: Color,
    val answer: Pair<Color, Color>,
    val end: Pair<Color, Color>,
    val holdBorder: Color,
    val holdContent: Color,
    val keep: Color,
    val entrance: AlertEntrance,
)

/** Runs go day, night (the call screens' palette), day, each with its own entrance. */
fun alertOnNight(run: Int): Boolean = (run - 1).mod(3) == 1

@Composable
private fun alertSkin(run: Int, level: RiskLevel): AlertSkin {
    val c = Spell.colors
    val high = level == RiskLevel.High
    val entrance = when ((run - 1).mod(3)) {
        0 -> AlertEntrance.ZoomIn
        1 -> AlertEntrance.Jiggle
        else -> AlertEntrance.Slam
    }
    return if (alertOnNight(run)) {
        val accent = if (high) c.hangUp else c.warn
        AlertSkin(
            bg = c.night, glow = if (high) accent.copy(alpha = 0.16f) else c.warnGlow,
            fg = c.nightInk, muted = c.nightMuted,
            pill = if (high) c.hangUp to c.night else c.warn to c.onWarn,
            word = accent, badge = c.nightCard to accent, chip = c.nightCard to c.nightInk, line = c.nightLine,
            eyebrow = c.nightMuted, card = c.nightCard, cardLine = c.nightLine,
            answer = c.earOff to c.nightInk, end = c.hangUp to c.night,
            holdBorder = c.nightMuted, holdContent = c.nightInk, keep = c.nightMuted,
            entrance = entrance,
        )
    } else {
        val badge = if (high) c.badgeQr else c.badgeOtp
        // Premium's day surface is dark, where its deep red word would not read.
        val word = if (high && c.bg.luminance() > 0.5f) c.end else badge.second
        AlertSkin(
            bg = c.bg, glow = if (high) c.end.copy(alpha = 0.16f) else c.warnGlow,
            fg = c.ink, muted = c.faint,
            pill = if (high) c.end to c.onEnd else c.warn to c.onWarn,
            word = word, badge = badge, chip = badge, line = null,
            eyebrow = c.eyebrow, card = c.card, cardLine = c.line,
            answer = c.accentC to c.onAccentC, end = c.end to c.onEnd,
            holdBorder = c.accent, holdContent = c.accent, keep = c.muted,
            entrance = entrance,
        )
    }
}

/**
 * The full-screen alert, in the app's own look. It wears a different face each run (day,
 * night, day, each arriving differently) so it never turns into wallpaper. Same words, same
 * order, same buttons every time; "What they said" shows the signals the server named.
 */
@Composable
fun SpellAlertScreen(
    alert: ActiveAlert,
    run: Int,
    askedAgoSeconds: Long,
    onEndCall: () -> Unit,
    onHold: () -> Unit,
    onKeepTalking: () -> Unit,
) {
    val edition = Spell.edition
    val skin = alertSkin(run, alert.level)
    val copy = copyFor(alert.type)
    var answer by rememberSaveable(alert.id) { mutableStateOf<Boolean?>(null) }
    val reduce = LocalReduceMotion.current
    val entrance = remember(alert.id) { Animatable(if (reduce) 1f else 0f) }
    LaunchedEffect(alert.id) {
        if (!reduce) {
            when (skin.entrance) {
                AlertEntrance.ZoomIn -> entrance.animateTo(1f, tween(550, easing = CubicBezierEasing(0.2f, 1.3f, 0.4f, 1f)))
                AlertEntrance.Jiggle -> entrance.animateTo(1f, tween(700, easing = LinearEasing))
                AlertEntrance.Slam -> entrance.animateTo(1f, tween(600, easing = CubicBezierEasing(0.2f, 1.25f, 0.4f, 1f)))
            }
        }
    }
    BackHandler { /* the alert stays until the user chooses */ }

    val title = stringResource(if (edition == Edition.Premium) copy.premiumWord else copy.word)
    val shadow = Spell.colors.shadow
    Box(
        Modifier
            .fillMaxSize()
            .graphicsLayer { applyEntrance(skin.entrance, entrance.value) }
            .clip(if (skin.entrance == AlertEntrance.ZoomIn) RoundedCornerShape(((1f - entrance.value.coerceIn(0f, 1f)) * 200f).dp) else RectangleShape)
            .background(skin.bg)
            .semantics { paneTitle = title },
    ) {
        GlowBackground(skin.glow, Modifier.matchParentSize())
        PinnedColumn(
            PaddingValues(start = 22.dp, end = 22.dp, top = 54.dp, bottom = 24.dp),
            spacing = 14.dp,
            top = {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Text(
                    stringResource(if (alert.level == RiskLevel.High) R.string.level_high else R.string.level_possible).uppercase(),
                    style = Spell.type.eyebrow,
                    color = skin.pill.second,
                    modifier = Modifier.clip(RoundedCornerShape(999.dp)).background(skin.pill.first).padding(horizontal = 12.dp, vertical = 6.dp),
                )
                if (askedAgoSeconds > 0) {
                    Text(
                        stringResource(R.string.sb_asked_ago, askedAgoSeconds.toInt()),
                        style = TextStyle(fontSize = 12.sp, fontWeight = FontWeight.SemiBold),
                        color = skin.muted,
                    )
                }
            }
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(14.dp)) {
                FlexWord(title, skin.word, Modifier.weight(1f).semantics {
                    heading()
                    liveRegion = LiveRegionMode.Assertive
                })
                val tile = RoundedCornerShape(26.dp)
                Box(
                    Modifier.size(84.dp).clip(tile).background(skin.badge.first)
                        .then(if (skin.line != null) Modifier.border(1.dp, skin.line, tile) else Modifier),
                    contentAlignment = Alignment.Center,
                ) { CrossedGlyph(copy.glyph, skin.badge.second, Modifier.size(56.dp)) }
            }
            Text(stringResource(copy.line), style = TextStyle(fontSize = 19.sp, lineHeight = 25.5.sp, fontWeight = FontWeight.Bold), color = skin.fg)
            if (alert.signals.isNotEmpty()) SignalChips(alert.signals, label = skin.eyebrow, chip = skin.chip, line = skin.line)
            val card = RoundedCornerShape(22.dp)
            Column(
                Modifier.fillMaxWidth().clip(card).background(skin.card).border(1.dp, skin.cardLine, card).padding(16.dp),
                verticalArrangement = Arrangement.spacedBy(10.dp),
            ) {
                val chosen = answer
                if (chosen == null) {
                    Text(stringResource(copy.question), style = TextStyle(fontSize = 17.sp, lineHeight = 23.sp, fontWeight = FontWeight.Bold), color = skin.fg)
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        SpellButton(stringResource(R.string.sb_yes), { answer = true }, Modifier.weight(1f), background = skin.answer.first, content = skin.answer.second, height = 48.dp, radius = 16.dp, fontSize = 15.sp)
                        SpellButton(stringResource(R.string.sb_no), { answer = false }, Modifier.weight(1f), background = skin.answer.first, content = skin.answer.second, height = 48.dp, radius = 16.dp, fontSize = 15.sp)
                    }
                } else {
                    Text(
                        stringResource(if (chosen) copy.yes else copy.no),
                        style = TextStyle(fontSize = 17.sp, lineHeight = 24.sp, fontWeight = FontWeight.Bold),
                        color = skin.fg,
                        modifier = Modifier.semantics { liveRegion = LiveRegionMode.Polite },
                    )
                }
            }
            },
            bottom = {
            SpellButton(
                stringResource(R.string.end_call), onEndCall,
                Modifier.fillMaxWidth().drawBehind {
                    drawRoundRect(shadow, topLeft = Offset(0f, 10.dp.toPx()), size = size, cornerRadius = CornerRadius(28.dp.toPx()))
                },
                background = skin.end.first, content = skin.end.second, height = 74.dp, radius = 28.dp, fontSize = 22.sp, weight = FontWeight.Black,
            )
            SpellButton(
                stringResource(R.string.sb_hold_caller), onHold, Modifier.fillMaxWidth(),
                background = Color.Transparent, content = skin.holdContent, border = skin.holdBorder, height = 54.dp, radius = 20.dp, fontSize = 16.sp,
            )
            KeepTalkingButton(skin.keep, onKeepTalking)
            },
        )
    }
}

private fun androidx.compose.ui.graphics.GraphicsLayerScope.applyEntrance(entrance: AlertEntrance, p: Float) {
    when (entrance) {
        AlertEntrance.ZoomIn -> {
            val s = 0.55f + 0.45f * p
            scaleX = s
            scaleY = s
            alpha = p.coerceIn(0f, 1f)
        }
        AlertEntrance.Jiggle -> {
            // 0%: small and clear; 25% -3deg; 45% +3; 65% -2; 85% +1; 100% still
            alpha = (p / 0.25f).coerceIn(0f, 1f)
            val s = if (p < 0.25f) 0.9f + 0.12f * (p / 0.25f) else 1.02f - 0.02f * ((p - 0.25f) / 0.75f)
            scaleX = s
            scaleY = s
            rotationZ = when {
                p < 0.25f -> -3f * (p / 0.25f)
                p < 0.45f -> -3f + 6f * ((p - 0.25f) / 0.2f)
                p < 0.65f -> 3f - 5f * ((p - 0.45f) / 0.2f)
                p < 0.85f -> -2f + 3f * ((p - 0.65f) / 0.2f)
                else -> 1f - (p - 0.85f) / 0.15f
            }
        }
        AlertEntrance.Slam -> translationY = -size.height * (1f - p)
    }
    transformOrigin = TransformOrigin.Center
}

/** The big word arrives narrow and light and stretches out heavy (letter spacing tightens as it lands). */
@Composable
private fun FlexWord(text: String, color: Color, modifier: Modifier = Modifier) {
    val reduce = LocalReduceMotion.current
    val p = remember { Animatable(if (reduce) 1f else 0f) }
    LaunchedEffect(Unit) {
        if (!reduce) {
            delay(150)
            p.animateTo(1f, tween(1100, easing = Motion.EaseOut))
        }
    }
    val base = Spell.type.alertWord
    Text(
        text,
        style = base.copy(letterSpacing = (0.08f - 0.09f * p.value).em),
        color = color,
        modifier = modifier.graphicsLayer {
            alpha = 0.4f + 0.6f * p.value
            scaleX = 0.88f + 0.12f * p.value
            transformOrigin = TransformOrigin(0f, 0.5f)
        },
    )
}

private const val KEEP_TALKING_MS = 1_250

/** Keeping the call going needs a deliberate press and hold; a quick tap does nothing. */
@Composable
private fun KeepTalkingButton(color: Color, onConfirmed: () -> Unit) {
    val progress = remember { Animatable(0f) }
    val scope = rememberCoroutineScope()
    val haptics = LocalHapticFeedback.current
    var holding by remember { mutableStateOf(false) }
    val label = stringResource(R.string.sb_keep_talking_a11y)
    Box(
        contentAlignment = Alignment.Center,
        modifier = Modifier
            .fillMaxWidth()
            .heightIn(min = 48.dp)
            .clip(RoundedCornerShape(14.dp))
            .semantics {
                role = Role.Button
                contentDescription = label
                onLongClick(label = label) { onConfirmed(); true }
            }
            .pointerInput(Unit) {
                detectTapGestures(onPress = {
                    holding = true
                    haptics.performHapticFeedback(HapticFeedbackType.TextHandleMove)
                    val job = scope.launch {
                        val remaining = ((1f - progress.value) * KEEP_TALKING_MS).toInt()
                        progress.animateTo(1f, tween(remaining, easing = LinearEasing))
                        haptics.performHapticFeedback(HapticFeedbackType.LongPress)
                        holding = false
                        onConfirmed()
                    }
                    tryAwaitRelease()
                    holding = false
                    if (progress.value < 1f) {
                        job.cancel()
                        scope.launch { progress.animateTo(0f, tween(250)) }
                    }
                })
            },
    ) {
        Box(
            Modifier
                .matchParentSize()
                .graphicsLayer {
                    scaleX = progress.value
                    transformOrigin = TransformOrigin(0f, 0.5f)
                }
                .background(color.copy(alpha = 0.2f))
        )
        Text(
            stringResource(if (holding) R.string.sb_keep_holding else R.string.sb_keep_talking),
            style = TextStyle(fontSize = 14.sp, fontWeight = FontWeight.SemiBold),
            color = color.copy(alpha = 0.85f),
        )
    }
}

// ---------- On hold ----------

/** The caller is on hold: a 30-second ring drains while the user takes a breath. */
@Composable
fun PauseScreen(heldAtMs: Long, type: RequestType?, onEndCall: () -> Unit, onResume: () -> Unit) {
    val c = Spell.colors
    val brush = guardianBrush()
    val elapsed = rememberElapsed(heldAtMs)
    val left = (30 - elapsed).coerceAtLeast(0)
    val reduce = LocalReduceMotion.current
    val drain = remember { Animatable(0f) }
    LaunchedEffect(heldAtMs) {
        if (!reduce) drain.animateTo(1f, tween(30_000, easing = LinearEasing)) else drain.snapTo(1f)
    }
    BackHandler(onBack = onResume)
    Box(Modifier.fillMaxSize().background(c.bg)) {
        GlowBackground(c.glow, Modifier.fillMaxSize())
        PinnedColumn(
            PaddingValues(start = 22.dp, end = 22.dp, top = 64.dp, bottom = 26.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            spacing = 16.dp,
            top = {
            Box(Modifier.size(240.dp), contentAlignment = Alignment.Center) {
                Canvas(Modifier.fillMaxSize().clearAndSetSemantics { }) {
                    val w = 8.dp.toPx()
                    val inset = 10.dp.toPx() + w / 2
                    val arcSize = Size(size.width - 2 * inset, size.height - 2 * inset)
                    drawCircle(c.surface2, radius = arcSize.width / 2, style = Stroke(w))
                    drawArc(c.accent, -90f, 360f * (1f - drain.value), false, Offset(inset, inset), arcSize, style = Stroke(w, cap = StrokeCap.Round))
                }
                GuardianBlob(Blob.Cookie, Modifier.size(150.dp), radius = 70f, fill = brush)
                Display(left.toString(), 40f, color = c.onGuardian, lineHeight = 1f)
            }
            Display(stringResource(R.string.sb_on_hold), 34f, lineHeight = 1.05f, align = TextAlign.Center)
            Body(stringResource(R.string.sb_on_hold_body), 16.sp, lineHeight = 1.5f, align = TextAlign.Center, modifier = Modifier.widthIn(max = 300.dp))
            Text(
                stringResource(truthText(type)),
                style = TextStyle(fontSize = 16.sp, lineHeight = 23.sp, fontWeight = FontWeight.Bold),
                color = c.onAccentC,
                textAlign = TextAlign.Center,
                modifier = Modifier.clip(RoundedCornerShape(22.dp)).background(c.accentC).border(1.dp, c.line, RoundedCornerShape(22.dp)).padding(horizontal = 16.dp, vertical = 14.dp),
            )
            },
            bottom = {
            SpellButton(stringResource(R.string.end_call), onEndCall, Modifier.fillMaxWidth(), background = c.end, content = c.onEnd, height = 72.dp, radius = 28.dp, fontSize = 21.sp, weight = FontWeight.Black)
            SpellButton(stringResource(R.string.sb_back_to_call), onResume, Modifier.fillMaxWidth(), background = Color.Transparent, content = c.accent, border = c.accent, height = 54.dp, radius = 20.dp, fontSize = 16.sp)
            },
        )
    }
}

// ---------- After the call ----------

/** After the call: what happened, told plainly, and help if it's needed. */
@Composable
fun StoryScreen(
    reason: EndReason?,
    timeline: List<TimelineEntry>,
    callSeconds: Long,
    scamOn: Boolean,
    onOpenRecovery: () -> Unit,
    onBack: () -> Unit,
) {
    val c = Spell.colors
    val brush = guardianBrush()
    BackHandler(onBack = onBack)
    val declined = reason == EndReason.Declined || (timeline.isEmpty() && callSeconds == 0L)
    val outcome = if (declined) null else CallHistory.outcome(timeline, scamOn)
    val warnAt = CallHistory.firstWarning(timeline)?.atSeconds ?: 0
    val after = (callSeconds - warnAt).coerceAtLeast(1).toInt()
    val title = when (outcome) {
        null -> stringResource(R.string.ended_declined)
        CallOutcome.Stopped -> plural(R.plurals.sb_story_stopped, after, after)
        CallOutcome.Kept -> stringResource(R.string.sb_story_kept)
        CallOutcome.CallerLeft -> stringResource(R.string.sb_story_caller)
        CallOutcome.Calm -> stringResource(R.string.sb_story_calm)
        CallOutcome.Off -> stringResource(R.string.sb_story_off)
    }
    val body = when (outcome) {
        null -> stringResource(R.string.sb_story_declined_body)
        CallOutcome.Stopped -> stringResource(R.string.sb_story_stopped_body)
        CallOutcome.Kept -> stringResource(R.string.sb_story_kept_body)
        CallOutcome.CallerLeft -> stringResource(R.string.sb_story_caller_body)
        CallOutcome.Calm -> stringResource(R.string.sb_story_calm_body)
        CallOutcome.Off -> stringResource(R.string.sb_story_off_body)
    }
    val warned = outcome == CallOutcome.Stopped || outcome == CallOutcome.Kept || outcome == CallOutcome.CallerLeft
    Box(Modifier.fillMaxSize().background(c.bg)) {
        GlowBackground(c.glow, Modifier.fillMaxSize())
        PinnedColumn(
            PaddingValues(start = 22.dp, end = 22.dp, top = 72.dp, bottom = 28.dp),
            spacing = 16.dp,
            top = {
            GuardianBlob(if (outcome == CallOutcome.Stopped) Blob.Burst else Blob.Cookie, Modifier.size(88.dp), radius = 74f, fill = brush)
            Eyebrow(stringResource(R.string.sb_after_call))
            Display(title, 36f, lineHeight = 1.04f, modifier = Modifier.semantics { heading() })
            Body(body, 16.sp, lineHeight = 1.5f)
            if (warned) {
                SpellRow(
                    title = stringResource(R.string.sb_help_title),
                    subtitle = stringResource(R.string.sb_help_sub_story),
                    background = c.tert,
                    contentColor = c.onTert,
                    subtitleColor = c.onTert.copy(alpha = 0.85f),
                    outlined = false,
                    onClick = onOpenRecovery,
                    trailing = { Icon(Icons.Outlined.ChevronRight, contentDescription = null, tint = c.onTert, modifier = Modifier.size(22.dp)) },
                )
            }
            },
            bottom = {
            Text(stringResource(R.string.sb_nothing_recorded), style = TextStyle(fontSize = 13.sp), color = c.faint, textAlign = TextAlign.Center, modifier = Modifier.fillMaxWidth())
            SpellButton(stringResource(R.string.sb_back_home), onBack, Modifier.fillMaxWidth(), height = 66.dp, radius = 28.dp)
            },
        )
    }
}

// ---------- Practice ----------

/** "Feel a warning": the buzz, the chime and the voice, once, so the user knows it when it's real. */
@Composable
fun PracticeScreen(language: AppLanguage, onFeel: () -> Unit, onDone: () -> Unit) {
    val c = Spell.colors
    var replays by remember { mutableStateOf(0) }
    LaunchedEffect(replays) { onFeel() }
    BackHandler(onBack = onDone)
    Column(
        Modifier.fillMaxSize().background(c.night).safeDrawingPadding().padding(start = 22.dp, end = 22.dp, top = 50.dp, bottom = 28.dp),
        verticalArrangement = Arrangement.spacedBy(18.dp),
    ) {
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
            Text(stringResource(R.string.sb_practice).uppercase(), style = TextStyle(fontSize = 12.sp, fontWeight = FontWeight.Bold, letterSpacing = 0.18.em), color = c.nightMuted)
            Box(
                Modifier.size(44.dp).clip(RoundedCornerShape(14.dp)).background(c.nightCard).press(onDone, label = stringResource(R.string.sb_close)),
                contentAlignment = Alignment.Center,
            ) { Icon(Icons.Outlined.Close, contentDescription = stringResource(R.string.sb_close), tint = c.nightInk, modifier = Modifier.size(20.dp)) }
        }
        Box(Modifier.weight(1f).fillMaxWidth(), contentAlignment = Alignment.Center) {
            EarGlow(c.warnGlow, 340.dp)
            Column(horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(20.dp)) {
                GuardianBlob(Blob.Burst, Modifier.size(176.dp), radius = 74f, color = c.warn, spin = Spin.Fast)
                Display(stringResource(R.string.sb_practice_title), 30f, color = c.nightInk, lineHeight = 1.1f, align = TextAlign.Center)
                HapBars(Modifier.width(180.dp))
                Body(stringResource(R.string.sb_practice_body, langName(language)), 15.sp, color = c.nightMuted, lineHeight = 1.5f, align = TextAlign.Center, modifier = Modifier.widthIn(max = 300.dp))
                Body("“" + stringResource(R.string.sb_voice_qr) + "”", 16.sp, color = c.warnSoft, align = TextAlign.Center, modifier = Modifier.widthIn(max = 300.dp))
            }
        }
        SpellButton(stringResource(R.string.sb_practice_again), { replays++ }, Modifier.fillMaxWidth(), background = c.warn, content = c.onWarn, height = 64.dp)
        SpellButton(stringResource(R.string.sb_done), onDone, Modifier.fillMaxWidth(), background = Color.Transparent, content = c.nightMuted, height = 48.dp, radius = 18.dp, fontSize = 16.sp, weight = FontWeight.Bold)
    }
}
