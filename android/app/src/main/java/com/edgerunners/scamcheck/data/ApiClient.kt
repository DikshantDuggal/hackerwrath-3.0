package com.edgerunners.scamcheck.data

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.decodeFromString
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody
import okhttp3.RequestBody.Companion.toRequestBody

@Serializable
data class LoginRequest(val username: String, val password: String)

@Serializable
data class LoginResponse(@SerialName("app_token") val appToken: String, @SerialName("user_id") val userId: String)

@Serializable
data class VoiceTokenResponse(@SerialName("voice_token") val voiceToken: String, val identity: String)

@Serializable
data class SettingsDto(
    @SerialName("scam_check") val scamCheck: Boolean,
    val lang: String,
    @SerialName("role_context") val roleContext: String? = null,
)

@Serializable
data class ActionRequest(val action: String, @SerialName("request_type") val requestType: String? = null)

@Serializable
data class ActionResponse(val ok: Boolean, @SerialName("call_state") val callState: String)

@Serializable
data class DemoCallRequest(val scenario: String)

@Serializable
data class DemoCallResponse(@SerialName("call_id") val callId: String)

@Serializable
data class CallStartDto(
    @SerialName("recipient_id") val recipientId: String,
    @SerialName("caller_id") val callerId: String? = null,
    @SerialName("language_code") val languageCode: String = "auto",
    @SerialName("enable_scam_detection") val enableScamDetection: Boolean = true,
)

@Serializable
data class CallStartResult(
    @SerialName("call_id") val callId: String,
    @SerialName("room_id") val roomId: String,
    @SerialName("caller_id") val callerId: String,
    @SerialName("recipient_id") val recipientId: String,
    val status: String,
    @SerialName("ai_detection_active") val aiDetectionActive: Boolean = true,
    @SerialName("consent_notice") val consentNotice: String? = null,
)

@Serializable
data class CallActionDto(
    @SerialName("user_id") val userId: String? = null,
    val reason: String? = null,
)

@Serializable
data class CallActionResult(
    @SerialName("call_id") val callId: String,
    val status: String,
    val message: String,
)

@Serializable
data class CallTokenDto(
    @SerialName("user_id") val userId: String? = null,
    @SerialName("ttl_seconds") val ttlSeconds: Int? = null,
)

@Serializable
data class CallTokenResult(
    val token: String,
    @SerialName("server_url") val serverUrl: String,
    @SerialName("room_id") val roomId: String,
    @SerialName("participant_identity") val participantIdentity: String,
    @SerialName("participant_name") val participantName: String? = null,
    @SerialName("expires_in_seconds") val expiresInSeconds: Int = 3600,
    @SerialName("ai_notice") val aiNotice: String? = null,
)

@Serializable
data class SystemStatusDto(
    @SerialName("backend_online") val backendOnline: Boolean = false,
    val service: String = "",
    val version: String = "",
    @SerialName("telegram_configured") val telegramConfigured: Boolean = false,
    @SerialName("telegram_status") val telegramStatus: String = "",
    @SerialName("telegram_bot_username") val telegramBotUsername: String? = null,
    @SerialName("telegram_chat_id") val telegramChatId: String? = null,
    @SerialName("stt_working") val sttWorking: Boolean = false,
    @SerialName("stt_model") val sttModel: String = "",
    @SerialName("rules_engine_working") val rulesEngineWorking: Boolean = false,
    @SerialName("icfd_model_working") val icfdModelWorking: Boolean = false,
    @SerialName("contextual_ai_working") val contextualAiWorking: Boolean = false,
    @SerialName("total_messages_analyzed") val totalMessagesAnalyzed: Int = 0,
    @SerialName("active_alerts_count") val activeAlertsCount: Int = 0,
)

@Serializable
data class MessageAnalysisRequestDto(val text: String)

@Serializable
data class MessageAnalysisDto(
    val id: String = "",
    val timestamp: Double = 0.0,
    @SerialName("original_text") val originalText: String = "",
    @SerialName("normalized_text") val normalizedText: String = "",
    @SerialName("detected_language") val detectedLanguage: String = "",
    @SerialName("detected_script") val detectedScript: String = "",
    @SerialName("risk_score") val riskScore: Double = 0.0,
    @SerialName("risk_level") val riskLevel: String = "LOW",
    val headline: String = "",
    @SerialName("safe_action") val safeAction: String = "",
    val signals: List<String> = emptyList(),
    @SerialName("protective_advice") val protectiveAdvice: Boolean = false,
    @SerialName("is_conversational") val isConversational: Boolean = false,
)

@Serializable
private data class ErrorBody(val error: ErrorDetail)

@Serializable
private data class ErrorDetail(val code: String, val message: String)

/** A non-2xx answer from the backend, with its error code (never shown raw to the user). */
class ApiException(val status: Int, val code: String) : Exception("HTTP $status $code")

/** REST client for the backend contract in docs/architecture.md section 5. */
class ApiClient(private val http: OkHttpClient, private val baseUrl: String) {
    private val json = Json { ignoreUnknownKeys = true; explicitNulls = false }
    private val jsonType = "application/json".toMediaType()

    suspend fun login(username: String, password: String): LoginResponse =
        post("/api/login", null, json.encodeToString(LoginRequest(username, password)))

    suspend fun voiceToken(token: String): VoiceTokenResponse = post("/api/voice-token", token, "{}")

    suspend fun getSettings(token: String): SettingsDto = send(request("/api/settings", token).get().build())

    suspend fun putSettings(token: String, settings: SettingsDto): SettingsDto =
        send(request("/api/settings", token).put(body(json.encodeToString(settings))).build())

    suspend fun action(token: String, callId: String, action: String, requestType: String? = null): ActionResponse =
        post("/api/calls/$callId/actions", token, json.encodeToString(ActionRequest(action, requestType)))

    suspend fun demoCall(token: String, scenario: String): DemoCallResponse =
        post("/api/demo/calls", token, json.encodeToString(DemoCallRequest(scenario)))


    suspend fun startCall(recipientId: String, callerId: String? = null, lang: String = "auto"): CallStartResult =
        post("/api/calls/start", null, json.encodeToString(CallStartDto(recipientId, callerId, lang)))

    suspend fun acceptCall(callId: String, userId: String? = null): CallActionResult =
        post("/api/calls/$callId/accept", null, json.encodeToString(CallActionDto(userId)))

    suspend fun rejectCall(callId: String, userId: String? = null, reason: String? = null): CallActionResult =
        post("/api/calls/$callId/reject", null, json.encodeToString(CallActionDto(userId, reason)))

    suspend fun endCall(callId: String, userId: String? = null, reason: String? = null): CallActionResult =
        post("/api/calls/$callId/end", null, json.encodeToString(CallActionDto(userId, reason)))

    suspend fun getCallToken(callId: String, userId: String? = null): CallTokenResult =
        post("/api/calls/$callId/token", null, json.encodeToString(CallTokenDto(userId)))

    suspend fun getSystemStatus(): SystemStatusDto = send(request("/api/system/status", null).get().build())

    suspend fun analyzeMessage(text: String): MessageAnalysisDto =
        post("/api/messages/analyze", null, json.encodeToString(MessageAnalysisRequestDto(text)))

    suspend fun getMessageHistory(): List<MessageAnalysisDto> =
        send(request("/api/messages/history", null).get().build())


    private suspend inline fun <reified T> post(path: String, token: String?, payload: String): T =
        send(request(path, token).post(body(payload)).build())

    private fun request(path: String, token: String?): Request.Builder {
        val builder = Request.Builder().url(baseUrl.trimEnd('/') + path).header("Accept", "application/json")
        if (token != null) builder.header("Authorization", "Bearer $token")
        return builder
    }

    private fun body(payload: String): RequestBody = payload.toRequestBody(jsonType)

    private suspend inline fun <reified T> send(request: Request): T = withContext(Dispatchers.IO) {
        http.newCall(request).execute().use { response ->
            val text = response.body?.string().orEmpty()
            if (!response.isSuccessful) {
                val code = runCatching { json.decodeFromString<ErrorBody>(text).error.code }.getOrDefault("http_${response.code}")
                throw ApiException(response.code, code)
            }
            json.decodeFromString<T>(text)
        }
    }
}
