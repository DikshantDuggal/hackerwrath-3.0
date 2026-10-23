"""
FastAPI Routes for RAG-Powered Scam Detection & Semantic Vector Retrieval.
Endpoints:
- POST /analyze       (Root alias for RAG transcript analysis)
- POST /rag/analyze   (Explicit RAG analysis endpoint)
- GET /rag/health     (Health and vector store readiness status)
"""
from __future__ import annotations

import time
from typing import Any, Dict

from app.core.compat import APIRouter, Depends, HTTPException
from app.core.logging import get_logger
from app.rag.schemas import (
    RAGClassificationRequest,
    RAGClassificationResponse,
    RAGHealthResponse,
)
from app.rag.service import RAGService, get_rag_service

logger = get_logger("scam_detector.api.rag")

router = APIRouter(tags=["rag_detection"])


@router.post("/rag/analyze", response_model=RAGClassificationResponse)
@router.post("/analyze", response_model=RAGClassificationResponse)
async def analyze_transcript_rag(
    request: RAGClassificationRequest,
    rag_service: RAGService = Depends(get_rag_service),
) -> RAGClassificationResponse:
    """
    Analyzes an incoming transcript segment or conversational text using RAG semantic retrieval
    against reference phone-scam dialogues, contextual intent logic, and uncertainty estimation.
    """
    if not request.text or not request.text.strip():
        raise HTTPException(
            status_code=422,
            detail="The 'text' field must not be empty or whitespace only.",
        )

    try:
        response = rag_service.classify_text(
            text=request.text,
            preceding_context=request.preceding_context,
            top_k=request.top_k,
            include_retrieved_examples=request.include_retrieved_examples,
        )
        return response
    except Exception as exc:
        logger.error("RAG classification failure: %s", exc)
        raise HTTPException(
            status_code=500,
            detail="Internal analysis error occurred while evaluating semantic evidence.",
        )


@router.get("/rag/health", response_model=RAGHealthResponse)
async def get_rag_health(
    rag_service: RAGService = Depends(get_rag_service),
) -> RAGHealthResponse:
    """
    Returns the readiness and status of the embedding model and persistent vector index.
    """
    try:
        return rag_service.get_health()
    except Exception as exc:
        logger.error("RAG health check error: %s", exc)
        return RAGHealthResponse(
            status="UNAVAILABLE",
            embedding_model="unknown",
            embedding_model_loaded=False,
            vector_index_loaded=False,
            indexed_documents_count=0,
            vector_store_type="NONE",
        )
