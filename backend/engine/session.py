"""One engine per call: caller turns in, warning events out.

Speech-to-text (Sarvam, or whatever your plug-in uses) calls `hear(text, final)` for each
partial and final transcript of the caller's leg. The engine then:

1. runs the phrase engine on every turn; a hit sends `first_warning` (Possible risk) and asks
   for an assessment straight away;
2. keeps the last few final turns and asks the detector about them, one call in flight per
   call, newer turns coalesced into the next call, behind an account-wide rate limit;
3. hands each fresh assessment to the policy and sends what it decides.

`hear` never waits for the detector. Nothing is stored: turns live in memory for the call
only and are never logged.
"""

from __future__ import annotations

import asyncio
import logging
import secrets
from collections import deque

from app.events import EventHub
from app.store import CallSession, UserSettings
from detection.adapter import Detector, PhraseEngine, RateLimiter, run_detector, run_phrase_engine
from detection.policy import Decision, OpenAlert, decide
from detection.schemas import AssessmentContext, PhraseHit, Turn

log = logging.getLogger("engine")

MAX_TURNS = 8


class CallEngine:
    def __init__(
        self,
        call: CallSession,
        settings: UserSettings,
        hub: EventHub,
        phrases: PhraseEngine,
        detector: Detector,
        *,
        timeout: float,
        limiter: RateLimiter | None = None,
    ) -> None:
        self.call = call
        self.settings = settings
        self.hub = hub
        self.phrases = phrases
        self.detector = detector
        self.timeout = timeout
        self.limiter = limiter
        self.alert: OpenAlert | None = None
        self._turns: deque[Turn] = deque(maxlen=MAX_TURNS)
        self._earlier: list[str] = []
        self._next_turn = 1
        self._task: asyncio.Task | None = None
        self._again = False

    @property
    def listening(self) -> bool:
        # Scam check off means no analysis at all, not analysis we ignore.
        return self.call.state == "ACTIVE" and self.settings.scam_check

    async def hear(self, text: str, final: bool) -> None:
        """One partial or final transcript of the caller. Returns without waiting for the detector."""
        if not self.listening or not text.strip():
            return
        turn = Turn(turn_id=f"turn_{self._next_turn}", text=text, final=final)
        if final:
            self._turns.append(turn)
            self._next_turn += 1
        hit = run_phrase_engine(self.phrases, turn)
        if hit is not None:
            await self._first_warning(hit)
        if final or hit is not None:
            self._schedule()

    def on_continue(self) -> None:
        """The user chose to keep talking: the app dropped the alert, so a new ask warns again."""
        self.alert = None

    def close(self) -> None:
        if self._task is not None:
            self._task.cancel()
        self._turns.clear()

    async def wait_idle(self) -> None:
        """For tests and scripted calls: wait for the assessment in flight, if any."""
        while self._task is not None and not self._task.done():
            await asyncio.shield(self._task)

    def _schedule(self) -> None:
        if self._task is not None and not self._task.done():
            self._again = True
            return
        self._task = asyncio.create_task(self._assess_until_current())

    async def _assess_until_current(self) -> None:
        while True:
            self._again = False
            await self._assess_once()
            if not self._again or not self.listening:
                return

    async def _assess_once(self) -> None:
        if self.limiter is not None and not self.limiter.try_acquire():
            log.warning("detector rate limited", extra={"code": "rate_limited", "call_id": self.call.call_id})
            await self._apply(Decision("degraded"))
            return
        revision = self.call.revision
        context = AssessmentContext(
            call_id=self.call.call_id,
            revision=revision,
            turns=tuple(self._turns),
            role_context=self.settings.role_context,
            earlier_requests=tuple(dict.fromkeys(self._earlier)),
        )
        assessment, failed = await run_detector(self.detector, context, self.timeout)
        if not self.listening or self.call.revision != revision:
            return  # the call ended or moved on while we waited: a late answer changes nothing
        decision = decide(
            assessment,
            failed=failed,
            open_alert=self.alert,
            role_context=self.settings.role_context,
            known_turn_ids={t.turn_id for t in self._turns},
        )
        await self._apply(decision)

    async def _first_warning(self, hit: PhraseHit) -> None:
        if self.alert is not None:
            return  # one warning at a time; the detector refines it
        self.alert = OpenAlert(_alert_id(), hit.request_type, "possible", confirmed=False)
        await self.hub.first_warning(self.call, self.alert.alert_id, hit.request_type, hit.signals)

    async def _apply(self, decision: Decision) -> None:
        if decision.action == "degraded":
            if self.call.monitor == "monitoring":
                self.call.monitor = "degraded"
                await self.hub.status(self.call, "degraded")
            return
        if decision.action == "clear":
            if self.alert is not None:
                await self.hub.cleared(self.call, self.alert.alert_id)
                self.alert = None
            return
        if decision.action != "confirm" or decision.request_type is None or decision.level is None:
            return
        same = self.alert is not None and (not self.alert.confirmed or self.alert.request_type == decision.request_type)
        alert_id = self.alert.alert_id if same and self.alert is not None else _alert_id()
        self.alert = OpenAlert(alert_id, decision.request_type, decision.level, confirmed=True)
        self._earlier.append(decision.request_type)
        await self.hub.confirmed(self.call, alert_id, decision.request_type, decision.level, decision.signals)
        if self.call.monitor == "degraded":
            self.call.monitor = "monitoring"
            await self.hub.status(self.call, "monitoring")


def _alert_id() -> str:
    return "al_" + secrets.token_hex(4)
