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

        if risk_level == "HIGH":
            categories = {i.category for i in indicators}
            if "QR_SCAN_TO_RECEIVE_MONEY" in categories:
                headline = "High-Risk Payment Pattern: Caller asked you to scan a QR code to receive money"
                safe_action = (
                    "End the call. Scanning a QR code or entering a UPI PIN sends money from your account—it is never required to receive money."
                )
            elif "OTP_OR_PIN_REQUEST" in categories:
                headline = "High-Risk Credential Request: Caller asked for an OTP, UPI PIN, or password"
                safe_action = (
                    "Do not share any OTP, UPI PIN, CVV, or password on the call. Hang up and verify directly via your official banking app."
                )
            elif "REMOTE_ACCESS_OR_SCREEN_SHARE" in categories:
                headline = "High-Risk Device Access Request: Caller asked for screen sharing or remote control"
                safe_action = (
                    "Do not install AnyDesk, TeamViewer, or share your screen during a financial call. Disconnect immediately."
                )
            else:
                headline = "High-Risk Coercive or Impersonation Pattern Detected"
                safe_action = (
                    "Hang up and verify the claim independently using an official helpline number. Government and bank officials never conduct arrests or demand fees over calls."
                )

            return AlertPayload(
                alert_id=alert_id,
                triggered=True,
                severity="CRITICAL",
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
