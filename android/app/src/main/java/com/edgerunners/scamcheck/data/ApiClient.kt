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
