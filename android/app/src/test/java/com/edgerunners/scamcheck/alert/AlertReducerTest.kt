package com.edgerunners.scamcheck.alert

import com.edgerunners.scamcheck.data.AppEvent
import com.edgerunners.scamcheck.model.EndReason
import com.edgerunners.scamcheck.model.RequestType
import com.edgerunners.scamcheck.model.RiskLevel
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class AlertReducerTest {
    private val call = "call_1"

    private fun inCall(now: Long = 0): CallUiState {
        val ringing = AlertReducer.onEvent(CallUiState(), AppEvent.CallStarted(call, 1, "+91 90000 12345", demo = true), now).state
        return AlertReducer.onAnswered(ringing, now).state
    }

    @Test
    fun `call started rings the phone`() {
        val r = AlertReducer.onEvent(CallUiState(), AppEvent.CallStarted(call, 1, "+91 1", demo = false), 0)
        assertEquals(CallPhase.Ringing, r.state.phase)
        assertEquals(call, r.state.callId)
    }

    @Test
    fun `first warning turns the status amber with a chime and vibration`() {
        val r = AlertReducer.onEvent(inCall(), AppEvent.FirstWarning(call, 2, 0, "al_1", RequestType.QrReceive), 1_000)
        assertEquals(Monitor.Checking, r.state.monitor)
        assertFalse(r.state.alertOpen)
        assertTrue(Effect.Chime in r.effects)
        assertTrue(Effect.Vibrate in r.effects)
    }

    @Test
    fun `events for another call are ignored`() {
        val start = inCall()
        val r = AlertReducer.onEvent(start, AppEvent.FirstWarning("call_other", 5, 0, "al_1", RequestType.OtpShare), 1_000)
        assertEquals(start, r.state)
        assertTrue(r.effects.isEmpty())
    }

    @Test
    fun `older event_seq is ignored`() {
        val warned = AlertReducer.onEvent(inCall(), AppEvent.FirstWarning(call, 5, 0, "al_1", RequestType.QrReceive), 1_000).state
        val stale = AlertReducer.onEvent(warned, AppEvent.Status(call, 4, "monitoring", null), 2_000)
        assertEquals(warned, stale.state)
    }

    @Test
    fun `a status heartbeat does not hide an amber check in progress`() {
        val warned = AlertReducer.onEvent(inCall(), AppEvent.FirstWarning(call, 2, 0, "al_1", RequestType.QrReceive), 1_000).state
        val r = AlertReducer.onEvent(warned, AppEvent.Status(call, 3, "monitoring", null), 2_000)
        assertEquals(Monitor.Checking, r.state.monitor)
    }

    @Test
    fun `confirmed high risk opens the full alert with a spoken warning`() {
        val warned = AlertReducer.onEvent(inCall(), AppEvent.FirstWarning(call, 2, 0, "al_1", RequestType.QrReceive), 1_000).state
        val r = AlertReducer.onEvent(warned, AppEvent.Confirmed(call, 3, 1, "al_1", RequestType.QrReceive, RiskLevel.High), 3_000)
        assertTrue(r.state.alertOpen)
        assertEquals(RiskLevel.High, r.state.alert?.level)
        assertTrue(Effect.Speak(RequestType.QrReceive, RiskLevel.High) in r.effects)
    }

    @Test
    fun `a stale assessment revision is discarded`() {
        val warned = AlertReducer.onEvent(inCall(), AppEvent.FirstWarning(call, 2, 0, "al_1", RequestType.QrReceive), 1_000).state
        val confirmed = AlertReducer.onEvent(warned, AppEvent.Confirmed(call, 3, 2, "al_1", RequestType.QrReceive, RiskLevel.High), 2_000).state
        val r = AlertReducer.onEvent(confirmed, AppEvent.Confirmed(call, 4, 1, "al_1", RequestType.QrReceive, RiskLevel.Possible), 3_000)
        assertEquals(RiskLevel.High, r.state.alert?.level)
    }

    @Test
    fun `cleared returns quietly to listening`() {
        val warned = AlertReducer.onEvent(inCall(), AppEvent.FirstWarning(call, 2, 0, "al_1", RequestType.QrReceive), 1_000).state
        val r = AlertReducer.onEvent(warned, AppEvent.Cleared(call, 3, 1, "al_1"), 2_000)
        assertEquals(Monitor.Listening, r.state.monitor)
        assertNull(r.state.alert)
        assertFalse(r.effects.any { it is Effect.Chime || it is Effect.Speak })
    }

    @Test
    fun `a repeated request within twenty seconds does not chime again`() {
        val first = AlertReducer.onEvent(inCall(), AppEvent.FirstWarning(call, 2, 0, "al_1", RequestType.QrReceive), 1_000).state
        val cleared = AlertReducer.onEvent(first, AppEvent.Cleared(call, 3, 1, "al_1"), 2_000).state
        val again = AlertReducer.onEvent(cleared, AppEvent.FirstWarning(call, 4, 1, "al_2", RequestType.QrReceive), 10_000)
        assertEquals(Monitor.Checking, again.state.monitor)
        assertFalse(Effect.Chime in again.effects)
    }

    @Test
    fun `ten seconds without a heartbeat shows protection unavailable`() {
        val start = inCall(now = 0)
        assertEquals(Monitor.Starting, AlertReducer.onHeartbeatCheck(start, 9_000).state.monitor)
        assertEquals(Monitor.Unavailable, AlertReducer.onHeartbeatCheck(start, 10_001).state.monitor)
    }

    @Test
    fun `scam check off never turns into unavailable`() {
        val off = AlertReducer.onEvent(inCall(), AppEvent.Status(call, 2, "off", null), 0).state
        assertEquals(Monitor.Off, AlertReducer.onHeartbeatCheck(off, 60_000).state.monitor)
    }

    @Test
    fun `continue closes the alert and goes back to listening`() {
        val warned = AlertReducer.onEvent(inCall(), AppEvent.FirstWarning(call, 2, 0, "al_1", RequestType.OtpShare), 1_000).state
        val confirmed = AlertReducer.onEvent(warned, AppEvent.Confirmed(call, 3, 1, "al_1", RequestType.OtpShare, RiskLevel.High), 2_000).state
        val r = AlertReducer.onContinue(confirmed)
        assertFalse(r.state.alertOpen)
        assertTrue(r.state.continued)
        assertEquals(Monitor.Listening, r.state.monitor)
    }

    @Test
    fun `the caller ending the call closes any alert`() {
        val confirmed = AlertReducer.onEvent(
            AlertReducer.onEvent(inCall(), AppEvent.FirstWarning(call, 2, 0, "al_1", RequestType.QrReceive), 1_000).state,
            AppEvent.Confirmed(call, 3, 1, "al_1", RequestType.QrReceive, RiskLevel.High), 2_000,
        ).state
        val r = AlertReducer.onEvent(confirmed, AppEvent.CallEnded(call, 4, EndReason.CallerEnded), 3_000)
        assertEquals(CallPhase.Ended, r.state.phase)
        assertFalse(r.state.alertOpen)
        assertTrue(Effect.CancelHeadsUp in r.effects)
    }

    @Test
    fun `a twilio ring adopts the backend call id when it arrives`() {
        val ringing = AlertReducer.onLocalIncoming(CallUiState(), "+91 1", 0).state
        val r = AlertReducer.onEvent(ringing, AppEvent.CallStarted(call, 1, "+91 1", demo = false), 100)
        assertEquals(call, r.state.callId)
        assertEquals(CallPhase.Ringing, r.state.phase)
    }
}
