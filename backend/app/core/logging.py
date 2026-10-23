"""
Privacy-safe structured logging utility.
By default (LOG_SENSITIVE_TRANSCRIPTS=false), raw transcript content is never written to logs.
"""
from __future__ import annotations

import logging
from typing import Any, Dict
from app.core.config import get_settings


def get_logger(name: str = "scam_detector") -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


def sanitize_log_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Redacts transcript text from log dictionaries unless explicitly enabled."""
    settings = get_settings()
    if settings.log_sensitive_transcripts:
        return dict(payload)

    redacted: Dict[str, Any] = {}
    sensitive_keys = {"transcript", "text", "excerpt", "raw_text", "utterance"}
    for key, val in payload.items():
        if key.lower() in sensitive_keys and isinstance(val, str):
            redacted[key] = f"<REDACTED len={len(val)}>"
        else:
            redacted[key] = val
    return redacted
