"""
Script-Aware Multilingual Language and Script Identification Engine.

Supports 7 distinct categories:
1. english (Latin script)
2. hindi_devanagari (Devanagari script)
3. hinglish (Hindi written in Latin script)
4. punjabi_gurmukhi (Gurmukhi script)
5. punjabi_latin (Punjabi written in Latin script)
6. hindi_mixed (Devanagari mixed with Latin/English words)
7. punjabi_mixed (Gurmukhi mixed with Latin/English words)

Preserves original input text without destructive transliteration or lossy overwriting.
"""
from __future__ import annotations

import re
from typing import Dict, List, Literal, Optional, Set, Tuple
from app.core.compat import BaseModel, Field

# Script Unicode Ranges
DEVANAGARI_RE = re.compile(r"[\u0900-\u097F\uA8E0-\uA8FF]")
GURMUKHI_RE = re.compile(r"[\u0A00-\u0A7F]")
LATIN_WORDS_RE = re.compile(r"\b[a-zA-Z]+(?:'[a-zA-Z]+)?\b")

LanguageCategoryType = Literal[
    "english",
    "hindi_devanagari",
    "hinglish",
    "punjabi_gurmukhi",
    "punjabi_latin",
    "hindi_mixed",
    "punjabi_mixed",
    "unknown",
]

ScriptType = Literal["Latin", "Devanagari", "Gurmukhi", "Mixed", "None"]


class LanguageDetectionResult(BaseModel):
    """Structured result of language and script identification."""

    original_text: str = Field(default="", description="Original un-mutated input text")
    normalized_text: str = Field(default="", description="Normalized text for downstream matching")
    detected_language: LanguageCategoryType = Field(default="unknown")
    detected_script: ScriptType = Field(default="None")
    confidence: float = Field(default=0.85, ge=0.0, le=1.0)
    is_conversational: bool = Field(
        default=False,
        description="Whether the text represents everyday conversational greetings/chat",
    )
    language_category: str = Field(default="unknown")
    matched_markers: List[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# VOCABULARY MARKERS
# ---------------------------------------------------------------------------

PUNJABI_SPECIFIC_MARKERS: Set[str] = {
    # Pronouns & determiners
    "tussi", "tusi", "tuhada", "tuhadi", "tuhade", "tuhaada", "tuhaadi", "tuhaade",
    "saada", "saadi", "saade", "kise", "mainu", "tenu", "assi", "asin", "tuhanu",
    # Verbs
    "dasso", "daso", "dass", "das", "dassna", "dassiye", "dasna", "dasiye",
    "deo", "diyo", "devo", "paao", "paa", "paalo", "paalo", "vekh", "vekho", "labh",
    "jaavega", "jaavegi", "jaavange", "hovega", "hovegi", "hovange",
    "karange", "karan", "kariye", "karda", "kardi", "karde",
    "reha", "rahi", "rehnde", "onde", "jande", "saunde",
    # Particles, adverbs, prepositions
    "kive", "kiven", "kivein", "kidda", "kiddan", "kitho", "kithe", "kadon",
    "kinna", "kinne", "hune", "chheti", "vich", "naal", "kol", "agay", "pichay",
    "te", "nu", "da", "di", "de", "ne", "ch", "si", "san", "nai", "aaho",
    # Greetings & honorifics
    "paaji", "paji", "veere", "veerji", "bhaji", "bhenji", "chaaji", "chaachi",
    "sat", "sri", "akaal", "hanji", "haanji", "chahida", "chahidi", "chahide",
    "rab", "rakha", "dhanwad", "haal", "chaal", "thaak",
    # Fraud & Banking
    "pese", "khate"
}

HINGLISH_MARKERS: Set[str] = {
    # Pronouns & determiners
    "aap", "aapka", "aapke", "aapki", "apna", "apne", "apni",
    "mera", "meri", "mere", "tera", "teri", "tere", "tum", "tumhara", "tumhari", "tumhare",
    "hum", "humare", "hamara", "hamari", "hamare", "kisi", "kisko", "kiska", "kiske", "kiski",
    "koi", "kuch", "sab", "sabka", "sabki", "sabke",
    # Auxiliary verbs & tense
    "hai", "hain", "ho", "hoon", "hu", "hoga", "hogi", "hoge",
    "tha", "thi", "the", "raha", "rahi", "rahe",
    # Verbs
    "karo", "karein", "karna", "kijiye", "kardo", "kar", "karta", "karti", "karte",
    "batao", "bataiye", "bata", "batao", "batana", "bataye",
    "de", "do", "dena", "dijiye", "dekh", "dekho", "dekhiye",
    "bhejo", "bhejiye", "bhej", "bhejna", "daalo", "daaliye", "daal", "daalna",
    "bolo", "boliye", "bol", "bolna", "likho", "likhiye", "likh", "likhna",
    "chahiye", "samajh", "samjho", "aayega", "aayegi", "ayega", "ayegi", "chal", "chalo",
    # Questions & adverbs
    "kya", "kyun", "kyu", "kaise", "kaisa", "kaisi", "kaha", "kahan", "kidhar", "kab",
    "kitna", "kitni", "kitne", "jaldi", "turant", "warna", "kripya", "matlab",
    # Negations, conversational particles, greetings
    "nahi", "nahin", "na", "mat", "kabhi", "bhi", "toh", "to", "hi", "ji",
    "namaste", "pranam", "shukriya", "dhanyawad", "theek", "achha", "accha", "haan", "ha",
    "bhai", "yaar", "dost", "baat", "baatein", "khata", "band", "paise", "rupaye"
}

CONVERSATIONAL_GREETING_PATTERNS: Tuple[re.Pattern, ...] = (
    # Hinglish greetings
    re.compile(r"\b(?:aap|tum)\s+kaise\s+(?:hai|hain|ho)\b", re.IGNORECASE),
    re.compile(r"\b(?:kya|ki)\s+(?:haal|chal)\s+(?:hai|chaal)\b", re.IGNORECASE),
    re.compile(r"\bbhai\s+kya\s+(?:kar\s+raha|chal\s+raha)\b", re.IGNORECASE),
    re.compile(r"\bnamaste(?:\s+ji)?\b", re.IGNORECASE),
    re.compile(r"\bsab\s+theek(?:\s+hai)?\b", re.IGNORECASE),
    re.compile(r"\baur\s+batao\b", re.IGNORECASE),
    re.compile(r"\btheek\s+(?:hoon|hu)\b", re.IGNORECASE),
    # Punjabi Latin greetings
    re.compile(r"\b(?:tussi|tusi)\s+(?:kive|kiven|kivein)\s+(?:ho|o)\b", re.IGNORECASE),
    re.compile(r"\bki\s+haal(?:\s+chaal)?(?:\s+hai)?\b", re.IGNORECASE),
    re.compile(r"\bkidda(?:\s+paaji|\s+veere)?\b", re.IGNORECASE),
    re.compile(r"\bsat\s+sri\s+akaal(?:\s+ji)?\b", re.IGNORECASE),
    re.compile(r"\bsab\s+theek\s+thaak\b", re.IGNORECASE),
    # Devanagari greetings
    re.compile(r"(?:आप|तुम)\s+कैसे\s+(?:हैं|हो)", re.IGNORECASE),
    re.compile(r"क्या\s+हाल\s+है", re.IGNORECASE),
    re.compile(r"नमस्ते(?:\s+जी)?", re.IGNORECASE),
    re.compile(r"सब\s+ठीक\s+है", re.IGNORECASE),
    re.compile(r"भाई\s+क्या\s+कर\s+रहे\s+हो", re.IGNORECASE),
    # Gurmukhi greetings
    re.compile(r"ਤੁਸੀਂ\s+ਕਿਵੇਂ\s+ਹੋ", re.IGNORECASE),
    re.compile(r"ਕੀ\s+ਹਾਲ\s+ਹੈ", re.IGNORECASE),
    re.compile(r"ਕਿਵੇਂ\s+ਹੋ\s+ਪਾਜੀ", re.IGNORECASE),
    re.compile(r"ਸਤਿ\s+ਸ਼੍ਰੀ\s+ਅਕਾਲ(?:\s+ਜੀ)?", re.IGNORECASE),
    re.compile(r"ਸਭ\s+ਠੀਕ\s+ਠਾਕ", re.IGNORECASE),
    # English greetings
    re.compile(r"\b(?:how\s+are\s+you|how's\s+it\s+going|good\s+morning|good\s+afternoon|good\s+evening)\b", re.IGNORECASE),
    re.compile(r"\b(?:hello|hi|hey)\b.*?\b(?:how\s+are\s+you|doing|today)\b", re.IGNORECASE),
)


class LanguageDetector:
    """
    Robust, script-aware language and dialect classifier for Indian English,
    Hindi, Hinglish, Punjabi, and Romanized Punjabi speech.
    """

    @classmethod
    def normalise(cls, text: str) -> str:
        """Lowercases and cleans extra whitespace while preserving all 3 alphabets."""
        if not text:
            return ""
        cleaned = re.sub(r"[^\w\s\u0900-\u097F\uA8E0-\uA8FF\u0A00-\u0A7F']", " ", text.lower())
        return re.sub(r"\s+", " ", cleaned).strip()

    @classmethod
    def detect(cls, text: str) -> LanguageDetectionResult:
        """
        Classifies input text into one of the 7 supported language categories:
        - english
        - hindi_devanagari
        - hinglish
        - punjabi_gurmukhi
        - punjabi_latin
        - hindi_mixed
        - punjabi_mixed
        (or unknown if empty/unintelligible).
        """
        raw_text = text or ""
        norm = cls.normalise(raw_text)

        if not norm:
            return LanguageDetectionResult(
                original_text=raw_text,
                normalized_text="",
                detected_language="unknown",
                detected_script="None",
                confidence=0.0,
                is_conversational=False,
                language_category="unknown",
            )

        has_devanagari = bool(DEVANAGARI_RE.search(norm))
        has_gurmukhi = bool(GURMUKHI_RE.search(norm))
        latin_words = [w.lower() for w in LATIN_WORDS_RE.findall(norm)]
        total_latin = len(latin_words)

        # Check conversational patterns
        is_conv = any(pat.search(raw_text) or pat.search(norm) for pat in CONVERSATIONAL_GREETING_PATTERNS)

        # -------------------------------------------------------------------
        # 1. Gurmukhi Script Processing
        # -------------------------------------------------------------------
        if has_gurmukhi:
            if total_latin >= 1:
                # E.g. "ਤੁਹਾਡਾ bank account block ਹੋ ਜਾਵੇਗਾ" or "ਆਪਣਾ OTP ਦੱਸੋ"
                return LanguageDetectionResult(
                    original_text=raw_text,
                    normalized_text=norm,
                    detected_language="punjabi_mixed",
                    detected_script="Mixed",
                    confidence=0.95,
                    is_conversational=is_conv,
                    language_category="Mixed Punjabi-English",
                    matched_markers=latin_words[:5],
                )
            else:
                return LanguageDetectionResult(
                    original_text=raw_text,
                    normalized_text=norm,
                    detected_language="punjabi_gurmukhi",
                    detected_script="Gurmukhi",
                    confidence=0.98,
                    is_conversational=is_conv,
                    language_category="Punjabi (Gurmukhi)",
                )

        # -------------------------------------------------------------------
        # 2. Devanagari Script Processing
        # -------------------------------------------------------------------
        if has_devanagari:
            if total_latin >= 1:
                # E.g. "कृपया अपना OTP verify करें"
                return LanguageDetectionResult(
                    original_text=raw_text,
                    normalized_text=norm,
                    detected_language="hindi_mixed",
                    detected_script="Mixed",
                    confidence=0.95,
                    is_conversational=is_conv,
                    language_category="Mixed Hindi-English",
                    matched_markers=latin_words[:5],
                )
            else:
                return LanguageDetectionResult(
                    original_text=raw_text,
                    normalized_text=norm,
                    detected_language="hindi_devanagari",
                    detected_script="Devanagari",
                    confidence=0.98,
                    is_conversational=is_conv,
                    language_category="Hindi (Devanagari)",
                )

        # -------------------------------------------------------------------
        # 3. Pure Latin Script Processing (English vs. Hinglish vs. Punjabi Latin)
        # -------------------------------------------------------------------
        if total_latin == 0:
            return LanguageDetectionResult(
                original_text=raw_text,
                normalized_text=norm,
                detected_language="unknown",
                detected_script="None",
                confidence=0.0,
                is_conversational=False,
                language_category="unknown",
            )

        punjabi_hits = [w for w in latin_words if w in PUNJABI_SPECIFIC_MARKERS]
        hinglish_hits = [w for w in latin_words if w in HINGLISH_MARKERS]

        punjabi_count = len(punjabi_hits)
        hinglish_count = len(hinglish_hits)

        # Direct bigram or key trigram checks for Punjabi Latin:
        # e.g., "tussi kive ho", "ki haal", "kise nu", "de naal"
        if any(w in norm for w in ("tussi kive", "tusi kive", "ki haal", "kidda paaji", "kise nu", "kise naal", "sat sri akaal", "tuhada account")):
            punjabi_count += 3

        # Direct check for Hinglish key phrases:
        # e.g., "aap kaise", "kya kar", "sab theek", "bata do", "bhej do", "mat dena"
        if any(w in norm for w in ("aap kaise", "kaise hai", "kaise ho", "kya kar", "mat dena", "bata do", "bhej do", "kisi ko", "kisi ke")):
            hinglish_count += 3

        # Classification decision based on marker dominance:
        if punjabi_count > 0 and punjabi_count >= hinglish_count:
            return LanguageDetectionResult(
                original_text=raw_text,
                normalized_text=norm,
                detected_language="punjabi_latin",
                detected_script="Latin",
                confidence=min(0.95, 0.75 + (punjabi_count / max(1, total_latin)) * 0.25),
                is_conversational=is_conv,
                language_category="Punjabi (Latin)",
                matched_markers=punjabi_hits,
            )

        if hinglish_count > 0:
            return LanguageDetectionResult(
                original_text=raw_text,
                normalized_text=norm,
                detected_language="hinglish",
                detected_script="Latin",
                confidence=min(0.95, 0.75 + (hinglish_count / max(1, total_latin)) * 0.25),
                is_conversational=is_conv,
                language_category="Hinglish (Latin)",
                matched_markers=hinglish_hits,
            )

        # Default to English
        return LanguageDetectionResult(
            original_text=raw_text,
            normalized_text=norm,
            detected_language="english",
            detected_script="Latin",
            confidence=0.92,
            is_conversational=is_conv,
            language_category="English",
        )


_detector_instance: Optional[LanguageDetector] = None


def get_language_detector() -> LanguageDetector:
    """Returns singleton LanguageDetector."""
    global _detector_instance
    if _detector_instance is None:
        _detector_instance = LanguageDetector()
    return _detector_instance
