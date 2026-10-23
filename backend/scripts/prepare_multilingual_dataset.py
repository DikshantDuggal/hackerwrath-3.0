"""
Production Data Preparation Pipeline for Multilingual EdgeRunners Scam Detection.
Processes both English (Text_english) and Hindi (Text_hindi) datasets from D:\\Dataset for EdgeRunners.

Key Engineering Guarantees:
1. Leakage-Free Stratification:
   Groups parallel English and Hindi dialogues by their shared dialogue ID so that
   an example's English and Hindi counterparts are ALWAYS assigned to the exact same split
   (never split across Train and Test).
2. Devanagari Unicode Integrity:
   Strict UTF-8 encoding/decoding preservation without aggressive ascii stripping or corruption.
3. Deduplication:
   Filters exact duplicate files within each language partition while recording duplicate lineage.
4. Output Partitions:
   - data/train.jsonl     (70% Train - Combined Multilingual Reference Set)
   - data/val.jsonl       (15% Validation - Combined Multilingual Set)
   - data/test.jsonl      (15% Test - Combined Multilingual Held-Out Test Set)
   - data/test_en.jsonl   (15% English-only isolated test slice)
   - data/test_hi.jsonl   (15% Hindi-only isolated test slice)
   - data/multilingual_data_quality_report.json
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import random
import re
import sys
import unicodedata
from collections import Counter
from typing import Any, Dict, List, Set, Tuple


def normalize_dialogue_text(text: str) -> str:
    """
    Normalizes encoding and whitespace while strictly preserving conversational turns,
    Devanagari characters, punctuation, numbers, and speaker labels.
    """
    if not text:
        return ""
    # NFKC normalizes Unicode compatibility characters while preserving Devanagari
    text = unicodedata.normalize("NFKC", text)
    # Standardize whitespace and line endings
    text = text.replace("\xa0", " ").replace("\t", " ")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    lines = [re.sub(r"[ ]+", " ", line).strip() for line in text.split("\n")]
    return "\n".join(lines).strip()


def detect_script(text: str) -> str:
    """Classifies script composition of text."""
    dev = sum(1 for c in text if 0x0900 <= ord(c) <= 0x097F)
    lat = sum(1 for c in text if ("a" <= c <= "z" or "A" <= c <= "Z"))
    if dev > 0 and lat == 0:
        return "Devanagari"
    elif dev > 0 and lat > 0:
        ratio = dev / (dev + lat)
        return "Devanagari_Dominant_Mixed" if ratio >= 0.5 else "Latin_Dominant_Mixed"
    elif lat > 0 and dev == 0:
        return "Latin"
    return "Other"


def load_and_deduplicate_language_folder(
    dataset_dir: str,
    lang_code: str,
) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Any]]:
    """
    Loads legit and scam subdirectories for a specific language dataset,
    normalizes text, and indexes canonical records by base dialogue file key.
    """
    legit_dir = os.path.join(dataset_dir, "legit")
    scam_dir = os.path.join(dataset_dir, "scam")

    if not os.path.isdir(legit_dir) or not os.path.isdir(scam_dir):
        raise FileNotFoundError(
            f"Expected 'legit' and 'scam' folders in {dataset_dir}"
        )

    files_by_cat = {
        "LEGITIMATE": glob.glob(os.path.join(legit_dir, "*.txt")),
        "SCAM": glob.glob(os.path.join(scam_dir, "*.txt")),
    }

    print(f"[{lang_code.upper()}] Loading files: {len(files_by_cat['LEGITIMATE'])} legit, {len(files_by_cat['SCAM'])} scam.")

    dialogue_records: Dict[str, Dict[str, Any]] = {}
    content_fingerprints: Dict[str, str] = {}  # sha256 -> base_key
    duplicates_removed = 0
    empty_records = 0

    for label, filepaths in files_by_cat.items():
        for fp in filepaths:
            base_filename = os.path.splitext(os.path.basename(fp))[0]
            try:
                with open(fp, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read().strip()
            except Exception as e:
                empty_records += 1
                continue

            if not content:
                empty_records += 1
                continue

            cleaned = normalize_dialogue_text(content)
            h = hashlib.sha256(cleaned.encode("utf-8")).hexdigest()

            # If identical content already seen in this language, record as duplicate
            if h in content_fingerprints:
                duplicates_removed += 1
                canonical_key = content_fingerprints[h]
                if canonical_key in dialogue_records:
                    dialogue_records[canonical_key]["duplicate_files"].append(base_filename)
                continue

            content_fingerprints[h] = base_filename
            script_type = detect_script(cleaned)
            dialogue_records[base_filename] = {
                "dialogue_key": base_filename,
                "text": cleaned,
                "label": label,
                "language": lang_code,
                "script": script_type,
                "char_length": len(cleaned),
                "word_count": len(cleaned.split()),
                "fingerprint": h,
                "duplicate_files": [base_filename],
            }

    stats = {
        "language": lang_code,
        "total_files": len(files_by_cat["LEGITIMATE"]) + len(files_by_cat["SCAM"]),
        "legit_raw": len(files_by_cat["LEGITIMATE"]),
        "scam_raw": len(files_by_cat["SCAM"]),
        "empty_files": empty_records,
        "duplicates_removed": duplicates_removed,
        "canonical_unique_records": len(dialogue_records),
        "legit_canonical": sum(1 for r in dialogue_records.values() if r["label"] == "LEGITIMATE"),
        "scam_canonical": sum(1 for r in dialogue_records.values() if r["label"] == "SCAM"),
    }
    print(f"[{lang_code.upper()}] Deduplication complete: {len(dialogue_records)} canonical unique records ({duplicates_removed} duplicates filtered).")
    return dialogue_records, stats


def prepare_multilingual_splits(
    eng_dir: str,
    hindi_dir: str,
    output_dir: str,
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
    test_ratio: float = 0.15,
    seed: int = 42,
) -> Dict[str, Any]:
    """
    Loads English and Hindi datasets, performs cross-lingual dialogue grouping,
    stratified splitting, and writes output JSONL files.
    """
    os.makedirs(output_dir, exist_ok=True)

    eng_records, eng_stats = load_and_deduplicate_language_folder(eng_dir, "en")
    hindi_records, hindi_stats = load_and_deduplicate_language_folder(hindi_dir, "hi")

    # Union of all dialogue keys across English and Hindi
    all_keys = sorted(list(set(eng_records.keys()).union(set(hindi_records.keys()))))
    print(f"\nTotal unique dialogue keys across both languages: {len(all_keys)}")

    # Classify each dialogue key's canonical label
    key_labels: Dict[str, str] = {}
    label_conflicts = 0
    for k in all_keys:
        eng_label = eng_records.get(k, {}).get("label")
        hin_label = hindi_records.get(k, {}).get("label")
        if eng_label and hin_label:
            if eng_label != hin_label:
                label_conflicts += 1
                print(f"WARNING: Cross-lingual label conflict on key '{k}': Eng={eng_label}, Hin={hin_label}")
                canonical_label = eng_label
            else:
                canonical_label = eng_label
        elif eng_label:
            canonical_label = eng_label
        else:
            canonical_label = hin_label
        key_labels[k] = canonical_label

    # Deterministic Stratified Split by dialogue key
    rng = random.Random(seed)
    scam_keys = [k for k in all_keys if key_labels[k] == "SCAM"]
    legit_keys = [k for k in all_keys if key_labels[k] == "LEGITIMATE"]

    rng.shuffle(scam_keys)
    rng.shuffle(legit_keys)

    def split_list(lst: List[str]) -> Tuple[List[str], List[str], List[str]]:
        n = len(lst)
        n_train = int(n * train_ratio)
        n_val = int(n * val_ratio)
        return lst[:n_train], lst[n_train : n_train + n_val], lst[n_train + n_val :]

    train_scam, val_scam, test_scam = split_list(scam_keys)
    train_legit, val_legit, test_legit = split_list(legit_keys)

    train_keys_set = set(train_scam + train_legit)
    val_keys_set = set(val_scam + val_legit)
    test_keys_set = set(test_scam + test_legit)

    print(f"Dialogue Key Partitioning (Stratified 70/15/15):")
    print(f"  - Train Dialogue Keys: {len(train_keys_set)} ({len(train_scam)} SCAM / {len(train_legit)} LEGIT)")
    print(f"  - Val Dialogue Keys:   {len(val_keys_set)} ({len(val_scam)} SCAM / {len(val_legit)} LEGIT)")
    print(f"  - Test Dialogue Keys:  {len(test_keys_set)} ({len(test_scam)} SCAM / {len(test_legit)} LEGIT)")

    # Verify no dialogue leakage
    assert len(train_keys_set.intersection(test_keys_set)) == 0, "FATAL: Train/Test dialogue leakage detected!"
    assert len(train_keys_set.intersection(val_keys_set)) == 0, "FATAL: Train/Val dialogue leakage detected!"
    assert len(val_keys_set.intersection(test_keys_set)) == 0, "FATAL: Val/Test dialogue leakage detected!"

    # Materialize records for each partition
    partitions = {
        "train": [],
        "val": [],
        "test": [],
        "test_en": [],
        "test_hi": [],
    }

    record_counter = 0
    for key in all_keys:
        target_split = (
            "train" if key in train_keys_set else ("val" if key in val_keys_set else "test")
        )

        # Add English instance if present
        if key in eng_records:
            record_counter += 1
            e_rec = eng_records[key]
            rec_obj = {
                "example_id": f"ex_{record_counter:06d}",
                "dialogue_key": key,
                "text": e_rec["text"],
                "label": e_rec["label"],
                "language": "en",
                "script": e_rec["script"],
                "source": "TeleAntiFraud-28k-English",
                "word_count": e_rec["word_count"],
            }
            partitions[target_split].append(rec_obj)
            if target_split == "test":
                partitions["test_en"].append(rec_obj)

        # Add Hindi instance if present
        if key in hindi_records:
            record_counter += 1
            h_rec = hindi_records[key]
            rec_obj = {
                "example_id": f"ex_{record_counter:06d}",
                "dialogue_key": key,
                "text": h_rec["text"],
                "label": h_rec["label"],
                "language": "hi",
                "script": h_rec["script"],
                "source": "TeleAntiFraud-28k-Hindi",
                "word_count": h_rec["word_count"],
            }
            partitions[target_split].append(rec_obj)
            if target_split == "test":
                partitions["test_hi"].append(rec_obj)

    # Save to JSONL files
    file_map = {
        "train.jsonl": partitions["train"],
        "val.jsonl": partitions["val"],
        "test.jsonl": partitions["test"],
        "test_en.jsonl": partitions["test_en"],
        "test_hi.jsonl": partitions["test_hi"],
    }

    for fname, recs in file_map.items():
        fpath = os.path.join(output_dir, fname)
        with open(fpath, "w", encoding="utf-8") as f:
            for r in recs:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"Saved {len(recs)} records -> '{fpath}'")

    report = {
        "english_audit": eng_stats,
        "hindi_audit": hindi_stats,
        "cross_dataset_stats": {
            "total_unique_dialogues": len(all_keys),
            "label_conflicts": label_conflicts,
            "train_dialogues": len(train_keys_set),
            "val_dialogues": len(val_keys_set),
            "test_dialogues": len(test_keys_set),
            "train_records_combined": len(partitions["train"]),
            "val_records_combined": len(partitions["val"]),
            "test_records_combined": len(partitions["test"]),
            "test_en_records": len(partitions["test_en"]),
            "test_hi_records": len(partitions["test_hi"]),
        },
        "class_distributions": {
            "train": Counter(r["label"] for r in partitions["train"]),
            "val": Counter(r["label"] for r in partitions["val"]),
            "test": Counter(r["label"] for r in partitions["test"]),
            "test_en": Counter(r["label"] for r in partitions["test_en"]),
            "test_hi": Counter(r["label"] for r in partitions["test_hi"]),
        },
    }

    report_path = os.path.join(output_dir, "multilingual_data_quality_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"Saved data quality report to '{report_path}'")
    return report


def main():
    parser = argparse.ArgumentParser(description="Prepare Multilingual Dataset for EdgeRunners.")
    parser.add_argument("--eng-dir", default=r"D:\Dataset for EdgeRunners\Text_english", help="English dataset folder")
    parser.add_argument("--hindi-dir", default=r"D:\Dataset for EdgeRunners\Text_hindi", help="Hindi dataset folder")
    parser.add_argument("--output-dir", default=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data"), help="Output data directory")
    args = parser.parse_args()

    print("=== PHASE B: EXECUTING REPRODUCIBLE MULTILINGUAL DATA PREPARATION ===")
    prepare_multilingual_splits(
        eng_dir=args.eng_dir,
        hindi_dir=args.hindi_dir,
        output_dir=args.output_dir,
    )


if __name__ == "__main__":
    main()
