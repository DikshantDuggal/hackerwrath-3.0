package com.edgerunners.scamcheck.ui.theme

import androidx.compose.ui.graphics.Color

// Nordic calm palette. Brand blue is never used for status, and nothing here is green:
// the app never signals "safe".

// Base
val NordicWhite = Color(0xFFFAFAF8)     // app background
val PureWhite = Color(0xFFFFFFFF)       // raised cards
val CoolGrey = Color(0xFFE6E8EB)        // secondary surfaces, dividers
val Charcoal = Color(0xFF1F2937)        // primary text
val Slate = Color(0xFF4B5563)           // secondary text (7:1+ on NordicWhite)
val Outline = Color(0xFFC9CDD3)         // control borders

// Brand
val EditorialBlue = Color(0xFF226192)   // primary actions, listening status
val EditorialBlueDark = Color(0xFF123A58)
val EditorialBlueContainer = Color(0xFFE3EDF5)
val PalePink = Color(0xFFF4BEBB)        // decorative only: illustrations, never status UI

// Status: possible risk / checking (amber)
val AmberContainer = Color(0xFFFFF4DC)
val AmberBorder = Color(0xFFE8A317)
val AmberIcon = Color(0xFFB26A00)
val OnAmberContainer = Color(0xFF6B4300)

// Status: high risk (red)
val RedContainer = Color(0xFFFDECEB)
val RedBorder = Color(0xFFD92D20)
val OnRedContainer = Color(0xFF8A1C14)
val RedAction = Color(0xFFB42318)       // End call button; white text on it
val OnRedAction = Color(0xFFFFFFFF)

// Status: protection unavailable / scam check off (neutral, not alarming)
val InfoContainer = Color(0xFFEEF2F6)
val InfoIcon = EditorialBlue
val OnInfoContainer = Charcoal
val OffGrey = Color(0xFF6B7280)

// Night: the call screens. A deep Nordic night so the Halo can glow.
val Night = Color(0xFF0C1724)
val NightRaised = Color(0xFF13243A)
val NightHorizon = Color(0xFF18314D)
val OnNight = Color(0xFFEEF3F8)
val OnNightMuted = Color(0xFF9DB0C5)       // 7:1+ on Night
val NightControl = Color(0x1AFFFFFF)       // 10% white
val AnswerBlue = Color(0xFF2F7DBE)
val DeclineRed = Color(0xFFC8322A)

// Halo moods. Each is always paired with words on screen.
val HaloDay = Color(0xFF2E78B4)            // Home and recap, on light
val HaloListening = Color(0xFF5CAAE8)      // on Night
val HaloChecking = Color(0xFFF2A93B)
val HaloHigh = Color(0xFFE5484D)
val HaloPaused = Color(0xFF8A97A8)
val HaloOff = Color(0xFFB0B9C4)
val CheckingText = Color(0xFFF6C46E)       // amber words on Night

// Takeover floods (top of the gradient to the bottom)
val FloodHighTop = Color(0xFFD0342A)
val FloodHighMid = Color(0xFF9E1D14)
val FloodHighBottom = Color(0xFF5A0E09)
val FloodPossibleTop = Color(0xFFE9A23A)
val FloodPossibleMid = Color(0xFF9C6206)
val FloodPossibleBottom = Color(0xFF3A2500)
val TokenGold = Color(0xFFFFD27A)
val OnTokenGold = Color(0xFF5A3A00)
val BankNote = Color(0xFFFFF7E6)
val BankNoteBorder = Color(0xFFF3D9A4)
