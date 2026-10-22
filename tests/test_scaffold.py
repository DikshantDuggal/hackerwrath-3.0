import asyncio
import json

import httpx
import pytest
from pydantic import ValidationError

from edgerunners_api.main import app
from edgerunners_contracts import RequestType, WarningEvent
from edgerunners_detection.phrases import advisories


def test_health_is_distinct_from_protection_readiness():
    async def exercise():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            assert (await client.get("/healthz")).status_code == 200
            response = await client.get("/readyz")
            assert response.status_code == 503
            assert response.json()["state"] == "protection_unavailable"
            schema = (await client.get("/api/contracts/warning")).json()
            assert schema == WarningEvent.model_json_schema()

    asyncio.run(exercise())


@pytest.mark.parametrize("text,expected", [
    ("Read me the code you just received", {RequestType.OTP_SHARE}),
    ("Enter your PIN to receive this payment", {RequestType.PIN_RECEIVE}),
    ("Scan my QR to receive money", {RequestType.QR_RECEIVE}),
    ("Never share your OTP", set()),
    ("Send me your QR so I can pay", set()),
    ("I work in the army; is the cycle available?", set()),
])
def test_starter_advisories(text, expected):
    assert advisories(text) == expected


def test_wire_contract_rejects_unknown_actions_and_bad_sequence():
    event = dict(v=1, call_id="call_123", event_seq=18, assessment_revision=7,
                 type="confirmed", alert_id="alert_4", request_type="otp_share", level="high")
    assert WarningEvent.model_validate_json(json.dumps(event)).event_seq == 18
    for patch in ({"event_seq": 0}, {"request_type": "freeze_account"}, {"action": "hold"}):
        with pytest.raises(ValidationError):
            WarningEvent.model_validate_json(json.dumps(event | patch))
