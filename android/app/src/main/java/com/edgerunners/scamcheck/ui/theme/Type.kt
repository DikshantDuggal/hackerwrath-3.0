package com.edgerunners.scamcheck.ui.theme

import androidx.compose.material3.Typography
import androidx.compose.runtime.Immutable
import androidx.compose.runtime.staticCompositionLocalOf
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.em
import androidx.compose.ui.unit.sp
import com.edgerunners.scamcheck.model.AppLanguage

// The design calls for Noto Sans with its Devanagari and Gurmukhi versions. Android already
// renders Devanagari and Gurmukhi with Noto, so the system font is used for now. To match the
// design exactly, add the Noto .ttf files to res/font and return those families here.
fun fontFamilyFor(@Suppress("UNUSED_PARAMETER") language: AppLanguage): FontFamily = FontFamily.Default

// Sizes are in sp so Android's font-size setting (up to 200%) scales them.
// Line heights are about 1.5x; Indic scripts need the room for their marks.
fun appTypography(family: FontFamily) = Typography(
    headlineMedium = TextStyle(fontFamily = family, fontWeight = FontWeight.SemiBold, fontSize = 28.sp, lineHeight = 38.sp),
    headlineSmall = TextStyle(fontFamily = family, fontWeight = FontWeight.SemiBold, fontSize = 24.sp, lineHeight = 34.sp),
    titleLarge = TextStyle(fontFamily = family, fontWeight = FontWeight.SemiBold, fontSize = 22.sp, lineHeight = 30.sp),
    titleMedium = TextStyle(fontFamily = family, fontWeight = FontWeight.Medium, fontSize = 18.sp, lineHeight = 27.sp),
    bodyLarge = TextStyle(fontFamily = family, fontWeight = FontWeight.Normal, fontSize = 18.sp, lineHeight = 28.sp),
    bodyMedium = TextStyle(fontFamily = family, fontWeight = FontWeight.Normal, fontSize = 16.sp, lineHeight = 24.sp),
    labelLarge = TextStyle(fontFamily = family, fontWeight = FontWeight.SemiBold, fontSize = 18.sp, lineHeight = 24.sp),
    labelMedium = TextStyle(fontFamily = family, fontWeight = FontWeight.Medium, fontSize = 14.sp, lineHeight = 20.sp),
)

// Spellbreaker display type. The design calls for Anek Latin/Devanagari/Gurmukhi (variable width)
// in Standard and Tiro Devanagari Hindi/Gurmukhi in Premium. Until those .ttf files are in
// res/font, Standard uses the system sans at a heavy weight and Premium the system serif.
@Immutable
data class SpellType(
    private val displayBase: TextStyle,
    private val displayScale: Float,
    /** The alert's one big word ("DON'T SCAN."). */
    val alertWord: TextStyle,
    /** Small uppercase labels above sections. */
    val eyebrow: TextStyle,
) {
    /** A display line at the design's [size] (in sp), scaled per edition. */
    fun display(size: Float, lineHeight: Float = 1.05f): TextStyle =
        displayBase.copy(fontSize = (size * displayScale).sp, lineHeight = (size * displayScale * lineHeight).sp)
}

fun spellType(edition: Edition): SpellType = when (edition) {
    Edition.Standard -> SpellType(
        displayBase = TextStyle(fontFamily = FontFamily.Default, fontWeight = FontWeight.ExtraBold, letterSpacing = (-0.015).em),
        displayScale = 1f,
        alertWord = TextStyle(fontFamily = FontFamily.Default, fontWeight = FontWeight.Black, fontSize = 56.sp, lineHeight = 52.sp, letterSpacing = (-0.01).em),
        eyebrow = TextStyle(fontWeight = FontWeight.Bold, fontSize = 12.sp, lineHeight = 16.sp, letterSpacing = 0.16.em),
    )
    Edition.Premium -> SpellType(
        displayBase = TextStyle(fontFamily = FontFamily.Serif, fontWeight = FontWeight.Normal, letterSpacing = (-0.01).em),
        displayScale = 1.08f,
        alertWord = TextStyle(fontFamily = FontFamily.Serif, fontWeight = FontWeight.Normal, fontStyle = FontStyle.Italic, fontSize = 54.sp, lineHeight = 52.sp, letterSpacing = (-0.01).em),
        eyebrow = TextStyle(fontWeight = FontWeight.Bold, fontSize = 12.sp, lineHeight = 16.sp, letterSpacing = 0.24.em),
    )
}

val LocalSpellType = staticCompositionLocalOf { spellType(Edition.Standard) }
