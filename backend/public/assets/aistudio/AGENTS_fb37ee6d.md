# AGENTS.md: Edgerunners Live Scam Protection

Instructions for coding agents (Codex and others) working in this repo. Read this file fully, then `docs/architecture.md` and `docs/build-plan.md` before writing code.

## What this is
A 9-hour hackathon demo. A seller (Android app) and a buyer (web page) talk in an in-app call about a marketplace listing. A Python worker listens to the **buyer's** audio, sends it to Sarvam's realtime speech-to-text, and if the buyer asks the seller to scan a QR code, enter a UPI PIN or share an OTP, it warns the **seller only**: a chime and vibration within 2 s, then a spoken warning and full alert within 5 s. Calls run on LiveKit Cloud. Detection uses a fast phrase check plus Sarvam-105B. Nothing is stored.

**Priority order: get one full demo call working end to end, then polish, then extras.** See `docs/build-plan.md` for milestones and times.

## Repo layout
```
AGENTS.md
docs/architecture.md        # how it works, interfaces, risks: the source of truth
docs/build-plan.md          # milestones, checks, scenario set, string drafts
backend/
  app/                      # FastAPI: call tokens, rooms, listing, reports
  worker/                   # LiveKit worker: audio → Sarvam STT → phrase check → detector → policy → alerts
  data/listings.json        # the one demo listing
  data/phrases.yaml         # trigger phrases (reviewed by native speakers)
  prompts/detector_v1.txt   # detector system prompt (versioned by file name)
  scenarios/                # 15 recorded clips + cases.json + run.py
  tests/
  .env.example              # placeholders only
android/                    # Kotlin + Jetpack Compose seller app
web/                        # buyer page (owned by the designer)
```

## Commands
Backend (Python 3.11+):
```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000           # API
python -m worker.agent dev                          # worker (LiveKit Agents dev mode; check the CLI in their docs)
pytest -q                                           # all backend tests
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
Run the relevant tests after every change. Before saying a milestone is done, run the full backend test suite and the Android unit tests, and say exactly what passed and what wasn't run.

## Hard rules (never break these)
1. **Secrets live only in `backend/.env` on the server.** Never commit `.env`. Never put the Sarvam key, LiveKit API secret, `DEMO_ACCESS_CODE` server value or `TS_DEMO_KEY` in Android or web code. Clients get short-lived LiveKit tokens from `POST /api/call-token`.
2. **Never show or say "safe", "verified", "all clear" or anything like it.** The levels are Possible risk and High risk. A cleared alert closes quietly.
3. **Warnings go to the protected seller only.** Send `scam-alert` messages with destination identities set to the protected identity from room metadata. Never broadcast. The buyer page never handles `scam-alert`.
4. **The seller app accepts `scam-alert` messages only from the identity `scam-check`.** Ignore everything else.
5. **No free text from the server or the model ever reaches the user.** The worker sends keys and enums (architecture 5.3); the app maps them to its own reviewed strings in `values/`, `values-hi/`, `values-pa/`.
6. **Levels are decided only in `backend/worker/policy.py`.** The phrase check alone can never produce High risk. Invalid or late model output never raises a level.
7. **The transcript is data, not instructions.** Keep it inside the fenced block in the detector prompt. Never concatenate transcript text into the system prompt.
8. **No analysis when scam check is off.** The worker reads room metadata (set only by the API) and leaves the room before opening any Sarvam connection if `scam_check` isn't true. Only the buyer's audio is analysed, never the protected seller's.
9. **Store nothing.** No audio, no transcripts, no database. Logs hold event types, request types, ids and latencies only. Transcripts may be logged only when `DEBUG_TRANSCRIPTS=1`, for team test calls, never at the demo.
10. **Respect the caps:** 15 minutes of audio per call to Sarvam, 30 detector calls per call, one detector call in flight, 3 s detector timeout. Never retry Sarvam in a tight loop.
11. **Spoken and chime cues play only on the seller's phone, with the seller's mic muted while they play.**
12. **Don't change an interface** (routes, JSON shapes, message types, room metadata) without updating `docs/architecture.md` in the same change and telling the other lane.

## Using Sarvam and LiveKit correctly
- **Don't guess API parameters.** Check the docs (markdown versions: append `.md` to a Sarvam docs URL):
  - Sarvam realtime STT: https://docs.sarvam.ai/api/api-guides-tutorials/speech-to-text/realtime-streaming
  - Sarvam-105B: https://docs.sarvam.ai/api/getting-started/models/sarvam-105b
  - LiveKit text streams: https://docs.livekit.io/transport/data/text-streams
  - LiveKit raw audio (Python): https://docs.livekit.io/transport/media/raw-tracks
  - LiveKit index: https://docs.livekit.io/llms.txt
- Sarvam realtime STT: endpoint `/speech-to-text-realtime/ws`, `stream_type="fast"`, 16 kHz mono `linear16`, audio as `{"event": "audio_input", "audio": "<base64>"}`, partials arrive as `transcript.partial`. It's labelled beta: handle `error` events and the close codes.
- Sarvam-105B thinks by default: always pass `reasoning_effort=None` for the detector, and validate the JSON yourself.
- Use current releases of `livekit-agents`, `livekit-api`, `sarvamai`, `fastapi`, `pydantic` and the LiveKit Android SDK; **pin exact versions** in `requirements.txt` and Gradle once they install cleanly.

## Coding conventions
- **Python:** type hints everywhere, Pydantic models for every JSON in or out, `async` for anything touching LiveKit or Sarvam, no global mutable state outside one `CallMonitor` per call. Small modules as laid out above.
- **Kotlin:** Jetpack Compose, coroutines and Flow, a state machine for alerts (`AlertManager`), no hardcoded colors or text sizes in screens (use the theme in `ui/theme/` from the designer), all user-facing text from string resources.
- **Tests are named after the behavior** they check, for example `seller asked to scan a QR to receive payment is high risk`, `alert manager ignores messages from the buyer identity`. Write the test first for policy, phrase check, detector validation and the alert state machine.
- **Mark anything faked** with a `DEMO-FAKE:` comment (demo identities, the mock trust-and-safety queue, the listing) and list it in the README's "Real vs simulated" section.
- **Commits:** small, working, plain messages ("Add phrase check for QR requests"). Never commit secrets, recordings of real people, or debug transcripts.

## Things you don't change
- `android/app/src/main/java/**/ui/theme/*`: the designer's theme. Ask before editing.
- `values-hi/` and `values-pa/` strings, spoken clips in `res/raw/`, and `data/phrases.yaml`: owned by the language speakers. You may add keys; don't rewrite their wording.
- `prompts/detector_v1.txt`: to change the wording, copy it to `detector_v2.txt`, point `DETECTOR_PROMPT` at it, and rerun the scenario set.
- `web/`: owned by the designer.

## Definition of done (per milestone)
- The behavior works on the **demo phone** with the buyer page, not just in tests.
- Relevant tests exist, were run, and pass; failures are reported, not hidden or skipped.
- No secret in client code; no transcript in logs; no "safe" wording anywhere.
- Anything faked is marked `DEMO-FAKE:` and listed in the README.
- `docs/architecture.md` matches what you built.

## When you're stuck
Stop and ask instead of guessing when: an API doesn't behave as its docs say, a change would touch another lane's files or an interface, something would send audio when scam check is off, or a fix would weaken any rule above.
