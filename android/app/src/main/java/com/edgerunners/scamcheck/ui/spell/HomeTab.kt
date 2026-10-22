package com.edgerunners.scamcheck.ui.spell

import androidx.annotation.PluralsRes
import androidx.compose.animation.core.Animatable
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.spring
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.ExperimentalFoundationApi
import androidx.compose.foundation.combinedClickable
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.interaction.collectIsPressedAsState
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.selection.selectable
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.outlined.ArrowForward
import androidx.compose.material.icons.outlined.ChevronRight
import androidx.compose.material.icons.outlined.Support
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.PathEffect
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.drawscope.rotate
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.platform.LocalConfiguration
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.clearAndSetSemantics
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.stateDescription
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.edgerunners.scamcheck.R
import com.edgerunners.scamcheck.alert.CallHistory
import com.edgerunners.scamcheck.alert.CallOutcome
import com.edgerunners.scamcheck.alert.CallRecord
import com.edgerunners.scamcheck.alert.DayTally
import com.edgerunners.scamcheck.model.RequestType
import com.edgerunners.scamcheck.ui.theme.LocalReduceMotion
import com.edgerunners.scamcheck.ui.theme.Spell
import kotlinx.coroutines.delay
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import kotlin.math.PI
import kotlin.math.cos
import kotlin.math.min
import kotlin.math.sin

/** Plural text in the app's chosen language. */
@Composable
fun plural(@PluralsRes id: Int, count: Int, vararg args: Any): String =
    LocalContext.current.resources.getQuantityString(id, count, *args)

@Composable
fun appLocale(): Locale = LocalConfiguration.current.locales[0]

fun clockTime(ms: Long, locale: Locale): String = SimpleDateFormat("HH:mm", locale).format(Date(ms))

/** The home tab: is scam check on, what happened this week, and help if it's too late. */
@Composable
fun HomeTab(
    scamOn: Boolean,
    live: Boolean,
    history: List<CallRecord>,
    nowMs: Long,
    selectedDay: Int,
    onSelectDay: (Int) -> Unit,
    onToggleScam: (Boolean) -> Unit,
    onLongPressGuardian: (() -> Unit)?,
    onOpenRecents: () -> Unit,
    onOpenRecovery: () -> Unit,
) {
    val c = Spell.colors
    val locale = appLocale()
    val week = remember(history, nowMs / 60_000) { CallHistory.week(history, nowMs) }
    val stopped = remember(history, nowMs / 60_000) { CallHistory.stoppedThisWeek(history, nowMs) }
    val checked = week.sumOf { it.calls }
    val warnings = week.sumOf { it.warnings }
    val fastest = stopped.minOfOrNull { it.secondsToEnd }
    val slowest = stopped.maxOfOrNull { it.secondsToEnd }

    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
        val chip = when {
            !scamOn -> R.string.sb_chip_off
            !live -> R.string.sb_chip_offline
            else -> R.string.sb_chip_on
        }
        ScamCheckChip(stringResource(chip), on = scamOn, live = live, onToggle = onToggleScam)
        Display(
            stringResource(
                when {
                    !scamOn -> R.string.sb_home_title_off
                    !live -> R.string.sb_home_title_offline
                    else -> R.string.sb_home_title_on
                }
            ),
            42f,
            lineHeight = 0.98f,
            modifier = Modifier.widthIn(max = 300.dp),
        )

        WeekDial(
            scamOn = scamOn,
            week = week,
            selected = selectedDay,
            onSelect = onSelectDay,
            onToggle = { onToggleScam(!scamOn) },
            onLongPress = onLongPressGuardian,
            modifier = Modifier.align(Alignment.CenterHorizontally).padding(top = 2.dp),
        )

        // Scams stopped this week
        Row(verticalAlignment = Alignment.Bottom, horizontalArrangement = Arrangement.spacedBy(14.dp), modifier = Modifier.padding(top = 4.dp)) {
            Display(stopped.size.toString(), 80f, lineHeight = 0.78f)
            Column(verticalArrangement = Arrangement.spacedBy(3.dp), modifier = Modifier.padding(bottom = 2.dp)) {
                Text(
                    plural(R.plurals.sb_scams_stopped, stopped.size),
                    style = TextStyle(fontSize = 18.sp, fontWeight = FontWeight.ExtraBold),
                    color = c.head,
                )
                Body(
                    if (slowest != null) plural(R.plurals.sb_stopped_sub, slowest.toInt(), slowest.toInt()) else stringResource(R.string.sb_stopped_none),
                    13.sp,
                    color = c.faint,
                    lineHeight = 1.35f,
                )
            }
        }

        DayStory(week.getOrNull(selectedDay) ?: week.last(), isToday = selectedDay == week.lastIndex, locale = locale)

        // This week as a ticker
        Column(Modifier.padding(top = 4.dp)) {
            Hairline()
            Row(Modifier.padding(top = 14.dp), verticalAlignment = Alignment.CenterVertically) {
                Ticker(checked.toString(), stringResource(R.string.sb_stat_checked), first = true)
                Ticker(warnings.toString(), plural(R.plurals.sb_stat_warnings, warnings))
                Ticker(if (fastest != null) stringResource(R.string.sb_seconds_short, fastest.toInt()) else "–", stringResource(R.string.sb_stat_fastest))
                Box(Modifier.weight(1f))
                Box(
                    Modifier
                        .size(48.dp)
                        .clip(CircleShape)
                        .background(c.accentC)
                        .border(1.dp, c.line, CircleShape)
                        .press(onOpenRecents, label = stringResource(R.string.sb_open_recents)),
                    contentAlignment = Alignment.Center,
                ) {
                    Icon(Icons.AutoMirrored.Outlined.ArrowForward, contentDescription = stringResource(R.string.sb_open_recents), tint = c.onAccentC, modifier = Modifier.size(20.dp))
                }
            }
        }

        HelpPill(stringResource(R.string.sb_help_title), stringResource(R.string.sb_help_sub), onOpenRecovery, Modifier.padding(top = 8.dp))
    }
}

@Composable
private fun Ticker(value: String, label: String, first: Boolean = false) {
    val c = Spell.colors
    Row(verticalAlignment = Alignment.CenterVertically) {
        if (!first) VHairline(height = 44.dp)
        Column(
            Modifier.padding(start = if (first) 0.dp else 14.dp, end = 14.dp).described("$value $label"),
            verticalArrangement = Arrangement.spacedBy(5.dp),
        ) {
            Display(value, 28f, lineHeight = 1f)
            Text(label, style = TextStyle(fontSize = 12.sp), color = c.faint)
        }
    }
}

/** "Already paid or shared a code?": findable, but quiet. */
@Composable
fun HelpPill(title: String, subtitle: String, onClick: () -> Unit, modifier: Modifier = Modifier) {
    val c = Spell.colors
    Row(
        modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(999.dp))
            .background(c.tert)
            .press(onClick)
            .padding(start = 8.dp, top = 8.dp, bottom = 8.dp, end = 16.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Box(Modifier.size(40.dp).clip(CircleShape).background(c.shade), contentAlignment = Alignment.Center) {
            Icon(Icons.Outlined.Support, contentDescription = null, tint = c.onTert, modifier = Modifier.size(22.dp))
        }
        Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(1.dp)) {
            Text(title, style = TextStyle(fontSize = 15.sp, fontWeight = FontWeight.ExtraBold), color = c.onTert)
            Text(subtitle, style = TextStyle(fontSize = 12.sp), color = c.onTert.copy(alpha = 0.85f))
        }
        Icon(Icons.Outlined.ChevronRight, contentDescription = null, tint = c.onTert, modifier = Modifier.size(18.dp))
    }
}

// ---------- The week dial ----------

private const val DIAL_W = 320
private const val DIAL_H = 300
private const val DIAL_R = 128f
private fun angleOf(i: Int): Float = 165f - i * 25f

/**
 * The week dial: the guardian at the centre (tap to turn scam check on or off), the last seven
 * days on an arc below it, and a hand that points at the day you pick.
 */
@Composable
private fun WeekDial(
    scamOn: Boolean,
    week: List<DayTally>,
    selected: Int,
    onSelect: (Int) -> Unit,
    onToggle: () -> Unit,
    onLongPress: (() -> Unit)?,
    modifier: Modifier = Modifier,
) {
    val c = Spell.colors
    val locale = appLocale()
    val reduce = LocalReduceMotion.current
    val hand by animateFloatAsState(angleOf(selected), if (reduce) tween(0) else spring(dampingRatio = 0.55f, stiffness = 160f), label = "hand")

    Box(modifier.size(DIAL_W.dp, DIAL_H.dp)) {
        Canvas(Modifier.fillMaxSize().clearAndSetSemantics { }) {
            val u = size.width / DIAL_W
            val arc = Path()
            var a = 165f
            var firstPoint = true
            while (a >= 15f) {
                val rad = a * PI.toFloat() / 180f
                val x = (160f + DIAL_R * cos(rad)) * u
                val y = (130f + DIAL_R * sin(rad)) * u
                if (firstPoint) arc.moveTo(x, y) else arc.lineTo(x, y)
                firstPoint = false
                a -= 3f
            }
            drawPath(
                arc,
                c.ringc,
                style = Stroke(2f * u, cap = StrokeCap.Round, pathEffect = PathEffect.dashPathEffect(floatArrayOf(0.01f, 8f * u))),
            )
            rotate(hand, Offset(160f * u, 130f * u)) {
                drawLine(c.accent, Offset(236f * u, 130f * u), Offset(262f * u, 130f * u), 2.5f * u, StrokeCap.Round)
                drawCircle(c.accent, 3.5f * u, Offset(236f * u, 130f * u))
            }
        }

        GuardianButton(
            scamOn = scamOn,
            onToggle = onToggle,
            onLongPress = onLongPress,
            modifier = Modifier.offset(60.dp, 30.dp).size(200.dp),
        )

        val dayName = remember(locale) { SimpleDateFormat("EEEE", locale) }
        val dayLetter = remember(locale) { SimpleDateFormat("EEEEE", locale) }
        val today = stringResource(R.string.sb_today)
        week.forEachIndexed { i, day ->
            val isToday = i == week.lastIndex
            val picked = i == selected
            val warn = day.warnings > 0
            val blob = if (warn) 40 else min(36, 16 + day.calls * 4)
            val rad = angleOf(i) * PI.toFloat() / 180f
            val x = 160f + DIAL_R * cos(rad)
            val y = 130f + DIAL_R * sin(rad)
            val name = if (isToday) today else dayName.format(Date(day.startMs))
            val a11y = name + ", " + plural(R.plurals.sb_calls_checked, day.calls, day.calls) +
                if (warn) ", " + plural(R.plurals.sb_warnings_count, day.warnings, day.warnings) else ""
            Column(
                Modifier
                    .offset((x - 28f).dp, (y - blob / 2f).dp)
                    .width(56.dp)
                    .selectable(selected = picked, role = Role.RadioButton, onClick = { onSelect(i) })
                    .semantics(mergeDescendants = true) { contentDescription = a11y },
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.spacedBy(4.dp),
            ) {
                GuardianBlob(
                    if (warn) Blob.Burst else Blob.Cookie,
                    Modifier.size(blob.dp),
                    radius = 80f,
                    color = when {
                        warn -> c.end
                        isToday -> c.accent
                        else -> c.accentC
                    },
                    stroke = if (warn) null else c.ringc,
                    strokeUnits = 7f,
                    spin = if (isToday) Spin.Fast else Spin.Normal,
                )
                Text(
                    if (isToday) today else dayLetter.format(Date(day.startMs)),
                    style = TextStyle(fontSize = 12.sp, fontWeight = if (picked) FontWeight.ExtraBold else FontWeight.SemiBold),
                    color = if (picked) c.accent else c.faint,
                )
            }
        }
    }
}

/**
 * The guardian itself. Tap: scam check on or off, with a jelly wobble and a ripple.
 * Long-press: demo calls (a presenter's shortcut).
 */
@OptIn(ExperimentalFoundationApi::class)
@Composable
private fun GuardianButton(scamOn: Boolean, onToggle: () -> Unit, onLongPress: (() -> Unit)?, modifier: Modifier = Modifier) {
    val c = Spell.colors
    val reduce = LocalReduceMotion.current
    val brush = guardianBrush()
    var wobble by remember { mutableStateOf(false) }
    var pulses by remember { mutableIntStateOf(0) }
    val ripple = remember { Animatable(1f) }
    val slash = remember { Animatable(if (scamOn) 0f else 1f) }
    val pressed = remember { Animatable(1f) }
    LaunchedEffect(pulses) {
        if (pulses == 0 || reduce) return@LaunchedEffect
        wobble = true
        ripple.snapTo(0f)
        delay(260)
        wobble = false
    }
    LaunchedEffect(pulses) {
        if (pulses > 0 && !reduce) ripple.animateTo(1f, tween(1100))
    }
    LaunchedEffect(scamOn) {
        if (reduce) slash.snapTo(if (scamOn) 0f else 1f)
        else if (scamOn) slash.snapTo(0f) else { delay(150); slash.animateTo(1f, tween(400)) }
    }
    val label = stringResource(if (scamOn) R.string.sb_guard_on_a11y else R.string.sb_guard_off_a11y)
    val state = stringResource(if (scamOn) R.string.sb_chip_on else R.string.sb_chip_off)
    val demoLabel = stringResource(R.string.sb_demo_calls)
    val toggle = {
        pulses++
        onToggle()
    }
    // A drag across the guardian (scrolling Home) must never flip scam check, so this uses
    // combinedClickable, which cancels once the finger moves, rather than a raw tap detector.
    val interaction = remember { MutableInteractionSource() }
    val isPressed by interaction.collectIsPressedAsState()
    LaunchedEffect(isPressed) {
        if (reduce) return@LaunchedEffect
        if (isPressed) pressed.animateTo(0.93f, tween(120)) else pressed.animateTo(1f, spring(dampingRatio = 0.35f, stiffness = 400f))
    }
    Box(
        modifier
            .graphicsLayer {
                scaleX = pressed.value
                scaleY = pressed.value
            }
            .combinedClickable(
                interactionSource = interaction,
                indication = null,
                role = Role.Switch,
                onLongClickLabel = if (onLongPress != null) demoLabel else null,
                onLongClick = onLongPress,
                onClick = toggle,
            )
            .semantics {
                contentDescription = label
                stateDescription = state
            },
    ) {
        // Ripples out from the shape when toggled
        Canvas(Modifier.fillMaxSize().clearAndSetSemantics { }) {
            val u = size.width / 200f
            val color = if (scamOn) c.accent else c.off
            listOf(0f, 0.13f).forEach { delayShare ->
                val p = ((ripple.value - delayShare) / (1f - delayShare)).coerceIn(0f, 1f)
                if (p in 0.001f..0.999f) {
                    drawCircle(color.copy(alpha = 0.6f * (1f - p)), radius = 62f * u * (1f + 0.62f * p), style = Stroke(3f * u))
                }
            }
        }
        GuardianBlob(Blob.Cookie, Modifier.fillMaxSize(), radius = 84f, stroke = c.ringc, strokeUnits = 1.2f, spin = Spin.SlowReverse)
        GuardianBlob(Blob.Cookie, Modifier.fillMaxSize(), radius = 74f, stroke = c.ringc, strokeUnits = 1.6f, spin = Spin.Reverse)
        GuardianBlob(
            kind = when {
                wobble -> Blob.Wobble
                scamOn -> Blob.Cookie
                else -> Blob.Soft
            },
            modifier = Modifier.fillMaxSize(),
            radius = 62f,
            fill = if (scamOn) brush else null,
            color = c.off,
            spin = Spin.Normal,
            breathe = scamOn,
            highlight = 0.5f,
        )
        Canvas(Modifier.fillMaxSize().clearAndSetSemantics { }) {
            val u = size.width / 200f
            drawShield(c.onGuardian, u)
            drawSlash(c.onGuardian, u, slash.value)
        }
    }
}

// ---------- The selected day, told as a short story ----------

@Composable
private fun DayStory(day: DayTally, isToday: Boolean, locale: Locale) {
    val c = Spell.colors
    val name = if (isToday) stringResource(R.string.sb_today) else remember(locale, day.startMs) { SimpleDateFormat("EEEE", locale).format(Date(day.startMs)) }
    val ev = day.latestWarning
    Column(Modifier.padding(top = 6.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.Bottom) {
            Eyebrow(name)
            Text(plural(R.plurals.sb_calls_checked, day.calls, day.calls), style = TextStyle(fontSize = 13.sp), color = c.faint)
        }
        Text(
            stringResource(
                when (ev?.type) {
                    null -> R.string.sb_day_calm
                    RequestType.QrReceive -> R.string.sb_day_qr
                    RequestType.PinReceive -> R.string.sb_day_pin
                    RequestType.OtpShare -> R.string.sb_day_otp
                    RequestType.RemoteAccess -> R.string.sb_day_remote
                }
            ),
            style = TextStyle(fontSize = 19.sp, lineHeight = 25.sp, fontWeight = FontWeight.Bold),
            color = c.head,
        )
        if (ev != null) {
            Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                Fuse(fuseFraction(ev))
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                    Text(
                        stringResource(R.string.sb_fuse_left, clockTime(ev.endedAtMs - ev.secondsToEnd * 1000, locale)),
                        style = TextStyle(fontSize = 12.sp, fontWeight = FontWeight.SemiBold),
                        color = c.faint,
                    )
                    Text(fuseRight(ev), style = TextStyle(fontSize = 12.sp, fontWeight = FontWeight.SemiBold), color = c.head)
                }
            }
        } else {
            Row(Modifier.padding(vertical = 8.dp), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                repeat(min(day.calls, 10)) {
                    Box(Modifier.size(12.dp).clip(CircleShape).background(c.accentC).border(1.5.dp, c.ringc, CircleShape))
                }
            }
        }
    }
}

/** 15 s from the ask to the end is the full fuse; kept talking burns it all. */
fun fuseFraction(r: CallRecord): Float = if (r.outcome == CallOutcome.Kept) 1f else (r.secondsToEnd / 15f).coerceIn(0f, 1f)

@Composable
fun fuseRight(r: CallRecord): String = when (r.outcome) {
    CallOutcome.Kept -> stringResource(R.string.sb_fuse_kept)
    CallOutcome.CallerLeft -> stringResource(R.string.sb_fuse_caller_left, r.secondsToEnd.toInt())
    else -> stringResource(R.string.sb_fuse_hung_up, r.secondsToEnd.toInt())
}
