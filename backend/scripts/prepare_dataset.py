"""
Script to inspect, clean, deduplicate, and stratify the English Scam/Legit dataset.
Supports TeleAntiFraud-28k dialogue format (Text_english/legit and Text_english/scam).

Output files generated:
- data/cleaned_dataset.jsonl  (All deduplicated canonical records)
- data/train.jsonl            (70% Stratified training / reference index)
- data/val.jsonl              (15% Stratified validation set)
- data/test.jsonl             (15% Stratified test set, isolated for final evaluation)
- data/data_quality_report.json (Comprehensive audit report)
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import random
import re
import unicodedata
from collections import Counter
from typing import Any, Dict, List, Tuple


def normalize_text(text: str) -> str:
    """
    Normalizes encoding and whitespace while strictly preserving conversational wording,
    punctuation, numbers, and speaker turn markers (e.g., 'Speaker1:', 'Speaker2:').
    """
    if not text:
        return ""
    # Unicode NFKC normalization
    text = unicodedata.normalize("NFKC", text)
    # Replace non-breaking spaces and tabs with standard space
    text = text.replace("\xa0", " ").replace("\t", " ")
    # Normalize CRLF to LF
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Collapse 3+ newlines into 2
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Normalize intra-line spaces (preserve newlines)
    lines = [re.sub(r"[ ]+", " ", line).strip() for line in text.split("\n")]
    # Strip empty leading/trailing lines
    cleaned = "\n".join(lines).strip()
    return cleaned


def detect_pii(text: str) -> Dict[str, int]:
    """Scans for potential personally identifiable numbers and credentials."""
    phones = len(re.findall(r"\b(?:\+?\d{1,3}[- ]?)?[6-9]\d{9}\b", text))
    accounts = len(re.findall(r"\b\d{12,19}\b", text))
    otps = len(re.findall(r"(?i)\b(?:otp|one[- ]time password|verification code|pin code)\b", text))
    amounts = len(re.findall(r"(?i)(?:₹|\$|rs\.?|inr|usd|dollars?|rupees?)\s*\d+[\d,]*", text))
    return {
        "phone_patterns": phones,
        "account_patterns": accounts,
        "otp_credential_patterns": otps,
        "monetary_amount_patterns": amounts,
    }


def load_raw_dataset(data_dir: str) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Loads all files from legit and scam subdirectories."""
    legit_dir = os.path.join(data_dir, "legit")
    scam_dir = os.path.join(data_dir, "scam")

    if not os.path.isdir(legit_dir) or not os.path.isdir(scam_dir):
        raise FileNotFoundError(
            f"Expected 'legit' and 'scam' subdirectories in '{data_dir}'. Found: {os.listdir(data_dir)}"
        )

    legit_files = glob.glob(os.path.join(legit_dir, "*.txt"))
    scam_files = glob.glob(os.path.join(scam_dir, "*.txt"))

    print(f"Discovered {len(legit_files)} files in 'legit/' and {len(scam_files)} files in 'scam/'.")

    raw_records: List[Dict[str, Any]] = []
    empty_records = 0

    for filepath in legit_files:
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read().strip()
            if not content:
                empty_records += 1
                continue
            raw_records.append({
                "raw_id": os.path.splitext(os.path.basename(filepath))[0],
                "raw_text": content,
                "raw_label": "legit",
                "normalized_label": "LEGITIMATE",
                "filepath": filepath,
            })
        except Exception as e:
            print(f"Warning: Failed to read {filepath}: {e}")

    for filepath in scam_files:
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read().strip()
            if not content:
                empty_records += 1
                continue
            raw_records.append({
                "raw_id": os.path.splitext(os.path.basename(filepath))[0],
                "raw_text": content,
                "raw_label": "scam",
                "normalized_label": "SCAM",
                "filepath": filepath,
            })
        except Exception as e:
            print(f"Warning: Failed to read {filepath}: {e}")

    stats = {
        "total_files_discovered": len(legit_files) + len(scam_files),
        "legit_files": len(legit_files),
        "scam_files": len(scam_files),
        "empty_files": empty_records,
    }
    return raw_records, stats


def clean_and_deduplicate(raw_records: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Cleans text, groups exact and near-duplicates, and extracts canonical examples.
    """
    canonical_map: Dict[str, Dict[str, Any]] = {}
    duplicate_count = 0
    cross_label_conflicts = 0

    for idx, rec in enumerate(raw_records):
        cleaned_text = normalize_text(rec["raw_text"])
        label = rec["normalized_label"]

        # Fingerprint: normalized lower-case without whitespace variation
        fingerprint = hashlib.sha256(cleaned_text.lower().encode("utf-8")).hexdigest()

        if fingerprint in canonical_map:
            duplicate_count += 1
            existing = canonical_map[fingerprint]
            existing["duplicate_count"] += 1
            existing["source_files"].append(rec["raw_id"])
            if existing["label"] != label:
                cross_label_conflicts += 1
                print(f"Conflict: text appears under both labels! (ID: {rec['raw_id']})")
        else:
            words = cleaned_text.split()
            pii_info = detect_pii(cleaned_text)
            canonical_map[fingerprint] = {
                "example_id": f"ex_{len(canonical_map) + 1:05d}",
                "text": cleaned_text,
                "label": label,
                "source": "TeleAntiFraud-28k",
                "word_count": len(words),
                "fingerprint": fingerprint,
                "duplicate_count": 1,
                "source_files": [rec["raw_id"]],
                "pii_signals": pii_info,
            }

    canonical_records = list(canonical_map.values())

    dedup_stats = {
        "raw_record_count": len(raw_records),
        "canonical_record_count": len(canonical_records),
        "duplicate_records_removed": duplicate_count,
        "cross_label_conflicts": cross_label_conflicts,
        "scam_canonical_count": sum(1 for r in canonical_records if r["label"] == "SCAM"),
        "legit_canonical_count": sum(1 for r in canonical_records if r["label"] == "LEGITIMATE"),
    }
    return canonical_records, dedup_stats


def stratified_split(
    records: List[Dict[str, Any]],
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
    test_ratio: float = 0.15,
    seed: int = 42,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Performs deterministic stratified split on canonical records by label.
    """
    rng = random.Random(seed)

    scam_records = [r for r in records if r["label"] == "SCAM"]
    legit_records = [r for r in records if r["label"] == "LEGITIMATE"]

    rng.shuffle(scam_records)
    rng.shuffle(legit_records)

    def split_group(group: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
        n = len(group)
        n_train = int(n * train_ratio)
        n_val = int(n * val_ratio)
        train = group[:n_train]
        val = group[n_train : n_train + n_val]
        test = group[n_train + n_val :]
        return train, val, test

    scam_train, scam_val, scam_test = split_group(scam_records)
    legit_train, legit_val, legit_test = split_group(legit_records)

    train = scam_train + legit_train
    val = scam_val + legit_val
    test = scam_test + legit_test

    rng.shuffle(train)
    rng.shuffle(val)
    rng.shuffle(test)

    return train, val, test


def save_jsonl(records: List[Dict[str, Any]], filepath: str) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        for r in records:
            # Save core required fields: example_id, text, label, source, word_count
            payload = {
                "example_id": r["example_id"],
                "text": r["text"],
                "label": r["label"],
                "source": r.get("source", "TeleAntiFraud-28k"),
                "word_count": r["word_count"],
            }
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Clean, deduplicate, and stratify scam call dataset.")
    parser.add_argument("--data-dir", default=r"D:\Dataset for EdgeRunners\Text_english", help="Input dataset path")
    parser.add_argument("--output-dir", default=os.path.join(os.path.dirname(__file__), "..", "data"), help="Output data directory")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    args = parser.parse_args()

    data_dir = os.path.abspath(args.data_dir)
    output_dir = os.path.abspath(args.output_dir)
    os.makedirs(output_dir, exist_ok=True)

    print(f"=== PHASE 1 & 2: DATASET INSPECTION & PREPARATION ===")
    print(f"Reading from: {data_dir}")
    print(f"Writing to:   {output_dir}")

    # 1. Load raw files
    raw_records, raw_stats = load_raw_dataset(data_dir)

    # 2. Clean & Deduplicate
    canonical_records, dedup_stats = clean_and_deduplicate(raw_records)

    # 3. Compute word statistics
    scam_words = [r["word_count"] for r in canonical_records if r["label"] == "SCAM"]
    legit_words = [r["word_count"] for r in canonical_records if r["label"] == "LEGITIMATE"]

    def calc_stats(wlist: List[int]) -> Dict[str, Any]:
        if not wlist:
            return {"min": 0, "max": 0, "mean": 0.0}
        return {
            "min": min(wlist),
            "max": max(wlist),
            "mean": round(sum(wlist) / len(wlist), 1),
        }

    # 4. Stratified Split (70/15/15)
    train_set, val_set, test_set = stratified_split(canonical_records, seed=args.seed)

    # 5. Save Partition Files
    cleaned_path = os.path.join(output_dir, "cleaned_dataset.jsonl")
    train_path = os.path.join(output_dir, "train.jsonl")
    val_path = os.path.join(output_dir, "val.jsonl")
    test_path = os.path.join(output_dir, "test.jsonl")

    save_jsonl(canonical_records, cleaned_path)
    save_jsonl(train_set, train_path)
    save_jsonl(val_set, val_path)
    save_jsonl(test_set, test_path)

    # 6. Generate Data Quality Report
    report = {
        "raw_dataset_statistics": raw_stats,
        "deduplication_summary": dedup_stats,
        "word_count_distribution": {
            "scam": calc_stats(scam_words),
            "legitimate": calc_stats(legit_words),
            "overall": calc_stats([r["word_count"] for r in canonical_records]),
        },
        "stratified_partitions": {
            "train": {
                "total": len(train_set),
                "scam": sum(1 for r in train_set if r["label"] == "SCAM"),
                "legitimate": sum(1 for r in train_set if r["label"] == "LEGITIMATE"),
                "ratio_scam_percent": round(sum(1 for r in train_set if r["label"] == "SCAM") / len(train_set) * 100, 2),
            },
            "validation": {
                "total": len(val_set),
                "scam": sum(1 for r in val_set if r["label"] == "SCAM"),
                "legitimate": sum(1 for r in val_set if r["label"] == "LEGITIMATE"),
                "ratio_scam_percent": round(sum(1 for r in val_set if r["label"] == "SCAM") / len(val_set) * 100, 2),
            },
            "test": {
                "total": len(test_set),
                "scam": sum(1 for r in test_set if r["label"] == "SCAM"),
                "legitimate": sum(1 for r in test_set if r["label"] == "LEGITIMATE"),
                "ratio_scam_percent": round(sum(1 for r in test_set if r["label"] == "SCAM") / len(test_set) * 100, 2),
            },
        },
        "split_ratios": {"train": 0.70, "val": 0.15, "test": 0.15},
        "random_seed": args.seed,
    }

    report_path = os.path.join(output_dir, "data_quality_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print("\n=== DATA QUALITY & SPLIT REPORT ===")
    print(f"Raw Files Discovered: {raw_stats['total_files_discovered']}")
    print(f"Exact Duplicates Removed: {dedup_stats['duplicate_records_removed']}")
    print(f"Canonical Unique Records: {dedup_stats['canonical_record_count']}")
    print(f"  - SCAM:       {dedup_stats['scam_canonical_count']} ({dedup_stats['scam_canonical_count']/dedup_stats['canonical_record_count']*100:.1f}%)")
    print(f"  - LEGITIMATE: {dedup_stats['legit_canonical_count']} ({dedup_stats['legit_canonical_count']/dedup_stats['canonical_record_count']*100:.1f}%)")
    print(f"Partitions Generated:")
    print(f"  - Train Set:  {len(train_set)} records ({report['stratified_partitions']['train']['scam']} SCAM / {report['stratified_partitions']['train']['legitimate']} LEGIT)")
    print(f"  - Val Set:    {len(val_set)} records ({report['stratified_partitions']['validation']['scam']} SCAM / {report['stratified_partitions']['validation']['legitimate']} LEGIT)")
    print(f"  - Test Set:   {len(test_set)} records ({report['stratified_partitions']['test']['scam']} SCAM / {report['stratified_partitions']['test']['legitimate']} LEGIT)")
    print(f"Saved artifacts to {output_dir}")


if __name__ == "__main__":
    main()
