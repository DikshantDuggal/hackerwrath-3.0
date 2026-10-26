# EdgeRunner Guardian V2 — Comprehensive Launch & Verification Guide

## Executive Summary
EdgeRunner Guardian V2 is a real-time, multilingual AI-driven scam call and message interception system designed for Android and modern communication platforms. It features a hybrid multi-layer defense engine (deterministic regex safety rules, ICFD calibrated classifier, and contextual directors), real-time Sarvam Saaras multilingual STT speech processing, a unified Telegram Bot & Audio ingestion bridge, and a responsive native Android client with real-time WebSocket event synchronization.

---

## A. Development Environment & Path Manifest

| Resource | Verified File Path | Description |
| :--- | :--- | :--- |
| **Workspace Root** | `D:\edgerunner guardian frontend` | Git repository root (`hackerwrath-3.0`) |
| **Backend Root** | `D:\edgerunner guardian frontend\backend` | FastAPI application directory |
| **Python Virtualenv** | `D:\edgerunner guardian frontend\backend\.venv\Scripts\python.exe` | Python 3.11+ environment with PyTorch & HuggingFace |
| **Android SDK Root** | `D:\android-tools\android-sdk` | Android SDK tools and platform binaries |
| **Android AVD Home** | `D:\android-tools\.android\avd` | Storage path for Android Virtual Devices |
| **Android Emulator** | `D:\android-tools\android-sdk\emulator\emulator.exe` | Hardware-accelerated emulator binary |
| **ADB Executable** | `D:\android-tools\android-sdk\platform-tools\adb.exe` | Android Debug Bridge client |
| **Android Project** | `D:\edgerunner guardian frontend\android` | Jetpack Compose native application |
| **Debug APK Output** | `D:\edgerunner guardian frontend\android\app\build\outputs\apk\debug\app-debug.apk` | Compiled Android package |
| **Backend Launcher** | `D:\edgerunner guardian frontend\scripts\start_backend.ps1` | Automated environment setup and backend server |
| **Emulator Launcher**| `D:\edgerunner guardian frontend\scripts\start_emulator.ps1`| Automated AVD boot script with physical keyboard enabled |

---

## B. Environment Recovery & Port Conflict Resolution

### Root Cause of `[Errno 10048]` (Address Already in Use)
When starting the FastAPI backend on `0.0.0.0:8000`, attempting to bind to port 8000 fails with:
```
ERROR: [Errno 10048] error while attempting to bind on address ('0.0.0.0', 8000): only one usage of each socket address is normally permitted
```
This occurs when:
1. A previously launched Uvicorn/FastAPI process is still alive and listening on TCP port 8000.
2. Multiple terminal sessions or background task runners independently attempt to launch `start_backend.ps1` without checking port occupancy.
3. An orphaned Python worker process retains the socket lock.

### Safe Port Auditing & Recovery Procedure
Before restarting the backend, identify and clean up orphaned processes:
```powershell
# 1. Inspect processes listening on TCP port 8000
Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | Select-Object LocalAddress, LocalPort, OwningProcess, State

# 2. Inspect the owner PID (e.g., PID 17576)
Get-Process -Id (Get-NetTCPConnection -LocalPort 8000).OwningProcess | Select-Object Id, ProcessName, Path, StartTime

# 3. If unhealthy or orphaned, terminate the owning process cleanly:
Stop-Process -Id (Get-NetTCPConnection -LocalPort 8000).OwningProcess -Force

# 4. Verify the socket has been released:
Test-NetConnection -ComputerName 127.0.0.1 -Port 8000
```

---

## C. Backend Multi-Layer Scam Detection Architecture

The Guardian V2 detection pipeline employs four cooperating defense layers:

```
[ Incoming Call Segment / Message / Transcript ]
                     │
                     ▼
  ┌─────────────────────────────────────┐
  │ Layer 1: Fast Regex Rules Engine   │ ──(Critical Match)──► [ Immediate Safety Floor ]
  │  - OTP, Banking PIN, Remote APK     │                       (Score: 75 - 100)
  │  - Coercive Arrest, Digital Arrest  │
  └──────────────────┬──────────────────┘
                     │ (No Critical Rule)
                     ▼
  ┌─────────────────────────────────────┐
  │ Layer 2: ICFD Calibrated Classifier │ ──(Feature Embeddings)──► [ Empirical Risk Vector ]
  │  - TF-IDF + Calibrated Classifier   │
  └──────────────────┬──────────────────┘
                     │
                     ▼
  ┌─────────────────────────────────────┐
  │ Layer 3: Contextual Director        │ ──(Contextual Analysis)──► [ Intent & Urgency Scoring ]
  │  - Sarvam-105B / Fallback Classifier│
  └──────────────────┬──────────────────┘
                     │
                     ▼
  ┌─────────────────────────────────────┐
  │ Layer 4: Cross-Call State Engine    │ ──(Dampening / Cumulative)──► [ Final Risk Level ]
  │  - Call-isolated state buffers      │                              - CRITICAL (75-100)
  │  - Keyword dampening safeguards     │                              - WARNING (40-74)
  └─────────────────────────────────────┘                              - LOW (0-39)
```

### Deterministic Safety Overrides
- **OTP & Sensitive Credentials:** Any solicitation of one-time passwords, NetBanking passwords, or UPI credentials triggers an automatic floor of **100 (CRITICAL)**.
- **Remote Access Applications:** Solicitations to install remote screen-sharing tools (AnyDesk, TeamViewer, RustDesk) or third-party APKs enforce a strict safety override of **>= 75 (HIGH)**, preventing keyword dampening from suppressing high-risk attacks.
- **Law Enforcement & Digital Arrest:** Coercive demands claiming arrest warrants or customs confiscations enforce a minimum threshold of **>= 85 (CRITICAL)**.

---

## D. Telegram Bridge Architecture & Telephony Constraints

### Verified Capabilities
- **Bot Identity:** Integrated via official Telegram Bot API (`@EdgingToRunner_bot`, Target Chat: `7391483991`).
- **Text Message Ingestion:** Processes incoming private messages, runs scam risk analysis, replies to Telegram with structured alerts, and synchronizes with the Android application.
- **Voice Note Ingestion:** Downloads voice attachments (`.oga`, `.ogg`, `.mp3`), sends raw audio to Sarvam `saaras:v3` for speech-to-text transcription, evaluates transcripts through the scam engine, and alerts users.
- **Bot Commands:**
  - `/status` — Reports system readiness, STT provider, active rules, and call states.
  - `/latest` — Displays the most recent scam evaluation.
  - `/mute` — Mutes alerts for the active session.
  - `/help` — Lists operational bot capabilities.

### Telephony Boundaries: Messages vs. Live VoIP Calls
> [!IMPORTANT]
> The **Telegram Bot API cannot tap or record live 1-on-1 VoIP calls** due to end-to-end encryption and Bot API architectural constraints. 
> 
> - **Supported:** Text messages, forwarded scam chats, voice notes, and recorded audio files sent to the bot.
> - **Live Telephony Monitoring:** Monitoring live desktop or mobile VoIP calls requires either an MTProto client userbot (e.g. `py-tgcalls`) or local system audio loopback capture (Windows WASAPI / Android Accessibility Audio Capture).

---

## E. Android Virtual Device (AVD) & Physical Keyboard Configuration

### Verified AVD Profile
- **AVD Name:** `edgerunner_playstore`
- **Target OS:** Android 14.0 (Google APIs / Google Play Store x86_64)
- **Play Store Services:** Installed and verified (`com.android.vending`, `com.google.android.gms`).

### Enabling Laptop Physical Keyboard Input
In `D:\android-tools\.android\avd\edgerunner_playstore.avd\config.ini`:
```ini
hw.keyboard = yes
hw.keyboard.charmap = qwerty2
```
When launching the emulator:
```powershell
& "D:\android-tools\android-sdk\emulator\emulator.exe" -avd edgerunner_playstore -netdelay none -netspeed full
```
- Physical keyboard typing sends keycodes directly into focused `TextField` elements.
- On-screen virtual keyboard is suppressed during physical typing while remaining accessible when tapped.

---

## F. Android Native Client & Real-Time Sync

### Architecture
- **Language/Framework:** Kotlin, Jetpack Compose, Coroutines.
- **Network Pipeline:** 
  - Base URL: `http://10.0.2.2:8000` (emulator alias for host loopback).
  - WebSocket: `ws://10.0.2.2:8000/ws/app` for instantaneous event streaming.
  - Polling Fallback: Periodic background ticker (every 4 seconds) to ensure message history remains synchronized if WebSocket drops.
- **Event Handling:** Handles `AppEvent.MessageAnalyzed` to immediately refresh `_analyzedMessages` in `AppController`.
- **Recents Screen:** Categorized display of:
  - Phone calls (All calls vs. Only warnings).
  - Analyzed messages and Telegram transcripts with language badges, risk badges (LOW, HIGH, CRITICAL), and protective action recommendations.

---

## G. Step-by-Step Launch & Smoke Test Runbook

### Step 1: Start the Backend Service
Open PowerShell and run:
```powershell
Set-Location "D:\edgerunner guardian frontend"
.\scripts\start_backend.ps1
```
Verify the health endpoint:
```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/health"
```
Expected output:
```json
{
  "status": "ok",
  "working": true,
  "service": "AI Scam-Call Detection Backend",
  "stt_provider": "sarvam_saaras_v3",
  "rules_engine_rules_count": 10,
  "telegram_configured": true
}
```

### Step 2: Start the Android Emulator
```powershell
Set-Location "D:\edgerunner guardian frontend"
.\scripts\start_emulator.ps1
```
Verify device connection:
```powershell
& "D:\android-tools\android-sdk\platform-tools\adb.exe" devices
```

### Step 3: Build & Install Android Client
```powershell
Set-Location "D:\edgerunner guardian frontend\android"
.\gradlew.bat assembleDebug
& "D:\android-tools\android-sdk\platform-tools\adb.exe" install -r app\build\outputs\apk\debug\app-debug.apk
& "D:\android-tools\android-sdk\platform-tools\adb.exe" shell am start -n com.edgerunners.scamcheck/.MainActivity
```

### Step 4: Run Backend Test Suites
```powershell
Set-Location "D:\edgerunner guardian frontend\backend"
& ".\.venv\Scripts\python.exe" -m unittest tests/test_english_scam_detection.py
& ".\.venv\Scripts\python.exe" -m unittest tests/test_telegram_voice_and_messages.py
```

### Smoke Test Verification Checklist
- [x] Backend responds on `http://127.0.0.1:8000/health` with `status: ok`.
- [x] Emulator `edgerunner_playstore` boots with Google Play Store present.
- [x] Physical keyboard inputs letters, numbers, spaces, and punctuation into app text fields.
- [x] Remote access scam "Install this remote access application..." returns `HIGH (75%)`.
- [x] Bank account OTP demand returns `CRITICAL (100%)`.
- [x] Benign conversation "Hello, how are you today?" returns `LOW (0%)`.
- [x] Telegram incoming messages and voice transcripts populate the Android Recents screen in real time.
- [x] Git repository remote verified as `hackerwrath-3.0` (zero pushes to dogfood).
