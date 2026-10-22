package com.edgerunners.scamcheck.alert

import android.content.Context
import android.media.AudioAttributes
import android.media.AudioManager
import android.media.MediaPlayer
import android.media.ToneGenerator
import android.os.Handler
import android.os.Looper
import android.util.Log
import com.edgerunners.scamcheck.model.AppLanguage
import com.edgerunners.scamcheck.model.RequestType

/** Lets cues mute the call while they play, then put back whatever the user had. */
interface MuteControl {
    fun userMuted(): Boolean
    fun applyCallMute(muted: Boolean)
}

/**
 * Plays cues on this phone only, never into the call: the call is muted while a cue plays
 * and restored to the user's own mute choice afterwards.
 *
 * Spoken clips live in res/raw as warning_<request>_<lang> (for example
 * warning_qr_receive_hi.ogg), recorded by native speakers. Until a clip exists, the chime
 * and vibration carry the warning on their own.
 */
class CuePlayer(private val context: Context) {
    private val main = Handler(Looper.getMainLooper())

    fun chime(mute: MuteControl) {
        mute.applyCallMute(true)
        val tone = try {
            ToneGenerator(AudioManager.STREAM_VOICE_CALL, 70)
        } catch (e: RuntimeException) {
            Log.w(TAG, "tone generator unavailable", e)
            mute.applyCallMute(mute.userMuted())
            return
        }
        tone.startTone(ToneGenerator.TONE_PROP_BEEP2, 450)
        main.postDelayed({
            tone.release()
            mute.applyCallMute(mute.userMuted())
        }, 700)
    }

    fun speak(type: RequestType, language: AppLanguage, mute: MuteControl) {
        val name = "warning_${type.wire}_${language.code}"
        @Suppress("DiscouragedApi")
        val resId = context.resources.getIdentifier(name, "raw", context.packageName)
        if (resId == 0) {
            Log.i(TAG, "no spoken clip yet: $name")
            return
        }
        mute.applyCallMute(true)
        try {
            val player = MediaPlayer()
            context.resources.openRawResourceFd(resId).use { fd -> player.setDataSource(fd) }
            player.setAudioAttributes(
                AudioAttributes.Builder()
                    .setUsage(AudioAttributes.USAGE_VOICE_COMMUNICATION)
                    .setContentType(AudioAttributes.CONTENT_TYPE_SPEECH)
                    .build()
            )
            player.setOnCompletionListener {
                it.release()
                mute.applyCallMute(mute.userMuted())
            }
            player.prepare()
            player.start()
        } catch (e: Exception) {
            Log.w(TAG, "spoken clip failed", e)
            mute.applyCallMute(mute.userMuted())
        }
    }

    private companion object {
        const val TAG = "CuePlayer"
    }
}
