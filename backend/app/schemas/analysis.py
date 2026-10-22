"""
Pydantic schemas for Rule-Based Detection, Contextual AI Director Analysis,
Calibrated Scam Risk Scoring, and Alert Generation.
"""
from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional
from app.core.compat import BaseModel, Field

RiskLevelType = Literal["LOW", "MEDIUM", "HIGH", "UNKNOWN"]
IntentClassificationType = Literal[
    "SCAM_SOLICITATION",
    "SUSPICIOUS_PRESSURE",
    "PROTECTIVE_WARNING",
    "LEGITIMATE_INQUIRY",
    "INSUFFICIENT_CONTEXT",
]
AiServiceStatusType = Literal[
    "OK",
    "FALLBACK_HEURISTIC",
    "TIMEOUT",
    "MALFORMED_OUTPUT",
    "UNAVAILABLE",
]


class TriggeredIndicator(BaseModel):
    """A specific suspicious indicator triggered by the Rule-Based Engine."""

    rule_id: str
    category: str
    keyword_or_pattern: str
    weight: float = Field(default=0.0, ge=0.0, le=1.0)
    excerpt: str
    start_seconds: Optional[float] = None
    end_seconds: Optional[float] = None
    synced_across_calls: bool = False
    explanation: str = ""


class RuleEngineResult(BaseModel):
    """Output of the configurable Rule-Based Detection Engine."""

    rule_score: float = Field(default=0.0, ge=0.0, le=1.0)
    triggered_indicators: List[TriggeredIndicator] = Field(default_factory=list)
    suppressed_protective_matches: List[str] = Field(default_factory=list)
    duplicate_indicators_skipped: int = Field(default=0, ge=0)
    synced_keywords_matched: List[str] = Field(default_factory=list)


class ContextualAIWireSchema(BaseModel):
    """Strict validation schema for raw LLM / Contextual Director JSON responses."""

    model_config = {"extra": "forbid"}

    caller_identity_claim: Optional[str] = None
    claimed_organisation: Optional[str] = None
    requested_actions: List[str] = Field(default_factory=list)
    money_or_sensitive_requests: List[str] = Field(default_factory=list)
    threats_urgency_manipulation: List[str] = Field(default_factory=list)
    possible_impersonation: bool = False
    protective_or_legitimate_explanations: List[str] = Field(default_factory=list)
    supporting_excerpts: List[str] = Field(default_factory=list)
    contextual_caption: str = Field(default="Monitoring call intent")
    intent_classification: IntentClassificationType = "LEGITIMATE_INQUIRY"
    intent_risk_score: float = Field(default=0.0, ge=0.0, le=1.0)
    model_confidence: float = Field(default=0.8, ge=0.0, le=1.0)


class ContextualAnalysisOutput(BaseModel):
    """Full output of the Contextual AI Director module, including service reliability metadata."""

    caller_identity_claim: Optional[str] = None
    claimed_organisation: Optional[str] = None
    requested_actions: List[str] = Field(default_factory=list)
    money_or_sensitive_requests: List[str] = Field(default_factory=list)
    threats_urgency_manipulation: List[str] = Field(default_factory=list)
    possible_impersonation: bool = False
    protective_or_legitimate_explanations: List[str] = Field(default_factory=list)
    supporting_excerpts: List[str] = Field(default_factory=list)
    contextual_caption: str = Field(default="Monitoring call intent")
    intent_classification: IntentClassificationType = "LEGITIMATE_INQUIRY"
    intent_risk_score: float = Field(default=0.0, ge=0.0, le=1.0)
    model_confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    service_status: AiServiceStatusType = "OK"


class DeepfakeAnalysisResult(BaseModel):
    """Optional acoustic voice spoofing / deepfake detection output."""

    enabled: bool = False
    is_suspected_deepfake: bool = False
    spoof_score: float = Field(default=0.0, ge=0.0, le=1.0)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    provider: str = "acoustic_heuristic_v1"
    explanation: str = "Deepfake voice analysis not enabled for this segment."


class EvidenceItem(BaseModel):
    """Suspicious transcript excerpt and timestamp supporting the risk assessment."""

    excerpt: str
    start_seconds: Optional[float] = None
    end_seconds: Optional[float] = None
    source: Literal["rule_engine", "contextual_ai", "cross_call_sync"] = "rule_engine"
    indicator: str = ""


class AlertPayload(BaseModel):
    """Non-definitive safety alert generated when risk thresholds are reached."""

    alert_id: str
    triggered: bool = False
    severity: Literal["NONE", "ADVISORY", "WARNING", "CRITICAL"] = "NONE"
    headline: str = ""
    safe_action: str = ""
    disclaimer: str = (
        "Automated risk indicator based on call patterns. Do not treat as a definitive determination of fraud; verify independently through official channels."
    )


class ScamRiskAssessment(BaseModel):
    """
    Unified Scam Risk Assessment combining Rule-Based Evidence, Contextual AI Director,
    Cross-Call Keyword Synchronization, and Optional Deepfake Detection.
    """

    risk_score: float = Field(default=0.0, ge=0.0, le=1.0)
    p_scam: Optional[float] = Field(default=None)
    risk_level: RiskLevelType = "LOW"
    confidence: Optional[float] = Field(default=0.85, ge=0.0, le=1.0)
    caption: str = Field(default="Normal conversation monitoring")
    reasons: List[str] = Field(default_factory=list)
    evidence: List[EvidenceItem] = Field(default_factory=list)
    recommended_action: str = Field(
        default="Continue with normal caution; never share OTPs, UPI PINs, or passwords on a call."
    )
    rule_analysis: RuleEngineResult = Field(default_factory=RuleEngineResult)
    contextual_analysis: ContextualAnalysisOutput = Field(
        default_factory=ContextualAnalysisOutput
    )
    deepfake_analysis: Optional[DeepfakeAnalysisResult] = None
    alert: Optional[AlertPayload] = None
    synchronization_status: Dict[str, Any] = Field(default_factory=dict)


class TranscriptAnalysisRequest(BaseModel):
    """Request payload for POST /analyze/transcript."""

    transcript: str = Field(min_length=1)
    language_code: str = Field(default="auto")
    call_id: Optional[str] = None
    speaker: str = Field(default="caller")
    start_seconds: Optional[float] = Field(default=0.0, ge=0.0)
    end_seconds: Optional[float] = Field(default=5.0, ge=0.0)
    transcript_confidence: float = Field(default=0.92, ge=0.0, le=1.0)
    conversation_history: List[str] = Field(default_factory=list)
