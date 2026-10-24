"""
Mobile App Support Endpoints:
Provides authentication, voice tokens, user settings, call actions, demo call triggers,
and the real-time /ws/app WebSocket bridge matching the Android client contract (ApiClient.kt / EventsSocket.kt).
"""
from __future__ import annotations

import asyncio
import time
import uuid
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.core.compat import APIRouter, WebSocket, WebSocketDisconnect
from app.core.logging import get_logger
from app.services.live_audio_processor import get_broadcaster

logger = get_logger("scam_detector.mobile_api")

router = APIRouter(prefix="/api", tags=["mobile"])
ws_router = APIRouter(tags=["mobile_ws"])


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
_user_settings: Dict[str, SettingsDto] = {}
_active_demo_tasks: Dict[str, asyncio.Task] = {}


@router.post("/login", response_model=LoginResponse)
async def login(req: LoginRequest) -> LoginResponse:
    user_id = req.username.strip() or "demo_user"
    token = f"app_token_{user_id}_{int(time.time())}"
    logger.info("Mobile login successful for user '%s'", user_id)
    return LoginResponse(app_token=token, user_id=f"u_{user_id}")


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
    broadcaster = get_broadcaster()
    action_type = req.action.lower()

    if action_type in ("hang_up", "end"):
        # Cancel any active simulated demo task
        task = _active_demo_tasks.pop(call_id, None)
        if task and not task.done():
            task.cancel()
        await broadcaster.broadcast({
            "v": 1,
            "type": "call_ended",
            "call_id": call_id,
            "event_seq": 99,
            "reason": "user_hung_up",
        })
    elif action_type in ("dismiss", "clear"):
        await broadcaster.broadcast({
            "v": 1,
            "type": "cleared",
            "call_id": call_id,
            "event_seq": 98,
            "assessment_revision": 99,
            "alert_id": f"alert_cleared_{call_id}",
        })

    return ActionResponse(ok=True, call_state=f"ACTION_{req.action.upper()}_ACKNOWLEDGED")


async def _run_demo_scenario(call_id: str, scenario: str) -> None:
    """Asynchronous workflow executing a realistic scam-call alert progression for mobile demos."""
    broadcaster = get_broadcaster()
    seq = 1
    try:
        # Step 1: Call Started
        await asyncio.sleep(0.5)
        await broadcaster.broadcast({
            "v": 1,
            "type": "call_started",
            "call_id": call_id,
            "event_seq": seq,
            "from_number": "+91 98765 43210",
            "demo": True,
        })
        seq += 1

        # Step 2: Monitoring status
        await asyncio.sleep(1.5)
        await broadcaster.broadcast({
            "v": 1,
            "type": "status",
            "call_id": call_id,
            "event_seq": seq,
            "state": "monitoring",
            "reason": None,
        })
        seq += 1

        # Step 3: First Warning (suspicious intent detected)
        await asyncio.sleep(2.0)
        req_type = "otp" if "bank" in scenario or "otp" in scenario else "gift_card"
        signals = ["otp", "urgency"] if req_type == "otp" else ["urgency", "financial_threat"]
        alert_id = f"alert_{uuid.uuid4().hex[:6]}"

        await broadcaster.broadcast({
            "v": 1,
            "type": "first_warning",
            "call_id": call_id,
            "event_seq": seq,
            "assessment_revision": 1,
            "alert_id": alert_id,
            "request_type": req_type,
            "signals": signals,
        })
        seq += 1

        # Step 4: Confirmed High Risk Alert
        await asyncio.sleep(1.5)
        await broadcaster.broadcast({
            "v": 1,
            "type": "confirmed",
            "call_id": call_id,
            "event_seq": seq,
            "assessment_revision": 2,
            "alert_id": alert_id,
            "request_type": req_type,
            "level": "high",
            "signals": signals + ["impersonation"],
        })
        seq += 1

        # Step 5: Active call monitoring heartbeats every 2.5s for 25s
        for _ in range(10):
            await asyncio.sleep(2.5)
            await broadcaster.broadcast({
                "v": 1,
                "type": "status",
                "call_id": call_id,
                "event_seq": seq,
                "state": "monitoring",
                "reason": None,
            })
            seq += 1

        # Step 6: Natural end after duration if user didn't hang up
        await broadcaster.broadcast({
            "v": 1,
            "type": "call_ended",
            "call_id": call_id,
            "event_seq": seq,
            "reason": "caller_hung_up",
        })
    except asyncio.CancelledError:
        logger.info("Demo scenario for call '%s' cancelled by user action", call_id)
    except Exception as exc:
        logger.warning("Error running demo scenario for call '%s': %s", call_id, exc)
    finally:
        _active_demo_tasks.pop(call_id, None)


@router.post("/demo/calls", response_model=DemoCallResponse)
async def trigger_demo_call(req: DemoCallRequest) -> DemoCallResponse:
    demo_call_id = f"demo_call_{uuid.uuid4().hex[:8]}"
    logger.info("Triggering demo call '%s' with scenario '%s'", demo_call_id, req.scenario)
    task = asyncio.create_task(_run_demo_scenario(demo_call_id, req.scenario))
    _active_demo_tasks[demo_call_id] = task
    return DemoCallResponse(call_id=demo_call_id)


@ws_router.websocket("/ws/app")
async def websocket_mobile_app(websocket: WebSocket) -> None:
    """
    Primary WebSocket connection endpoint for EdgeRunner Guardian Android mobile client.
    Handles auth handshake, delivers Ready event, and streams live fraud detection events.
    """
    await websocket.accept()
    broadcaster = get_broadcaster()
    broadcaster.register(websocket)
    logger.info("Android client WebSocket connected to /ws/app")

    try:
        # 1. Await auth handshake frame from client
        try:
            auth_data = await asyncio.wait_for(websocket.receive_json(), timeout=10.0)
            token = auth_data.get("app_token", "")
            logger.info("Android client authenticated with token: %s", token[:15] + "...")
        except Exception:
            logger.warning("Android client auth frame timed out or malformed; continuing in demo mode")

        # 2. Immediately send v1 Ready event to activate shield and turn status green
        await websocket.send_json({"v": 1, "type": "ready"})
        logger.info("Sent Ready event to Android client; warning service active")

        # 3. Keep connection open, handle heartbeats
        while True:
            msg = await websocket.receive_text()
            if msg:
                try:
                    import json
                    parsed = json.loads(msg)
                    if parsed.get("type") == "ping":
                        await websocket.send_json({"type": "pong"})
                except Exception:
                    pass
    except (WebSocketDisconnect, RuntimeError):
        logger.info("Android client /ws/app disconnected cleanly")
    except Exception as exc:
        logger.warning("Android client /ws/app connection error: %s", exc)
    finally:
        broadcaster.unregister(websocket)
