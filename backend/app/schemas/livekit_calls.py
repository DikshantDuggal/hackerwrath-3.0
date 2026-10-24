"""
LiveKit Internet Calling & Room Management Pydantic Schemas.
Models the complete call lifecycle: CREATED -> RINGING -> ACCEPTED -> ACTIVE -> ENDED / REJECTED.
"""
from __future__ import annotations

import time
from typing import Any, Dict, List, Literal, Optional
from app.core.compat import BaseModel, Field

LiveKitCallStatus = Literal[
    "CREATED",
    "RINGING",
    "ACCEPTED",
    "ACTIVE",
    "REJECTED",
    "ENDED",
    "FAILED",
]


class CallStartRequest(BaseModel):
    """Payload to initiate a new LiveKit internet call."""

    recipient_id: str = Field(min_length=1, description="Target recipient username or user ID")
    caller_id: Optional[str] = Field(default=None, description="Initiating caller username or user ID")
    language_code: str = Field(default="auto", description="Primary or auto speech language")
    enable_scam_detection: bool = Field(default=True, description="Enable AI real-time scam call analysis")


class CallStartResponse(BaseModel):
    """Response returned upon successful creation of a LiveKit call and room."""

    call_id: str
    room_id: str
    caller_id: str
    recipient_id: str
    status: LiveKitCallStatus
    created_at: float
    ai_detection_active: bool = True
    consent_notice: str = (
        "AI-assisted scam call analysis is active for safety on this call. "
        "Participant speech is transcribed and evaluated in real time for fraud detection."
    )


class CallActionRequest(BaseModel):
    """Payload for call lifecycle transitions (accept, reject, end)."""

    user_id: Optional[str] = Field(default=None, description="Authenticated requesting user ID")
    reason: Optional[str] = Field(default=None, description="Optional cancellation or rejection reason")


class CallActionResponse(BaseModel):
    """Response returned upon state transition (accept, reject, end)."""

    call_id: str
    status: LiveKitCallStatus
    updated_at: float
    message: str


class CallTokenRequest(BaseModel):
    """Request to generate an authorized participant token for a LiveKit room."""

    user_id: Optional[str] = Field(default=None, description="Requesting user ID")
    ttl_seconds: Optional[int] = Field(default=None, description="Optional custom token TTL")


class CallTokenResponse(BaseModel):
    """Signed LiveKit participant token and connection parameters."""

    token: str
    server_url: str
    room_id: str
    participant_identity: str
    participant_name: str
    expires_in_seconds: int
    ai_notice: str = (
        "Notice: EdgeRunner AI Guardian is active in this room. "
        "Audio is analyzed independently per participant for scam warning protection."
    )


class LiveKitCallDetail(BaseModel):
    """Detailed metadata and audit posture for an ongoing or completed LiveKit call."""

    call_id: str
    room_id: str
    caller_id: str
    recipient_id: str
    status: LiveKitCallStatus
    created_at: float
    accepted_at: Optional[float] = None
    started_at: Optional[float] = None
    ended_at: Optional[float] = None
    language_code: str = "auto"
    ai_detection_active: bool = True
    participants: List[str] = Field(default_factory=list)
    final_risk_score: Optional[float] = None
    final_risk_level: Optional[str] = None
    indicators_count: int = 0
