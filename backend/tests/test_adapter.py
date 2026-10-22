"""The sockets: a broken or misbehaving plug-in must degrade protection, never break a call."""

from __future__ import annotations

import asyncio

import pytest
from pydantic import ValidationError

from detection.adapter import (
    PluginOptions,
    RateLimiter,
    UnknownPlugin,
    available,
    detector,
    make_detector,
    make_phrase_engine,
    run_detector,
    run_phrase_engine,
)
from detection.schemas import Assessment, AssessmentContext, Turn

CONTEXT = AssessmentContext(call_id="call_1", revision=0, turns=(Turn(turn_id="turn_1", text="hello", final=True),))


class Returns:
    def __init__(self, value):
        self.value = value

    async def assess(self, context):
        return self.value


class Sleeps:
    async def assess(self, context):
        await asyncio.sleep(1)


class Raises:
    async def assess(self, context):
        raise RuntimeError("boom")

    def match(self, turn):
        raise RuntimeError("boom")


def run(coro):
    return asyncio.run(coro)


def test_a_detector_that_times_out_counts_as_failed():
    assert run(run_detector(Sleeps(), CONTEXT, timeout=0.01)) == (None, True)


def test_a_detector_that_raises_counts_as_failed():
    assert run(run_detector(Raises(), CONTEXT, timeout=1)) == (None, True)


def test_a_detector_naming_an_unknown_level_or_type_counts_as_failed():
    assert run(run_detector(Returns({"request_type": "safe", "confidence": "high"}), CONTEXT, timeout=1)) == (None, True)


def test_a_detector_adding_free_text_counts_as_failed():
    bot_style = {"request_type": "otp_share", "confidence": "high", "analysis": "High-risk scam solicitation"}
    assert run(run_detector(Returns(bot_style), CONTEXT, timeout=1)) == (None, True)


def test_a_detector_returning_a_dict_is_validated_into_an_assessment():
    raw = {"request_type": "otp_share", "confidence": "high", "evidence_turn_ids": ["turn_1"], "signals": ["otp_or_pin_request"]}
    assessment, failed = run(run_detector(Returns(raw), CONTEXT, timeout=1))
    assert not failed
    assert assessment == Assessment(request_type="otp_share", confidence="high", evidence_turn_ids=("turn_1",), signals=("otp_or_pin_request",))


def test_a_detector_with_nothing_to_add_is_not_a_failure():
    assert run(run_detector(Returns(None), CONTEXT, timeout=1)) == (None, False)


def test_a_phrase_engine_that_raises_counts_as_no_hit():
    assert run_phrase_engine(Raises(), Turn(turn_id="turn_1", text="OTP batao", final=False)) is None


def test_unknown_plug_in_names_are_refused_with_what_is_available():
    with pytest.raises(UnknownPlugin, match="example"):
        make_detector("missing", PluginOptions())


def test_two_plug_ins_cannot_share_a_name():
    available()  # the built-ins, "example" among them, are registered
    with pytest.raises(ValueError):
        detector("example")(Returns)


def test_the_built_in_plug_ins_are_plugged_in():
    make_phrase_engine("example", PluginOptions())
    make_detector("none", PluginOptions())


def test_the_http_detector_refuses_plain_http_to_another_host():
    with pytest.raises(ValueError, match="https"):
        make_detector("http", PluginOptions(detector_url="http://detector.example.com/assess"))
    make_detector("http", PluginOptions(detector_url="http://127.0.0.1:9000/assess"))


def test_the_rate_limiter_allows_the_cap_per_minute_then_refuses():
    now = [0.0]
    limiter = RateLimiter(2, clock=lambda: now[0])
    assert limiter.try_acquire() and limiter.try_acquire()
    assert not limiter.try_acquire()
    now[0] = 60.0
    assert limiter.try_acquire()


def test_assessments_cannot_carry_text_for_the_user():
    with pytest.raises(ValidationError):
        Assessment.model_validate({"request_type": "otp_share", "confidence": "high", "message": "Hang up now"})
