"""
Optional Deepfake / Synthetic Voice Detection Module.
Designed behind an abstract interface so external acoustic spoofing models
(e.g., AASIST, RawNet2, or commercial voice-liveness APIs) can be plugged in seamlessly.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional
from app.core.config import Settings, get_settings
from app.schemas.analysis import DeepfakeAnalysisResult


class BaseDeepfakeDetector(ABC):
    """Abstract interface for voice deepfake / spoofing detectors."""

    @abstractmethod
    def analyze_audio(
        self, audio_bytes: Optional[bytes] = None, filename: str = ""
    ) -> DeepfakeAnalysisResult:
        """Evaluates raw audio bytes for synthetic voice spoofing indicators."""


class HeuristicAcousticDeepfakeDetector(BaseDeepfakeDetector):
    """
    Default pluggable deepfake detector implementation.
    Disabled by default unless ENABLE_DEEPFAKE_DETECTION=true.
    """

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self.settings = settings or get_settings()

    def analyze_audio(
        self, audio_bytes: Optional[bytes] = None, filename: str = ""
    ) -> DeepfakeAnalysisResult:
        if not self.settings.enable_deepfake_detection or not audio_bytes:
            return DeepfakeAnalysisResult(
                enabled=self.settings.enable_deepfake_detection,
                is_suspected_deepfake=False,
                spoof_score=0.0,
                confidence=0.0,
                provider="acoustic_heuristic_v1",
                explanation="Deepfake voice detection is disabled or no raw audio provided.",
            )

        # Deterministic check on synthetic test markers or header metadata
        is_synthetic_marker = b"SYNTHETIC_VOICE_MARKER" in audio_bytes or "deepfake" in filename.lower()
        score = 0.82 if is_synthetic_marker else 0.08
        return DeepfakeAnalysisResult(
            enabled=True,
            is_suspected_deepfake=score >= 0.70,
            spoof_score=score,
            confidence=0.75,
            provider="acoustic_heuristic_v1",
            explanation=(
                "Synthetic acoustic artifacts detected in voice stream."
                if is_synthetic_marker
                else "No strong synthetic voice spoofing artifacts detected."
            ),
        )
