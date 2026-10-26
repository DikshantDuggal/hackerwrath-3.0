"""
Multilingual Regression Test Suite.
Validates:
1. All 7 distinct language and script categories:
   - english (Latin)
   - hindi_devanagari (Devanagari)
   - hinglish (Latin)
   - punjabi_gurmukhi (Gurmukhi)
   - punjabi_latin (Latin)
   - hindi_mixed (Mixed)
   - punjabi_mixed (Mixed)
2. Casual conversational greetings across all languages returning LOW risk (score 0.0).
3. Protective security advice ("OTP kisi ko mat dena", Gurmukhi/Punjabi equivalents) suppressed to LOW risk.
4. Scam solicitations across all 7 categories flagged as HIGH or CRITICAL risk (>= 75.0).
5. Non-destructive text preservation (original_text preserved exactly without overwriting).
"""
from __future__ import annotations

import unittest
from app.services.language_detector import get_language_detector, LanguageDetector
from app.detectors.sensitive_info_detector import SensitiveInfoDetector
from app.services.conversation_manager import ConversationManager
from app.schemas.analysis import TranscriptAnalysisRequest
from app.services.transcription_service import SarvamSaarasProvider


class TestMultilingualPipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.detector = get_language_detector()
        cls.conv_manager = ConversationManager()
        cls.sensitive_detector = SensitiveInfoDetector()

    # -------------------------------------------------------------------------
    # 1. LANGUAGE & SCRIPT CLASSIFICATION (7 CATEGORIES)
    # -------------------------------------------------------------------------

    def test_category_1_english_latin(self):
        text = "Hello, this is a legitimate call regarding your delivery schedule."
        res = self.detector.detect(text)
        self.assertEqual(res.detected_language, "english")
        self.assertEqual(res.detected_script, "Latin")
        self.assertEqual(res.original_text, text)

    def test_category_2_hindi_devanagari(self):
        text = "आप कैसे हैं, क्या सब कुशल मंगल है?"
        res = self.detector.detect(text)
        self.assertEqual(res.detected_language, "hindi_devanagari")
        self.assertEqual(res.detected_script, "Devanagari")
        self.assertEqual(res.original_text, text)

    def test_category_3_hinglish_latin(self):
        text = "aap kaise hai, kya chal raha hai aajkal?"
        res = self.detector.detect(text)
        self.assertEqual(res.detected_language, "hinglish")
        self.assertEqual(res.detected_script, "Latin")
        self.assertEqual(res.original_text, text)

    def test_category_4_punjabi_gurmukhi(self):
        text = "ਤੁਸੀਂ ਕਿਵੇਂ ਹੋ, ਸਭ ਠੀਕ ਠਾਕ ਹੈ ਨਾ?"
        res = self.detector.detect(text)
        self.assertEqual(res.detected_language, "punjabi_gurmukhi")
        self.assertEqual(res.detected_script, "Gurmukhi")
        self.assertEqual(res.original_text, text)

    def test_category_5_punjabi_latin(self):
        text = "tussi kive ho paaji, ki haal chaal hai?"
        res = self.detector.detect(text)
        self.assertEqual(res.detected_language, "punjabi_latin")
        self.assertEqual(res.detected_script, "Latin")
        self.assertEqual(res.original_text, text)

    def test_category_6_hindi_mixed(self):
        text = "कृपया अपना bank account verify करें और OTP मत बताना"
        res = self.detector.detect(text)
        self.assertEqual(res.detected_language, "hindi_mixed")
        self.assertEqual(res.detected_script, "Mixed")
        self.assertEqual(res.original_text, text)

    def test_category_7_punjabi_mixed(self):
        text = "ਤੁਹਾਡਾ bank account block ਹੋ ਜਾਵੇਗਾ, ਕਿਰਪਾ ਕਰਕੇ ਧਿਆਨ ਦਿਓ"
        res = self.detector.detect(text)
        self.assertEqual(res.detected_language, "punjabi_mixed")
        self.assertEqual(res.detected_script, "Mixed")
        self.assertEqual(res.original_text, text)

    # -------------------------------------------------------------------------
    # 2. CONVERSATIONAL GREETINGS (LOW RISK, SCORE 0.0)
    # -------------------------------------------------------------------------

    def test_conversational_greetings_low_risk(self):
        conversational_samples = [
            ("aap kaise hai", "hinglish", "Latin"),
            ("aap kaise ho", "hinglish", "Latin"),
            ("आप कैसे हैं", "hindi_devanagari", "Devanagari"),
            ("ਤੁਸੀਂ ਕਿਵੇਂ ਹੋ", "punjabi_gurmukhi", "Gurmukhi"),
            ("tussi kive ho", "punjabi_latin", "Latin"),
            ("sat sri akaal ji tussi kivein ho", "punjabi_latin", "Latin"),
            ("bhai kya kar raha hai", "hinglish", "Latin"),
            ("Hello, how are you today?", "english", "Latin"),
        ]
        for text, exp_lang, exp_script in conversational_samples:
            with self.subTest(sample=text):
                det = self.detector.detect(text)
                self.assertTrue(det.is_conversational, f"Expected is_conversational=True for '{text}'")
                self.assertEqual(det.detected_language, exp_lang)
                self.assertEqual(det.detected_script, exp_script)

                req = TranscriptAnalysisRequest(transcript=text)
                assessment = self.conv_manager.analyze_standalone_transcript(req)
                self.assertEqual(assessment.risk_level, "LOW")
                self.assertEqual(assessment.risk_score, 0.0)
                self.assertEqual(assessment.original_text, text)

    # -------------------------------------------------------------------------
    # 3. PROTECTIVE ADVICE SUPPRESSION
    # -------------------------------------------------------------------------

    def test_protective_advice_across_languages(self):
        protective_samples = [
            ("apna OTP kisi ko mat dena", "hinglish"),
            ("OTP kisi ko mat dena", "hinglish"),
            ("kabhi bhi kisi ko apna OTP mat batana", "hinglish"),
            ("kise nu vi apna OTP na dasso", "punjabi_latin"),
            ("apna otp kise nu na daso", "punjabi_latin"),
            ("ਓਟੀਪੀ ਕਿਸੇ ਨੂੰ ਨਾ ਦਿਓ", "punjabi_gurmukhi"),
            ("ਕਿਸੇ ਨੂੰ ਆਪਣਾ ਓਟੀਪੀ ਨਾ ਦੱਸੋ", "punjabi_gurmukhi"),
            ("अपना ओटीपी किसी को मत देना", "hindi_devanagari"),
            ("Never share your OTP with anyone on call", "english"),
        ]
        for text, exp_lang in protective_samples:
            with self.subTest(protective=text):
                sens = self.sensitive_detector.detect(text)
                self.assertTrue(sens.is_protective_warning, f"Expected protective warning for '{text}'")
                self.assertFalse(sens.is_solicitation, f"Protective text should not be solicitation: '{text}'")

                req = TranscriptAnalysisRequest(transcript=text)
                assessment = self.conv_manager.analyze_standalone_transcript(req)
                self.assertEqual(assessment.risk_level, "LOW")
                self.assertEqual(assessment.risk_score, 0.0)
                self.assertEqual(assessment.detected_language, exp_lang)
                self.assertEqual(assessment.original_text, text)
                self.assertTrue(len(assessment.counter_evidence) > 0)

    # -------------------------------------------------------------------------
    # 4. HIGH-RISK SCAM SOLICITATION DETECTION
    # -------------------------------------------------------------------------

    def test_scam_solicitations_across_languages(self):
        scam_samples = [
            ("apna OTP batao warna account block ho jayega", "hinglish", 85.0),
            ("tuhada account block ho jaavega apna otp daso", "punjabi_latin", 85.0),
            ("ਤੁਹਾਡਾ ਅਕਾਊਂਟ ਬਲਾਕ ਹੋ ਜਾਵੇਗਾ ਆਪਣਾ ਓਟੀਪੀ ਦੱਸੋ", "punjabi_gurmukhi", 85.0),
            ("आपका बैंक खाता ब्लॉक हो जाएगा तुरंत ओटीपी बताएं", "hindi_devanagari", 85.0),
            ("Your bank account is suspended immediately disclose your verification OTP", "english", 85.0),
        ]
        for text, exp_lang, min_score in scam_samples:
            with self.subTest(scam=text):
                req = TranscriptAnalysisRequest(transcript=text)
                assessment = self.conv_manager.analyze_standalone_transcript(req)
                self.assertIn(assessment.risk_level, ("HIGH", "CRITICAL"))
                self.assertGreaterEqual(assessment.risk_score, min_score)
                self.assertEqual(assessment.detected_language, exp_lang)
                self.assertEqual(assessment.original_text, text)

    # -------------------------------------------------------------------------
    # 5. TEXT PRESERVATION & TRANSCRIPTION SERVICE
    # -------------------------------------------------------------------------

    def test_transcription_service_preservation(self):
        provider = SarvamSaarasProvider()
        test_payload = b"RIFF....WAVEfmt ....data....TRANSCRIPT: tussi kive ho paaji"
        resp = provider.transcribe_bytes(test_payload, filename="test.wav", language_code="auto")
        self.assertEqual(resp.original_text, "tussi kive ho paaji")
        self.assertEqual(resp.detected_language, "punjabi_latin")
        self.assertEqual(resp.detected_script, "Latin")
        self.assertEqual(resp.transcript, "tussi kive ho paaji")


if __name__ == "__main__":
    unittest.main()
