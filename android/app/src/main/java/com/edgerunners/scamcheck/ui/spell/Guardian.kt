package com.edgerunners.scamcheck.ui.spell

import androidx.compose.animation.core.Animatable
import androidx.compose.animation.core.animateOffsetAsState
import androidx.compose.animation.core.spring
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.State
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.withFrameNanos
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.StrokeJoin
import androidx.compose.ui.graphics.drawscope.DrawScope
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.drawscope.rotate
import androidx.compose.ui.graphics.drawscope.scale
import androidx.compose.ui.graphics.drawscope.translate
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.semantics.clearAndSetSemantics
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import com.edgerunners.scamcheck.ui.Motion
import com.edgerunners.scamcheck.ui.theme.LocalReduceMotion
import com.edgerunners.scamcheck.ui.theme.Spell
import kotlin.math.PI
import kotlin.math.abs
import kotlin.math.cos
import kotlin.math.pow
import kotlin.math.sign
import kotlin.math.sin

/**
 * The guardian: one soft shape that stands for scam check everywhere. A nine-lobed cookie while
 * it listens, a spiky burst when someone asks for money, smooth when scam check is off. It is
 * decoration; every screen says the same thing in words.
 */
enum class Blob { Cookie, Burst, Soft, Wobble }

/** How fast a shape turns: one full turn every so many seconds; negative turns backwards. */
enum class Spin(val seconds: Float) { None(0f), Normal(26f), Fast(5f), Reverse(-60f), SlowReverse(-90f) }

private const val POINTS = 120

/** Radius multipliers around the shape, one per point (the design's shapePath()). */
fun blobRadii(kind: Blob): FloatArray = FloatArray(POINTS) { i ->
    val t = i.toFloat() / POINTS * 2f * PI.toFloat()
    when (kind) {
        Blob.Cookie -> 1f + 0.075f * cos(9 * t)
        Blob.Burst -> {
            val f = cos(12 * t)
            1f + 0.16f * sign(f) * abs(f).pow(0.55f)
        }
        Blob.Soft -> 1f + 0.03f * cos(4 * t)
        Blob.Wobble -> 1f + 0.15f * cos(9 * t + 0.6f)
    }
}

/** A closed path through [radii], centred on [center]. */
fun blobPath(radii: FloatArray, center: Offset, radius: Float, lobes: Float = 1f): Path = Path().apply {
    for (i in radii.indices) {
        val t = i.toFloat() / radii.size * 2f * PI.toFloat()
        val r = radius * (1f + (radii[i] - 1f) * lobes)
        val x = center.x + r * cos(t)
        val y = center.y + r * sin(t)
        if (i == 0) moveTo(x, y) else lineTo(x, y)
    }
    close()
}

/** Seconds since this first composed, read in draw so only drawing repeats. Stops when motion is off. */
@Composable
fun rememberSeconds(): State<Float> {
    val reduce = LocalReduceMotion.current
    val time = remember { mutableFloatStateOf(0f) }
    LaunchedEffect(reduce) {
        if (reduce) return@LaunchedEffect
        val start = withFrameNanos { it }
        while (true) withFrameNanos { time.floatValue = (it - start) / 1_000_000_000f }
    }
    return time
}

private class Morph(var from: FloatArray, var to: FloatArray)

/**
 * Draws a guardian shape. [size] is the box; [radius] is the shape's radius as a share of the
 * design's 200-unit box (62 on Home, 74 on the alert, 80 in small marks).
 */
@Composable
fun GuardianBlob(
    kind: Blob,
    modifier: Modifier = Modifier,
    radius: Float = 62f,
    fill: Brush? = null,
    color: Color = Color.Unspecified,
    stroke: Color? = null,
    strokeUnits: Float = 0f,
    spin: Spin = Spin.Normal,
    breathe: Boolean = false,
    highlight: Float = 0f,
) {
    val reduce = LocalReduceMotion.current
    val morph = remember { Morph(blobRadii(kind), blobRadii(kind)) }
    val progress = remember { Animatable(1f) }
    LaunchedEffect(kind) {
        val target = blobRadii(kind)
        if (!target.contentEquals(morph.to)) {
            val p = progress.value
            morph.from = FloatArray(POINTS) { morph.from[it] + (morph.to[it] - morph.from[it]) * p }
            morph.to = target
            if (reduce) {
                progress.snapTo(1f)
            } else {
                progress.snapTo(0f)
                progress.animateTo(1f, spring(dampingRatio = 0.5f, stiffness = 260f))
            }
        }
    }
    val seconds = rememberSeconds()
    Canvas(modifier.clearAndSetSemantics { }) {
        val unit = size.minDimension / 200f
        val p = progress.value
        val radii = FloatArray(POINTS) { morph.from[it] + (morph.to[it] - morph.from[it]) * p }
        val path = blobPath(radii, center, radius * unit)
        val t = seconds.value
        val angle = if (spin == Spin.None) 0f else (360f * t / spin.seconds) % 360f
        val breath = if (breathe) 1f + 0.0225f * (1f - cos(2f * PI.toFloat() * t / 4.8f)) else 1f
        scale(breath, center) {
            rotate(angle, center) {
                when {
                    fill != null -> drawPath(path, fill)
                    color != Color.Unspecified -> drawPath(path, color)
                }
                if (stroke != null && strokeUnits > 0f) drawPath(path, stroke, style = Stroke(strokeUnits * unit))
                if (highlight > 0f) {
                    drawPath(
                        path,
                        Brush.radialGradient(
                            listOf(Color.White.copy(alpha = highlight), Color.White.copy(alpha = 0f)),
                            center = Offset(size.width * 0.34f, size.height * 0.28f),
                            radius = size.minDimension * 0.62f,
                        ),
                    )
                }
            }
        }
    }
}

/** The guardian's gradient: light top-left to deep bottom-right. */
@Composable
fun guardianBrush(): Brush {
    val c = Spell.colors
    return remember(c) { Brush.linearGradient(listOf(c.h1, c.h2), start = Offset.Zero, end = Offset.Infinite) }
}

/** The shield drawn on the guardian, in the design's 200-unit box. */
fun DrawScope.drawShield(color: Color, unit: Float, strokeUnits: Float = 5f) {
    val p = Path().apply {
        moveTo(100f * unit, 76f * unit)
        lineTo(120f * unit, 84.5f * unit)
        lineTo(120f * unit, 99.5f * unit)
        cubicTo(120f * unit, 113f * unit, 111.5f * unit, 124f * unit, 100f * unit, 129f * unit)
        cubicTo(88.5f * unit, 124f * unit, 80f * unit, 113f * unit, 80f * unit, 99.5f * unit)
        lineTo(80f * unit, 84.5f * unit)
        close()
    }
    drawPath(p, color, style = Stroke(strokeUnits * unit, join = StrokeJoin.Round))
}

/** The slash across the shield when scam check is off; [drawn] runs 0 to 1. */
fun DrawScope.drawSlash(color: Color, unit: Float, drawn: Float) {
    if (drawn <= 0f) return
    val start = Offset(80f * unit, 80f * unit)
    val end = Offset(120f * unit, 128f * unit)
    drawLine(color, start, start + (end - start) * drawn, strokeWidth = 5f * unit, cap = StrokeCap.Round)
}

private val FieldRings = listOf(130f, 190f, 260f, 340f, 430f, 530f)
private val FieldRadii = FloatArray(160) { j ->
    val t = j / 160f * 2f * PI.toFloat()
    1f + 0.05f * cos(9 * t)
}

/**
 * The protection field: guardian-shaped rings rippling out across the background. Its centre
 * glides to sit behind whatever the current tab is about.
 */
@Composable
fun ProtectionField(origin: Offset, modifier: Modifier = Modifier) {
    val c = Spell.colors
    val reduce = LocalReduceMotion.current
    val at by animateOffsetAsState(origin, if (reduce) tween(0) else tween(1100, easing = Motion.EaseOut), label = "field")
    val seconds = rememberSeconds()
    Canvas(modifier.graphicsLayer { alpha = c.fieldAlpha }.clearAndSetSemantics { }) {
        val centre = Offset(at.x * density, at.y * density)
        val t = seconds.value
        translate(0f, 0f) {
            FieldRings.forEachIndexed { i, r ->
                val period = 70f + i * 25f
                val angle = (360f * t / period) % 360f * if (i % 2 == 1) -1f else 1f
                rotate(angle, centre) {
                    drawPath(
                        blobPath(FieldRadii, centre, r * density),
                        c.ringc.copy(alpha = c.ringc.alpha * (1f - i * 0.13f)),
                        style = Stroke((1.4f - i * 0.12f) * density),
                    )
                }
            }
        }
    }
}

/** Radial glow behind the content, drifting slowly side to side. */
@Composable
fun GlowBackground(color: Color, modifier: Modifier = Modifier, height: Dp = 0.dp) {
    val seconds = rememberSeconds()
    Canvas(modifier.clearAndSetSemantics { }) {
        val drift = sin(2f * PI.toFloat() * seconds.value / 36f) * size.width * 0.06f
        val h = if (height > 0.dp) height.toPx() else size.height * 0.7f
        val centre = Offset(size.width / 2f + drift, h * 0.35f)
        drawRect(
            Brush.radialGradient(listOf(color, color.copy(alpha = 0f)), center = centre, radius = size.width * 0.8f),
        )
    }
}
