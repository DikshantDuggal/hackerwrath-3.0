"""
LiveKit Internet Calling & Room Management Service.
Handles call session lifecycles (start, accept, reject, end), participant authentication,
LiveKit Cloud room token minting, and AI scam detection orchestration.
"""
from __future__ import annotations

import asyncio
import datetime
import threading
import time
import uuid
from typing import Any, Dict, List, Optional

import livekit.api as lk_api

from app.core.compat import HTTPException
from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.schemas.livekit_calls import (
    CallActionResponse,
    CallStartRequest,
    CallStartResponse,
    CallTokenResponse,
    LiveKitCallDetail,
    LiveKitCallStatus,
)
from app.services.live_audio_processor import get_broadcaster

logger = get_logger("scam_detector.livekit_service")


class LiveKitCallManager:
    """
    Thread-safe state manager for LiveKit Internet Calling.
    Coordinates room creation, token generation, call state transitions,
    and triggering server-side AI scam detection workers.
    """

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self.settings = settings or get_settings()
        self._lock = threading.RLock()
        self._calls: Dict[str, LiveKitCallDetail] = {}
        self._room_to_call: Dict[str, str] = {}
        self._active_workers: Dict[str, Any] = {}

    def get_call(self, call_id: str) -> Optional[LiveKitCallDetail]:
        """Returns the call detail by call_id or None."""
        with self._lock:
            return self._calls.get(call_id.strip())

    def get_call_by_room(self, room_id: str) -> Optional[LiveKitCallDetail]:
        """Returns the call detail by room_id or None."""
        with self._lock:
            call_id = self._room_to_call.get(room_id.strip())
            if not call_id:
                return None
            return self._calls.get(call_id)

    def list_calls(self) -> List[LiveKitCallDetail]:
        """Returns all recorded calls."""
        with self._lock:
            return list(self._calls.values())

    def list_active_calls(self) -> List[LiveKitCallDetail]:
        """Returns all currently ongoing or ringing calls."""
        with self._lock:
            return [
                call
                for call in self._calls.values()
                if call.status in ("CREATED", "RINGING", "ACCEPTED", "ACTIVE")
            ]

    def list_calls_for_user(self, user_id: str) -> List[LiveKitCallDetail]:
        """Returns all calls where the user is either caller or recipient."""
        uid = user_id.strip().lower()
        with self._lock:
            return [
                c
                for c in self._calls.values()
                if c.caller_id.lower() == uid or c.recipient_id.lower() == uid
            ]

    def start_call(
        self,
        recipient_id: str,
        caller_id: Optional[str] = None,
        language_code: str = "auto",
        enable_scam_detection: bool = True,
    ) -> LiveKitCallDetail:
        """
        Initiates a new LiveKit call session and registers a unique room.
        Status begins as RINGING so the recipient can accept or reject.
        """
        caller = (caller_id or "caller_anonymous").strip()
        recipient = recipient_id.strip()

        if not recipient:
            raise HTTPException(status_code=400, detail="recipient_id must not be empty.")
        if caller.lower() == recipient.lower():
            raise HTTPException(
                status_code=400, detail="Cannot initiate a call to oneself."
            )

        call_id = f"call_{uuid.uuid4().hex[:12]}"
        room_id = f"room_{uuid.uuid4().hex[:12]}"
        now = time.time()

        call_detail = LiveKitCallDetail(
            call_id=call_id,
            room_id=room_id,
            caller_id=caller,
            recipient_id=recipient,
            status="RINGING",
            created_at=now,
            language_code=language_code or "auto",
            ai_detection_active=enable_scam_detection,
            participants=[caller],
        )

        with self._lock:
            self._calls[call_id] = call_detail
            self._room_to_call[room_id] = call_id

        logger.info(
            "LiveKit call created: call_id='%s' room_id='%s' caller='%s' recipient='%s'",
            call_id,
            room_id,
            caller,
            recipient,
        )

        # Broadcast call invitation to dashboard and active subscribers
        self._notify_subscribers(
            {
                "type": "call_invitation",
                "call_id": call_id,
                "room_id": room_id,
                "caller_id": caller,
                "recipient_id": recipient,
                "ai_detection_active": enable_scam_detection,
                "created_at": now,
            }
        )

        return call_detail

    def accept_call(self, call_id: str, user_id: Optional[str] = None) -> LiveKitCallDetail:
        """
        Transitions call state from RINGING to ACTIVE.
        Triggers the AI scam detection worker if enabled.
        """
        with self._lock:
            call = self._calls.get(call_id.strip())
            if not call:
                raise HTTPException(
                    status_code=404, detail=f"Call '{call_id}' not found."
                )

            if call.status in ("ENDED", "REJECTED", "FAILED"):
                raise HTTPException(
                    status_code=400,
                    detail=f"Cannot accept call '{call_id}' in terminal state '{call.status}'.",
                )

            if call.status == "ACTIVE":
                return call

            # Verify authorization if user_id is provided
            if user_id:
                uid = user_id.strip().lower()
                if uid != call.recipient_id.lower() and uid != call.caller_id.lower():
                    raise HTTPException(
                        status_code=403,
                        detail=f"User '{user_id}' is not authorized to accept call '{call_id}'.",
                    )
                if user_id.strip() not in call.participants:
                    call.participants.append(user_id.strip())
            else:
                if call.recipient_id not in call.participants:
                    call.participants.append(call.recipient_id)

            now = time.time()
            call.status = "ACTIVE"
            call.accepted_at = now
            call.started_at = now

        logger.info("LiveKit call accepted: call_id='%s'", call_id)

        self._notify_subscribers(
            {
                "type": "call_accepted",
                "call_id": call_id,
                "room_id": call.room_id,
                "caller_id": call.caller_id,
                "recipient_id": call.recipient_id,
                "accepted_at": now,
            }
        )

        # Trigger AI audio inspection worker if scam detection is active
        if call.ai_detection_active:
            self._start_ai_worker(call)

        return call

    def reject_call(
        self, call_id: str, user_id: Optional[str] = None, reason: Optional[str] = None
    ) -> LiveKitCallDetail:
        """
        Transitions call state to REJECTED.
        """
        with self._lock:
            call = self._calls.get(call_id.strip())
            if not call:
                raise HTTPException(
                    status_code=404, detail=f"Call '{call_id}' not found."
                )

            if call.status in ("ENDED", "REJECTED", "FAILED"):
                return call

            if user_id:
                uid = user_id.strip().lower()
                if uid != call.recipient_id.lower() and uid != call.caller_id.lower():
                    raise HTTPException(
                        status_code=403,
                        detail=f"User '{user_id}' is not authorized to reject call '{call_id}'.",
                    )

            now = time.time()
            call.status = "REJECTED"
            call.ended_at = now

        logger.info("LiveKit call rejected: call_id='%s' reason='%s'", call_id, reason)

        self._stop_ai_worker(call_id)

        self._notify_subscribers(
            {
                "type": "call_rejected",
                "call_id": call_id,
                "reason": reason or "User declined the call",
                "ended_at": now,
            }
        )

        return call

    def end_call(
        self, call_id: str, user_id: Optional[str] = None, reason: Optional[str] = None
    ) -> LiveKitCallDetail:
        """
        Ends an active or ongoing call, disconnecting participants and tearing down AI workers.
        """
        with self._lock:
            call = self._calls.get(call_id.strip())
            if not call:
                raise HTTPException(
                    status_code=404, detail=f"Call '{call_id}' not found."
                )

            if call.status == "ENDED":
                return call

            if user_id:
                uid = user_id.strip().lower()
                if uid != call.recipient_id.lower() and uid != call.caller_id.lower():
                    raise HTTPException(
                        status_code=403,
                        detail=f"User '{user_id}' is not authorized to end call '{call_id}'.",
                    )

            now = time.time()
            call.status = "ENDED"
            call.ended_at = now

        logger.info("LiveKit call ended: call_id='%s' reason='%s'", call_id, reason)

        self._stop_ai_worker(call_id)

        self._notify_subscribers(
            {
                "type": "call_ended",
                "call_id": call_id,
                "room_id": call.room_id,
                "reason": reason or "Normal hangup",
                "ended_at": now,
            }
        )

        return call

    def generate_token(
        self,
        call_id: str,
        user_id: Optional[str] = None,
        ttl_seconds: Optional[int] = None,
    ) -> CallTokenResponse:
        """
        Mints a cryptographic participant token to access the LiveKit room.
        Enforces participant authorization: only the caller or recipient can join.
        """
        call = self.get_call(call_id)
        if not call:
            raise HTTPException(status_code=404, detail=f"Call '{call_id}' not found.")

        if call.status in ("ENDED", "REJECTED", "FAILED"):
            raise HTTPException(
                status_code=400,
                detail=f"Cannot generate room token for terminated call '{call_id}' (status: {call.status}).",
            )

        identity = (user_id or call.caller_id).strip()
        uid_lower = identity.lower()

        # Authorization validation
        allowed_users = {call.caller_id.lower(), call.recipient_id.lower(), "scam-guard-ai"}
        if uid_lower not in allowed_users:
            raise HTTPException(
                status_code=403,
                detail=f"User '{identity}' is not an authorized participant in call '{call_id}'.",
            )

        ttl = ttl_seconds or self.settings.livekit_token_ttl_seconds or 3600

        # Construct LiveKit Video Grants
        grants = lk_api.VideoGrants(
            room_join=True,
            room=call.room_id,
            can_publish=True,
            can_subscribe=True,
        )

        server_url = self.settings.livekit_url
        if self.settings.has_livekit_credentials:
            # Genuine LiveKit Cloud token
            token_builder = (
                lk_api.AccessToken(
                    self.settings.livekit_api_key,
                    self.settings.livekit_api_secret,
                )
                .with_identity(identity)
                .with_name(identity)
                .with_grants(grants)
                .with_ttl(datetime.timedelta(seconds=ttl))
            )
            raw_token = token_builder.to_jwt()
        else:
            # Fallback deterministic development / mock token
            # Uses mock signing keys while adhering to LiveKit token specifications
            mock_key = "devkey_edgerunner_guardian"
            mock_secret = "devsecret_mock_livekit_key_at_least_32_bytes_long"
            token_builder = (
                lk_api.AccessToken(mock_key, mock_secret)
                .with_identity(identity)
                .with_name(identity)
                .with_grants(grants)
                .with_ttl(datetime.timedelta(seconds=ttl))
            )
            raw_token = token_builder.to_jwt()
            if not server_url:
                server_url = "wss://mock.livekit.cloud"

        # Update participants set
        with self._lock:
            if identity not in call.participants:
                call.participants.append(identity)

        return CallTokenResponse(
            token=raw_token,
            server_url=server_url,
            room_id=call.room_id,
            participant_identity=identity,
            participant_name=identity,
            expires_in_seconds=ttl,
        )

    def _notify_subscribers(self, payload: Dict[str, Any]) -> None:
        """Dispatches an asynchronous broadcast event without blocking the call state machine."""
        broadcaster = get_broadcaster()
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(broadcaster.broadcast(payload))
        except RuntimeError:
            pass

    def _start_ai_worker(self, call: LiveKitCallDetail) -> None:
        """Launches the LiveKit server-side AI scam detection worker for the active room."""
        from app.services.livekit_worker import get_worker_manager

        worker_manager = get_worker_manager()
        worker_manager.start_worker_for_call(call)

    def _stop_ai_worker(self, call_id: str) -> None:
        """Stops the AI scam detection worker associated with the given call_id."""
        from app.services.livekit_worker import get_worker_manager

        worker_manager = get_worker_manager()
        worker_manager.stop_worker_for_call(call_id)


_livekit_manager: Optional[LiveKitCallManager] = None
_manager_lock = threading.Lock()


def get_livekit_manager() -> LiveKitCallManager:
    """Dependency provider returning the singleton LiveKitCallManager instance."""
    global _livekit_manager
    if _livekit_manager is None:
        with _manager_lock:
            if _livekit_manager is None:
                _livekit_manager = LiveKitCallManager()
    return _livekit_manager
