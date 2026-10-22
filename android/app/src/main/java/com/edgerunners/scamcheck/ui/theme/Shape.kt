package com.edgerunners.scamcheck.ui.theme

import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Shapes
import androidx.compose.ui.unit.dp

val AppShapes = Shapes(
    small = RoundedCornerShape(12.dp),   // chips, small panels
    medium = RoundedCornerShape(16.dp),  // cards, status panels, buttons
    large = RoundedCornerShape(24.dp),   // alert sheet, bottom panels
)

/** Spacing and sizing tokens. Touch targets never go below MinTouch. */
object Space {
    val xs = 4.dp
    val sm = 8.dp
    val md = 16.dp
    val lg = 24.dp
    val xl = 32.dp
    val xxl = 48.dp
    val screenPadding = 24.dp
    val MinTouch = 48.dp
    val PrimaryButtonHeight = 64.dp      // End call and other primary actions
    val CallControlSize = 72.dp          // round mute / speaker / end controls
}
