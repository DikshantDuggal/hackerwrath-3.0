"""
LiveKit Server-Side AI Audio Ingestion & Scam Detection Worker.
Connects to active LiveKit calling rooms via livekit.rtc, subscribes to each participant's
microphone track independently, and streams 16kHz PCM audio frames into the
multi-channel LiveAudioSession for real-time STT and scam risk scoring.
"""
from __future__ import annotations

import asyncio
import threading
import time
from typing import Any, Dict, Optional, Set

import livekit.rtc as rtc

from app.api.routes_analysis import get_conversation_manager
from app.api.routes_transcription import get_stt_provider
from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.schemas.livekit_calls import LiveKitCallDetail
from app.services.conversation_manager import ConversationManager
from app.services.live_audio_processor import LiveAudioSession, get_broadcaster
from app.services.telegram_service import TelegramAlertService, get_telegram_service
from app.services.transcription_service import BaseSpeechToTextProvider

logger = get_logger("scam_detector.livekit_worker")


class LiveKitScamDetectionWorker:
    """
    Subscribes to participant audio tracks in a LiveKit room and feeds them
    to the speech recognition and multi-layer scam detection pipeline.
    """

    def __init__(
        self,
        call: LiveKitCallDetail,
        settings: Optional[Settings] = None,
        stt_provider: Optional[BaseSpeechToTextProvider] = None,
        conversation_manager: Optional[ConversationManager] = None,
        telegram_service: Optional[TelegramAlertService] = None,
    ) -> None:
        self.call = call
        self.call_id = call.call_id
        self.room_id = call.room_id
        self.settings = settings or get_settings()
        self.stt_provider = stt_provider or get_stt_provider()
        self.conversation_manager = conversation_manager or get_conversation_manager()
        self.telegram_service = telegram_service or get_telegram_service()
        self.broadcaster = get_broadcaster()

        self._is_running = False
        self._room: Optional[rtc.Room] = None
        self._stream_tasks: Dict[str, asyncio.Task] = {}
        self._main_task: Optional[asyncio.Task] = None
        self._sample_offsets: Dict[str, int] = {
            call.caller_id: 0,
            call.recipient_id: 0,
        }

        # Initialize multi-channel LiveAudioSession
        self.audio_session = LiveAudioSession(
            call_id=self.call_id,
            stt_provider=self.stt_provider,
            conversation_manager=self.conversation_manager,
            telegram_service=self.telegram_service,
            broadcaster=self.broadcaster,
            language_code=call.language_code,
            source="livekit_calling",
            telegram_meta={
                "room_id": self.room_id,
                "caller_id": call.caller_id,
                "recipient_id": call.recipient_id,
            },
        )

    @property
    def is_running(self) -> bool:
        return self._is_running

    def start(self) -> None:
        """Launches the background worker task."""
        if self._is_running:
            return
        self._is_running = True
        try:
            loop = asyncio.get_running_loop()
            self.audio_session.start()
            self._main_task = loop.create_task(self._run_worker())
        except RuntimeError:
            logger.warning(
                "No running asyncio event loop; worker initialized in passive mode for call '%s'",
                self.call_id,
            )

    async def _run_worker(self) -> None:
        """
        Connects to the LiveKit room if live cloud credentials are available,
        or operates in passive/synthetic mode for offline local development and testing.
        """
        if not self.settings.has_livekit_credentials:
            logger.info(
                "LiveKit Cloud credentials not configured. Worker running in simulated mode for room '%s'",
                self.room_id,
            )
            # Notify subscribers that scam detection is active on this call
            await self.broadcaster.broadcast(
                {
                    "type": "ai_worker_status",
                    "call_id": self.call_id,
                    "room_id": self.room_id,
                    "status": "active_simulated",
                    "notice": "AI Scam Analysis is active on this call.",
                }
            )
            return

        try:
            from app.services.livekit_service import get_livekit_manager

            token_resp = get_livekit_manager().generate_token(
                call_id=self.call_id,
                user_id="scam-guard-ai",
                ttl_seconds=3600,
            )

            room = rtc.Room()
            self._room = room

            @room.on("track_subscribed")
            def on_track_subscribed(
                track: rtc.Track,
                publication: rtc.RemoteTrackPublication,
                participant: rtc.RemoteParticipant,
            ) -> None:
                if track.kind == rtc.TrackKind.KIND_AUDIO:
                    identity = participant.identity
                    task_key = f"{identity}_{track.sid}"
                    logger.info(
                        "Subscribed to audio track '%s' from participant '%s' in call '%s'",
                        track.sid,
                        identity,
                        self.call_id,
                    )
                    task = asyncio.create_task(
                        self._consume_track_stream(identity, track)
                    )
                    self._stream_tasks[task_key] = task

            @room.on("track_unsubscribed")
            def on_track_unsubscribed(
                track: rtc.Track,
                publication: rtc.RemoteTrackPublication,
                participant: rtc.RemoteParticipant,
            ) -> None:
                identity = participant.identity
                task_key = f"{identity}_{track.sid}"
                task = self._stream_tasks.pop(task_key, None)
                if task and not task.done():
                    task.cancel()
                logger.info(
                    "Unsubscribed from track '%s' for participant '%s'",
                    track.sid,
                    identity,
                )

            logger.info(
                "AI Worker connecting to LiveKit room '%s' at '%s'",
                self.room_id,
                self.settings.livekit_url,
            )
            await room.connect(self.settings.livekit_url, token_resp.token)
            logger.info("AI Worker connected to LiveKit room '%s'", self.room_id)

            await self.broadcaster.broadcast(
                {
                    "type": "ai_worker_status",
                    "call_id": self.call_id,
                    "room_id": self.room_id,
                    "status": "connected",
                    "notice": "AI Scam Analysis is active on this call.",
                }
            )

            # Wait while running
            while self._is_running and room.isconnected:
                await asyncio.sleep(1.0)

        except asyncio.CancelledError:
            pass
        except Exception as exc:
            logger.error(
                "Error in LiveKit AI Worker for call '%s': %s",
                self.call_id,
                exc,
                exc_info=True,
            )
        finally:
            await self._cleanup()

    async def _consume_track_stream(self, identity: str, track: rtc.Track) -> None:
        """
        Consumes 16kHz mono PCM frames from an active LiveKit audio track.
        Separates caller (channel 0) and recipient/remote (channel 1) audio.
        """
        # Determine channel: caller is channel 0, recipient / other is channel 1
        channel_id = 0 if identity.lower() == self.call.caller_id.lower() else 1

        try:
            # Resample to 16kHz mono for speech recognition
            audio_stream = rtc.AudioStream.from_track(
                track, sample_rate=16000, num_channels=1
            )
            async for event in audio_stream:
                if not self._is_running:
                    break
                frame = event.frame
                pcm_data = bytes(frame.data)
                if not pcm_data:
                    continue

                num_samples = len(pcm_data) // 2
                current_offset = self._sample_offsets.get(identity, 0)
                self._sample_offsets[identity] = current_offset + num_samples

                self.audio_session.push_audio_frame(
                    channel_id=channel_id,
                    offset=current_offset,
                    pcm_bytes=pcm_data,
                )
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            logger.warning(
                "Audio stream consumption ended for participant '%s' in call '%s': %s",
                identity,
                self.call_id,
                exc,
            )

    def push_synthetic_audio(
        self, participant_identity: str, pcm_bytes: bytes, sample_offset: Optional[int] = None
    ) -> bool:
        """
        Allows pushing audio frames directly into the worker for unit testing
        and local simulation without active network connections.
        """
        if not self._is_running or not pcm_bytes:
            return False

        channel_id = 0 if participant_identity.lower() == self.call.caller_id.lower() else 1
        num_samples = len(pcm_bytes) // 2
        offset = (
            sample_offset
            if sample_offset is not None
            else self._sample_offsets.get(participant_identity, 0)
        )
        self._sample_offsets[participant_identity] = offset + num_samples

        return self.audio_session.push_audio_frame(
            channel_id=channel_id,
            offset=offset,
            pcm_bytes=pcm_bytes,
        )

    async def _cleanup(self) -> None:
        """Closes all streams, disconnects from room, and flushes audio buffers."""
        for task in self._stream_tasks.values():
            if not task.done():
                task.cancel()
        self._stream_tasks.clear()

        if self._room:
            try:
                if self._room.isconnected:
                    await self._room.disconnect()
            except Exception as exc:
                logger.warning("Error disconnecting from LiveKit room: %s", exc)
            self._room = None

        await self.audio_session.stop_and_flush()
        logger.info("AI Worker stopped and flushed for call '%s'", self.call_id)

    def stop(self) -> None:
        """Stops the worker immediately."""
        self._is_running = False
        if self._main_task and not self._main_task.done():
            self._main_task.cancel()

        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._cleanup())
        except RuntimeError:
            pass


class LiveKitWorkerManager:
    """Manages active server-side AI workers for all concurrent LiveKit calls."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._workers: Dict[str, LiveKitScamDetectionWorker] = {}

    def start_worker_for_call(self, call: LiveKitCallDetail) -> LiveKitScamDetectionWorker:
        """Creates and starts an AI detection worker for an accepted call."""
        with self._lock:
            existing = self._workers.get(call.call_id)
            if existing and existing.is_running:
                return existing

            worker = LiveKitScamDetectionWorker(call=call)
            self._workers[call.call_id] = worker
            worker.start()
            logger.info("Registered and started AI worker for call '%s'", call.call_id)
            return worker

    def stop_worker_for_call(self, call_id: str) -> None:
        """Stops and unregisters the worker for a completed call."""
        with self._lock:
            worker = self._workers.pop(call_id.strip(), None)
            if worker:
                worker.stop()
                logger.info("Unregistered and stopped AI worker for call '%s'", call_id)

    def get_worker(self, call_id: str) -> Optional[LiveKitScamDetectionWorker]:
        with self._lock:
            return self._workers.get(call_id.strip())


_worker_manager: Optional[LiveKitWorkerManager] = None
_worker_manager_lock = threading.Lock()


def get_worker_manager() -> LiveKitWorkerManager:
    """Singleton accessor for the LiveKit worker manager."""
    global _worker_manager
    if _worker_manager is None:
        with _worker_manager_lock:
            if _worker_manager is None:
                _worker_manager = LiveKitWorkerManager()
    return _worker_manager
