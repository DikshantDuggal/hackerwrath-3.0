"""
Unified RAG Service for the scam-call detection system.
Manages singleton lifecycle, vector index readiness, and provides clean APIs
for both HTTP endpoints and live-call audio transcript processing.
"""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from app.core.logging import get_logger
from app.rag.classifier import RAGScamClassifier, get_classifier
from app.rag.config import DEFAULT_TOP_K
from app.rag.embeddings import get_embedding_engine
from app.rag.retriever import SemanticRetriever, get_retriever
from app.rag.schemas import (
    RAGClassificationRequest,
    RAGClassificationResponse,
    RAGHealthResponse,
)

logger = get_logger("scam_detector.rag.service")

_GLOBAL_RAG_SERVICE: Optional[RAGService] = None


class RAGService:
    """
    Singleton service coordinating embedding model, persistent retriever,
    and fraud classification.
    """

    def __init__(self) -> None:
        self.embedding_engine = get_embedding_engine()
        self.retriever = get_retriever()
        self.classifier = get_classifier()
        self._is_initialized = False

    def initialize(self) -> None:
        """Loads embedding model weights and vector index into memory on application startup."""
        if self._is_initialized:
            return

        t0 = time.time()
        logger.info("Initializing RAG Scam Detection Service...")

        # 1. Load embedding model
        self.embedding_engine.load()

        # 2. Load persistent vector index
        self.retriever.load()

        self._is_initialized = True
        logger.info(
            "RAG Scam Detection Service initialized in %.2fs (Indexed records: %d)",
            time.time() - t0,
            self.retriever.total_indexed,
        )

    def classify_text(
        self,
        text: str,
        preceding_context: Optional[str] = None,
        top_k: int = DEFAULT_TOP_K,
        include_retrieved_examples: bool = True,
    ) -> RAGClassificationResponse:
        """
        Classifies a single incoming text utterance or transcript segment.
        Reusable function designed for live-call audio pipelines.
        """
        if not self._is_initialized:
            self.initialize()

        req = RAGClassificationRequest(
            text=text,
            preceding_context=preceding_context,
            top_k=top_k,
            include_retrieved_examples=include_retrieved_examples,
        )
        return self.classifier.classify(req)

    def get_health(self) -> RAGHealthResponse:
        """Returns health status of the embedding engine and vector store."""
        is_ready = self.retriever.is_ready
        indexed_count = self.retriever.total_indexed

        return RAGHealthResponse(
            status="READY" if is_ready else "INITIALIZING",
            embedding_model=self.embedding_engine.model_name,
            embedding_model_loaded=self.embedding_engine.is_loaded,
            vector_index_loaded=is_ready,
            indexed_documents_count=indexed_count,
            vector_store_type="CHROMA_AND_NUMPY_OPTIMIZED",
        )


def get_rag_service() -> RAGService:
    """Returns singleton RAGService instance."""
    global _GLOBAL_RAG_SERVICE
    if _GLOBAL_RAG_SERVICE is None:
        _GLOBAL_RAG_SERVICE = RAGService()
    return _GLOBAL_RAG_SERVICE
