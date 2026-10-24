"""
LiveKit Cloud Internet Calling API Endpoints.
Provides REST APIs for call lifecycle management:
- POST /calls/start
- POST /calls/{call_id}/accept
- POST /calls/{call_id}/reject
- POST /calls/{call_id}/end
- POST /calls/{call_id}/token
- GET /calls/{call_id}/status
- GET /calls/active
- GET /calls
"""
from __future__ import annotations

import time
from typing import List, Optional

from app.core.compat import APIRouter, Depends, HTTPException, Query
from app.schemas.livekit_calls import (
    CallActionRequest,
    CallActionResponse,
    CallStartRequest,
    CallStartResponse,
    CallTokenRequest,
    CallTokenResponse,
    LiveKitCallDetail,
)
from app.services.livekit_service import LiveKitCallManager, get_livekit_manager

router = APIRouter(prefix="/calls", tags=["livekit_calls"])


@router.post("/start", response_model=CallStartResponse)
async def start_call(
    request: CallStartRequest,
    manager: LiveKitCallManager = Depends(get_livekit_manager),
) -> CallStartResponse:
    """Initiates a new LiveKit internet call and allocates a room."""
    call = manager.start_call(
        recipient_id=request.recipient_id,
        caller_id=request.caller_id,
        language_code=request.language_code,
        enable_scam_detection=request.enable_scam_detection,
    )
    return CallStartResponse(
        call_id=call.call_id,
        room_id=call.room_id,
        caller_id=call.caller_id,
        recipient_id=call.recipient_id,
        status=call.status,
        created_at=call.created_at,
        ai_detection_active=call.ai_detection_active,
    )


@router.get("/active", response_model=List[LiveKitCallDetail])
async def list_active_calls(
    manager: LiveKitCallManager = Depends(get_livekit_manager),
) -> List[LiveKitCallDetail]:
    """Lists all active, ringing, or ongoing calls."""
    return manager.list_active_calls()


@router.get("", response_model=List[LiveKitCallDetail])
async def list_all_calls(
    user_id: Optional[str] = Query(default=None, description="Filter calls by participant user ID"),
    manager: LiveKitCallManager = Depends(get_livekit_manager),
) -> List[LiveKitCallDetail]:
    """Returns all calls, optionally filtered by participant user ID."""
    if user_id:
        return manager.list_calls_for_user(user_id)
    return manager.list_calls()


@router.get("/{call_id}/status", response_model=LiveKitCallDetail)
async def get_call_status(
    call_id: str,
    manager: LiveKitCallManager = Depends(get_livekit_manager),
) -> LiveKitCallDetail:
    """Returns detailed status and metadata for a specific call."""
    call = manager.get_call(call_id.strip())
    if not call:
        raise HTTPException(status_code=404, detail=f"Call '{call_id}' not found.")
    return call


@router.post("/{call_id}/accept", response_model=CallActionResponse)
async def accept_call(
    call_id: str,
    request: Optional[CallActionRequest] = None,
    manager: LiveKitCallManager = Depends(get_livekit_manager),
) -> CallActionResponse:
    """Accepts an incoming call, activating audio and AI scam detection."""
    user_id = request.user_id if request else None
    call = manager.accept_call(call_id.strip(), user_id=user_id)
    return CallActionResponse(
        call_id=call.call_id,
        status=call.status,
        updated_at=call.accepted_at or time.time(),
        message="Call accepted successfully. Audio session and AI scam detection active.",
    )


@router.post("/{call_id}/reject", response_model=CallActionResponse)
async def reject_call(
    call_id: str,
    request: Optional[CallActionRequest] = None,
    manager: LiveKitCallManager = Depends(get_livekit_manager),
) -> CallActionResponse:
    """Rejects an incoming call invitation."""
    user_id = request.user_id if request else None
    reason = request.reason if request else None
    call = manager.reject_call(call_id.strip(), user_id=user_id, reason=reason)
    return CallActionResponse(
        call_id=call.call_id,
        status=call.status,
        updated_at=call.ended_at or time.time(),
        message=f"Call rejected. Reason: {reason or 'User declined'}",
    )


@router.post("/{call_id}/end", response_model=CallActionResponse)
async def end_call(
    call_id: str,
    request: Optional[CallActionRequest] = None,
    manager: LiveKitCallManager = Depends(get_livekit_manager),
) -> CallActionResponse:
    """Terminates an ongoing call and tears down AI audio processing workers."""
    user_id = request.user_id if request else None
    reason = request.reason if request else None
    call = manager.end_call(call_id.strip(), user_id=user_id, reason=reason)
    return CallActionResponse(
        call_id=call.call_id,
        status=call.status,
        updated_at=call.ended_at or time.time(),
        message=f"Call ended. Reason: {reason or 'Normal hangup'}",
    )


@router.post("/{call_id}/token", response_model=CallTokenResponse)
async def get_call_token(
    call_id: str,
    request: Optional[CallTokenRequest] = None,
    manager: LiveKitCallManager = Depends(get_livekit_manager),
) -> CallTokenResponse:
    """
    Generates a secure, room-restricted LiveKit participant token.
    Enforces authorization: only call participants may receive tokens.
    """
    user_id = request.user_id if request else None
    ttl = request.ttl_seconds if request else None
    return manager.generate_token(
        call_id=call_id.strip(),
        user_id=user_id,
        ttl_seconds=ttl,
    )
