"""
Unit & Integration Tests for LiveKit Cloud Real-Time Calling and AI Audio Worker.
Tests the full calling lifecycle:
- POST /calls/start
- POST /calls/{call_id}/accept
- POST /calls/{call_id}/reject
- POST /calls/{call_id}/end
- POST /calls/{call_id}/token
- GET /calls/{call_id}/status
- GET /calls/active
- State transitions, participant authorization, mock/cloud token issuance,
  multi-channel audio worker ingestion, and cleanup.
"""
from __future__ import annotations

import unittest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.schemas.livekit_calls import LiveKitCallDetail
from app.services.livekit_service import LiveKitCallManager, get_livekit_manager
from app.services.livekit_worker import LiveKitScamDetectionWorker, get_worker_manager
from app.schemas.transcription import TranscriptionResponse
from app.services.transcription_service import BaseSpeechToTextProvider


class MockSTT(BaseSpeechToTextProvider):
    @property
    def provider_name(self) -> str:
        return "mock"

    def transcribe_bytes(
        self,
        audio_bytes: bytes,
        filename: str = "audio.wav",
        language_code: str = "auto",
    ) -> TranscriptionResponse:
        return TranscriptionResponse(
            transcript="Mock transcript for LiveKit call test",
            language_code=language_code,
            confidence=0.95,
            duration_seconds=1.0,
            provider="mock",
        )


class TestLiveKitCalling(unittest.TestCase):
    def setUp(self) -> None:
        self.app = create_app()
        self.client = TestClient(self.app)
        self.manager = get_livekit_manager()
        # Reset state for isolation
        with self.manager._lock:
            self.manager._calls.clear()
            self.manager._room_to_call.clear()

    def test_start_call_success(self) -> None:
        response = self.client.post(
            "/calls/start",
            json={
                "caller_id": "alice",
                "recipient_id": "bob",
                "language_code": "hi",
                "enable_scam_detection": True,
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()
        self.assertTrue(data["call_id"].startswith("call_"))
        self.assertTrue(data["room_id"].startswith("room_"))
        self.assertEqual(data["caller_id"], "alice")
        self.assertEqual(data["recipient_id"], "bob")
        self.assertEqual(data["status"], "RINGING")
        self.assertTrue(data["ai_detection_active"])
        self.assertIn("scam call analysis is active", data["consent_notice"].lower())

    def test_start_call_validation_errors(self) -> None:
        # Empty recipient
        resp1 = self.client.post("/calls/start", json={"caller_id": "alice", "recipient_id": ""})
        self.assertIn(resp1.status_code, (400, 422))

        # Calling self
        resp2 = self.client.post("/calls/start", json={"caller_id": "alice", "recipient_id": "alice"})
        self.assertEqual(resp2.status_code, 400)
        self.assertIn("oneself", resp2.json()["detail"].lower())

    def test_call_lifecycle_accept_and_end(self) -> None:
        # 1. Start
        start_resp = self.client.post(
            "/calls/start",
            json={"caller_id": "rahul", "recipient_id": "priya"},
        )
        call_id = start_resp.json()["call_id"]

        # Check status endpoint
        status_resp = self.client.get(f"/calls/{call_id}/status")
        self.assertEqual(status_resp.status_code, 200)
        self.assertEqual(status_resp.json()["status"], "RINGING")

        # 2. Accept
        accept_resp = self.client.post(
            f"/calls/{call_id}/accept",
            json={"user_id": "priya"},
        )
        self.assertEqual(accept_resp.status_code, 200)
        self.assertEqual(accept_resp.json()["status"], "ACTIVE")

        # Active calls list should contain this call
        active_resp = self.client.get("/calls/active")
        self.assertEqual(active_resp.status_code, 200)
        active_ids = [c["call_id"] for c in active_resp.json()]
        self.assertIn(call_id, active_ids)

        # 3. End
        end_resp = self.client.post(
            f"/calls/{call_id}/end",
            json={"user_id": "rahul", "reason": "Completed conversation"},
        )
        self.assertEqual(end_resp.status_code, 200)
        self.assertEqual(end_resp.json()["status"], "ENDED")

        # Verify not in active calls anymore
        active_resp_after = self.client.get("/calls/active")
        active_ids_after = [c["call_id"] for c in active_resp_after.json()]
        self.assertNotIn(call_id, active_ids_after)

    def test_call_rejection(self) -> None:
        start_resp = self.client.post(
            "/calls/start",
            json={"caller_id": "unknown_spammer", "recipient_id": "victim"},
        )
        call_id = start_resp.json()["call_id"]

        reject_resp = self.client.post(
            f"/calls/{call_id}/reject",
            json={"user_id": "victim", "reason": "Potential spam caller"},
        )
        self.assertEqual(reject_resp.status_code, 200)
        self.assertEqual(reject_resp.json()["status"], "REJECTED")

        # Cannot accept rejected call
        cannot_accept = self.client.post(
            f"/calls/{call_id}/accept",
            json={"user_id": "victim"},
        )
        self.assertEqual(cannot_accept.status_code, 400)

    def test_token_generation_and_authorization(self) -> None:
        start_resp = self.client.post(
            "/calls/start",
            json={"caller_id": "caller1", "recipient_id": "receiver1"},
        )
        call_id = start_resp.json()["call_id"]
        room_id = start_resp.json()["room_id"]

        # Valid token for caller
        t_caller = self.client.post(
            f"/calls/{call_id}/token",
            json={"user_id": "caller1"},
        )
        self.assertEqual(t_caller.status_code, 200)
        caller_token_data = t_caller.json()
        self.assertTrue(len(caller_token_data["token"]) > 20)
        self.assertEqual(caller_token_data["room_id"], room_id)
        self.assertEqual(caller_token_data["participant_identity"], "caller1")
        self.assertIn("ai guardian is active", caller_token_data["ai_notice"].lower())

        # Valid token for receiver
        t_receiver = self.client.post(
            f"/calls/{call_id}/token",
            json={"user_id": "receiver1"},
        )
        self.assertEqual(t_receiver.status_code, 200)
        self.assertEqual(t_receiver.json()["participant_identity"], "receiver1")

        # Reject unauthorized third party
        t_intruder = self.client.post(
            f"/calls/{call_id}/token",
            json={"user_id": "eavesdropper"},
        )
        self.assertEqual(t_intruder.status_code, 403)
        self.assertIn("not an authorized participant", t_intruder.json()["detail"].lower())

    def test_api_calls_prefix_alias(self) -> None:
        """Verifies that endpoints are also accessible via /api/calls/... for mobile client."""
        start_resp = self.client.post(
            "/api/calls/start",
            json={"caller_id": "mobile_user", "recipient_id": "support_agent"},
        )
        self.assertEqual(start_resp.status_code, 200)
        call_id = start_resp.json()["call_id"]

        status_resp = self.client.get(f"/api/calls/{call_id}/status")
        self.assertEqual(status_resp.status_code, 200)
        self.assertEqual(status_resp.json()["caller_id"], "mobile_user")

    def test_livekit_ai_worker_lifecycle(self) -> None:
        """Tests the LiveKitScamDetectionWorker instantiation, synthetic frame pushing, and stop."""
        call_detail = LiveKitCallDetail(
            call_id="call_worker_test_123",
            room_id="room_worker_test_123",
            caller_id="agent_smith",
            recipient_id="neo",
            status="ACTIVE",
            created_at=1000.0,
            ai_detection_active=True,
            participants=["agent_smith", "neo"],
        )

        mock_stt = MockSTT()
        worker = LiveKitScamDetectionWorker(call=call_detail, stt_provider=mock_stt)
        worker.start()
        self.assertTrue(worker.is_running)

        # Push synthetic 16kHz PCM audio frame (e.g. 320 bytes = 160 samples = 10ms)
        dummy_pcm = b"\x00\x00" * 160
        success_caller = worker.push_synthetic_audio("agent_smith", dummy_pcm)
        self.assertTrue(success_caller)

        success_recipient = worker.push_synthetic_audio("neo", dummy_pcm)
        self.assertTrue(success_recipient)

        # Worker Manager verification
        worker_mgr = get_worker_manager()
        w_reg = worker_mgr.start_worker_for_call(call_detail)
        self.assertIsNotNone(w_reg)
        worker_mgr.stop_worker_for_call(call_detail.call_id)
        self.assertIsNone(worker_mgr.get_worker(call_detail.call_id))

        worker.stop()


if __name__ == "__main__":
    unittest.main()
