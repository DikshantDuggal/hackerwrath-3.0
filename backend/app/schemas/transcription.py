"""Pydantic schemas for the Speech-to-Text (Sarvam AI Saaras) module."""
from __future__ import annotations

from typing import List, Optional
from app.core.compat import BaseModel, Field


class TimestampedSegment(BaseModel):
    """A single timestamped utterance segment returned by the STT provider."""

    start_seconds: float = Field(default=0.0, ge=0.0)
    end_seconds: float = Field(default=0.0, ge=0.0)
    text: str = Field(default="")
    speaker: str = Field(default="caller")
    confidence: float = Field(default=0.9, ge=0.0, le=1.0)


class TranscriptionResponse(BaseModel):
    """Structured response returned by POST /transcribe."""

    provider: str = Field(default="sarvam_saaras")
    model: str = Field(default="saaras:v3")
    language_code: str = Field(default="auto")
    transcript: str = Field(default="")
    original_text: Optional[str] = Field(default=None, description="Original un-mutated transcript")
    normalized_text: Optional[str] = Field(default=None, description="Normalized transcript")
    detected_language: Optional[str] = Field(default=None, description="Detected language category")
    detected_script: Optional[str] = Field(default=None, description="Detected script")
    confidence: float = Field(default=0.9, ge=0.0, le=1.0)
    duration_seconds: float = Field(default=0.0, ge=0.0)
    segments: List[TimestampedSegment] = Field(default_factory=list)
    streaming_ready: bool = Field(default=True)
    operational_status: str = Field(default="WORKING")
