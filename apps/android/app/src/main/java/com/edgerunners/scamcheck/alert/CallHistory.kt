package com.edgerunners.scamcheck.alert

import com.edgerunners.scamcheck.model.RequestType
import kotlinx.serialization.Serializable
import java.util.Calendar
import java.util.TimeZone

/** How a call went, as Recents and the after-call screen tell it. There is no "safe". */
@Serializable
enum class CallOutcome {
    /** Warned, and the user hung up. */
    Stopped,
    /** Warned, and the user chose to keep talking. */
    Kept,
    /** Warned, and the caller hung up first. */
    CallerLeft,
    /** Checked; nobody asked for a QR scan, a PIN or an OTP. */
    Calm,
    /** Scam check was off for this call. */
    Off,
}

/**
 * One finished call, kept on this phone only for Recents and the week dial: a masked number,
 * times, the outcome and the request type. Never audio or anything that was said.
 */
@Serializable
data class CallRecord(
    val callId: String,
    val number: String,
    val endedAtMs: Long,
    val outcome: CallOutcome,
    val requestType: String? = null,
    /** Seconds from the first warning to the end of the call. */
    val secondsToEnd: Long = 0,
    val lengthSeconds: Long = 0,
    val demo: Boolean = false,
) {
    val warned: Boolean get() = outcome == CallOutcome.Stopped || outcome == CallOutcome.Kept || outcome == CallOutcome.CallerLeft
    val type: RequestType? get() = RequestType.fromWire(requestType)
}

/** One day on the week dial. */
data class DayTally(val startMs: Long, val calls: Int, val warnings: Int, val latestWarning: CallRecord?)

/** Pure helpers over call history, so they are unit tested. */
object CallHistory {
    const val MAX_RECORDS = 50

    fun outcome(timeline: List<TimelineEntry>, scamCheck: Boolean): CallOutcome {
        if (!scamCheck) return CallOutcome.Off
        val warnAt = firstWarning(timeline) ?: return CallOutcome.Calm
        val after = timeline.filter { it.atSeconds >= warnAt.atSeconds }
        return when {
            after.any { it.kind == TimelineKind.Continued } -> CallOutcome.Kept
            after.any { it.kind == TimelineKind.YouEnded } -> CallOutcome.Stopped
            else -> CallOutcome.CallerLeft
        }
    }

    fun firstWarning(timeline: List<TimelineEntry>): TimelineEntry? = timeline.firstOrNull {
        it.kind == TimelineKind.Checking || it.kind == TimelineKind.Possible || it.kind == TimelineKind.High
    }

    fun record(
        callId: String,
        fromNumber: String?,
        endedAtMs: Long,
        timeline: List<TimelineEntry>,
        lengthSeconds: Long,
        scamCheck: Boolean,
        demo: Boolean,
    ): CallRecord {
        val warn = firstWarning(timeline)
        val type = timeline.firstOrNull { it.type != null }?.type
        return CallRecord(
            callId = callId,
            number = maskNumber(fromNumber),
            endedAtMs = endedAtMs,
            outcome = outcome(timeline, scamCheck),
            requestType = if (warn != null) type?.wire else null,
            secondsToEnd = if (warn != null) (lengthSeconds - warn.atSeconds).coerceAtLeast(1) else 0,
            lengthSeconds = lengthSeconds,
            demo = demo,
        )
    }

    /** Keeps the country code and the last two digits: "+91 98XXX XXX21". */
    fun maskNumber(number: String?): String {
        val raw = number?.trim().orEmpty()
        if (raw.isEmpty()) return ""
        val digits = raw.filter { it.isDigit() }
        if (digits.length < 6) return raw
        val country = if (raw.startsWith("+") && digits.length > 10) "+" + digits.dropLast(10) + " " else ""
        val local = digits.takeLast(10)
        return country + local.take(2) + "XXX XXX" + local.takeLast(2)
    }

    fun add(history: List<CallRecord>, record: CallRecord): List<CallRecord> =
        (listOf(record) + history.filter { it.callId != record.callId }).take(MAX_RECORDS)

    /** The last seven days, oldest first, ending today. */
    fun week(history: List<CallRecord>, nowMs: Long, zone: TimeZone = TimeZone.getDefault()): List<DayTally> {
        val cal = Calendar.getInstance(zone).apply {
            timeInMillis = nowMs
            set(Calendar.HOUR_OF_DAY, 0)
            set(Calendar.MINUTE, 0)
            set(Calendar.SECOND, 0)
            set(Calendar.MILLISECOND, 0)
            add(Calendar.DAY_OF_YEAR, -6)
        }
        return (0 until 7).map {
            val start = cal.timeInMillis
            cal.add(Calendar.DAY_OF_YEAR, 1)
            val end = cal.timeInMillis
            val day = history.filter { r -> r.endedAtMs in start until end && r.outcome != CallOutcome.Off }
            DayTally(start, day.size, day.count { r -> r.warned }, day.filter { r -> r.warned }.maxByOrNull { r -> r.endedAtMs })
        }
    }

    /** Seconds from the ask to hanging up, over this week's stopped calls. */
    fun stoppedThisWeek(history: List<CallRecord>, nowMs: Long, zone: TimeZone = TimeZone.getDefault()): List<CallRecord> {
        val from = week(history, nowMs, zone).first().startMs
        return history.filter { it.endedAtMs >= from && it.outcome == CallOutcome.Stopped }
    }
}
