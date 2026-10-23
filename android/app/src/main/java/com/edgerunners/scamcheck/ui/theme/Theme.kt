package com.edgerunners.scamcheck.ui.theme

import android.provider.Settings
import androidx.compose.material3.ColorScheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.remember
import androidx.compose.runtime.staticCompositionLocalOf
import androidx.compose.ui.platform.LocalContext
import com.edgerunners.scamcheck.model.AppLanguage

// The pre-Spellbreaker Nordic scheme, kept for reference while the redesign settles.
@Suppress("unused")
private val NordicLightColors = lightColorScheme(
    primary = EditorialBlue,
    onPrimary = PureWhite,
    primaryContainer = EditorialBlueContainer,
    onPrimaryContainer = EditorialBlueDark,
    secondary = Slate,
    onSecondary = PureWhite,
    secondaryContainer = CoolGrey,
    onSecondaryContainer = Charcoal,
    tertiary = PalePink,
    onTertiary = Charcoal,
    background = NordicWhite,
    onBackground = Charcoal,
    surface = NordicWhite,
    onSurface = Charcoal,
    surfaceVariant = CoolGrey,
    onSurfaceVariant = Slate,
    outline = Outline,
    outlineVariant = CoolGrey,
    error = RedAction,
    onError = OnRedAction,
    errorContainer = RedContainer,
    onErrorContainer = OnRedContainer,
)

/** Material colours for the Spellbreaker screens, so text fields and dialogs match the edition. */
private fun spellScheme(c: SpellColors): ColorScheme {
    val base = if (c.premium) darkColorScheme() else lightColorScheme()
    return base.copy(
        primary = c.accent,
        onPrimary = c.onAccent,
        primaryContainer = c.accentC,
        onPrimaryContainer = c.onAccentC,
        secondary = c.muted,
        onSecondary = c.bg,
        secondaryContainer = c.surface2,
        onSecondaryContainer = c.ink,
        tertiary = c.tert,
        onTertiary = c.onTert,
        background = c.bg,
        onBackground = c.ink,
        surface = c.bg,
        onSurface = c.ink,
        surfaceVariant = c.surface2,
        onSurfaceVariant = c.faint,
        outline = c.handle,
        outlineVariant = c.line,
        error = c.end,
        onError = c.onEnd,
    )
}

/** True when the user has turned animations off in Android's accessibility settings. */
val LocalReduceMotion = staticCompositionLocalOf { false }

/**
 * App theme. Spellbreaker for every screen; [edition] picks Standard or Premium. Dynamic colour
 * (Material You) is deliberately off so status colours always mean the same thing. The Nordic
 * palette above stays available for the status tones and notifications.
 */
@Composable
fun EdgerunnersTheme(
    language: AppLanguage = AppLanguage.English,
    edition: Edition = Edition.Standard,
    content: @Composable () -> Unit,
) {
    val context = LocalContext.current
    val reduceMotion = remember {
        Settings.Global.getFloat(context.contentResolver, Settings.Global.ANIMATOR_DURATION_SCALE, 1f) == 0f
    }
    val spell = if (edition == Edition.Premium) PremiumSpell else StandardSpell
    CompositionLocalProvider(
        LocalStatusColors provides LightStatusColors,
        LocalReduceMotion provides reduceMotion,
        LocalEdition provides edition,
        LocalSpellColors provides spell,
        LocalSpellType provides spellType(edition),
    ) {
        MaterialTheme(
            colorScheme = remember(spell) { spellScheme(spell) },
            typography = appTypography(fontFamilyFor(language)),
            shapes = AppShapes,
            content = content,
        )
    }
}

object AppTheme {
    val status: StatusColors
        @Composable get() = LocalStatusColors.current
}
