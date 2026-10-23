"""
Retrieval engine for RAG scam detection.
Performs semantic similarity search against indexed reference examples.
"""
from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from app.core.logging import get_logger
from app.rag.config import (
    CHROMA_COLLECTION_NAME,
    CHROMA_PERSIST_DIR,
    DEFAULT_TOP_K,
    METADATA_INDEX_PATH,
    NUMPY_INDEX_PATH,
    WEAK_EVIDENCE_SIMILARITY_THRESHOLD,
)
from app.rag.embeddings import get_embedding_engine
from app.rag.schemas import RetrievedExample

logger = get_logger("scam_detector.rag.retriever")

_GLOBAL_RETRIEVER: Optional[SemanticRetriever] = None


class SemanticRetriever:
    """
    Retrieves nearest reference examples using vector similarity.
    Prefers ultra-fast persistent NumPy cosine matrix multiplication (<2ms);
    falls back to ChromaDB if NumPy index is not yet built.
    """

    def __init__(self) -> None:
        self.embedding_engine = get_embedding_engine()
        self._numpy_embeddings: Optional[np.ndarray] = None
        self._example_ids: Optional[np.ndarray] = None
        self._labels: Optional[np.ndarray] = None
        self._metadata_map: Dict[str, Dict[str, Any]] = {}
        self._chroma_collection = None
        self._is_loaded = False

    def load(self) -> bool:
        """Loads index into memory once."""
        if self._is_loaded:
            return True

        t0 = time.time()

        # 1. Try loading NumPy index (preferred for sub-2ms latency)
        if os.path.exists(NUMPY_INDEX_PATH) and os.path.exists(METADATA_INDEX_PATH):
            try:
                npz = np.load(NUMPY_INDEX_PATH)
                self._numpy_embeddings = npz["embeddings"].astype(np.float32)
                self._example_ids = npz["example_ids"]
                self._labels = npz["labels"]

                # Ensure embeddings are L2-normalized
                norms = np.linalg.norm(self._numpy_embeddings, axis=1, keepdims=True)
                norms[norms == 0] = 1.0
                self._numpy_embeddings = self._numpy_embeddings / norms

                # Load metadata
                self._metadata_map = {}
                with open(METADATA_INDEX_PATH, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            item = json.loads(line)
                            self._metadata_map[item["example_id"]] = item

                self._is_loaded = True
                logger.info(
                    "Loaded NumPy vector index with %d documents in %.3fs",
                    len(self._numpy_embeddings),
                    time.time() - t0,
                )
                return True
            except Exception as e:
                logger.warning("Failed to load NumPy index: %s", e)

        # 2. Try ChromaDB collection fallback
        try:
            import chromadb

            if os.path.isdir(CHROMA_PERSIST_DIR):
                client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
                self._chroma_collection = client.get_collection(CHROMA_COLLECTION_NAME)
                self._is_loaded = True
                logger.info("Connected to ChromaDB collection '%s'", CHROMA_COLLECTION_NAME)
                return True
        except Exception as chroma_err:
            logger.debug("ChromaDB not available or collection not found: %s", chroma_err)

        logger.warning("No persistent vector index found. Retriever is operating unindexed.")
        return False

    @property
    def is_ready(self) -> bool:
        return self._is_loaded and (self._numpy_embeddings is not None or self._chroma_collection is not None)

    @property
    def total_indexed(self) -> int:
        if self._numpy_embeddings is not None:
            return len(self._numpy_embeddings)
        if self._chroma_collection is not None:
            return self._chroma_collection.count()
        return 0

    def retrieve(
        self,
        query_text: str,
        top_k: int = DEFAULT_TOP_K,
        similarity_threshold: float = WEAK_EVIDENCE_SIMILARITY_THRESHOLD,
    ) -> Tuple[List[RetrievedExample], bool, float]:
        """
        Retrieves top_k nearest examples for query_text.
        Returns:
            (retrieved_examples, insufficient_evidence_flag, latency_ms)
        """
        t0 = time.time()
        if not self._is_loaded:
            self.load()

        if not self.is_ready or not query_text or not query_text.strip():
            latency_ms = round((time.time() - t0) * 1000, 2)
            return [], True, latency_ms

        # 1. Encode query text
        query_vector = self.embedding_engine.encode(query_text)
        q_norm = np.linalg.norm(query_vector)
        if q_norm > 1e-9:
            query_vector = query_vector / q_norm

        results: List[RetrievedExample] = []

        # 2. Fast NumPy Vector Search
        if self._numpy_embeddings is not None:
            # Dot product with all normalized vectors gives exact cosine similarities
            sims = np.dot(self._numpy_embeddings, query_vector)
            top_k_actual = min(top_k, len(sims))
            # argpartition for O(N) top-k selection, then sort top-k
            top_indices = np.argpartition(sims, -top_k_actual)[-top_k_actual:]
            sorted_indices = top_indices[np.argsort(-sims[top_indices])]

            for idx in sorted_indices:
                sim = float(np.clip(sims[idx], -1.0, 1.0))
                ex_id = str(self._example_ids[idx])
                label = str(self._labels[idx])
                meta = self._metadata_map.get(ex_id, {})
                text_snippet = meta.get("text", "")
                if len(text_snippet) > 250:
                    text_snippet = text_snippet[:250] + "..."

                results.append(
                    RetrievedExample(
                        example_id=ex_id,
                        label=label,
                        similarity=round(sim, 4),
                        distance=round(max(0.0, 1.0 - sim), 4),
                        text=text_snippet,
                    )
                )

        # 3. ChromaDB Search Fallback
        elif self._chroma_collection is not None:
            res = self._chroma_collection.query(
                query_embeddings=[query_vector.tolist()],
                n_results=top_k,
                include=["documents", "metadatas", "distances"],
            )
            if res and res.get("ids") and len(res["ids"][0]) > 0:
                for i in range(len(res["ids"][0])):
                    ex_id = res["ids"][0][i]
                    dist = float(res["distances"][0][i]) if "distances" in res else 0.0
                    sim = max(0.0, 1.0 - dist)
                    meta = res["metadatas"][0][i] if "metadatas" in res else {}
                    doc = res["documents"][0][i] if "documents" in res else ""
                    if len(doc) > 250:
                        doc = doc[:250] + "..."
                    results.append(
                        RetrievedExample(
                            example_id=ex_id,
                            label=meta.get("label", "LEGITIMATE"),
                            similarity=round(sim, 4),
                            distance=round(dist, 4),
                            text=doc,
                        )
                    )

        latency_ms = round((time.time() - t0) * 1000, 2)

        # Check weak evidence
        insufficient_evidence = False
        if not results:
            insufficient_evidence = True
        elif results[0].similarity < similarity_threshold:
            insufficient_evidence = True

        return results, insufficient_evidence, latency_ms


def get_retriever() -> SemanticRetriever:
    """Returns singleton SemanticRetriever instance."""
    global _GLOBAL_RETRIEVER
    if _GLOBAL_RETRIEVER is None:
        _GLOBAL_RETRIEVER = SemanticRetriever()
    return _GLOBAL_RETRIEVER
