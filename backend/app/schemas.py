"""Request and response bodies."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class LoginIn(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)


class LoginOut(BaseModel):
    app_token: str
    user_id: str


class VoiceTokenOut(BaseModel):
    voice_token: str
    identity: str


class SettingsBody(BaseModel):
    scam_check: bool
    lang: Literal["en", "hi", "pa"]
    role_context: Literal["expecting_payment"] | None = None


class ActionIn(BaseModel):
    action: Literal["answer", "end", "continue", "hold", "resume", "report", "decline"]
    request_type: Literal["qr_receive", "pin_receive", "otp_share", "remote_access"] | None = None


class ActionOut(BaseModel):
    ok: bool
    call_state: str


class DemoCallIn(BaseModel):
    scenario: Literal["qr_scan", "otp", "remote_access", "harmless", "unavailable", "detector"] = "qr_scan"


class DemoCallOut(BaseModel):
    call_id: str
