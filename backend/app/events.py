"""Warning and status events for the protected user's app.

Events carry keys and enums only (never free text, transcripts or "safe"); the app
renders its own reviewed strings. Every event has a per-call, increasing event_seq.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from fastapi import WebSocket

from .store import CallSession

log = logging.getLogger("events")

REQUEST_TYPES = frozenset({"qr_receive", "pin_receive", "otp_share"})
LEVELS = frozenset({"possible", "high"})
STATES = frozenset({"starting", "monitoring", "degraded", "unavailable", "off"})
REASONS = frozenset({"stt_down", "detector_down", "behind", "cap_reached"})


class EventHub:
    """Fans events out to every open app socket of one user."""

    def __init__(self) -> None:
        self._sockets: dict[str, set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def add(self, user_id: str, ws: WebSocket) -> None:
        async with self._lock:
            self._sockets.setdefault(user_id, set()).add(ws)

    async def remove(self, user_id: str, ws: WebSocket) -> None:
        async with self._lock:
            self._sockets.get(user_id, set()).discard(ws)

    async def _send(self, user_id: str, event: dict[str, Any]) -> None:
        async with self._lock:
            targets = list(self._sockets.get(user_id, ()))
        for ws in targets:
            try:
                await ws.send_json(event)
            except Exception:  # a closed socket is removed by its own handler
                log.info("send failed; socket will be dropped", extra={"type": event.get("type")})

    async def _publish(self, call: CallSession, payload: dict[str, Any]) -> dict[str, Any]:
        event = {"v": 1, "call_id": call.call_id, "event_seq": call.next_seq(), **payload}
        log.info("event", extra={"call_id": call.call_id, "type": event["type"], "seq": event["event_seq"]})
        await self._send(call.user_id, event)
        return event

    async def call_started(self, call: CallSession) -> dict[str, Any]:
        return await self._publish(
            call, {"type": "call_started", "from_number": call.from_number, "demo": call.demo}
        )

    async def status(self, call: CallSession, state: str, reason: str | None = None) -> dict[str, Any]:
        if state not in STATES:
            raise ValueError(f"unknown state {state}")
        payload: dict[str, Any] = {"type": "status", "state": state}
        if reason is not None:
            if reason not in REASONS:
                raise ValueError(f"unknown reason {reason}")
            payload["reason"] = reason
        return await self._publish(call, payload)

    async def first_warning(self, call: CallSession, alert_id: str, request_type: str) -> dict[str, Any]:
        _check_request(request_type, "possible")
        return await self._publish(
            call,
            {
                "type": "first_warning",
                "assessment_revision": call.revision,
                "alert_id": alert_id,
                "request_type": request_type,
                "level": "possible",
            },
        )

    async def confirmed(self, call: CallSession, alert_id: str, request_type: str, level: str) -> dict[str, Any]:
        _check_request(request_type, level)
        return await self._publish(
            call,
            {
                "type": "confirmed",
                "assessment_revision": call.next_revision(),
                "alert_id": alert_id,
                "request_type": request_type,
                "level": level,
            },
        )

    async def cleared(self, call: CallSession, alert_id: str) -> dict[str, Any]:
        return await self._publish(
            call, {"type": "cleared", "assessment_revision": call.next_revision(), "alert_id": alert_id}
        )

    async def call_ended(self, call: CallSession, reason: str) -> dict[str, Any]:
        if reason not in {"user_ended", "caller_ended", "declined"}:
            raise ValueError(f"unknown end reason {reason}")
        return await self._publish(call, {"type": "call_ended", "reason": reason})


def _check_request(request_type: str, level: str) -> None:
    if request_type not in REQUEST_TYPES:
        raise ValueError(f"unknown request type {request_type}")
    if level not in LEVELS:
        raise ValueError(f"unknown level {level}")
