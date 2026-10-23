package com.edgerunners.scamcheck.ui.theme

import androidx.compose.runtime.Immutable
import androidx.compose.runtime.staticCompositionLocalOf
import androidx.compose.ui.graphics.Color

/** Colours for one monitoring state. Always pair with an icon and words, never colour alone. */
@Immutable
data class StatusTone(
    val container: Color,
    val border: Color,
    val icon: Color,
    val content: Color,
)

@Immutable
data class StatusColors(
    val listening: StatusTone,
    val checking: StatusTone,   // amber: "Checking a payment request…" and Possible risk
    val highRisk: StatusTone,   // red: High risk
    val unavailable: StatusTone,
    val off: StatusTone,
    val endCall: Color,
    val onEndCall: Color,
)

val LightStatusColors = StatusColors(
    listening = StatusTone(EditorialBlueContainer, EditorialBlue, EditorialBlue, EditorialBlueDark),
    checking = StatusTone(AmberContainer, AmberBorder, AmberIcon, OnAmberContainer),
    highRisk = StatusTone(RedContainer, RedBorder, RedBorder, OnRedContainer),
    unavailable = StatusTone(InfoContainer, Outline, InfoIcon, OnInfoContainer),
    off = StatusTone(CoolGrey, Outline, OffGrey, Charcoal),
    endCall = RedAction,
    onEndCall = OnRedAction,
)

val LocalStatusColors = staticCompositionLocalOf { LightStatusColors }
