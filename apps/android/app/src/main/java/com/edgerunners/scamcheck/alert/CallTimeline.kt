package com.edgerunners.scamcheck.alert

import com.edgerunners.scamcheck.model.EndReason
import com.edgerunners.scamcheck.model.RequestType
import com.edgerunners.scamcheck.model.RiskLevel

/** What the call recap can show. Keys and times only: never audio or words from the call. */
enum class TimelineKind { Checking, Possible, High, Paused, Resumed, Continued, YouEnded, CallerEnded }

data class TimelineEntry(val atSeconds: Long, val kind: TimelineKind, val type: RequestType? = null)

/**
 * Derives recap entries from two consecutive call states. Pure, so it is unit tested.
 * Only answered calls get entries; a declined or unanswered call has no timeline.
 */
object CallTimeline {
    fun diff(before: CallUiState, after: CallUiState, atSeconds: Long): List<TimelineEntry> {
        val wasInCall = before.phase == CallPhase.InCall
        if (!wasInCall && after.phase != CallPhase.InCall) return emptyList()
        val out = mutableListOf<TimelineEntry>()

        if (after.phase == CallPhase.InCall) {
            if (before.monitor != Monitor.Checking && after.monitor == Monitor.Checking) {
                out += TimelineEntry(atSeconds, TimelineKind.Checking, after.alert?.type)
            }
            val a = after.alert
            val b = before.alert
            if (a != null && a.confirmed &&
                (b == null || !b.confirmed || b.id != a.id || b.level != a.level || b.type != a.type)
            ) {
                val kind = if (a.level == RiskLevel.High) TimelineKind.High else TimelineKind.Possible
                out += TimelineEntry(atSeconds, kind, a.type)
            }
            if (before.monitor != Monitor.Unavailable && after.monitor == Monitor.Unavailable && wasInCall) {
                out += TimelineEntry(atSeconds, TimelineKind.Paused)
            }
            if (before.monitor == Monitor.Unavailable && wasInCall &&
                (after.monitor == Monitor.Listening || after.monitor == Monitor.Checking)
            ) {
                out += TimelineEntry(atSeconds, TimelineKind.Resumed)
            }
            if (!before.continued && after.continued) {
                out += TimelineEntry(atSeconds, TimelineKind.Continued)
            }
        }

        if (wasInCall && after.phase == CallPhase.Ended) {
            val kind = if (after.endReason == EndReason.UserEnded) TimelineKind.YouEnded else TimelineKind.CallerEnded
            out += TimelineEntry(atSeconds, kind)
        }
        return out
    }
}
