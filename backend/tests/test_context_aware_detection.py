"""
Comprehensive Regression Test Suite for Context-Aware Scam Detection.
Validates Scenarios A through N:
  A: Caller requesting bank OTP -> HIGH
  B: Caller requesting banking PIN -> HIGH
  C: Caller pressuring for auth code -> HIGH
  D: Warning never to share OTP -> LOW + counter_evidence
  E: Educational discussion about OTP fraud -> LOW
  F: Quoted suspicious caller -> LOW
  G: Legitimate mention of OTP -> LOW
  H: Incomplete transcript 'OTP' -> UNKNOWN
  I: Hindi/Hinglish sensitive info request -> HIGH
  J: Punjabi sensitive info request -> HIGH
  K: Strong deterministic indicator + low-risk LLM -> Safety override preserves HIGH
  L: Low-quality/very brief transcript -> UNKNOWN
  M: Duplicate segments -> Deduplicated
  N: Urgency without scam indicators -> LOW/MEDIUM (no false alarm)
"""
from __future__ import annotations

import unittest
from typing import List, Optional
from app.core.config import Settings
from app.detectors.sensitive_info_detector import SensitiveInfoDetector
from app.repositories.conversation_repository import InMemoryConversationRepository
from app.schemas.analysis import (
    ContextualAnalysisOutput,
    RuleEngineResult,
    TranscriptAnalysisRequest,
    TriggeredIndicator,
)
from app.schemas.calls import CallSegmentRequest
from app.services.contextual_analyzer import ContextualAnalyzer
from app.services.conversation_manager import ConversationManager
from app.services.keyword_sync_service import KeywordSyncService
from app.services.risk_scorer import RiskScorer
from app.services.rules_engine import RulesEngine


class TestContextAwareScamDetection(unittest.TestCase):
    """Test suite covering scenarios A through N for context-aware scam detection."""

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

    # -------------------------------------------------------------------------
    # SCENARIO A: Caller requesting bank OTP
    # -------------------------------------------------------------------------
    def test_scenario_a_caller_requesting_bank_otp(self) -> None:
        """Caller requests OTP with bank account block threat -> HIGH risk."""
        text = "Sir, aapka bank account block ho jayega. Verification ke liye OTP bata do."
        assessment = self.manager.analyze_standalone_transcript(
            TranscriptAnalysisRequest(transcript=text, language_code="hi")
        )
        self.assertIn(assessment.risk_level, ("HIGH", "CRITICAL"))
        self.assertGreaterEqual(assessment.risk_score, 70.0)
        self.assertEqual(assessment.status, "success")
        self.assertIn("OTP", assessment.explanation)
        self.assertIn("independently verify", assessment.recommended_action.lower())
        self.assertIn("never share otp", assessment.recommended_action.lower())

    # -------------------------------------------------------------------------
    # SCENARIO B: Caller requesting banking PIN
    # -------------------------------------------------------------------------
    def test_scenario_b_caller_requesting_banking_pin(self) -> None:
        """Caller solicits 4-digit ATM or UPI PIN -> HIGH risk."""
        text = "Please share your 4-digit ATM PIN or UPI PIN to verify your refund amount."
        assessment = self.manager.analyze_standalone_transcript(
            TranscriptAnalysisRequest(transcript=text, language_code="en")
        )
        self.assertIn(assessment.risk_level, ("HIGH", "CRITICAL"))
        self.assertGreaterEqual(assessment.risk_score, 70.0)
        self.assertTrue(any("pin" in ind.get("category", "").lower() or "credential" in ind.get("category", "").lower() for ind in assessment.indicators))

    # -------------------------------------------------------------------------
    # SCENARIO C: Caller pressuring for auth code
    # -------------------------------------------------------------------------
    def test_scenario_c_caller_pressuring_for_auth_code(self) -> None:
        """Caller demands authentication code with disconnection pressure -> HIGH risk."""
        text = "We sent an authentication code to your mobile. Read it out to me right now or your service will be disconnected."
        assessment = self.manager.analyze_standalone_transcript(
            TranscriptAnalysisRequest(transcript=text, language_code="en")
        )
        self.assertIn(assessment.risk_level, ("HIGH", "CRITICAL"))
        self.assertGreaterEqual(assessment.risk_score, 70.0)

    # -------------------------------------------------------------------------
    # SCENARIO D: Warning never to share OTP
    # -------------------------------------------------------------------------
    def test_scenario_d_protective_warning_never_share_otp(self) -> None:
        """Warning someone NOT to share OTP -> LOW risk + counter_evidence."""
        phrases = [
            "Bank ka OTP kisi ke saath share mat karna.",
            "Never share your OTP or UPI PIN with anyone on a phone call.",
            "Kabhi bhi kisi ko apna OTP mat batana.",
        ]
        for text in phrases:
            assessment = self.manager.analyze_standalone_transcript(
                TranscriptAnalysisRequest(transcript=text, language_code="auto")
            )
            self.assertEqual(assessment.risk_level, "LOW", f"Failed for text: {text}")
            self.assertLessEqual(assessment.risk_score, 20.0)
            self.assertGreater(len(assessment.counter_evidence), 0, f"Expected counter_evidence for: {text}")

    # -------------------------------------------------------------------------
    # SCENARIO E: Educational discussion about OTP fraud
    # -------------------------------------------------------------------------
    def test_scenario_e_educational_discussion_about_otp_fraud(self) -> None:
        """General discussion about fraud methods -> LOW risk."""
        text = "Cyber criminals often call people pretending to be bank officials and ask for OTP. Many OTP fraud cases are reported every day."
        assessment = self.manager.analyze_standalone_transcript(
            TranscriptAnalysisRequest(transcript=text, language_code="en")
        )
        self.assertEqual(assessment.risk_level, "LOW")
        self.assertLessEqual(assessment.risk_score, 25.0)
        self.assertGreater(len(assessment.counter_evidence), 0)

    # -------------------------------------------------------------------------
    # SCENARIO F: Quoted suspicious caller
    # -------------------------------------------------------------------------
    def test_scenario_f_quoted_suspicious_caller(self) -> None:
        """Reporting what a past caller said while refusing -> LOW risk."""
        text = "The caller asked me to share OTP, but I hung up immediately."
        assessment = self.manager.analyze_standalone_transcript(
            TranscriptAnalysisRequest(transcript=text, language_code="en")
        )
        self.assertEqual(assessment.risk_level, "LOW")
        self.assertLessEqual(assessment.risk_score, 25.0)

    # -------------------------------------------------------------------------
    # SCENARIO G: Legitimate mention of OTP
    # -------------------------------------------------------------------------
    def test_scenario_g_legitimate_mention_of_otp(self) -> None:
        """Automated system notification or personal reference -> LOW risk."""
        texts = [
            "Your OTP for logging into your account is 482910.",
            "I received an OTP for my train ticket booking earlier.",
        ]
        for text in texts:
            assessment = self.manager.analyze_standalone_transcript(
                TranscriptAnalysisRequest(transcript=text, language_code="en")
            )
            self.assertEqual(assessment.risk_level, "LOW")
            self.assertLessEqual(assessment.risk_score, 20.0)

    # -------------------------------------------------------------------------
    # SCENARIO H: Incomplete transcript 'OTP'
    # -------------------------------------------------------------------------
    def test_scenario_h_incomplete_transcript_otp(self) -> None:
        """Isolated single keyword 'OTP' -> UNKNOWN risk + insufficient_evidence."""
        assessment = self.manager.analyze_standalone_transcript(
            TranscriptAnalysisRequest(transcript="OTP", language_code="auto")
        )
        self.assertEqual(assessment.risk_level, "UNKNOWN")
        self.assertEqual(assessment.status, "insufficient_evidence")
        self.assertGreater(len(assessment.limitations), 0)

    # -------------------------------------------------------------------------
    # SCENARIO I: Hindi / Hinglish sensitive info request
    # -------------------------------------------------------------------------
    def test_scenario_i_hindi_hinglish_sensitive_info_request(self) -> None:
        """Hindi and Hinglish credential solicitations -> HIGH risk."""
        samples = [
            "Sir verification complete karne ke liye jo message aaya hai uska code bataiye.",
            "Aapke phone pe 6 digit ka OTP aaya hoga, turant bata do account unblock karne ke liye.",
            "ओटीपी बताओ जल्दी से आपका बैंक खाता चालू हो जाएगा।",
        ]
        for text in samples:
            assessment = self.manager.analyze_standalone_transcript(
                TranscriptAnalysisRequest(transcript=text, language_code="hi")
            )
            self.assertIn(assessment.risk_level, ("HIGH", "CRITICAL"), f"Failed for: {text}")
            self.assertGreaterEqual(assessment.risk_score, 70.0)

    # -------------------------------------------------------------------------
    # SCENARIO J: Punjabi sensitive info request
    # -------------------------------------------------------------------------
    def test_scenario_j_punjabi_sensitive_info_request(self) -> None:
        """Punjabi (Gurmukhi & Romanized) sensitive requests -> HIGH risk."""
        samples = [
            "ਤੁਹਾਡੇ ਫ਼ੋਨ 'ਤੇ ਇੱਕ ਓਟੀਪੀ ਆਇਆ ਹੈ, ਮੈਨੂੰ ਤੁਰੰਤ ਦੱਸੋ ਨਹੀਂ ਤਾਂ ਖਾਤਾ ਬੰਦ ਹੋ ਜਾਵੇਗਾ।",
            "Tuhade phone te OTP aya hai, mainu turant dasso nahi ta bank khata band ho javega.",
        ]
        for text in samples:
            assessment = self.manager.analyze_standalone_transcript(
                TranscriptAnalysisRequest(transcript=text, language_code="pa")
            )
            self.assertIn(assessment.risk_level, ("HIGH", "CRITICAL"), f"Failed for: {text}")
            self.assertGreaterEqual(assessment.risk_score, 70.0)

    # -------------------------------------------------------------------------
    # SCENARIO K: Deterministic safety override preserves HIGH despite low-risk LLM
    # -------------------------------------------------------------------------
    def test_scenario_k_safety_override_preserves_high_despite_low_risk_llm(self) -> None:
        """An explicit OTP demand cannot be downgraded to LOW by a cautious/disagreeing LLM."""
        text = "Give me your OTP immediately or your account will be suspended."

        # Mock Contextual Analyzer returning overly cautious low risk score
        mock_contextual_output = ContextualAnalysisOutput(
            contextual_caption="Caller inquiring about account details",
            intent_classification="LEGITIMATE_INQUIRY",
            intent_risk_score=10.0,
            model_confidence=0.85,
            service_status="OK",
        )

        # Evaluate rules engine
        rule_res, _ = self.rules_engine.evaluate(text)

        # Score directly with the mock LLM output
        assessment = self.risk_scorer.score(
            rule_result=rule_res,
            contextual_result=mock_contextual_output,
            raw_transcript=text,
        )

        self.assertIn(assessment.risk_level, ("HIGH", "CRITICAL"))
        self.assertGreaterEqual(assessment.risk_score, 75.0)
        self.assertIn("Deterministic safety override", assessment.explanation)

    # -------------------------------------------------------------------------
    # SCENARIO L: Low-quality or very brief transcript
    # -------------------------------------------------------------------------
    def test_scenario_l_low_quality_or_very_brief_transcript(self) -> None:
        """Very brief transcript or low STT confidence -> UNKNOWN risk."""
        # Low confidence
        assessment1 = self.manager.analyze_standalone_transcript(
            TranscriptAnalysisRequest(
                transcript="Hello sir verify your details",
                transcript_confidence=0.45,  # Below 0.60 threshold
            )
        )
        self.assertEqual(assessment1.risk_level, "UNKNOWN")
        self.assertEqual(assessment1.status, "insufficient_evidence")

        # Brief utterance (< 3 words)
        assessment2 = self.manager.analyze_standalone_transcript(
            TranscriptAnalysisRequest(
                transcript="Hello yes",
                transcript_confidence=0.95,
            )
        )
        self.assertEqual(assessment2.risk_level, "UNKNOWN")
        self.assertEqual(assessment2.status, "insufficient_evidence")

    # -------------------------------------------------------------------------
    # SCENARIO M: Duplicate segments deduplication
    # -------------------------------------------------------------------------
    def test_scenario_m_duplicate_segments_deduplication(self) -> None:
        """Sending repeated duplicate segment retries does not inflate score or duplicate evidence."""
        call_id = "test_dup_call_901"
        segment = CallSegmentRequest(
            speaker="caller",
            text="Your bank account is blocked, give me the OTP code now.",
            start_seconds=0.0,
            end_seconds=4.0,
            transcript_confidence=0.94,
        )

        # First delivery
        resp1 = self.manager.process_segment(call_id, segment)
        initial_score = resp1.assessment.risk_score
        initial_evidence_count = len(resp1.assessment.evidence)

        # Second delivery (exact retry)
        resp2 = self.manager.process_segment(call_id, segment)
        self.assertEqual(resp2.duplicate_evidence_suppressed, 1)
        self.assertEqual(resp2.assessment.risk_score, initial_score)
        self.assertEqual(len(resp2.assessment.evidence), initial_evidence_count)

    # -------------------------------------------------------------------------
    # SCENARIO N: Urgency without scam indicators
    # -------------------------------------------------------------------------
    def test_scenario_n_urgency_without_scam_indicators(self) -> None:
        """Everyday benign urgency without financial or credential demands -> LOW risk."""
        texts = [
            "Please come quickly, the meeting is starting in 5 minutes, we are waiting for you!",
            "Jaldi aao bhai, train nikalne wali hai platform number do se.",
        ]
        for text in texts:
            assessment = self.manager.analyze_standalone_transcript(
                TranscriptAnalysisRequest(transcript=text, language_code="auto")
            )
            self.assertIn(assessment.risk_level, ("LOW", "MEDIUM"), f"Failed for text: {text}")
            self.assertLess(assessment.risk_score, 60.0)
            self.assertNotIn("CRITICAL", assessment.risk_level)
            self.assertNotIn("HIGH", assessment.risk_level)


if __name__ == "__main__":
    unittest.main()
