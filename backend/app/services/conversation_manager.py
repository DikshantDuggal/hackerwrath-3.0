"""
Conversation State & History Manager.
Coordinates multi-segment call analysis, cross-call keyword synchronization,
duplicate evidence suppression across segments, and call history retrieval.
"""
from __future__ import annotations

import time
import uuid
from typing import List, Optional
from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.repositories.conversation_repository import (
    ConversationRepository,
    get_conversation_repository,
)
from app.schemas.analysis import (
    RuleEngineResult,
    ScamRiskAssessment,
    TranscriptAnalysisRequest,
)
from app.schemas.calls import (
    CallClearResponse,
    CallHistoryResponse,
    CallSegmentRecord,
    CallSegmentRequest,
    CallSegmentUpdateResponse,
)
from app.services.contextual_analyzer import ContextualAnalyzer
from app.services.keyword_sync_service import KeywordSyncService, get_keyword_sync_service
from app.services.risk_scorer import RiskScorer
from app.services.rules_engine import RulesEngine

logger = get_logger("scam_detector.conversation_manager")


class ConversationManager:
    """Maintains context and cumulative risk assessment across call transcript segments."""

    def __init__(
        self,
        repository: Optional[ConversationRepository] = None,
        rules_engine: Optional[RulesEngine] = None,
        contextual_analyzer: Optional[ContextualAnalyzer] = None,
        risk_scorer: Optional[RiskScorer] = None,
        keyword_sync_service: Optional[KeywordSyncService] = None,
        settings: Optional[Settings] = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.keyword_sync = keyword_sync_service or get_keyword_sync_service()
        self.repository = repository or get_conversation_repository()
        self.rules_engine = rules_engine or RulesEngine(
            settings=self.settings, keyword_sync_service=self.keyword_sync
        )
        self.contextual_analyzer = contextual_analyzer or ContextualAnalyzer(
            settings=self.settings
        )
        self.risk_scorer = risk_scorer or RiskScorer(settings=self.settings)

    def analyze_standalone_transcript(
        self, request: TranscriptAnalysisRequest
    ) -> ScamRiskAssessment:
        """Analyses a single transcript (with optional conversation history)."""
        rule_res, _ = self.rules_engine.evaluate(
            request.transcript,
            start_seconds=request.start_seconds,
            end_seconds=request.end_seconds,
            call_id=request.call_id,
        )
        ctx_res = self.contextual_analyzer.analyze(
            request.transcript, conversation_history=request.conversation_history
        )
        return self.risk_scorer.score(
            rule_result=rule_res,
            contextual_result=ctx_res,
            transcript_confidence=request.transcript_confidence,
            start_seconds=request.start_seconds,
            end_seconds=request.end_seconds,
            sync_status=self.keyword_sync.get_sync_status(),
        )

    def process_segment(
        self, call_id: str, segment: CallSegmentRequest
    ) -> CallSegmentUpdateResponse:
        """
        Processes a new transcript segment for `call_id`, updates cumulative conversation
        state without double-counting duplicate evidence, and returns the updated risk assessment.
        """
        state = self.repository.get_or_create(call_id)

        # Evaluate new segment against rules engine, passing `state.seen_rule_keys`
        # so repeated evidence across segments is skipped rather than double-counted.
        segment_rule_res, updated_seen_keys = self.rules_engine.evaluate(
            segment.text,
            start_seconds=segment.start_seconds,
            end_seconds=segment.end_seconds,
            already_seen_keys=state.seen_rule_keys,
            call_id=call_id,
        )
        state.seen_rule_keys = updated_seen_keys
        state.total_duplicates_skipped += segment_rule_res.duplicate_indicators_skipped

        for ind in segment_rule_res.triggered_indicators:
            state.accumulated_indicators.append(ind)
        for sup in segment_rule_res.suppressed_protective_matches:
            if sup not in state.suppressed_protective_matches:
                state.suppressed_protective_matches.append(sup)
        for skw in segment_rule_res.synced_keywords_matched:
            if skw not in state.synced_keywords_hit:
                state.synced_keywords_hit.append(skw)

        # Recompute cumulative rule score across all unique indicators in this call
        if not state.accumulated_indicators:
            cumulative_rule_score = 0.0
        else:
            complement = 1.0
            for item in state.accumulated_indicators:
                complement *= max(0.0, 1.0 - min(0.95, item.weight))
            cumulative_rule_score = round(min(1.0, 1.0 - complement), 4)

        cumulative_rule_result = RuleEngineResult(
            rule_score=cumulative_rule_score,
            triggered_indicators=list(state.accumulated_indicators),
            suppressed_protective_matches=list(state.suppressed_protective_matches),
            duplicate_indicators_skipped=state.total_duplicates_skipped,
            synced_keywords_matched=list(state.synced_keywords_hit),
        )

        # Evaluate Contextual Director with prior utterances + current segment
        contextual_result = self.contextual_analyzer.analyze(
            segment.text, conversation_history=state.recent_utterances
        )

        # Keep rolling history window bounded
        state.recent_utterances.append(segment.text)
        if len(state.recent_utterances) > 12:
            state.recent_utterances = state.recent_utterances[-12:]

        assessment = self.risk_scorer.score(
            rule_result=cumulative_rule_result,
            contextual_result=contextual_result,
            transcript_confidence=segment.transcript_confidence,
            start_seconds=segment.start_seconds,
            end_seconds=segment.end_seconds,
            sync_status=self.keyword_sync.get_sync_status(),
        )

        seq_num = len(state.segments) + 1
        segment_id = f"seg_{seq_num:03d}_{uuid.uuid4().hex[:6]}"
        seg_record = CallSegmentRecord(
            segment_id=segment_id,
            sequence_number=seq_num,
            speaker=segment.speaker,
            language_code=segment.language_code,
            start_seconds=segment.start_seconds,
            end_seconds=segment.end_seconds,
            transcript_confidence=segment.transcript_confidence,
            detected_indicators=[
                i.keyword_or_pattern for i in segment_rule_res.triggered_indicators
            ],
            risk_level_at_segment=assessment.risk_level,
            risk_score_at_segment=assessment.risk_score,
            caption_at_segment=assessment.caption,
            processed_at=round(time.time(), 3),
        )

        state.segments.append(seg_record)
        if len(state.segments) > self.settings.max_segments_per_call:
            state.segments = state.segments[-self.settings.max_segments_per_call :]

        state.latest_assessment = assessment
        self.repository.save(state)

        return CallSegmentUpdateResponse(
            call_id=call_id,
            segment_id=segment_id,
            sequence_number=seq_num,
            duplicate_evidence_suppressed=segment_rule_res.duplicate_indicators_skipped,
            synced_keywords_triggered=list(segment_rule_res.synced_keywords_matched),
            assessment=assessment,
        )

    def get_latest_risk(self, call_id: str) -> Optional[ScamRiskAssessment]:
        state = self.repository.get(call_id)
        if state is None:
            return None
        return state.latest_assessment

    def get_history(self, call_id: str) -> Optional[CallHistoryResponse]:
        state = self.repository.get(call_id)
        if state is None:
            return None
        return CallHistoryResponse(
            call_id=state.call_id,
            created_at=state.created_at,
            updated_at=state.updated_at,
            expires_at=state.expires_at,
            retention_seconds=state.retention_seconds,
            segment_count=len(state.segments),
            unique_indicators=[
                f"{i.category}:{i.keyword_or_pattern}" for i in state.accumulated_indicators
            ],
            synced_keywords_hit=list(state.synced_keywords_hit),
            segments=list(state.segments),
            latest_assessment=state.latest_assessment,
        )

    def clear_call(self, call_id: str) -> Optional[CallClearResponse]:
        existed = self.repository.delete(call_id)
        if not existed:
            return None
        return CallClearResponse(
            call_id=call_id,
            cleared=True,
            message=f"Stored conversation state and history for call '{call_id}' cleared.",
        )
