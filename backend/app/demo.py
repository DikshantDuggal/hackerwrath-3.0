"""DEMO-FAKE: scripted calls for testing the app end to end without Twilio or Sarvam.

The live engine (Twilio media stream -> Sarvam -> phrase engine -> assessment -> policy)
emits the same events through EventHub; this driver only fakes what is heard.
Enabled only when DEMO_MODE=1.

Most scenarios script the events directly. The "detector" scenario instead scripts what the
caller says and feeds it through the plugged-in phrase engine, detector and policy, so a
plug-in can be tried against the real app (docs/plugins.md).
"""

from __future__ import annotations

import asyncio

from detection.policy import ALWAYS_HIGH

from .config import Config
from .events import EventHub
from .store import CallSession, UserSettings

SCENARIOS = ("qr_scan", "otp", "remote_access", "harmless", "unavailable", "detector")
DEMO_CALLER = "+91 90000 12345"

# Scenario -> (request type, first warning signals, confirmed signals).
SCRIPTED = {
    "qr_scan": ("qr_receive", ("financial_solicitation",), ("financial_solicitation",)),
    "otp": (
        "otp_share",
        ("otp_or_pin_request",),
        ("otp_or_pin_request", "authority_impersonation", "account_suspension_threat"),
    ),
    "remote_access": (
        "remote_access",
        ("remote_access",),
        ("remote_access", "otp_or_pin_request", "financial_solicitation"),
    ),
    "harmless": ("qr_receive", ("financial_solicitation",), ()),
}

# DEMO-FAKE: what the scripted caller "says" in the detector scenario, as (text, final).
DETECTOR_SCRIPT = (
    ("Hello, I'm calling from your bank's customer care.", True),
    ("Your account will be blocked today because your KYC expired.", True),
    ("To stop it, please read me the", False),
    ("To stop it, please read me the OTP you just received.", True),
)


async def heartbeat(hub: EventHub, call: CallSession, config: Config) -> None:
    """Status every few seconds while the call is active, so the app can spot silence."""
    while call.state == "ACTIVE":
        await hub.status(call, call.monitor)
        await asyncio.sleep(config.heartbeat_seconds * config.demo_time_scale)


async def _start_monitoring(hub: EventHub, call: CallSession, settings: UserSettings, config: Config) -> bool:
    if not settings.scam_check:
        call.monitor = "off"
        await hub.status(call, "off")
        return False
    await hub.status(call, "starting")
    await asyncio.sleep(1 * config.demo_time_scale)
    call.monitor = "monitoring"
    await hub.status(call, "monitoring")
    return True


async def run_scenario(hub: EventHub, call: CallSession, settings: UserSettings, config: Config) -> None:
    def wait(seconds: float):
        return asyncio.sleep(seconds * config.demo_time_scale)

    if not await _start_monitoring(hub, call, settings, config):
        return

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

    request_type, first_signals, confirmed_signals = SCRIPTED[scenario]
    await wait(3)
    if call.state != "ACTIVE" or call.continued:
        return
    await hub.first_warning(call, "al_1", request_type, first_signals)

    await wait(3)
    if call.state != "ACTIVE" or call.continued:
        return
    if scenario == "harmless":
        await hub.cleared(call, "al_1")
        return
    # Mirrors the policy: "scan to receive" is high risk when the user expects a payment;
    # an OTP or remote-access request is high risk on its own.
    expecting = settings.role_context == "expecting_payment"
    level = "high" if (request_type in ALWAYS_HIGH or expecting) else "possible"
    await hub.confirmed(call, "al_1", request_type, level, confirmed_signals)


async def run_detector_script(hub: EventHub, call: CallSession, settings: UserSettings, config: Config) -> None:
    """Feeds DETECTOR_SCRIPT through the call's engine, as speech-to-text would."""
    if not await _start_monitoring(hub, call, settings, config):
        return
    for text, final in DETECTOR_SCRIPT:
        await asyncio.sleep(2 * config.demo_time_scale)
        if call.state != "ACTIVE":
            return
        await call.engine.hear(text, final)
    await call.engine.wait_idle()
