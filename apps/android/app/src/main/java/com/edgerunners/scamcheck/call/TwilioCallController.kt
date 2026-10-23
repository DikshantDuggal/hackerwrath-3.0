package com.edgerunners.scamcheck.call

import android.content.Context
import android.media.AudioManager
import android.util.Log
import com.twilio.voice.Call
import com.twilio.voice.CallException
import com.twilio.voice.CallInvite
import com.twilio.voice.CancelledCallInvite
import com.twilio.voice.MessageListener
import com.twilio.voice.RegistrationException
import com.twilio.voice.RegistrationListener
import com.twilio.voice.Voice
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.asSharedFlow

sealed interface VoiceCallEvent {
    data class Incoming(val callSid: String, val from: String) : VoiceCallEvent
    data object InviteCancelled : VoiceCallEvent
    data object Connected : VoiceCallEvent
    data class Disconnected(val failed: Boolean) : VoiceCallEvent
    data class RegistrationFailed(val code: Int) : VoiceCallEvent
}

/**
 * Twilio Voice SDK wrapper: registers this device for incoming calls (FCM), hands push
 * payloads to the SDK, and controls the live call. Demo calls never touch this class.
 */
class TwilioCallController(private val context: Context) {
    private val _events = MutableSharedFlow<VoiceCallEvent>(extraBufferCapacity = 16)
    val events: SharedFlow<VoiceCallEvent> = _events.asSharedFlow()

    private val audio = context.getSystemService(Context.AUDIO_SERVICE) as AudioManager
    private var invite: CallInvite? = null
    private var call: Call? = null

    val hasInvite: Boolean get() = invite != null

    fun register(accessToken: String, fcmToken: String) {
        Voice.register(accessToken, Voice.RegistrationChannel.FCM, fcmToken, object : RegistrationListener {
            override fun onRegistered(accessToken: String, fcmToken: String) {
                Log.i(TAG, "registered for incoming calls")
            }

            override fun onError(error: RegistrationException, accessToken: String, fcmToken: String) {
                Log.w(TAG, "registration failed: ${error.errorCode}")
                _events.tryEmit(VoiceCallEvent.RegistrationFailed(error.errorCode))
            }
        })
    }

    /** Returns true when the push was a Twilio call message. */
    fun handlePush(data: Map<String, String>): Boolean =
        Voice.handleMessage(context, data, object : MessageListener {
            override fun onCallInvite(callInvite: CallInvite) {
                invite = callInvite
                _events.tryEmit(VoiceCallEvent.Incoming(callInvite.callSid, callInvite.from ?: ""))
            }

            override fun onCancelledCallInvite(cancelledCallInvite: CancelledCallInvite, callException: CallException?) {
                invite = null
                _events.tryEmit(VoiceCallEvent.InviteCancelled)
            }
        })

    fun accept() {
        val pending = invite ?: return
        invite = null
        audio.mode = AudioManager.MODE_IN_COMMUNICATION
        call = pending.accept(context, listener)
    }

    fun reject() {
        invite?.reject(context)
        invite = null
    }

    fun hangUp() {
        call?.disconnect()
        call = null
        invite?.reject(context)
        invite = null
        resetAudio()
    }

    fun setMuted(muted: Boolean) {
        call?.mute(muted)
    }

    @Suppress("DEPRECATION") // simple routing for the demo; AudioSwitch is the long-term option
    fun setSpeaker(on: Boolean) {
        audio.isSpeakerphoneOn = on
    }

    private fun resetAudio() {
        @Suppress("DEPRECATION")
        audio.isSpeakerphoneOn = false
        audio.mode = AudioManager.MODE_NORMAL
    }

    private val listener = object : Call.Listener {
        override fun onConnectFailure(call: Call, callException: CallException) {
            Log.w(TAG, "connect failed: ${callException.errorCode}")
            this@TwilioCallController.call = null
            resetAudio()
            _events.tryEmit(VoiceCallEvent.Disconnected(failed = true))
        }

        override fun onRinging(call: Call) = Unit

        override fun onConnected(call: Call) {
            _events.tryEmit(VoiceCallEvent.Connected)
        }

        override fun onReconnecting(call: Call, callException: CallException) = Unit

        override fun onReconnected(call: Call) = Unit

        override fun onDisconnected(call: Call, callException: CallException?) {
            this@TwilioCallController.call = null
            resetAudio()
            _events.tryEmit(VoiceCallEvent.Disconnected(failed = callException != null))
        }
    }

    private companion object {
        const val TAG = "TwilioCall"
    }
}
