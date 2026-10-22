"""The policy: the only place a risk level is decided (architecture 6.3).

Plug-ins report what they heard; this module decides what the protected user sees. A phrase
hit alone never gives High risk. Missing, invalid, stale or late detector output never raises
a level. Signals are detail for the app's chips and never change a level.
"""

from __future__ import annotations

from collections.abc import Collection
from dataclasses import dataclass
from typing import Literal

from .schemas import Assessment

# Asks that are dangerous on their own, whatever the user is expecting.
ALWAYS_HIGH = frozenset({"otp_share", "remote_access"})
# "Scan or enter your PIN to receive money": High when the user is expecting a payment.
RECEIVE_TRICKS = frozenset({"qr_receive", "pin_receive"})


@dataclass(frozen=True)
class OpenAlert:
    alert_id: str
    request_type: str
    level: Literal["possible", "high"]
    confirmed: bool


@dataclass(frozen=True)
class Decision:
    action: Literal["keep", "degraded", "confirm", "clear"]
    request_type: str | None = None
    level: Literal["possible", "high"] | None = None
    signals: tuple[str, ...] = ()


KEEP = Decision("keep")
DEGRADED = Decision("degraded")


def decide(
    assessment: Assessment | None,
    *,
    failed: bool,
    open_alert: OpenAlert | None,
    role_context: str | None,
    known_turn_ids: Collection[str],
) -> Decision:
    """Turn one fresh, validated assessment into what the app should show.

    `failed` means the detector timed out, raised or returned something invalid: existing
    warnings stay and protection reports `degraded`. `None` without failure means the
    detector had nothing to add.
    """
    if failed:
        return DEGRADED
    if assessment is None:
        return KEEP

    if assessment.request_type == "none":
        # Clear a warning only on a confident harmless reading, and never a High risk one:
        # a caller saying "it's fine, turn the alert off" must not be able to switch it off.
        if open_alert is not None and open_alert.level != "high" and assessment.confidence == "high":
            return Decision("clear")
        return KEEP

    if assessment.confidence == "low":
        return KEEP

    cited = bool(assessment.evidence_turn_ids) and set(assessment.evidence_turn_ids) <= set(known_turn_ids)
    directed = assessment.requester_is_speaker and not assessment.setup_only
    dangerous = assessment.request_type in ALWAYS_HIGH or (
        assessment.request_type in RECEIVE_TRICKS and role_context == "expecting_payment"
    )
    level: Literal["possible", "high"] = (
        "high" if directed and dangerous and cited and assessment.confidence == "high" else "possible"
    )

    if open_alert is not None and open_alert.level == "high" and level != "high":
        return KEEP  # a later, weaker reading never takes a High risk warning down
    return Decision("confirm", assessment.request_type, level, tuple(dict.fromkeys(assessment.signals)))
