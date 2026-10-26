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

class MessageAnalysisRequest(BaseModel):
    text: str
    source: Optional[str] = "telegram"
    language_code: Optional[str] = "auto"


class MessageAnalysisResponse(BaseModel):
    id: str
    timestamp: float
    original_text: str
    normalized_text: str
    detected_language: str
    detected_script: str
    risk_score: float
    risk_level: str
    headline: str
    safe_action: str
    signals: List[str]
    protective_advice: bool
    is_conversational: bool


class SystemStatusResponse(BaseModel):
    backend_online: bool = True
    service: str = "EdgeRunner Guardian"
    version: str = "1.0.0"
    telegram_configured: bool = False
    telegram_status: str = "DISCONNECTED"
    telegram_bot_username: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    stt_working: bool = True
    stt_model: str = "saaras:v3"
    rules_engine_working: bool = True
    icfd_model_working: bool = True
    contextual_ai_working: bool = True
    total_messages_analyzed: int = 0
    active_alerts_count: int = 0

_analyzed_messages: List[Dict[str, Any]] = []



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




@router.get("/system/status", response_model=SystemStatusResponse)
async def get_system_status() -> SystemStatusResponse:
    from app.core.config import get_settings
    from app.services.telegram_service import get_telegram_service
    from app.detectors.icfd_classifier import get_icfd_classifier
    settings = get_settings()
    tg_service = get_telegram_service()
    tg_status = tg_service.get_status()
    icfd = get_icfd_classifier()
    
    return SystemStatusResponse(
        backend_online=True,
        service=settings.app_name,
        version=settings.app_version,
        telegram_configured=tg_status.configured,
        telegram_status=tg_status.status,
        telegram_bot_username=tg_status.bot_username,
        telegram_chat_id=settings.telegram_chat_id if tg_status.chat_id_configured else None,
        stt_working=True,
        stt_model=settings.sarvam_stt_model,
        rules_engine_working=True,
        icfd_model_working=icfd.available,
        contextual_ai_working=True,
        total_messages_analyzed=len(_analyzed_messages),
        active_alerts_count=tg_status.total_alerts_sent,
    )


@router.post("/messages/analyze", response_model=MessageAnalysisResponse)
async def analyze_message(req: MessageAnalysisRequest) -> MessageAnalysisResponse:
    from app.api.routes_analysis import get_conversation_manager
    from app.schemas.analysis import TranscriptAnalysisRequest
    from app.services.telegram_service import get_telegram_service
    from app.detectors.sensitive_info_detector import get_sensitive_info_detector

    clean_text = req.text.strip()
    if not clean_text:
        from app.core.compat import HTTPException
        raise HTTPException(status_code=422, detail="Message text must not be empty.")

    msg_id = f"msg_{uuid.uuid4().hex[:8]}"
    now_ts = time.time()
    
    conv_manager = get_conversation_manager()
    analysis_req = TranscriptAnalysisRequest(
        transcript=clean_text,
        language_code=req.language_code or "auto",
        call_id=msg_id,
    )
    assessment = conv_manager.analyze_standalone_transcript(analysis_req)
    is_protective = get_sensitive_info_detector().detect(clean_text).is_protective_warning

    if assessment.risk_level in ("HIGH", "CRITICAL") and not is_protective:
        try:
            tg_svc = get_telegram_service()
            if tg_svc.is_configured and tg_svc.is_enabled:
                tg_svc.send_risk_alert(assessment, msg_id)
        except Exception as exc:
            logger.warning("Telegram alert dispatch error: %s", exc)

    from app.services.language_detector import get_language_detector
    lang_info = get_language_detector().detect(clean_text)

    resp = MessageAnalysisResponse(
        id=msg_id,
        timestamp=now_ts,
        original_text=clean_text,
        normalized_text=assessment.normalized_text or lang_info.normalized_text,
        detected_language=assessment.detected_language or lang_info.detected_language,
        detected_script=assessment.detected_script or lang_info.detected_script,
        risk_score=assessment.risk_score,
        risk_level=assessment.risk_level,
        headline=assessment.caption,
        safe_action=assessment.recommended_action,
        signals=assessment.reasons if assessment.reasons else [e.category for e in assessment.evidence],
        protective_advice=is_protective,
        is_conversational=lang_info.is_conversational,
    )

    _analyzed_messages.insert(0, resp.model_dump())
    if len(_analyzed_messages) > 50:
        _analyzed_messages.pop()

    try:
        broadcaster = get_broadcaster()
        asyncio.create_task(broadcaster.broadcast({
            "v": 1,
            "type": "message_analyzed",
            "message_id": msg_id,
            "risk_level": assessment.risk_level,
            "risk_score": assessment.risk_score,
            "detected_language": assessment.detected_language,
            "detected_script": assessment.detected_script,
            "headline": assessment.caption,
            "safe_action": assessment.recommended_action,
            "protective_advice": is_protective,
        }))
    except Exception:
        pass

    return resp


@router.get("/messages/history", response_model=List[MessageAnalysisResponse])
async def get_message_history() -> List[MessageAnalysisResponse]:
    return [MessageAnalysisResponse(**m) for m in _analyzed_messages]


@router.delete("/messages/history")
async def clear_message_history() -> Dict[str, Any]:
    _analyzed_messages.clear()
    return {"ok": True, "cleared": True}


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
