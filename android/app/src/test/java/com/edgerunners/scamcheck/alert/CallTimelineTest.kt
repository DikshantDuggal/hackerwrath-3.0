package com.edgerunners.scamcheck.alert

import com.edgerunners.scamcheck.model.EndReason
import com.edgerunners.scamcheck.model.RequestType
import com.edgerunners.scamcheck.model.RiskLevel
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class CallTimelineTest {
    private val inCall = CallUiState(callId = "c1", phase = CallPhase.InCall, monitor = Monitor.Listening)
    private val possibleQr = ActiveAlert("a1", RequestType.QrReceive, RiskLevel.Possible, confirmed = false)

    @Test
    fun `checking starts an amber entry with the request type`() {
        val after = inCall.copy(monitor = Monitor.Checking, alert = possibleQr)
        assertEquals(
            listOf(TimelineEntry(3, TimelineKind.Checking, RequestType.QrReceive)),
            CallTimeline.diff(inCall, after, 3),
        )
    }

    @Test
    fun `a confirmed high risk adds one entry and a repeat of it adds none`() {
        val before = inCall.copy(monitor = Monitor.Checking, alert = possibleQr)
        val confirmed = possibleQr.copy(level = RiskLevel.High, confirmed = true)
        val after = before.copy(monitor = Monitor.Listening, alert = confirmed, alertOpen = true)
        assertEquals(listOf(TimelineEntry(6, TimelineKind.High, RequestType.QrReceive)), CallTimeline.diff(before, after, 6))
        assertTrue(CallTimeline.diff(after, after, 7).isEmpty())
    }

    @Test
    fun `losing and regaining protection are both recorded`() {
        val paused = inCall.copy(monitor = Monitor.Unavailable)
        assertEquals(listOf(TimelineEntry(4, TimelineKind.Paused)), CallTimeline.diff(inCall, paused, 4))
        assertEquals(listOf(TimelineEntry(12, TimelineKind.Resumed)), CallTimeline.diff(paused, inCall, 12))
    }

    @Test
    fun `keeping the call going after a warning is recorded`() {
        val after = inCall.copy(continued = true)
        assertEquals(listOf(TimelineEntry(9, TimelineKind.Continued)), CallTimeline.diff(inCall, after, 9))
    }

    @Test
    fun `who ended the call is recorded`() {
        val you = inCall.copy(phase = CallPhase.Ended, endReason = EndReason.UserEnded)
        val them = inCall.copy(phase = CallPhase.Ended, endReason = EndReason.CallerEnded)
        assertEquals(TimelineKind.YouEnded, CallTimeline.diff(inCall, you, 10).single().kind)
        assertEquals(TimelineKind.CallerEnded, CallTimeline.diff(inCall, them, 10).single().kind)
    }

    @Test
    fun `a declined call has no timeline`() {
        val ringing = CallUiState(callId = "c1", phase = CallPhase.Ringing)
        val declined = ringing.copy(phase = CallPhase.Ended, endReason = EndReason.Declined)
        assertTrue(CallTimeline.diff(ringing, declined, 0).isEmpty())
    }
}
