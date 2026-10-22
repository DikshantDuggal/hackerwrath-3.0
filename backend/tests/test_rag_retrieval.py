"""
Automated unit tests for SemanticRetriever:
Verifies top-k retrieval, distance metric consistency, weak evidence handling,
and empty query resilience.
"""
from __future__ import annotations

import unittest
import numpy as np

from app.rag.retriever import SemanticRetriever
from app.rag.schemas import RetrievedExample


class MockEmbeddingEngine:
    """Deterministic mock embedding engine for unit testing retriever math."""

    def __init__(self) -> None:
        self.model_name = "mock-minilm"
        self.is_loaded = True

    def load(self) -> None:
        pass

    def encode(self, text: str) -> np.ndarray:
        v = np.zeros(384, dtype=np.float32)
        words = text.lower().split()
        for w in words:
            idx = abs(hash(w)) % 384
            v[idx] += 1.0
        norm = np.linalg.norm(v)
        if norm > 0:
            v /= norm
        return v


class RAGRetrievalTestSuite(unittest.TestCase):
    """Verifies vector search calculations, top-k ranking, and thresholding."""

    def setUp(self) -> None:
        self.retriever = SemanticRetriever()
        self.retriever.embedding_engine = MockEmbeddingEngine()  # type: ignore

        # Set up a small synthetic in-memory index
        rng = np.random.RandomState(42)
        embs = rng.randn(10, 384).astype(np.float32)
        norms = np.linalg.norm(embs, axis=1, keepdims=True)
        self.retriever._numpy_embeddings = embs / norms
        self.retriever._example_ids = np.array([f"synth_{i}" for i in range(10)])
        self.retriever._labels = np.array(["SCAM" if i % 2 == 0 else "LEGITIMATE" for i in range(10)])
        self.retriever._metadata_map = {
            f"synth_{i}": {"text": f"Synthetic text sample {i}", "label": "SCAM" if i % 2 == 0 else "LEGITIMATE"}
            for i in range(10)
        }
        self.retriever._is_loaded = True

    def test_01_top_k_retrieval_returns_exact_count(self) -> None:
        results, weak, latency = self.retriever.retrieve("bank verification call", top_k=3)
        self.assertEqual(len(results), 3)
        self.assertGreater(latency, 0.0)

    def test_02_distance_and_similarity_metric_consistency(self) -> None:
        results, _, _ = self.retriever.retrieve("test payment", top_k=5)
        for r in results:
            self.assertGreaterEqual(r.similarity, -1.0)
            self.assertLessEqual(r.similarity, 1.0)
            self.assertAlmostEqual(r.distance, max(0.0, 1.0 - r.similarity), places=3)

    def test_03_results_are_sorted_descending_by_similarity(self) -> None:
        results, _, _ = self.retriever.retrieve("urgent transfer", top_k=5)
        sims = [r.similarity for r in results]
        self.assertEqual(sims, sorted(sims, reverse=True))

    def test_04_empty_query_returns_empty_and_insufficient(self) -> None:
        results, weak, latency = self.retriever.retrieve("", top_k=5)
        self.assertEqual(results, [])
        self.assertTrue(weak)

    def test_05_weak_similarity_triggers_insufficient_evidence(self) -> None:
        # High threshold will mark any moderate match as weak
        results, weak, _ = self.retriever.retrieve("obscure token", top_k=3, similarity_threshold=0.99)
        self.assertTrue(weak)


if __name__ == "__main__":
    unittest.main()
