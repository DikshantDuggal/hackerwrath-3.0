# EdgeRunner Guardian: Local Development & Windows Setup Guide

**Target Hardware:** ASUS TUF Gaming A16 (Windows 11 Home, AMD Ryzen Processor, 16 GB RAM)  
**Target Repository:** `D:\edgerunner guardian frontend`  
**Git Branch:** `backend/dikshant`  
**Storage Policy:** Zero unnecessary writes to `C:`. Strict isolation of all SDKs, AVDs, model caches, and build artifacts to `D:` drive to maintain at least 5–6 GB of free space on `C:`.

---

## 1. System & Architecture Overview

EdgeRunner Guardian consists of:
1. **FastAPI Backend (`backend/`):** Real-time conversational scam detection engine featuring dual-channel audio ingestion, ICFD-31k trained neural classification, RAG vector retrieval (Chroma / TF-IDF), and LiveKit calling lifecycle management.
2. **Android Application (`android/`):** Jetpack Compose modern mobile interface with incoming/outgoing LiveKit internet calling, two-channel audio streaming, and live scam warning dialogs.
3. **Storage Engine (`D:\` drive):** Caches, AVD virtual disks, HuggingFace weights, and HatchZip in-place archive utilities.

---

## 2. D: Drive Storage Isolation Matrix

To prevent `C:` disk exhaustion, configure your environment variables to point directly to `D:`:

```powershell
# Set permanently in Windows User Environment Variables:
[Environment]::SetEnvironmentVariable("ANDROID_HOME", "D:\android-tools\android-sdk", "User")
[Environment]::SetEnvironmentVariable("ANDROID_AVD_HOME", "D:\android-tools\.android\avd", "User")
[Environment]::SetEnvironmentVariable("GRADLE_USER_HOME", "D:\android-tools\.gradle", "User")
[Environment]::SetEnvironmentVariable("PIP_CACHE_DIR", "D:\pip_cache", "User")
[Environment]::SetEnvironmentVariable("EDGERUNNER_MODELS_DIR", "D:\edgerunner_models", "User")
[Environment]::SetEnvironmentVariable("HF_HOME", "D:\edgerunner_models\huggingface", "User")
[Environment]::SetEnvironmentVariable("TORCH_HOME", "D:\edgerunner_models\torch", "User")
```

| Component | Default Path (Avoided) | Isolated Path on D: | Purpose |
| :--- | :--- | :--- | :--- |
| **Android SDK** | `C:\Users\...\AppData\Local\Android\Sdk` | `D:\android-tools\android-sdk` | Platforms, build-tools, emulator |
| **Android AVD Disks**| `C:\Users\...\.android\avd` | `D:\android-tools\.android\avd` | Virtual device user data & system images (~6 GB) |
| **Gradle Cache** | `C:\Users\...\.gradle` | `D:\android-tools\.gradle` | Dependency jars, Kotlin daemons (~3 GB) |
| **Pip Cache** | `C:\Users\...\AppData\Local\pip\cache` | `D:\pip_cache` | Python wheel downloads |
| **Model Weights** | `C:\Users\...\.cache\huggingface` | `D:\edgerunner_models\huggingface` | MiniLM, BERT, Whisper models |
| **HatchZip Binary** | `C:\Users\...\AppData\Local\Programs` | `D:\edgerunner_tools\HatchZip` | In-place zero-overhead archive extractor |

---

## 3. Toolchain & Prerequisites

### 3.1 Java JDK 17
* **Location:** `D:\android-tools\jdk-17.0.20.1+1`
* **Verify:**
  ```powershell
  $env:JAVA_HOME = "D:\android-tools\jdk-17.0.20.1+1"
  & "$env:JAVA_HOME\bin\java.exe" -version
  # Output: openjdk version "17.0.20.1" 2026-07-21
  ```

### 3.2 Python 3.11 Runtime
* **Location:** `C:\Users\diksh\AppData\Local\Programs\Python\Python311\python.exe`
* **Verify:**
  ```powershell
  python --version
  # Output: Python 3.11.x
  ```

### 3.3 HatchZip (In-Place Extraction Utility)
* **Location:** `D:\edgerunner_tools\HatchZip\hatchzip.exe`
* **Verify:**
  ```powershell
  hatchzip --version
  # Output: hatchzip 0.1.2
  ```

---

## 4. One-Command Launch Workflow

EdgeRunner Guardian provides automated PowerShell scripts in `scripts/`:

### 4.1 Launch Everything (All-in-One)
```powershell
cd 'D:\edgerunner guardian frontend'
.\scripts\dev_runner.ps1 -Action all
```
* Spawns the FastAPI backend server in a background PowerShell window.
* Boots the Android Emulator with GPU acceleration.
* Configures ADB reverse port forwarding (`8000:8000`).
* Installs `app-debug.apk` and launches the application.

### 4.2 Start Backend Separately
```powershell
.\scripts\start_backend.ps1
```
* Binds to `0.0.0.0:8000`.
* Verifiable at `http://127.0.0.1:8000/health/ready` or `http://127.0.0.1:8000/docs`.

### 4.3 Start Emulator Separately
```powershell
.\scripts\start_emulator.ps1 -AvdName edgerunner_pixel
```

### 4.4 Run Health Check & Status
```powershell
.\scripts\dev_runner.ps1 -Action status
```

---

## 5. Android Emulator Networking & Communication

Android emulators execute inside a virtual network:
* Host `127.0.0.1` is reachable from inside the Android Emulator via `http://10.0.2.2:8000`.
* The Android application `build.gradle.kts` defaults `API_BASE_URL` to `http://10.0.2.2:8000`.
* In addition, `scripts/start_emulator.ps1` runs:
  ```powershell
  adb reverse tcp:8000 tcp:8000
  ```
  This enables localhost parity so requests to `http://localhost:8000` from the device also resolve cleanly to the Windows backend.

---

## 6. Running the Automated Test Suite

### 6.1 Backend Tests (93 Tests, 100% Passing)
```powershell
cd 'D:\edgerunner guardian frontend\backend'
python -m unittest discover -s tests -p "test_*.py"
```
**Test Coverage Includes:**
* `test_backend.py`: Core FastAPI endpoints, health checks, risk scoring.
* `test_context_aware_detection.py`: Multi-turn conversational threat progression.
* `test_icfd_integration.py`: Multilingual ICFD-31k fraud classifier and threshold calibration.
* `test_livekit_calling.py`: LiveKit calling lifecycle (`/calls/start`, `/calls/{id}/accept`, `/calls/{id}/end`, deterministic JWT tokens, scam detection worker).
* `test_rag_classifier.py` & `test_rag_retrieval.py`: Semantic retrieval over Indian financial scam corpus.
* `test_stale_transcripts_and_duplicates.py`: Deduplication engine and protective advice dampening.

### 6.2 Android Application Build
```powershell
cd 'D:\edgerunner guardian frontend\android'
$env:GRADLE_USER_HOME = "D:\android-tools\.gradle"
$env:JAVA_HOME = "D:\android-tools\jdk-17.0.20.1+1"
.\gradlew.bat assembleDebug
```
* Generates: `android/app/build/outputs/apk/debug/app-debug.apk` (~117 MB).

---

## 7. Troubleshooting

| Issue | Cause | Fix |
| :--- | :--- | :--- |
| **App reports "Couldn't reach server"** | Backend not running or wrong IP | Ensure backend is running (`.\scripts\start_backend.ps1`). Emulator must access `http://10.0.2.2:8000`. |
| **`adb devices` shows offline** | Emulator still initializing | Wait for `sys.boot_completed=1` or run `adb kill-server && adb start-server`. |
| **C: drive low space warning** | Caches defaulting to C: | Verify `$env:ANDROID_AVD_HOME` and `$env:GRADLE_USER_HOME` point to `D:\android-tools`. |
| **Port 8000 in use** | Stray uvicorn or python process | Run `Get-Process python \| Stop-Process -Force` in PowerShell. |
