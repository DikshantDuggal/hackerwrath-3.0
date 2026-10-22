"""
Live Audio Processing, Bounded Buffering, Non-Blocking Streaming,
and Progressive Word-Chunked Captioning Engine for Suraksha Scam Shield.

Features:
- Bounded async queues with backpressure protection (drops oldest on overflow).
- Non-blocking audio capture loop (audio thread never waits for STT or AI).
- Progressive caption generation targeting ~7-8 words per chunk.
- Silence / pause detection with automatic buffer flushing.
- Concurrent multi-layer scam risk evaluation & Telegram alert dispatch.
- Supports both OnFloor Telegram Bridge protocol (16kHz PCM16LE) and Web Browser Live Audio.
"""
from __future__ import annotations

import asyncio
import io
import json
import time
import uuid
import wave
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set

from app.core.logging import get_logger
from app.schemas.calls import CallSegmentRequest
from app.services.conversation_manager import ConversationManager
from app.services.telegram_service import TelegramAlertService
from app.services.transcription_service import BaseSpeechToTextProvider

logger = get_logger("scam_detector.live_audio_processor")

TARGET_WORDS_PER_CHUNK = 8
MIN_BUFFER_BYTES = 24_000   # ~0.75 seconds of 16kHz 16-bit mono
IDEAL_BUFFER_BYTES = 48_000 # ~1.5 seconds of 16kHz 16-bit mono
MAX_BUFFER_BYTES = 96_000   # ~3.0 seconds max accumulation before forcing slice
PAUSE_FLUSH_SECONDS = 1.2   # Flush if speaker pauses for > 1.2s


def pcm16_to_wav_bytes(pcm_bytes: bytes, sample_rate: int = 16000) -> bytes:
    """Wraps raw 16-bit mono PCM bytes in standard RIFF WAV container in memory."""
    wav_io = io.BytesIO()
    with wave.open(wav_io, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_bytes)
    return wav_io.getvalue()


def split_text_into_word_chunks(text: str, target_size: int = TARGET_WORDS_PER_CHUNK) -> List[str]:
    """
    Splits continuous transcript text into progressive presentation chunks
    targeting approximately 7-8 words each.
    """
    words = [w.strip() for w in text.split() if w.strip()]
    if not words:
        return []
    if len(words) <= target_size:
        return [" ".join(words)]

    chunks = []
    for i in range(0, len(words), target_size):
        chunk = " ".join(words[i : i + target_size])
        if chunk:
            chunks.append(chunk)
    return chunks


class DashboardBroadcaster:
    """Manages active Web dashboard subscribers and broadcasts live captions & alerts."""

    def __init__(self) -> None:
        self._subscribers: Set[Any] = set()

    def register(self, ws: Any) -> None:
        self._subscribers.add(ws)
        logger.debug("Dashboard subscriber registered (total: %d)", len(self._subscribers))

    def unregister(self, ws: Any) -> None:
        self._subscribers.discard(ws)
        logger.debug("Dashboard subscriber removed (total: %d)", len(self._subscribers))

    async def broadcast(self, payload: Dict[str, Any]) -> None:
        dead = []
        for ws in list(self._subscribers):
            try:
                await ws.send_json(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self._subscribers.discard(ws)


_broadcaster = DashboardBroadcaster()


def get_broadcaster() -> DashboardBroadcaster:
    return _broadcaster


@dataclass
class LiveAudioSession:
    """
    Stateful real-time audio capture session for an active call.
    Buffers incoming PCM chunks, runs background worker, generates progressive captions,
    and coordinates scam risk analysis without blocking the audio capture stream.
    """

    call_id: str
    stt_provider: BaseSpeechToTextProvider
    conversation_manager: ConversationManager
    telegram_service: TelegramAlertService
    broadcaster: DashboardBroadcaster
    language_code: str = "auto"
    queue: asyncio.Queue = field(default_factory=lambda: asyncio.Queue(maxsize=100))
    pcm_buffer: bytearray = field(default_factory=bytearray)
    is_active: bool = True
    total_packets_received: int = 0
    total_packets_dropped: int = 0
    total_words_emitted: int = 0
    slice_counter: int = 0
    last_packet_time: float = field(default_factory=time.time)
    worker_task: Optional[asyncio.Task] = None
    on_event_callback: Optional[Callable[[Dict[str, Any]], Any]] = None

    def start(self) -> None:
        """Launches the background audio consumer worker task."""
        self.is_active = True
        self.last_packet_time = time.time()
        self.worker_task = asyncio.create_task(self._audio_consumer_loop())

    def push_pcm_frame(self, pcm_bytes: bytes) -> bool:
        """
        Enqueues raw PCM16 audio non-blockingly.
        If the worker queue is full (backpressure), drops oldest chunk to prevent latency build-up.
        """
        if not self.is_active or not pcm_bytes:
            return False

        self.total_packets_received += 1
        self.last_packet_time = time.time()

        if self.queue.full():
            try:
                self.queue.get_nowait()
                self.total_packets_dropped += 1
                if self.total_packets_dropped == 1 or self.total_packets_dropped % 25 == 0:
                    logger.warning(
                        "Audio buffer queue full for call '%s'; dropped %d oldest packets (backpressure)",
                        self.call_id,
                        self.total_packets_dropped,
                    )
            except Exception:
                pass

        try:
            self.queue.put_nowait(pcm_bytes)
            return True
        except asyncio.QueueFull:
            return False

    async def _audio_consumer_loop(self) -> None:
        """
        Continuously pulls PCM packets, checks buffer size & pause thresholds,
        and transcribes slices without blocking audio ingestion.
        """
        logger.info("Started continuous audio consumer worker for call '%s'", self.call_id)
        while self.is_active:
            try:
                # Wait for next audio packet with a short timeout to handle pauses
                try:
                    packet = await asyncio.wait_for(self.queue.get(), timeout=0.3)
                    self.pcm_buffer.extend(packet)
                    self.queue.task_done()
                except asyncio.TimeoutError:
                    packet = None

                now = time.time()
                buf_len = len(self.pcm_buffer)

                # Determine if we should process a slice:
                # 1. Buffer has reached ideal chunk size (~1.5s - 2.5s)
                # 2. Speaker paused (> PAUSE_FLUSH_SECONDS of inactivity) and buffer has minimal speech
                should_process = (
                    buf_len >= IDEAL_BUFFER_BYTES
                    or (buf_len >= MIN_BUFFER_BYTES and (now - self.last_packet_time) >= PAUSE_FLUSH_SECONDS)
                    or buf_len >= MAX_BUFFER_BYTES
                )

                if should_process and buf_len > 0:
                    chunk = bytes(self.pcm_buffer)
                    self.pcm_buffer.clear()
                    await self._transcribe_and_evaluate_slice(chunk, is_final=False)

            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("Error in audio consumer worker for call '%s': %s", self.call_id, exc)
                await asyncio.sleep(0.05)

    async def _transcribe_and_evaluate_slice(self, pcm_chunk: bytes, is_final: bool = False) -> None:
        """Converts chunk to WAV, transcribes via Sarvam, emits 7-8 word captions, and evaluates scam risk."""
        if len(pcm_chunk) < 3200:  # Skip trivial clicks under 100ms
            return

        self.slice_counter += 1
        wav_bytes = pcm16_to_wav_bytes(pcm_chunk, sample_rate=16000)
        slice_name = f"{self.call_id}_slice_{self.slice_counter:04d}.wav"

        try:
            # Run blocking STT call in a thread pool to NEVER block the async loop
            stt_res = await asyncio.to_thread(
                self.stt_provider.transcribe_bytes,
                wav_bytes,
                slice_name,
                self.language_code,
            )

            text = (stt_res.transcript or "").strip()
            if not text:
                return

            # Progressive caption chunking targeting ~7-8 words
            word_chunks = split_text_into_word_chunks(text, target_size=TARGET_WORDS_PER_CHUNK)

            # Evaluate through conversation manager (Rules + Contextual + RiskScorer)
            seg_req = CallSegmentRequest(
                text=text,
                speaker="caller",
                language_code=stt_res.language_code or self.language_code,
                start_seconds=0.0,
                end_seconds=stt_res.duration_seconds,
                transcript_confidence=stt_res.confidence,
            )

            seg_res = self.conversation_manager.process_segment(self.call_id, seg_req)
            assessment = seg_res.assessment

            # Emit progressive caption chunks
            for idx, w_chunk in enumerate(word_chunks):
                self.total_words_emitted += len(w_chunk.split())
                is_last_in_slice = idx == len(word_chunks) - 1

                event_payload = {
                    "type": "caption_chunk",
                    "callId": self.call_id,
                    "text": w_chunk,
                    "fullTranscript": text,
                    "wordCount": len(w_chunk.split()),
                    "isPartial": not is_last_in_slice and not is_final,
                    "isFinal": is_final and is_last_in_slice,
                    "speaker": "caller",
                    "language": stt_res.language_code,
                    "riskScore": assessment.risk_score,
                    "riskLevel": assessment.risk_level,
                    "flaggedKeywords": [
                        i.keyword_or_pattern for i in assessment.rule_analysis.triggered_indicators
                    ],
                    "recommendedAction": assessment.recommended_action,
                    "timestamp": round(time.time(), 3),
                }

                # Send to direct callback if provided
                if self.on_event_callback:
                    try:
                        res = self.on_event_callback(event_payload)
                        if asyncio.iscoroutine(res):
                            await res
                    except Exception as cb_err:
                        logger.warning("Error in on_event_callback: %s", cb_err)

                # Broadcast to connected dashboard sessions
                await self.broadcaster.broadcast(event_payload)

            # Check if Telegram alert should be triggered
            if (
                assessment.risk_level in ("HIGH", "CRITICAL")
                and self.telegram_service.is_enabled
            ):
                alert_res = self.telegram_service.send_risk_alert(assessment, self.call_id)
                if alert_res.delivered:
                    alert_event = {
                        "type": "telegram_alert_sent",
                        "callId": self.call_id,
                        "messageId": alert_res.message_id,
                        "riskLevel": assessment.risk_level,
                        "riskScore": assessment.risk_score,
                    }
                    await self.broadcaster.broadcast(alert_event)

        except Exception as exc:
            logger.warning("Transcription/evaluation error on slice %d: %s", self.slice_counter, exc)

    async def stop_and_flush(self) -> Dict[str, Any]:
        """Stops the audio session, flushes remaining buffer, and releases resources."""
        self.is_active = False

        if self.worker_task and not self.worker_task.done():
            self.worker_task.cancel()
            try:
                await self.worker_task
            except asyncio.CancelledError:
                pass

        # Flush any remaining un-processed audio
        if len(self.pcm_buffer) >= 3200:
            remaining = bytes(self.pcm_buffer)
            self.pcm_buffer.clear()
            await self._transcribe_and_evaluate_slice(remaining, is_final=True)

        close_event = {
            "type": "call_ended",
            "callId": self.call_id,
            "totalWords": self.total_words_emitted,
            "totalPackets": self.total_packets_received,
            "droppedPackets": self.total_packets_dropped,
        }
        await self.broadcaster.broadcast(close_event)
        logger.info(
            "Call '%s' audio session ended. Processed %d words across %d packets.",
            self.call_id,
            self.total_words_emitted,
            self.total_packets_received,
        )
        return close_event
