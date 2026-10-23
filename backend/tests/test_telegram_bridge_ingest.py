"""
Targeted Integration Tests for OnFloor Telegram Audio Bridge (/internal/live/ingest).

Covers:
1. WebSocket authentication (x-bridge-secret & query param fallback).
2. call_started handshake with protocolVersion: 1 and callId acknowledgment.
3. Dual-channel audio routing (0 = agent / local mic, 1 = customer / remote caller).
4. Audio frame decoding, sample offset tracking (uint32 LE), and alignment.
5. Empty, malformed, unaligned, and oversized frame rejection.
6. Duplicate frame suppression and audio gap tracking.
7. Session reconnection and callId resumption without duplicate sessions.
8. Prompt call_ended acknowledgment.
9. Browser stream isolation and regression prevention.
"""
from __future__ import annotations

import asyncio
import io
import json
import struct
import time
import unittest
from typing import Any, Dict, List

from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.api.routes_analysis import get_conversation_manager
from app.api.routes_live_ingest import get_bridge_registry
from app.api.routes_transcription import get_stt_provider
from app.core.config import Settings, get_settings
from app.main import create_app
from app.repositories.conversation_repository import InMemoryConversationRepository
from app.schemas.transcription import TimestampedSegment, TranscriptionResponse
from app.services.contextual_analyzer import ContextualAnalyzer
from app.services.conversation_manager import ConversationManager
from app.services.keyword_sync_service import KeywordSyncService
from app.services.live_audio_processor import DashboardBroadcaster, LiveAudioSession
from app.services.risk_scorer import RiskScorer
from app.services.rules_engine import RulesEngine
from app.services.telegram_service import TelegramAlertService
from app.services.transcription_service import BaseSpeechToTextProvider


class MockSTTProvider(BaseSpeechToTextProvider):
    def __init__(self, sample_transcript: str = "Sir please give me your OTP immediately"):
        self.sample_transcript = sample_transcript

    @property
    def provider_name(self) -> str:
        return "mock_sarvam"

    def transcribe_bytes(
        self, audio_bytes: bytes, filename: str = "audio.wav", language_code: str = "auto"
    ) -> TranscriptionResponse:
        return TranscriptionResponse(
            provider="mock_sarvam",
            model="saaras:v2",
            language_code="en-IN",
            transcript=self.sample_transcript,
            confidence=0.96,
            duration_seconds=2.0,
            segments=[
                TimestampedSegment(
                    start_seconds=0.0,
                    end_seconds=2.0,
                    text=self.sample_transcript,
                    speaker="caller",
                    confidence=0.96,
                )
            ],
            streaming_ready=True,
            operational_status="WORKING",
        )


class TelegramBridgeIngestTestSuite(unittest.TestCase):
    def setUp(self) -> None:
        self.secret = "test_bridge_secret_9988"
        self.settings = Settings(
            bridge_secret=self.secret,
            sarvam_api_key="",
            max_audio_file_size_mb=1.0,
            calibrated_probability_enabled=False,
            call_state_retention_seconds=3600,
        )

        self.sync_service = KeywordSyncService(settings=self.settings)
        self.rules_engine = RulesEngine(settings=self.settings, keyword_sync_service=self.sync_service)
        self.contextual_analyzer = ContextualAnalyzer(settings=self.settings)
        self.risk_scorer = RiskScorer(settings=self.settings)
        self.repo = InMemoryConversationRepository()
        self.conv_manager = ConversationManager(
            repository=self.repo,
            rules_engine=self.rules_engine,
            contextual_analyzer=self.contextual_analyzer,
            risk_scorer=self.risk_scorer,
            settings=self.settings,
        )
        self.mock_stt = MockSTTProvider()

        self.app = create_app()
        self.app.dependency_overrides[get_settings] = lambda: self.settings
        self.app.dependency_overrides[get_conversation_manager] = lambda: self.conv_manager
        self.app.dependency_overrides[get_stt_provider] = lambda: self.mock_stt
        self.client = TestClient(self.app)

    def tearDown(self) -> None:
        self.app.dependency_overrides.clear()

    def _receive_until(self, ws: Any, expected_type: str, timeout_iterations: int = 10) -> Dict[str, Any]:
        """Reads messages from WebSocket until expected type is found, ignoring interim events."""
        for _ in range(timeout_iterations):
            msg = ws.receive_json()
            if msg.get("type") == expected_type:
                return msg
        self.fail(f"Did not receive message of type '{expected_type}' within {timeout_iterations} reads")

    # 1. AUTHENTICATION TEST
    def test_01_bridge_authentication(self) -> None:
        # Valid header
        with self.client.websocket_connect(
            "/internal/live/ingest", headers={"x-bridge-secret": self.secret}
        ) as ws:
            ws.send_text(
                json.dumps({
                    "type": "call_started",
                    "protocolVersion": 1,
                    "telegramCallId": "tg_auth_01",
                    "customer": {"id": "111", "displayName": "Tester"},
                })
            )
            ack = ws.receive_json()
            self.assertEqual(ack["type"], "ack")
            ws.send_text(json.dumps({"type": "call_ended", "reason": "test_complete"}))
            ended = self._receive_until(ws, "ended")
            self.assertEqual(ended["type"], "ended")

        # Valid query param fallback
        with self.client.websocket_connect(f"/internal/live/ingest?secret={self.secret}") as ws:
            ws.send_text(
                json.dumps({
                    "type": "call_started",
                    "protocolVersion": 1,
                    "telegramCallId": "tg_auth_02",
                    "customer": {"id": "222", "displayName": "Tester 2"},
                })
            )
            ack = ws.receive_json()
            self.assertEqual(ack["type"], "ack")
            ws.send_text(json.dumps({"type": "call_ended", "reason": "test_complete"}))
            ended = self._receive_until(ws, "ended")
            self.assertEqual(ended["type"], "ended")

        # Invalid secret rejected with close code 1008
        with self.assertRaises(WebSocketDisconnect) as cm:
            with self.client.websocket_connect(
                "/internal/live/ingest", headers={"x-bridge-secret": "wrong_secret"}
            ) as ws:
                ws.receive_text()
        self.assertEqual(cm.exception.code, 1008)

    # 2. CALL START AND PROTOCOL VERSION NEGOTIATION
    def test_02_call_started_handshake_and_error_handling(self) -> None:
        with self.client.websocket_connect(
            "/internal/live/ingest", headers={"x-bridge-secret": self.secret}
        ) as ws:
            # Malformed JSON
            ws.send_text("THIS IS NOT JSON")
            err_msg = ws.receive_json()
            self.assertEqual(err_msg["type"], "error")
            self.assertEqual(err_msg["code"], "MALFORMED_JSON")

            # Unsupported protocolVersion (e.g. 2)
            ws.send_text(
                json.dumps({
                    "type": "call_started",
                    "protocolVersion": 99,
                    "telegramCallId": "tg_unsupported_ver",
                })
            )
            err_proto = ws.receive_json()
            self.assertEqual(err_proto["type"], "error")
            self.assertEqual(err_proto["code"], "UNSUPPORTED_PROTOCOL")

            # Valid protocolVersion 1
            ws.send_text(
                json.dumps({
                    "type": "call_started",
                    "protocolVersion": 1,
                    "telegramCallId": "tg_valid_ver",
                    "customer": {"id": "333", "displayName": "Customer 333"},
                })
            )
            ack = ws.receive_json()
            self.assertEqual(ack["type"], "ack")
            self.assertEqual(ack["protocolVersion"], 1)
            self.assertTrue(ack["callId"].startswith("tg_call_"))

            # Clean exit
            ws.send_text(json.dumps({"type": "call_ended", "reason": "hangup"}))
            ended = self._receive_until(ws, "ended")
            self.assertEqual(ended["type"], "ended")
            self.assertEqual(ended["callId"], ack["callId"])

    # 3. DUAL-CHANNEL AUDIO FRAME DECODING & SEPARATION
    def test_03_dual_channel_routing_and_sample_offsets(self) -> None:
        registry = get_bridge_registry()
        with self.client.websocket_connect(
            "/internal/live/ingest", headers={"x-bridge-secret": self.secret}
        ) as ws:
            ws.send_text(
                json.dumps({
                    "type": "call_started",
                    "protocolVersion": 1,
                    "telegramCallId": "tg_dual_ch",
                    "customer": {"id": "444", "displayName": "Dual Channel Customer"},
                })
            )
            ack = ws.receive_json()
            call_id = ack["callId"]

            session = registry.get(call_id)
            self.assertIsNotNone(session)
            self.assertIn(0, session.channels)  # Agent channel
            self.assertIn(1, session.channels)  # Customer channel
            self.assertEqual(session.channels[0].speaker, "agent")
            self.assertEqual(session.channels[1].speaker, "customer")

            # Frame for Channel 0 (agent / local mic): offset 0, 1600 samples (3200 bytes)
            frame_ch0_1 = struct.pack("<BI", 0, 0) + (b"\x01\x00" * 1600)
            ws.send_bytes(frame_ch0_1)

            # Frame for Channel 1 (customer / remote voice): offset 0, 1600 samples (3200 bytes)
            frame_ch1_1 = struct.pack("<BI", 1, 0) + (b"\x02\x00" * 1600)
            ws.send_bytes(frame_ch1_1)

            # Frame for Channel 0: offset 1600, 1600 samples
            frame_ch0_2 = struct.pack("<BI", 0, 1600) + (b"\x01\x00" * 1600)
            ws.send_bytes(frame_ch0_2)

            # Frame for Channel 1: offset 1600, 1600 samples
            frame_ch1_2 = struct.pack("<BI", 1, 1600) + (b"\x02\x00" * 1600)
            ws.send_bytes(frame_ch1_2)

            # Check that channel 0 and channel 1 received their respective frames
            for _ in range(50):
                if session.channels[0].total_packets_received == 2 and session.channels[1].total_packets_received == 2:
                    break
                time.sleep(0.01)
            self.assertEqual(session.channels[0].total_packets_received, 2)
            self.assertEqual(session.channels[1].total_packets_received, 2)
            self.assertEqual(session.channels[0].next_expected_sample, 3200)
            self.assertEqual(session.channels[1].next_expected_sample, 3200)

            ws.send_text(json.dumps({"type": "call_ended", "reason": "hangup"}))
            ended = self._receive_until(ws, "ended")
            self.assertEqual(ended["type"], "ended")
            self.assertIn("channels", ended["summary"])
            self.assertEqual(ended["summary"]["channels"]["ch_0"]["speaker"], "agent")
            self.assertEqual(ended["summary"]["channels"]["ch_1"]["speaker"], "customer")

    # 4. MALFORMED, UNALIGNED, OVERSIZED, AND PRE-ACK FRAMES
    def test_04_malformed_and_oversized_frame_rejection(self) -> None:
        registry = get_bridge_registry()
        with self.client.websocket_connect(
            "/internal/live/ingest", headers={"x-bridge-secret": self.secret}
        ) as ws:
            # Pre-ack frame before call_started: must be safely rejected
            ws.send_bytes(struct.pack("<BI", 1, 0) + (b"\x00\x00" * 100))

            ws.send_text(
                json.dumps({
                    "type": "call_started",
                    "protocolVersion": 1,
                    "telegramCallId": "tg_malformed_test",
                })
            )
            ack = ws.receive_json()
            call_id = ack["callId"]
            session = registry.get(call_id)
            self.assertIsNotNone(session)

            # Malformed frame: < 5 bytes
            ws.send_bytes(b"\x00\x01\x02")

            # Malformed frame: unaligned odd PCM bytes (5 bytes header + 3 bytes PCM)
            ws.send_bytes(struct.pack("<BI", 1, 0) + b"\x01\x02\x03")

            # Invalid channel: channel 5 (only 0 and 1 are supported)
            ws.send_bytes(struct.pack("<BI", 5, 0) + (b"\x00\x00" * 100))

            # Oversized frame: > 65536 bytes
            ws.send_bytes(struct.pack("<BI", 1, 0) + (b"\x00\x00" * 33000))

            # Valid frame after malformed frames: must still be accepted
            ws.send_bytes(struct.pack("<BI", 1, 0) + (b"\x00\x00" * 800))
            for _ in range(50):
                if session.channels[1].total_packets_received == 1:
                    break
                time.sleep(0.01)
            self.assertEqual(session.channels[1].total_packets_received, 1)

            ws.send_text(json.dumps({"type": "call_ended", "reason": "hangup"}))
            ws.receive_json()

    # 5. DUPLICATE FRAMES AND AUDIO GAP HANDLING
    def test_05_duplicate_offsets_and_audio_gaps(self) -> None:
        registry = get_bridge_registry()
        with self.client.websocket_connect(
            "/internal/live/ingest", headers={"x-bridge-secret": self.secret}
        ) as ws:
            ws.send_text(
                json.dumps({
                    "type": "call_started",
                    "protocolVersion": 1,
                    "telegramCallId": "tg_offset_test",
                })
            )
            ack = ws.receive_json()
            call_id = ack["callId"]
            session = registry.get(call_id)
            self.assertIsNotNone(session)

            # Packet 1: offset 0, 1600 samples (next_expected_sample becomes 1600)
            ws.send_bytes(struct.pack("<BI", 1, 0) + (b"\x00\x00" * 1600))
            for _ in range(50):
                if session.channels[1].next_expected_sample == 1600:
                    break
                time.sleep(0.01)
            self.assertEqual(session.channels[1].next_expected_sample, 1600)

            # Packet 2 (DUPLICATE): re-send offset 0, 1600 samples
            ws.send_bytes(struct.pack("<BI", 1, 0) + (b"\x00\x00" * 1600))
            for _ in range(50):
                if session.channels[1].total_duplicate_frames == 1:
                    break
                time.sleep(0.01)
            # Must be flagged as duplicate and suppressed
            self.assertEqual(session.channels[1].total_duplicate_frames, 1)
            self.assertEqual(session.channels[1].next_expected_sample, 1600)

            # Packet 3 (GAP): send offset 4800 (gap of 3200 samples from 1600)
            ws.send_bytes(struct.pack("<BI", 1, 4800) + (b"\x00\x00" * 1600))

            ws.send_text(json.dumps({"type": "call_ended", "reason": "hangup"}))
            ended = self._receive_until(ws, "ended")
            self.assertEqual(ended["type"], "ended")
            self.assertEqual(ended["summary"]["channels"]["ch_1"]["duplicateFrames"], 1)
            self.assertEqual(ended["summary"]["channels"]["ch_1"]["gapSamples"], 3200)

    # 6. RECONNECTION AND CALL ID RESUMPTION
    def test_06_reconnection_and_call_id_resumption(self) -> None:
        registry = get_bridge_registry()

        # Session 1: initial connection
        call_id = None
        with self.client.websocket_connect(
            "/internal/live/ingest", headers={"x-bridge-secret": self.secret}
        ) as ws1:
            ws1.send_text(
                json.dumps({
                    "type": "call_started",
                    "protocolVersion": 1,
                    "telegramCallId": "tg_reconnect_peer_123",
                    "customer": {"id": "999", "displayName": "Reconnect User"},
                })
            )
            ack1 = ws1.receive_json()
            call_id = ack1["callId"]

            # Stream one frame
            ws1.send_bytes(struct.pack("<BI", 1, 0) + (b"\x00\x00" * 1600))
            # Disconnect unexpectedly (no call_ended sent)

        self.assertIsNotNone(call_id)
        # Session must remain in registry during the 15-second grace period
        session_before = registry.get(call_id)
        self.assertIsNotNone(session_before)

        # Session 2: reconnect within grace period with the acknowledged callId
        with self.client.websocket_connect(
            "/internal/live/ingest", headers={"x-bridge-secret": self.secret}
        ) as ws2:
            ws2.send_text(
                json.dumps({
                    "type": "call_started",
                    "protocolVersion": 1,
                    "telegramCallId": "tg_reconnect_peer_123",
                    "callId": call_id,  # Resume existing callId
                })
            )
            ack2 = ws2.receive_json()
            self.assertEqual(ack2["type"], "ack")
            # Server MUST return the exact same callId!
            self.assertEqual(ack2["callId"], call_id)

            # Stream second frame continuing from offset 1600
            ws2.send_bytes(struct.pack("<BI", 1, 1600) + (b"\x00\x00" * 1600))

            # Send call_ended to finalize
            ws2.send_text(json.dumps({"type": "call_ended", "reason": "telegram_hangup"}))
            ended = self._receive_until(ws2, "ended")
            self.assertEqual(ended["type"], "ended")
            self.assertEqual(ended["callId"], call_id)

        # After explicit call_ended, session is removed from registry
        self.assertIsNone(registry.get(call_id))

    # 7. BROWSER STREAM WORKFLOW ISOLATION & REGRESSION PREVENTION
    def test_07_browser_stream_workflow_isolation(self) -> None:
        with self.client.websocket_connect("/internal/live/browser-stream") as ws:
            ready = ws.receive_json()
            self.assertEqual(ready["type"], "session_ready")
            self.assertTrue(ready["callId"].startswith("web_live_"))
            self.assertEqual(ready["sampleRate"], 16000)

            # Stream raw 16kHz PCM16 bytes directly
            pcm_data = b"\x00\x01" * 800
            ws.send_bytes(pcm_data)

            # Stop browser stream
            ws.send_text(json.dumps({"type": "stop"}))


if __name__ == "__main__":
    unittest.main()
