"""
Pydantic schemas for optional Telegram Bot Integration, Alert Payloads,
and Webhook Command Interfaces.
"""
from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional
from app.core.compat import BaseModel, Field
from app.schemas.analysis import RiskLevelType

TelegramServiceStatus = Literal["CONNECTED", "NOT_CONFIGURED", "DISABLED", "DELIVERY_FAILED", "UNAUTHORIZED"]


class TelegramStatusResponse(BaseModel):
    """Response returned by GET /telegram/status."""

    configured: bool
    enabled: bool
    status: TelegramServiceStatus
    bot_username: Optional[str] = None
    chat_id_configured: bool = False
    alert_threshold: str = "HIGH"
    total_alerts_sent: int = 0
    last_alert_timestamp: Optional[float] = None
    last_error: Optional[str] = None
    call_control_limitation: str = (
        "Telephony Limitation: Web and Telegram alerts cannot terminate or mute carrier-level "
        "cellular GSM calls. Users must manually disconnect using their native phone dialer."
    )


class TelegramSendAlertRequest(BaseModel):
    """Request payload to manually trigger or test a Telegram alert."""

    call_id: str = Field(default="test_call_001")
    risk_level: RiskLevelType = "CRITICAL"
    risk_score: float = Field(default=85.0, ge=0.0, le=100.0)
    headline: str = "Critical Payment Scam Warning"
    safe_action: str = "Hang up immediately. Never share any OTP or scan unverified QR codes."
    detected_categories: List[str] = Field(default_factory=lambda: ["OTP_OR_PIN_REQUEST"])


class TelegramSendAlertResponse(BaseModel):
    """Result of attempting to dispatch a Telegram alert."""

    delivered: bool
    message_id: Optional[int] = None
    status: TelegramServiceStatus
    detail: str
    call_id: str


class TelegramFromUser(BaseModel):
    """Telegram user model inside Webhook Message."""

    id: int
    is_bot: bool = False
    first_name: Optional[str] = None
    username: Optional[str] = None


class TelegramChat(BaseModel):
    """Telegram chat model."""

    id: int
    type: str = "private"
    title: Optional[str] = None
    username: Optional[str] = None


class TelegramMessage(BaseModel):
    """Telegram message model."""

    message_id: int
    from_user: Optional[TelegramFromUser] = Field(default=None, alias="from")
    chat: TelegramChat
    text: Optional[str] = None
    voice: Optional[Dict[str, Any]] = None
    audio: Optional[Dict[str, Any]] = None
    date: int = 0


class TelegramWebhookUpdate(BaseModel):
    """Incoming update from Telegram Bot API via webhook."""

    update_id: int
    message: Optional[TelegramMessage] = None


class TelegramCommandResponse(BaseModel):
    """Response returned after processing a webhook command."""

    handled: bool
    command: Optional[str] = None
    reply_text: Optional[str] = None
    authorized: bool = True
