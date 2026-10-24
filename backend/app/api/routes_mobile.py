"""
Mobile App Support Endpoints:
Provides authentication, voice tokens, user settings, call actions, and demo call triggers
matching the Android client contract (ApiClient.kt).
"""
from __future__ import annotations

import time
import uuid
from typing import Optional
from pydantic import BaseModel, Field
from app.core.compat import APIRouter

router = APIRouter(prefix="/api", tags=["mobile"])


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    app_token: str
    user_id: str


class VoiceTokenResponse(BaseModel):
    voice_token: str
    identity: str


class SettingsDto(BaseModel):
    scam_check: bool = True
    lang: str = "hi"
    role_context: Optional[str] = "general"


class ActionRequest(BaseModel):
    action: str
    request_type: Optional[str] = None


class ActionResponse(BaseModel):
    ok: bool = True
    call_state: str = "PROCESSED"


class DemoCallRequest(BaseModel):
    scenario: str = "bank_fraud"


class DemoCallResponse(BaseModel):
    call_id: str


# In-memory settings storage per user
_user_settings: dict[str, SettingsDto] = {}


@router.post("/login", response_model=LoginResponse)
async def login(req: LoginRequest) -> LoginResponse:
    user_id = req.username.strip() or "demo_user"
    token = f"app_token_{user_id}_{int(time.time())}"
    return LoginResponse(app_token=token, user_id=user_id)


@router.post("/voice-token", response_model=VoiceTokenResponse)
async def voice_token() -> VoiceTokenResponse:
    return VoiceTokenResponse(
        voice_token=f"vtoken_{uuid.uuid4().hex[:12]}",
        identity="mobile_client",
    )


@router.get("/settings", response_model=SettingsDto)
async def get_settings() -> SettingsDto:
    return _user_settings.get("default", SettingsDto())


@router.put("/settings", response_model=SettingsDto)
async def update_settings(settings: SettingsDto) -> SettingsDto:
    _user_settings["default"] = settings
    return settings


@router.post("/calls/{call_id}/actions", response_model=ActionResponse)
async def call_action(call_id: str, req: ActionRequest) -> ActionResponse:
    return ActionResponse(ok=True, call_state=f"ACTION_{req.action.upper()}_ACKNOWLEDGED")


@router.post("/demo/calls", response_model=DemoCallResponse)
async def trigger_demo_call(req: DemoCallRequest) -> DemoCallResponse:
    demo_call_id = f"demo_call_{uuid.uuid4().hex[:8]}"
    return DemoCallResponse(call_id=demo_call_id)
