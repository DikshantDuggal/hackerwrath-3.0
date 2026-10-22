"""
Real-Time Ingestion WebSocket & API for Telegram VoIP Voice Call Bridge.
Compatible with onfloor/apps/telegram-bridge (py-tgcalls + pyrogram).

Protocol:
1. Client connects to WS `/internal/live/ingest` with optional header `x-bridge-secret`.
2. Client sends JSON: `{"type": "call_started", "protocolVersion": 1, "telegramCallId": "...", "customer": {...}}`
   Server acknowledges: `{"type": "ack", "protocolVersion": 1, "callId": "..."}`
3. Client streams binary frames:
   - Byte 0: channel (0 = agent, 1 = customer / potential scammer)
   - Bytes 1-4: unsigned little-endian sample offset (uint32)
   - Bytes 5+: PCM16LE audio at 16kHz mono
4. Customer audio is buffered and transcribed via Sarvam Saaras / ConversationManager.
   Risk is evaluated in real-time, flagged keywords are identified, and protective alerts are dispatched.
5. Client sends JSON: `{"type": "call_ended", "reason": "telegram_hangup"}`
   Server acknowledges: `{"type": "ended", "callId": "..."}`
"""
from __future__ import annotations

import io
import json
import struct
import time
import uuid
import wave
from typing import Any, Dict, Optional

from app.api.routes_analysis import get_conversation_manager
from app.api.routes_transcription import get_stt_provider
from app.core.compat import APIRouter, Depends, Header, HTTPException, WebSocket, WebSocketDisconnect
from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.schemas.calls import CallSegmentRequest
from app.services.conversation_manager import ConversationManager
from app.services.live_audio_processor import (
    LiveAudioSession,
    get_broadcaster,
)
from app.services.telegram_service import TelegramAlertService, get_telegram_service
from app.services.transcription_service import BaseSpeechToTextProvider

logger = get_logger("scam_detector.live_ingest")
router = APIRouter(prefix="/internal/live", tags=["live_ingest"])


@router.get("/status")
async def get_live_bridge_status(
    settings: Settings = Depends(get_settings),
) -> Dict[str, Any]:
    """Returns the readiness status of the Telegram VoIP live call audio bridge."""
    return {
        "status": "ready",
        "websocket_endpoint": "/internal/live/ingest",
        "protocol_version": 1,
        "sample_rate_hz": 16000,
        "format": "PCM16LE_MONO",
        "supported_channels": ["0:agent", "1:customer"],
        "sarvam_stt_connected": settings.has_live_sarvam_key,
        "bridge_secret_configured": bool(settings.telegram_webhook_secret),
    }


@router.post("/spike")
async def test_bridge_spike_simulation(
    payload: Dict[str, Any],
    manager: ConversationManager = Depends(get_conversation_manager),
    telegram_service: TelegramAlertService = Depends(get_telegram_service),
) -> Dict[str, Any]:
    """
    Simulates a Telegram VoIP Call Bridge event without requiring active py-tgcalls setup.
    Useful for testing the live audio analysis, keyword flagging, and Telegram alerts.
    """
    transcript = payload.get(
        "transcript",
        "Hello sir, your bank account is blocked today. Share the 6-digit OTP immediately to avoid police arrest.",
    )
    call_id = payload.get("call_id") or f"tg_spike_{uuid.uuid4().hex[:6]}"
    customer_name = payload.get("customer_name", "Telegram Suspicious Caller")

    seg_req = CallSegmentRequest(
        text=transcript,
        speaker="customer",
        language_code=payload.get("language_code", "auto"),
        start_seconds=0.0,
        end_seconds=4.0,
        transcript_confidence=0.96,
    )
    seg_resp = manager.process_segment(call_id, seg_req)

    # Dispatch alert if enabled
    alert_result = None
    if telegram_service.is_enabled:
        alert_result = telegram_service.send_risk_alert(seg_resp.assessment, call_id).model_dump()

    return {
        "status": "simulated",
        "call_id": call_id,
        "customer_name": customer_name,
        "assessment": seg_resp.assessment.model_dump(),
        "flagged_keywords": [i.keyword_or_pattern for i in seg_resp.assessment.rule_analysis.triggered_indicators],
        "telegram_alert": alert_result,
    }


@router.websocket("/ingest")
async def websocket_live_ingest(
    websocket: WebSocket,
    manager: ConversationManager = Depends(get_conversation_manager),
    stt_provider: BaseSpeechToTextProvider = Depends(get_stt_provider),
    telegram_service: TelegramAlertService = Depends(get_telegram_service),
    settings: Settings = Depends(get_settings),
) -> None:
    """
    WebSocket endpoint ingesting real-time audio from onfloor telegram-bridge (py-tgcalls).
    Uses non-blocking bounded queues, concurrent asynchronous transcription, and 7-8 word chunking.
    """
    await websocket.accept()

    expected_secret = settings.bridge_secret or settings.telegram_webhook_secret
    if expected_secret:
        client_secret = websocket.headers.get("x-bridge-secret", "")
        if client_secret != expected_secret:
            logger.warning("Rejected unauthorized WebSocket live ingest connection")
            await websocket.close(code=1008)
            return

    logger.info("Telegram live call audio bridge connected")

    call_id: Optional[str] = None
    session: Optional[LiveAudioSession] = None
    broadcaster = get_broadcaster()

    async def forward_to_bridge_client(event: Dict[str, Any]) -> None:
        try:
            await websocket.send_json(event)
        except Exception:
            pass

    try:
        while True:
            message = await websocket.receive()

            # Handle JSON Control Messages
            if "text" in message and message["text"]:
                try:
                    data = json.loads(message["text"])
                except Exception:
                    continue

                msg_type = data.get("type")

                if msg_type == "call_started":
                    tg_id = data.get("telegramCallId", f"peer_{uuid.uuid4().hex[:6]}")
                    call_id = f"tg_call_{uuid.uuid4().hex[:8]}"

                    logger.info("Started Telegram call '%s' (tg: %s)", call_id, tg_id)

                    session = LiveAudioSession(
                        call_id=call_id,
                        stt_provider=stt_provider,
                        conversation_manager=manager,
                        telegram_service=telegram_service,
                        broadcaster=broadcaster,
                        language_code="auto",
                        on_event_callback=forward_to_bridge_client,
                    )
                    session.start()

                    await websocket.send_json({
                        "type": "ack",
                        "protocolVersion": 1,
                        "callId": call_id,
                    })

                elif msg_type == "call_ended":
                    if session:
                        end_summary = await session.stop_and_flush()
                        logger.info("Ended Telegram call '%s'", call_id)
                        await websocket.send_json({
                            "type": "ended",
                            "callId": call_id,
                            "summary": end_summary,
                        })
                        session = None
                    break

            # Handle Binary PCM Audio Frames (16kHz 16-bit Mono)
            elif "bytes" in message and message["bytes"]:
                raw_bytes = message["bytes"]
                if len(raw_bytes) < 6:
                    continue

                channel = raw_bytes[0]  # 0 = agent, 1 = customer / potential scammer
                pcm = raw_bytes[5:]

                # Enqueue customer audio non-blockingly
                if channel == 1 and session:
                    session.push_pcm_frame(pcm)

    except (WebSocketDisconnect, RuntimeError) as disconnect_exc:
        logger.info("Telegram bridge WebSocket disconnected cleanly (%s): %s", call_id, disconnect_exc)
    except Exception as exc:
        logger.error("Telegram bridge error: %s", exc)
    finally:
        if session:
            await session.stop_and_flush()
        try:
            await websocket.close()
        except Exception:
            pass


@router.websocket("/browser-stream")
async def websocket_browser_stream(
    websocket: WebSocket,
    manager: ConversationManager = Depends(get_conversation_manager),
    stt_provider: BaseSpeechToTextProvider = Depends(get_stt_provider),
    telegram_service: TelegramAlertService = Depends(get_telegram_service),
) -> None:
    """
    Direct WebSocket endpoint for continuous browser-based live audio capture.
    Allows capturing live ongoing phone calls (e.g., phone on speaker or Telegram desktop audio)
    directly through the browser microphone without stopping after every sentence.
    """
    await websocket.accept()
    call_id = f"web_live_{uuid.uuid4().hex[:8]}"
    broadcaster = get_broadcaster()
    broadcaster.register(websocket)

    async def forward_to_browser(event: Dict[str, Any]) -> None:
        try:
            await websocket.send_json(event)
        except Exception:
            pass

    session = LiveAudioSession(
        call_id=call_id,
        stt_provider=stt_provider,
        conversation_manager=manager,
        telegram_service=telegram_service,
        broadcaster=broadcaster,
        language_code="auto",
        on_event_callback=forward_to_browser,
    )
    session.start()

    await websocket.send_json({
        "type": "session_ready",
        "callId": call_id,
        "sampleRate": 16000,
        "chunkTargetWords": 8,
        "status": "LISTENING_CONTINUOUS",
    })

    try:
        while True:
            msg = await websocket.receive()
            if "text" in msg and msg["text"]:
                try:
                    data = json.loads(msg["text"])
                    if data.get("type") == "stop":
                        break
                    if data.get("type") == "set_language":
                        session.language_code = data.get("language_code", "auto")
                except Exception:
                    continue
            elif "bytes" in msg and msg["bytes"]:
                # Browser streams raw PCM16LE audio chunks continuously
                session.push_pcm_frame(msg["bytes"])

    except (WebSocketDisconnect, RuntimeError):
        logger.info("Browser audio stream disconnected (%s)", call_id)
    except Exception as exc:
        logger.error("Browser stream error: %s", exc)
    finally:
        broadcaster.unregister(websocket)
        await session.stop_and_flush()


@router.websocket("/events")
async def websocket_dashboard_events(
    websocket: WebSocket,
) -> None:
    """
    HUD broadcast WebSocket for the Suraksha frontend dashboard.
    Receives all live caption updates, risk score changes, and Telegram notifications in real-time.
    """
    await websocket.accept()
    broadcaster = get_broadcaster()
    broadcaster.register(websocket)
    try:
        while True:
            await websocket.receive_text()
    except (WebSocketDisconnect, RuntimeError):
        pass
    finally:
        broadcaster.unregister(websocket)
