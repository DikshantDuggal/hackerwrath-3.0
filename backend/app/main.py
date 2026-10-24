"""
FastAPI Application Entrypoint for the AI-Powered Scam-Call Detection Backend.
Run locally in VS Code / Google Antigravity with:
    uvicorn app.main:app --reload --port 8000
"""
from __future__ import annotations

import sys
if sys.platform == "win32":
    import asyncio
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    except Exception:
        pass

from pathlib import Path
from app.api.routes_analysis import router as analysis_router
from app.api.routes_calls import router as calls_router
from app.api.routes_health import router as health_router
from app.api.routes_live_ingest import router as live_ingest_router
from app.api.routes_livekit_calls import router as livekit_calls_router
from app.api.routes_mobile import router as mobile_router, ws_router as mobile_ws_router
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
            "Telegram Audio Bridge & Ingestion Gateway, and Calibrated Risk Scoring."
        ),
    )

    try:
        from fastapi.middleware.cors import CORSMiddleware
        application.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    except Exception:
        pass

    application.include_router(health_router)
    application.include_router(transcription_router)
    application.include_router(analysis_router)
    application.include_router(calls_router)
    application.include_router(livekit_calls_router)
    application.include_router(livekit_calls_router, prefix="/api")
    application.include_router(telegram_router)
    application.include_router(live_ingest_router)
    application.include_router(rag_router)
    application.include_router(mobile_router)
    application.include_router(mobile_ws_router)

    # Mount compiled frontend dist if available so http://127.0.0.1:8000 serves the UI directly
    dist_dir = Path(__file__).resolve().parent.parent / "dist"
    assets_dir = dist_dir / "assets"
    if dist_dir.exists() and (dist_dir / "index.html").exists():
        try:
            from fastapi.staticfiles import StaticFiles
            if assets_dir.exists():
                application.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")
            application.mount("/", StaticFiles(directory=str(dist_dir), html=True), name="static")
        except Exception:
            pass

    return application


app = create_app()
