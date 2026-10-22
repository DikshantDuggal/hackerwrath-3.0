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
    WebSocket endpoint ingesting real-time audio from onfloor telegram-bridge.
    """
    await websocket.accept()
    logger.info("Telegram live call audio bridge connected")

    call_id: Optional[str] = None
    customer_pcm_buffer = bytearray()
    last_process_time = time.time()
    call_metadata: Dict[str, Any] = {}

    try:
        while True:
            # Receive text or binary frame
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
                    call_metadata = data.get("customer") or {}
                    customer_pcm_buffer.clear()
                    last_process_time = time.time()

                    logger.info("Started Telegram call '%s' (tg: %s)", call_id, tg_id)
                    await websocket.send_json({
                        "type": "ack",
                        "protocolVersion": 1,
                        "callId": call_id,
                    })

                elif msg_type == "call_ended":
                    if call_id:
                        logger.info("Ended Telegram call '%s'", call_id)
                        await websocket.send_json({
                            "type": "ended",
                            "callId": call_id,
                        })
                    break

            # Handle Binary PCM Audio Frames
            elif "bytes" in message and message["bytes"]:
                raw_bytes = message["bytes"]
                if len(raw_bytes) < 6:
                    continue

                channel = raw_bytes[0]  # 0 = agent, 1 = customer
                offset = struct.unpack("<I", raw_bytes[1:5])[0]
                pcm = raw_bytes[5:]

                # Process customer audio (the remote caller/scammer)
                if channel == 1 and call_id:
                    customer_pcm_buffer.extend(pcm)

                    # When buffer reaches ~2.5 seconds (80,000 bytes at 16kHz 16-bit mono)
                    # or elapsed time > 3 seconds, process segment
                    now = time.time()
                    if len(customer_pcm_buffer) >= 64000 or (len(customer_pcm_buffer) >= 32000 and now - last_process_time > 2.5):
                        chunk_to_process = bytes(customer_pcm_buffer)
                        customer_pcm_buffer.clear()
                        last_process_time = now

                        # Convert PCM16 buffer to standard in-memory WAV
                        wav_io = io.BytesIO()
                        with wave.open(wav_io, "wb") as wf:
                            wf.setnchannels(1)
                            wf.setsampwidth(2)
                            wf.setframerate(16000)
                            wf.writeframes(chunk_to_process)
                        wav_bytes = wav_io.getvalue()

                        try:
                            # Transcribe with Sarvam Saaras
                            stt_res = stt_provider.transcribe_bytes(
                                audio_bytes=wav_bytes,
                                filename=f"{call_id}_slice.wav",
                                language_code="auto",
                            )

                            transcript_text = (stt_res.transcript or "").strip()
                            if transcript_text:
                                seg_res = manager.process_segment(
                                    call_id,
                                    CallSegmentRequest(
                                        text=transcript_text,
                                        speaker="customer",
                                        language_code=stt_res.language_code,
                                        start_seconds=0.0,
                                        end_seconds=stt_res.duration_seconds,
                                        transcript_confidence=stt_res.confidence,
                                    ),
                                )

                                # Send live analysis back over WebSocket
                                await websocket.send_json({
                                    "type": "assessment",
                                    "callId": call_id,
                                    "transcript": transcript_text,
                                    "riskLevel": seg_res.assessment.risk_level,
                                    "riskScore": seg_res.assessment.risk_score,
                                    "flaggedKeywords": [
                                        i.keyword_or_pattern for i in seg_res.assessment.rule_analysis.triggered_indicators
                                    ],
                                    "recommendedAction": seg_res.assessment.recommended_action,
                                })
                        except Exception as exc:
                            logger.warning("Error processing Telegram audio slice: %s", exc)

    except WebSocketDisconnect:
        logger.info("Telegram bridge WebSocket disconnected (%s)", call_id)
    except Exception as exc:
        logger.error("Telegram bridge error: %s", exc)
        try:
            await websocket.close()
        except Exception:
            pass
