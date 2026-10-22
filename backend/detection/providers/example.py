"""Example plug-ins: a working model to copy, and a way to test the sockets end to end.

A few English and romanized Hindi keywords, matched as plain substrings. This is NOT the
reviewed phrase list (resources/phrases.yaml, owned by the language speakers) and NOT a real
detector: don't run it at the demo. Select with PHRASE_ENGINE=example and DETECTOR_PROVIDER=example.
"""

from __future__ import annotations

from ..adapter import PluginOptions, detector, phrase_engine
from ..schemas import Assessment, AssessmentContext, PhraseHit, Turn

# Checked in this order; the first request type that matches wins.
REQUESTS: dict[str, tuple[str, ...]] = {
    "remote_access": ("anydesk", "teamviewer", "quicksupport", "share your screen", "screen share", "install this app", "download this app"),
    "otp_share": ("otp", "one time password", "verification code", "code you received", "code batao"),
    "pin_receive": ("upi pin", "enter your pin", "pin daalo"),
    "qr_receive": ("scan the qr", "scan this qr", "qr scan", "scan kar"),
}

SIGNALS: dict[str, tuple[str, ...]] = {
    "authority_impersonation": ("from your bank", "bank se", "rbi", "customer care", "police", "income tax"),
    "account_suspension_threat": ("account will be blocked", "account blocked", "suspended", "kyc expired", "block ho"),
    "coercive_threat": ("arrest", "legal action", "immediately", "right now", "turant"),
    "financial_solicitation": ("send money", "transfer", "refund", "cashback", "receive money", "paisa"),
}

# The request itself is also a chip.
REQUEST_SIGNAL = {
    "remote_access": "remote_access",
    "otp_share": "otp_or_pin_request",
    "pin_receive": "otp_or_pin_request",
    "qr_receive": "financial_solicitation",
}


def _request_in(text: str) -> str | None:
    low = text.lower()
    return next((kind for kind, words in REQUESTS.items() if any(w in low for w in words)), None)


def _signals_in(texts: list[str], request: str | None) -> tuple[str, ...]:
    low = " ".join(texts).lower()
    found = [name for name, words in SIGNALS.items() if any(w in low for w in words)]
    if request is not None:
        found.insert(0, REQUEST_SIGNAL[request])
    return tuple(dict.fromkeys(found))


@phrase_engine("example")
class ExamplePhrases:
    def __init__(self, options: PluginOptions) -> None:
        pass

    def match(self, turn: Turn) -> PhraseHit | None:
        request = _request_in(turn.text)
        if request is None:
            return None
        return PhraseHit(request_type=request, signals=_signals_in([turn.text], request))


@detector("example")
class ExampleDetector:
    def __init__(self, options: PluginOptions) -> None:
        pass

    async def assess(self, context: AssessmentContext) -> Assessment:
        finals = [t for t in context.turns if t.final]
        hits = [(t.turn_id, _request_in(t.text)) for t in finals]
        hits = [(turn_id, kind) for turn_id, kind in hits if kind is not None]
        if not hits:
            return Assessment(request_type="none", confidence="medium")
        turn_id, request = hits[-1]
        return Assessment(
            request_type=request,
            confidence="high",
            evidence_turn_ids=(turn_id,),
            signals=_signals_in([t.text for t in finals], request),
        )
