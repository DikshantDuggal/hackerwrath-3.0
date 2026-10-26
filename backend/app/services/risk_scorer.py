"""
Scam Risk Scoring Engine.

Scoring & Calibration Documentation:
------------------------------------
1. Weighted Combination & Dedicated Sensitive-Information Detection:
   - `rule_score` in [0, 100] comes from configurable indicator weights in `RulesEngine`.
   - `contextual_score` in [0, 100] comes from `ContextualAnalyzer` ("Contextual Director").
   - Sensitive credential solicitation (OTPs, PINs, passwords) is analyzed by `SensitiveInfoDetector`.
   - When protective advice, educational discussions, quoted speech, or legitimate buyer QR offers
     are confirmed and no coercive attack exists, risk is dampened to LOW (0–20).
   - Mandatory Deterministic Safety Override:
     When an un-negated solicitation for sensitive authentication information (OTP/PIN/Password)
     is detected, the risk MUST NOT be reduced to LOW or MEDIUM by a cautious LLM or weak contextual score.
     The score is floored at minimum HIGH (>= 75.0) with explicit explanation and independent verification advice.
2. Calibrated Probability `p_scam`:
   - A heuristic score is NEVER labelled as a true probability.
   - `p_scam` is `None` (`null` in JSON) unless `CALIBRATED_PROBABILITY_ENABLED=true`,
     in which case Platt scaling `1 / (1 + exp(-(slope * risk_score + intercept)))` is applied.
3. `UNKNOWN` Risk Level Handling:
   - Returns `risk_level="UNKNOWN"` and `status="insufficient_evidence"` when:
     a) `transcript_confidence < settings.min_transcript_confidence` (poor audio/STT quality), OR
     b) The transcript is too brief (< 3 words) or contains only isolated keywords (e.g. "OTP"), OR
     c) The Contextual AI service failed (`TIMEOUT`, `MALFORMED_OUTPUT`, `UNAVAILABLE`) AND
        rule-based evidence alone is insufficient to establish risk.
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional
from app.core.config import Settings, get_settings
from app.services.language_detector import get_language_detector
from app.detectors.sensitive_info_detector import (
    SensitiveInfoDetectionResult,
    SensitiveInfoDetector,
    get_sensitive_info_detector,
)
from app.schemas.analysis import (
    ContextualAnalysisOutput,
    DeepfakeAnalysisResult,
    EvidenceItem,
    RiskLevelType,
    RuleEngineResult,
    ScamRiskAssessment,
)
from app.services.alert_service import AlertService


class RiskScorer:
    """Combines rule-based evidence, contextual AI analysis, and sensitive info detection."""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        alert_service: Optional[AlertService] = None,
        sensitive_info_detector: Optional[SensitiveInfoDetector] = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.alert_service = alert_service or AlertService()
        self.sensitive_detector = sensitive_info_detector or get_sensitive_info_detector()

    def _compute_calibrated_probability(self, risk_score: float) -> Optional[float]:
        """
        Returns None (null) unless calibration is explicitly enabled and validated.
        Never labels a heuristic score as a true probability.
        """
        if not self.settings.calibrated_probability_enabled:
            return None
        norm_score = risk_score / 100.0 if risk_score > 1.0 else risk_score
        z = self.settings.calibration_slope * norm_score + self.settings.calibration_intercept
        prob = 1.0 / (1.0 + math.exp(-z))
        return round(min(0.999, max(0.001, prob)), 4)

    def score(
        self,
        *,
        rule_result: RuleEngineResult,
        contextual_result: ContextualAnalysisOutput,
        transcript_confidence: float = 0.92,
        start_seconds: Optional[float] = 0.0,
        end_seconds: Optional[float] = 5.0,
        deepfake_result: Optional[DeepfakeAnalysisResult] = None,
        sync_status: Optional[Dict[str, Any]] = None,
        rag_result: Optional[Dict[str, Any]] = None,
        icfd_result: Optional[Dict[str, Any]] = None,
        raw_transcript: Optional[str] = None,
        sensitive_detection: Optional[SensitiveInfoDetectionResult] = None,
    ) -> ScamRiskAssessment:
        reasons: List[str] = []
        evidence: List[EvidenceItem] = []
        counter_evidence: List[str] = []
        indicators: List[Dict[str, Any]] = []
        limitations: List[str] = [
            "Automated risk indicator based on transcript patterns; does not constitute definitive judicial proof of fraud.",
            "Caller identity cannot be authenticated solely over an audio or transcript channel.",
        ]

        # Extract text for length / word count verification
        sample_text = (raw_transcript or "").strip()
        if not sample_text:
            if rule_result.triggered_indicators:
                sample_text = " ".join(ind.excerpt for ind in rule_result.triggered_indicators)
            elif rule_result.suppressed_protective_matches:
                sample_text = " ".join(rule_result.suppressed_protective_matches)
            elif contextual_result.supporting_excerpts:
                sample_text = " ".join(contextual_result.supporting_excerpts)
        words = sample_text.split()
        word_count = len(words)
        lang_info = get_language_detector().detect(raw_transcript or sample_text)

        # Run or use dedicated SensitiveInfoDetector
        sens_res = sensitive_detection
        if sens_res is None:
            sens_res = self.sensitive_detector.detect(sample_text)

        is_protective = (
            sens_res.is_protective_warning
            or bool(rule_result.suppressed_protective_matches)
            or contextual_result.intent_classification == "PROTECTIVE_WARNING"
        )

        # Add counter evidence from protective / educational matches
        if sens_res.counter_evidence:
            counter_evidence.extend(sens_res.counter_evidence)
        for prot in rule_result.suppressed_protective_matches:
            counter_msg = f"Protective/Legitimate statement suppressed from rule triggers: '{prot}'."
            if counter_msg not in counter_evidence:
                counter_evidence.append(counter_msg)
        for prot in contextual_result.protective_or_legitimate_explanations:
            counter_msg = f"Contextual Director confirmed protective/legitimate context: {prot}."
            if counter_msg not in counter_evidence:
                counter_evidence.append(counter_msg)

        # Collect rule evidence and structured indicators
        for ind in rule_result.triggered_indicators:
            reasons.append(f"[{ind.category}] {ind.explanation}")
            evidence.append(
                EvidenceItem(
                    excerpt=ind.excerpt,
                    start_seconds=ind.start_seconds if ind.start_seconds is not None else start_seconds,
                    end_seconds=ind.end_seconds if ind.end_seconds is not None else end_seconds,
                    source="cross_call_sync" if ind.synced_across_calls else "rule_engine",
                    indicator=ind.keyword_or_pattern,
                )
            )
            severity = "CRITICAL" if ind.weight >= 80 else ("HIGH" if ind.weight >= 60 else "MEDIUM")
            indicators.append({
                "rule_id": ind.rule_id,
                "category": ind.category,
                "keyword_or_pattern": ind.keyword_or_pattern,
                "weight": ind.weight,
                "excerpt": ind.excerpt,
                "explanation": ind.explanation,
                "severity": severity,
                "confidence": 0.92,
            })

        # Collect sensitive info detector evidence if active solicitation
        if sens_res.is_solicitation and sens_res.evidence_excerpts:
            if not any(i.get("category") in ("OTP_OR_PIN_REQUEST", "OTP_SOLICITATION", "PIN_SOLICITATION") for i in indicators):
                indicators.append({
                    "rule_id": "RULE_SENSITIVE_CREDENTIAL_SOLICITATION",
                    "category": sens_res.category or "SENSITIVE_INFO_SOLICITATION",
                    "keyword_or_pattern": ", ".join(sens_res.target_items),
                    "weight": 85.0,
                    "excerpt": sens_res.evidence_excerpts[0],
                    "explanation": sens_res.explanation,
                    "severity": "HIGH",
                    "confidence": sens_res.confidence,
                })
                evidence.append(
                    EvidenceItem(
                        excerpt=sens_res.evidence_excerpts[0],
                        start_seconds=start_seconds,
                        end_seconds=end_seconds,
                        source="sensitive_detector",
                        indicator=sens_res.category or "CREDENTIAL_SOLICITATION",
                    )
                )

        # Collect ICFD trained model evidence
        if icfd_result and isinstance(icfd_result, dict) and icfd_result.get("available"):
            if icfd_result.get("is_fraud"):
                prob = icfd_result.get("fraud_probability", 0.0)
                lang = icfd_result.get("detected_language", "unknown")
                reasons.append(f"[ICFD Model] Flagged as fraudulent with {prob * 100:.1f}% calibrated risk ({lang}).")
                evidence.append(
                    EvidenceItem(
                        excerpt=f"ICFD-31k multilingual model calibrated fraud probability: {prob:.2f}",
                        start_seconds=start_seconds,
                        end_seconds=end_seconds,
                        source="icfd_classifier",
                        indicator=f"P(fraud)={prob:.2f}",
                    )
                )

        # Collect RAG semantic evidence
        if rag_result and isinstance(rag_result, dict):
            rag_expl = rag_result.get("explanation")
            if rag_expl and rag_expl not in reasons:
                reasons.append(f"[RAG Semantic Analysis] {rag_expl}")
            for ex in rag_result.get("retrieved_examples", []):
                if isinstance(ex, dict) and ex.get("label") == "SCAM":
                    sim = ex.get("similarity", 0.0)
                    evidence.append(
                        EvidenceItem(
                            excerpt=f"Matched case: {ex.get('text', '')[:75]}...",
                            start_seconds=start_seconds,
                            end_seconds=end_seconds,
                            source="rag_retrieval",
                            indicator=f"Cosine similarity {sim:.2f}",
                        )
                    )

        # Collect contextual AI reasons & evidence
        if contextual_result.possible_impersonation and contextual_result.claimed_organisation:
            reasons.append(
                f"Contextual AI detected possible impersonation of {contextual_result.claimed_organisation}."
            )
        for req in contextual_result.money_or_sensitive_requests:
            msg = f"Contextual AI identified sensitive/financial solicitation: {req}."
            if msg not in reasons:
                reasons.append(msg)
        for threat in contextual_result.threats_urgency_manipulation:
            msg = f"Contextual AI identified coercive manipulation: {threat}."
            if msg not in reasons:
                reasons.append(msg)
        for prot in contextual_result.protective_or_legitimate_explanations:
            reasons.append(f"Protective/Legitimate context: {prot}")

        for exc in contextual_result.supporting_excerpts:
            if not any(e.excerpt == exc for e in evidence):
                evidence.append(
                    EvidenceItem(
                        excerpt=exc,
                        start_seconds=start_seconds,
                        end_seconds=end_seconds,
                        source="contextual_ai",
                        indicator=contextual_result.intent_classification,
                    )
                )

        # ---------------------------------------------------------------------
        # UNKNOWN CONDITION 1: Low transcription quality
        # ---------------------------------------------------------------------
        if transcript_confidence < self.settings.min_transcript_confidence:
            reasons.insert(
                0,
                f"Transcription confidence ({transcript_confidence:.2f}) is below minimum reliability threshold ({self.settings.min_transcript_confidence:.2f}).",
            )
            limitations.append(
                f"Audio transcription confidence is low ({transcript_confidence:.2f}); speech content may be noisy or distorted."
            )
            alert = self.alert_service.build_alert("UNKNOWN", 0.0, rule_result.triggered_indicators)
            return ScamRiskAssessment(
                risk_score=0.0,
                p_scam=None,
                risk_level="UNKNOWN",
                status="insufficient_evidence",
                confidence=round(transcript_confidence, 4),
                caption="Low transcription quality; unable to verify call safety reliably",
                reasons=reasons,
                explanation="Audio transcription quality is below the reliability threshold. Automated assessment suspended to prevent false positives.",
                indicators=indicators,
                evidence=evidence,
                counter_evidence=counter_evidence,
                limitations=limitations,
                recommended_action=(
                    "Speech recognition quality is poor. Exercise caution, independently verify the caller's identity through official channels, and never share OTPs or passwords."
                ),
                rule_analysis=rule_result,
                contextual_analysis=contextual_result,
                icfd_analysis=icfd_result,
                deepfake_analysis=deepfake_result,
                alert=alert,
                synchronization_status=sync_status or {"working": True},
                original_text=raw_transcript or sample_text,
                normalized_text=lang_info.normalized_text,
                detected_language=lang_info.detected_language,
                detected_script=lang_info.detected_script,
            )

        # ---------------------------------------------------------------------
        # UNKNOWN CONDITION 2: Very brief or isolated token transcript (< 3 words)
        # (e.g. isolated token "OTP", "hello", "yes")
        # ---------------------------------------------------------------------
        is_isolated_token = (0 < word_count < 3) and not (
            rule_result.rule_score >= 60.0 and len(rule_result.triggered_indicators) >= 2
        )
        if is_isolated_token and not is_protective and not lang_info.is_conversational:
            limitations.append(
                "Transcript is too brief or contains only isolated tokens without conversational context to determine intent."
            )
            reasons.append(
                "Transcript contains insufficient speech length (< 3 words) for reliable intent determination."
            )
            alert = self.alert_service.build_alert("UNKNOWN", 0.0, [])
            return ScamRiskAssessment(
                risk_score=0.0,
                p_scam=None,
                risk_level="UNKNOWN",
                status="insufficient_evidence",
                confidence=0.25,
                caption="Incomplete or very brief transcript; insufficient context",
                reasons=reasons,
                explanation="Single keyword or isolated phrase detected without actionable context. Awaiting further conversation segments before scoring.",
                indicators=indicators,
                evidence=evidence,
                counter_evidence=counter_evidence,
                limitations=limitations,
                recommended_action=(
                    "Insufficient transcript context available. Exercise normal caution: never share OTPs, PINs, or banking passwords with anyone."
                ),
                rule_analysis=rule_result,
                contextual_analysis=contextual_result,
                icfd_analysis=icfd_result,
                deepfake_analysis=deepfake_result,
                alert=alert,
                synchronization_status=sync_status or {"working": True},
                original_text=raw_transcript or sample_text,
                normalized_text=lang_info.normalized_text,
                detected_language=lang_info.detected_language,
                detected_script=lang_info.detected_script,
            )

        # ---------------------------------------------------------------------
        # PROTECTIVE / EDUCATIONAL / QUOTED / BENIGN OVERRIDES
        # ---------------------------------------------------------------------
        is_protective = (
            sens_res.is_protective_warning
            or bool(rule_result.suppressed_protective_matches)
            or contextual_result.intent_classification == "PROTECTIVE_WARNING"
        )
        is_educational = sens_res.is_educational_discussion
        is_quoted = sens_res.is_quoted_speech
        is_benign = sens_res.is_benign_notification

        # If purely protective, educational, quoted, or benign notification with no un-negated attack
        if (is_protective or is_educational or is_quoted or is_benign) and not sens_res.is_solicitation:
            counter_evidence.extend(sens_res.counter_evidence)
            # Purge any false-positive solicitation indicators and reasons triggered by protective / educational context
            clean_indicators = [
                ind for ind in indicators
                if (ind.get("category") if isinstance(ind, dict) else getattr(ind, "category", "")) not in (
                    "OTP_OR_PIN_REQUEST",
                    "QR_SCAN_TO_RECEIVE_MONEY",
                    "FINANCIAL_SOLICITATION",
                    "REMOTE_ACCESS_OR_SCREEN_SHARE",
                    "SUSPICIOUS_LINK_OR_APK",
                )
            ]
            clean_reasons = [
                r for r in reasons
                if not r.startswith("[OTP_OR_PIN_REQUEST]")
                and "solicitation" not in r.lower()
                and "requested an otp" not in r.lower()
            ]
            expl_msg = ""
            caption_msg = ""
            if is_protective:
                expl_msg = "Protective security advice detected warning never to disclose credentials or sensitive information."
                caption_msg = "Protective security reminder detected: Warning never to share credentials or OTP"
            elif is_educational:
                expl_msg = "Educational discussion regarding scam techniques detected without active fraud solicitation."
                caption_msg = "Educational scam awareness discussion detected"
            elif is_quoted:
                expl_msg = "Quoted/reported speech narrating a past caller attempt detected rather than a live attack."
                caption_msg = "Narrative or quoted reference to a past contact attempt"
            elif is_benign:
                expl_msg = "Standard notification or official self-service instruction detected."
                caption_msg = "Standard system notification or self-service instruction"

            clean_reasons.append(expl_msg)
            alert = self.alert_service.build_alert("LOW", 0.0, [])
            return ScamRiskAssessment(
                risk_score=0.0,
                p_scam=self._compute_calibrated_probability(0.0),
                risk_level="LOW",
                status="success",
                confidence=0.92,
                caption=caption_msg,
                reasons=clean_reasons,
                explanation=expl_msg,
                indicators=clean_indicators,
                evidence=[],
                counter_evidence=counter_evidence,
                limitations=limitations,
                recommended_action=(
                    "Continue with normal caution. Never share OTPs, UPI PINs, or passwords with anyone on a phone call. Legitimate organizations will never ask for your secret codes."
                ),
                rule_analysis=RuleEngineResult(
                    rule_score=0.0,
                    triggered_indicators=clean_indicators,
                    suppressed_protective_matches=rule_result.suppressed_protective_matches,
                    duplicate_indicators_skipped=rule_result.duplicate_indicators_skipped,
                    synced_keywords_matched=[],
                ),
                contextual_analysis=contextual_result,
                icfd_analysis=icfd_result,
                deepfake_analysis=deepfake_result,
                alert=alert,
                synchronization_status=sync_status or {"working": True},
                original_text=raw_transcript or sample_text,
                normalized_text=lang_info.normalized_text,
                detected_language=lang_info.detected_language,
                detected_script=lang_info.detected_script,
            )

        # ---------------------------------------------------------------------
        # UNKNOWN CONDITION 3: AI service failure (timeout / malformed / unavailable)
        # ---------------------------------------------------------------------
        ai_failed = contextual_result.service_status in (
            "TIMEOUT",
            "MALFORMED_OUTPUT",
            "UNAVAILABLE",
        )
        if ai_failed and rule_result.rule_score < 45.0 and not sens_res.is_solicitation:
            reasons.append(
                f"Contextual AI service status is {contextual_result.service_status} and rule-based evidence alone is insufficient for a reliable classification."
            )
            limitations.append(
                f"Contextual intent service encountered {contextual_result.service_status}; fallback heuristics applied."
            )
            alert = self.alert_service.build_alert("UNKNOWN", rule_result.rule_score, rule_result.triggered_indicators)
            return ScamRiskAssessment(
                risk_score=round(rule_result.rule_score * 0.5, 2),
                p_scam=None,
                risk_level="UNKNOWN",
                status="insufficient_evidence",
                confidence=0.30,
                caption=contextual_result.contextual_caption,
                reasons=reasons,
                explanation=f"Contextual AI service returned {contextual_result.service_status}; available evidence is inconclusive.",
                indicators=indicators,
                evidence=evidence,
                counter_evidence=counter_evidence,
                limitations=limitations,
                recommended_action=(
                    "Automated analysis is temporarily degraded. Exercise standard caution with any payment or credential requests and verify caller independently."
                ),
                rule_analysis=rule_result,
                contextual_analysis=contextual_result,
                icfd_analysis=icfd_result,
                deepfake_analysis=deepfake_result,
                alert=alert,
                synchronization_status=sync_status or {"working": True},
                original_text=raw_transcript or sample_text,
                normalized_text=lang_info.normalized_text,
                detected_language=lang_info.detected_language,
                detected_script=lang_info.detected_script,
            )

        # ---------------------------------------------------------------------
        # UNKNOWN CONDITION 4: Empty / insufficient context
        # ---------------------------------------------------------------------
        if (
            contextual_result.intent_classification == "INSUFFICIENT_CONTEXT"
            and not rule_result.triggered_indicators
            and not rule_result.suppressed_protective_matches
            and not sens_res.has_sensitive_mention
            and not lang_info.is_conversational
        ):
            reasons.append("Available transcript evidence is too brief or ambiguous to assess caller intent.")
            limitations.append("Insufficient conversational speech captured in this segment.")
            alert = self.alert_service.build_alert("UNKNOWN", 0.0, [])
            return ScamRiskAssessment(
                risk_score=0.0,
                p_scam=None,
                risk_level="UNKNOWN",
                status="insufficient_evidence",
                confidence=0.25,
                caption=contextual_result.contextual_caption,
                reasons=reasons,
                explanation="Speech segment does not contain enough linguistic evidence to determine intent.",
                indicators=[],
                evidence=[],
                counter_evidence=counter_evidence,
                limitations=limitations,
                recommended_action=(
                    "Monitoring conversation. Exercise standard caution: never share OTPs or passwords over the phone."
                ),
                rule_analysis=rule_result,
                contextual_analysis=contextual_result,
                icfd_analysis=icfd_result,
                deepfake_analysis=deepfake_result,
                alert=alert,
                synchronization_status=sync_status or {"working": True},
                original_text=raw_transcript or sample_text,
                normalized_text=lang_info.normalized_text,
                detected_language=lang_info.detected_language,
                detected_script=lang_info.detected_script,
            )


        # ---------------------------------------------------------------------
        # SCORING COMBINATION
        # ---------------------------------------------------------------------
        w_rule = self.settings.rule_score_weight
        w_ctx = 0.0 if ai_failed else self.settings.contextual_score_weight
        has_valid_rag = bool(rag_result and isinstance(rag_result, dict) and not rag_result.get("insufficient_evidence"))
        w_rag = self.settings.rag_score_weight if has_valid_rag else 0.0
        weight_sum = max(0.01, w_rule + w_ctx + w_rag)

        rag_contribution = w_rag * float(rag_result.get("risk_score", 0.0)) if has_valid_rag else 0.0
        combined = (
            w_rule * rule_result.rule_score + w_ctx * contextual_result.intent_risk_score + rag_contribution
        ) / weight_sum

        # Synergy boost when both Rule Engine and Contextual Director detect strong solicitation
        if rule_result.rule_score >= 40.0 and contextual_result.intent_risk_score >= 55.0:
            combined = min(100.0, combined + 14.0)

        # Temper isolated non-sensitive keyword if contextual intent confirms benign/protective
        if (
            rule_result.rule_score > 0.0
            and len(rule_result.triggered_indicators) == 1
            and not sens_res.is_solicitation
            and contextual_result.intent_classification in ("PROTECTIVE_WARNING", "LEGITIMATE_INQUIRY")
            and contextual_result.intent_risk_score < 20.0
        ):
            combined = min(combined, 22.0)
            reasons.append(
                "Single rule indicator was tempered because contextual intent analysis found no solicitation or threat."
            )

        # Urgency without scam indicators should NOT trigger a high false alarm
        urgency_only = (
            len(rule_result.triggered_indicators) == 1
            and rule_result.triggered_indicators[0].category in ("URGENT_PAYMENT_DEMAND", "PRESSURE_AND_SECRECY_TACTIC")
            and not sens_res.is_solicitation
            and contextual_result.intent_risk_score < 35.0
        )
        if urgency_only and "meeting" in sample_text.lower() or "train" in sample_text.lower() or "late" in sample_text.lower():
            combined = min(combined, 25.0)

        # ---------------------------------------------------------------------
        # MANDATORY DETERMINISTIC SAFETY OVERRIDE
        # ---------------------------------------------------------------------
        # If an un-negated solicitation for sensitive authentication information
        # (OTP, PIN, Password, Credentials) is detected, the risk MUST NOT be reduced
        # to LOW or MEDIUM by a cautious LLM or weak contextual score.
        categories_triggered = {ind.category for ind in rule_result.triggered_indicators}
        has_otp_rule = "OTP_OR_PIN_REQUEST" in categories_triggered
        has_sensitive_solicitation = sens_res.is_solicitation or has_otp_rule

        # Check for corroborating attack signals
        has_authority_claim = (
            "AUTHORITY_OR_BANK_IMPERSONATION" in categories_triggered
            or contextual_result.possible_impersonation
        )
        has_coercion_or_threat = (
            "ACCOUNT_SUSPENSION_THREAT" in categories_triggered
            or "THREAT_ARREST_OR_LEGAL_ACTION" in categories_triggered
            or bool(contextual_result.threats_urgency_manipulation)
        )
        has_urgency = (
            "URGENT_PAYMENT_DEMAND" in categories_triggered
            or "PRESSURE_AND_SECRECY_TACTIC" in categories_triggered
        )

        override_activated = False
        if has_sensitive_solicitation and not is_protective:
            # Dangerous pattern: Credential solicitation combined with bank/threat/urgency
            # OR direct OTP/PIN solicitation alone (banks NEVER request OTP/PIN over call)
            override_activated = True
            base_floor = 75.0  # Guarantees HIGH risk
            if has_authority_claim or has_coercion_or_threat:
                base_floor = 85.0  # Escalates to CRITICAL when combined with threats/impersonation
            if has_authority_claim and has_coercion_or_threat and has_urgency:
                base_floor = 92.0

            if combined < base_floor:
                combined = base_floor
                reasons.append(
                    "Deterministic safety override activated: un-negated sensitive authentication information solicitation detected. Banks and legitimate services never ask for OTP or PIN over phone calls."
                )

        risk_score = round(min(100.0, max(0.0, combined)), 2)

        # Determine risk level with configurable thresholds:
        # 80-100: CRITICAL, 60-79: HIGH, 30-59: MEDIUM, 0-29: LOW
        if risk_score >= self.settings.critical_risk_threshold:
            risk_level: RiskLevelType = "CRITICAL"
        elif risk_score >= self.settings.medium_risk_threshold:
            risk_level = "HIGH"
        elif risk_score >= self.settings.low_risk_threshold:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"

        if not reasons:
            reasons.append("No suspicious payment demands, credential requests, or coercive threats detected.")

        alert = self.alert_service.build_alert(
            risk_level, risk_score, rule_result.triggered_indicators
        )

        # Formulate plain-language explanation
        if override_activated or risk_level in ("HIGH", "CRITICAL"):
            explanation_parts = []
            if sens_res.is_solicitation or has_otp_rule:
                explanation_parts.append("The caller requested sensitive authentication credentials (such as an OTP or PIN).")
            if has_authority_claim:
                explanation_parts.append("The caller claimed to represent a bank, official body, or authority without independent verification.")
            if has_coercion_or_threat:
                explanation_parts.append("The caller employed coercive pressure (such as threats of account suspension or legal action).")
            if has_urgency:
                explanation_parts.append("The caller used urgency manipulation demanding immediate action.")
            if override_activated:
                explanation_parts.append("Deterministic safety override enforced a minimum HIGH risk level because legitimate financial institutions never ask for OTPs or PINs over the phone.")
            explanation = " ".join(explanation_parts)
        elif risk_level == "MEDIUM":
            explanation = "Suspicious indicators detected (such as unusual urgency or unverified claims), but evidence remains inconclusive. Exercise heightened caution."
        else:
            explanation = "No meaningful scam indicators detected; conversation patterns match normal, benign, or protective communication."

        # Formulate actionable recommended_action with explicit independent verification guidance
        if risk_level in ("HIGH", "CRITICAL"):
            recommended_action = (
                "High-risk scam pattern detected. Disconnect the call immediately and independently verify through your official bank app, website, or local branch. Never call back a number supplied by the caller, and never share OTPs, UPI PINs, passwords, or remote screen access."
            )
        elif risk_level == "MEDIUM":
            recommended_action = (
                "Suspicious call indicators detected. Do not rush into any payments, credential sharing, or app installations. Independently verify the caller's identity through official public channels before taking any action."
            )
        else:
            recommended_action = (
                "Continue with normal caution. Never share OTPs, UPI PINs, or passwords with anyone on a phone call. Legitimate banks and organizations will never ask for secret codes."
            )

        overall_confidence = round(
            min(
                1.0,
                transcript_confidence
                * (0.55 if ai_failed else max(0.75, contextual_result.model_confidence)),
            ),
            4,
        )

        return ScamRiskAssessment(
            risk_score=risk_score,
            p_scam=self._compute_calibrated_probability(risk_score),
            risk_level=risk_level,
            status="success",
            confidence=overall_confidence,
            caption=contextual_result.contextual_caption,
            reasons=reasons,
            explanation=explanation,
            indicators=indicators,
            evidence=evidence,
            counter_evidence=counter_evidence,
            limitations=limitations,
            recommended_action=recommended_action,
            scoring_version="2.1.0-contextual-aware",
            rule_analysis=rule_result,
            contextual_analysis=contextual_result,
            rag_analysis=rag_result,
            icfd_analysis=icfd_result,
            deepfake_analysis=deepfake_result,
            alert=alert,
            synchronization_status=sync_status or {"working": True},
                original_text=raw_transcript or sample_text,
                normalized_text=lang_info.normalized_text,
                detected_language=lang_info.detected_language,
                detected_script=lang_info.detected_script,
        )
