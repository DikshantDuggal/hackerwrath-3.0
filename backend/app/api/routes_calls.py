"""
Multi-segment Call State Endpoints:
- POST /calls/{call_id}/segments
- GET /calls/{call_id}/risk
- GET /calls/{call_id}/history
- DELETE /calls/{call_id}
"""
from __future__ import annotations

from app.api.routes_analysis import get_conversation_manager
from app.core.compat import APIRouter, Depends, HTTPException
from app.schemas.analysis import ScamRiskAssessment
from app.schemas.calls import (
    CallClearResponse,
    CallHistoryResponse,
    CallSegmentRequest,
    CallSegmentUpdateResponse,
)
from app.services.conversation_manager import ConversationManager

router = APIRouter(prefix="/calls", tags=["calls"])


@router.post("/{call_id}/segments", response_model=CallSegmentUpdateResponse)
async def add_call_segment(
    call_id: str,
    segment: CallSegmentRequest,
    manager: ConversationManager = Depends(get_conversation_manager),
) -> CallSegmentUpdateResponse:
    clean_id = call_id.strip()
    if not clean_id:
        raise HTTPException(status_code=400, detail="call_id must not be empty.")
    if not segment.text or not segment.text.strip():
        raise HTTPException(status_code=422, detail="Segment text must not be empty.")
    return manager.process_segment(clean_id, segment)


@router.get("/{call_id}/risk", response_model=ScamRiskAssessment)
async def get_call_risk(
    call_id: str,
    manager: ConversationManager = Depends(get_conversation_manager),
) -> ScamRiskAssessment:
    assessment = manager.get_latest_risk(call_id.strip())
    if assessment is None:
        raise HTTPException(
            status_code=404,
            detail=f"No active risk assessment found for call_id '{call_id}'.",
        )
    return assessment


@router.get("/{call_id}/history", response_model=CallHistoryResponse)
async def get_call_history(
    call_id: str,
    manager: ConversationManager = Depends(get_conversation_manager),
) -> CallHistoryResponse:
    history = manager.get_history(call_id.strip())
    if history is None:
        raise HTTPException(
            status_code=404,
            detail=f"No stored conversation history found for call_id '{call_id}'.",
        )
    return history


@router.delete("/{call_id}", response_model=CallClearResponse)
async def delete_call_state(
    call_id: str,
    manager: ConversationManager = Depends(get_conversation_manager),
) -> CallClearResponse:
    cleared = manager.clear_call(call_id.strip())
    if cleared is None:
        raise HTTPException(
            status_code=404,
            detail=f"No stored call state found for call_id '{call_id}'.",
        )
    return cleared
