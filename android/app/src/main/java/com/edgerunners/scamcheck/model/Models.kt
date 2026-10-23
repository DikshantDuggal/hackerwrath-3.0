package com.edgerunners.scamcheck.model

/** Language chosen on Home; drives every screen, notifications and the spoken clip. */
enum class AppLanguage(val code: String) {
    English("en"), Hindi("hi"), Punjabi("pa");

    companion object {
        fun fromCode(code: String?): AppLanguage = entries.firstOrNull { it.code == code } ?: English
    }
}

data class UserSettings(
    val scamCheck: Boolean = true,
    val language: AppLanguage = AppLanguage.English,
    val expectingPayment: Boolean = false,
)

/** Request types the backend can warn about (wire values match the server). */
enum class RequestType(val wire: String) {
    QrReceive("qr_receive"), PinReceive("pin_receive"), OtpShare("otp_share"), RemoteAccess("remote_access");

    companion object {
        fun fromWire(value: String?): RequestType? = entries.firstOrNull { it.wire == value }
    }
}

/**
 * What the caller did, as the alert's "What they said" chips. Detail only: a signal never
 * raises or lowers the level. Declared in the order the chips show.
 */
enum class ThreatSignal(val wire: String) {
    OtpOrPinRequest("otp_or_pin_request"),
    RemoteAccess("remote_access"),
    FinancialSolicitation("financial_solicitation"),
    AuthorityImpersonation("authority_impersonation"),
    CoerciveThreat("coercive_threat"),
    AccountSuspensionThreat("account_suspension_threat");

    companion object {
        fun fromWire(value: String?): ThreatSignal? = entries.firstOrNull { it.wire == value }
    }
}

/** Only two levels exist. There is deliberately no "safe" level. */
enum class RiskLevel(val wire: String) {
    Possible("possible"), High("high");

    companion object {
        fun fromWire(value: String?): RiskLevel? = entries.firstOrNull { it.wire == value }
    }
}

enum class EndReason(val wire: String) {
    UserEnded("user_ended"), CallerEnded("caller_ended"), Declined("declined");

    companion object {
        fun fromWire(value: String?): EndReason? = entries.firstOrNull { it.wire == value }
    }
}

/** DEMO-FAKE scripted calls served by the backend demo driver. */
enum class DemoScenario(val wire: String) {
    QrScan("qr_scan"), Otp("otp"), Harmless("harmless"), Unavailable("unavailable")
}

enum class ConnectionState { Disconnected, Connecting, Connected }
