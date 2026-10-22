"""
RAG (Retrieval-Augmented Generation) & Semantic Similarity Scam Detection Module.
Provides fast, context-aware scam-versus-legitimate classification, vector retrieval,
baseline comparisons, and protective advice distinction.
"""
from app.rag.schemas import (
    RAGClassificationRequest,
    RAGClassificationResponse,
    RAGHealthResponse,
    RetrievedExample,
)

__all__ = [
    "RAGClassificationRequest",
    "RAGClassificationResponse",
    "RAGHealthResponse",
    "RetrievedExample",
]
