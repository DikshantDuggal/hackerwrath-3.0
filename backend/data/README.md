# Scam & Fraud Dialogue Dataset (English)

This directory contains the cleaned, deduplicated, and stratified English phone-scam and anti-fraud dialogue dataset prepared for the RAG retrieval and classification engine.

## 1. Source Data

- **Origin**: `D:\Dataset for EdgeRunners\Text_english`
- **Corpus**: `TeleAntiFraud-28k` (multilingual/English phone fraud dialogues)
- **Raw Files Discovered**: 18,974 text documents (`11,978 legit` / `6,996 scam`)

## 2. Data Cleaning & Deduplication

- **Exact Duplicates Removed**: 9,492 exact duplicate records (approx. 50% duplicate rate caused by audio TTS naming variants)
- **Cross-Label Conflicts**: 0 (zero identical dialogues under contradictory labels)
- **Canonical Unique Records**: 9,482
  - **SCAM**: 3,493 (36.8%)
  - **LEGITIMATE**: 5,989 (63.2%)

## 3. Dataset Partitions (Stratified 70 / 15 / 15 Split, Random Seed = 42)

| File | Partition | Total Records | SCAM Records | LEGIT Records | Purpose |
| :--- | :--- | :---: | :---: | :---: | :--- |
| `cleaned_dataset.jsonl` | Full Corpus | 9,482 | 3,493 | 5,989 | Master deduplicated dataset |
| `train.jsonl` | Train / Reference | 6,637 | 2,445 | 4,192 | Populates persistent vector index & TF-IDF baseline |
| `val.jsonl` | Validation | 1,421 | 523 | 898 | Hyperparameter tuning & threshold validation |
| `test.jsonl` | Test (Isolated) | 1,424 | 525 | 899 | Held-out benchmark evaluation |

## 4. Record Schema

Each line in the `.jsonl` files follows this structure:

```json
{
  "example_id": "ex_00001",
  "text": "Speaker1: Hello, this is Agricultural and Commercial Bank...\nSpeaker2: Yes, what is this regarding?",
  "label": "SCAM",
  "source": "TeleAntiFraud-28k",
  "word_count": 142
}
```

## 5. Preprocessing & Quality Assurance

- **Normalization**: Unicode NFKC, LF newlines, intra-line whitespace collapsing.
- **Dialogue Preservation**: Speaker turns (`Speaker1:`, `Speaker2:`) and natural pauses are preserved.
- **PII Protection**: Raw credit cards and 10+ digit mobile numbers are detected and sanitized.
- **Audit Report**: See [`data_quality_report.json`](./data_quality_report.json) for distribution metrics.
