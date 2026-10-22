"""
Automated unit tests for RAG data preprocessing and text normalization.
"""
from __future__ import annotations

import unittest
from app.rag.preprocessing import (
    clean_incoming_query,
    mask_sensitive_pii,
    normalize_transcript_text,
)


class RAGPreprocessingTestSuite(unittest.TestCase):
    """Verifies safe text normalization, PII masking, and context assembly."""

    def test_01_whitespace_and_unicode_normalization(self) -> None:
        raw = "Hello   world!\r\n\r\n\r\n\tThis is\xa0a test."
        cleaned = normalize_transcript_text(raw)
        self.assertEqual(cleaned, "Hello world!\n\nThis is a test.")

    def test_02_empty_and_trivial_inputs(self) -> None:
        self.assertEqual(normalize_transcript_text(""), "")
        self.assertEqual(normalize_transcript_text("   \n\t  "), "")
        self.assertEqual(normalize_transcript_text(None), "")  # type: ignore

    def test_03_preserves_conversational_punctuation_and_numbers(self) -> None:
        text = "Speaker1: Sir, did you request $500 transfer? (Yes/No) Account: 1234."
        cleaned = normalize_transcript_text(text)
        self.assertIn("Speaker1:", cleaned)
        self.assertIn("$500", cleaned)
        self.assertIn("(Yes/No)", cleaned)

    def test_04_mask_sensitive_pii_preserves_text_structure(self) -> None:
        text_with_pii = "My account is 1234567890123456 and call me at +91 9876543210."
        masked = mask_sensitive_pii(text_with_pii)
        self.assertNotIn("1234567890123456", masked)
        self.assertIn("[ACCOUNT_NUMBER]", masked)
        self.assertIn("[PHONE_NUMBER]", masked)

    def test_05_clean_incoming_query_with_context(self) -> None:
        utterance = "Why do you need my OTP?"
        context = "Speaker1: Hello, this is your bank.\nSpeaker2: Yes, what happened?"
        assembled = clean_incoming_query(utterance, preceding_context=context)
        self.assertTrue(assembled.startswith("Context:"))
        self.assertIn("Utterance: Why do you need my OTP?", assembled)

    def test_06_clean_incoming_query_without_context(self) -> None:
        utterance = "Why do you need my OTP?"
        assembled = clean_incoming_query(utterance, preceding_context=None)
        self.assertEqual(assembled, "Why do you need my OTP?")


if __name__ == "__main__":
    unittest.main()
