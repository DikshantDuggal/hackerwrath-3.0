"""POST /transcribe endpoint for uploading and transcribing audio files via Sarvam Saaras."""
from __future__ import annotations

from app.core.compat import APIRouter, Depends, File, Form, HTTPException, UploadFile
from app.schemas.transcription import TranscriptionResponse
from app.services.transcription_service import (
    BaseSpeechToTextProvider,
    SarvamSaarasProvider,
    TranscriptionUpstreamError,
    TranscriptionValidationError,
)

router = APIRouter(tags=["transcription"])

_default_stt_provider = SarvamSaarasProvider()


def get_stt_provider() -> BaseSpeechToTextProvider:
    return _default_stt_provider


@router.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe_audio(
    file: UploadFile = File(...),
    language_code: str = Form("auto"),
    stt_provider: BaseSpeechToTextProvider = Depends(get_stt_provider),
) -> TranscriptionResponse:
    if file is None:
        raise HTTPException(status_code=400, detail="Audio file is required.")

    audio_bytes = await file.read()
    filename = getattr(file, "filename", None) or "audio.wav"

    try:
        return stt_provider.transcribe_bytes(
            audio_bytes=audio_bytes,
            filename=filename,
            language_code=language_code,
        )
    except TranscriptionValidationError as val_err:
        raise HTTPException(
            status_code=val_err.status_code, detail=val_err.message
        ) from val_err
    except TranscriptionUpstreamError as up_err:
        raise HTTPException(
            status_code=up_err.status_code, detail=up_err.message
        ) from up_err
