# EdgeRunner Guardian: Database Architecture & Disk-Efficient Storage Decision

**Project:** EdgeRunner Guardian (Multilingual AI Scam Call Detection)  
**Author:** EdgeRunner Engineering Team  
**Date:** October 2026  
**Status:** Approved & Implemented  
**Target Platform:** Android (Client) + FastAPI (Backend) + LiveKit Cloud/Self-Hosted (Calling)  
**Host Environment:** Windows 11 (ASUS TUF A16) — Primary Development Drive `D:`

---

## 1. Executive Summary

EdgeRunner Guardian processes real-time conversational audio in English, Hindi, and Punjabi to identify financial fraud, credential harvesting, impersonation, and coercive scams. The application operates across two distinct operational boundaries:
1. **The Android Mobile Client:** Low-latency UI, incoming call management, local consent auditing, and user alert displays.
2. **The FastAPI Backend Service:** Real-time dual-channel audio ingestion, STT streaming, multi-stage RAG retrieval, ICFD-31k neural classification, and audit logging.

Because the host development machine (ASUS TUF A16) has constrained space on the Windows OS drive (`C:`) with a strict requirement to keep at least 5–6 GB free, this architecture formalizes:
* A **dual-tier database architecture** (Room/SQLite on Android + In-Memory/SQLite/PostgreSQL on Backend).
* A **disk-efficient asset and model storage strategy** integrating the in-place archive extraction principles of [HatchZip](https://github.com/xevrion/hatchzip) to eliminate 2× disk bloat when unpacking multi-gigabyte models and datasets.
* Strict storage isolation confining Android SDKs, AVD emulators, Gradle caches, PyTorch/HuggingFace checkpoints, and vector stores to the high-capacity `D:` drive.

---

## 2. Client-Side Database Architecture (Android)

### 2.1 Technology Selection: Android Room (SQLite)

For the Android client, **Android Jetpack Room** (built atop SQLite) is selected over raw SQLite and Key-Value stores (DataStore/SharedPreferences) for structured data.

| Technology | Latency | Schema Typing | Complex Queries | Offline Support | Verdict |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Android Room (SQLite)** | < 3 ms | Compile-time verified | Full SQL & joins | Full offline support | **Selected (Primary)** |
| **Jetpack DataStore** | < 1 ms | Protobuf / Typed | No (Key-value only) | Yes | **Selected for Preferences only** |
| **Raw SQLiteOpenHelper** | < 3 ms | Runtime string queries | Manual cursor mapping | Yes | **Rejected (Error-prone)** |
| **ObjectBox / Realm** | < 2 ms | Object mapping | Proprietary query API | Yes | **Rejected (Heavy native bin)** |

### 2.2 Client-Side Data Entities

The Android local database maintains the following entities:

1. **`calls` table**:
   * `id` (UUID string, Primary Key)
   * `caller_number` / `caller_name` (Encrypted / Masked)
   * `call_type` (INCOMING, OUTGOING, LIVEKIT_INTERNET)
   * `started_at`, `ended_at` (Epoch timestamps)
   * `overall_risk_level` (SAFE, SUSPICIOUS, HIGH_RISK)
   * `highest_risk_score` (Float 0.0 - 100.0)
   * `consent_granted` (Boolean)

2. **`call_transcripts` table**:
   * `id` (UUID, Primary Key)
   * `call_id` (Foreign Key -> `calls.id` ON DELETE CASCADE)
   * `channel` (0 = Local Caller, 1 = Remote Party)
   * `speaker_label` (e.g., "Remote", "You")
   * `text` (Transcribed text segment)
   * `language` (en, hi, pa)
   * `timestamp_ms` (Offset in milliseconds)
   * `is_scam_trigger` (Boolean)

3. **`scam_alerts` table**:
   * `id` (UUID, Primary Key)
   * `call_id` (Foreign Key -> `calls.id`)
   * `timestamp` (Epoch timestamp)
   * `risk_level` (SUSPICIOUS, HIGH_RISK)
   * `caption` (Short explanation, e.g. "OTP Solicitation Detected")
   * `explanation` (User-facing plain-language warning)
   * `suggested_action` (HANG_UP, VERIFY_OFFICIALLY, MUTE)

---

## 3. Server-Side Database Architecture (Backend)

### 3.1 Technology Selection & Dual-Mode Strategy

The backend requires high-throughput real-time state tracking during active calls, combined with persistent audit trails. To ensure seamless developer onboarding without requiring Docker or cloud infrastructure, the backend implements a **pluggable repository pattern** (`ConversationRepository`):

```
                   +----------------------------------+
                   |      ConversationRepository      |
                   |      (Abstract Base Class)       |
                   +----------------------------------+
                                     |
             +-----------------------+-----------------------+
             |                                               |
+--------------------------+                    +--------------------------+
| InMemoryConversationRepo |                    |  PostgreSQL / Supabase   |
| (Zero-overhead local dev |                    | (Production Audit & Team |
|  & CI unit test runner)  |                    |  Multi-tenant Compliance)|
+--------------------------+                    +--------------------------+
```

| Criterion | In-Memory (Current Local) | SQLite (File-backed) | PostgreSQL (Production) | Redis (Real-Time Cache) |
| :--- | :--- | :--- | :--- | :--- |
| **Setup Overhead** | Zero (Zero external deps) | Zero (Single `.db` file) | Medium (Docker / Managed) | Low/Medium (Daemon) |
| **Throughput** | > 100,000 ops/sec | ~ 15,000 ops/sec | ~ 8,000 ops/sec | > 80,000 ops/sec |
| **ACID Guarantees** | Process lifetime only | Full local ACID | Full distributed ACID | In-memory persistence |
| **Retention Policy** | Automatic TTL in-memory | Periodic cron / vacuum | Declarative TTL / Timescale | Native key EXPIRE |
| **Target Role** | **Local Dev & Unit Tests** | **Offline Desktop/Edge** | **Production Core Database** | **Real-time Call State Cache** |

### 3.2 Production Relational Schema (PostgreSQL DDL)

```sql
-- EdgeRunner Guardian Core Relational Schema (PostgreSQL 15+)

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    phone_hash VARCHAR(64) UNIQUE NOT NULL, -- SHA-256 of E.164 phone number
    display_name VARCHAR(100),
    preferred_language VARCHAR(10) DEFAULT 'hi',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS calls (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    room_name VARCHAR(128) UNIQUE NOT NULL,
    caller_id UUID REFERENCES users(id) ON DELETE SET NULL,
    recipient_id UUID REFERENCES users(id) ON DELETE SET NULL,
    call_status VARCHAR(32) NOT NULL DEFAULT 'ACTIVE', -- ACTIVE, COMPLETED, REJECTED
    max_risk_score DOUBLE PRECISION DEFAULT 0.0,
    max_risk_level VARCHAR(20) DEFAULT 'LOW', -- LOW, SUSPICIOUS, HIGH
    started_at TIMESTAMPTZ DEFAULT NOW(),
    ended_at TIMESTAMPTZ,
    end_reason VARCHAR(64)
);

CREATE TABLE IF NOT EXISTS call_segments (
    id BIGSERIAL PRIMARY KEY,
    call_id UUID NOT NULL REFERENCES calls(id) ON DELETE CASCADE,
    speaker_channel INT NOT NULL, -- 0 = Caller, 1 = Recipient
    transcript TEXT NOT NULL,
    cleaned_transcript TEXT,
    language VARCHAR(10) DEFAULT 'en',
    start_time_offset_ms INT NOT NULL,
    end_time_offset_ms INT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS scam_assessments (
    id BIGSERIAL PRIMARY KEY,
    call_id UUID NOT NULL REFERENCES calls(id) ON DELETE CASCADE,
    segment_id BIGINT REFERENCES call_segments(id) ON DELETE SET NULL,
    risk_score DOUBLE PRECISION NOT NULL,
    risk_level VARCHAR(20) NOT NULL,
    caption TEXT NOT NULL,
    explanation TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS triggered_indicators (
    id BIGSERIAL PRIMARY KEY,
    assessment_id BIGINT NOT NULL REFERENCES scam_assessments(id) ON DELETE CASCADE,
    rule_id VARCHAR(64) NOT NULL,
    category VARCHAR(64) NOT NULL,
    keyword_or_pattern VARCHAR(128) NOT NULL,
    weight DOUBLE PRECISION NOT NULL,
    excerpt TEXT NOT NULL
);

-- Indices for sub-millisecond query performance
CREATE INDEX IF NOT EXISTS idx_calls_room_name ON calls(room_name);
CREATE INDEX IF NOT EXISTS idx_call_segments_call_id ON call_segments(call_id);
CREATE INDEX IF NOT EXISTS idx_scam_assessments_call_id ON scam_assessments(call_id);
```

---

## 4. Large Model & Dataset Storage Strategy (HatchZip Integration)

### 4.1 The 2× Storage Overhead Problem

When deploying speech transcription models (Whisper), multilingual embedding checkpoints (`sentence-transformers/all-MiniLM-L6-v2`), and large tabular datasets (ICFD-31k corpus):
1. An archive file (e.g. `icfd_dataset.zip`, 2.5 GB) is downloaded to disk.
2. Standard extraction tools (`unzip`, Python's `zipfile`) require space for the archive **plus** space for the extracted files simultaneously.
3. This creates a **peak disk requirement of 2× the asset size (5.0 GB)** before the source archive can be safely deleted.
4. On systems with constrained space (such as keeping `C:` free by 5–6 GB), unpacking multiple archives frequently triggers OS out-of-disk errors.

### 4.2 HatchZip Analysis (`https://github.com/xevrion/hatchzip`)

[HatchZip](https://github.com/xevrion/hatchzip) is a specialized open-source utility designed specifically to eliminate this 2× overhead:
* **Mechanism:** It processes the archive from the **tail (end) towards the head (start)**. As each batch of files is extracted and validated, it truncates the archive file in-place using standard OS filesystem APIs.
* **Peak Space Reduction:** The peak disk consumption is reduced from `Archive Size + Unpacked Size` to approximately `Archive Size + Size of Largest Single File Chunk`.
* **Filesystem Independence:** Unlike sparse-file hole-punching which fails on FAT/exFAT, file truncation works reliably across NTFS, ext4, APFS, and exFAT.
* **Crash Resilience:** It employs transactional journaling with CRC-32 checks. If interrupted mid-extraction, it safely resumes without corrupting previously extracted files.

### 4.3 Implementation in EdgeRunner Guardian: `AssetManager`

We implemented `backend/app/services/asset_manager.py` with the following production architecture:

```
[Remote Model / Dataset Archive]
              |
              v
    Stream Download to D:\edgerunner_models\temp
              |
              v
    SHA-256 Checksum Verification
              |
              +----> Is 'hatchzip' installed?
                     |
                     +-- YES --> Run 'hatchzip unpack' (In-place tail truncation, 0 extra disk bloat)
                     |
                     +-- NO  --> Stream zipfile extract + Atomic directory promotion (.partial -> active)
              |
              v
    Final Asset Activation in D:\edgerunner_models
```

### 4.4 Environment Redirection Matrix (Conserving C: Drive Space)

To guarantee that no machine learning cache or build artifact pollutes `C:`, the following paths are configured:

| Subsystem | Default Windows Path (C:) | EdgeRunner Redirected Path (D:) | Environment Variable / Flag |
| :--- | :--- | :--- | :--- |
| **Android SDK Root** | `C:\Users\<user>\AppData\Local\Android\Sdk` | `D:\android-tools\android-sdk` | `ANDROID_HOME`, `ANDROID_SDK_ROOT` |
| **Android AVD Storage** | `C:\Users\<user>\.android\avd` | `D:\android-tools\.android\avd` | `ANDROID_AVD_HOME` |
| **Gradle Cache & Daemons**| `C:\Users\<user>\.gradle` | `D:\android-tools\.gradle` | `GRADLE_USER_HOME` |
| **Python Pip Cache** | `C:\Users\<user>\AppData\Local\pip\cache`| `D:\pip_cache` | `PIP_CACHE_DIR` |
| **HuggingFace Hub Cache**| `C:\Users\<user>\.cache\huggingface` | `D:\edgerunner_models\huggingface` | `HF_HOME`, `TRANSFORMERS_CACHE` |
| **PyTorch Weights Cache**| `C:\Users\<user>\.cache\torch` | `D:\edgerunner_models\torch` | `TORCH_HOME` |
| **RAG Vector Store** | In-repo `backend/vector_store` | `D:\edgerunner guardian frontend\backend\vector_store` | `RAG_VECTOR_STORE_DIR` |

---

## 5. Data Privacy, Redaction & DPDP Act Compliance

Under India's **Digital Personal Data Protection Act (DPDP Act 2023)** and telecom regulatory directives:
1. **PII Masking:**
   * Transcripts never persist plain-text OTPs, CVVs, or 12-digit Aadhaar numbers. The backend `sensitive_info_detector.py` automatically redacts these patterns to `[REDACTED_OTP]` and `[REDACTED_CREDENTIAL]`.
2. **Short-Term Retention (TTL):**
   * Active call conversation states in memory or database are retained for exactly `call_state_retention_seconds` (default: 300 seconds / 5 minutes after call termination).
   * Raw audio frames fed into LiveKit workers are processed in-memory as PCM chunks and discarded immediately after transcription; raw audio is **never written to disk**.
3. **Informed Consent:**
   * Both participants receive visual and audio indications that automated scam detection is active. Users may opt out at any time.

---

## 6. Migration & Setup Verification Guide

1. **Verify Asset Manager:**
   ```powershell
   cd 'D:\edgerunner guardian frontend\backend'
   python -c "from app.services.asset_manager import get_asset_manager; am = get_asset_manager(); print(am.get_asset_status())"
   ```
2. **Install HatchZip (Optional but recommended for large archive extraction):**
   ```powershell
   irm https://raw.githubusercontent.com/xevrion/hatchzip/main/install.ps1 | iex
   ```
3. **Database Migration to PostgreSQL (When scaling beyond local in-memory):**
   * Set `DATABASE_URL=postgresql://user:pass@localhost:5432/edgerunner` in `.env`.
   * Run initial Alembic migrations: `alembic upgrade head`.
