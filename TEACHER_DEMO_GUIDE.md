# HackerWrath 3.0 (Edgerunners ScamCheck) — Teacher Presentation & Execution Guide

This document contains every exact path, terminal command, browser URL, and a scripted 5-minute live demonstration flow to present the project to your teacher.

---

## 1. Project Directory & Core File Paths

| Component | Absolute File Path | Description |
| :--- | :--- | :--- |
| **Project Root** | `C:\Users\diksh\.gemini\antigravity\scratch\hackerwrath-3.0` | Main Git repository root |
| **Unified Web Preview** | `C:\Users\diksh\.gemini\antigravity\scratch\hackerwrath-3.0\preview.html` | Source for the full Android + Web unified interface |
| **Backend Directory** | `C:\Users\diksh\.gemini\antigravity\scratch\hackerwrath-3.0\backend` | FastAPI server, RAG pipeline, ML models & test suite |
| **FastAPI Entrypoint** | `C:\Users\diksh\.gemini\antigravity\scratch\hackerwrath-3.0\backend\app\main.py` | FastAPI application factory, routing & static file mounts |
| **RAG Scam Engine** | `C:\Users\diksh\.gemini\antigravity\scratch\hackerwrath-3.0\backend\app\rag\service.py` | Semantic vector search, MiniLM embedding & classifier |
| **RAG Vector Store** | `C:\Users\diksh\.gemini\antigravity\scratch\hackerwrath-3.0\backend\vector_store\index_metadata.jsonl` | 2,841 reference phone fraud dialogues & metadata |
| **Native Android Source** | `C:\Users\diksh\.gemini\antigravity\scratch\hackerwrath-3.0\android` | Jetpack Compose native Android implementation |
| **Android Tab Specs** | `C:\Users\diksh\.gemini\antigravity\scratch\hackerwrath-3.0\android\app\src\main\java\com\edgerunners\scamcheck\ui\spell\TabsScreen.kt` | Native Android Compose bottom navigation & wipe effects |
| **Android Guardian Code** | `C:\Users\diksh\.gemini\antigravity\scratch\hackerwrath-3.0\android\app\src\main\java\com\edgerunners\scamcheck\ui\spell\Guardian.kt` | Native trigonometric guardian morphing canvas equations |
| **Backend Test Suite** | `C:\Users\diksh\.gemini\antigravity\scratch\hackerwrath-3.0\backend\tests` | 60 automated unit tests (RAG, live ingest, rules, calls) |

---

## 2. Browser URLs to Show Your Teacher

| Interface / URL | What It Displays | What to Highlight |
| :--- | :--- | :--- |
| **`http://127.0.0.1:8000/preview.html`** | **Unified Android + Web Application** | **The main showcase:** 3 Android tabs, live RAG vector search sandbox, audio chimes, guardian dispatch, and call simulation. |
| **`http://127.0.0.1:8000/docs`** | **FastAPI Swagger / OpenAPI Documentation** | Interactive REST API testing for `/rag/analyze`, `/rag/health`, `/analyze/transcript`, and `/calls`. |
| **`http://127.0.0.1:8000/rag/health`** | **RAG Model Health JSON** | Shows embedding model (`all-MiniLM-L6-v2`) and 2,841 indexed documents. |
| **`http://localhost:5173/`** | **React Vite Frontend (Optional)** | Secondary desktop web dashboard. |

---

## 3. How to Start Everything (If Not Already Running)

> [!NOTE]
> The backend server is **already currently running** in the background on port `8000`. You can simply open `http://127.0.0.1:8000/preview.html` in your browser right now!

If you ever restart your computer or need to launch from scratch, open **PowerShell** and run:

### Terminal 1: Start Backend & RAG Server
```powershell
cd C:\Users\diksh\.gemini\antigravity\scratch\hackerwrath-3.0\backend
$env:HF_HOME = "D:\huggingface_cache"
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### Terminal 2: Run All 60 Unit Tests (Show Teacher Code Quality)
```powershell
cd C:\Users\diksh\.gemini\antigravity\scratch\hackerwrath-3.0\backend
$env:HF_HOME = "D:\huggingface_cache"
python -m unittest discover tests
```
*(Expected output: `Ran 60 tests in 23.355s — OK`)*

---

## 4. Scripted 5-Minute Teacher Presentation Flow

Follow this step-by-step walkthrough during your presentation:

### Step 1: Open the Unified Web Experience
1. Open Chrome/Edge to: **`http://127.0.0.1:8000/preview.html`**.
2. **What to say to your teacher:**
   > *"This is HackerWrath 3.0 (Edgerunners ScamCheck). It is an on-device, real-time scam prevention application designed to protect vulnerable individuals and families from telecom fraud. The frontend integrates the native Android Jetpack Compose interface with our live AI/RAG backend."*

### Step 2: Show the Android 3-Tab Architecture
1. Click the **Home**, **Recents**, and **Contacts** tabs in the floating bottom navigation bar.
2. Note the smooth sliding liquid pill indicator.
3. On the **Home Tab**:
   - Point to the **Organic Guardian Blob**: explain that it morphs organically between 9 lobes (listening) and 12 lobes (scam detected). Click `Toggle View` to show the Nordic landscape illustration.
   - Switch language between **English**, **हिन्दी**, and **ਪੰਜਾਬੀ** to show full localization.
   - Click the **I'm expecting a payment** switch to show dynamic scam context sensitivity.
4. On the **Recents Tab**:
   - Click **Warnings only** vs **All calls** to show filterable call timelines.
   - Expand the first call card to show the detected scam trigger (*"Asked to scan QR code on PhonePe"*) and the automated safety action.
5. On the **Contacts & Guardian Tab**:
   - Show the pinned **Your Circle** defense cards: **Mum** (Lookout) and **Arjun** (Brother).
   - Click on Mum to open the **Your Circle Defense Modal** and click **Test Alert Dispatch** — it plays a real synthesized alert chime and simulates sending an emergency SMS to Mum with the caller details.

### Step 3: Run a Live Scam Simulation
1. On the Home tab under **Demo call simulation**, click **QR Scan**.
2. Watch the call flow unfold:
   - **Incoming screen:** caller appears with ripple ring animation and on-device protection pill.
   - Click **Answer**.
   - **In-Call screen:** duration ticks, audio visualizer animates, and the live speech transcript stream updates in real-time.
   - **Detection:** at 2.5s status turns Amber (*Checking…*), and at 4.5s the high-contrast **High Risk Alert Sheet** slides up.
   - The browser synthesizes dual-tone alert chimes (880Hz $\rightarrow$ 660Hz) and speaks the voice warning aloud (*"Warning: never scan any QR code or enter your UPI PIN to receive money"*).
   - An emergency dispatch is sent to Mum.
   - Click **End call immediately** to complete the defense flow.

### Step 4: Show the Live RAG Semantic Vector Analyzer Sandbox
1. Direct your teacher's attention to the right-hand **Inspector Panel**.
2. Point out the **Live RAG Vector Search & Scam Classifier**:
   - Click the preset **UPI QR Scam** and click **Analyze**.
   - Show the result: **SCAM**, Risk Score **95/100**, Confidence, and **Retrieved Vector Citations** with Cosine Similarity percentages against the 2,841 reference dialogues.
   - Click the preset **Safe Delivery** and click **Analyze** — show that it correctly classifies it as **LEGITIMATE** with a low risk score.
   - Show the sub-30ms latency benchmark.

### Step 5: Show the Theme Toggle
1. Click the palette icon or **Toggle Edition** in the app bar.
2. Demonstrate the switch between **Standard Nordic Editorial** (warm paper `#F4F1EA`, editorial blue `#226192`) and **Premium Obsidian Cyberpunk HUD** (deep void `#0E1014`, gold `#C18D17`).

### Step 6: Show Backend Tests & API Docs
1. Switch to the tab: **`http://127.0.0.1:8000/docs`** to show the complete FastAPI OpenAPI schema.
2. In your terminal, run `python -m unittest discover tests` and show that **all 60 automated tests pass** without errors.
