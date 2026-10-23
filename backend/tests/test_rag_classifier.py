"""
Automated unit tests for RAG Scam Classifier:
Verifies contextual intent recognition, protective advice suppression,
suspicious credential solicitation, ordinary authentication notices, and uncertainty handling.
"""
from __future__ import annotations

import unittest
from app.rag.classifier import RAGScamClassifier
from app.rag.schemas import RAGClassificationRequest, RetrievedExample


class MockRetriever:
    """Mock retriever returning controlled semantic neighbors for deterministic testing."""

    def __init__(self, mode: str = "scam") -> None:
        self.mode = mode
        self.is_ready = True
        self.total_indexed = 100

    def load(self) -> bool:
        return True

    def retrieve(self, query_text: str, top_k: int = 5, similarity_threshold: float = 0.38):
        if self.mode == "empty":
            return [], True, 1.2
        if self.mode == "weak":
            return [
                RetrievedExample(example_id="ex_1", label="SCAM", similarity=0.25, distance=0.75, text="unrelated"),
            ], True, 1.5
        if self.mode == "ambiguous":
            return [
                RetrievedExample(example_id="ex_1", label="SCAM", similarity=0.72, distance=0.28, text="transfer money"),
                RetrievedExample(example_id="ex_2", label="LEGITIMATE", similarity=0.71, distance=0.29, text="bank inquiry"),
            ], False, 1.8
        if self.mode == "legit":
            return [
                RetrievedExample(example_id="ex_1", label="LEGITIMATE", similarity=0.88, distance=0.12, text="How can I help you today?"),
                RetrievedExample(example_id="ex_2", label="LEGITIMATE", similarity=0.85, distance=0.15, text="Thank you for calling customer service."),
            ], False, 1.5
        # Default scam mode
        return [
            RetrievedExample(example_id="ex_1", label="SCAM", similarity=0.91, distance=0.09, text="Share your OTP immediately"),
            RetrievedExample(example_id="ex_2", label="SCAM", similarity=0.87, distance=0.13, text="Account blocked verify now"),
        ], False, 1.5


class RAGClassifierTestSuite(unittest.TestCase):
    """Verifies that RAG classifier distinguishes intent rather than blindly matching keywords."""

    def test_01_empty_input_returns_uncertain(self) -> None:
        classifier = RAGScamClassifier(retriever=MockRetriever())
        res = classifier.classify(RAGClassificationRequest(text=""))
        self.assertEqual(res.classification, "UNCERTAIN")
        self.assertTrue(res.insufficient_evidence)
        self.assertEqual(res.risk_score, 0.0)

    def test_02_protective_advice_never_flagged_as_scam(self) -> None:
        classifier = RAGScamClassifier(retriever=MockRetriever(mode="scam"))
        # Even if retriever returns scam neighbors, protective intent MUST override to LEGITIMATE
        res = classifier.classify(
            RAGClassificationRequest(text="Never share your OTP with anyone. Bank officials will never ask for it.")
        )
        self.assertEqual(res.classification, "LEGITIMATE")
        self.assertEqual(res.risk_score, 0.0)
        self.assertIn("Protective security advice detected", res.indicators[0])

    def test_03_active_credential_solicitation_flagged_as_scam(self) -> None:
        classifier = RAGScamClassifier(retriever=MockRetriever(mode="scam"))
        res = classifier.classify(
            RAGClassificationRequest(text="Sir, tell me the OTP you just received right now so I can verify your account.")
        )
        self.assertEqual(res.classification, "SCAM")
        self.assertGreaterEqual(res.risk_score, 75.0)
        self.assertGreaterEqual(res.confidence, 0.85)

    def test_04_inbound_authentication_notice_cleared_as_legitimate(self) -> None:
        classifier = RAGScamClassifier(retriever=MockRetriever(mode="legit"))
        res = classifier.classify(
            RAGClassificationRequest(text="Your OTP for logging into HDFC netbanking is 849201. Valid for 5 minutes.")
        )
        self.assertEqual(res.classification, "LEGITIMATE")
        self.assertLessEqual(res.risk_score, 10.0)

    def test_05_urgent_coercion_threat_flagged_as_scam(self) -> None:
        classifier = RAGScamClassifier(retriever=MockRetriever(mode="scam"))
        res = classifier.classify(
            RAGClassificationRequest(text="Your bank account is suspended immediately. Transfer funds now to prevent arrest.")
        )
        self.assertEqual(res.classification, "SCAM")
        self.assertGreaterEqual(res.risk_score, 70.0)

    def test_06_weak_retrieval_returns_uncertain(self) -> None:
        classifier = RAGScamClassifier(retriever=MockRetriever(mode="weak"))
        res = classifier.classify(
            RAGClassificationRequest(text="What is the weather outside today in New Delhi?")
        )
        self.assertEqual(res.classification, "UNCERTAIN")
        self.assertTrue(res.insufficient_evidence)

    def test_07_ambiguous_conflicting_evidence_returns_uncertain(self) -> None:
        classifier = RAGScamClassifier(retriever=MockRetriever(mode="ambiguous"))
        res = classifier.classify(
            RAGClassificationRequest(text="I need to check the status of my transfer from yesterday.")
        )
        self.assertEqual(res.classification, "UNCERTAIN")

    def test_08_prediction_consistency(self) -> None:
        classifier = RAGScamClassifier(retriever=MockRetriever(mode="scam"))
        query = RAGClassificationRequest(text="Please share the 6-digit verification code sent to your phone.")
        res1 = classifier.classify(query)
        res2 = classifier.classify(query)
        self.assertEqual(res1.classification, res2.classification)
        self.assertEqual(res1.risk_score, res2.risk_score)
        self.assertEqual(res1.confidence, res2.confidence)


if __name__ == "__main__":
    unittest.main()
