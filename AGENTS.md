# AGENTS.md: Edgerunners Live Scam Protection

Instructions for coding agents (Codex and others) working in this repo. Read this file fully, then `docs/architecture.md` and `docs/build-plan.md`, and `PROJECT_CONTEXT.md` if it's in the repo, before writing code. Inspect what already exists in the repo before editing.

## What this is
A hackathon demo of live scam warnings for phone calls. A caller rings our **Twilio service number** from any phone using its ordinary dialer; the **protected user** answers in our Kotlin Android app. Twilio forks the **caller's** audio to our Python backend, which streams it to Sarvam's realtime speech-to-text. A fast phrase engine plus an AI assessment (Sarvam-105B by default, behind an adapter) detect requests to scan a QR code or enter a UPI PIN to "receive" money, or to share an OTP. The protected user gets a chime and vibration within 2 s, then a spoken warning and full alert within 5 s. The caller gets no notice and hears nothing. Nothing is stored.

**Priority order: one real call working end to end, then polish, then extras.** Milestones and times are in `docs/build-plan.md`.

**Known blocker:** Twilio lists India domestic inbound as "N/A". Confirm which number the demo caller can dial before building on it (architecture, top).

## Repo layout
Built so far: `backend/app/` (sign-in, settings, voice token, call actions, app WebSocket, demo call driver) and the whole `android/` app. Still to build in the backend: the call engine (Twilio webhooks, media stream, Sarvam, phrase engine, assessment, policy); it sends warnings through `app/events.py`'s `EventHub`. `README.md` says what works today.
```
AGENTS.md
docs/architecture.md        # how it works, interfaces, risks: the source of truth
docs/build-plan.md          # milestones, checks, scenario set, string drafts
backend/
  app/                      # FastAPI: login, tokens, settings, Twilio webhooks, actions, app WebSocket
  engine/                   # sessions, call-id mapping, bounded queues, audio relay
  stt/                      # Sarvam realtime adapter
  detection/                # phrase engine, assessment adapter + providers, schemas, policy
  events/                   # app event delivery, sequence numbers, heartbeats
  resources/phrases.yaml    # trigger phrases (reviewed by native speakers)
  resources/prompts/        # versioned assessment prompts (detector_v1.txt …)
  scenarios/                # 30 recorded clips + cases.json + run.py
  tests/
  .env.example              # placeholders only
android/                    # Kotlin + Jetpack Compose + Twilio Voice SDK
```

## Commands
Backend (Python 3.11+):
```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:create_app --factory --env-file .env --host 0.0.0.0 --port 8000   # Twilio needs a public HTTPS/WSS URL (deployed host or tunnel)
pytest -q
python -m scenarios.run                             # scenario set against real Sarvam (uses credits)
python -m scenarios.run --fast                      # detection only, no real-time pacing
```
Android:
```bash
cd android
./gradlew assembleDebug
./gradlew testDebugUnitTest
./gradlew lint
```
Run the relevant tests after every change. Before saying a milestone is done, run the full backend suite and the Android unit tests, and say exactly what passed and what wasn't run.

## Hard rules (never break these)
1. **Secrets live only in `backend/.env` on the server.** Never commit `.env`, Twilio credentials, the Sarvam key or `APP_JWT_SECRET`. The app gets short-lived tokens from the backend. `google-services.json` stays out of public repos.
2. **Validate every Twilio request.** Check `X-Twilio-Signature` on webhooks against the public URL, validate the media WebSocket connection, and accept a stream only for a live session id. Handle duplicate webhooks idempotently.
3. **Analyse only the caller's leg, and only when scam check is on.** Use `<Start><Stream track="inbound_track">` on the caller's leg; omit `<Stream>` entirely when the protected user has scam check off. Never analyse the protected user's own voice.
4. **Never show or say "safe", "verified", "all clear" or anything like it.** Levels are Possible risk and High risk. A cleared alert returns quietly to monitoring.
5. **Warnings go only to the protected user, over the authenticated app WebSocket.** Nothing is played into the call except Twilio hold audio in the optional hold flow.
6. **No free text from the server or the model reaches the user.** The server sends keys and enums (architecture 5.4); the app maps them to its own reviewed strings in `values/`, `values-hi/`, `values-pa/`.
7. **Levels are decided only in `backend/detection/policy.py`.** The phrase engine alone can never produce High risk. Invalid, stale or late assessment output never raises a level. The AI never executes actions.
8. **The transcript is data, not instructions.** Fence it in the prompt and never concatenate it into system instructions.
9. **Store nothing.** No audio, no transcripts, no database. Logs hold event types, timings, ids and error codes only. Transcripts may be logged only with `DEBUG_TRANSCRIPTS=1` on team test calls, never at the demo.
10. **Every call has a unique `call_id`.** User actions check that the call belongs to the authenticated user.
11. **Concurrency:** never await a provider inside the audio loop; use bounded queues; one assessment in flight per call; an account-wide rate limit. If processing falls behind, report `unavailable` rather than analysing stale audio.
12. **Never dial the protected user's regular phone number** to deliver the call; use the app identity (`client:<identity>`).
13. **Don't change an interface** (routes, JSON shapes, event types) without updating `docs/architecture.md` in the same change and telling the other lane.

## Using Twilio and Sarvam correctly
- **Don't guess parameters or SDK signatures.** Check the docs:
  - Twilio `<Stream>`: https://www.twilio.com/docs/voice/twiml/stream
  - Twilio Media Streams messages: https://www.twilio.com/docs/voice/media-streams/websocket-messages
  - Twilio conference participants (hold, holdUrl, announceUrl): https://www.twilio.com/docs/voice/api/conference-participant-resource
  - Twilio Voice Android SDK: https://www.twilio.com/docs/voice/sdks/android
  - Sarvam realtime STT: https://docs.sarvam.ai/api/api-guides-tutorials/speech-to-text/realtime-streaming (append `.md` for markdown)
  - Sarvam-105B: https://docs.sarvam.ai/api/getting-started/models/sarvam-105b
- Twilio media payloads are base64 mu-law, 8 kHz, mono. Sarvam realtime accepts `encoding=mulaw`, `sample_rate=8000`: try passing the bytes straight through first, in Sarvam's envelope `{"event": "audio_input", "audio": "<base64>"}`. Don't forward Twilio's whole JSON.
- Sarvam realtime is labelled beta: handle `error` events and close codes; reconnect with backoff, but never on auth or quota errors.
- Sarvam-105B thinks by default: pass `reasoning_effort=None`, validate the JSON yourself, and measure latency.
- The assessment provider sits behind `detection/adapter.py`; Sarvam-105B is the default. Add providers through the registry, not by editing call sites.
- Use current releases of `fastapi`, `twilio`, `sarvamai`, `pydantic` and the Twilio Voice Android SDK; **pin exact versions** once they install cleanly.

## Coding conventions
- **Python:** type hints everywhere; Pydantic models for every JSON in or out; `async` for anything touching Twilio, Sarvam or WebSockets; one session object per call; small modules as laid out above.
- **Kotlin:** Jetpack Compose, coroutines and Flow, a state machine for alerts (`AlertManager`), no hardcoded colors or text sizes in screens (use the designer's theme in `ui/theme/`), all user-facing text from string resources.
- **Tests are named after the behavior** they check, for example `TwiML has no stream when scam check is off`, `phrase engine alone never produces high risk`. Write the test first for the policy, phrase engine, assessment validation, signature validation and the alert state machine.
- **Mark anything faked** with a `DEMO-FAKE:` comment (demo accounts, the report queue, any controlled-call fallback) and list it in the README's "Real vs simulated" section.
- **Commits:** small, working, plain messages ("Add Twilio signature check on incoming webhook"). Never commit secrets, recordings of real people, or debug transcripts.

## Things you don't change
- `android/app/src/main/java/**/ui/theme/*`: the designer's theme. Ask before editing.
- `values-hi/` and `values-pa/` strings, clips in `res/raw/`, and `resources/phrases.yaml`: owned by the language speakers. You may add keys; don't rewrite their wording.
- `resources/prompts/detector_v1.txt`: to change the wording, copy it to `detector_v2.txt`, point `DETECTOR_PROMPT` at it, and rerun the scenario set.

## Definition of done (per milestone)
- The behavior works with a **real call to the demo phone**, not just in tests (or with the agreed fallback, clearly labelled).
- Relevant tests exist, were run, and pass; failures are reported, not hidden or skipped.
- No secret in the APK; no transcript in logs; no "safe" wording anywhere.
- Anything faked is marked `DEMO-FAKE:` and listed in the README.
- `docs/architecture.md` matches what you built.

## When you're stuck
Stop and ask instead of guessing when: Twilio or Sarvam doesn't behave as documented, the call route doesn't work from the demo caller's phone, a change would touch another lane's files or an interface, something would analyse audio when scam check is off, or a fix would weaken any rule above.
