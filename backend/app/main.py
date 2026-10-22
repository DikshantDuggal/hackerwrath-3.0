"""
FastAPI Application Entrypoint for the AI-Powered Scam-Call Detection Backend.
Run locally in VS Code / Google Antigravity with:
    uvicorn app.main:app --reload --port 8000
"""
from __future__ import annotations

from app.api.routes_analysis import router as analysis_router
from app.api.routes_calls import router as calls_router
from app.api.routes_health import router as health_router
from app.api.routes_live_ingest import router as live_ingest_router
from app.api.routes_rag import router as rag_router
from app.api.routes_telegram import router as telegram_router
from app.api.routes_transcription import router as transcription_router
from app.core.compat import FastAPI
from app.core.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "Backend-only AI-powered multilingual scam-call detection system "
            "combining Sarvam AI Saaras STT, negation-aware Rule-Based Engine, "
            "Contextual AI Director, Cross-Call Keyword Synchronization, "
            "Optional Telegram Alerts, and Calibrated Risk Scoring."
        ),
    )

    application.include_router(health_router)
    application.include_router(transcription_router)
    application.include_router(analysis_router)
    application.include_router(calls_router)
    application.include_router(telegram_router)
    application.include_router(live_ingest_router)
    application.include_router(rag_router)
    return application


app = create_app()
