"""Canonical wire contracts; generate JSON Schema and Kotlin with make contracts."""
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class RequestType(StrEnum):
    QR_RECEIVE = "qr_receive"
    PIN_RECEIVE = "pin_receive"
    OTP_SHARE = "otp_share"
    NONE = "none"


class ProtectionState(StrEnum):
    STARTING = "starting"
    MONITORING = "monitoring"
    POSSIBLE_RISK = "possible_risk"
    HIGH_RISK = "high_risk"
    UNAVAILABLE = "protection_unavailable"


class WarningLevel(StrEnum):
    POSSIBLE = "possible"
    HIGH = "high"


class EventType(StrEnum):
    ADVISORY = "advisory"
    CONFIRMED = "confirmed"


class WarningEvent(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    v: Literal[1] = 1
    call_id: str = Field(min_length=1, max_length=128)
    event_seq: int = Field(ge=1)
    assessment_revision: int = Field(ge=1)
    type: EventType
    alert_id: str = Field(min_length=1, max_length=128)
    request_type: RequestType
    level: WarningLevel


class Assessment(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    request_type: RequestType
    confidence: Literal["low", "medium", "high"]
    setup_only: bool
    requester_is_speaker: bool
    evidence_turn_ids: list[str] = Field(min_length=1, max_length=20)
