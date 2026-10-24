"""Optional acoustic, deepfake, and ICFD trained ML detectors."""
from app.detectors.deepfake_detector import BaseDeepfakeDetector, HeuristicAcousticDeepfakeDetector
from app.detectors.icfd_classifier import IcfdClassifier, IcfdClassificationResult, get_icfd_classifier

__all__ = [
    "BaseDeepfakeDetector",
    "HeuristicAcousticDeepfakeDetector",
    "IcfdClassifier",
    "IcfdClassificationResult",
    "get_icfd_classifier",
]
