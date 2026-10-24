"""
Regression tests for stale transcript elimination, duplicate event prevention,
and segment-level vs cumulative call risk decoupling.
"""
from __future__ import annotations

import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock

from app.schemas.calls import CallSegmentRequest
from app.services.conversation_manager import ConversationManager
from app.services.live_audio_processor import DashboardBroadcaster, LiveAudioSession
from app.services.transcription_service import BaseSpeechToTextProvider, SarvamSaarasProvider, TranscriptionResponse


class StaleTranscriptsAndDuplicatesTestSuite(unittest.TestCase):
    """Verifies that individual utterances are evaluated independently and not contaminated by prior state."""

    def setUp(self) -> None:
        self.manager = ConversationManager()

    def test_01_benign_tokens_never_inherit_prior_scam_indicators(self) -> None:
        call_id = "call_decoupled_test_01"

        # Segment 1: Severe OTP solicitation
        s1 = self.manager.process_segment(
            call_id,
            CallSegmentRequest(
                text="Please tell me your 6 digit OTP right now or your account will be suspended.",
                start_seconds=0.0,
                end_seconds=4.0,
            ),
        )
        self.assertIn(s1.segment_assessment.risk_level, ("HIGH", "CRITICAL"))
        self.assertGreaterEqual(s1.segment_assessment.risk_score, 70.0)
        self.assertTrue(len(s1.segment_assessment.indicators) > 0)
        self.assertEqual(s1.cumulative_assessment.risk_level, s1.segment_assessment.risk_level)

        # Segment 2: Harmless single token greeting ("Hello")
        s2 = self.manager.process_segment(
            call_id,
            CallSegmentRequest(text="Hello", start_seconds=4.0, end_seconds=5.0),
        )
        # MUST NOT inherit OTP solicitation indicators
        self.assertEqual(len(s2.segment_assessment.indicators), 0)
        self.assertEqual(s2.segment_assessment.risk_score, 0.0)
        self.assertIn(s2.segment_assessment.risk_level, ("LOW", "UNKNOWN"))
        # Call posture remains aware of prior scam
        self.assertIn(s2.cumulative_assessment.risk_level, ("HIGH", "CRITICAL"))

        # Segment 3: Harmless acronym / student inquiry ("B.Sc.")
        s3 = self.manager.process_segment(
            call_id,
            CallSegmentRequest(text="B.Sc.", start_seconds=5.0, end_seconds=6.0),
        )
        self.assertEqual(len(s3.segment_assessment.indicators), 0)
        self.assertEqual(s3.segment_assessment.risk_score, 0.0)
        self.assertIn(s3.segment_assessment.risk_level, ("LOW", "UNKNOWN"))

        # Segment 4: Harmless full conversational sentence
        s4 = self.manager.process_segment(
            call_id,
            CallSegmentRequest(
                text="Haanji main bol raha hoon, kya haal hai aapka?",
                start_seconds=6.0,
                end_seconds=10.0,
            ),
        )
        self.assertEqual(len(s4.segment_assessment.indicators), 0)
        self.assertEqual(s4.segment_assessment.risk_score, 0.0)
        self.assertEqual(s4.segment_assessment.risk_level, "LOW")
        # Call risk remains preserved
        self.assertGreaterEqual(s4.cumulative_assessment.risk_score, 70.0)

    def test_02_silent_or_unmarked_audio_never_fabricates_otp_text(self) -> None:
        """Verifies STT provider returns empty string for silence or unrecognised audio without a key."""
        stt = SarvamSaarasProvider()
        # Mock settings to have no live Sarvam key
        stt.settings.sarvam_api_key = ""

        # 16000 bytes of zeros (0.5s of silent 16kHz PCM)
        silent_pcm = bytes(16000)
        res = stt.transcribe_bytes(silent_pcm, "test_silence.wav", "auto")

        self.assertEqual(res.transcript, "")
        self.assertEqual(res.confidence, 0.0)
        self.assertNotIn("OTP", res.transcript)
        self.assertNotIn("आर्मी", res.transcript)
        self.assertNotIn("ਓਟੀਪੀ", res.transcript)

    def test_03_isolated_greetings_and_fillers_classified_as_safe(self) -> None:
        """Verifies common benign tokens evaluate with 0 risk and 0 indicators."""
        test_tokens = ["Hello", "Hmm", "Okay", "B.Sc.", "Haanji", "Theek hai"]
        for token in test_tokens:
            s = self.manager.process_segment(
                f"isolated_test_{token}",
                CallSegmentRequest(text=token, start_seconds=0.0, end_seconds=1.5),
            )
            self.assertEqual(
                s.segment_assessment.risk_score,
                0.0,
                f"Token '{token}' should have risk score 0.0, got {s.segment_assessment.risk_score}",
            )
            self.assertEqual(
                len(s.segment_assessment.indicators),
                0,
                f"Token '{token}' should have 0 indicators, got {s.segment_assessment.indicators}",
            )

    def test_04_live_audio_session_caption_chunk_uses_segment_assessment(self) -> None:
        """Verifies caption chunks emitted by LiveAudioSession reflect the segment, not historical call state."""
        broadcaster = DashboardBroadcaster()
        received_chunks = []

        class MockWs:
            async def send_json(self, payload):
                received_chunks.append(payload)

        mock_ws = MockWs()
        broadcaster.register(mock_ws)

        class MockSTT(BaseSpeechToTextProvider):
            @property
            def provider_name(self) -> str:
                return "mock"

            def __init__(self):
                self.transcripts = [
                    "Please share your OTP right now to verify",
                    "Hello, B.Sc. student here",
                ]
                self.idx = 0

            def transcribe_bytes(self, audio_bytes, filename, language_code):
                t = self.transcripts[self.idx % len(self.transcripts)]
                self.idx += 1
                return TranscriptionResponse(
                    provider="mock",
                    model="mock",
                    language_code="en-IN",
                    transcript=t,
                    confidence=0.95,
                    duration_seconds=2.0,
                )

        session = LiveAudioSession(
            call_id="call_ws_chunk_test_01",
            stt_provider=MockSTT(),
            conversation_manager=self.manager,
            telegram_service=self.manager.telegram_service,
            broadcaster=broadcaster,
            language_code="auto",
        )

        dummy_pcm = bytes(48000)

        # Slice 1: OTP scam
        asyncio.run(session._transcribe_and_evaluate_slice(session.channels[1], dummy_pcm))
        self.assertGreater(len(received_chunks), 0)
        chunk1 = received_chunks[-1]
        self.assertEqual(chunk1["type"], "caption_chunk")
        self.assertIn(chunk1["riskLevel"], ("HIGH", "CRITICAL"))
        self.assertIn("share your otp", chunk1["flaggedKeywords"])

        received_chunks.clear()

        # Slice 2: Benign Hello B.Sc. student
        asyncio.run(session._transcribe_and_evaluate_slice(session.channels[1], dummy_pcm))
        self.assertGreater(len(received_chunks), 0)
        chunk2 = received_chunks[-1]
        self.assertEqual(chunk2["type"], "caption_chunk")
        # MUST be LOW risk for this chunk!
        self.assertEqual(chunk2["riskLevel"], "LOW")
        self.assertEqual(chunk2["riskScore"], 0.0)
        self.assertEqual(chunk2["flaggedKeywords"], [])
        # But call level remains high!
        self.assertIn(chunk2["callRiskLevel"], ("HIGH", "CRITICAL"))

    def test_05_no_duplicate_delivery_over_websocket(self) -> None:
        """Verifies a single websocket does not receive duplicate events when registered with broadcaster."""
        broadcaster = DashboardBroadcaster()
        delivery_count = 0

        class CountingWs:
            async def send_json(self, payload):
                nonlocal delivery_count
                if payload.get("type") == "caption_chunk":
                    delivery_count += 1

        c_ws = CountingWs()
        broadcaster.register(c_ws)

        class SingleMockSTT(BaseSpeechToTextProvider):
            @property
            def provider_name(self) -> str:
                return "mock"

            def transcribe_bytes(self, audio_bytes, filename, language_code):
                return TranscriptionResponse(
                    provider="mock",
                    model="mock",
                    language_code="en-IN",
                    transcript="Hello how are you doing",
                    confidence=0.95,
                    duration_seconds=1.5,
                )

        # In routes_live_ingest, on_event_callback=None because c_ws is in broadcaster
        session = LiveAudioSession(
            call_id="call_no_dup_01",
            stt_provider=SingleMockSTT(),
            conversation_manager=self.manager,
            telegram_service=self.manager.telegram_service,
            broadcaster=broadcaster,
            language_code="auto",
            on_event_callback=None,
        )

        dummy_pcm = bytes(48000)
        asyncio.run(session._transcribe_and_evaluate_slice(session.channels[1], dummy_pcm))

        # "Hello how are you doing" is 5 words, so TARGET_WORDS_PER_CHUNK (8) emits exactly 1 chunk
        self.assertEqual(delivery_count, 1, f"Expected exactly 1 caption_chunk delivered, got {delivery_count}")


if __name__ == "__main__":
    unittest.main()
