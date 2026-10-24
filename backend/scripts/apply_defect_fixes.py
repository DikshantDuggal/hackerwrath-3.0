"""
Applies root-cause fixes for:
1. Protective advice flagged as scam solicitation.
2. Contamination of subsequent calls and ordinary utterances.
3. Duplicate event dispatches and missing deterministic eventId.
"""
import re

def fix_sensitive_info_detector():
    p = r"D:\edgerunner guardian frontend\backend\app\detectors\sensitive_info_detector.py"
    with open(p, "r", encoding="utf-8") as f:
        content = f.read().replace("\r\n", "\n")

    if "share\\s+mat\\s+(?:karna|karein|karo|kijiye)" in content:
        print("sensitive_info_detector.py already updated")
        return

    old_target = """    r"kisi\s+ke\s+saath\s+(?:otp|pin|password|code)?\s*(?:share\s+)?mat\s+(?:karna|karein|share)|"
    r"(?:otp|pin|password)\s+(?:kisi\s+ko\s+)?mat\s+(?:batana|batao|dena|share)|"
    r"(?:otp|pin)\s+(?:kisi\s+ko\s+)?na\s+(?:dasso|do|dena|batao)|"
    r"kise\s+nu\s+(?:bhi\s+)?(?:otp|pin|password)?\s*na\s+(?:dasso|do|share)|"
    r"bank\s+kabhi\s+(?:bhi\s+)?(?:otp|pin|password)\s+nahi\s+maangta|"""

    replacement = """    r"kisi\s+ke\s+(?:saath|sath)\s+(?:bhi\s+)?(?:otp|pin|password|code)?\s*(?:share\s+)?mat\s+(?:karna|karein|karo|kijiye|share)|"
    r"kisi\s+se\s+(?:bhi\s+)?(?:otp|pin|password|code)?\s*(?:share\s+)?mat\s+(?:karna|karein|karo|kijiye|share)|"
    r"kisi\s+ko\s+(?:bhi\s+)?(?:otp|pin|password|code)?\s*mat\s+(?:batana|batao|dena|share|karna)|"
    r"share\s+mat\s+(?:karna|karein|karo|kijiye)|"
    r"share\s+na\s+(?:karein|karna|karo)|"
    r"mat\s+share\s+(?:karna|karo|karein)|"
    r"kabhi\s+(?:bhi\s+)?share\s+mat|"
    r"(?:otp|pin|password|code)\s+(?:kisi\s+ko\s+|kisi\s+ke\s+(?:saath|sath)\s+)?mat\s+(?:batana|batao|dena|share|karna)|"
    r"(?:otp|pin)\s+(?:kisi\s+ko\s+)?na\s+(?:dasso|do|dena|batao)|"
    r"kise?\s+nu\s+(?:bhi\s+)?(?:otp|pin|password)?\s*na\s+(?:dasso|do|share|karna|karo)|"
    r"kisi\s+naal\s+(?:bhi\s+)?(?:otp|pin|password)?\s*na\s+(?:dasso|do|share|karna|karo)|"
    r"bank\s+kabhi\s+(?:bhi\s+)?(?:otp|pin|password)\s+nahi\s+maangta|"""

    norm_target = old_target.replace("\r\n", "\n")
    norm_replacement = replacement.replace("\r\n", "\n")
    if norm_target in content:
        content = content.replace(norm_target, norm_replacement, 1)

    old_devanagari = 'r"बैंक\\s+कभी\\s+(?:भी\\s+)?ओटीपी\\s+नहीं\\s+मांगता|किसी\\s+को\\s+ओटीपी\\s+मत\\s+दीजिए|"'
    new_devanagari = 'r"बैंक\\s+कभी\\s+(?:भी\\s+)?ओटीपी\\s+नहीं\\s+मांगता|किसी\\s+को\\s+ओटीपी\\s+मत\\s+दीजिए|शेयर\\s+मत\\s+करना|साझा\\s+मत\\s+करें|"'
    if old_devanagari in content:
        content = content.replace(old_devanagari, new_devanagari, 1)

    old_gurmukhi = 'r"ਓਟੀਪੀ\\s+ਨਾ\\s+ਦੱਸੋ|ਕਦੇ\\s+ਵੀ\\s+ਓਟੀਪੀ\\s+ਸਾਂਝਾ\\s+ਨਾ\\s+ਕਰੋ|ਪਿੰਨ\\s+ਨਾ\\s+ਦੱਸੋ|ਬੈਂਕ\\s+ਕਦੇ\\s+ਵੀ\\s+ਓਟੀਪੀ\\s+ਨਹੀਂ\\s+ਮੰਗਦਾ"'
    new_gurmukhi = 'r"ਓਟੀਪੀ\\s+ਨਾ\\s+ਦੱਸੋ|ਕਦੇ\\s+ਵੀ\\s+ਓਟੀਪੀ\\s+ਸਾਂਝਾ\\s+ਨਾ\\s+ਕਰੋ|ਪਿੰਨ\\s+ਨਾ\\s+ਦੱਸੋ|ਬੈਂਕ\\s+ਕਦੇ\\s+ਵੀ\\s+ਓਟੀਪੀ\\s+ਨਹੀਂ\\s+ਮੰਗਦਾ|ਸ਼ੇਅਰ\\s+ਨਾ\\s+ਕਰੋ"'
    if old_gurmukhi in content:
        content = content.replace(old_gurmukhi, new_gurmukhi, 1)

    with open(p, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)
    print("Fixed sensitive_info_detector.py")


def fix_rules_engine():
    p = r"D:\edgerunner guardian frontend\backend\app\services\rules_engine.py"
    with open(p, "r", encoding="utf-8") as f:
        content = f.read().replace("\r\n", "\n")

    if "get_sensitive_info_detector" in content:
        print("rules_engine.py already updated")
        return

    content = content.replace(
        "from app.schemas.calls import (",
        "from app.detectors.sensitive_info_detector import get_sensitive_info_detector\nfrom app.schemas.calls import (",
        1
    )

    old_target = '    ("kisi ke saath otp share na karein", "Hindi protective advice"),'
    replacement = """    ("kisi ke saath otp share na karein", "Hindi protective advice"),
    ("kisi ke saath share mat karna", "Hindi protective advice against sharing"),
    ("kisi ke sath share mat karna", "Hindi protective advice against sharing"),
    ("kisi ke saath share mat", "Hindi protective advice against sharing"),
    ("kisi ke sath share mat", "Hindi protective advice against sharing"),
    ("share mat karna", "Hindi protective advice against sharing"),
    ("share mat karo", "Hindi protective advice against sharing"),
    ("share mat kijiye", "Hindi protective advice against sharing"),
    ("kisi ko bhi share mat karna", "Hindi protective advice"),
    ("kisi se share mat karna", "Hindi protective advice"),
    ("share na karein", "Hindi protective advice"),
    ("mat share karna", "Hindi protective advice"),
    ("kabhi share mat karna", "Hindi protective advice"),
    ("kisi nu share na karo", "Punjabi protective advice against sharing"),
    ("kisi nu share na karna", "Punjabi protective advice against sharing"),
    ("kisi naal share na karo", "Punjabi protective advice against sharing"),
    ("शेयर मत करना", "Hindi protective advice in Devanagari"),
    ("ਸ਼ੇਅਰ ਨਾ ਕਰੋ", "Punjabi protective advice in Gurmukhi"),"""

    if old_target in content:
        content = content.replace(old_target, replacement, 1)

    old_eval_check = """            # 1. Check if this clause is protective advice or a legitimate buyer payment offer
            matched_protective = False
            for prot_phrase, prot_reason in PROTECTIVE_OR_LEGITIMATE_PATTERNS:
                if normalise_text(prot_phrase) in norm_clause:
                    # Ensure the same clause isn't simultaneously commanding "ab otp batao"
                    if "ab otp batao" not in norm_clause and "tell me the code" not in norm_clause:
                        suppressed_protective.append(f"{prot_phrase} ({prot_reason})")
                        matched_protective = True
                        break

            if matched_protective:
                continue"""

    new_eval_check = """            # 1. Check if this clause is protective advice or a legitimate buyer payment offer
            matched_protective = False
            sens_check = get_sensitive_info_detector().detect(clause)
            if (sens_check.is_protective_warning or sens_check.is_educational_discussion) and "ab otp batao" not in norm_clause and "tell me the code" not in norm_clause:
                suppressed_protective.append(f"{sens_check.explanation}")
                matched_protective = True
            else:
                for prot_phrase, prot_reason in PROTECTIVE_OR_LEGITIMATE_PATTERNS:
                    if normalise_text(prot_phrase) in norm_clause:
                        # Ensure the same clause isn't simultaneously commanding "ab otp batao"
                        if "ab otp batao" not in norm_clause and "tell me the code" not in norm_clause:
                            suppressed_protective.append(f"{prot_phrase} ({prot_reason})")
                            matched_protective = True
                            break

            if matched_protective:
                continue"""

    if old_eval_check in content:
        content = content.replace(old_eval_check, new_eval_check, 1)

    with open(p, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)
    print("Fixed rules_engine.py")


def fix_contextual_analyzer():
    p = r"D:\edgerunner guardian frontend\backend\app\services\contextual_analyzer.py"
    with open(p, "r", encoding="utf-8") as f:
        content = f.read().replace("\r\n", "\n")

    if "get_sensitive_info_detector" in content:
        print("contextual_analyzer.py already updated")
        return

    content = content.replace(
        "from app.services.rules_engine import (",
        "from app.detectors.sensitive_info_detector import get_sensitive_info_detector\nfrom app.services.rules_engine import (",
        1
    )

    old_prot = """        # Detect protective advice or legitimate payment context
        is_protective_otp = (
            any(
                p in norm
                for p in (
                    "never share your otp",
                    "never share otp",
                    "do not share your otp",
                    "don't share your otp",
                    "never share your pin",
                    "bank will never ask",
                    "otp mat batana",
                    "kisi ko otp mat",
                    "ओटीपी मत बताना",
                    "कभी भी ओटीपी साझा न करें",
                    "ਓਟੀਪੀ ਨਾ ਦੱਸੋ",
                )
            )
            and "ab otp batao" not in norm
            and "tell me the code" not in norm
        )"""

    new_prot = """        # Detect protective advice or legitimate payment context
        sens_info = get_sensitive_info_detector().detect(current_text)
        is_protective_otp = (
            sens_info.is_protective_warning
            or any(
                p in norm
                for p in (
                    "never share your otp",
                    "never share otp",
                    "do not share your otp",
                    "don't share your otp",
                    "never share your pin",
                    "bank will never ask",
                    "otp mat batana",
                    "kisi ko otp mat",
                    "kisi ke saath share mat",
                    "kisi ke sath share mat",
                    "share mat karna",
                    "share mat karo",
                    "share na karein",
                    "kisi nu share na",
                    "ओटीपी मत बताना",
                    "कभी भी ओटीपी साझा न करें",
                    "ਓਟੀਪੀ ਨਾ ਦੱਸੋ",
                    "ਸ਼ੇਅਰ ਨਾ ਕਰੋ",
                )
            )
        ) and "ab otp batao" not in norm and "tell me the code" not in norm"""

    if old_prot in content:
        content = content.replace(old_prot, new_prot, 1)

    old_caption = 'contextual_caption="Protective security reminder or legitimate payment coordination detected",'
    new_caption = 'contextual_caption="Protective security reminder detected: Warning never to share credentials or OTP" if is_protective_otp else "Legitimate payment coordination detected",'
    if old_caption in content:
        content = content.replace(old_caption, new_caption, 1)

    with open(p, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)
    print("Fixed contextual_analyzer.py")


def fix_risk_scorer():
    p = r"D:\edgerunner guardian frontend\backend\app\services\risk_scorer.py"
    with open(p, "r", encoding="utf-8") as f:
        content = f.read().replace("\r\n", "\n")

    old_prot_block = """        # If purely protective, educational, quoted, or benign notification with no un-negated attack
        if (is_protective or is_educational or is_quoted or is_benign) and not sens_res.is_solicitation:
            expl_msg = ""
            if is_protective:
                expl_msg = "Protective security advice detected warning never to disclose credentials or sensitive information."
            elif is_educational:
                expl_msg = "Educational discussion regarding scam techniques detected without active fraud solicitation."
            elif is_quoted:
                expl_msg = "Quoted/reported speech narrating a past caller attempt detected rather than a live attack."
            elif is_benign:
                expl_msg = "Standard notification or official self-service instruction detected."

            reasons.append(expl_msg)
            alert = self.alert_service.build_alert("LOW", 0.0, [])
            return ScamRiskAssessment(
                risk_score=0.0,
                p_scam=self._compute_calibrated_probability(0.0),
                risk_level="LOW",
                status="success",
                confidence=0.92,
                caption=contextual_result.contextual_caption or "Protective or benign conversation",
                reasons=reasons,
                explanation=expl_msg,
                indicators=indicators,
                evidence=evidence,
                counter_evidence=counter_evidence,
                limitations=limitations,
                recommended_action=(
                    "Continue with normal caution. Never share OTPs, UPI PINs, or passwords with anyone on a phone call. Legitimate organizations will never ask for your secret codes."
                ),
                rule_analysis=rule_result,
                contextual_analysis=contextual_result,
                icfd_analysis=icfd_result,
                deepfake_analysis=deepfake_result,
                alert=alert,
                synchronization_status=sync_status or {"working": True},
            )"""

    new_prot_block = """        # If purely protective, educational, quoted, or benign notification with no un-negated attack
        if (is_protective or is_educational or is_quoted or is_benign) and not sens_res.is_solicitation:
            counter_evidence.extend(sens_res.counter_evidence)
            # Purge any false-positive solicitation indicators and reasons triggered by protective / educational context
            clean_indicators = [
                ind for ind in indicators
                if ind.category not in (
                    "OTP_OR_PIN_REQUEST",
                    "QR_SCAN_TO_RECEIVE_MONEY",
                    "FINANCIAL_SOLICITATION",
                    "REMOTE_ACCESS_OR_SCREEN_SHARE",
                    "SUSPICIOUS_LINK_OR_APK",
                )
            ]
            clean_reasons = [
                r for r in reasons
                if not r.startswith("[OTP_OR_PIN_REQUEST]")
                and "solicitation" not in r.lower()
                and "requested an otp" not in r.lower()
            ]
            expl_msg = ""
            caption_msg = ""
            if is_protective:
                expl_msg = "Protective security advice detected warning never to disclose credentials or sensitive information."
                caption_msg = "Protective security reminder detected: Warning never to share credentials or OTP"
            elif is_educational:
                expl_msg = "Educational discussion regarding scam techniques detected without active fraud solicitation."
                caption_msg = "Educational scam awareness discussion detected"
            elif is_quoted:
                expl_msg = "Quoted/reported speech narrating a past caller attempt detected rather than a live attack."
                caption_msg = "Narrative or quoted reference to a past contact attempt"
            elif is_benign:
                expl_msg = "Standard notification or official self-service instruction detected."
                caption_msg = "Standard system notification or self-service instruction"

            clean_reasons.append(expl_msg)
            alert = self.alert_service.build_alert("LOW", 0.0, [])
            return ScamRiskAssessment(
                risk_score=0.0,
                p_scam=self._compute_calibrated_probability(0.0),
                risk_level="LOW",
                status="success",
                confidence=0.92,
                caption=caption_msg,
                reasons=clean_reasons,
                explanation=expl_msg,
                indicators=clean_indicators,
                evidence=[],
                counter_evidence=counter_evidence,
                limitations=limitations,
                recommended_action=(
                    "Continue with normal caution. Never share OTPs, UPI PINs, or passwords with anyone on a phone call. Legitimate organizations will never ask for your secret codes."
                ),
                rule_analysis=RuleEngineResult(
                    rule_score=0.0,
                    triggered_indicators=clean_indicators,
                    suppressed_protective_matches=rule_result.suppressed_protective_matches,
                    duplicate_indicators_skipped=rule_result.duplicate_indicators_skipped,
                    synced_keywords_matched=[],
                ),
                contextual_analysis=contextual_result,
                icfd_analysis=icfd_result,
                deepfake_analysis=deepfake_result,
                alert=alert,
                synchronization_status=sync_status or {"working": True},
            )"""

    assert old_prot_block in content, "old_prot_block not found in risk_scorer.py"
    content = content.replace(old_prot_block, new_prot_block, 1)

    with open(p, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)
    print("Fixed risk_scorer.py")


def fix_live_audio_processor():
    p = r"D:\edgerunner guardian frontend\backend\app\services\live_audio_processor.py"
    with open(p, "r", encoding="utf-8") as f:
        content = f.read().replace("\r\n", "\n")

    old_payload = """            # Emit progressive caption chunks
            for idx, w_chunk in enumerate(word_chunks):
                self.total_words_emitted += len(w_chunk.split())
                is_last_in_slice = idx == len(word_chunks) - 1

                event_payload = {
                    "type": "caption_chunk",
                    "callId": self.call_id,
                    "channel": ch.channel_id,
                    "speaker": ch.speaker,
                    "text": w_chunk,
                    "fullTranscript": text,
                    "wordCount": len(w_chunk.split()),
                    "isPartial": not is_last_in_slice and not is_final,
                    "isFinal": is_final and is_last_in_slice,
                    "language": stt_res.language_code,
                    "riskScore": seg_assessment.risk_score,
                    "riskLevel": seg_assessment.risk_level,
                    "confidence": seg_assessment.confidence,
                    "transcriptConfidence": stt_res.confidence,
                    "retrievalSimilarity": retrieval_sim,
                    "flaggedKeywords": [
                        i.keyword_or_pattern for i in seg_assessment.rule_analysis.triggered_indicators
                    ],
                    "recommendedAction": seg_assessment.recommended_action,
                    "callRiskScore": cum_assessment.risk_score,
                    "callRiskLevel": cum_assessment.risk_level,
                    "callHasAlert": cum_assessment.risk_level in ("HIGH", "CRITICAL"),
                    "source": self.source,
                    "timestamp": round(time.time(), 3),
                }"""

    new_payload = """            # Emit progressive caption chunks
            for idx, w_chunk in enumerate(word_chunks):
                self.total_words_emitted += len(w_chunk.split())
                is_last_in_slice = idx == len(word_chunks) - 1
                event_id = f"evt_{self.call_id}_ch{ch.channel_id}_{ch.slice_counter}_{idx}"

                event_payload = {
                    "eventId": event_id,
                    "type": "caption_chunk",
                    "callId": self.call_id,
                    "channel": ch.channel_id,
                    "speaker": ch.speaker,
                    "text": w_chunk,
                    "fullTranscript": text,
                    "wordCount": len(w_chunk.split()),
                    "isPartial": not is_last_in_slice and not is_final,
                    "isFinal": is_final and is_last_in_slice,
                    "language": stt_res.language_code,
                    "riskScore": seg_assessment.risk_score,
                    "riskLevel": seg_assessment.risk_level,
                    "caption": seg_assessment.caption,
                    "confidence": seg_assessment.confidence,
                    "transcriptConfidence": stt_res.confidence,
                    "retrievalSimilarity": retrieval_sim,
                    "flaggedKeywords": [
                        i.keyword_or_pattern for i in seg_assessment.rule_analysis.triggered_indicators
                    ],
                    "recommendedAction": seg_assessment.recommended_action,
                    "callRiskScore": cum_assessment.risk_score,
                    "callRiskLevel": cum_assessment.risk_level,
                    "callHasAlert": cum_assessment.risk_level in ("HIGH", "CRITICAL"),
                    "source": self.source,
                    "timestamp": round(time.time(), 3),
                }"""

    if old_payload in content:
        content = content.replace(old_payload, new_payload, 1)

    old_tg_call = """            # Check if Telegram alert should be triggered (based on cumulative call state)
            if (
                cum_assessment.risk_level in ("HIGH", "CRITICAL")
                and self.telegram_service.is_enabled
            ):
                alert_res = self.telegram_service.send_risk_alert(cum_assessment, self.call_id)
                if alert_res.delivered:
                    alert_event = {
                        "type": "telegram_alert_sent",
                        "callId": self.call_id,
                        "channel": ch.channel_id,
                        "speaker": ch.speaker,
                        "messageId": alert_res.message_id,
                        "riskLevel": cum_assessment.risk_level,
                        "riskScore": cum_assessment.risk_score,
                        "timestamp": round(time.time(), 3),
                    }
                    await self.broadcaster.broadcast(alert_event)"""

    new_tg_call = """            # Telegram alert dispatch is handled centrally by conversation_manager.process_segment
            # to eliminate duplicate alert deliveries and ensure atomic deduplication."""

    if old_tg_call in content:
        content = content.replace(old_tg_call, new_tg_call, 1)

    with open(p, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)
    print("Fixed live_audio_processor.py")


if __name__ == "__main__":
    fix_sensitive_info_detector()
    fix_rules_engine()
    fix_contextual_analyzer()
    fix_risk_scorer()
    fix_live_audio_processor()
    print("All defect fixes applied successfully.")
