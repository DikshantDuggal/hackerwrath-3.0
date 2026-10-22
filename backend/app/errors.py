"""One error shape for the whole API: {"error": {"code": ..., "message": ...}}."""

from __future__ import annotations

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message


def error_body(code: str, message: str) -> dict:
    return {"error": {"code": code, "message": message}}


async def api_error_handler(_: Request, exc: ApiError) -> JSONResponse:
    return JSONResponse(status_code=exc.status, content=error_body(exc.code, exc.message))


async def validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    # Field names only; never echo submitted values back.
    fields = sorted({".".join(str(p) for p in err.get("loc", ())[1:]) for err in exc.errors()})
    return JSONResponse(
        status_code=400,
        content=error_body("invalid_request", "Check these fields: " + ", ".join(f for f in fields if f)),
    )
