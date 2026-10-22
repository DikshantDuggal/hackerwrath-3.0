"""
Automated endpoint integration tests for RAG scam detection routes:
- POST /analyze
- POST /rag/analyze
- GET /rag/health
"""
from __future__ import annotations

import unittest
from app.core.compat import LocalTestClient
from app.main import create_app
from app.rag.schemas import RAGClassificationResponse


class RAGApiTestSuite(unittest.TestCase):
    """Verifies FastAPI RAG endpoints and input validation."""

    def setUp(self) -> None:
        self.app = create_app()
        self.client = LocalTestClient(self.app)

    def test_01_analyze_endpoint_post(self) -> None:
        payload = {"text": "Sir, your account is suspended. Share your OTP immediately."}
        resp = self.client.post("/analyze", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("classification", data)
        self.assertIn("risk_score", data)
        self.assertIn("confidence", data)
        self.assertIn("retrieved_examples", data)
        self.assertIn(data["classification"], ("SCAM", "LEGITIMATE", "UNCERTAIN"))

    def test_02_rag_analyze_explicit_endpoint(self) -> None:
        payload = {
            "text": "Never share your OTP with anyone. It is a scam.",
            "top_k": 3,
            "include_retrieved_examples": True,
        }
        resp = self.client.post("/rag/analyze", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["classification"], "LEGITIMATE")
        self.assertEqual(data["risk_score"], 0.0)

    def test_03_empty_text_returns_422(self) -> None:
        resp = self.client.post("/rag/analyze", json={"text": "   "})
        self.assertEqual(resp.status_code, 422)

    def test_04_rag_health_endpoint(self) -> None:
        resp = self.client.get("/rag/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("status", data)
        self.assertIn("embedding_model", data)
        self.assertIn("indexed_documents_count", data)


if __name__ == "__main__":
    unittest.main()
