"""
ICFD-31k Trained Multilingual Fraud Classifier Detector.
Integrates the fine-tuned, calibrated fraud detection model trained on the
ICFD-31k conversational dataset into the FastAPI backend.
"""
from __future__ import annotations

import json
import logging
import re
import time
from pathlib import Path
from typing import Any, Dict, Optional
import joblib
from pydantic import BaseModel, Field

logger = logging.getLogger("scam_detector.icfd_classifier")

HINGLISH_MARKERS = {
    "namaste", "ji", "aap", "aapka", "aapki", "mera", "meri", "kya", "kyun",
    "hai", "hain", "nahi", "nahin", "karo", "karein", "karna", "paise", "rupaye",
    "bhai", "shukriya", "dhanyawad", "theek", "achha", "accha", "haan", "matlab",
    "kripya", "jaldi", "baat", "batao", "bataye", "dekh", "dekho", "chahiye",
    "bolo", "boliye", "kaha", "kahan", "samajh", "bhejo", "kardo", "hoga", "hogi"
}
DEVANAGARI_RE = re.compile(r"[\u0900-\u097F]")
LATIN_WORDS_RE = re.compile(r"\b[a-zA-Z]+\b")


class IcfdClassificationResult(BaseModel):
    """Structured result from the ICFD-31k trained model."""
    available: bool = Field(default=True, description="Whether the trained model is loaded and ready")
    fraud_probability: float = Field(default=0.0, description="Calibrated probability of fraud [0.0, 1.0]")
    is_fraud: bool = Field(default=False, description="Whether probability exceeds configured threshold")
    decision_threshold: float = Field(default=0.65, description="Operating alert threshold")
    model_name: str = Field(default="ICFD-31k Production Calibrated Classifier")
    model_version: str = Field(default="1.0.0")
    calibration_status: str = Field(default="calibrated_platt_sigmoid")
    detected_language: str = Field(default="unknown")
    latency_ms: float = Field(default=0.0)
    error_message: Optional[str] = None


class IcfdClassifier:
    """
    Singleton-friendly classifier that manages the multilingual sentence encoder
    and calibrated classifier head trained on ICFD-31k.
    """

    def __init__(self, model_dir: Optional[Path] = None) -> None:
        if model_dir is None:
            model_dir = Path(__file__).resolve().parent.parent / "models" / "icfd_classifier"
        self.model_dir = model_dir
        self.model_path = model_dir / "icfd_calibrated_model.joblib"
        self.config_path = model_dir / "config.json"
        
        self.classifier = None
        self.embedder = None
        self.config: Dict[str, Any] = {}
        self.threshold = 0.65
        self.available = False
        
        self._load_model()

    def _load_model(self) -> None:
        if not self.model_path.exists():
            logger.warning(
                "ICFD-31k model artifact not found at %s. Running in fallback mode.",
                self.model_path
            )
            self.available = False
            return

        try:
            logger.info("Loading ICFD-31k model artifact from %s", self.model_path)
            self.classifier = joblib.load(self.model_path)

            if self.config_path.exists():
                with open(self.config_path, "r", encoding="utf-8") as f:
                    self.config = json.load(f)
                    self.threshold = float(self.config.get("decision_threshold", 0.65))

            from sentence_transformers import SentenceTransformer
            embed_model_name = self.config.get("embedding_model", "sentence-transformers/all-MiniLM-L6-v2")
            self.embedder = SentenceTransformer(embed_model_name, device="cpu")
            self.available = True
            logger.info("ICFD-31k classifier loaded successfully (operating threshold: %.2f)", self.threshold)
        except Exception as exc:
            logger.error("Failed to load ICFD-31k model artifact: %s", exc, exc_info=True)
            self.available = False

    def detect_language(self, text: str) -> str:
        """Classifies text into Devanagari Hindi, Hinglish, or English."""
        if not text:
            return "unknown"
        has_devanagari = bool(DEVANAGARI_RE.search(text))
        words = [w.lower() for w in LATIN_WORDS_RE.findall(text)]
        if not words:
            return "hindi_devanagari" if has_devanagari else "unknown"
        
        hinglish_count = sum(1 for w in words if w in HINGLISH_MARKERS)
        ratio = hinglish_count / len(words)

        if has_devanagari and ratio > 0.05:
            return "hindi_mixed"
        elif has_devanagari:
            return "hindi_devanagari"
        elif ratio >= 0.04 or hinglish_count >= 2:
            return "hinglish"
        else:
            return "english"

    def predict(self, transcript: str) -> IcfdClassificationResult:
        """
        Computes calibrated fraud probability for the input transcript.
        """
        start_time = time.perf_counter()
        lang = self.detect_language(transcript)

        if not transcript or not transcript.strip():
            return IcfdClassificationResult(
                available=self.available,
                fraud_probability=0.0,
                is_fraud=False,
                decision_threshold=self.threshold,
                detected_language=lang,
                latency_ms=round((time.perf_counter() - start_time) * 1000, 2),
                error_message="Empty transcript provided"
            )

        if not self.available or self.classifier is None or self.embedder is None:
            return IcfdClassificationResult(
                available=False,
                fraud_probability=0.0,
                is_fraud=False,
                decision_threshold=self.threshold,
                detected_language=lang,
                latency_ms=round((time.perf_counter() - start_time) * 1000, 2),
                error_message="ICFD-31k classifier unavailable (using rule and RAG heuristics fallback)"
            )

        try:
            embedding = self.embedder.encode(
                [transcript],
                batch_size=1,
                show_progress_bar=False,
                normalize_embeddings=True
            )
            prob = float(self.classifier.predict_proba(embedding)[0, 1])
            is_fraud = prob >= self.threshold

            return IcfdClassificationResult(
                available=True,
                fraud_probability=round(prob, 4),
                is_fraud=is_fraud,
                decision_threshold=self.threshold,
                model_name=self.config.get("model_name", "ICFD-31k Production Calibrated Classifier"),
                model_version=self.config.get("version", "1.0.0"),
                calibration_status="calibrated_platt_sigmoid",
                detected_language=lang,
                latency_ms=round((time.perf_counter() - start_time) * 1000, 2)
            )
        except Exception as exc:
            logger.error("Inference failed on transcript: %s", exc)
            return IcfdClassificationResult(
                available=False,
                fraud_probability=0.0,
                is_fraud=False,
                decision_threshold=self.threshold,
                detected_language=lang,
                latency_ms=round((time.perf_counter() - start_time) * 1000, 2),
                error_message=f"Inference error: {str(exc)}"
            )


# Global singleton instance
_icfd_classifier_instance: Optional[IcfdClassifier] = None

def get_icfd_classifier() -> IcfdClassifier:
    global _icfd_classifier_instance
    if _icfd_classifier_instance is None:
        _icfd_classifier_instance = IcfdClassifier()
    return _icfd_classifier_instance
