"""
Telegram Alert & Notification Service for Suraksha Scam-Call Detection.

Features:
- Optional integration: works gracefully when bot token is not configured.
- PII & Sensitive Credential Scrubbing: strips OTPs, PINs, passwords, and sensitive transcripts.
- Incident Deduplication: prevents alert spamming for the same call incident.
- Configurable Risk Thresholds: alerts on HIGH and CRITICAL, suppresses LOW and UNKNOWN.
- Telephony Limitation Warning: clearly states that alerts cannot terminate cellular carrier calls.
- Webhook Command Handling: responds to /status, /help, /latest with strict user authorization.
- Testable Architecture: supports injected `http_transport` for deterministic offline testing.
"""
from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.request
from typing import Any, Callable, Dict, List, Optional, Set

from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.schemas.analysis import RiskLevelType, ScamRiskAssessment
from app.schemas.telegram import (
    TelegramCommandResponse,
    TelegramSendAlertResponse,
    TelegramServiceStatus,
    TelegramStatusResponse,
)

logger = get_logger("scam_detector.telegram_service")


def scrub_sensitive_pii(text: str) -> str:
    """
    Strips OTP codes, passwords, PINs, CVVs, and account digits from text before transmission.
    Guarantees that credentials are never leaked over Telegram notifications.
    """
    if not text:
        return ""
    # Redact 4 to 8 digit numbers (likely OTPs, PINs, or verification codes)
    scrubbed = re.sub(r"\b\d{4,8}\b", "[REDACTED_CODE]", text)
    # Redact 9 to 18 digit numbers (bank accounts, card numbers, Aadhaar)
    scrubbed = re.sub(r"\b\d{9,18}\b", "[REDACTED_NUMBER]", scrubbed)
    # Redact PIN/password assignments
    scrubbed = re.sub(r"(?i)\b(pin|password|cvv|otp|passcode)\s*[:=]\s*\S+", r"\1: [REDACTED]", scrubbed)
    # Redact phone numbers (+91 or 10-digit mobile)
    scrubbed = re.sub(r"(?:\+91[\s-]?)?[6789]\d{9}", "[REDACTED_PHONE]", scrubbed)
    return scrubbed


class TelegramAlertService:
    """Manages optional Telegram alerts, incident deduplication, and webhook commands."""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        http_transport: Optional[Callable[[str, Dict[str, Any]], Dict[str, Any]]] = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.http_transport = http_transport
        self._alerted_incidents: Dict[str, Dict[str, Any]] = {}
        self._total_alerts_sent: int = 0
        self._last_alert_timestamp: Optional[float] = None
        self._last_error: Optional[str] = None
        self._bot_username: Optional[str] = None
        self._alerts_muted: bool = False

    @property
    def is_configured(self) -> bool:
        return self.settings.has_live_telegram_credentials

    @property
    def is_enabled(self) -> bool:
        return (
            self.is_configured
            and self.settings.telegram_alerts_enabled
            and not self._alerts_muted
        )

    def should_alert(self, risk_level: RiskLevelType, risk_score: float) -> bool:
        """Determines if the assessed risk meets the configured Telegram alert threshold."""
        if not self.is_enabled:
            return False

        # Do not send alerts for UNKNOWN or LOW
        if risk_level in ("LOW", "UNKNOWN"):
            return False

        threshold = self.settings.telegram_alert_threshold.upper()
        if threshold == "CRITICAL":
            return risk_level == "CRITICAL" or risk_score >= 80.0
        if threshold == "MEDIUM":
            return risk_level in ("MEDIUM", "HIGH", "CRITICAL") or risk_score >= 30.0

        # Default threshold is HIGH (alerts for both HIGH and CRITICAL, or risk_score >= 60.0)
        return risk_level in ("HIGH", "CRITICAL") or risk_score >= 60.0

    def is_duplicate_incident(
        self,
        call_id: str,
        risk_level: RiskLevelType,
        risk_score: float,
        categories: Set[str],
    ) -> bool:
        """
        Suppresses duplicate alerts for the same call incident unless:
        - The risk escalates to CRITICAL from a lower level, OR
        - A new high-severity category appears, OR
        - 180 seconds have elapsed since the prior alert for this call.
        """
        prev = self._alerted_incidents.get(call_id)
        if prev is None:
            return False

        now = time.time()
        prev_level = prev.get("risk_level")
        prev_score = prev.get("risk_score", 0.0)
        prev_time = prev.get("timestamp", 0.0)
        prev_cats = prev.get("categories", set())

        # If call escalated to CRITICAL from HIGH/MEDIUM, allow escalation alert
        if risk_level == "CRITICAL" and prev_level != "CRITICAL":
            return False

        # If a new severe indicator category appeared, allow update
        if not categories.issubset(prev_cats):
            return False

        # If risk score surged by 20+ points, allow update
        if risk_score - prev_score >= 20.0:
            return False

        # If less than 180 seconds since last alert, suppress duplicate
        if now - prev_time < 180.0:
            return True

        return False

    def build_alert_message(
        self,
        call_id: str,
        risk_level: RiskLevelType,
        risk_score: float,
        headline: str,
        safe_action: str,
        detected_categories: List[str],
        caption: str = "",
    ) -> str:
        """
        Builds a safe, structured Telegram alert message.
        Guarantees that sensitive credentials and full transcripts are NEVER included.
        """
        is_critical = risk_level == "CRITICAL" or risk_score >= 80.0
        icon = "🚨🚨🚨" if is_critical else "⚠️"
        level_str = "CRITICAL EMERGENCY" if is_critical else "HIGH RISK DETECTED"

        cat_bullets = "\n".join(
            [f"• {c.replace('_', ' ').title()}" for c in (detected_categories or ["SUSPICIOUS_CALL_PATTERN"])]
        )

        safe_action_scrubbed = scrub_sensitive_pii(safe_action)
        caption_scrubbed = scrub_sensitive_pii(caption)

        message = (
            f"{icon} <b>SURAKSHA AI SCAM SHIELD</b> {icon}\n\n"
            f"<b>Status:</b> {level_str}\n"
            f"<b>Risk Score:</b> {int(round(risk_score))}/100\n"
            f"<b>Call ID:</b> <code>{scrub_sensitive_pii(call_id)}</code>\n"
            f"<b>Timestamp:</b> {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}\n\n"
            f"<b>🔍 Identified Threat Patterns:</b>\n{cat_bullets}\n\n"
        )

        if caption_scrubbed:
            message += f"<b>Analysis:</b> {caption_scrubbed}\n\n"

        message += (
            f"<b>🛡️ Recommended Protective Action:</b>\n"
            f"<b>{safe_action_scrubbed}</b>\n\n"
            f"<i>⚠️ Telephony Limitation Warning: Suraksha alerts cannot disconnect or mute "
            f"cellular GSM carrier calls. You must manually end the call on your phone dialer.</i>"
        )
        return message

    def send_risk_alert(
        self,
        assessment: ScamRiskAssessment,
        call_id: str,
    ) -> TelegramSendAlertResponse:
        """
        Evaluates assessment and sends a Telegram notification if threshold is reached
        and the alert is not a duplicate.
        """
        if not self.is_configured:
            return TelegramSendAlertResponse(
                delivered=False,
                status="NOT_CONFIGURED",
                detail="Telegram Bot Token or Chat ID not configured in environment.",
                call_id=call_id,
            )

        if not self.is_enabled:
            return TelegramSendAlertResponse(
                delivered=False,
                status="DISABLED",
                detail="Telegram alerts are currently disabled or muted.",
                call_id=call_id,
            )

        if not self.should_alert(assessment.risk_level, assessment.risk_score):
            return TelegramSendAlertResponse(
                delivered=False,
                status="CONNECTED",
                detail=f"Risk level {assessment.risk_level} ({assessment.risk_score}) below threshold ({self.settings.telegram_alert_threshold}).",
                call_id=call_id,
            )

        categories = {i.category for i in assessment.rule_analysis.triggered_indicators}
        if assessment.contextual_analysis.money_or_sensitive_requests:
            categories.add("FINANCIAL_SOLICITATION")
        if assessment.contextual_analysis.threats_urgency_manipulation:
            categories.add("COERCIVE_THREAT")

        if self.is_duplicate_incident(call_id, assessment.risk_level, assessment.risk_score, categories):
            logger.info("Suppressed duplicate Telegram alert for call '%s'", call_id)
            return TelegramSendAlertResponse(
                delivered=False,
                status="CONNECTED",
                detail="Duplicate incident alert suppressed to prevent notification spam.",
                call_id=call_id,
            )

        headline = assessment.alert.headline if assessment.alert else "Scam Risk Alert"
        safe_action = (
            assessment.alert.safe_action
            if assessment.alert
            else assessment.recommended_action
        )

        message_text = self.build_alert_message(
            call_id=call_id,
            risk_level=assessment.risk_level,
            risk_score=assessment.risk_score,
            headline=headline,
            safe_action=safe_action,
            detected_categories=list(categories),
            caption=assessment.caption,
        )

        payload = {
            "chat_id": self.settings.telegram_chat_id,
            "text": message_text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }

        # Send via injected transport (mocked in tests) or live HTTP
        try:
            if self.http_transport is not None:
                resp_dict = self.http_transport("sendMessage", payload)
            else:
                resp_dict = self._dispatch_http_request("sendMessage", payload)

            msg_id = resp_dict.get("result", {}).get("message_id")
            self._total_alerts_sent += 1
            self._last_alert_timestamp = time.time()
            self._last_error = None

            # Record incident state for deduplication
            self._alerted_incidents[call_id] = {
                "risk_level": assessment.risk_level,
                "risk_score": assessment.risk_score,
                "timestamp": self._last_alert_timestamp,
                "categories": categories,
                "message_id": msg_id,
            }

            return TelegramSendAlertResponse(
                delivered=True,
                message_id=msg_id,
                status="CONNECTED",
                detail="Telegram alert dispatched successfully.",
                call_id=call_id,
            )

        except urllib.error.HTTPError as http_err:
            error_msg = f"Telegram API HTTP {http_err.code}: {http_err.reason}"
            logger.warning("Telegram alert delivery failed: %s", error_msg)
            self._last_error = error_msg
            status: TelegramServiceStatus = "UNAUTHORIZED" if http_err.code == 401 else "DELIVERY_FAILED"
            return TelegramSendAlertResponse(
                delivered=False,
                status=status,
                detail=error_msg,
                call_id=call_id,
            )
        except Exception as exc:
            error_msg = f"Failed to dispatch Telegram message: {type(exc).__name__}: {str(exc)}"
            logger.warning(error_msg)
            self._last_error = error_msg
            return TelegramSendAlertResponse(
                delivered=False,
                status="DELIVERY_FAILED",
                detail=error_msg,
                call_id=call_id,
            )

    def _dispatch_http_request(self, method: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Sends an HTTP POST request to the official Telegram Bot API."""
        url = f"https://api.telegram.org/bot{self.settings.telegram_bot_token}/{method}"
        encoded = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url=url,
            data=encoded,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=self.settings.telegram_timeout_seconds) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data

    def sync_bot_identity(self) -> Dict[str, Any]:
        """
        Queries official Telegram Bot API (getMe, getUpdates) to discover bot identity
        and automatically detect the user's chat_id if not yet configured.
        """
        if not self.settings.has_live_telegram_token:
            return {
                "ok": False,
                "configured": False,
                "bot_username": None,
                "chat_id": None,
                "detail": "Telegram bot token is not configured in environment.",
            }

        try:
            if not self._bot_username:
                if self.http_transport is not None:
                    me_resp = self.http_transport("getMe", {})
                else:
                    me_resp = self._dispatch_http_request("getMe", {})

                if me_resp.get("ok"):
                    self._bot_username = me_resp.get("result", {}).get("username")

            # Try to auto-discover chat_id if not yet set
            discovered_chat_id = None
            if not self.settings.telegram_chat_id:
                if self.http_transport is not None:
                    upd_resp = self.http_transport("getUpdates", {"limit": 10})
                else:
                    upd_resp = self._dispatch_http_request("getUpdates", {"limit": 10})

                updates = upd_resp.get("result", [])
                for upd in reversed(updates):
                    msg = upd.get("message") or upd.get("channel_post") or {}
                    chat = msg.get("chat") or {}
                    cid = chat.get("id")
                    if cid:
                        discovered_chat_id = str(cid)
                        self.settings.telegram_chat_id = discovered_chat_id
                        logger.info("Discovered Telegram chat_id '%s'", discovered_chat_id)
                        break

            bot_tag = f"@{self._bot_username}" if self._bot_username else "your bot"
            return {
                "ok": True,
                "configured": self.is_configured,
                "bot_username": self._bot_username,
                "chat_id": self.settings.telegram_chat_id,
                "detail": (
                    f"Connected to {bot_tag} (Chat ID: {self.settings.telegram_chat_id})"
                    if self.settings.telegram_chat_id
                    else f"Bot {bot_tag} is active. Send /start to {bot_tag} in Telegram to link your chat ID."
                ),
            }
        except Exception as exc:
            err = str(exc)
            logger.warning("Failed to sync bot identity: %s", err)
            self._last_error = err
            return {
                "ok": False,
                "configured": False,
                "bot_username": self._bot_username,
                "chat_id": self.settings.telegram_chat_id,
                "detail": f"Failed to connect to Telegram: {err}",
            }

    def set_chat_id(self, chat_id: str) -> Dict[str, Any]:
        """Manually sets the target Telegram chat ID for notifications."""
        cid = str(chat_id).strip()
        self.settings.telegram_chat_id = cid
        return {
            "ok": True,
            "configured": self.is_configured,
            "chat_id": self.settings.telegram_chat_id,
            "bot_username": self._bot_username,
            "detail": f"Telegram chat ID set to '{cid}'.",
        }

    def handle_webhook_update(self, update_payload: Dict[str, Any]) -> TelegramCommandResponse:
        """
        Processes incoming updates from Telegram Webhook with access control validation.
        Restricts commands to authorized users configured in settings.
        """
        message = update_payload.get("message") or {}
        from_user = message.get("from") or {}
        chat = message.get("chat") or {}
        user_id = str(from_user.get("id", chat.get("id", "")))
        text = (message.get("text") or "").strip()

        # Authorization Check
        authorized_ids = set(self.settings.telegram_authorized_users)
        if self.settings.telegram_chat_id:
            authorized_ids.add(str(self.settings.telegram_chat_id))

        if authorized_ids and user_id not in authorized_ids:
            logger.warning("Unauthorized Telegram command attempt from user_id '%s'", user_id)
            return TelegramCommandResponse(
                handled=False,
                command=text,
                reply_text="⛔ Access Denied: Your Telegram account is not authorized to control Suraksha Scam Shield.",
                authorized=False,
            )

        if not text:
            return TelegramCommandResponse(handled=False, authorized=True)

        cmd = text.split()[0].lower()

        if cmd in ("/start", "/help"):
            reply = (
                "🛡️ <b>Suraksha AI Scam Shield Bot</b>\n\n"
                "<b>Supported Commands:</b>\n"
                "• <code>/status</code> - View backend STT, AI detector, and alert status\n"
                "• <code>/latest</code> - View latest call risk assessment\n"
                "• <code>/mute</code> - Temporarily mute Telegram notifications\n"
                "• <code>/unmute</code> - Re-enable Telegram notifications\n"
                "• <code>/help</code> - Show this guidance message\n\n"
                "<i>⚠️ Note on Call Control: Suraksha alerts cannot mute or disconnect cellular GSM carrier calls. "
                "Always hang up via your phone dialer if a scam is suspected.</i>"
            )
            return TelegramCommandResponse(handled=True, command=cmd, reply_text=reply, authorized=True)

        if cmd == "/status":
            reply = (
                "🛡️ <b>Suraksha System Status:</b>\n"
                f"• <b>Status:</b> {'ONLINE' if self.is_configured else 'NOT CONFIGURED'}\n"
                f"• <b>Alert Threshold:</b> {self.settings.telegram_alert_threshold}\n"
                f"• <b>Alerts Sent:</b> {self._total_alerts_sent}\n"
                f"• <b>Muted:</b> {'YES' if self._alerts_muted else 'NO'}\n"
                f"• <b>Active Incident Tracking:</b> {len(self._alerted_incidents)} calls"
            )
            return TelegramCommandResponse(handled=True, command=cmd, reply_text=reply, authorized=True)

        if cmd == "/mute":
            self._alerts_muted = True
            return TelegramCommandResponse(
                handled=True,
                command=cmd,
                reply_text="🔇 Suraksha Telegram alerts have been muted.",
                authorized=True,
            )

        if cmd == "/unmute":
            self._alerts_muted = False
            return TelegramCommandResponse(
                handled=True,
                command=cmd,
                reply_text="🔔 Suraksha Telegram alerts are now active.",
                authorized=True,
            )

        if cmd == "/latest":
            if not self._alerted_incidents:
                reply = "ℹ️ No scam incidents recorded in current session."
            else:
                last_call_id, details = list(self._alerted_incidents.items())[-1]
                reply = (
                    f"🛡️ <b>Latest Alert Record:</b>\n"
                    f"• <b>Call ID:</b> <code>{last_call_id}</code>\n"
                    f"• <b>Risk Level:</b> {details.get('risk_level')}\n"
                    f"• <b>Risk Score:</b> {details.get('risk_score')}/100"
                )
            return TelegramCommandResponse(handled=True, command=cmd, reply_text=reply, authorized=True)

        return TelegramCommandResponse(
            handled=False,
            command=cmd,
            reply_text=f"Unknown command '{cmd}'. Send /help for available commands.",
            authorized=True,
        )

    def get_status(self) -> TelegramStatusResponse:
        """Returns the operational and configuration status of the Telegram service."""
        if not self.is_configured:
            status: TelegramServiceStatus = "NOT_CONFIGURED"
        elif not self.settings.telegram_alerts_enabled or self._alerts_muted:
            status = "DISABLED"
        elif self._last_error and "401" in self._last_error:
            status = "UNAUTHORIZED"
        elif self._last_error:
            status = "DELIVERY_FAILED"
        else:
            status = "CONNECTED"

        return TelegramStatusResponse(
            configured=self.is_configured,
            enabled=self.is_enabled,
            status=status,
            bot_username=self._bot_username,
            chat_id_configured=bool(self.settings.telegram_chat_id),
            alert_threshold=self.settings.telegram_alert_threshold,
            total_alerts_sent=self._total_alerts_sent,
            last_alert_timestamp=self._last_alert_timestamp,
            last_error=self._last_error,
        )


_default_telegram_service = TelegramAlertService()


def get_telegram_service() -> TelegramAlertService:
    return _default_telegram_service


def set_telegram_service(service: TelegramAlertService) -> None:
    global _default_telegram_service
    _default_telegram_service = service
