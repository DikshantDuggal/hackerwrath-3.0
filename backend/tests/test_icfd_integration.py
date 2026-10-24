"""
Unit Tests for ICFD-31k Model Integration in FastAPI Backend.
Verifies model loading, fallback resilience, language identification,
probability calibration, and end-to-end assessment pipeline.
"""
from __future__ import annotations

import unittest
from pathlib import Path
from app.detectors.icfd_classifier import IcfdClassifier, get_icfd_classifier
from app.schemas.analysis import TranscriptAnalysisRequest
from app.services.conversation_manager import ConversationManager


class TestIcfdModelIntegration(unittest.TestCase):
    """Test suite for the ICFD-31k trained model integration."""

    @classmethod
    def setUpClass(cls):
        cls.classifier = get_icfd_classifier()
        cls.manager = ConversationManager()

    def test_01_model_loaded_and_configured(self):
        """Verifies the ICFD model loads its weights and configuration."""
        self.assertTrue(self.classifier.available, "ICFD classifier should be available")
        self.assertIsNotNone(self.classifier.classifier, "Classifier head must be loaded")
        self.assertIsNotNone(self.classifier.embedder, "SentenceTransformer embedder must be loaded")
        self.assertIn("model_name", self.classifier.config)
        self.assertGreater(self.classifier.threshold, 0.0)

    def test_02_language_detection(self):
        """Verifies language identification for English, Hinglish, and Devanagari."""
        eng_text = "Hello sir, I am calling from tech support regarding your computer virus."
        hing_text = "Namaste sir ji, aapka account block ho gaya hai, kripya OTP batao."
        dev_text = "नमस्ते सर, आपका बैंक खाता बंद कर दिया गया है।"

        self.assertEqual(self.classifier.detect_language(eng_text), "english")
        self.assertEqual(self.classifier.detect_language(hing_text), "hinglish")
        self.assertEqual(self.classifier.detect_language(dev_text), "hindi_devanagari")

    def test_03_probability_bounds_and_calibration(self):
        """Verifies that predicted fraud probability is strictly in [0.0, 1.0]."""
        text = "Please transfer 50000 rupees to my personal account right now."
        result = self.classifier.predict(text)
        self.assertTrue(result.available)
        self.assertGreaterEqual(result.fraud_probability, 0.0)
        self.assertLessEqual(result.fraud_probability, 1.0)
        self.assertEqual(result.calibration_status, "calibrated_platt_sigmoid")
        self.assertGreater(result.latency_ms, 0.0)

    def test_04_fraud_vs_legit_discrimination(self):
        """Verifies that fraud call gets higher risk probability than clean legitimate call."""
        fraud_text = "Sir transfer money immediately via UPI to this number or police will arrest you."
        legit_text = "Namaste sir, welcome to HDFC bank customer support. Thank you for calling, how may I help you with your debit card statement inquiry today?"

        res_fraud = self.classifier.predict(fraud_text)
        res_legit = self.classifier.predict(legit_text)

        self.assertGreater(
            res_fraud.fraud_probability,
            res_legit.fraud_probability,
            "Fraud call must receive higher fraud probability than legitimate support call"
        )

    def test_05_empty_transcript_handling(self):
        """Verifies empty or whitespace transcript returns safe empty result."""
        res = self.classifier.predict("")
        self.assertEqual(res.fraud_probability, 0.0)
        self.assertFalse(res.is_fraud)
        self.assertIn("Empty transcript", res.error_message)

    def test_06_conversation_manager_end_to_end(self):
        """Verifies full FastAPI standalone analysis returns icfd_analysis attached."""
        req = TranscriptAnalysisRequest(
            transcript="Send 5000 rupees urgently to verify your bank account details.",
            call_id="call-unit-test-icfd"
        )
        assessment = self.manager.analyze_standalone_transcript(req)
        self.assertIsNotNone(assessment.icfd_analysis)
        self.assertTrue(assessment.icfd_analysis.get("available"))
        self.assertIn("fraud_probability", assessment.icfd_analysis)
        self.assertIn("detected_language", assessment.icfd_analysis)

    def test_07_fallback_resilience(self):
        """Verifies graceful fallback behavior when pointing to a non-existent model directory."""
        dummy_classifier = IcfdClassifier(model_dir=Path("non_existent_dir_12345"))
        self.assertFalse(dummy_classifier.available)
        res = dummy_classifier.predict("Hello test call")
        self.assertFalse(res.available)
        self.assertEqual(res.fraud_probability, 0.0)
        self.assertIn("fallback", res.error_message)


if __name__ == "__main__":
    unittest.main()
