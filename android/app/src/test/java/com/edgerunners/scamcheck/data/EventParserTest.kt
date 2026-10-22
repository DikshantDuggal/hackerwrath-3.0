package com.edgerunners.scamcheck.data

import com.edgerunners.scamcheck.model.RequestType
import com.edgerunners.scamcheck.model.RiskLevel
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class EventParserTest {

    @Test
    fun `parses a confirmed warning`() {
        val e = EventParser.parse(
            """{"v":1,"call_id":"call_7f3a","event_seq":12,"assessment_revision":2,"type":"confirmed","alert_id":"al_1","request_type":"qr_receive","level":"high"}"""
        )
        assertEquals(AppEvent.Confirmed("call_7f3a", 12, 2, "al_1", RequestType.QrReceive, RiskLevel.High), e)
    }

    @Test
    fun `parses ready`() {
        assertEquals(AppEvent.Ready, EventParser.parse("""{"v":1,"type":"ready"}"""))
    }

    @Test
    fun `drops an unknown version`() {
        assertNull(EventParser.parse("""{"v":2,"call_id":"c","event_seq":1,"type":"status","state":"monitoring"}"""))
    }

    @Test
    fun `drops an unknown level such as safe`() {
        assertNull(
            EventParser.parse(
                """{"v":1,"call_id":"c","event_seq":3,"assessment_revision":1,"type":"confirmed","alert_id":"a","request_type":"qr_receive","level":"safe"}"""
            )
        )
    }

    @Test
    fun `drops an unknown status state`() {
        assertNull(EventParser.parse("""{"v":1,"call_id":"c","event_seq":1,"type":"status","state":"all_clear"}"""))
    }

    @Test
    fun `drops malformed json`() {
        assertNull(EventParser.parse("not json"))
    }

    @Test
    fun `drops an event without a sequence number`() {
        assertNull(EventParser.parse("""{"v":1,"call_id":"c","type":"cleared","alert_id":"a","assessment_revision":1}"""))
    }
}
