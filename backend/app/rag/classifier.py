"""
RAG-Powered Scam Detection Classifier.
Combines semantic retrieval evidence, contextual intent rules, and uncertainty estimation.
Distinguishes protective advice, authentication notices, and active fraud requests.
"""
from __future__ import annotations

import re
import time
from typing import Any, Dict, List, Optional, Tuple

from app.core.logging import get_logger
from app.rag.config import (
    AMBIGUITY_MARGIN,
    DEFAULT_TOP_K,
    STRONG_EVIDENCE_SIMILARITY_THRESHOLD,
    WEAK_EVIDENCE_SIMILARITY_THRESHOLD,
)
from app.rag.preprocessing import clean_incoming_query, normalize_transcript_text
from app.rag.retriever import SemanticRetriever, get_retriever
from app.rag.schemas import (
    RAGClassificationRequest,
    RAGClassificationResponse,
    RetrievedExample,
)

logger = get_logger("scam_detector.rag.classifier")

_GLOBAL_CLASSIFIER: Optional[RAGScamClassifier] = None

# High-precision patterns for context differentiation (English, Hinglish & Devanagari Hindi)
PROTECTIVE_ADVICE_RE = re.compile(
    r"\b(?:never|don'?t|do not|kabhi (?:bhi )?mat|alert|warning|beware|rule)\b.*"
    r"\b(?:share|give|tell|disclose|bhejo|batana)\b.*"
    r"\b(?:otp|pin|password|cvv|credentials|details)\b"
    r"|"
    r"\b(?:never share|do not share|don'?t give|kabhi mat batana)\b"
    r"|"
    r"(?:साझा\s+न\s+करें|कभी\s+(?:भी\s+)?मत\s+बताएं|किसी\s+को\s+न\s+दें|ओटीपी\s+शेयर\s+न\s+करें|बैंक\s+अधिकारी\s+कभी\s+नहीं\s+मांगते)",
    re.IGNORECASE,
)

INBOUND_AUTH_NOTIFICATION_RE = re.compile(
    r"\b(?:your|aapka|apka)\s+(?:otp|verification code|login code)\s+(?:is|for|to)\s+\d{4,8}\b"
    r"|"
    r"\bdo not share this code with anyone\b"
    r"|"
    r"(?:लॉगिन\s+के\s+लिए\s+आपका\s+ओटीपी|ओटीपी\s+कोड\s+\d{4,8}\s+है)",
    re.IGNORECASE,
)

ACTIVE_SOLICITATION_RE = re.compile(
    r"\b(?:tell|share|send|give|batao|bhejiye|provide)\b.*"
    r"\b(?:me|us|hume|mujhe)?\b.*"
    r"\b(?:otp|pin|cvv|code|password)\b"
    r"|"
    r"\b(?:verify|authenticate|unblock|confirm)\s+(?:your\s+)?(?:account|card|kyc|identity)\b.*"
    r"\b(?:otp|pin|code)\b"
    r"|"
    r"(?:ओटीपी.*(?:बताएं|दीजिए|साझा|भेजें|सत्यापित)|सत्यापित.*ओटीपी|अपना\s+ओटीपी)",
    re.IGNORECASE,
)

COERCION_URGENCY_RE = re.compile(
    r"\b(?:blocked|suspended|frozen|arrest|police|legal action|penalty|cbi|customs|fine)\b.*"
    r"\b(?:within|immediately|turant|hours?|minutes?|urgent|now)\b"
    r"|"
    r"(?:खाता.*(?:ब्लॉक|बंद|फ्रीज)|तुरंत.*(?:भुगतान|सत्यापित|ट्रांसफर)|कानूनी\s+कार्रवाई|जुर्माना)",
    re.IGNORECASE,
)


class RAGScamClassifier:
    """
    RAG-powered fraud classification engine.
    Analyzes top-k retrieved semantic neighbors and context rules.
    """

    def __init__(self, retriever: Optional[SemanticRetriever] = None) -> None:
        self.retriever = retriever or get_retriever()

    def classify(self, request: RAGClassificationRequest) -> RAGClassificationResponse:
        """
        Classifies incoming text using RAG evidence and contextual intent analysis.
        """
        t0 = time.time()
        raw_text = request.text.strip() if request.text else ""

        # 1. Input Validation
        if not raw_text:
            return RAGClassificationResponse(
                classification="UNCERTAIN",
                risk_score=0.0,
                confidence=0.0,
                insufficient_evidence=True,
                indicators=["Empty or missing input text"],
                retrieved_examples=[],
                explanation="Input transcript is empty. Unable to perform semantic scam classification.",
                retrieval_latency_ms=0.0,
                classification_latency_ms=round((time.time() - t0) * 1000, 2),
            )

        # 2. Preprocess & Prepare Retrieval Query
        cleaned_query = clean_incoming_query(raw_text, request.preceding_context)

        # 3. Semantic Vector Retrieval
        retrieved_examples, insufficient_evidence, retrieval_latency_ms = self.retriever.retrieve(
            query_text=cleaned_query,
            top_k=request.top_k,
            similarity_threshold=WEAK_EVIDENCE_SIMILARITY_THRESHOLD,
        )

        indicators: List[str] = []
        explanation_parts: List[str] = []

        # 4. Contextual Rule Analysis (Differentiating Intent)
        is_protective = bool(PROTECTIVE_ADVICE_RE.search(raw_text))
        is_auth_notice = bool(INBOUND_AUTH_NOTIFICATION_RE.search(raw_text)) and not is_protective
        is_active_solicitation = bool(ACTIVE_SOLICITATION_RE.search(raw_text))
        is_coercion = bool(COERCION_URGENCY_RE.search(raw_text))

        # 5. Semantic Evidence Weighting from Retrieved Neighbors
        scam_sim_sum = 0.0
        legit_sim_sum = 0.0
        scam_count = 0
        legit_count = 0
        max_scam_sim = 0.0
        max_legit_sim = 0.0

        for ex in retrieved_examples:
            # We square similarity to amplify high-confidence matches
            weight = max(0.0, ex.similarity) ** 2
            if ex.label == "SCAM":
                scam_sim_sum += weight
                scam_count += 1
                if ex.similarity > max_scam_sim:
                    max_scam_sim = ex.similarity
            else:
                legit_sim_sum += weight
                legit_count += 1
                if ex.similarity > max_legit_sim:
                    max_legit_sim = ex.similarity

        total_sim = scam_sim_sum + legit_sim_sum
        rag_scam_ratio = (scam_sim_sum / total_sim) if total_sim > 0 else 0.5

        # 6. Synthesize Classification Verdict
        # Case A: Explicit Protective Advice ("Never share your OTP...")
        if is_protective:
            classification = "LEGITIMATE"
            risk_score = 0.0
            confidence = 0.95
            indicators.append("Protective security advice detected (anti-scam awareness)")
            explanation_parts.append(
                "The message warns against sharing credentials or OTPs. "
                "This is protective security advice and is classified as legitimate."
            )

        # Case B: Inbound Authentication / OTP Delivery Notice ("Your OTP for login is...")
        elif is_auth_notice and not is_active_solicitation and not is_coercion:
            classification = "LEGITIMATE"
            risk_score = 5.0
            confidence = 0.90
            indicators.append("Standard automated authentication code delivery notification")
            explanation_parts.append(
                "The message represents a standard inbound system authentication notice, "
                "not an unsolicited third-party request for credentials."
            )

        # Case C: Active Credential Solicitation or Coercive Threat
        elif is_active_solicitation or (is_coercion and not is_protective):
            classification = "SCAM"
            # Base risk from solicitation/coercion (75) plus RAG evidence
            risk_score = min(100.0, 75.0 + (rag_scam_ratio * 25.0))
            confidence = max(0.85, max_scam_sim)
            if is_active_solicitation:
                indicators.append("Unsolicited request for sensitive authentication credentials (OTP/PIN)")
            if is_coercion:
                indicators.append("Artificial urgency or threat of account suspension/penalties")
            explanation_parts.append(
                f"The text actively solicits authentication credentials or imposes urgent threats. "
                f"Matches {scam_count}/{len(retrieved_examples)} fraud reference dialogues (peak similarity: {max_scam_sim:.2f})."
            )

        # Case D: Insufficient Evidence or Weak Semantic Match
        elif insufficient_evidence or (not retrieved_examples):
            classification = "UNCERTAIN"
            risk_score = 25.0
            confidence = 0.35
            indicators.append("Weak semantic retrieval evidence from reference fraud corpus")
            explanation_parts.append(
                "Retrieved semantic similarity is below minimum confidence threshold. "
                "Insufficient context to reliably determine fraud intent."
            )

        # Case E: Conflicting / Ambiguous Retrieval Evidence
        elif abs(max_scam_sim - max_legit_sim) < AMBIGUITY_MARGIN and scam_count > 0 and legit_count > 0:
            classification = "UNCERTAIN"
            risk_score = round(rag_scam_ratio * 100.0, 1)
            confidence = 0.50
            indicators.append("Contradictory retrieval evidence across both scam and legitimate reference examples")
            explanation_parts.append(
                f"Retrieved neighbors contain mixed signals ({scam_count} scam vs {legit_count} legitimate). "
                f"Nearest scam: {max_scam_sim:.2f}, nearest legitimate: {max_legit_sim:.2f}."
            )

        # Case F: Dominant Semantic Evidence from RAG Corpus
        elif rag_scam_ratio >= 0.60 and max_scam_sim >= WEAK_EVIDENCE_SIMILARITY_THRESHOLD:
            classification = "SCAM"
            risk_score = round(min(100.0, max(55.0, rag_scam_ratio * 95.0)), 1)
            confidence = round(max_scam_sim, 2)
            indicators.append(f"Strong semantic alignment with known phone scam dialogues ({scam_count}/{len(retrieved_examples)} matches)")
            explanation_parts.append(
                f"Corpus retrieval strongly aligns with fraudulent phone conversations (top similarity {max_scam_sim:.2f})."
            )

        else:
            classification = "LEGITIMATE"
            risk_score = round(max(0.0, rag_scam_ratio * 40.0), 1)
            confidence = round(max(0.70, max_legit_sim), 2)
            indicators.append(f"Semantic alignment with legitimate customer service or normal conversations ({legit_count}/{len(retrieved_examples)} matches)")
            explanation_parts.append(
                f"Conversation exhibits normal conversational dynamics aligning with legitimate records (top similarity {max_legit_sim:.2f})."
            )

        total_latency_ms = round((time.time() - t0) * 1000, 2)

        return RAGClassificationResponse(
            classification=classification,
            risk_score=float(risk_score),
            confidence=float(confidence),
            insufficient_evidence=insufficient_evidence,
            indicators=indicators,
            retrieved_examples=retrieved_examples if request.include_retrieved_examples else [],
            explanation=" ".join(explanation_parts),
            retrieval_latency_ms=retrieval_latency_ms,
            classification_latency_ms=total_latency_ms,
        )


def get_classifier() -> RAGScamClassifier:
    """Returns singleton RAGScamClassifier instance."""
    global _GLOBAL_CLASSIFIER
    if _GLOBAL_CLASSIFIER is None:
        _GLOBAL_CLASSIFIER = RAGScamClassifier()
    return _GLOBAL_CLASSIFIER
