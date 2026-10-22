"""
POST /analyze/transcript and Cross-Call Keyword Synchronization endpoints.
"""
from __future__ import annotations

from app.core.compat import APIRouter, Depends, HTTPException
from app.schemas.analysis import ScamRiskAssessment, TranscriptAnalysisRequest
from app.schemas.calls import (
    KeywordSyncEntry,
    KeywordSyncStateResponse,
    KeywordSyncUpdateRequest,
)
from app.services.conversation_manager import ConversationManager
from app.services.keyword_sync_service import KeywordSyncService, get_keyword_sync_service

router = APIRouter(tags=["analysis"])

_default_conversation_manager = ConversationManager()


def get_conversation_manager() -> ConversationManager:
    return _default_conversation_manager


@router.post("/analyze/transcript", response_model=ScamRiskAssessment)
async def analyze_transcript(
    request: TranscriptAnalysisRequest,
    manager: ConversationManager = Depends(get_conversation_manager),
) -> ScamRiskAssessment:
    if not request.transcript or not request.transcript.strip():
        raise HTTPException(status_code=422, detail="Transcript must not be empty.")
    return manager.analyze_standalone_transcript(request)


@router.get("/sync/keywords", response_model=KeywordSyncStateResponse)
async def get_synced_keywords(
    sync_service: KeywordSyncService = Depends(get_keyword_sync_service),
) -> KeywordSyncStateResponse:
    return sync_service.get_state_response()


@router.post("/sync/keywords", status_code=201, response_model=KeywordSyncEntry)
async def add_synced_keyword(
    request: KeywordSyncUpdateRequest,
    sync_service: KeywordSyncService = Depends(get_keyword_sync_service),
) -> KeywordSyncEntry:
    if not request.keyword or len(request.keyword.strip()) < 2:
        raise HTTPException(status_code=422, detail="Keyword must be at least 2 characters.")
    return sync_service.register_or_sync_keyword(
        keyword=request.keyword,
        category=request.category,
        weight=request.weight,
        source_call_id=request.source_call_id,
    )
