package com.edgerunners.scamcheck.ui.spell

import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.safeDrawingPadding
import androidx.activity.compose.BackHandler
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.animateColorAsState
import androidx.compose.animation.core.animateDpAsState
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.slideInVertically
import androidx.compose.animation.slideOutVertically
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxScope
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.RowScope
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.selection.toggleable
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.CallEnd
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.drawWithContent
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.PathEffect
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.DrawScope
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.clearAndSetSemantics
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.paneTitle
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.TextUnit
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.edgerunners.scamcheck.R
import com.edgerunners.scamcheck.model.ThreatSignal
import com.edgerunners.scamcheck.ui.Motion
import com.edgerunners.scamcheck.ui.calmSpec
import com.edgerunners.scamcheck.ui.giveSpec
import com.edgerunners.scamcheck.ui.pressScale
import com.edgerunners.scamcheck.ui.theme.LocalReduceMotion
import com.edgerunners.scamcheck.ui.theme.Spell
import kotlinx.coroutines.delay
import kotlin.math.PI
import kotlin.math.cos

// ---------- Type helpers ----------

/** A display line (the design's .disp), sized like the design. */
@Composable
fun Display(
    text: String,
    size: Float,
    modifier: Modifier = Modifier,
    color: Color = Spell.colors.head,
    lineHeight: Float = 1.05f,
    align: TextAlign? = null,
) {
    Text(text, style = Spell.type.display(size, lineHeight), color = color, modifier = modifier, textAlign = align)
}

@Composable
fun Eyebrow(text: String, modifier: Modifier = Modifier, color: Color = Spell.colors.eyebrow) {
    Text(text.uppercase(), style = Spell.type.eyebrow, color = color, modifier = modifier)
}

/** Plain body text in the design's sizes. */
@Composable
fun Body(
    text: String,
    size: TextUnit = 15.sp,
    modifier: Modifier = Modifier,
    color: Color = Spell.colors.muted,
    weight: FontWeight = FontWeight.Normal,
    lineHeight: Float = 1.45f,
    align: TextAlign? = null,
) {
    Text(
        text,
        style = TextStyle(fontSize = size, fontWeight = weight, lineHeight = size * lineHeight),
        color = color,
        modifier = modifier,
        textAlign = align,
    )
}

// ---------- Press ----------

/** Tappable with the app's jelly press and no ripple. */
@Composable
fun Modifier.press(onClick: () -> Unit, role: Role = Role.Button, label: String? = null): Modifier {
    val interaction = remember { MutableInteractionSource() }
    return this
        .pressScale(interaction)
        .clickable(interactionSource = interaction, indication = null, role = role, onClickLabel = label, onClick = onClick)
}

// ---------- Buttons ----------

@Composable
fun SpellButton(
    text: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    background: Color = Spell.colors.accent,
    content: Color = Spell.colors.onAccent,
    border: Color? = null,
    height: Dp = 64.dp,
    radius: Dp = 26.dp,
    fontSize: TextUnit = 18.sp,
    weight: FontWeight = FontWeight.ExtraBold,
) {
    val shape = RoundedCornerShape(radius)
    Box(
        contentAlignment = Alignment.Center,
        modifier = modifier
            .heightIn(min = height)
            .clip(shape)
            .background(background)
            .then(if (border != null) Modifier.border(1.5.dp, border, shape) else Modifier)
            .press(onClick)
            .padding(horizontal = 16.dp),
    ) {
        Text(text, style = TextStyle(fontSize = fontSize, fontWeight = weight), color = content, textAlign = TextAlign.Center)
    }
}

// ---------- Switches and chips ----------

/** The design's pill switch; the knob lands with a little give. */
@Composable
fun SpellSwitch(on: Boolean, width: Dp = 56.dp, height: Dp = 32.dp, knob: Dp = 24.dp) {
    val c = Spell.colors
    val inset = (height - knob) / 2
    val x by animateDpAsState(if (on) width - knob - inset else inset, giveSpec(), label = "knob")
    val track by animateColorAsState(if (on) c.accent else c.off, calmSpec(Motion.MEDIUM), label = "track")
    Box(Modifier.size(width, height).clip(RoundedCornerShape(height / 2)).background(track)) {
        Box(Modifier.offset(x = x, y = inset).size(knob).clip(CircleShape).background(if (on) c.knobOn else Color.White))
    }
}

/** A small dot that breathes a ring outwards while scam check is live. */
@Composable
fun LiveDot(active: Boolean, modifier: Modifier = Modifier, color: Color = Spell.colors.eyebrow) {
    val c = Spell.colors
    val seconds = rememberSeconds()
    Canvas(modifier.size(8.dp).clearAndSetSemantics { }) {
        val r = size.minDimension / 2f
        if (active) {
            val q = 0.5f - 0.5f * cos(2f * PI.toFloat() * seconds.value / 2.4f)
            drawCircle(c.glow.copy(alpha = c.glow.alpha * (1f - q)), radius = r + 7.dp.toPx() * q)
        }
        drawCircle(if (active) color else c.off, radius = r)
    }
}

/** "Scam check is on" with a live dot and a mini switch. The whole chip toggles. */
@Composable
fun ScamCheckChip(text: String, on: Boolean, live: Boolean, onToggle: (Boolean) -> Unit, modifier: Modifier = Modifier) {
    val c = Spell.colors
    val shape = RoundedCornerShape(19.dp)
    Row(
        modifier
            .heightIn(min = 38.dp)
            .clip(shape)
            .background(c.card)
            .border(1.dp, c.line, shape)
            .toggleable(value = on, role = Role.Switch, onValueChange = onToggle)
            .padding(start = 12.dp, end = 6.dp, top = 6.dp, bottom = 6.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        LiveDot(active = on && live)
        Text(text, style = TextStyle(fontSize = 13.sp, fontWeight = FontWeight.Bold), color = c.ink)
        SpellSwitch(on, width = 36.dp, height = 22.dp, knob = 16.dp)
    }
}

/** A rounded square holding an icon or a short mark. */
@Composable
fun IconTile(
    background: Color,
    modifier: Modifier = Modifier,
    size: Dp = 44.dp,
    radius: Dp = 14.dp,
    content: @Composable BoxScope.() -> Unit,
) {
    Box(modifier.size(size).clip(RoundedCornerShape(radius)).background(background), contentAlignment = Alignment.Center, content = content)
}

/** The design's .row: a card with an icon, a title, a line under it and anything trailing. */
@Composable
fun SpellRow(
    title: String,
    modifier: Modifier = Modifier,
    subtitle: String? = null,
    background: Color = Spell.colors.card,
    contentColor: Color = Spell.colors.ink,
    subtitleColor: Color = Spell.colors.faint,
    outlined: Boolean = true,
    onClick: (() -> Unit)? = null,
    toggle: Pair<Boolean, (Boolean) -> Unit>? = null,
    leading: (@Composable () -> Unit)? = null,
    trailing: (@Composable RowScope.() -> Unit)? = null,
) {
    val c = Spell.colors
    val shape = RoundedCornerShape(22.dp)
    val action = when {
        toggle != null -> Modifier.toggleable(value = toggle.first, role = Role.Switch, onValueChange = toggle.second)
        onClick != null -> Modifier.press(onClick)
        else -> Modifier
    }
    Row(
        modifier
            .fillMaxWidth()
            .clip(shape)
            .background(background)
            .then(if (outlined) Modifier.border(1.dp, c.line, shape) else Modifier)
            .then(action)
            .padding(horizontal = 16.dp, vertical = 14.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(14.dp),
    ) {
        leading?.invoke()
        Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
            Text(title, style = TextStyle(fontSize = 16.sp, fontWeight = FontWeight.ExtraBold, lineHeight = 21.sp), color = contentColor)
            if (subtitle != null) Body(subtitle, 13.sp, color = subtitleColor, lineHeight = 1.35f)
        }
        trailing?.invoke(this)
    }
}

/** A round person bubble with an initial; dashed when it is an "add" slot. */
@Composable
fun Bubble(
    initial: String,
    size: Dp,
    modifier: Modifier = Modifier,
    background: Color = Spell.colors.accentC,
    content: Color = Spell.colors.onAccentC,
    dashed: Boolean = false,
    ring: Color? = null,
    fontSize: TextUnit = 24.sp,
) {
    val c = Spell.colors
    Box(
        contentAlignment = Alignment.Center,
        modifier = modifier
            .size(size)
            .then(
                if (ring != null) {
                    Modifier.border(2.dp, ring, CircleShape).padding(5.dp)
                } else {
                    Modifier
                }
            )
            .clip(CircleShape)
            .background(if (dashed) c.bg else background)
            .then(if (dashed) Modifier.dashedCircle(c.handle) else Modifier),
    ) {
        Text(
            initial,
            style = Spell.type.display(fontSize.value, 1f),
            color = if (dashed) c.faint else content,
        )
    }
}

private fun Modifier.dashedCircle(color: Color): Modifier = drawWithContent {
    drawContent()
    drawCircle(color, radius = size.minDimension / 2f - 1.dp.toPx(), style = Stroke(1.5.dp.toPx(), pathEffect = PathEffect.dashPathEffect(floatArrayOf(5.dp.toPx(), 4.dp.toPx()))))
}

// ---------- Layout ----------

/**
 * A scrolling screen whose [bottom] actions sit at the foot of the screen when everything fits,
 * and scroll with the rest when the text is large.
 */
@Composable
fun PinnedColumn(
    padding: PaddingValues,
    modifier: Modifier = Modifier.safeDrawingPadding(),
    spacing: Dp,
    horizontalAlignment: Alignment.Horizontal = Alignment.Start,
    top: @Composable ColumnScope.() -> Unit,
    bottom: @Composable ColumnScope.() -> Unit,
) {
    BoxWithConstraints(Modifier.fillMaxSize().then(modifier)) {
        Column(
            Modifier.fillMaxWidth().verticalScroll(rememberScrollState()).heightIn(min = maxHeight).padding(padding),
            verticalArrangement = Arrangement.SpaceBetween,
            horizontalAlignment = horizontalAlignment,
        ) {
            Column(Modifier.fillMaxWidth(), verticalArrangement = Arrangement.spacedBy(spacing), horizontalAlignment = horizontalAlignment, content = top)
            Column(Modifier.fillMaxWidth().padding(top = spacing), verticalArrangement = Arrangement.spacedBy(spacing), horizontalAlignment = horizontalAlignment, content = bottom)
        }
    }
}

// ---------- Sheets and toast ----------

/** A bottom sheet over a scrim, rising like the design's .sheet. */
@Composable
fun SpellSheet(
    visible: Boolean,
    label: String,
    onDismiss: () -> Unit,
    content: @Composable ColumnScope.() -> Unit,
) {
    val c = Spell.colors
    val reduce = LocalReduceMotion.current
    if (visible) BackHandler(onBack = onDismiss)
    Box(Modifier.fillMaxSize()) {
        AnimatedVisibility(visible, enter = fadeIn(tween(250)), exit = fadeOut(tween(200))) {
            Box(
                Modifier
                    .fillMaxSize()
                    .background(c.scrim)
                    .clickable(interactionSource = remember { MutableInteractionSource() }, indication = null, onClickLabel = label, onClick = onDismiss)
            )
        }
        AnimatedVisibility(
            visible,
            modifier = Modifier.align(Alignment.BottomCenter),
            enter = if (reduce) fadeIn(tween(0)) else slideInVertically(tween(450, easing = Motion.EaseOut)) { it },
            exit = if (reduce) fadeOut(tween(0)) else slideOutVertically(tween(250)) { it },
        ) {
            Column(
                Modifier
                    .fillMaxWidth()
                    .clip(RoundedCornerShape(topStart = 32.dp, topEnd = 32.dp))
                    .background(c.sheet)
                    .border(1.dp, c.line, RoundedCornerShape(topStart = 32.dp, topEnd = 32.dp))
                    .pointerInput(Unit) { detectTapGestures { } }
                    .navigationBarsPadding()
                    .imePadding()
                    .semantics { paneTitle = label }
                    .verticalScroll(rememberScrollState())
                    .padding(start = 18.dp, end = 18.dp, top = 12.dp, bottom = 26.dp),
                verticalArrangement = Arrangement.spacedBy(12.dp),
            ) {
                Box(Modifier.align(Alignment.CenterHorizontally).size(40.dp, 5.dp).clip(RoundedCornerShape(3.dp)).background(c.handle))
                content()
            }
        }
    }
}

/** A short message at the bottom of the screen; [onGone] runs after 2.2 s. */
@Composable
fun SpellToast(text: String?, onGone: () -> Unit, modifier: Modifier = Modifier) {
    val c = Spell.colors
    LaunchedEffect(text) {
        if (text != null) {
            delay(2_200)
            onGone()
        }
    }
    Box(modifier.fillMaxSize().navigationBarsPadding().padding(bottom = 34.dp), contentAlignment = Alignment.BottomCenter) {
        AnimatedVisibility(text != null, enter = fadeIn(tween(200)), exit = fadeOut(tween(200))) {
            Text(
                text.orEmpty(),
                style = TextStyle(fontSize = 14.sp, fontWeight = FontWeight.SemiBold),
                color = c.bg,
                modifier = Modifier
                    .padding(horizontal = 24.dp)
                    .clip(RoundedCornerShape(14.dp))
                    .background(c.ink)
                    .padding(horizontal = 16.dp, vertical = 11.dp)
                    .semantics { liveRegion = LiveRegionMode.Polite },
            )
        }
    }
}

// ---------- Warning marks ----------

/**
 * The fuse: how long the caller had between asking and the call ending. A spiky mark where they
 * asked, a phone where it ended; 15 s is the full length.
 */
@Composable
fun Fuse(fraction: Float, modifier: Modifier = Modifier) {
    val c = Spell.colors
    val f by animateFloatAsState(fraction.coerceIn(0f, 1f), calmSpec(800), label = "fuse")
    Box(modifier.fillMaxWidth().height(28.dp).clearAndSetSemantics { }) {
        Canvas(Modifier.fillMaxSize()) {
            val y = size.height / 2f
            val left = 14.dp.toPx()
            val span = size.width - 28.dp.toPx()
            val h = 4.dp.toPx()
            drawRoundRect(c.surface2, Offset(left, y - h / 2), Size(span, h), CornerRadius(h / 2))
            if (f > 0f) drawRoundRect(c.end, Offset(left, y - h / 2), Size(span * f, h), CornerRadius(h / 2))
        }
        GuardianBlob(Blob.Burst, Modifier.size(26.dp).align(Alignment.CenterStart).offset(x = 1.dp), radius = 80f, color = c.end, spin = Spin.Fast)
        BoxWithConstraints(Modifier.fillMaxSize()) {
            val travel = maxWidth - 28.dp
            Box(
                Modifier.offset(x = travel * f).size(28.dp).clip(CircleShape).background(c.accent),
                contentAlignment = Alignment.Center,
            ) { Icon(Icons.Outlined.CallEnd, contentDescription = null, tint = c.onAccent, modifier = Modifier.size(14.dp)) }
        }
    }
}

/** Two short buzzes and a long one, drawn as bars that pulse in turn. */
@Composable
fun HapBars(modifier: Modifier = Modifier, color: Color = Spell.colors.warn, barHeight: Dp = 12.dp, gap: Dp = 6.dp) {
    val seconds = rememberSeconds()
    val reduce = LocalReduceMotion.current
    Canvas(modifier.height(barHeight * 1.4f).clearAndSetSemantics { }) {
        val g = gap.toPx()
        val unit = (size.width - 2 * g) / 4.6f
        val widths = floatArrayOf(unit, unit, unit * 2.6f)
        var x = 0f
        widths.forEachIndexed { i, w ->
            val (alpha, scale) = if (reduce) 1f to 1f else hapFrame(seconds.value - i * 0.18f)
            val h = barHeight.toPx() * scale
            drawRoundRect(color.copy(alpha = alpha), Offset(x, size.height / 2 - h / 2), Size(w, h), CornerRadius(barHeight.toPx() / 2))
            x += w + g
        }
    }
}

/** The design's hap keyframes: rest at 35% and 0.6x, peak at 30% of the 1.6 s cycle. */
private fun hapFrame(t: Float): Pair<Float, Float> {
    if (t < 0f) return 0.35f to 0.6f
    val p = (t % 1.6f) / 1.6f
    val k = if (p < 0.3f) p / 0.3f else 1f - (p - 0.3f) / 0.7f
    val e = 0.5f - 0.5f * cos(PI.toFloat() * k)
    return (0.35f + 0.65f * e) to (0.6f + 0.7f * e)
}

/** What the caller asked for, crossed out: a QR code, a code on the screen, or a PIN pad. */
enum class AskGlyph { Qr, Code, Pin, Install }

@Composable
fun CrossedGlyph(glyph: AskGlyph, color: Color, modifier: Modifier = Modifier) {
    Canvas(modifier.clearAndSetSemantics { }) {
        val u = size.minDimension / 24f
        val thin = Stroke(1.6f * u, cap = StrokeCap.Round)
        when (glyph) {
            AskGlyph.Qr -> {
                listOf(Offset(3f, 3f), Offset(14f, 3f), Offset(3f, 14f)).forEach {
                    drawRoundRect(color, Offset(it.x * u, it.y * u), Size(7f * u, 7f * u), CornerRadius(u), style = thin)
                }
                drawLine(color, Offset(14f * u, 14f * u), Offset(17f * u, 14f * u), thin.width, StrokeCap.Round)
                drawLine(color, Offset(17f * u, 14f * u), Offset(17f * u, 17f * u), thin.width, StrokeCap.Round)
                drawLine(color, Offset(21f * u, 21f * u), Offset(17f * u, 21f * u), thin.width, StrokeCap.Round)
            }
            AskGlyph.Code -> {
                drawRoundRect(color, Offset(2f * u, 7f * u), Size(20f * u, 10f * u), CornerRadius(3f * u), style = thin)
                listOf(7f, 12f, 17f).forEach { drawCircle(color, radius = 1.1f * u, center = Offset(it * u, 12f * u)) }
            }
            AskGlyph.Pin -> pinPad(color, u)
            AskGlyph.Install -> {
                drawRoundRect(color, Offset(6f * u, 2.5f * u), Size(12f * u, 19f * u), CornerRadius(2.5f * u), style = thin)
                drawLine(color, Offset(12f * u, 7f * u), Offset(12f * u, 14.5f * u), thin.width, StrokeCap.Round)
                drawLine(color, Offset(9f * u, 11.5f * u), Offset(12f * u, 14.5f * u), thin.width, StrokeCap.Round)
                drawLine(color, Offset(15f * u, 11.5f * u), Offset(12f * u, 14.5f * u), thin.width, StrokeCap.Round)
            }
        }
        drawLine(color, Offset(2f * u, 22f * u), Offset(22f * u, 2f * u), 2.4f * u, StrokeCap.Round)
    }
}

private fun DrawScope.pinPad(color: Color, u: Float) {
    for (row in 0 until 4) for (col in 0 until 3) {
        if (row == 3 && col != 1) continue
        drawCircle(color, radius = 1.5f * u, center = Offset((6f + col * 6f) * u, (4.5f + row * 5f) * u))
    }
}

/** The alert's "What they said": a label, then one pill per signal, in the app's own words. */
@OptIn(ExperimentalLayoutApi::class)
@Composable
fun SignalChips(signals: List<ThreatSignal>, label: Color, chip: Pair<Color, Color>, line: Color? = null, modifier: Modifier = Modifier) {
    val shape = RoundedCornerShape(999.dp)
    Column(modifier, verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Eyebrow(stringResource(R.string.sb_what_they_said), color = label)
        FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            signals.forEach { signal ->
                Text(
                    stringResource(signalLabel(signal)),
                    style = TextStyle(fontSize = 13.sp, fontWeight = FontWeight.Bold),
                    color = chip.second,
                    modifier = Modifier
                        .clip(shape)
                        .background(chip.first)
                        .then(if (line != null) Modifier.border(1.dp, line, shape) else Modifier)
                        .padding(horizontal = 12.dp, vertical = 6.dp),
                )
            }
        }
    }
}

fun signalLabel(signal: ThreatSignal): Int = when (signal) {
    ThreatSignal.OtpOrPinRequest -> R.string.signal_otp_or_pin_request
    ThreatSignal.RemoteAccess -> R.string.signal_remote_access
    ThreatSignal.FinancialSolicitation -> R.string.signal_financial_solicitation
    ThreatSignal.AuthorityImpersonation -> R.string.signal_authority_impersonation
    ThreatSignal.CoerciveThreat -> R.string.signal_coercive_threat
    ThreatSignal.AccountSuspensionThreat -> R.string.signal_account_suspension_threat
}

/** Marks a region as one thing for TalkBack. */
fun Modifier.described(text: String): Modifier = this.semantics(mergeDescendants = true) { contentDescription = text }

/** A thin divider line in the design's line colour. */
@Composable
fun Hairline(modifier: Modifier = Modifier) {
    Box(modifier.fillMaxWidth().height(1.dp).background(Spell.colors.line))
}

/** A vertical hairline, for the ticker. */
@Composable
fun VHairline(modifier: Modifier = Modifier, height: Dp = 40.dp) {
    Box(modifier.width(1.dp).height(height).background(Spell.colors.line))
}
