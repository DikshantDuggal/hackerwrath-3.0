package com.edgerunners.scamcheck.data

import android.content.Context
import com.edgerunners.scamcheck.alert.CallRecord
import com.edgerunners.scamcheck.model.AppLanguage
import com.edgerunners.scamcheck.model.UserSettings
import kotlinx.serialization.SerializationException
import kotlinx.serialization.builtins.ListSerializer
import kotlinx.serialization.json.Json

/** Small on-device store: the session token and a cache of the user's settings. */
class SessionStore(context: Context) {
    private val prefs = context.getSharedPreferences("session", Context.MODE_PRIVATE)

    val token: String? get() = prefs.getString(KEY_TOKEN, null)
    val userId: String? get() = prefs.getString(KEY_USER, null)

    fun saveLogin(token: String, userId: String) {
        prefs.edit().putString(KEY_TOKEN, token).putString(KEY_USER, userId).apply()
    }

    fun settings(): UserSettings = UserSettings(
        scamCheck = prefs.getBoolean(KEY_SCAM, true),
        language = AppLanguage.fromCode(prefs.getString(KEY_LANG, null)),
        expectingPayment = prefs.getBoolean(KEY_EXPECTING, false),
    )

    fun saveSettings(settings: UserSettings) {
        prefs.edit()
            .putBoolean(KEY_SCAM, settings.scamCheck)
            .putString(KEY_LANG, settings.language.code)
            .putBoolean(KEY_EXPECTING, settings.expectingPayment)
            .apply()
    }

    /** Counts shown on Home. Numbers only; nothing about what was said. */
    val callsWatched: Int get() = prefs.getInt(KEY_CALLS, 0)
    val warningsGiven: Int get() = prefs.getInt(KEY_WARNINGS, 0)

    fun saveCounts(calls: Int, warnings: Int) {
        prefs.edit().putInt(KEY_CALLS, calls).putInt(KEY_WARNINGS, warnings).apply()
    }

    /** Recents: masked numbers, times, outcomes and request types. Never audio or words. */
    fun history(): List<CallRecord> {
        val raw = prefs.getString(KEY_HISTORY, null) ?: return emptyList()
        return try {
            json.decodeFromString(ListSerializer(CallRecord.serializer()), raw)
        } catch (_: SerializationException) {
            emptyList()
        } catch (_: IllegalArgumentException) {
            emptyList()
        }
    }

    fun saveHistory(history: List<CallRecord>) {
        prefs.edit().putString(KEY_HISTORY, json.encodeToString(ListSerializer(CallRecord.serializer()), history)).apply()
    }

    /** How many full-screen alerts have been shown; picks the alert's look so it never repeats. */
    val alertRuns: Int get() = prefs.getInt(KEY_ALERT_RUNS, 0)

    fun saveAlertRuns(runs: Int) {
        prefs.edit().putInt(KEY_ALERT_RUNS, runs).apply()
    }

    fun clear() {
        prefs.edit().clear().apply()
    }

    private companion object {
        const val KEY_CALLS = "calls_watched"
        const val KEY_WARNINGS = "warnings_given"
        const val KEY_TOKEN = "app_token"
        const val KEY_USER = "user_id"
        const val KEY_SCAM = "scam_check"
        const val KEY_LANG = "lang"
        const val KEY_EXPECTING = "expecting_payment"
        const val KEY_HISTORY = "call_history"
        const val KEY_ALERT_RUNS = "alert_runs"
        val json = Json { ignoreUnknownKeys = true }
    }
}

fun UserSettings.toDto() = SettingsDto(
    scamCheck = scamCheck,
    lang = language.code,
    roleContext = if (expectingPayment) "expecting_payment" else null,
)

fun SettingsDto.toModel() = UserSettings(
    scamCheck = scamCheck,
    language = AppLanguage.fromCode(lang),
    expectingPayment = roleContext == "expecting_payment",
)
