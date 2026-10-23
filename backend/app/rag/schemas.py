"""
Pydantic schemas for RAG Retrieval & Classification Module.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from app.core.compat import BaseModel, Field


class RetrievedExample(BaseModel):
    """A single retrieved training/reference example with semantic similarity score."""
    example_id: str = Field(default="", description="Unique identifier of reference record")
    label: str = Field(default="LEGITIMATE", description="Canonical label: SCAM or LEGITIMATE")
    similarity: float = Field(default=0.0, ge=-1.0, le=1.0, description="Cosine similarity score (-1.0 to 1.0)")
    distance: float = Field(default=1.0, ge=0.0, description="Cosine distance metric (1 - similarity)")
    text: str = Field(default="", description="Reference text excerpt")


class RAGClassificationRequest(BaseModel):
    """Payload for POST /rag/analyze or POST /analyze."""
    text: str = Field(default="", description="Incoming call utterance, message, or transcript segment")
    preceding_context: Optional[str] = Field(default=None, description="Optional preceding conversational context")
    top_k: int = Field(default=5, ge=1, le=20, description="Number of nearest semantic examples to retrieve")
    include_retrieved_examples: bool = Field(default=True, description="Whether to include retrieved examples in output")


class RAGClassificationResponse(BaseModel):
    """Structured response returned by the RAG scam classification engine."""
    classification: str = Field(..., description="'SCAM', 'LEGITIMATE', or 'UNCERTAIN'")
    risk_score: float = Field(..., ge=0.0, le=100.0, description="Heuristic scam risk score from 0 to 100")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Classification confidence from 0.0 to 1.0")
    insufficient_evidence: bool = Field(default=False, description="True if semantic similarity is too weak or input is trivial")
    indicators: List[str] = Field(default_factory=list, description="Specific identified fraud or benign indicators")
    retrieved_examples: List[RetrievedExample] = Field(default_factory=list, description="Top-k nearest reference examples")
    explanation: str = Field(default="", description="Clear human-readable justification of the classification")
    retrieval_latency_ms: float = Field(default=0.0, description="Vector retrieval duration in milliseconds")
    classification_latency_ms: float = Field(default=0.0, description="Overall classification duration in milliseconds")


class RAGHealthResponse(BaseModel):
    """Health status of the RAG embedding and vector index sub-systems."""
    status: str = Field(default="READY")
    embedding_model: str = Field(default="all-MiniLM-L6-v2")
    embedding_model_loaded: bool = Field(default=False)
    vector_index_loaded: bool = Field(default=False)
    indexed_documents_count: int = Field(default=0)
    vector_store_type: str = Field(default="CHROMA_AND_NUMPY_FALLBACK")
