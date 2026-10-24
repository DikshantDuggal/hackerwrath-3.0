"""
Defensive AI Scam-Call Detection Benchmark Evaluation Suite.
Evaluates the multi-layer pipeline (Rules Engine + Contextual Director + Sensitive Info Detector)
on held-out test splits across English, Hindi, Punjabi, Hinglish, and Indian regional languages.

Computes:
- Precision, Recall, F1-Score, Accuracy
- False Positive Rate (FPR), False Negative Rate (FNR)
- Per-Language Performance Breakdown
- Per-Category Performance Breakdown
- Inference Latency Distribution (mean, p50, p95, p99 ms)
"""
from __future__ import annotations

import json
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List

# Ensure backend root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.contextual_analyzer import ContextualAnalyzer
from app.services.risk_scorer import RiskScorer
from app.services.rules_engine import RulesEngine

DATASET_ROOT = Path("D:/edgerunner_datasets")
TEST_SPLIT_PATH = DATASET_ROOT / "benchmarks" / "test.jsonl"
EVAL_RESULTS_PATH = DATASET_ROOT / "benchmark_evaluation_results.json"


def evaluate_dataset(test_file: Path, max_samples: int = 1000) -> Dict[str, Any]:
    if not test_file.exists():
        raise FileNotFoundError(f"Test split not found at {test_file}")

    rules_engine = RulesEngine()
    contextual_analyzer = ContextualAnalyzer()
    risk_scorer = RiskScorer()

    records: List[Dict[str, Any]] = []
    with open(test_file, "r", encoding="utf-8") as f:
        for idx, line in enumerate(f):
            if max_samples and idx >= max_samples:
                break
            line = line.strip()
            if line:
                records.append(json.loads(line))

    print(f"Loaded {len(records)} test samples from {test_file.name}")

    overall_tp = 0
    overall_fp = 0
    overall_tn = 0
    overall_fn = 0
    latencies: List[float] = []

    per_lang_stats: Dict[str, Dict[str, int]] = defaultdict(lambda: {"tp": 0, "fp": 0, "tn": 0, "fn": 0, "total": 0})
    per_source_stats: Dict[str, Dict[str, int]] = defaultdict(lambda: {"tp": 0, "fp": 0, "tn": 0, "fn": 0, "total": 0})

    for idx, rec in enumerate(records):
        text = rec["text"]
        true_label = rec["label"]  # "SCAM" or "BENIGN"
        lang = rec.get("language", "unknown").lower()
        source = rec.get("source_dataset", "unknown")

        t0 = time.perf_counter()
        rule_res, _ = rules_engine.evaluate(text)
        ctx_res = contextual_analyzer.analyze(text)
        assessment = risk_scorer.score(
            rule_result=rule_res,
            contextual_result=ctx_res,
            raw_transcript=text,
        )
        t_elapsed_ms = (time.perf_counter() - t0) * 1000.0
        latencies.append(t_elapsed_ms)

        pred_scam = assessment.risk_level in ("HIGH", "CRITICAL", "MEDIUM")

        is_tp = true_label == "SCAM" and pred_scam
        is_fp = true_label == "BENIGN" and pred_scam
        is_tn = true_label == "BENIGN" and not pred_scam
        is_fn = true_label == "SCAM" and not pred_scam

        if is_tp:
            overall_tp += 1
            per_lang_stats[lang]["tp"] += 1
            per_source_stats[source]["tp"] += 1
        elif is_fp:
            overall_fp += 1
            per_lang_stats[lang]["fp"] += 1
            per_source_stats[source]["fp"] += 1
        elif is_tn:
            overall_tn += 1
            per_lang_stats[lang]["tn"] += 1
            per_source_stats[source]["tn"] += 1
        elif is_fn:
            overall_fn += 1
            per_lang_stats[lang]["fn"] += 1
            per_source_stats[source]["fn"] += 1

        per_lang_stats[lang]["total"] += 1
        per_source_stats[source]["total"] += 1

        if (idx + 1) % 200 == 0 or (idx + 1) == len(records):
            print(f"Processed {idx + 1}/{len(records)} samples...")

    def compute_metrics(tp: int, fp: int, tn: int, fn: int) -> Dict[str, float]:
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
        accuracy = (tp + tn) / (tp + tn + fp + fn) if (tp + tn + fp + fn) > 0 else 0.0
        fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
        fnr = fn / (fn + tp) if (fn + tp) > 0 else 0.0
        return {
            "tp": tp,
            "fp": fp,
            "tn": tn,
            "fn": fn,
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1_score": round(f1, 4),
            "accuracy": round(accuracy, 4),
            "fpr": round(fpr, 4),
            "fnr": round(fnr, 4),
        }

    overall_metrics = compute_metrics(overall_tp, overall_fp, overall_tn, overall_fn)

    # Latency percentiles
    latencies.sort()
    n = len(latencies)
    latency_summary = {
        "mean_ms": round(sum(latencies) / max(1, n), 2),
        "min_ms": round(latencies[0], 2) if latencies else 0.0,
        "p50_ms": round(latencies[int(n * 0.50)], 2) if latencies else 0.0,
        "p90_ms": round(latencies[int(n * 0.90)], 2) if latencies else 0.0,
        "p95_ms": round(latencies[int(n * 0.95)], 2) if latencies else 0.0,
        "p99_ms": round(latencies[int(n * 0.99)], 2) if latencies else 0.0,
        "max_ms": round(latencies[-1], 2) if latencies else 0.0,
    }

    per_lang_breakdown = {}
    for lang, counts in per_lang_stats.items():
        m = compute_metrics(counts["tp"], counts["fp"], counts["tn"], counts["fn"])
        m["sample_count"] = counts["total"]
        per_lang_breakdown[lang] = m

    per_source_breakdown = {}
    for src, counts in per_source_stats.items():
        m = compute_metrics(counts["tp"], counts["fp"], counts["tn"], counts["fn"])
        m["sample_count"] = counts["total"]
        per_source_breakdown[src] = m

    report = {
        "evaluation_timestamp": "2026-10-24T22:15:00Z",
        "benchmark_file": str(test_file.name),
        "total_evaluated_samples": len(records),
        "overall_metrics": overall_metrics,
        "latency_statistics": latency_summary,
        "per_language_performance": per_lang_breakdown,
        "per_source_performance": per_source_breakdown,
    }

    with open(EVAL_RESULTS_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print("\n=======================================================")
    print("           BENCHMARK EVALUATION SUMMARY                ")
    print("=======================================================")
    print(f"Total Test Samples:   {report['total_evaluated_samples']}")
    print(f"Accuracy:             {overall_metrics['accuracy']:.2%}")
    print(f"Precision:            {overall_metrics['precision']:.2%}")
    print(f"Recall:               {overall_metrics['recall']:.2%}")
    print(f"F1-Score:             {overall_metrics['f1_score']:.2%}")
    print(f"False Positive Rate:  {overall_metrics['fpr']:.2%}")
    print(f"False Negative Rate:  {overall_metrics['fnr']:.2%}")
    print("-------------------------------------------------------")
    print(f"Inference Latency:    p50: {latency_summary['p50_ms']}ms | p95: {latency_summary['p95_ms']}ms | mean: {latency_summary['mean_ms']}ms")
    print("=======================================================\n")

    return report


if __name__ == "__main__":
    evaluate_dataset(TEST_SPLIT_PATH, max_samples=1000)
