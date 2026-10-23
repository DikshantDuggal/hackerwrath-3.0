"""
Multilingual Baseline Model Training and Validation for EdgeRunners.
Trains TF-IDF Vectorizer + Logistic Regression on data/train.jsonl (multilingual).
Evaluates on data/val.jsonl, reporting aggregate, English, and Hindi validation metrics.
Saves model bundle to vector_store/baseline_model.joblib.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from typing import Any, Dict, List, Tuple
import joblib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app.rag.config import BASELINE_MODEL_PATH, VECTOR_STORE_DIR


def load_records(jsonl_path: str) -> List[Dict[str, Any]]:
    records = []
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def compute_metrics(y_true: List[str], y_pred: List[str], latencies_ms: List[float]) -> Dict[str, Any]:
    labels = ["LEGITIMATE", "SCAM"]
    cm = confusion_matrix(y_true, y_pred, labels=labels)
    tn, fp, fn, tp = cm.ravel()

    acc = accuracy_score(y_true, y_pred)
    prec_scam = precision_score(y_true, y_pred, pos_label="SCAM", zero_division=0)
    rec_scam = recall_score(y_true, y_pred, pos_label="SCAM", zero_division=0)
    f1_scam = f1_score(y_true, y_pred, pos_label="SCAM", zero_division=0)

    prec_legit = precision_score(y_true, y_pred, pos_label="LEGITIMATE", zero_division=0)
    rec_legit = recall_score(y_true, y_pred, pos_label="LEGITIMATE", zero_division=0)
    f1_legit = f1_score(y_true, y_pred, pos_label="LEGITIMATE", zero_division=0)

    macro_f1 = f1_score(y_true, y_pred, average="macro", zero_division=0)
    fpr = (fp / (fp + tn)) if (fp + tn) > 0 else 0.0
    fnr = (fn / (fn + tp)) if (fn + tp) > 0 else 0.0

    return {
        "accuracy": round(float(acc), 4),
        "macro_f1": round(float(macro_f1), 4),
        "scam_metrics": {
            "precision": round(float(prec_scam), 4),
            "recall": round(float(rec_scam), 4),
            "f1": round(float(f1_scam), 4),
        },
        "legitimate_metrics": {
            "precision": round(float(prec_legit), 4),
            "recall": round(float(rec_legit), 4),
            "f1": round(float(f1_legit), 4),
        },
        "confusion_matrix": {
            "tn_legit": int(tn),
            "fp_scam": int(fp),
            "fn_legit": int(fn),
            "tp_scam": int(tp),
        },
        "false_positive_rate": round(float(fpr), 4),
        "false_negative_rate": round(float(fnr), 4),
        "avg_latency_ms": round(float(np.mean(latencies_ms)), 3) if latencies_ms else 0.0,
    }


def train_baseline(train_path: str, val_path: str, model_save_path: str = BASELINE_MODEL_PATH) -> Dict[str, Any]:
    print("=== PHASE C: TRAINING MULTILINGUAL TF-IDF + LOGISTIC REGRESSION BASELINE ===")
    train_records = load_records(train_path)
    val_records = load_records(val_path)

    print(f"Loaded {len(train_records)} training records (multilingual: English + Hindi).")
    print(f"Loaded {len(val_records)} validation records.")

    train_texts = [r["text"] for r in train_records]
    train_labels = [r["label"] for r in train_records]

    # Multilingual tokenization: word unigram + bigram, sublinear TF
    print("Fitting TF-IDF Vectorizer (max_features=25000, ngram_range=(1,2))...")
    vectorizer = TfidfVectorizer(
        max_features=25000,
        ngram_range=(1, 2),
        sublinear_tf=True,
        token_pattern=r"(?u)\b\w+\b",  # Unicode-aware word token pattern for Devanagari and Latin
    )
    X_train = vectorizer.fit_transform(train_texts)

    print("Fitting Logistic Regression with class_weight='balanced'...")
    clf = LogisticRegression(class_weight="balanced", max_iter=1000, random_state=42, C=1.0)
    clf.fit(X_train, train_labels)

    os.makedirs(os.path.dirname(model_save_path), exist_ok=True)
    joblib.dump({"vectorizer": vectorizer, "classifier": clf, "version": "1.0-multilingual"}, model_save_path)
    print(f"Saved fitted baseline model to '{model_save_path}'")

    # Evaluate on Validation Data
    print("\n--- Evaluating Baseline on Validation Set ---")
    val_texts = [r["text"] for r in val_records]
    y_true_all = [r["label"] for r in val_records]

    latencies = []
    y_pred_all = []
    for txt in val_texts:
        t0 = time.time()
        feat = vectorizer.transform([txt])
        pred = clf.predict(feat)[0]
        latencies.append((time.time() - t0) * 1000)
        y_pred_all.append(pred)

    overall_metrics = compute_metrics(y_true_all, y_pred_all, latencies)

    # Slice evaluation by language
    en_indices = [i for i, r in enumerate(val_records) if r.get("language") == "en"]
    hi_indices = [i for i, r in enumerate(val_records) if r.get("language") == "hi"]

    en_metrics = compute_metrics(
        [y_true_all[i] for i in en_indices],
        [y_pred_all[i] for i in en_indices],
        [latencies[i] for i in en_indices],
    )
    hi_metrics = compute_metrics(
        [y_true_all[i] for i in hi_indices],
        [y_pred_all[i] for i in hi_indices],
        [latencies[i] for i in hi_indices],
    )

    print("\n=== VALIDATION RESULTS (TF-IDF BASELINE) ===")
    print(f"{'Slice':<16} | {'Accuracy':<10} | {'Macro F1':<10} | {'Scam Rec':<10} | {'Scam Prec':<10} | {'FPR':<10} | {'Latency':<10}")
    print("-" * 88)
    print(f"{'Overall Val':<16} | {overall_metrics['accuracy']:<10.4f} | {overall_metrics['macro_f1']:<10.4f} | {overall_metrics['scam_metrics']['recall']:<10.4f} | {overall_metrics['scam_metrics']['precision']:<10.4f} | {overall_metrics['false_positive_rate']:<10.4f} | {overall_metrics['avg_latency_ms']:<8.2f}ms")
    print(f"{'English Val':<16} | {en_metrics['accuracy']:<10.4f} | {en_metrics['macro_f1']:<10.4f} | {en_metrics['scam_metrics']['recall']:<10.4f} | {en_metrics['scam_metrics']['precision']:<10.4f} | {en_metrics['false_positive_rate']:<10.4f} | {en_metrics['avg_latency_ms']:<8.2f}ms")
    print(f"{'Hindi Val':<16} | {hi_metrics['accuracy']:<10.4f} | {hi_metrics['macro_f1']:<10.4f} | {hi_metrics['scam_metrics']['recall']:<10.4f} | {hi_metrics['scam_metrics']['precision']:<10.4f} | {hi_metrics['false_positive_rate']:<10.4f} | {hi_metrics['avg_latency_ms']:<8.2f}ms")
    print("=" * 88)

    val_report = {
        "overall": overall_metrics,
        "english": en_metrics,
        "hindi": hi_metrics,
    }
    report_path = os.path.join(VECTOR_STORE_DIR, "baseline_val_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(val_report, f, indent=2)
    print(f"Saved validation report to '{report_path}'")
    return val_report


def main():
    parser = argparse.ArgumentParser(description="Train baseline TF-IDF model on multilingual data.")
    parser.add_argument("--train-data", default="data/train.jsonl")
    parser.add_argument("--val-data", default="data/val.jsonl")
    args = parser.parse_args()

    train_baseline(args.train_data, args.val_data)


if __name__ == "__main__":
    main()
