# EdgeRunner Guardian: Comprehensive Multilingual & Anti-Spoofing Dataset Catalog

**Project:** EdgeRunner Guardian — Defensive AI-Powered Scam-Call Detection Platform  
**Target Operational Languages:** English, Hindi (Devanagari & Romanized/Hinglish), Punjabi (Gurmukhi & Romanized), and Regional Indian Languages  
**Evaluation Date:** October 24, 2026  
**Storage Drive Isolation:** D: Drive (`D:\edgerunner_datasets`, `D:\Dataset for EdgeRunners`, `D:\edgerunner_models`)  
**C: Drive Free Space Preserved:** 27.38 GB (> 5 GB mandatory safety margin)

---

## 1. Executive Summary & Selection Taxonomy

This catalog provides an empirical, evidence-grounded audit of candidate datasets for training, benchmarking, fine-tuning, and evaluating the multi-layered EdgeRunner Guardian defensive call security platform.

To prevent unconstrained disk bloat, network timeouts, and legal licensing liabilities, candidate datasets are evaluated under a strict taxonomy:
1. **Acquired & Active Benchmarks:** Ungated, fully audited datasets downloaded directly to `D:\edgerunner_datasets\raw`, normalized, and incorporated into `edgerunner_multilingual_corpus.jsonl` and test splits.
2. **Selective / Streaming Targets:** Massive speech or multimodal archives (e.g. 243 GB collections) designated for targeted shard streaming or transfer learning without full local mirror.
3. **Gated / Restricted Benchmarks:** Datasets requiring specific user agreement credentials or institutional application, documented with reproduction instructions.

---

## 2. Comprehensive Dataset Directory

### Domain A: Scam, Fraud Intent & Phishing Datasets

| Dataset Identifier | Canonical URL / Repo | Modality & Scope | Languages | Disk Scale | License | Access Status | Guardian Verdict |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Trilingual Fraud Consumer Protection v2** | [`karanverma19/trilingual_fraud_consumer_protection_v2`](https://huggingface.co/datasets/karanverma19/trilingual_fraud_consumer_protection_v2) | Text / Fraud Intent | English, Hindi, Punjabi | 0.03 MB (28.6 KB) | MIT | **Public / Ungated** | **Acquired (Gold Benchmark)**: High-precision intent coverage across all 3 primary project languages. |
| **Scam / Ham India 14 Languages** | [`anmolshrivastav/scam_ham_india_14_languages`](https://huggingface.co/datasets/anmolshrivastav/scam_ham_india_14_languages) | Text / SMS & Dialogues | 14 Indian languages (hi, ta, te, pa, ml, bn, mr, gu, kn, or, ur, as, en) | 3.34 MB (14,000 samples) | MIT | **Public / Ungated** | **Acquired (Multilingual held-out test)**: Balanced 50:50 distribution per language for cross-lingual zero-shot evaluation. |
| **Hinglish Scam Text Dataset** | [`bolewara/hinglish-scam-text-dataset`](https://huggingface.co/datasets/bolewara/hinglish-scam-text-dataset) | Text / Romanized Chat & Calls | Hinglish (Hindi in Latin script) | 0.45 MB (3,787 samples) | CC-BY-4.0 | **Public / Ungated** | **Acquired (Hinglish Corpus)**: Realistic UPI fraud, fake lottery, electricity cutoff, and KYC phishing lures. |
| **EdgeRunner Local Dialogue Corpus** | `D:\Dataset for EdgeRunners` (`Text_hindi`, `Text_english`) | Full multi-turn dialogues | Hindi, English | ~19 MB (18,974 dialogues) | Internal Research / Defensive | **Local Disk (D:)** | **Active**: 9,485 unique deduplicated dialogues partitioned into stratified 70/15/15 splits. |
| **INDICA Benchmark** | [`vikrant-vikram/INDICA`](https://huggingface.co/datasets/vikrant-vikram/INDICA) | Multilingual evaluation text | 10 Indic languages | 77.18 MB (`Text_samples.tar.gz`) | CC-BY-NC-4.0 | **Public / Ungated** | **Selective Validation**: Excellent for cross-lingual evaluation; non-commercial license requires separation from commercial deployments. |
| **ICFD-31k (Indian Call Fraud Dataset)** | [`rishia2220/icfd-31k`](https://huggingface.co/datasets/rishia2220/icfd-31k) | Call transcripts & metadata | Hindi, English, Hinglish | 0.02 MB manifest / ~31k records | Research Use | **Public / Ungated** | **Integrated via RAG**: Powers few-shot retrieval in `ICFDContextMatcher` and vector store. |
| **MultiFraudAlign** | [`ggirishg/MultiFraudAlign`](https://huggingface.co/datasets/ggirishg/MultiFraudAlign) | Cross-lingual aligned fraud dialogues | Hindi, English, Bengali | ~120 MB | Research Agreement | **Gated (HTTP 401)** | **Documented / Restricted**: Requires manual maintainer approval on Hugging Face; acquisition script prepared. |
| **Phishing Scam Detector Base** | [`Horizon-Labs/phishing-scam-detector-base`](https://huggingface.co/Horizon-Labs/phishing-scam-detector-base) | Model weights (DeBERTa-v3) | English | 499 MB | Apache 2.0 | **Public / Ungated** | **Evaluated as Tier-2 classifier**: High English precision but lacks Indian regional nuance compared to our fine-tuned RAG matcher. |

---

### Domain B: Voice Authenticity, Deepfake & Anti-Spoofing Datasets

| Dataset Identifier | Canonical URL / Resource | Modality & Scope | Scale | Acoustic Characteristics | License | Guardian Verdict |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **ASVspoof 2021 (Logical Access & Deepfake)** | [asvspoof.org](https://www.asvspoof.org/index2021.html) / [Zenodo](https://zenodo.org/record/4835108) | Audio (FLAC 16kHz) | ~7.8 GB (LA subset), ~14 GB (DF) | State-of-the-art vocoders (HiFi-GAN, WaveGrad, Tacotron2) vs bona fide human speakers | Open Research (EER benchmark) | **Reference Architecture Benchmark**: Acoustic criteria (high-frequency roll-off, spectral flatness, phase smearing) directly inform `VoiceAuthenticityDetector`. |
| **Audio Deepfake Detection Catalogue** | [`media-sec-lab/Audio-Deepfake-Detection`](https://github.com/media-sec-lab/Audio-Deepfake-Detection) | Comprehensive survey & dataset registry | Registry of 22 datasets | Multi-codec, telephony band-limiting (G.711/AMR), synthetic voice cloning | Open Access Catalog | **Taxonomy Source**: Grounding source for anti-spoofing feature engineering in live calls. |
| **MLAAD (Multi-Language Audio Anti-Spoofing)** | [`mueller91/MLAAD`](https://huggingface.co/datasets/mueller91/MLAAD) | Multilingual synthetic vs bona fide audio | Multi-GB (40+ languages) | Cross-lingual synthetic vocoder artifacts in non-English speech | Research Gated (HTTP 401) | **Selective Transfer Target**: Informs multilingual synthetic acoustic threshold tuning. |

---

### Domain C: Multilingual Speech Recognition & Conversational Speech

| Dataset Identifier | Canonical URL / Resource | Audio Scale | Languages | License | Access Status | Guardian Verdict |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **IndicVoices (AI4Bharat)** | [`ai4bharat/IndicVoices`](https://huggingface.co/datasets/ai4bharat/IndicVoices) | 7,300+ hours natural speech | 22 Indian languages, 145 districts | CC-BY-4.0 | **Gated (Auto click-through)** | **Core Baseline for Indic STT**: Extremely valuable for fine-tuning regional Punjabi/Hindi acoustic models. |
| **Vaani (IISc & ARTPARK / Google)** | [vaani.iisc.ac.in](https://vaani.iisc.ac.in/dataset) | 16,000+ hours across 80 districts | Indian dialects, conversational Hindi, Punjabi, South Indian languages | Open Data Initiative | **Public Web Download** | **Evaluation Target for Dialectal Robustness**: Spontaneous phone-quality speech across rural India. |
| **Hinglish Conversational Speech** | [`agarwalayushi/hinglish`](https://huggingface.co/datasets/agarwalayushi/hinglish) | **243.62 GB** (815,671 clips) | Hinglish code-switched conversational speech | Research Use | **Public / Ungated** | **DO NOT BULK DOWNLOAD (Storage Constraint)**: At 243 GB, a full download would exhaust D: drive. Evaluated via streaming audio samples only. |
| **Samvaad Hindi v1** | [`sarvamai/samvaad-hi-v1`](https://huggingface.co/datasets/sarvamai/samvaad-hi-v1) | 101,000 conversational turns | Clean conversational Hindi | Apache 2.0 | **Public / Ungated** | **Benign Baseline**: Ideal source of negative (ham) conversational examples to calibrate false positive rates. |

---

## 3. Storage & Integrity Audit of Acquired Data

All acquired assets reside exclusively on drive `D:` under `D:\edgerunner_datasets`:

```text
D:\edgerunner_datasets\
├── dataset_manifest.json          [SHA-256: Verified manifest of all 9,352 records]
├── raw\
│   ├── karanverma19__trilingual_fraud_consumer_protection_v2__trilingual_fraud_consumer_protection_v2.csv  (28.6 KB)
│   ├── anmolshrivastav__scam_ham_india_14_languages__scam_ham_india_14_languages.csv                      (3.49 MB)
│   └── bolewara__hinglish-scam-text-dataset__data.json                                                     (472.6 KB)
├── normalized\
│   └── edgerunner_multilingual_corpus.jsonl                                                                (6.03 MB, 9,352 records)
└── benchmarks\
    ├── train.jsonl                                                                                         (4.24 MB, 6,547 records)
    ├── val.jsonl                                                                                           (599.7 KB, 935 records)
    └── test.jsonl                                                                                          (1.19 MB, 1,870 records)
```

### Breakdown of Unified Benchmark Corpus:
- **Total Deduplicated Records:** 9,352
- **Real-World Conversational Records:** 8,152 (87.2%)
- **Synthetic / Dialogue Augmented Records:** 1,200 (12.8%)
- **Distribution by Target Language:**
  * Hinglish: 3,558 samples
  * Punjabi: 1,050 samples
  * Hindi: 1,650 samples (1,050 regional + 600 dialogue)
  * English: 659 samples (59 regional + 600 dialogue)
  * Regional Indian Languages (Marathi, Kannada, Odia, etc.): 2,435 samples
- **Binary Class Balance:** 3,511 SCAM (37.5%) vs 5,841 BENIGN (62.5%) — reflects real-world class imbalance where most phone calls are benign.
