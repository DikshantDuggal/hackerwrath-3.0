"""
Alert Generation Service.
Generates practical, non-definitive safety alerts and recommendations from risk assessments.
"""
from __future__ import annotations

import uuid
from typing import List
from app.schemas.analysis import AlertPayload, RiskLevelType, TriggeredIndicator


class AlertService:
    """Produces structured AlertPayload objects without claiming definitive fraud."""

    def build_alert(
        self,
        risk_level: RiskLevelType,
        risk_score: float,
        indicators: List[TriggeredIndicator],
    ) -> AlertPayload:
        alert_id = f"alt_{uuid.uuid4().hex[:10]}"

        if risk_level in ("HIGH", "CRITICAL"):
            categories = {i.category for i in indicators}
            is_critical = (risk_level == "CRITICAL" or risk_score >= 80.0)
            prefix = "Critical" if is_critical else "High-Risk"

            if "QR_SCAN_TO_RECEIVE_MONEY" in categories:
                headline = f"{prefix} Payment Scam Warning: Caller asked you to scan a QR code to receive money"
                safe_action = (
                    "End the call immediately. Scanning a QR code or entering a UPI PIN sends money from your account—it is never required to receive money."
                )
            elif "OTP_OR_PIN_REQUEST" in categories:
                headline = f"{prefix} Credential Theft Alert: Caller asked for an OTP, UPI PIN, or password"
                safe_action = (
                    "Never share any OTP, UPI PIN, CVV, or password. Disconnect the call immediately and contact your official bank branch."
                )
            elif "REMOTE_ACCESS_OR_SCREEN_SHARE" in categories:
                headline = f"{prefix} Device Takeover Request: Caller asked for screen sharing or remote control"
                safe_action = (
                    "Do not install AnyDesk, TeamViewer, or share your screen. Disconnect immediately."
                )
            elif "SUSPICIOUS_LINK_OR_APK" in categories:
                headline = f"{prefix} Malicious Link / APK Warning: Caller asked to open link or install APK"
                safe_action = (
                    "Do not click links or install APKs sent during calls. Disconnect immediately."
                )
            elif "THREAT_ARREST_OR_LEGAL_ACTION" in categories:
                headline = f"{prefix} Legal Threat / Extortion: Digital Arrest or Police/CBI Threat"
                safe_action = (
                    "Hang up immediately. Law enforcement, CBI, and courts never conduct arrests or demand money over phone or video calls."
                )
            else:
                headline = f"{prefix} Coercive or Impersonation Pattern Detected"
                safe_action = (
                    "Hang up and verify independently using official helplines. Legitimate organizations never demand immediate money or secret codes over calls."
                )

            return AlertPayload(
                alert_id=alert_id,
                triggered=True,
                severity="CRITICAL" if is_critical else "WARNING",
                headline=headline,
                safe_action=safe_action,
            )

        if risk_level == "MEDIUM":
            return AlertPayload(
                alert_id=alert_id,
                triggered=True,
                severity="WARNING",
                headline="Suspicious Call Indicators Detected: Proceed with Caution",
                safe_action=(
                    "Do not rush into any payment, QR scan, or credential sharing. Verify the caller's identity through an independent official channel."
                ),
            )

        if risk_level == "UNKNOWN":
            return AlertPayload(
                alert_id=alert_id,
                triggered=False,
                severity="ADVISORY",
                headline="Assessment Inconclusive (Insufficient Evidence or Service Reliability)",
                safe_action=(
                    "Automated analysis could not reliably assess this segment. Remain cautious with any payment or credential requests."
                ),
            )

        return AlertPayload(
            alert_id=alert_id,
            triggered=False,
            severity="NONE",
            headline="No High-Risk Scam Indicators Detected",
            safe_action="Continue with standard caution; never share OTPs, UPI PINs, or passwords.",
        )
