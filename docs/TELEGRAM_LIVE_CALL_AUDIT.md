# EdgeRunners — Telegram Live Call Hearing Mode Audit & Architecture

**Date:** October 2026  
**Platform:** Windows 11 (Python 3.11.9, Node.js v24.20.0)  
**Workspace:** `C:\Users\diksh\.gemini\antigravity\scratch\hackerwrath-3.0`  
**Git Branch:** `backend/dikshant`  

---

## 1. Executive Summary & Verification Findings

A complete non-destructive audit of the EdgeRunners repository, the external Telegram bridge (`ashboi005/onfloor/tree/main/apps/telegram-bridge`), local environment, datasets, models, and test suites was conducted.

### Core Discoveries:
1. **Telegram Bridge (`onfloor/apps/telegram-bridge`) Reality:**
   - The external bridge uses `py-tgcalls 3.0.0` and `pyrogram` over MTProto.
   - It requires interactive authentication with `TELEGRAM_API_ID`, `TELEGRAM_API_HASH`, and a user session string.
   - **Critical Limitation:** The bridge is designed to **act as the client** and answer calls on a dedicated user account. It **cannot tap or monitor an active one-on-one call** taking place on Telegram Desktop with a friend.
   - On Windows, `pytgcalls` and `pyrogram` are not installed in the system Python environment.
2. **Current Audio Path in Hearing Mode:**
   - In `backend/src/components/LiveVoiceTester.tsx`, audio capture uses browser `navigator.mediaDevices.getUserMedia()`.
   - This captures **only the local microphone**.
   - Remote participant audio routed by Telegram Desktop to the PC speakers or headphones is **not captured**.
3. **RAG & Baseline Model State:**
   - Multilingual datasets (37,948 samples across Hindi and English) are prepared with dialogue-grouped stratification in `backend/data/`.
   - The TF-IDF + Logistic Regression baseline model (`backend/vector_store/tfidf_logistic_baseline.joblib`) is trained and achieved 100% validation accuracy with sub-2ms latency.
   - Persistent vector store (`backend/vector_store/index_embeddings.npz`) has 2,841 indexed documents.
   - **Key Pipeline Gap:** Live audio ingestion (`LiveAudioSession` -> `ConversationManager`) was calling only `RulesEngine` and `ContextualAnalyzer`; `RAGScamClassifier` was omitted from the live loop.
4. **Active Credentials:**
   - `SARVAM_API_KEY`: Configured and verified (`saaras:v3`).
   - `TELEGRAM_BOT_TOKEN`: Configured and verified (`@EdgingToRunner_bot`, Chat ID `7391483991`).
5. **System Storage Constraint:**
   - Drive `C:` has **<200 MB free**.
   - Drive `D:` has **81.4 GB free**.
   - All caches (`HF_HOME`, `PIP_CACHE_DIR`) must reside on `D:`.

---

## 2. Component-by-Component Status Audit

| # | Component | Status | Source References | Verification Details |
|---|---|---|---|---|
| **1** | Telegram Bridge (Personal Call Audio) | **BLOCKED BY EXTERNAL REQUIREMENT** | `app/api/routes_live_ingest.py`, external `bridge.py` | `py-tgcalls` cannot hook into Telegram Desktop calls. Requires dedicated MTProto account and answers calls directly. |
| **2** | Local Mic & Remote Audio Capture | **PARTIALLY IMPLEMENTED** | `src/components/LiveVoiceTester.tsx`, `app/services/live_audio_processor.py` | Local mic captures at 16kHz via browser `getUserMedia`. Remote caller audio has no capture adapter (needs WASAPI loopback). |
| **3** | Sarvam AI STT Integration | **VERIFIED WORKING** (Unit/Offline) | `app/services/transcription_service.py`, `app/core/config.py` | `saaras:v3` integration loaded. Offline simulation passed. Validated with live API key in `.env`. |
| **4** | Multilingual Dataset Preparation | **VERIFIED WORKING** | `scripts/prepare_multilingual_dataset.py`, `data/` | 13,277 train, 2,841 val, 2,849 test records generated with dialogue grouping to prevent cross-lingual leakage. |
| **5** | Trained Baseline Classifier | **VERIFIED WORKING** | `scripts/train_baseline.py`, `vector_store/tfidf_logistic_baseline.joblib` | 25k feature TF-IDF + Logistic Regression. 100% accuracy on validation set, ~1.1ms latency. |
| **6** | Persistent RAG Index & Embeddings | **PARTIALLY IMPLEMENTED** | `app/rag/retriever.py`, `vector_store/index_embeddings.npz` | 2,841 docs indexed in NumPy cosine index (<2ms lookup). Full 13,277 train set index pending. Model is English-only (`all-MiniLM-L6-v2`). |
| **7** | Live Transcript RAG Integration | **IMPLEMENTED (WIRED)** | `app/services/conversation_manager.py`, `app/services/risk_scorer.py` | Wired `RAGService` into `ConversationManager.process_segment` to enrich live risk scores with semantic retrieval. |
| **8** | Dynamic Scam-Risk Scoring | **VERIFIED WORKING** | `app/services/risk_scorer.py`, `app/services/rules_engine.py` | 0–100 scale, LOW/MEDIUM/HIGH/CRITICAL/UNKNOWN levels. Protective advice damping and keyword sync active. |
| **9** | FastAPI Endpoints & WebSockets | **VERIFIED WORKING** | `app/main.py`, `app/api/routes_live_ingest.py` | REST routes and WebSockets (`/browser-stream`, `/internal/live/ingest`, `/events`) tested under Uvicorn. |
| **10** | Hearing Mode Frontend | **IMPLEMENTED BUT NOT VERIFIED** (Live Call) | `src/components/LiveVoiceTester.tsx`, `src/components/RiskDisplay.tsx` | Dark obsidian/purple UI, audio level meter, progressive captions, Telegram badge. |
| **11** | Telegram Bot Alerts | **VERIFIED WORKING** | `app/services/telegram_service.py`, `app/api/routes_telegram.py` | PII scrubbing, 180s incident deduplication, escalation overrides. Connected to `@EdgingToRunner_bot`. |
| **12** | Session Lifecycle & Privacy | **VERIFIED WORKING** | `app/repositories/conversation_repository.py` | 3600s TTL auto-purging, bounded async queues, in-memory transient audio processing. |
| **13** | Automated Test Suite | **VERIFIED WORKING** | `backend/tests/` | **53/53 tests pass** across RAG, STT, Telegram, Ingest, and Scorer. |

---

## 3. Dependency Chain for Telegram Call Monitoring

```text
[Telegram Call on Windows Desktop]
               │
   ┌───────────┴───────────┐
   ▼                       ▼
Local Microphone     Remote Output
(Browser UserMedia)  (WASAPI Loopback)
   └───────────┬───────────┘
               ▼
WebSocket Ingestion (/internal/live/browser-stream)
               │ (16kHz PCM16LE mono chunks)
               ▼
LiveAudioSession (Bounded Queue + Pause Detection)
               │ (48,000-byte slice in memory WAV)
               ▼
Sarvam Saaras STT (saaras:v3)
               │ (Transcribed Text + Timestamps)
               ▼
ConversationManager (Session Context & TTL State)
   ├── RulesEngine (Devanagari Hindi + English Regex & Negation)
   ├── ContextualAnalyzer (Semantic Intent & Urgency Heuristics)
   └── RAGService (TF-IDF Baseline + Vector Store Cosine Similarity)
               │
               ▼
RiskScorer (Composite 0-100 Score, Risk Level & Recommendations)
   ├── DashboardBroadcaster -> WebSocket (/internal/live/events) -> Hearing Mode UI
   └── TelegramAlertService -> Telegram Bot (@EdgingToRunner_bot) [if High/Critical]
```

---

## 4. Test Suite Execution Results

Ran full backend test suite (`python -m unittest discover -s tests -p "test_*.py"`):
- `test_backend.py`: **31 passed**
- `test_rag_api.py`: **5 passed**
- `test_rag_classifier.py`: **5 passed**
- `test_rag_preprocessing.py`: **6 passed**
- `test_rag_retrieval.py`: **6 passed**
- **Total: 53 tests passed in 27.8s (0 failures, 0 errors).**
