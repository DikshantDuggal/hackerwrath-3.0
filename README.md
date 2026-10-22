# Edgerunners Live Scam Protection

Live scam warnings during phone calls, in English, Hindi and Punjabi. A caller rings our service number from any phone; the protected user answers in our Android app; if the caller asks them to scan a QR code or enter a UPI PIN to "receive" money, or to share an OTP, the app warns them: a chime and vibration within 2 s, then a spoken warning and a full alert within 5 s. The caller never sees or hears any warning.

Read `AGENTS.md`, `docs/architecture.md`, `docs/build-plan.md` and `docs/ux-flows.md` for the design. `PROJECT_CONTEXT.md` has the Twilio background.

## What works today
| Part | State |
|---|---|
| Android app in the **Spellbreaker** design (from the "Scam Check Guardian" design canvas): sign-in; Home with the guardian switch, week dial and scams-stopped count; Recents; Contacts and Your circle; settings, demo-call, recovery and keypad sheets; incoming call; "at your ear" call screen (Listening / Checking / Unavailable / Off); the full-screen alert that rotates through three looks (red field, night siren, red frame); on-hold screen; after-call story; "Feel a warning" practice | Built, not yet compiled |
| Call history for Recents and the week dial: masked number, times, outcome and request type, on the phone only | Built |
| App ↔ backend: REST (login, settings, voice token, call actions) and the private warning WebSocket with reconnects and a 10 s heartbeat watchdog | Built |
| Warning experience: chime + three long vibration pulses, spoken clip slot, heads-up notification over other apps, call muted during cues (your mute choice restored) | Built (spoken clips still to record) |
| Motion: soft screen transitions, breathing waveform, amber panel ease-in with one icon pulse, alert sheet slides up, buttons give on press; all off when Android animations are off | Built |
| Twilio calling in the app (Voice SDK, push registration, answer/decline/end, mute, speaker) | Built; needs Twilio + Firebase setup |
| Backend: sign-in, settings, voice token, call actions, app WebSocket, heartbeat | Built |
| Backend: demo call driver (scripted QR / OTP / harmless / unavailable calls) | Built (DEMO-FAKE) |
| Backend: call engine (Twilio webhooks, caller media stream, Sarvam STT, phrase engine, assessment, policy) | **Not built yet**: see `docs/build-plan.md` Milestones 1–4 |
| Hindi and Punjabi strings, spoken clips | **To do** by the language speakers (`values-hi/`, `values-pa/`, `res/raw/`) |

Nothing here has been compiled or run yet on the machine it was written on (no Android or Python tooling there). Expect a first-build fix pass.

## Real vs simulated
- **Real:** the app, its backend connection, warnings, sounds and haptics, failure handling, Twilio calling code.
- **Simulated (DEMO-FAKE):** demo accounts, the demo call driver and its scripted callers, the report queue. In the app: the sample people in Contacts and Your circle (`ui/spell/DemoPeople.kt`), and the actions that need them (call a contact, keypad call, block, tell your trusted person, send a test, setup code). These show "Demo only. This isn't connected yet."
- **Waiting on the backend:** "Put them on hold · 30 s" calls the `hold` action, which answers 501 until the hold flow (architecture section 7) is built; the app then says hold isn't available and never shows the on-hold screen.
- **Never fake:** a demo call presented as a real phone call, or a pre-triggered warning presented as live detection.

## Run the backend
Python 3.11 or newer.
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate            # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env            # then edit: APP_JWT_SECRET, DEMO_USERS, DEMO_MODE=1
pytest -q
uvicorn app.main:create_app --factory --env-file .env --host 0.0.0.0 --port 8000
```

## Run the app
1. Open `android/` in Android Studio (it sets up Gradle and the SDK).
2. Copy `android/local.properties.example` to `android/local.properties` and set `api.baseUrl`:
   - emulator: `http://10.0.2.2:8000`
   - real phone on the same Wi-Fi: `http://<your computer's LAN IP>:8000`
   - deployed backend: its HTTPS URL
3. Run the `app` configuration on a phone or emulator (Android 7.1+).
4. Sign in with a `DEMO_USERS` account, allow microphone and notifications.
5. Open **Settings** (top right) → **Demo calls**, or long-press the shield on Home, and pick a scripted call (QR scan, OTP, ordinary, protection drops out). The phone rings; answer it; watch the guardian turn amber, then the alert rise.
6. Optional: set `ui.edition=premium` in `local.properties` for the Premium (night and gold) edition.

The Spellbreaker type uses Anek (Standard) and Tiro (Premium). Until those font files are added to `res/font`, the app uses the system sans and serif (see `ui/theme/Type.kt`).

Tip: turn on "I'm expecting a payment" before the QR scan demo to see High risk; leave it off to see Possible risk.

## Turn on real calls (Twilio)
1. Twilio: an API key, a TwiML app, and a push credential for FCM. Put them in `backend/.env`.
2. Firebase: create a project, add an Android app with package `com.edgerunners.scamcheck`, and copy its app ID, API key, project ID and sender ID into `android/local.properties`.
3. Build the call engine (backend Milestones 1–4) so incoming calls reach the app and the caller's audio is analysed.
4. Settle which number the demo caller can dial (Twilio lists India domestic inbound as "N/A").

## Tests
- Backend: `pytest -q` in `backend/`: sign-in, settings, the WebSocket handshake, call ownership, and each demo scenario's events.
- App: `./gradlew testDebugUnitTest` in `android/`: the alert state machine (other calls and stale events ignored, one chime per 20 s, 10 s silence → unavailable, never "safe"), the event parser, and call history (outcomes, masking, the week).
