"""
Context-Aware Sensitive-Information Detector.

Identifies requests for sensitive authentication and banking credentials
(OTPs, PINs, UPI PINs, passwords, CVVs, credentials, authorization codes)
across English, Hindi (Devanagari & Romanized), and Punjabi (Gurmukhi & Romanized).

Crucially distinguishes between:
1. DIRECT SOLICITATION: Asking the user to disclose, read out, enter, or send credentials.
2. PROTECTIVE WARNINGS: Warning the user NEVER to share OTPs/PINs.
3. EDUCATIONAL DISCUSSIONS: General awareness/fraud discussion without an active attack.
4. QUOTED / REPORTED SPEECH: Relating what a past suspicious caller asked for.
5. BENIGN SYSTEM NOTIFICATIONS: Automated OTP delivery or self-service app instructions.
"""
from __future__ import annotations

import re
from typing import List, Optional
from app.core.compat import BaseModel, Field


class SensitiveInfoDetectionResult(BaseModel):
    """Structured result of sensitive information and credential solicitation detection."""

    has_sensitive_mention: bool = False
    is_solicitation: bool = False
    is_protective_warning: bool = False
    is_educational_discussion: bool = False
    is_quoted_speech: bool = False
    is_benign_notification: bool = False
    category: Optional[str] = None  # e.g., "OTP_SOLICITATION", "PIN_SOLICITATION", "CREDENTIAL_SOLICITATION"
    target_items: List[str] = Field(default_factory=list)  # e.g., ["OTP", "UPI_PIN"]
    matched_phrases: List[str] = Field(default_factory=list)
    counter_evidence: List[str] = Field(default_factory=list)
    evidence_excerpts: List[str] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    explanation: str = ""


# ---------------------------------------------------------------------------
# REGEX DEFINITIONS
# ---------------------------------------------------------------------------

# Sensitive credential tokens across English, Romanized Hindi/Punjabi, Devanagari, and Gurmukhi
REGEX_SENSITIVE_TOKENS = re.compile(
    r"\b("
    r"otp|one[- ]time[- ]password|passcode|verification[- ]code|verification\s+code|auth[- ]code|authentication[- ]code|authentication\s+code|"
    r"6[- ]digit[- ]code|4[- ]digit[- ]code|security[- ]code|secret[- ]code|"
    r"pin|upi[- ]pin|atm[- ]pin|mpin|banking[- ]pin|"
    r"password|passwords|login[- ]credentials|credentials|cvv|cvv[- ]number|"
    r"bank[- ]details|card[- ]details|account[- ]details|net[- ]banking[- ]password"
    r")\b|"
    r"(?:"
    r"ओटीपी|वन[- ]टाइम[- ]पासवर्ड|पिन|यूपीआई[- ]पिन|पासवर्ड|सीवीवी|सत्यापन[- ]कोड|सुरक्षा[- ]कोड|गोपनीय[- ]कोड|खाता[- ]विवरण|"
    r"ਓਟੀਪੀ|ਪਿੰਨ|ਯੂਪੀਆਈ[- ]ਪਿੰਨ|ਪਾਸਵਰਡ|ਸੀਵੀਵੀ|ਗੁਪਤ[- ]ਕੋਡ"
    r")",
    re.IGNORECASE,
)

# Protective / Negation patterns indicating advice NOT to share credentials
REGEX_PROTECTIVE = re.compile(
    r"\b("
    r"never\s+(?:share|give|tell|disclose|enter|send)|"
    r"do\s+not\s+(?:share|give|tell|disclose|enter|send)|"
    r"don'?t\s+(?:share|give|tell|disclose|enter|send)|"
    r"(?:will\s+)?never\s+ask\s+(?:for\s+)?(?:your\s+)?(?:otp|pin|password|code)|"
    r"bank\s+(?:employees?\s+)?never\s+ask|"
    r"kabhi\s+(?:bhi\s+)?(?:kisi\s+ko\s+|kise?\s+nu\s+)?(?:bhi\s+)?(?:apna\s+)?(?:otp|pin|password|code)?\s*(?:mat|na)\s+(?:batana|batao|dena|do|dasso|daso|deo|devo|share|karna)|"
    r"kisi\s+ko\s+(?:bhi\s+)?(?:apna\s+)?(?:otp|pin|password|code)?\s*mat\s+(?:batana|batao|dena|do|share|karna)|"
    r"kisi\s+ke\s+(?:saath|sath)\s+(?:bhi\s+)?(?:apna\s+)?(?:otp|pin|password|code)?\s*(?:share\s+)?mat\s+(?:karna|karein|karo|kijiye|share)|"
    r"kisi\s+se\s+(?:bhi\s+)?(?:apna\s+)?(?:otp|pin|password|code)?\s*(?:share\s+)?mat\s+(?:karna|karein|karo|kijiye|share)|"
    r"share\s+mat\s+(?:karna|karein|karo|kijiye)|"
    r"share\s+na\s+(?:karein|karna|karo)|"
    r"mat\s+share\s+(?:karna|karo|karein)|"
    r"kabhi\s+(?:bhi\s+)?share\s+mat|"
    r"(?:apna\s+)?(?:otp|pin|password|code)\s+(?:kisi\s+ko\s+|kisi\s+ke\s+(?:saath|sath)\s+)?mat\s+(?:batana|batao|dena|do|dijiye|share|karna)|"
    r"(?:apna\s+)?(?:otp|pin|password|code)\s+(?:kisi\s+ko\s+|kise?\s+nu\s+)?na\s+(?:dasso|daso|deo|devo|diyo|do|dena|batao|share)|"
    r"kise?\s+nu\s+(?:vi|bhi)?\s*(?:apna\s+)?(?:otp|pin|password|code)?\s*na\s+(?:dasso|daso|deo|devo|diyo|do|dena|share|dasna|dassna|karna|karo)|"
    r"kisi\s+naal\s+(?:vi|bhi)?\s*(?:apna\s+)?(?:otp|pin|password|code)?\s*na\s+(?:dasso|daso|deo|devo|diyo|do|dena|share|karna|karo)|"
    r"bank\s+(?:kabhi|kade)\s+(?:bhi|vi)?\s*(?:otp|pin|password)\s+nahi\s+(?:maangta|mangda)|"
    r"warning\s*:\s*never\s+share|"
    r"avoid\s+sharing\s+(?:your\s+)?(?:otp|pin|password)"
    r")\b|"
    r"(?:"
    r"ओटीपी\s+मत\s+बताना|ओटीपी\s+साझा\s+न\s+करें|कभी\s+भी\s+ओटीपी\s+साझा\s+न\s+करें|पिन\s+मत\s+डालें|पासवर्ड\s+मत\s+बताएं|"
    r"बैंक\s+कभी\s+(?:भी\s+)?ओटीपी\s+नहीं\s+मांगता|किसी\s+को\s+(?:भी\s+)?(?:अपना\s+)?ओटीपी\s+मत\s+(?:दीजिए|दो|देना|बताएं|बताओ)|शेयर\s+मत\s+करना|साझा\s+मत\s+करें|"
    r"किसी\s+को\s+ओटीपी\s+मत\s+देना|ओटीपी\s+किसी\s+को\s+मत\s+देना|ओटीपी\s+मत\s+देना|"
    r"ਓਟੀਪੀ\s+ਨਾ\s+ਦੱਸੋ|ਓਟੀਪੀ\s+ਨਾ\s+ਦਿਓ|ਓਟੀਪੀ\s+ਕਿਸੇ\s+ਨੂੰ\s+ਨਾ\s+ਦਿਓ|ਕਿਸੇ\s+ਨੂੰ\s+(?:ਵੀ\s+)?(?:ਆਪਣਾ\s+)?ਓਟੀਪੀ\s+ਨਾ\s+(?:ਦੱਸੋ|ਦਿਓ|ਦੇਵੋ|ਸਾਂਝਾ)|"
    r"ਕਦੇ\s+ਵੀ\s+ਓਟੀਪੀ\s+ਸਾਂਝਾ\s+ਨਾ\s+ਕਰੋ|ਪਿੰਨ\s+ਨਾ\s+ਦੱਸੋ|ਬੈਂਕ\s+ਕਦੇ\s+ਵੀ\s+ਓਟੀਪੀ\s+ਨਹੀਂ\s+ਮੰਗਦਾ|ਸ਼ੇਅਰ\s+ਨਾ\s+ਕਰੋ"
    r")",
    re.IGNORECASE,
)

# Educational / Fraud discussion patterns (talking about scam techniques, not an active attack)
REGEX_EDUCATIONAL = re.compile(
    r"\b("
    r"(?:scammers?|fraudsters?|criminals?|hackers?|cyber\s+criminals?)\s+(?:often|usually|call|frequently|tend\s+to|try\s+to)\s+(?:ask|demand|seek|steal)|"
    r"(?:cases?\s+of|incidents?\s+of|awareness\s+about|preventing)\s+(?:otp|banking|cyber|online)\s+(?:fraud|scams?)|"
    r"(?:otp|banking|cyber)\s+fraud\s+(?:cases?|awareness|alert|workshop|seminar|session)|"
    r"people\s+(?:lose|lost)\s+money\s+(?:when|if)\s+they\s+share|"
    r"scam\s+callers?\s+(?:ask|demand|pretend)|"
    r"in\s+these\s+scams?,?\s+(?:they|callers?)\s+(?:ask|demand)|"
    r"dhokhadhadi\s+ke\s+cases|cyber\s+crime\s+se\s+bachein"
    r")\b",
    re.IGNORECASE,
)

# Quoted speech / Narrative reporting of past attempts ("The caller said 'give OTP' but I hung up")
REGEX_QUOTED_OR_REPORTED = re.compile(
    r"\b("
    r"(?:caller|someone|he|she)\s+(?:said|told\s+me|asked\s+me\s+to|demanded)\s+['\"]?.*?(?:otp|pin|code)|"
    r"usne\s+bola\s+(?:ki\s+)?['\"]?.*?(?:otp|pin|code)\s*(?:batao|do).*?maine\s+(?:phone\s+kaat|mana\s+kar|disconnect)|"
    r"(?:i|maine)\s+(?:hung\s+up|cut\s+the\s+call|refused|disconnected)\s+(?:when|jab)\s+(?:they|usne)\s+asked"
    r")\b",
    re.IGNORECASE,
)

# Benign system notification / self-service instruction patterns
REGEX_BENIGN_NOTIFICATION = re.compile(
    r"\b("
    r"your\s+otp\s+for\s+(?:logging|transaction|login|verification|booking|payment)\s+is|"
    r"your\s+one[- ]time\s+password\s+is\s+\d+|"
    r"is\s+your\s+secret\s+otp|"
    r"otp\s+has\s+been\s+sent\s+to\s+your\s+registered|"
    r"received\s+(?:an\s+)?otp\s+for\s+(?:my\s+)?(?:booking|ticket|order|delivery|login)|"
    r"enter\s+(?:the\s+)?otp\s+on\s+(?:the\s+)?official\s+(?:app|website|portal)|"
    r"enter\s+otp\s+in\s+your\s+banking\s+app"
    r")\b",
    re.IGNORECASE,
)

# Active solicitation verbs across languages
# (Requests asking the listener to disclose or enter credentials)
REGEX_SOLICITATION_VERBS = re.compile(
    r"\b("
    # English
    r"tell|give|share|enter|send|provide|read(?:\s+\w+)?\s+out|read|type|input|verify|confirm|disclose|"
    r"what\s+is|whats|forward|speak|mention|"
    # Hindi / Hinglish / Punjabi
    r"batao|bata|bataiye|bata\s+do|bata\s+de|batao\s+na|dasso|daso|das|dass|dass\s+do|das\s+do|dassiye|dasiye|"
    r"share\s+karo|share\s+karein|de\s+do|de\s+dijiye|deo|diyo|devo|dena|daalo|daal\s+do|daaliye|paao|paa\s+do|paa\s+diyo|"
    r"bhejo|bhej\s+do|bhejiye|likho|likh\s+do|bolo|boliye|chahiye|chahida|chahidi|mang\s+raha|"
    r"verify\s+karo|verify\s+karein|confirm\s+karo|confirm\s+karein|enter\s+karo"
    r")\b|"
    r"(?:"
    # Devanagari
    r"बताओ|बताइए|बताएं|बताएँ|बता\s+दो|दीजिए|दो|दें|डालो|डालें|डाल\s+दो|डालिए|भेजो|भेजें|भेजिए|लिखो|बोलो|बोलिए|चाहिए|साझा\s+करो|साझा\s+करें|वेरिफाई\s+करो|"
    # Gurmukhi
    r"ਦੱਸੋ|ਦੱਸ|ਦੱਸ\s+ਦਿਓ|ਦਿਓ|ਦੇਵੋ|ਪਾਓ|ਪਾ\s+ਦਿਓ|ਭੇਜੋ|ਸਾਂਝਾ\s+ਕਰੋ"
    r")",
    re.IGNORECASE,
)


class SensitiveInfoDetector:
    """
    Dedicated context-aware detector for sensitive authentication information.
    Distinguishes solicitations from protective advice, educational talks, and system alerts.
    """

    def detect(self, transcript: str) -> SensitiveInfoDetectionResult:
        """
        Analyses transcript for sensitive information mentions and determines context.
        """
        text = (transcript or "").strip()
        if not text:
            return SensitiveInfoDetectionResult()

        # Step 1: Detect presence of sensitive credential tokens
        sensitive_matches = REGEX_SENSITIVE_TOKENS.findall(text)
        # Normalize matches (extract non-empty match string)
        tokens_found = set()
        for m in sensitive_matches:
            if isinstance(m, tuple):
                for sub in m:
                    if sub.strip():
                        tokens_found.add(sub.strip().lower())
            elif isinstance(m, str) and m.strip():
                tokens_found.add(m.strip().lower())

        # If no sensitive token matches at all, check if Hindi/Punjabi keywords match directly
        if not tokens_found:
            for kw in ("ओटीपी", "पिन", "पासवर्ड", "ਸੀਵੀਵੀ", "ਓਟੀਪੀ", "ਪਿੰਨ"):
                if kw in text:
                    tokens_found.add(kw)

        if not tokens_found:
            return SensitiveInfoDetectionResult(has_sensitive_mention=False)

        target_items = sorted(list(tokens_found))

        # Step 2: Check for Protective Warning Context
        protective_match = REGEX_PROTECTIVE.search(text)
        if protective_match:
            matched_phrase = protective_match.group(0).strip()
            return SensitiveInfoDetectionResult(
                has_sensitive_mention=True,
                is_solicitation=False,
                is_protective_warning=True,
                target_items=target_items,
                matched_phrases=[matched_phrase],
                counter_evidence=[
                    f"Protective advice detected: '{matched_phrase}'. User or speaker is warning against sharing credentials."
                ],
                confidence=0.95,
                explanation="Protective security advice detected warning never to disclose credentials.",
            )

        # Step 3: Check for Educational / Fraud Discussion Context
        educational_match = REGEX_EDUCATIONAL.search(text)
        if educational_match:
            matched_phrase = educational_match.group(0).strip()
            return SensitiveInfoDetectionResult(
                has_sensitive_mention=True,
                is_solicitation=False,
                is_educational_discussion=True,
                target_items=target_items,
                matched_phrases=[matched_phrase],
                counter_evidence=[
                    f"Educational fraud awareness context: '{matched_phrase}'. General discussion of scam methods without active solicitation."
                ],
                confidence=0.88,
                explanation="General educational discussion about scam techniques rather than an active credential solicitation.",
            )

        # Step 4: Check for Quoted / Reported Speech Context
        quoted_match = REGEX_QUOTED_OR_REPORTED.search(text)
        if quoted_match:
            matched_phrase = quoted_match.group(0).strip()
            return SensitiveInfoDetectionResult(
                has_sensitive_mention=True,
                is_solicitation=False,
                is_quoted_speech=True,
                target_items=target_items,
                matched_phrases=[matched_phrase],
                counter_evidence=[
                    f"Quoted/reported speech: '{matched_phrase}'. Speaker is narrating a past interaction rather than an active request."
                ],
                confidence=0.85,
                explanation="Reported speech narrating a past suspicious caller rather than a live solicitation.",
            )

        # Step 5: Check for Benign System Notification / Self-Service Instruction
        benign_match = REGEX_BENIGN_NOTIFICATION.search(text)
        if benign_match:
            matched_phrase = benign_match.group(0).strip()
            return SensitiveInfoDetectionResult(
                has_sensitive_mention=True,
                is_solicitation=False,
                is_benign_notification=True,
                target_items=target_items,
                matched_phrases=[matched_phrase],
                counter_evidence=[
                    f"Benign notification/instruction: '{matched_phrase}'."
                ],
                confidence=0.90,
                explanation="Automated notification or official self-service instruction rather than an inbound solicitation.",
            )

        # Step 6: Check for Active Credential Solicitation
        # Look for combination of sensitive tokens and solicitation verbs
        verb_match = REGEX_SOLICITATION_VERBS.search(text)
        if verb_match:
            matched_verb = verb_match.group(0).strip()
            
            # Determine specific category
            category = "CREDENTIAL_SOLICITATION"
            if any("otp" in t or "one" in t or "ओटीपी" in t or "ਓਟੀਪੀ" in t or "code" in t for t in target_items):
                category = "OTP_SOLICITATION"
            elif any("pin" in t or "पिन" in t or "ਪਿੰਨ" in t for t in target_items):
                category = "PIN_SOLICITATION"
            elif any("password" in t or "पासवर्ड" in t or "ਪਾਸਵਰਡ" in t for t in target_items):
                category = "PASSWORD_SOLICITATION"

            return SensitiveInfoDetectionResult(
                has_sensitive_mention=True,
                is_solicitation=True,
                category=category,
                target_items=target_items,
                matched_phrases=[matched_verb, *target_items],
                evidence_excerpts=[text],
                confidence=0.94,
                explanation=(
                    f"Direct credential solicitation detected: speaker is requesting listener to disclose "
                    f"or verify sensitive authentication data ({', '.join(target_items)})."
                ),
            )

        # If sensitive token is mentioned without clear verb, it is an ambiguous mention
        return SensitiveInfoDetectionResult(
            has_sensitive_mention=True,
            is_solicitation=False,
            target_items=target_items,
            confidence=0.40,
            explanation=f"Sensitive term ({', '.join(target_items)}) mentioned without explicit solicitation verb or protective advice.",
        )


_detector_instance: Optional[SensitiveInfoDetector] = None


def get_sensitive_info_detector() -> SensitiveInfoDetector:
    """Singleton factory for SensitiveInfoDetector."""
    global _detector_instance
    if _detector_instance is None:
        _detector_instance = SensitiveInfoDetector()
    return _detector_instance
