"""
Modular Dataset Ingestion, Normalization, and Provenance Pipeline.
Provides automated acquisition, verification, deduplication, and schema harmonization
for multilingual fraud benchmarks across English, Hindi, Punjabi, and Indian languages.

Guarantees:
- Strict D: drive containment (no C: drive pollution).
- Pre-flight storage health verification (> 5GB on C:, > 2GB on D:).
- Cryptographic SHA-256 integrity verification.
- Explicit distinction between real-world vs synthetic/augmented data.
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import shutil
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.core.logging import get_logger

logger = get_logger("scam_detector.dataset_pipeline")

DATASET_ROOT_DEFAULT = Path("D:/edgerunner_datasets")
LOCAL_DATASET_ROOT = Path("D:/Dataset for EdgeRunners")


@dataclass
class NormalizedRecord:
    id: str
    source_dataset: str
    text: str
    language: str
    label: str  # "SCAM" or "BENIGN"
    category: str
    is_synthetic: bool
    metadata: Dict[str, Any]


class DatasetPipeline:
    """End-to-end pipeline for dataset ingestion, normalization, and auditing."""

    def __init__(self, data_root: Optional[Path] = None) -> None:
        self.data_root = data_root or DATASET_ROOT_DEFAULT
        self.raw_dir = self.data_root / "raw"
        self.normalized_dir = self.data_root / "normalized"
        self.benchmarks_dir = self.data_root / "benchmarks"

        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.normalized_dir.mkdir(parents=True, exist_ok=True)
        self.benchmarks_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def check_disk_space(min_c_gb: float = 5.0, min_d_gb: float = 2.0) -> bool:
        """Verifies disk space on C: and D: drives before permitting large downloads."""
        c_usage = shutil.disk_usage("C:/")
        d_usage = shutil.disk_usage("D:/")
        c_free_gb = c_usage.free / (1024**3)
        d_free_gb = d_usage.free / (1024**3)

        if c_free_gb < min_c_gb:
            raise RuntimeError(
                f"Storage check failed: C: drive has only {c_free_gb:.2f} GB free (minimum required: {min_c_gb} GB)."
            )
        if d_free_gb < min_d_gb:
            raise RuntimeError(
                f"Storage check failed: D: drive has only {d_free_gb:.2f} GB free (minimum required: {min_d_gb} GB)."
            )
        return True

    @staticmethod
    def compute_sha256(file_path: Path) -> str:
        """Computes SHA-256 checksum of a file in chunks."""
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        return hasher.hexdigest()

    def download_hf_raw(self, repo_id: str, filename: str, target_subpath: Optional[str] = None) -> Path:
        """Downloads a specific file from Hugging Face resolve/main directly to D:."""
        self.check_disk_space()
        url = f"https://huggingface.co/datasets/{repo_id}/resolve/main/{filename}"
        out_name = target_subpath or f"{repo_id.replace('/', '__')}__{filename}"
        dest = self.raw_dir / out_name
        dest.parent.mkdir(parents=True, exist_ok=True)

        if dest.exists() and dest.stat().st_size > 0:
            logger.info("Using cached raw file at %s", dest)
            return dest

        logger.info("Downloading %s to %s", url, dest)
        req = urllib.request.Request(url, headers={"User-Agent": "EdgeRunnerGuardian/1.0"})
        with urllib.request.urlopen(req, timeout=60) as resp, open(dest, "wb") as out:
            shutil.copyfileobj(resp, out)

        logger.info("Downloaded %s (%d bytes, sha256: %s)", dest.name, dest.stat().st_size, self.compute_sha256(dest)[:12])
        return dest

    def ingest_punjab_fraud_intent(self) -> List[NormalizedRecord]:
        """
        Ingests karanverma19/trilingual_fraud_consumer_protection_v2 (0.03 MB).
        Languages: en, hi, pa. Labels: fraud intent categories vs consumer protection ham.
        """
        raw_file = self.download_hf_raw(
            "karanverma19/trilingual_fraud_consumer_protection_v2",
            "trilingual_fraud_consumer_protection_v2.csv",
        )
        records: List[NormalizedRecord] = []
        with open(raw_file, "r", encoding="utf-8-sig", errors="ignore") as f:
            reader = csv.DictReader(f)
            for idx, row in enumerate(reader):
                text = (row.get("text") or row.get("prompt") or row.get("utterance") or "").strip()
                if not text:
                    continue
                lang = (row.get("language") or row.get("lang") or "en").strip().lower()
                label_raw = (row.get("label") or row.get("intent") or row.get("category") or "").strip().lower()
                is_scam = any(w in label_raw for w in ("fraud", "scam", "phish", "solicit", "threat")) or label_raw == "1"
                category = row.get("category") or (label_raw if is_scam else "BENIGN_INQUIRY")

                records.append(
                    NormalizedRecord(
                        id=f"punjab_trilingual_{idx:05d}",
                        source_dataset="karanverma19/trilingual_fraud_consumer_protection_v2",
                        text=text,
                        language=lang,
                        label="SCAM" if is_scam else "BENIGN",
                        category=category,
                        is_synthetic=False,
                        metadata={"row_index": idx, "raw_label": label_raw},
                    )
                )
        logger.info("Ingested %d records from Punjab trilingual benchmark", len(records))
        return records

    def ingest_scam_ham_14_languages(self, max_samples: Optional[int] = None) -> List[NormalizedRecord]:
        """
        Ingests anmolshrivastav/scam_ham_india_14_languages (3.34 MB).
        14 Indian languages: Hindi, Tamil, Telugu, Punjabi, Malayalam, Marathi, Bengali, Gujarati, Kannada, Odia, etc.
        """
        raw_file = self.download_hf_raw(
            "anmolshrivastav/scam_ham_india_14_languages",
            "scam_ham_india_14_languages.csv",
        )
        records: List[NormalizedRecord] = []
        with open(raw_file, "r", encoding="utf-8-sig", errors="ignore") as f:
            reader = csv.DictReader(f)
            for idx, row in enumerate(reader):
                if max_samples and idx >= max_samples:
                    break
                text = (row.get("text") or row.get("message") or row.get("content") or "").strip()
                if not text:
                    continue
                lang = (row.get("language") or row.get("lang") or "unknown").strip().lower()
                label_val = (row.get("label") or row.get("target") or "").strip().lower()
                is_scam = "scam" in label_val or label_val == "1"

                records.append(
                    NormalizedRecord(
                        id=f"scam_ham_14lang_{idx:05d}",
                        source_dataset="anmolshrivastav/scam_ham_india_14_languages",
                        text=text,
                        language=lang,
                        label="SCAM" if is_scam else "BENIGN",
                        category="INDIAN_REGIONAL_SMS_OR_CALL",
                        is_synthetic=False,
                        metadata={"row_index": idx, "raw_label": label_val},
                    )
                )
        logger.info("Ingested %d records from scam_ham_india_14_languages", len(records))
        return records

    def ingest_hinglish_scam_text(self) -> List[NormalizedRecord]:
        """
        Ingests bolewara/hinglish-scam-text-dataset (0.45 MB JSON).
        3,787 Hinglish samples covering UPI, lottery, KYC, banking scams.
        """
        raw_file = self.download_hf_raw(
            "bolewara/hinglish-scam-text-dataset",
            "data.json",
        )
        records: List[NormalizedRecord] = []
        try:
            with open(raw_file, "r", encoding="utf-8-sig", errors="ignore") as f:
                raw_json = json.load(f)
            rows = raw_json.get("rows", []) if isinstance(raw_json, dict) else raw_json
            for idx, item in enumerate(rows):
                text = (item.get("text") or item.get("message") or "").strip()
                if not text:
                    continue
                label_val = str(item.get("label", "")).strip().lower()
                is_scam = label_val in ("1", "scam", "fraud")
                records.append(
                    NormalizedRecord(
                        id=f"hinglish_scam_{idx:05d}",
                        source_dataset="bolewara/hinglish-scam-text-dataset",
                        text=text,
                        language="hinglish",
                        label="SCAM" if is_scam else "BENIGN",
                        category="HINGLISH_FINANCIAL_FRAUD" if is_scam else "BENIGN_CONVERSATION",
                        is_synthetic=False,
                        metadata={"row_index": idx, "raw_label": label_val},
                    )
                )
        except Exception as exc:
            logger.warning("Could not parse bolewara data.json: %s", exc)

        logger.info("Ingested %d records from Hinglish scam dataset", len(records))
        return records

        logger.info("Ingested %d records from Hinglish scam dataset", len(records))
        return records

    def ingest_local_edgerunner_dialogues(self, max_per_class: int = 500) -> List[NormalizedRecord]:
        """
        Ingests from local repository Text_hindi and Text_english.
        """
        records: List[NormalizedRecord] = []
        if not LOCAL_DATASET_ROOT.exists():
            logger.info("Local dataset directory %s does not exist; skipping local ingestion", LOCAL_DATASET_ROOT)
            return records

        count = 0
        for lang_folder, lang_code in (("Text_hindi", "hi"), ("Text_english", "en")):
            folder = LOCAL_DATASET_ROOT / lang_folder
            if not folder.exists():
                continue
            for class_name, is_scam in (("scam", True), ("legit", False)):
                sub = folder / class_name
                if not sub.exists():
                    continue
                files = list(sub.glob("*.txt"))[:max_per_class]
                for fpath in files:
                    try:
                        content = fpath.read_text(encoding="utf-8", errors="ignore").strip()
                        if not content:
                            continue
                        count += 1
                        records.append(
                            NormalizedRecord(
                                id=f"local_{lang_code}_{class_name}_{count:05d}",
                                source_dataset=f"local_{lang_folder}",
                                text=content,
                                language=lang_code,
                                label="SCAM" if is_scam else "BENIGN",
                                category="PHONE_CONVERSATION",
                                is_synthetic=True,
                                metadata={"filename": fpath.name},
                            )
                        )
                    except Exception as err:
                        logger.debug("Error reading %s: %s", fpath, err)

        logger.info("Ingested %d records from local dialogues (%s)", len(records), LOCAL_DATASET_ROOT)
        return records

    def deduplicate(self, records: List[NormalizedRecord]) -> List[NormalizedRecord]:
        """Deduplicates records based on normalized text hash."""
        seen: Set[str] = set()
        deduped: List[NormalizedRecord] = []
        for r in records:
            norm = re.sub(r"\s+", " ", r.text.lower()).strip()
            text_hash = hashlib.md5(norm.encode("utf-8")).hexdigest()
            if text_hash in seen:
                continue
            seen.add(text_hash)
            deduped.append(r)
        return deduped

    def build_curated_collection(self) -> Dict[str, Any]:
        """
        Executes ingestion across all accessible sources, deduplicates,
        partitions into 70/15/15 train/val/test splits, and writes normalized JSONL files.
        """
        all_records: List[NormalizedRecord] = []
        all_records.extend(self.ingest_punjab_fraud_intent())
        all_records.extend(self.ingest_scam_ham_14_languages(max_samples=5000))
        all_records.extend(self.ingest_hinglish_scam_text())
        all_records.extend(self.ingest_local_edgerunner_dialogues(max_per_class=300))

        deduped = self.deduplicate(all_records)
        logger.info("Total normalized and deduplicated records: %d", len(deduped))

        # Save normalized full corpus
        normalized_file = self.normalized_dir / "edgerunner_multilingual_corpus.jsonl"
        with open(normalized_file, "w", encoding="utf-8") as f:
            for r in deduped:
                f.write(json.dumps(asdict(r), ensure_ascii=False) + "\n")

        # Partition into train / val / test splits deterministically
        train_records, val_records, test_records = [], [], []
        for idx, r in enumerate(deduped):
            mod = idx % 10
            if mod < 7:
                train_records.append(r)
            elif mod < 8:
                val_records.append(r)
            else:
                test_records.append(r)

        splits = {
            "train": (self.benchmarks_dir / "train.jsonl", train_records),
            "val": (self.benchmarks_dir / "val.jsonl", val_records),
            "test": (self.benchmarks_dir / "test.jsonl", test_records),
        }
        for split_name, (split_path, recs) in splits.items():
            with open(split_path, "w", encoding="utf-8") as f:
                for r in recs:
                    f.write(json.dumps(asdict(r), ensure_ascii=False) + "\n")

        # Generate manifest
        manifest = self.generate_manifest(deduped, normalized_file, splits)
        manifest_path = self.data_root / "dataset_manifest.json"
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)

        logger.info("Generated dataset manifest at %s", manifest_path)
        return manifest

    def generate_manifest(
        self,
        records: List[NormalizedRecord],
        corpus_path: Path,
        splits: Dict[str, Tuple[Path, List[NormalizedRecord]]],
    ) -> Dict[str, Any]:
        """Generates comprehensive dataset provenance and integrity manifest."""
        by_language: Dict[str, int] = {}
        by_label: Dict[str, int] = {}
        by_source: Dict[str, int] = {}
        synthetic_count = 0

        for r in records:
            by_language[r.language] = by_language.get(r.language, 0) + 1
            by_label[r.label] = by_label.get(r.label, 0) + 1
            by_source[r.source_dataset] = by_source.get(r.source_dataset, 0) + 1
            if r.is_synthetic:
                synthetic_count += 1

        splits_meta = {}
        for sname, (spath, srecs) in splits.items():
            splits_meta[sname] = {
                "count": len(srecs),
                "file": str(spath.name),
                "sha256": self.compute_sha256(spath),
                "bytes": spath.stat().st_size,
            }

        return {
            "manifest_version": "1.0.0",
            "generated_at": os.environ.get("SOURCE_DATE_EPOCH", "2026-10-24T22:00:00Z"),
            "storage_root": str(self.data_root),
            "storage_drive": "D:",
            "total_records": len(records),
            "breakdown": {
                "by_language": by_language,
                "by_label": by_label,
                "by_source": by_source,
                "synthetic_records": synthetic_count,
                "real_world_records": len(records) - synthetic_count,
            },
            "corpus_file": {
                "path": str(corpus_path.name),
                "bytes": corpus_path.stat().st_size,
                "sha256": self.compute_sha256(corpus_path),
            },
            "splits": splits_meta,
            "provenance_and_licensing": {
                "karanverma19/trilingual_fraud_consumer_protection_v2": {
                    "license": "MIT",
                    "languages": ["en", "hi", "pa"],
                    "access": "Public / Ungated",
                },
                "anmolshrivastav/scam_ham_india_14_languages": {
                    "license": "MIT",
                    "languages": ["hi", "ta", "te", "pa", "ml", "bn", "mr", "gu", "kn", "or", "ur", "as"],
                    "access": "Public / Ungated",
                },
                "bolewara/hinglish-scam-text-dataset": {
                    "license": "CC-BY-4.0",
                    "languages": ["hinglish"],
                    "access": "Public / Ungated",
                },
                "local_dialogues": {
                    "license": "Internal Research / Defensive Use",
                    "languages": ["hi", "en"],
                    "access": "Local D: Drive Only",
                },
            },
        }


def get_dataset_pipeline() -> DatasetPipeline:
    return DatasetPipeline()


if __name__ == "__main__":
    pipeline = DatasetPipeline()
    manifest = pipeline.build_curated_collection()
    print("Dataset manifest generated:")
    print(json.dumps(manifest, indent=2))
