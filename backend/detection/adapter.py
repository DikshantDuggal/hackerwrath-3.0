"""The plug-in sockets: where phrase engines and detectors plug in.

Two sockets, each with a registry:

- **Phrase engine** (`@phrase_engine("name")`): fast, synchronous, runs on every partial and
  final caller turn. A hit starts a Possible risk warning and an immediate assessment.
- **Detector** (`@detector("name")`): async, runs on finished turns, one call in flight per
  call. Its `Assessment` goes to the policy, which alone decides the level.

Register a class (or any callable) that takes `PluginOptions`. Pick it with `PHRASE_ENGINE` /
`DETECTOR_PROVIDER`; load modules outside this package with `DETECTION_PLUGINS`. The engine
calls plug-ins only through `run_phrase_engine` and `run_detector`, which time out, catch
errors and validate output, so a broken plug-in degrades protection instead of breaking calls.
See docs/plugins.md.
"""

from __future__ import annotations

import asyncio
import importlib
import logging
import time
from collections import deque
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any, Protocol, TypeVar

from pydantic import ValidationError

from .schemas import Assessment, AssessmentContext, PhraseHit, Turn

log = logging.getLogger("detection")


@dataclass(frozen=True)
class PluginOptions:
    """Settings a plug-in may need, read from the environment by the app."""

    detector_url: str = ""
    detector_token: str = ""


class PhraseEngine(Protocol):
    def match(self, turn: Turn) -> PhraseHit | None: ...


class Detector(Protocol):
    async def assess(self, context: AssessmentContext) -> Assessment | dict[str, Any] | None: ...


class UnknownPlugin(LookupError):
    """No plug-in is registered under that name."""


_phrase_engines: dict[str, Callable[[PluginOptions], PhraseEngine]] = {}
_detectors: dict[str, Callable[[PluginOptions], Detector]] = {}

F = TypeVar("F", bound=Callable[..., Any])


def phrase_engine(name: str) -> Callable[[F], F]:
    """Register a phrase engine under `name`."""
    return _register(_phrase_engines, name)


def detector(name: str) -> Callable[[F], F]:
    """Register a detector under `name`."""
    return _register(_detectors, name)


def _register(table: dict[str, Any], name: str) -> Callable[[F], F]:
    def wrap(factory: F) -> F:
        if name in table and table[name] is not factory:
            raise ValueError(f"a plug-in named {name!r} is already registered")
        table[name] = factory
        return factory

    return wrap


def load_plugins(modules: Iterable[str] = ()) -> None:
    """Import the built-in plug-ins plus any extra modules, so their decorators run."""
    importlib.import_module("detection.providers")
    for module in modules:
        importlib.import_module(module)


def available() -> dict[str, list[str]]:
    load_plugins()
    return {"phrase_engines": sorted(_phrase_engines), "detectors": sorted(_detectors)}


def make_phrase_engine(name: str, options: PluginOptions) -> PhraseEngine:
    load_plugins()
    if name not in _phrase_engines:
        raise UnknownPlugin(f"phrase engine {name!r} isn't plugged in; have {sorted(_phrase_engines)}")
    return _phrase_engines[name](options)


def make_detector(name: str, options: PluginOptions) -> Detector:
    load_plugins()
    if name not in _detectors:
        raise UnknownPlugin(f"detector {name!r} isn't plugged in; have {sorted(_detectors)}")
    return _detectors[name](options)


def run_phrase_engine(engine: PhraseEngine, turn: Turn) -> PhraseHit | None:
    """A phrase engine that raises or returns junk counts as no hit."""
    try:
        raw = engine.match(turn)
        return None if raw is None else PhraseHit.model_validate(raw)
    except ValidationError:
        log.warning("phrase engine output invalid", extra={"code": "phrase_invalid"})
    except Exception as e:  # noqa: BLE001 - a plug-in must never break the call
        log.warning("phrase engine failed", extra={"code": "phrase_error", "error": type(e).__name__})
    return None


async def run_detector(detector: Detector, context: AssessmentContext, timeout: float) -> tuple[Assessment | None, bool]:
    """Returns (assessment, failed). Timeouts, errors and invalid output are failures."""
    started = time.monotonic()
    try:
        raw = await asyncio.wait_for(detector.assess(context), timeout)
    except asyncio.TimeoutError:
        log.warning("detector timed out", extra={"code": "detector_timeout", "call_id": context.call_id})
        return None, True
    except Exception as e:  # noqa: BLE001 - a plug-in must never break the call
        log.warning("detector failed", extra={"code": "detector_error", "error": type(e).__name__, "call_id": context.call_id})
        return None, True
    ms = round((time.monotonic() - started) * 1000)
    if raw is None:
        log.info("detector had nothing", extra={"call_id": context.call_id, "ms": ms})
        return None, False
    try:
        assessment = raw if isinstance(raw, Assessment) else Assessment.model_validate(raw)
    except ValidationError:
        log.warning("detector output invalid", extra={"code": "detector_invalid", "call_id": context.call_id})
        return None, True
    log.info("detector answered", extra={"call_id": context.call_id, "ms": ms, "request_type": assessment.request_type})
    return assessment, False


class RateLimiter:
    """Account-wide cap on detector calls per minute (Sarvam-105B Starter allows 40)."""

    def __init__(self, per_minute: int, clock: Callable[[], float] = time.monotonic) -> None:
        self._per_minute = per_minute
        self._clock = clock
        self._calls: deque[float] = deque()

    def try_acquire(self) -> bool:
        now = self._clock()
        while self._calls and now - self._calls[0] >= 60:
            self._calls.popleft()
        if len(self._calls) >= self._per_minute:
            return False
        self._calls.append(now)
        return True
