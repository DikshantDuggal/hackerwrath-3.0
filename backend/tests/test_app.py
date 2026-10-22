"""Behaviour tests for the app-facing API and the demo call driver."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.config import Config
from app.main import create_app

SECRET = "x" * 40


@pytest.fixture
def client():
    config = Config(
        app_jwt_secret=SECRET,
        demo_users={"demo-user": "pw", "other-user": "pw2"},
        demo_mode=True,
        heartbeat_seconds=1.0,
        demo_time_scale=0.01,
    )
    # The context manager keeps one event loop alive, so background tasks started by
    # a request keep running while the WebSocket is open.
    with TestClient(create_app(config)) as c:
        yield c


def login(client: TestClient, user: str = "demo-user", pw: str = "pw") -> str:
    res = client.post("/api/login", json={"username": user, "password": pw})
    assert res.status_code == 200, res.text
    return res.json()["app_token"]


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def read_until(ws, wanted_type: str, limit: int = 60) -> list[dict]:
    seen = []
    for _ in range(limit):
        event = ws.receive_json()
        seen.append(event)
        if event.get("type") == wanted_type:
            return seen
    raise AssertionError(f"never saw {wanted_type}: {[e.get('type') for e in seen]}")


def test_signs_in_with_demo_account(client):
    res = client.post("/api/login", json={"username": "demo-user", "password": "pw"})
    assert res.status_code == 200
    assert res.json()["user_id"] == "demo-user"


def test_rejects_a_wrong_password_with_the_standard_error_shape(client):
    res = client.post("/api/login", json={"username": "demo-user", "password": "nope"})
    assert res.status_code == 401
    assert res.json() == {"error": {"code": "bad_credentials", "message": "That username or password didn't match."}}


def test_locks_out_after_five_bad_attempts(client):
    for _ in range(5):
        client.post("/api/login", json={"username": "demo-user", "password": "nope"})
    res = client.post("/api/login", json={"username": "demo-user", "password": "pw"})
    assert res.status_code == 429


def test_settings_need_a_token(client):
    assert client.get("/api/settings").status_code == 401


def test_settings_round_trip(client):
    token = login(client)
    body = {"scam_check": False, "lang": "pa", "role_context": "expecting_payment"}
    assert client.put("/api/settings", json=body, headers=auth(token)).json() == body
    assert client.get("/api/settings", headers=auth(token)).json() == body


def test_rejects_an_unknown_language(client):
    token = login(client)
    res = client.put("/api/settings", json={"scam_check": True, "lang": "fr"}, headers=auth(token))
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "invalid_request"


def test_voice_token_says_calling_is_not_set_up_without_twilio_config(client):
    token = login(client)
    res = client.post("/api/voice-token", headers=auth(token))
    assert res.status_code == 503
    assert res.json()["error"]["code"] == "voice_not_configured"


def test_websocket_closes_when_the_first_message_is_not_auth(client):
    with client.websocket_connect("/ws/app") as ws:
        ws.send_json({"type": "hello"})
        with pytest.raises(WebSocketDisconnect) as exc:
            ws.receive_json()
        assert exc.value.code == 4401


def test_websocket_closes_on_a_bad_token(client):
    with client.websocket_connect("/ws/app") as ws:
        ws.send_json({"type": "auth", "app_token": "forged"})
        with pytest.raises(WebSocketDisconnect):
            ws.receive_json()


def test_demo_qr_call_for_a_user_expecting_payment_ends_in_high_risk(client):
    token = login(client)
    client.put(
        "/api/settings",
        json={"scam_check": True, "lang": "en", "role_context": "expecting_payment"},
        headers=auth(token),
    )
    with client.websocket_connect("/ws/app") as ws:
        ws.send_json({"type": "auth", "app_token": token})
        assert ws.receive_json()["type"] == "ready"
        call_id = client.post("/api/demo/calls", json={"scenario": "qr_scan"}, headers=auth(token)).json()["call_id"]
        started = ws.receive_json()
        assert started["type"] == "call_started" and started["call_id"] == call_id
        client.post(f"/api/calls/{call_id}/actions", json={"action": "answer"}, headers=auth(token))
        events = read_until(ws, "confirmed")
    types = [e["type"] for e in events]
    assert types.index("first_warning") < types.index("confirmed")
    confirmed = events[-1]
    assert confirmed["request_type"] == "qr_receive" and confirmed["level"] == "high"
    seqs = [e["event_seq"] for e in [started, *events]]
    assert seqs == sorted(seqs) and len(set(seqs)) == len(seqs)


def test_qr_request_without_payment_context_is_possible_risk(client):
    token = login(client)
    with client.websocket_connect("/ws/app") as ws:
        ws.send_json({"type": "auth", "app_token": token})
        ws.receive_json()
        call_id = client.post("/api/demo/calls", json={"scenario": "qr_scan"}, headers=auth(token)).json()["call_id"]
        ws.receive_json()
        client.post(f"/api/calls/{call_id}/actions", json={"action": "answer"}, headers=auth(token))
        events = read_until(ws, "confirmed")
    assert events[-1]["level"] == "possible"


def test_harmless_call_clears_the_first_warning(client):
    token = login(client)
    with client.websocket_connect("/ws/app") as ws:
        ws.send_json({"type": "auth", "app_token": token})
        ws.receive_json()
        call_id = client.post("/api/demo/calls", json={"scenario": "harmless"}, headers=auth(token)).json()["call_id"]
        ws.receive_json()
        client.post(f"/api/calls/{call_id}/actions", json={"action": "answer"}, headers=auth(token))
        events = read_until(ws, "cleared")
    assert "confirmed" not in [e["type"] for e in events]


def test_no_event_carries_free_text_or_safe_wording(client):
    token = login(client)
    with client.websocket_connect("/ws/app") as ws:
        ws.send_json({"type": "auth", "app_token": token})
        ws.receive_json()
        call_id = client.post("/api/demo/calls", json={"scenario": "otp"}, headers=auth(token)).json()["call_id"]
        ws.receive_json()
        client.post(f"/api/calls/{call_id}/actions", json={"action": "answer"}, headers=auth(token))
        events = read_until(ws, "confirmed")
    allowed = {"v", "call_id", "event_seq", "type", "state", "reason", "assessment_revision",
               "alert_id", "request_type", "level", "from_number", "demo"}
    for event in events:
        assert set(event) <= allowed
        assert "safe" not in json.dumps(event).lower()


def test_scam_check_off_sends_off_and_no_warnings(client):
    token = login(client)
    client.put("/api/settings", json={"scam_check": False, "lang": "en"}, headers=auth(token))
    with client.websocket_connect("/ws/app") as ws:
        ws.send_json({"type": "auth", "app_token": token})
        ws.receive_json()
        call_id = client.post("/api/demo/calls", json={"scenario": "qr_scan"}, headers=auth(token)).json()["call_id"]
        ws.receive_json()
        client.post(f"/api/calls/{call_id}/actions", json={"action": "answer"}, headers=auth(token))
        events = [ws.receive_json() for _ in range(4)]
    assert all(e["type"] == "status" for e in events)
    assert any(e["state"] == "off" for e in events)


def test_another_user_cannot_act_on_the_call(client):
    owner = login(client)
    other = login(client, "other-user", "pw2")
    call_id = client.post("/api/demo/calls", json={"scenario": "qr_scan"}, headers=auth(owner)).json()["call_id"]
    res = client.post(f"/api/calls/{call_id}/actions", json={"action": "end"}, headers=auth(other))
    assert res.status_code == 403


def test_ending_twice_is_harmless(client):
    token = login(client)
    call_id = client.post("/api/demo/calls", json={"scenario": "qr_scan"}, headers=auth(token)).json()["call_id"]
    first = client.post(f"/api/calls/{call_id}/actions", json={"action": "end"}, headers=auth(token))
    second = client.post(f"/api/calls/{call_id}/actions", json={"action": "end"}, headers=auth(token))
    assert first.json() == second.json() == {"ok": True, "call_state": "ENDED"}


def test_unknown_call_is_404(client):
    token = login(client)
    res = client.post("/api/calls/call_nope/actions", json={"action": "end"}, headers=auth(token))
    assert res.status_code == 404


def test_demo_calls_are_off_unless_demo_mode():
    config = Config(app_jwt_secret=SECRET, demo_users={"demo-user": "pw"}, demo_mode=False)
    with TestClient(create_app(config)) as client:
        token = login(client)
        assert client.post("/api/demo/calls", json={}, headers=auth(token)).status_code == 404
