"""The call engine: plug-ins in, warning events out, under the hard rules."""

from __future__ import annotations

import asyncio
from typing import Any

from app.events import EventHub
from app.store import CallSession, UserSettings
from detection.adapter import PluginOptions, RateLimiter, make_detector, make_phrase_engine
from detection.schemas import Assessment
from engine.session import CallEngine


class RecordingHub(EventHub):
    def __init__(self) -> None:
        super().__init__()
        self.events: list[dict[str, Any]] = []

    async def _send(self, user_id: str, event: dict[str, Any]) -> None:
        self.events.append(event)

    def types(self) -> list[str]:
        return [e["type"] for e in self.events]


class CountingDetector:
    """Answers with a fixed assessment after an optional wait, counting calls and overlap."""

    def __init__(self, answer: Assessment | None = None, wait: float = 0.0, error: bool = False) -> None:
        self.answer, self.wait, self.error = answer, wait, error
        self.calls = 0
        self.in_flight = 0
        self.most_in_flight = 0

    async def assess(self, context):
        self.calls += 1
        self.in_flight += 1
        self.most_in_flight = max(self.most_in_flight, self.in_flight)
        try:
            await asyncio.sleep(self.wait)
            if self.error:
                raise RuntimeError("down")
            return self.answer
        finally:
            self.in_flight -= 1


def engine(detector=None, *, phrases="example", scam_check=True, limiter=None) -> tuple[CallEngine, RecordingHub]:
    call = CallSession(call_id="call_1", user_id="u", from_number="+91 1", demo=True, state="ACTIVE", monitor="monitoring")
    hub = RecordingHub()
    e = CallEngine(
        call,
        UserSettings(scam_check=scam_check),
        hub,
        make_phrase_engine(phrases, PluginOptions()),
        detector if detector is not None else make_detector("none", PluginOptions()),
        timeout=0.5,
        limiter=limiter,
    )
    return e, hub


def test_the_phrase_engine_alone_never_produces_high_risk():
    async def go():
        e, hub = engine()
        await e.hear("Please read me the OTP you just received.", final=True)
        await e.wait_idle()
        return hub

    hub = asyncio.run(go())
    assert hub.types() == ["first_warning"]
    assert hub.events[0]["level"] == "possible"


def test_a_phrase_hit_warns_before_the_detector_answers():
    async def go():
        e, hub = engine(CountingDetector(wait=0.2))
        await e.hear("OTP batao", final=False)
        seen = hub.types()
        e.close()
        return seen

    assert asyncio.run(go()) == ["first_warning"]


def test_the_example_plug_ins_confirm_an_otp_ask_as_high_risk_with_its_signals():
    async def go():
        e, hub = engine(make_detector("example", PluginOptions()))
        await e.hear("Hello, I'm calling from your bank's customer care.", final=True)
        await e.hear("Your account will be blocked today because your KYC expired.", final=True)
        await e.hear("Please read me the OTP you just received.", final=True)
        await e.wait_idle()
        return hub

    hub = asyncio.run(go())
    confirmed = [ev for ev in hub.events if ev["type"] == "confirmed"][-1]
    assert (confirmed["request_type"], confirmed["level"]) == ("otp_share", "high")
    assert confirmed["signals"] == ["otp_or_pin_request", "authority_impersonation", "account_suspension_threat"]


def test_nothing_is_analysed_when_scam_check_is_off():
    async def go():
        detector = CountingDetector(Assessment(request_type="otp_share", confidence="high"))
        e, hub = engine(detector, scam_check=False)
        await e.hear("Please read me the OTP.", final=True)
        await e.wait_idle()
        return detector, hub

    detector, hub = asyncio.run(go())
    assert detector.calls == 0
    assert hub.events == []


def test_only_one_assessment_is_in_flight_per_call():
    async def go():
        detector = CountingDetector(wait=0.05)
        e, _ = engine(detector, phrases="none")
        await e.hear("turn 0", final=True)
        await asyncio.sleep(0.01)  # the first assessment is now in flight
        for n in range(1, 5):
            await e.hear(f"turn {n}", final=True)
        await e.wait_idle()
        return detector

    detector = asyncio.run(go())
    assert detector.most_in_flight == 1
    assert detector.calls == 2  # the first, then one more covering everything heard meanwhile


def test_a_late_answer_after_the_call_ends_changes_nothing():
    async def go():
        answer = Assessment(request_type="otp_share", confidence="high", evidence_turn_ids=("turn_1",))
        e, hub = engine(CountingDetector(answer, wait=0.05), phrases="none")
        await e.hear("read me the code", final=True)
        e.call.state = "ENDED"
        await asyncio.sleep(0.1)
        return hub

    assert asyncio.run(go()).events == []


def test_a_failing_detector_reports_degraded_and_keeps_the_warning():
    async def go():
        e, hub = engine(CountingDetector(error=True))
        await e.hear("OTP batao", final=True)
        await e.wait_idle()
        return hub

    hub = asyncio.run(go())
    assert hub.types() == ["first_warning", "status"]
    assert hub.events[1]["state"] == "degraded"


def test_rate_limited_assessments_report_degraded():
    async def go():
        detector = CountingDetector()
        e, hub = engine(detector, phrases="none", limiter=RateLimiter(0))
        await e.hear("hello", final=True)
        await e.wait_idle()
        return detector, hub

    detector, hub = asyncio.run(go())
    assert detector.calls == 0
    assert hub.events[-1]["state"] == "degraded"
