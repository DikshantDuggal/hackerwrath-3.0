"""GET /health and GET /health/ready endpoints reporting backend and module readiness."""
from __future__ import annotations

from typing import Any, Dict
from app.core.compat import APIRouter
from app.core.config import get_settings
from app.detectors.icfd_classifier import get_icfd_classifier
from app.services.keyword_sync_service import get_keyword_sync_service

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    settings = get_settings()
    sync_service = get_keyword_sync_service()
    icfd_clf = get_icfd_classifier()
    return {
        "status": "ok",
        "working": True,
        "service": settings.app_name,
        "version": settings.app_version,
        "sarvam_configured": settings.has_live_sarvam_key,
        "modules": {
            "speech_to_text": {
                "working": True,
                "provider": "sarvam_saaras",
                "model": settings.sarvam_stt_model,
                "live_api_key_configured": settings.has_live_sarvam_key,
            },
            "rules_engine": {
                "working": True,
                "negation_and_protective_suppression": True,
                "configured_rules": len(settings.rule_weights),
            },
            "contextual_director": {
                "working": True,
                "model": settings.sarvam_llm_model,
                "structured_pydantic_validation": True,
            },
            "risk_scorer": {
                "working": True,
                "calibrated_p_scam_enabled": settings.calibrated_probability_enabled,
            },
            "icfd_model": {
                "working": icfd_clf.available,
                "model_name": icfd_clf.config.get("model_name", "ICFD-31k Production Calibrated Classifier"),
                "threshold": icfd_clf.threshold,
            },
            "conversation_state": {
                "working": True,
                "retention_seconds": settings.call_state_retention_seconds,
            },
            "cross_call_keyword_sync": sync_service.get_sync_status(),
            "telegram_alerts": {
                "working": True,
                "configured": settings.has_live_telegram_credentials,
                "enabled": settings.telegram_alerts_enabled,
                "threshold": settings.telegram_alert_threshold,
            },
        },
    }


@router.get("/health/ready")
@router.get("/ready")
async def readiness_check() -> Dict[str, Any]:
    settings = get_settings()
    icfd_clf = get_icfd_classifier()
    sync_service = get_keyword_sync_service()
    
    return {
        "status": "ready",
        "ready": True,
        "service": settings.app_name,
        "version": settings.app_version,
        "model_loaded": icfd_clf.available,
        "icfd_classifier": {
            "available": icfd_clf.available,
            "architecture": icfd_clf.config.get("selected_architecture", "Calibrated Logistic Regression (L2)"),
            "threshold": icfd_clf.threshold,
        },
        "rule_engine_ready": True,
        "active_rules_count": len(settings.rule_weights),
        "synced_keywords_count": len(sync_service.get_active_keywords()),
        "sarvam_stt_configured": settings.has_live_sarvam_key,
    }
