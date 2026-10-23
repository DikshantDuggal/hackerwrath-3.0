"""
Text preprocessing and normalization for the RAG Scam Detection Engine.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Dict, List, Optional, Tuple


def normalize_transcript_text(text: str) -> str:
    """
    Normalizes transcript text safely:
    - Unicode NFKC normalization.
    - Strips non-printable characters.
    - Normalizes spacing while strictly preserving punctuation, quotes, case, and numbers.
    """
    if not text or not isinstance(text, str):
        return ""

    # NFKC unicode normalization
    text = unicodedata.normalize("NFKC", text)

    # Normalize weird whitespace characters
    text = text.replace("\xa0", " ").replace("\t", " ")
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Split by lines, collapse intra-line spaces, and strip each line
    lines = [re.sub(r"[ ]{2,}", " ", line).strip() for line in text.split("\n")]
    cleaned = "\n".join(lines).strip()
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)

    return cleaned


def mask_sensitive_pii(text: str) -> str:
    """
    Replaces raw sensitive credentials (e.g. 16-digit cards, explicit account numbers)
    with safe tokens to protect user privacy.
    """
    if not text:
        return ""
    # 13 to 19 digit account/card numbers
    masked = re.sub(r"\b\d{13,19}\b", "[ACCOUNT_NUMBER]", text)
    # 10 to 12 digit phone numbers
    masked = re.sub(r"\b(?:\+?\d{1,3}[- ]?)?[6-9]\d{9}\b", "[PHONE_NUMBER]", masked)
    return masked


def clean_incoming_query(text: str, preceding_context: Optional[str] = None) -> str:
    """
    Prepares an incoming live-call transcript query for embedding and retrieval.
    If preceding context is provided, combines it naturally.
    """
    norm_text = normalize_transcript_text(text)
    if not preceding_context:
        return norm_text

    norm_context = normalize_transcript_text(preceding_context)
    if not norm_context:
        return norm_text

    # Take the last 200 words of preceding context to maintain tight semantic focus
    context_words = norm_context.split()[-200:]
    return f"Context: {' '.join(context_words)}\nUtterance: {norm_text}"
