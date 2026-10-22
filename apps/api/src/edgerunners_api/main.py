from fastapi import FastAPI
from fastapi.responses import JSONResponse

from edgerunners_contracts import ProtectionState, WarningEvent

app = FastAPI(title="Edgerunners API", version="0.1.0")


@app.get("/healthz")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/readyz", status_code=503)
async def readiness() -> JSONResponse:
    return JSONResponse(
        status_code=503,
        content={
            "state": ProtectionState.UNAVAILABLE,
            "reason": "Call routing, STT, AI and authenticated events are not connected",
        },
    )


@app.get("/api/contracts/warning")
async def warning_schema() -> dict:
    return WarningEvent.model_json_schema()
