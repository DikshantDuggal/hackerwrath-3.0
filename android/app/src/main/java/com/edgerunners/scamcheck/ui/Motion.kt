package com.edgerunners.scamcheck.ui

import androidx.compose.animation.AnimatedContentTransitionScope
import androidx.compose.animation.ContentTransform
import androidx.compose.animation.EnterTransition
import androidx.compose.animation.ExitTransition
import androidx.compose.animation.core.Animatable
import androidx.compose.animation.core.AnimationSpec
import androidx.compose.animation.core.CubicBezierEasing
import androidx.compose.animation.core.Spring
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.snap
import androidx.compose.animation.core.spring
import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.scaleIn
import androidx.compose.animation.slideInVertically
import androidx.compose.animation.togetherWith
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.interaction.collectIsPressedAsState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.unit.dp
import com.edgerunners.scamcheck.ui.theme.LocalReduceMotion
import kotlinx.coroutines.delay

/**
 * Motion language: calm and physical. Screens drift up and settle; the Halo glides between
 * screens; warnings arrive with one decisive move (the flood). Nothing loops except the Halo's
 * breathing. Everything snaps when Android's animations are off.
 */
object Motion {
    val EaseOut = CubicBezierEasing(0.2f, 0f, 0f, 1f)
    /** For the alert flood: slow start, fast middle, soft landing. */
    val Flood = CubicBezierEasing(0.6f, 0f, 0.2f, 1f)
    const val SHORT = 180
    const val MEDIUM = 280
    const val LONG = 450
    const val FLOOD = 750
}

@Composable
fun <T> calmSpec(durationMs: Int = Motion.MEDIUM): AnimationSpec<T> =
    if (LocalReduceMotion.current) snap() else tween(durationMs, easing = Motion.EaseOut)

/** A soft spring with a little give, for switches, pills and selection. */
@Composable
fun <T> giveSpec(): AnimationSpec<T> =
    if (LocalReduceMotion.current) snap() else spring(dampingRatio = 0.72f, stiffness = Spring.StiffnessMediumLow)

/** Screen-to-screen: the new screen drifts up and settles while the old one fades. */
fun <S> AnimatedContentTransitionScope<S>.screenTransition(reduceMotion: Boolean): ContentTransform =
    if (reduceMotion) {
        EnterTransition.None togetherWith ExitTransition.None
    } else {
        (fadeIn(tween(Motion.LONG, easing = Motion.EaseOut)) +
            slideInVertically(tween(Motion.LONG + 100, easing = Motion.EaseOut)) { it / 24 } +
            scaleIn(tween(Motion.LONG + 100, easing = Motion.EaseOut), initialScale = 0.98f)) togetherWith
            fadeOut(tween(Motion.SHORT + 60))
    }

/** Buttons give a little when pressed. */
@Composable
fun Modifier.pressScale(interaction: MutableInteractionSource): Modifier {
    val pressed by interaction.collectIsPressedAsState()
    val scale by animateFloatAsState(if (pressed) 0.95f else 1f, giveSpec(), label = "press")
    return graphicsLayer {
        scaleX = scale
        scaleY = scale
    }
}

/** Content rises into place after [delayMs], once, when it first appears. */
@Composable
fun Modifier.riseIn(delayMs: Int): Modifier {
    val reduceMotion = LocalReduceMotion.current
    val progress = remember { Animatable(if (reduceMotion) 1f else 0f) }
    LaunchedEffect(Unit) {
        if (!reduceMotion) {
            delay(delayMs.toLong())
            progress.animateTo(1f, tween(Motion.LONG, easing = Motion.EaseOut))
        }
    }
    return graphicsLayer {
        alpha = progress.value
        translationY = (1f - progress.value) * 18.dp.toPx()
    }
}
