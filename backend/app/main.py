"""FastAPI app: the app-facing API, the warning WebSocket and the demo call driver.

Run:  uvicorn app.main:create_app --factory --env-file .env --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import asyncio
import logging

from fastapi import FastAPI, Header, WebSocket, WebSocketDisconnect
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from . import demo
from .auth import Auth
from .config import Config, load_config
from .errors import ApiError, api_error_handler, validation_error_handler
from .events import EventHub
from .schemas import (
    ActionIn,
    ActionOut,
    DemoCallIn,
    DemoCallOut,
    LoginIn,
    LoginOut,
    SettingsBody,
    VoiceTokenOut,
)
from .store import CallSession, Store

log = logging.getLogger("app")


def create_app(config: Config | None = None) -> FastAPI:
    config = config or load_config()
    auth = Auth(config)
    store = Store()
    hub = EventHub()

    app = FastAPI(title="Edgerunners backend", docs_url=None, redoc_url=None)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_exception_handler(ApiError, api_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.state.store = store
    app.state.hub = hub

    def owned_call(call_id: str, user_id: str) -> CallSession:
        call = store.calls.get(call_id)
        if call is None:
            raise ApiError(404, "unknown_call", "That call isn't active.")
        if call.user_id != user_id:
            raise ApiError(403, "not_your_call", "That call belongs to someone else.")
        return call

    def stop_tasks(call: CallSession) -> None:
        current = asyncio.current_task()
        for task in call.tasks:
            if task is not current:
                task.cancel()
        call.tasks.clear()

    @app.get("/healthz")
    async def healthz() -> dict:
        # Process health only: says nothing about speech recognition or detection.
        return {"ok": True}

    @app.post("/api/login", response_model=LoginOut)
    async def login(body: LoginIn) -> LoginOut:
        token = auth.login(body.username, body.password)
        return LoginOut(app_token=token, user_id=body.username)

    @app.post("/api/voice-token", response_model=VoiceTokenOut)
    async def voice_token(authorization: str | None = Header(default=None)) -> VoiceTokenOut:
        user_id = auth.user_from_header(authorization)
        if not config.voice_configured:
            raise ApiError(503, "voice_not_configured", "Phone calling isn't set up on this server.")
        from twilio.jwt.access_token import AccessToken
        from twilio.jwt.access_token.grants import VoiceGrant

        token = AccessToken(
            config.twilio_account_sid,
            config.twilio_api_key_sid,
            config.twilio_api_key_secret,
            identity=user_id,
            ttl=3600,
        )
        token.add_grant(
            VoiceGrant(
                outgoing_application_sid=config.twilio_twiml_app_sid,
                incoming_allow=True,
                push_credential_sid=config.twilio_push_credential_sid or None,
            )
        )
        jwt_value = token.to_jwt()
        if isinstance(jwt_value, bytes):
            jwt_value = jwt_value.decode()
        return VoiceTokenOut(voice_token=jwt_value, identity=user_id)

    @app.get("/api/settings", response_model=SettingsBody)
    async def get_settings(authorization: str | None = Header(default=None)) -> SettingsBody:
        user_id = auth.user_from_header(authorization)
        s = store.settings_for(user_id)
        return SettingsBody(scam_check=s.scam_check, lang=s.lang, role_context=s.role_context)

    @app.put("/api/settings", response_model=SettingsBody)
    async def put_settings(body: SettingsBody, authorization: str | None = Header(default=None)) -> SettingsBody:
        user_id = auth.user_from_header(authorization)
        s = store.settings_for(user_id)
        s.scam_check, s.lang, s.role_context = body.scam_check, body.lang, body.role_context
        return body

    @app.post("/api/calls/{call_id}/actions", response_model=ActionOut)
    async def call_action(
        call_id: str, body: ActionIn, authorization: str | None = Header(default=None)
    ) -> ActionOut:
        user_id = auth.user_from_header(authorization)
        call = owned_call(call_id, user_id)
        settings = store.settings_for(user_id)

        if body.action == "answer":
            if call.state == "RINGING":
                call.state = "ACTIVE"
                call.tasks.append(asyncio.create_task(demo.heartbeat(hub, call, config)))
                if call.demo:
                    call.tasks.append(asyncio.create_task(demo.run_scenario(hub, call, settings, config)))
                # Live calls: the call engine starts analysis from the Twilio media stream.
        elif body.action == "decline":
            if call.state == "RINGING":
                call.state = "ENDED"
                stop_tasks(call)
                await hub.call_ended(call, "declined")
        elif body.action == "end":
            if call.state != "ENDED":
                call.state = "ENDED"
                stop_tasks(call)
                await hub.call_ended(call, "user_ended")
                # Live calls: the call engine also ends the Twilio conference.
        elif body.action == "continue":
            call.continued = True
        elif body.action == "report":
            store.add_report(call, body.request_type)
        else:  # hold / resume: built after ordinary alerts work
            raise ApiError(501, "not_available", "Hold isn't available yet.")
        return ActionOut(ok=True, call_state=call.state)

    @app.post("/api/demo/calls", response_model=DemoCallOut, status_code=201)
    async def demo_call(body: DemoCallIn, authorization: str | None = Header(default=None)) -> DemoCallOut:
        if not config.demo_mode:
            raise ApiError(404, "not_found", "Not found.")
        user_id = auth.user_from_header(authorization)
        call = store.new_call(user_id, demo.DEMO_CALLER, demo=True, scenario=body.scenario)
        await hub.call_started(call)
        return DemoCallOut(call_id=call.call_id)

    @app.websocket("/ws/app")
    async def ws_app(ws: WebSocket) -> None:
        await ws.accept()
        try:
            first = await asyncio.wait_for(ws.receive_json(), timeout=5)
            if not isinstance(first, dict) or first.get("type") != "auth":
                raise ApiError(401, "missing_token", "auth first")
            user_id = auth.verify(str(first.get("app_token", "")))
        except (ApiError, asyncio.TimeoutError, ValueError, WebSocketDisconnect):
            try:
                await ws.close(code=4401)
            except RuntimeError:
                pass
            return
        await hub.add(user_id, ws)
        await ws.send_json({"v": 1, "type": "ready"})
        try:
            while True:
                await ws.receive_text()  # the app sends nothing else; keep the socket open
        except WebSocketDisconnect:
            pass
        finally:
            await hub.remove(user_id, ws)

    return app
