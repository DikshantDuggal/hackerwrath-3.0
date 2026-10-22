"""English starter patterns. Language coverage must be evaluated before live use."""
import re

from edgerunners_contracts import RequestType

_PATTERNS = {
    RequestType.OTP_SHARE: re.compile(
        r"\b(?:read|tell|give|share|send) (?:me |us )?(?:your |the )?"
        r"(?:otp|verification code|code you (?:just )?received)\b", re.I
    ),
    RequestType.PIN_RECEIVE: re.compile(
        r"\benter (?:your |the )?(?:upi )?pin to receive\b", re.I
    ),
    RequestType.QR_RECEIVE: re.compile(
        r"\bscan (?:my |our |this |the )?(?:payment )?qr (?:code )?to receive\b", re.I
    ),
}
_NEGATION = re.compile(r"\b(?:never|do not|don't|dont|must not|should not)\b", re.I)


def advisories(text: str) -> set[RequestType]:
    """Return possible-risk candidates only; never authorize call control."""
    hits = set()
    for clause in re.split(r"[.!?;\n]", text):
        if not _NEGATION.search(clause):
            hits.update(kind for kind, pattern in _PATTERNS.items() if pattern.search(clause))
    return hits
