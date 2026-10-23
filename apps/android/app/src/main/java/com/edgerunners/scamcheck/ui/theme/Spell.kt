package com.edgerunners.scamcheck.ui.theme

import androidx.compose.runtime.Composable
import androidx.compose.runtime.Immutable
import androidx.compose.runtime.staticCompositionLocalOf
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp

// Spellbreaker: the research pick from the design canvas ("Scam Check Guardian").
// One app, two editions: Standard (warm paper, editorial blue) and Premium (night, gold).
// Like the Nordic palette, nothing here is green: the app never signals "safe".

enum class Edition { Standard, Premium }

/** Pick the edition with `ui.edition=premium` in local.properties. */
fun editionFrom(value: String): Edition = if (value.equals("premium", ignoreCase = true)) Edition.Premium else Edition.Standard

@Immutable
data class SpellColors(
    val premium: Boolean,
    // Day surfaces
    val bg: Color,
    val glow: Color,
    val surface2: Color,
    val card: Color,
    val line: Color,
    val ink: Color,
    val muted: Color,
    val faint: Color,
    val head: Color,
    val accent: Color,
    val onAccent: Color,
    val accentC: Color,
    val onAccentC: Color,
    val tert: Color,
    val onTert: Color,
    val off: Color,
    val knobOn: Color,
    // The guardian's gradient and its rings
    val h1: Color,
    val h2: Color,
    val ringc: Color,
    val eyebrow: Color,
    val fieldAlpha: Float,
    // Night: call screens
    val night: Color,
    val nightCard: Color,
    val nightInk: Color,
    val nightMuted: Color,
    val nightLine: Color,
    val earFill: Color,
    val earGlow: Color,
    val earRing: Color,
    val earOff: Color,
    // Warning amber (checking, practice)
    val warn: Color,
    val onWarn: Color,
    val warnSoft: Color,
    val warnGlow: Color,
    val warnRing: Color,
    // Sheets and chrome
    val sheet: Color,
    val handle: Color,
    val scrim: Color,
    val end: Color,
    val onEnd: Color,
    val navBg: Color,
    /** End-call red on the night screens. */
    val hangUp: Color,
    /** White marks drawn on the guardian (shield, countdown, "YOU"). */
    val onGuardian: Color,
    /** Soft dark wash behind small icons, and the drop shadow under big buttons. */
    val shade: Color,
    val shadow: Color,
    /** Tab colours, in tab order Recents, Home, Contacts: the radial wipe and the nav pill. */
    val wipe: List<Color>,
    val indicator: List<Color>,
    val onIndicator: List<Color>,
    val wipeTitle: List<Color>,
    /** Demo call badges: QR scam, OTP scam, ordinary call. Background then content. */
    val badgeQr: Pair<Color, Color>,
    val badgeOtp: Pair<Color, Color>,
    val badgeCalm: Pair<Color, Color>,
)

val StandardSpell = SpellColors(
    premium = false,
    bg = Color(0xFFF4F1EA),
    glow = Color(0x29226192),
    surface2 = Color(0xFFEAE6DE),
    card = Color(0xFFFFFFFF),
    line = Color(0x0F1D1B16),
    ink = Color(0xFF1D1B16),
    muted = Color(0xFF4A4840),
    faint = Color(0xFF6B6960),
    head = Color(0xFF0B2F4D),
    accent = Color(0xFF226192),
    onAccent = Color(0xFFFFFFFF),
    accentC = Color(0xFFD3E4F5),
    onAccentC = Color(0xFF0B2F4D),
    tert = Color(0xFFFFDCCB),
    onTert = Color(0xFF5A1E00),
    off = Color(0xFFC9C5BB),
    knobOn = Color(0xFFFFFFFF),
    h1 = Color(0xFF3A86C4),
    h2 = Color(0xFF164A75),
    ringc = Color(0x38226192),
    eyebrow = Color(0xFF226192),
    fieldAlpha = 0.75f,
    night = Color(0xFF0E1015),
    nightCard = Color(0xFF171A22),
    nightInk = Color(0xFFE8EAF0),
    nightMuted = Color(0xFF8A90A0),
    nightLine = Color(0x0FFFFFFF),
    earFill = Color(0xFF3B5B86),
    earGlow = Color(0x4D3B5B86),
    earRing = Color(0x387DB8E8),
    earOff = Color(0xFF2A2E38),
    warn = Color(0xFFF2B035),
    onWarn = Color(0xFF2B1D00),
    warnSoft = Color(0xFFFFE3A6),
    warnGlow = Color(0x4DF2B035),
    warnRing = Color(0x73F2B035),
    sheet = Color(0xFFF4F1EA),
    handle = Color(0xFFC9C5BB),
    scrim = Color(0x6B1D1B16),
    end = Color(0xFFC4161C),
    onEnd = Color(0xFFFFFFFF),
    navBg = Color(0xE6F4F1EA),
    hangUp = Color(0xFFE5484D),
    onGuardian = Color(0xFFFFFFFF),
    shade = Color(0x14000000),
    shadow = Color(0x2E000000),
    wipe = listOf(Color(0xFF2563C9), Color(0xFF226192), Color(0xFF0B2F4D)),
    indicator = listOf(Color(0xFF2563C9), Color(0xFF226192), Color(0xFF0B2F4D)),
    onIndicator = listOf(Color(0xFFFFFFFF), Color(0xFFFFFFFF), Color(0xFFFFFFFF)),
    wipeTitle = listOf(Color(0xFFFFFFFF), Color(0xFFFFFFFF), Color(0xFFFFFFFF)),
    badgeQr = Color(0xFFFBE3E1) to Color(0xFF8A1C14),
    badgeOtp = Color(0xFFFFF4DC) to Color(0xFF6B4300),
    badgeCalm = Color(0xFFD3E4F5) to Color(0xFF0B2F4D),
)

val PremiumSpell = SpellColors(
    premium = true,
    bg = Color(0xFF0E1014),
    glow = Color(0x33C18D17),
    surface2 = Color(0xFF1C2028),
    card = Color(0xFF15181E),
    line = Color(0x2ED9B26A),
    ink = Color(0xFFF1ECE2),
    muted = Color(0xADF1ECE2),
    faint = Color(0x8CF1ECE2),
    head = Color(0xFFF1ECE2),
    accent = Color(0xFFC18D17),
    onAccent = Color(0xFF120D04),
    accentC = Color(0xFF1C2028),
    onAccentC = Color(0xFFF1ECE2),
    tert = Color(0xFF241D14),
    onTert = Color(0xFFE2C27C),
    off = Color(0xFF3A3F4B),
    knobOn = Color(0xFF120D04),
    h1 = Color(0xFFF0D594),
    h2 = Color(0xFF9C7313),
    ringc = Color(0x52D9B26A),
    eyebrow = Color(0xFFD9B26A),
    fieldAlpha = 0.6f,
    night = Color(0xFF07080B),
    nightCard = Color(0xFF12151B),
    nightInk = Color(0xFFF1ECE2),
    nightMuted = Color(0x8CF1ECE2),
    nightLine = Color(0x29D9B26A),
    earFill = Color(0xFF8C6A1E),
    earGlow = Color(0x24C18D17),
    earRing = Color(0x38D9B26A),
    earOff = Color(0xFF2A2E38),
    warn = Color(0xFFE2B04A),
    onWarn = Color(0xFF1A1205),
    warnSoft = Color(0xFFF3DDA8),
    warnGlow = Color(0x4DF2B035),
    warnRing = Color(0x73F2B035),
    sheet = Color(0xFF15181E),
    handle = Color(0xFF3A3F4B),
    scrim = Color(0x99000000),
    end = Color(0xFF800000),
    onEnd = Color(0xFFFFFFFF),
    navBg = Color(0xE00E1014),
    hangUp = Color(0xFFE5484D),
    onGuardian = Color(0xFFFFFFFF),
    shade = Color(0x14000000),
    shadow = Color(0x40000000),
    wipe = listOf(Color(0xFF1E3A6E), Color(0xFFC18D17), Color(0xFF1C2028)),
    indicator = listOf(Color(0xFF1E3A6E), Color(0xFFC18D17), Color(0xFFF1ECE2)),
    onIndicator = listOf(Color(0xFFF1ECE2), Color(0xFF120D04), Color(0xFF120D04)),
    wipeTitle = listOf(Color(0xFFFFFFFF), Color(0xFF120D04), Color(0xFFFFFFFF)),
    badgeQr = Color(0xFF2A1214) to Color(0xFFF3B4AE),
    badgeOtp = Color(0xFF2A2214) to Color(0xFFE2C27C),
    badgeCalm = Color(0xFF1C2028) to Color(0xFFF1ECE2),
)

/**
 * The full-screen alert breaks the app's look on purpose, and wears a different face each time
 * so the warning never turns into wallpaper. Same words, same order, same buttons.
 */
enum class AlertEntrance { ZoomIn, Jiggle, Slam }

@Immutable
data class AlertLook(
    val bg: Color,
    val fg: Color,
    val highlight: Color,
    val card: Color,
    val end: Color,
    val onEnd: Color,
    val line: Color,
    val entrance: AlertEntrance,
    val frame: Color? = null,
    val frameWidth: Dp = 10.dp,
    val frameHairline: Color? = null,
)

/** Run 1 Red field, run 2 Night siren, run 3 Red frame. */
fun alertLooks(edition: Edition): List<AlertLook> = when (edition) {
    Edition.Standard -> listOf(
        AlertLook(Color(0xFFC4161C), Color.White, Color.White, Color(0x24FFFFFF), Color.White, Color(0xFF9E0F14), Color(0xBFFFFFFF), AlertEntrance.ZoomIn),
        AlertLook(Color(0xFF0B0B0C), Color.White, Color(0xFFFF453A), Color(0xFF1E1E22), Color(0xFFFF453A), Color(0xFF0B0B0C), Color(0xFFFF453A), AlertEntrance.Jiggle),
        AlertLook(Color.White, Color(0xFF1A1A1A), Color(0xFFC4161C), Color(0xFFFCE8E8), Color(0xFFC4161C), Color.White, Color(0xFFC4161C), AlertEntrance.Slam, frame = Color(0xFFC4161C)),
    )
    Edition.Premium -> listOf(
        AlertLook(Color(0xFF800000), Color.White, Color(0xFFF3DDA8), Color(0x14FFFFFF), Color(0xFFF1ECE2), Color(0xFF5C0000), Color(0xB3F3DDA8), AlertEntrance.ZoomIn, frame = Color(0xFF800000), frameHairline = Color(0x8CF3DDA8)),
        AlertLook(Color(0xFF07080B), Color.White, Color(0xFFFF5A4E), Color(0xFF14161C), Color(0xFFFF5A4E), Color(0xFF07080B), Color(0xCCFF5A4E), AlertEntrance.Jiggle),
        AlertLook(Color(0xFFF1ECE2), Color(0xFF1A1408), Color(0xFF800000), Color(0xFFFFD5FB), Color(0xFF800000), Color.White, Color(0xFF800000), AlertEntrance.Slam, frame = Color(0xFF800000)),
    )
}

val LocalSpellColors = staticCompositionLocalOf { StandardSpell }
val LocalEdition = staticCompositionLocalOf { Edition.Standard }

object Spell {
    val colors: SpellColors
        @Composable get() = LocalSpellColors.current
    val edition: Edition
        @Composable get() = LocalEdition.current
    val type: SpellType
        @Composable get() = LocalSpellType.current
}
