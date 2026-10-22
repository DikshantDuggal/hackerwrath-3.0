"""
FastAPI Router for optional Telegram Bot Integration, Status, and Webhook Commands.
"""
from __future__ import annotations

from typing import Any, Dict
from app.core.compat import APIRouter, Depends, HTTPException
from app.schemas.analysis import AlertPayload, ScamRiskAssessment
from app.schemas.telegram import (
    TelegramCommandResponse,
    TelegramSendAlertRequest,
    TelegramSendAlertResponse,
    TelegramStatusResponse,
)
from app.services.telegram_service import TelegramAlertService, get_telegram_service

router = APIRouter(prefix="/telegram", tags=["telegram"])


@router.get("/status", response_model=TelegramStatusResponse)
async def get_telegram_status(
    service: TelegramAlertService = Depends(get_telegram_service),
) -> TelegramStatusResponse:
    """Returns the operational and configuration status of the Telegram alert service."""
    return service.get_status()


@router.post("/alert", response_model=TelegramSendAlertResponse)
async def send_manual_alert(
    request: TelegramSendAlertRequest,
    service: TelegramAlertService = Depends(get_telegram_service),
) -> TelegramSendAlertResponse:
    """Dispatches a structured scam risk alert to the configured Telegram chat."""
    mock_assessment = ScamRiskAssessment(
        risk_score=request.risk_score,
        risk_level=request.risk_level,
        caption=request.headline,
        recommended_action=request.safe_action,
        alert=AlertPayload(
            alert_id=f"alt_manual_{request.call_id}",
            triggered=True,
            severity="CRITICAL" if request.risk_level == "CRITICAL" else "WARNING",
            headline=request.headline,
            safe_action=request.safe_action,
        ),
    )
    return service.send_risk_alert(mock_assessment, request.call_id)


@router.post("/webhook", response_model=TelegramCommandResponse)
async def telegram_webhook(
    update: Dict[str, Any],
    service: TelegramAlertService = Depends(get_telegram_service),
) -> TelegramCommandResponse:
    """
    Receives incoming webhook updates from the Telegram Bot API.
    Validates sender authorization and executes bot commands (/status, /help, /latest, /mute).
    """
    if not update:
        raise HTTPException(status_code=400, detail="Empty webhook payload.")
    return service.handle_webhook_update(update)
