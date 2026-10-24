# EdgeRunner Guardian: Data Acquisition, Ingestion, and Storage Guide

**Target Environment:** Windows 11 (ASUS TUF A16)  
**Dedicated Storage Path:** `D:\edgerunner_datasets` and `D:\edgerunner_models`  
**Storage Rule:** Mandatory preservation of C: drive space (> 5 GB free). No downloads, checkpoints, or pip caches on C:.

---

## 1. Pre-Flight Storage & Environment Verification

Before downloading any dataset or model asset, execute the automated pre-flight storage check:

```powershell
# In PowerShell:
Set-Location "D:\edgerunner guardian frontend\backend"
.\.venv\Scripts\python.exe -c "from app.services.dataset_pipeline import DatasetPipeline; DatasetPipeline.check_disk_space(min_c_gb=5.0, min_d_gb=2.0); print('Storage verification passed.')"
```

If free space on `C:` drops below 5.0 GB or `D:` below 2.0 GB, execution is halted immediately.

### Pip & Hugging Face Cache Redirection:
Always configure pip and Hugging Face cache directories to point exclusively to `D:`:
```powershell
$env:PIP_CACHE_DIR = "D:\pip_cache"
$env:HF_HOME = "D:\edgerunner_datasets\hf_cache"
$env:TRANSFORMERS_CACHE = "D:\edgerunner_datasets\hf_cache\transformers"
$env:UV_CACHE_DIR = "D:\pip_cache\uv"
```

---

## 2. Automated Acquisition & Ingestion Pipeline

The unified pipeline in `backend/app/services/dataset_pipeline.py` acquires, verifies, and normalizes all ungated benchmarks into standard JSONL format with zero manual steps:

```powershell
Set-Location "D:\edgerunner guardian frontend\backend"
.\.venv\Scripts\python.exe -m app.services.dataset_pipeline
```

### What this script does:
1. Downloads `karanverma19/trilingual_fraud_consumer_protection_v2` (`trilingual_fraud_consumer_protection_v2.csv`).
2. Downloads `anmolshrivastav/scam_ham_india_14_languages` (`scam_ham_india_14_languages.csv`).
3. Downloads `bolewara/hinglish-scam-text-dataset` (`data.json`).
4. Ingests local stratified dialogue files from `D:\Dataset for EdgeRunners\Text_hindi` and `Text_english`.
5. Computes MD5 text hashes for cross-dataset deduplication.
6. Maps all records to canonical schema:
   ```json
   {
     "id": "scam_ham_14lang_00123",
     "source_dataset": "anmolshrivastav/scam_ham_india_14_languages",
     "text": "बधाई हो! आपने ₹50,000 का पुरस्कार जीता है। दावा करने के लिए लिंक पर क्लिक करें।",
     "language": "hindi",
     "label": "SCAM",
     "category": "INDIAN_REGIONAL_SMS_OR_CALL",
     "is_synthetic": false,
     "metadata": { "row_index": 123, "raw_label": "scam" }
   }
   ```
7. Generates reproducible 70/15/15 train/val/test splits in `D:\edgerunner_datasets\benchmarks\`.
8. Generates cryptographic SHA-256 manifest in `D:\edgerunner_datasets\dataset_manifest.json`.

---

## 3. Cryptographic Verification & Checksums

| Acquired Raw File | Path on Disk | Size | SHA-256 Hash |
| :--- | :--- | :--- | :--- |
| **Punjab Trilingual CSV** | `D:\edgerunner_datasets\raw\karanverma19...csv` | 28,654 bytes | `1cc2ccb829753e1cb0fc373bb2b406fa71ca6c93da539423c4a2df856671a81e` |
| **Scam / Ham 14-Lang CSV** | `D:\edgerunner_datasets\raw\anmolshrivastav...csv` | 3,497,601 bytes | `50b633a3a17b3a9a1036f0141b714b21eebdfd7beea92d529f796bf4749f7b60` |
| **Hinglish Scam JSON** | `D:\edgerunner_datasets\raw\bolewara...json` | 472,689 bytes | `4c2ea6d6c93060c41da36dae858db112bf8e29a39ca2197623192f1539e6a39d` |
| **Unified Corpus JSONL** | `D:\edgerunner_datasets\normalized\edgerunner_multilingual_corpus.jsonl` | 6,037,136 bytes | `b3798ca9d5a6a85c6d1aa95eda4b24f5068362fd5b5dc9eb4f04daf30a14ea5c` |
| **Held-Out Test Split** | `D:\edgerunner_datasets\benchmarks\test.jsonl` | 1,195,778 bytes | `cff4ca7ccc4f519b6a63f6aaefd022360610011d7e9127064f167d1052965805` |

To verify any file locally:
```powershell
Get-FileHash -Algorithm SHA256 "D:\edgerunner_datasets\dataset_manifest.json"
```

---

## 4. Handling Gated Hugging Face Datasets

For restricted datasets such as `ggirishg/MultiFraudAlign`, `mueller91/MLAAD`, or `ai4bharat/IndicVoices`:

### Step 1: Request Access via Browser
1. Log into your Hugging Face account at https://huggingface.co.
2. Visit the repository page:
   - https://huggingface.co/datasets/ggirishg/MultiFraudAlign
   - https://huggingface.co/datasets/ai4bharat/IndicVoices
   - https://huggingface.co/datasets/mueller91/MLAAD
3. Accept the user conditions / license terms.

### Step 2: Set Access Token in Environment
```powershell
$env:HF_TOKEN = "hf_your_actual_token_here"
```

### Step 3: Streamed Download with Isolated Cache
```python
from datasets import load_dataset
import os

# Ensure cache is on D:
os.environ["HF_HOME"] = "D:/edgerunner_datasets/hf_cache"

# Load via streaming (avoids downloading entire multi-gigabyte dataset upfront)
ds = load_dataset("ai4bharat/IndicVoices", "punjabi", split="train", streaming=True, token=os.environ["HF_TOKEN"])
sample = next(iter(ds))
print("Sample audio duration:", sample["audio"]["sampling_rate"])
```

---

## 5. Streaming Strategy for Massive Datasets (243 GB agarwalayushi/hinglish)

**CRITICAL WARNING:** Do not attempt `git clone` or full `load_dataset` on `agarwalayushi/hinglish`. The repository contains 815,671 audio clips totaling **243.62 GB**, which would saturate available disk capacity.

### Safe Selective Shard Streaming Workflow:
```python
from datasets import load_dataset
import soundfile as sf
from pathlib import Path

out_dir = Path("D:/edgerunner_datasets/audio_subsets/hinglish_eval")
out_dir.mkdir(parents=True, exist_ok=True)

# Stream first 200 clips only for acoustic evaluation
ds = load_dataset("agarwalayushi/hinglish", split="train", streaming=True)
for idx, item in enumerate(ds):
    if idx >= 200:
        break
    audio_arr = item["audio"]["array"]
    sr = item["audio"]["sampling_rate"]
    sf.write(out_dir / f"hinglish_{idx:04d}.wav", audio_arr, sr)

print("Downloaded 200 representative clips (scale: ~15 MB).")
```

---

## 6. Safe Cleanup & Asset Management

To purge temporary download artifacts without removing normalized benchmarks:
```powershell
# Safely remove pip download cache if space is needed:
Remove-Item -Recurse -Force "D:\pip_cache\*" -ErrorAction SilentlyContinue

# Verify disk headroom remains intact:
Get-PSDrive -PSProvider FileSystem | Select-Object Name, Free, Used
```
