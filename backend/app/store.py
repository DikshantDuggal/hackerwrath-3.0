"""In-memory state. Nothing is persisted: no audio, no transcripts, no database."""

from __future__ import annotations

import asyncio
import secrets
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class UserSettings:
    scam_check: bool = True
    lang: str = "en"
    role_context: str | None = None


@dataclass
class CallSession:
    call_id: str
    user_id: str
    from_number: str
    demo: bool
    scenario: str | None = None
    state: str = "RINGING"          # RINGING | ACTIVE | ENDED
    monitor: str = "starting"       # starting | monitoring | degraded | unavailable | off
    continued: bool = False
    seq: int = 0
    revision: int = 0
    tasks: list[asyncio.Task] = field(default_factory=list)
    # The engine.session.CallEngine analysing this call, when one is.
    engine: Any = None

    def next_seq(self) -> int:
        self.seq += 1
        return self.seq

    def next_revision(self) -> int:
        self.revision += 1
        return self.revision


@dataclass
class Report:
    report_id: str
    call_id: str
    from_number: str
    request_type: str | None
    at: float


class Store:
    def __init__(self) -> None:
        self.settings: dict[str, UserSettings] = {}
        self.calls: dict[str, CallSession] = {}
        self.reports: list[Report] = []

    def settings_for(self, user_id: str) -> UserSettings:
        return self.settings.setdefault(user_id, UserSettings())

    def new_call(self, user_id: str, from_number: str, demo: bool, scenario: str | None = None) -> CallSession:
        call = CallSession(
            call_id="call_" + secrets.token_hex(6),
            user_id=user_id,
            from_number=from_number,
            demo=demo,
            scenario=scenario,
        )
        self.calls[call.call_id] = call
        return call

    def add_report(self, call: CallSession, request_type: str | None) -> Report:
        report = Report("rep_" + secrets.token_hex(4), call.call_id, call.from_number, request_type, time.time())
        self.reports.append(report)
        return report
