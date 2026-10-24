package com.edgerunners.scamcheck.call

import android.content.Context
import android.media.AudioManager
import android.util.Log
import io.livekit.android.LiveKit
import io.livekit.android.events.RoomEvent
import io.livekit.android.room.Room
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asSharedFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.collect
import kotlinx.coroutines.launch

sealed interface LiveKitCallEvent {
    data class Connecting(val callId: String, val roomId: String) : LiveKitCallEvent
    data class Connected(val callId: String, val roomId: String) : LiveKitCallEvent
    data class ParticipantJoined(val identity: String) : LiveKitCallEvent
    data class ParticipantLeft(val identity: String) : LiveKitCallEvent
    data class Disconnected(val reason: String?) : LiveKitCallEvent
    data class Error(val message: String) : LiveKitCallEvent
}

enum class LiveKitCallStatus {
    IDLE,
    CONNECTING,
    CONNECTED,
    DISCONNECTED,
    ERROR
}

/**
 * LiveKit Cloud WebRTC Internet Calling Controller.
 * Manages room lifecycle, participant track subscription, microphone publishing,
 * and audio routing for AI scam-protected voice calls.
 */
class LiveKitCallController(private val context: Context) {
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Main)
    private val audio = context.getSystemService(Context.AUDIO_SERVICE) as AudioManager

    private val _events = MutableSharedFlow<LiveKitCallEvent>(extraBufferCapacity = 16)
    val events: SharedFlow<LiveKitCallEvent> = _events.asSharedFlow()

    private val _status = MutableStateFlow(LiveKitCallStatus.IDLE)
    val status: StateFlow<LiveKitCallStatus> = _status.asStateFlow()

    private val _isMuted = MutableStateFlow(false)
    val isMuted: StateFlow<Boolean> = _isMuted.asStateFlow()

    private val _isSpeakerOn = MutableStateFlow(false)
    val isSpeakerOn: StateFlow<Boolean> = _isSpeakerOn.asStateFlow()

    private var room: Room? = null
    private var eventJob: Job? = null
    private var currentCallId: String? = null
    private var currentRoomId: String? = null

    val isConnected: Boolean get() = _status.value == LiveKitCallStatus.CONNECTED
    val callId: String? get() = currentCallId
    val roomId: String? get() = currentRoomId

    val consentNotice: String =
        "AI Scam Protection is active on this call. Audio is analyzed in real time to detect fraudulent patterns."

    /**
     * Connects to a LiveKit room using the given server URL and authorized participant token.
     */
    fun connect(serverUrl: String, token: String, callId: String, roomId: String) {
        scope.launch {
            try {
                disconnectInternal()

                currentCallId = callId
                currentRoomId = roomId
                _status.value = LiveKitCallStatus.CONNECTING
                _events.tryEmit(LiveKitCallEvent.Connecting(callId, roomId))

                val liveRoom = LiveKit.create(context.applicationContext)
                room = liveRoom

                // Configure communication audio mode
                audio.mode = AudioManager.MODE_IN_COMMUNICATION

                // Collect room events
                eventJob = launch {
                    liveRoom.events.events.collect { event ->
                        when (event) {
                            is RoomEvent.Connected -> {
                                Log.i(TAG, "LiveKit room connected: $roomId")
                                _status.value = LiveKitCallStatus.CONNECTED
                                _events.tryEmit(LiveKitCallEvent.Connected(callId, roomId))
                            }
                            is RoomEvent.ParticipantConnected -> {
                                Log.i(TAG, "Participant joined: ${event.participant.identity?.value}")
                                val identity = event.participant.identity?.value.orEmpty()
                                _events.tryEmit(LiveKitCallEvent.ParticipantJoined(identity))
                            }
                            is RoomEvent.ParticipantDisconnected -> {
                                Log.i(TAG, "Participant left: ${event.participant.identity?.value}")
                                val identity = event.participant.identity?.value.orEmpty()
                                _events.tryEmit(LiveKitCallEvent.ParticipantLeft(identity))
                            }
                            is RoomEvent.Disconnected -> {
                                Log.i(TAG, "LiveKit room disconnected: ${event.error?.message}")
                                _status.value = LiveKitCallStatus.DISCONNECTED
                                _events.tryEmit(LiveKitCallEvent.Disconnected(event.error?.message))
                                resetAudio()
                            }
                            is RoomEvent.FailedToConnect -> {
                                Log.e(TAG, "Failed to connect to LiveKit room: ${event.error.message}", event.error)
                                _status.value = LiveKitCallStatus.ERROR
                                _events.tryEmit(LiveKitCallEvent.Error(event.error.message ?: "Failed to connect"))
                                resetAudio()
                            }
                            else -> Unit
                        }
                    }
                }

                Log.i(TAG, "Connecting to LiveKit room '$roomId' at '$serverUrl' for call '$callId'")
                liveRoom.connect(serverUrl, token)

                // Publish local microphone
                liveRoom.localParticipant.setMicrophoneEnabled(true)
                _isMuted.value = false

            } catch (e: Exception) {
                Log.e(TAG, "Error connecting to LiveKit room: ${e.message}", e)
                _status.value = LiveKitCallStatus.ERROR
                _events.tryEmit(LiveKitCallEvent.Error(e.message ?: "Connection error"))
                resetAudio()
            }
        }
    }

    /**
     * Mutes or unmutes local microphone transmission.
     */
    fun setMuted(muted: Boolean) {
        scope.launch {
            try {
                room?.localParticipant?.setMicrophoneEnabled(!muted)
                _isMuted.value = muted
            } catch (e: Exception) {
                Log.w(TAG, "Error toggling microphone mute: ${e.message}")
            }
        }
    }

    /**
     * Routes audio output to speakerphone or earpiece.
     */
    @Suppress("DEPRECATION")
    fun setSpeaker(on: Boolean) {
        try {
            audio.isSpeakerphoneOn = on
            _isSpeakerOn.value = on
        } catch (e: Exception) {
            Log.w(TAG, "Error toggling speakerphone: ${e.message}")
        }
    }

    /**
     * Disconnects cleanly from the current LiveKit room and resets audio hardware.
     */
    fun disconnect() {
        scope.launch {
            disconnectInternal()
        }
    }

    private fun disconnectInternal() {
        eventJob?.cancel()
        eventJob = null

        room?.disconnect()
        room?.release()
        room = null

        currentCallId = null
        currentRoomId = null
        _status.value = LiveKitCallStatus.DISCONNECTED
        resetAudio()
    }

    @Suppress("DEPRECATION")
    private fun resetAudio() {
        audio.isSpeakerphoneOn = false
        audio.mode = AudioManager.MODE_NORMAL
        _isSpeakerOn.value = false
        _isMuted.value = false
    }

    companion object {
        private const val TAG = "LiveKitCallController"
    }
}
