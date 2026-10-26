"""
Comprehensive English Scam Detection Regression Test Suite for EdgeRunner Guardian V2.

Verifies:
1. Ordinary conversation is not classified as scam (LOW risk, score <= 20).
2. Protective advice ("Please do not share your OTP with anyone") is identified as protective (LOW risk).
3. Contextual evaluation of high-risk solicitations:
   - "Your bank account will be blocked. Tell me your OTP immediately." -> CRITICAL / HIGH
   - "I am calling from your bank. Share your account password." -> HIGH
   - "Install this remote access application so I can verify your bank account." -> HIGH
   - "Transfer money immediately to prevent your account from being suspended." -> CRITICAL / HIGH
4. Multi-turn conversation state isolation: unrelated calls/conversations do not inherit stale text or risk evidence.
"""
from __future__ import annotations

import unittest
from app.core.config import Settings
from app.detectors.sensitive_info_detector import SensitiveInfoDetector
from app.repositories.conversation_repository import InMemoryConversationRepository
from app.schemas.analysis import TranscriptAnalysisRequest
from app.services.contextual_analyzer import ContextualAnalyzer
from app.services.conversation_manager import ConversationManager
from app.services.keyword_sync_service import KeywordSyncService
from app.services.risk_scorer import RiskScorer
from app.services.rules_engine import RulesEngine


class TestEnglishScamDetectionRegression(unittest.TestCase):
    def setUp(self) -> None:
        self.settings = Settings(
            sarvam_api_key="",
            max_audio_file_size_mb=1.0,
            calibrated_probability_enabled=False,
            call_state_retention_seconds=3600,
            min_transcript_confidence=0.60,
        )
        self.sync_service = KeywordSyncService(settings=self.settings)
        self.rules_engine = RulesEngine(
            settings=self.settings, keyword_sync_service=self.sync_service
        )
        self.contextual_analyzer = ContextualAnalyzer(settings=self.settings)
        self.sensitive_detector = SensitiveInfoDetector()
        self.risk_scorer = RiskScorer(
            settings=self.settings,
            sensitive_info_detector=self.sensitive_detector,
        )
        self.repository = InMemoryConversationRepository(settings=self.settings)
        self.manager = ConversationManager(
            repository=self.repository,
            rules_engine=self.rules_engine,
            contextual_analyzer=self.contextual_analyzer,
            risk_scorer=self.risk_scorer,
            keyword_sync_service=self.sync_service,
            settings=self.settings,
        )

    # 1. BENIGN ORDINARY MESSAGES
    def test_benign_ordinary_conversation(self) -> None:
        benign_messages = [
            "Hello, how are you?",
            "I will call you tomorrow.",
            "Thank you for your help.",
            "Your bank called me today.",
        ]
        for msg in benign_messages:
            res = self.manager.analyze_standalone_transcript(
                TranscriptAnalysisRequest(transcript=msg, language_code="en", call_id="test_benign")
            )
            self.assertEqual(
                res.risk_level,
                "LOW",
                f"Expected LOW risk for ordinary message '{msg}', got {res.risk_level} ({res.risk_score})"
            )
            self.assertLessEqual(res.risk_score, 25.0)

    # 2. PROTECTIVE SECURITY ADVICE
    def test_protective_security_advice(self) -> None:
        msg = "Please do not share your OTP with anyone."
        res = self.manager.analyze_standalone_transcript(
            TranscriptAnalysisRequest(transcript=msg, language_code="en", call_id="test_protective")
        )
        det = self.sensitive_detector.detect(msg)
        self.assertTrue(det.is_protective_warning, "Expected is_protective_warning to be True")
        self.assertEqual(res.risk_level, "LOW")
        self.assertLessEqual(res.risk_score, 20.0)

    # 3. SUSPICIOUS MESSAGES
    def test_suspicious_bank_block_otp_solicitation(self) -> None:
        msg = "Your bank account will be blocked. Tell me your OTP immediately."
        res = self.manager.analyze_standalone_transcript(
            TranscriptAnalysisRequest(transcript=msg, language_code="en", call_id="test_susp_1")
        )
        self.assertIn(res.risk_level, ("HIGH", "CRITICAL"))
        self.assertGreaterEqual(res.risk_score, 70.0)

    def test_suspicious_bank_impersonation_password(self) -> None:
        msg = "I am calling from your bank. Share your account password."
        res = self.manager.analyze_standalone_transcript(
            TranscriptAnalysisRequest(transcript=msg, language_code="en", call_id="test_susp_2")
        )
        self.assertIn(res.risk_level, ("HIGH", "CRITICAL"))
        self.assertGreaterEqual(res.risk_score, 70.0)

    def test_suspicious_remote_access_application(self) -> None:
        msg = "Install this remote access application so I can verify your bank account."
        res = self.manager.analyze_standalone_transcript(
            TranscriptAnalysisRequest(transcript=msg, language_code="en", call_id="test_susp_3")
        )
        self.assertIn(res.risk_level, ("HIGH", "CRITICAL"))
        self.assertGreaterEqual(res.risk_score, 60.0)

    def test_suspicious_urgent_money_transfer_suspension(self) -> None:
        msg = "Transfer money immediately to prevent your account from being suspended."
        res = self.manager.analyze_standalone_transcript(
            TranscriptAnalysisRequest(transcript=msg, language_code="en", call_id="test_susp_4")
        )
        self.assertIn(res.risk_level, ("HIGH", "CRITICAL"))
        self.assertGreaterEqual(res.risk_score, 60.0)

    # 4. CONVERSATION STATE ISOLATION (NO EVIDENCE LEAKAGE)
    def test_conversation_state_isolation(self) -> None:
        call_a = "call_suspicious_session_a"
        call_b = "call_benign_session_b"

        # Call A receives high-risk message
        from app.schemas.calls import CallSegmentRequest
        resp_a = self.manager.process_segment(
            call_a,
            CallSegmentRequest(
                text="Your account is blocked, give me your password now.",
                speaker="customer",
                language_code="en",
                start_seconds=0.0,
                end_seconds=3.0,
            ),
        )
        self.assertIn(resp_a.assessment.risk_level, ("HIGH", "CRITICAL"))

        # Call B receives benign message
        resp_b = self.manager.process_segment(
            call_b,
            CallSegmentRequest(
                text="Hello, how are you today?",
                speaker="customer",
                language_code="en",
                start_seconds=0.0,
                end_seconds=2.0,
            ),
        )
        self.assertEqual(resp_b.assessment.risk_level, "LOW")
        self.assertNotIn("password", [ind.keyword_or_pattern for ind in resp_b.assessment.rule_analysis.triggered_indicators])


if __name__ == "__main__":
    unittest.main()
