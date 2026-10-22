package com.edgerunners.scamcheck.data

import com.edgerunners.scamcheck.model.EndReason
import com.edgerunners.scamcheck.model.RequestType
import com.edgerunners.scamcheck.model.RiskLevel
import com.edgerunners.scamcheck.model.ThreatSignal
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.booleanOrNull
import kotlinx.serialization.json.intOrNull
import kotlinx.serialization.json.jsonObject

/** Events from the backend's app WebSocket. Keys and enums only; never text to show. */
sealed interface AppEvent {
    data object Ready : AppEvent

    sealed interface CallEvent : AppEvent {
        val callId: String
        val seq: Int
    }

    data class CallStarted(override val callId: String, override val seq: Int, val fromNumber: String, val demo: Boolean) : CallEvent
    data class Status(override val callId: String, override val seq: Int, val state: String, val reason: String?) : CallEvent
    data class FirstWarning(
        override val callId: String,
        override val seq: Int,
        val revision: Int,
        val alertId: String,
        val requestType: RequestType,
        val signals: List<ThreatSignal> = emptyList(),
    ) : CallEvent
    data class Confirmed(
        override val callId: String,
        override val seq: Int,
        val revision: Int,
        val alertId: String,
        val requestType: RequestType,
        val level: RiskLevel,
        val signals: List<ThreatSignal> = emptyList(),
    ) : CallEvent
    data class Cleared(override val callId: String, override val seq: Int, val revision: Int, val alertId: String) : CallEvent
    data class CallEnded(override val callId: String, override val seq: Int, val reason: EndReason) : CallEvent
}

/** Strict parser: anything unexpected (version, type, enum, missing field) is dropped. */
object EventParser {
    private val json = Json { ignoreUnknownKeys = true }
    private val states = setOf("starting", "monitoring", "degraded", "unavailable", "off")

    fun parse(text: String): AppEvent? = try {
        parse(json.parseToJsonElement(text).jsonObject)
    } catch (_: Exception) {
        null
    }

    fun parse(o: JsonObject): AppEvent? {
        if (o.int("v") != 1) return null
        val type = o.str("type") ?: return null
        if (type == "ready") return AppEvent.Ready
        val callId = o.str("call_id") ?: return null
        val seq = o.int("event_seq") ?: return null
        return when (type) {
            "call_started" -> AppEvent.CallStarted(callId, seq, o.str("from_number") ?: return null, o.bool("demo") ?: false)
            "status" -> {
                val state = o.str("state")?.takeIf { it in states } ?: return null
                AppEvent.Status(callId, seq, state, o.str("reason"))
            }
            "first_warning" -> AppEvent.FirstWarning(
                callId, seq,
                o.int("assessment_revision") ?: 0,
                o.str("alert_id") ?: return null,
                RequestType.fromWire(o.str("request_type")) ?: return null,
                o.signals(),
            )
            "confirmed" -> AppEvent.Confirmed(
                callId, seq,
                o.int("assessment_revision") ?: return null,
                o.str("alert_id") ?: return null,
                RequestType.fromWire(o.str("request_type")) ?: return null,
                RiskLevel.fromWire(o.str("level")) ?: return null,
                o.signals(),
            )
            "cleared" -> AppEvent.Cleared(
                callId, seq,
                o.int("assessment_revision") ?: return null,
                o.str("alert_id") ?: return null,
            )
            "call_ended" -> AppEvent.CallEnded(callId, seq, EndReason.fromWire(o.str("reason")) ?: return null)
            else -> null
        }
    }

    /** Optional, and never a reason to drop the event: unknown or repeated values are left out. */
    private fun JsonObject.signals(): List<ThreatSignal> {
        val known = (this["signals"] as? JsonArray).orEmpty()
            .mapNotNull { (it as? JsonPrimitive)?.takeIf { p -> p.isString }?.let { p -> ThreatSignal.fromWire(p.content) } }
            .toSet()
        return ThreatSignal.entries.filter { it in known }
    }

    private fun JsonObject.str(key: String): String? = (this[key] as? JsonPrimitive)?.takeIf { it.isString }?.content
    private fun JsonObject.int(key: String): Int? = (this[key] as? JsonPrimitive)?.takeIf { !it.isString }?.intOrNull
    private fun JsonObject.bool(key: String): Boolean? = (this[key] as? JsonPrimitive)?.takeIf { !it.isString }?.booleanOrNull
}
