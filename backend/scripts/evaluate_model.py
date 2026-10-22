"""
Comprehensive Evaluation Suite for Scam Detection Systems.
Evaluates on the isolated test set (data/test.jsonl):
1. TF-IDF + Logistic Regression Baseline
2. RAG Semantic Retrieval & Contextual Classifier
Reports: Accuracy, Precision, Recall, F1, Confusion Matrix, FPR, FNR, Latency.
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

# Ensure backend root is on sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app.rag.classifier import RAGScamClassifier
from app.rag.config import BASELINE_MODEL_PATH, TEST_DATA_PATH, TRAIN_DATA_PATH, VECTOR_STORE_DIR
from app.rag.retriever import get_retriever
from app.rag.schemas import RAGClassificationRequest


def load_dataset_records(jsonl_path: str) -> List[Dict[str, Any]]:
    records = []
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def train_or_load_tfidf_baseline(train_records: List[Dict[str, Any]]) -> Any:
    """Trains or loads TF-IDF + Logistic Regression baseline."""
    os.makedirs(VECTOR_STORE_DIR, exist_ok=True)
    if os.path.exists(BASELINE_MODEL_PATH):
        try:
            model_dict = joblib.load(BASELINE_MODEL_PATH)
            return model_dict["vectorizer"], model_dict["classifier"]
        except Exception:
            pass

    print("Training TF-IDF + Logistic Regression Baseline on train partition...")
    train_texts = [r["text"] for r in train_records]
    train_labels = [r["label"] for r in train_records]

    vectorizer = TfidfVectorizer(max_features=10000, ngram_range=(1, 2), sublinear_tf=True)
    X_train = vectorizer.fit_transform(train_texts)

    clf = LogisticRegression(class_weight="balanced", max_iter=500, random_state=42)
    clf.fit(X_train, train_labels)

    joblib.dump({"vectorizer": vectorizer, "classifier": clf}, BASELINE_MODEL_PATH)
    print(f"Saved baseline model to '{BASELINE_MODEL_PATH}'")
    return vectorizer, clf


def evaluate_predictions(y_true: List[str], y_pred: List[str]) -> Dict[str, Any]:
    """Computes full classification metrics."""
    # Convert UNCERTAIN in predictions to SCAM or treat safely; for binary evaluation:
    # Any prediction not matching the positive class is considered negative
    labels = ["LEGITIMATE", "SCAM"]
    cm = confusion_matrix(y_true, y_pred, labels=labels)

    # cm structure:
    # [ [TN, FP],
    #   [FN, TP] ]
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
            "true_negatives_legit": int(tn),
            "false_positives_scam": int(fp),
            "false_negatives_legit": int(fn),
            "true_positives_scam": int(tp),
        },
        "false_positive_rate": round(float(fpr), 4),
        "false_negative_rate": round(float(fnr), 4),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate baseline and RAG scam detection models on test partition.")
    parser.add_argument("--test-data", default=TEST_DATA_PATH, help="Path to test.jsonl")
    parser.add_argument("--train-data", default=TRAIN_DATA_PATH, help="Path to train.jsonl (for baseline training)")
    parser.add_argument("--sample-limit", type=int, default=0, help="Optional sample limit for fast benchmarking (0 = full test set)")
    parser.add_argument("--output-json", default=os.path.join(VECTOR_STORE_DIR, "evaluation_report.json"), help="Output JSON path")
    args = parser.parse_args()

    print("=== PHASE 7: EVALUATING SCAM DETECTION ON ISOLATED TEST SET ===")
    test_records = load_dataset_records(args.test_data)
    train_records = load_dataset_records(args.train_data)

    if args.sample_limit > 0:
        test_records = test_records[: args.sample_limit]

    total_test = len(test_records)
    y_true = [r["label"] for r in test_records]
    print(f"Loaded {total_test} isolated test records ({sum(1 for y in y_true if y == 'SCAM')} SCAM / {sum(1 for y in y_true if y == 'LEGITIMATE')} LEGITIMATE)")

    # -------------------------------------------------------------
    # SYSTEM 1: TF-IDF + Logistic Regression Baseline
    # -------------------------------------------------------------
    print("\n--- Evaluating System 1: TF-IDF + Logistic Regression Baseline ---")
    vectorizer, clf = train_or_load_tfidf_baseline(train_records)

    t_base_start = time.time()
    X_test = vectorizer.transform([r["text"] for r in test_records])
    y_pred_baseline = clf.predict(X_test).tolist()
    baseline_time = time.time() - t_base_start
    avg_baseline_latency_ms = round((baseline_time / total_test) * 1000, 3)

    metrics_baseline = evaluate_predictions(y_true, y_pred_baseline)
    metrics_baseline["avg_latency_ms"] = avg_baseline_latency_ms

    # -------------------------------------------------------------
    # SYSTEM 2: RAG Contextual Retrieval & Semantic Classifier
    # -------------------------------------------------------------
    print("\n--- Evaluating System 2: RAG Semantic Retrieval & Contextual Classifier ---")
    retriever = get_retriever()
    if not retriever.is_ready:
        retriever.load()

    classifier = RAGScamClassifier(retriever=retriever)

    y_pred_rag = []
    rag_latencies = []
    retrieval_latencies = []

    t_rag_start = time.time()
    for idx, r in enumerate(test_records):
        req = RAGClassificationRequest(text=r["text"], top_k=5, include_retrieved_examples=False)
        res = classifier.classify(req)
        # If UNCERTAIN, resolve based on risk score threshold (> 50 -> SCAM)
        pred_label = res.classification
        if pred_label == "UNCERTAIN":
            pred_label = "SCAM" if res.risk_score >= 50.0 else "LEGITIMATE"
        y_pred_rag.append(pred_label)
        rag_latencies.append(res.classification_latency_ms)
        retrieval_latencies.append(res.retrieval_latency_ms)

    metrics_rag = evaluate_predictions(y_true, y_pred_rag)
    metrics_rag["avg_inference_latency_ms"] = round(float(np.mean(rag_latencies)), 2)
    metrics_rag["avg_retrieval_latency_ms"] = round(float(np.mean(retrieval_latencies)), 2)

    # -------------------------------------------------------------
    # Targeted Benchmark Probe: Protective vs Solicitation vs Inbound
    # -------------------------------------------------------------
    probe_cases = [
        {"id": "Probe_Protective", "text": "Never share your OTP with anyone. Our bank representatives never ask for it.", "expected": "LEGITIMATE"},
        {"id": "Probe_Solicitation", "text": "Tell me the OTP you just received right now so I can verify your account.", "expected": "SCAM"},
        {"id": "Probe_AuthNotice", "text": "Your OTP for login is 492018. Valid for 10 minutes. Do not share.", "expected": "LEGITIMATE"},
        {"id": "Probe_UrgentFreeze", "text": "Your bank account has been blocked immediately. Transfer 5000 to unfreeze.", "expected": "SCAM"},
    ]

    probe_results = []
    for p in probe_cases:
        res = classifier.classify(RAGClassificationRequest(text=p["text"]))
        passed = (res.classification == p["expected"])
        probe_results.append({
            "probe_id": p["id"],
            "text": p["text"],
            "expected": p["expected"],
            "predicted": res.classification,
            "risk_score": res.risk_score,
            "passed": passed,
        })

    # Summary Report
    report = {
        "dataset": {
            "test_size": total_test,
            "scam_count": sum(1 for y in y_true if y == "SCAM"),
            "legit_count": sum(1 for y in y_true if y == "LEGITIMATE"),
        },
        "system_1_tfidf_baseline": metrics_baseline,
        "system_2_rag_classifier": metrics_rag,
        "targeted_probes": probe_results,
    }

    with open(args.output_json, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print("\n======================= FINAL EVALUATION BENCHMARK =======================")
    print(f"{'Metric':<30} | {'TF-IDF + LogReg':<18} | {'RAG Semantic System':<20}")
    print("-" * 75)
    print(f"{'Accuracy':<30} | {metrics_baseline['accuracy']:<18.4f} | {metrics_rag['accuracy']:<20.4f}")
    print(f"{'Macro F1-Score':<30} | {metrics_baseline['macro_f1']:<18.4f} | {metrics_rag['macro_f1']:<20.4f}")
    print(f"{'SCAM Precision':<30} | {metrics_baseline['scam_metrics']['precision']:<18.4f} | {metrics_rag['scam_metrics']['precision']:<20.4f}")
    print(f"{'SCAM Recall':<30} | {metrics_baseline['scam_metrics']['recall']:<18.4f} | {metrics_rag['scam_metrics']['recall']:<20.4f}")
    print(f"{'SCAM F1-Score':<30} | {metrics_baseline['scam_metrics']['f1']:<18.4f} | {metrics_rag['scam_metrics']['f1']:<20.4f}")
    print(f"{'False Positive Rate (FPR)':<30} | {metrics_baseline['false_positive_rate']:<18.4f} | {metrics_rag['false_positive_rate']:<20.4f}")
    print(f"{'False Negative Rate (FNR)':<30} | {metrics_baseline['false_negative_rate']:<18.4f} | {metrics_rag['false_negative_rate']:<20.4f}")
    print(f"{'Avg Inference Latency (ms)':<30} | {metrics_baseline['avg_latency_ms']:<18.3f} | {metrics_rag['avg_inference_latency_ms']:<20.2f}")
    print(f"{'Avg Retrieval Latency (ms)':<30} | {'N/A':<18} | {metrics_rag['avg_retrieval_latency_ms']:<20.2f}")
    print("=" * 75)

    print("\n--- Targeted Probe Verification ---")
    for pr in probe_results:
        status_icon = "PASS" if pr["passed"] else "FAIL"
        print(f"[{status_icon}] {pr['probe_id']}: Expected={pr['expected']}, Pred={pr['predicted']} (Risk Score: {pr['risk_score']})")
    print(f"\nSaved full benchmark report to: {args.output_json}")


if __name__ == "__main__":
    main()
