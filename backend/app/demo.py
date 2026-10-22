"""DEMO-FAKE: scripted calls for testing the app end to end without Twilio or Sarvam.

The live engine (Twilio media stream -> Sarvam -> phrase engine -> assessment -> policy)
emits the same events through EventHub; this driver only fakes what is heard.
Enabled only when DEMO_MODE=1.
"""

from __future__ import annotations

import asyncio

from .config import Config
from .events import EventHub
from .store import CallSession, UserSettings

SCENARIOS = ("qr_scan", "otp", "harmless", "unavailable")
DEMO_CALLER = "+91 90000 12345"


async def heartbeat(hub: EventHub, call: CallSession, config: Config) -> None:
    """Status every few seconds while the call is active, so the app can spot silence."""
    while call.state == "ACTIVE":
        await hub.status(call, call.monitor)
        await asyncio.sleep(config.heartbeat_seconds * config.demo_time_scale)


async def run_scenario(hub: EventHub, call: CallSession, settings: UserSettings, config: Config) -> None:
    def wait(seconds: float):
        return asyncio.sleep(seconds * config.demo_time_scale)

    if not settings.scam_check:
        call.monitor = "off"
        await hub.status(call, "off")
        return

    await hub.status(call, "starting")
    await wait(1)
    call.monitor = "monitoring"
    await hub.status(call, "monitoring")

    scenario = call.scenario or "qr_scan"
    if scenario == "unavailable":
        await wait(4)
        call.monitor = "unavailable"
        await hub.status(call, "unavailable", "stt_down")
        await wait(10)
        if call.state == "ACTIVE":
            call.monitor = "monitoring"
            await hub.status(call, "monitoring")
        return

    request_type = "otp_share" if scenario == "otp" else "qr_receive"
    await wait(3)
    if call.state != "ACTIVE" or call.continued:
        return
    await hub.first_warning(call, "al_1", request_type)

    await wait(3)
    if call.state != "ACTIVE" or call.continued:
        return
    if scenario == "harmless":
        await hub.cleared(call, "al_1")
        return
    # Mirrors the policy: "scan to receive" is high risk when the user expects a payment;
    # an OTP request is high risk on its own.
    expecting = settings.role_context == "expecting_payment"
    level = "high" if (request_type == "otp_share" or expecting) else "possible"
    await hub.confirmed(call, "al_1", request_type, level)
