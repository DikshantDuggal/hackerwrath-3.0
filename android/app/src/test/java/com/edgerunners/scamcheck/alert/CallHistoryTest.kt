package com.edgerunners.scamcheck.alert

import com.edgerunners.scamcheck.model.RequestType
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test
import java.util.TimeZone

class CallHistoryTest {
    private val warned = listOf(TimelineEntry(4, TimelineKind.Checking, RequestType.QrReceive), TimelineEntry(6, TimelineKind.High, RequestType.QrReceive))
    private val utc = TimeZone.getTimeZone("UTC")

    @Test
    fun `hanging up after a warning is a stopped scam`() {
        assertEquals(CallOutcome.Stopped, CallHistory.outcome(warned + TimelineEntry(10, TimelineKind.YouEnded), scamCheck = true))
    }

    @Test
    fun `keeping the call going after a warning is kept even if you hang up later`() {
        val timeline = warned + TimelineEntry(8, TimelineKind.Continued) + TimelineEntry(30, TimelineKind.YouEnded)
        assertEquals(CallOutcome.Kept, CallHistory.outcome(timeline, scamCheck = true))
    }

    @Test
    fun `the caller hanging up after a warning is not counted as you stopping it`() {
        assertEquals(CallOutcome.CallerLeft, CallHistory.outcome(warned + TimelineEntry(9, TimelineKind.CallerEnded), scamCheck = true))
    }

    @Test
    fun `a call with no warning is calm and never safe`() {
        assertEquals(CallOutcome.Calm, CallHistory.outcome(listOf(TimelineEntry(20, TimelineKind.YouEnded)), scamCheck = true))
    }

    @Test
    fun `a call with scam check off is off whatever happened`() {
        assertEquals(CallOutcome.Off, CallHistory.outcome(warned, scamCheck = false))
    }

    @Test
    fun `a record keeps the request type and seconds from the ask to the end`() {
        val record = CallHistory.record("c1", "+919812345621", 1_000, warned + TimelineEntry(10, TimelineKind.YouEnded), 10, true, false)
        assertEquals("qr_receive", record.requestType)
        assertEquals(6L, record.secondsToEnd)
        assertEquals("+91 98XXX XXX21", record.number)
    }

    @Test
    fun `a calm record has no request type`() {
        val record = CallHistory.record("c2", "+919812345621", 1_000, emptyList(), 42, true, false)
        assertNull(record.requestType)
        assertEquals(0L, record.secondsToEnd)
    }

    @Test
    fun `the week ends today and counts warnings per day`() {
        val day = 86_400_000L
        val now = 10 * day + 3_600_000L
        val history = listOf(
            CallRecord("a", "", now - 60_000, CallOutcome.Stopped, "otp_share", 9),
            CallRecord("b", "", now - day, CallOutcome.Calm),
            CallRecord("c", "", now - 8 * day, CallOutcome.Stopped, "qr_receive", 5),
        )
        val week = CallHistory.week(history, now, utc)
        assertEquals(7, week.size)
        assertEquals(1, week.last().warnings)
        assertEquals("a", week.last().latestWarning?.callId)
        assertEquals(1, week[5].calls)
        assertEquals(2, week.sumOf { it.calls })
    }

    @Test
    fun `history keeps the newest first and drops a repeat of the same call`() {
        val first = CallRecord("x", "", 1, CallOutcome.Calm)
        val again = first.copy(endedAtMs = 2, outcome = CallOutcome.Stopped)
        assertEquals(listOf(again), CallHistory.add(listOf(first), again))
    }
}
