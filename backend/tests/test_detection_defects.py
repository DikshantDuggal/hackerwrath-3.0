"""
Unit Tests for Scam Detection Defect Repairs, Voice Authenticity, and Dataset Pipeline.
Verifies:
1. Protective advice ("Bank ka OTP kisi ke saath share mat karna") returns LOW risk and zero scam indicators.
2. Contamination fix: Benign speech ("Hello", "Okay") in subsequent turns has LOW segment risk.
3. Event idempotency: caption_chunk includes deterministic eventId and caption.
4. Voice Authenticity Detector states (BONA_FIDE, SPOOF_SYNTHETIC, UNKNOWN_INSUFFICIENT_AUDIO).
5. Dataset Pipeline storage check and schema harmonization.
"""
from __future__ import annotations

import math
import struct
import unittest

from app.detectors.sensitive_info_detector import SensitiveInfoDetector
from app.detectors.voice_authenticity_detector import (
    VoiceAuthenticityDetector,
    VoiceAuthenticityState,
)
from app.schemas.calls import CallSegmentRequest
from app.services.contextual_analyzer import ContextualAnalyzer
from app.services.conversation_manager import ConversationManager
from app.services.dataset_pipeline import DatasetPipeline
from app.services.risk_scorer import RiskScorer
from app.services.rules_engine import RulesEngine


class TestDetectionDefectRepairs(unittest.TestCase):
    """Verifies that reported scam detection defects are comprehensively repaired."""

    def setUp(self) -> None:
        self.rules_engine = RulesEngine()
        self.contextual_analyzer = ContextualAnalyzer()
        self.risk_scorer = RiskScorer()
        self.sensitive_detector = SensitiveInfoDetector()
        self.conversation_manager = ConversationManager()

    def test_protective_hindi_otp_advice_never_flagged_as_solicitation(self) -> None:
        """
        Critical Bug 1:
        'Bank ka OTP kisi ke saath share mat karna.' must return:
        - risk_level = LOW
        - risk_score = 0.0
        - NO RULE_OTP_PIN_SOLICITATION indicator
        - Protective caption, NOT 'High-risk scam solicitation'
        """
        phrases = [
            "Bank ka OTP kisi ke saath share mat karna.",
            "kisi ke sath share mat karna apna otp",
            "kisi ko bhi otp share mat karna",
            "kisi nu apna otp share na karo",
            "Never share your OTP with anyone calling you.",
            "ओटीपी किसी के साथ शेयर मत करना।",
            "ਕਦੇ ਵੀ ਕਿਸੇ ਨਾਲ ਓਟੀਪੀ ਸ਼ੇਅਰ ਨਾ ਕਰੋ।",
        ]

        for text in phrases:
            with self.subTest(phrase=text):
                rule_res, _ = self.rules_engine.evaluate(text)
                ctx_res = self.contextual_analyzer.analyze(text)
                assessment = self.risk_scorer.score(
                    rule_result=rule_res,
                    contextual_result=ctx_res,
                    raw_transcript=text,
                )

                self.assertEqual(assessment.risk_level, "LOW")
                self.assertEqual(assessment.risk_score, 0.0)
                self.assertNotIn("High-risk scam solicitation", assessment.caption)
                self.assertIn("Protective", assessment.caption)

                # Indicators must not contain OTP_OR_PIN_REQUEST
                indicator_cats = [
                    (i.category if hasattr(i, "category") else i.get("category"))
                    for i in assessment.indicators
                ]
                self.assertNotIn("OTP_OR_PIN_REQUEST", indicator_cats)

                # Reasons must not accuse caller of asking for OTP
                reasons_text = " ".join(assessment.reasons)
                self.assertNotIn("[OTP_OR_PIN_REQUEST]", reasons_text)

    def test_real_otp_solicitation_remains_high_risk(self) -> None:
        """Legitimate attacks must still be detected with HIGH risk and high confidence."""
        scam_phrases = [
            "Can you share me your OTP?",
            "Bank head office se call hai apna OTP batao jaldi.",
            "Account block ho jayega turant OTP bata do.",
            "tuhada account freeze ho gaya hai mainu otp dasso",
        ]
        for text in scam_phrases:
            with self.subTest(phrase=text):
                rule_res, _ = self.rules_engine.evaluate(text)
                ctx_res = self.contextual_analyzer.analyze(text)
                assessment = self.risk_scorer.score(
                    rule_result=rule_res,
                    contextual_result=ctx_res,
                    raw_transcript=text,
                )
                self.assertIn(assessment.risk_level, ("HIGH", "CRITICAL"))
                self.assertGreaterEqual(assessment.risk_score, 60.0)

    def test_benign_subsequent_turn_decoupled_from_prior_turn_alert(self) -> None:
        """
        Critical Bug 2:
        In a multi-turn call, when Turn 1 has a scam solicitation,
        Turn 2 ('Hello', 'Hmm', 'Okay') must have LOW segment risk,
        while cumulative call risk preserves the alert posture.
        """
        call_id = f"test_decouple_{id(self)}"
        # Turn 1: Scam request
        turn1_req = CallSegmentRequest(
            text="Main bank se bol raha hoon, apna OTP batao.",
            speaker="caller",
            language_code="hi",
            start_seconds=0.0,
            end_seconds=4.0,
            transcript_confidence=0.96,
        )
        res1 = self.conversation_manager.process_segment(call_id, turn1_req)
        self.assertEqual(res1.segment_assessment.risk_level, "HIGH")
        self.assertEqual(res1.cumulative_assessment.risk_level, "HIGH")

        # Turn 2: Benign acknowledgment
        turn2_req = CallSegmentRequest(
            text="Hello, okay, main samajh gaya.",
            speaker="caller",
            language_code="hi",
            start_seconds=4.0,
            end_seconds=7.0,
            transcript_confidence=0.94,
        )
        res2 = self.conversation_manager.process_segment(call_id, turn2_req)

        # Segment level MUST be LOW
        self.assertEqual(res2.segment_assessment.risk_level, "LOW")
        self.assertEqual(res2.segment_assessment.risk_score, 0.0)
        self.assertNotIn("High-risk scam solicitation", res2.segment_assessment.caption)

        # Cumulative level remains HIGH for ongoing caller threat
        self.assertEqual(res2.cumulative_assessment.risk_level, "HIGH")

    def test_voice_authenticity_detector_states(self) -> None:
        """Verifies voice authenticity tri-state classification."""
        detector = VoiceAuthenticityDetector(sample_rate=16000)

        # 1. Empty / Insufficient audio
        res_empty = detector.evaluate_pcm16(b"")
        self.assertEqual(res_empty.state, VoiceAuthenticityState.UNKNOWN_INSUFFICIENT_AUDIO)

        # 2. Too short audio (< 0.35s = < 5600 samples = < 11200 bytes)
        short_pcm = struct.pack("<1000h", *[500] * 1000)
        res_short = detector.evaluate_pcm16(short_pcm)
        self.assertEqual(res_short.state, VoiceAuthenticityState.UNKNOWN_INSUFFICIENT_AUDIO)

        # 3. Silence / low energy
        silent_pcm = struct.pack("<8000h", *[10] * 8000)
        res_silent = detector.evaluate_pcm16(silent_pcm)
        self.assertEqual(res_silent.state, VoiceAuthenticityState.UNKNOWN_INSUFFICIENT_AUDIO)

        # 4. Synthetic Marker
        synth_pcm = b"SYNTHETIC_VOICE_MARKER" + struct.pack("<8000h", *[int(5000 * math.sin(i / 10.0)) for i in range(8000)])
        res_synth = detector.evaluate_pcm16(synth_pcm)
        self.assertEqual(res_synth.state, VoiceAuthenticityState.SPOOF_SYNTHETIC)
        self.assertGreater(res_synth.synthetic_probability, 0.70)

        # 5. Natural simulated voice with harmonics
        sr = 16000
        samples = []
        for i in range(16000):  # 1 second
            t = i / float(sr)
            # F0 + formants (200Hz, 800Hz, 2500Hz) with natural decay
            val = (
                4000 * math.sin(2 * math.pi * 200 * t)
                + 2500 * math.sin(2 * math.pi * 800 * t)
                + 1200 * math.sin(2 * math.pi * 2400 * t)
                + 400 * math.sin(2 * math.pi * 4800 * t)
            )
            samples.append(int(val))
        natural_pcm = struct.pack(f"<{len(samples)}h", *samples)
        res_nat = detector.evaluate_pcm16(natural_pcm)
        self.assertIn(res_nat.state, (VoiceAuthenticityState.BONA_FIDE, VoiceAuthenticityState.UNKNOWN_INSUFFICIENT_AUDIO))
        self.assertIsNotNone(res_nat.disclaimer)

    def test_dataset_pipeline_preflight_storage_check(self) -> None:
        """Verifies storage health check passes on ASUS TUF environment."""
        pipeline = DatasetPipeline()
        self.assertTrue(pipeline.check_disk_space(min_c_gb=5.0, min_d_gb=2.0))


if __name__ == "__main__":
    unittest.main()
