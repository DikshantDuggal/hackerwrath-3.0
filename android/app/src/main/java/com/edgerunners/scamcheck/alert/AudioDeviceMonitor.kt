package com.edgerunners.scamcheck.alert

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.media.AudioDeviceCallback
import android.media.AudioDeviceInfo
import android.media.AudioManager
import android.os.Build
import android.util.Log
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

enum class AudioRoute(val displayName: String) {
    EARPIECE("Earpiece (Handset)"),
    SPEAKERPHONE("Speakerphone"),
    WIRED_HEADSET("Wired Headset"),
    BLUETOOTH_HEADSET("Bluetooth Headset")
}

data class AudioDeviceState(
    val route: AudioRoute = AudioRoute.EARPIECE,
    val isHeadsetConnected: Boolean = false,
    val hasMicrophone: Boolean = false,
    val isNoHeadphonesMode: Boolean = true,
    val isPrivateCuePermitted: Boolean = false,
    val lastTransitionReason: String = "INITIALIZED"
)

/**
 * Manages audio device state transitions:
 * - Wired headset connect/disconnect (ACTION_HEADSET_PLUG)
 * - Bluetooth audio connect/disconnect (ACTION_AUDIO_BECOMING_NOISY & AudioDeviceCallback)
 * - Headset unplugged mid-call safety (ACTION_AUDIO_BECOMING_NOISY)
 * - No-headphones behavior: enforces in-call acoustic isolation so warning chimes/speech
 *   play strictly into STREAM_VOICE_CALL earpiece rather than blasting external speaker.
 */
class AudioDeviceMonitor(private val context: Context) {
    private val audioManager = context.getSystemService(Context.AUDIO_SERVICE) as AudioManager
    private val _state = MutableStateFlow(computeCurrentState("INITIALIZED"))
    val state: StateFlow<AudioDeviceState> = _state.asStateFlow()

    private var registered = false

    private val headsetReceiver = object : BroadcastReceiver() {
        override fun onReceive(ctx: Context?, intent: Intent?) {
            when (intent?.action) {
                Intent.ACTION_HEADSET_PLUG -> {
                    val pluggedState = intent.getIntExtra("state", 0)
                    val hasMic = intent.getIntExtra("microphone", 0) == 1
                    val reason = if (pluggedState == 1) "WIRED_HEADSET_PLUGGED" else "WIRED_HEADSET_UNPLUGGED"
                    Log.i(TAG, "Headset plug event: $reason (hasMic=$hasMic)")
                    updateState(
                        if (pluggedState == 1) AudioRoute.WIRED_HEADSET else AudioRoute.EARPIECE,
                        hasMic,
                        reason
                    )
                }
                AudioManager.ACTION_AUDIO_BECOMING_NOISY -> {
                    // Headset unplugged during live audio: fallback to earpiece immediately to prevent room leakage
                    Log.i(TAG, "Audio becoming noisy: routing immediately to earpiece for call security")
                    updateState(AudioRoute.EARPIECE, hasMic = false, reason = "AUDIO_BECOMING_NOISY_SAFE_FALLBACK")
                }
            }
        }
    }

    private val deviceCallback = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
        object : AudioDeviceCallback() {
            override fun onAudioDevicesAdded(addedDevices: Array<out AudioDeviceInfo>?) {
                evaluateConnectedDevices("DEVICE_ADDED")
            }

            override fun onAudioDevicesRemoved(removedDevices: Array<out AudioDeviceInfo>?) {
                evaluateConnectedDevices("DEVICE_REMOVED")
            }
        }
    } else null

    fun start() {
        if (registered) return
        val filter = IntentFilter().apply {
            addAction(Intent.ACTION_HEADSET_PLUG)
            addAction(AudioManager.ACTION_AUDIO_BECOMING_NOISY)
        }
        context.registerReceiver(headsetReceiver, filter)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M && deviceCallback != null) {
            audioManager.registerAudioDeviceCallback(deviceCallback, null)
        }
        registered = true
        _state.value = computeCurrentState("MONITOR_STARTED")
    }

    fun stop() {
        if (!registered) return
        try {
            context.unregisterReceiver(headsetReceiver)
        } catch (_: Exception) {}
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M && deviceCallback != null) {
            audioManager.unregisterAudioDeviceCallback(deviceCallback)
        }
        registered = false
    }

    fun simulateTransition(route: AudioRoute, reason: String = "SIMULATED_TEST") {
        updateState(
            route,
            hasMic = (route == AudioRoute.WIRED_HEADSET || route == AudioRoute.BLUETOOTH_HEADSET),
            reason = reason
        )
    }

    private fun evaluateConnectedDevices(reason: String) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            val devices = audioManager.getDevices(AudioManager.GET_DEVICES_OUTPUTS)
            var hasBt = false
            var hasWired = false
            for (dev in devices) {
                when (dev.type) {
                    AudioDeviceInfo.TYPE_BLUETOOTH_SCO,
                    AudioDeviceInfo.TYPE_BLUETOOTH_A2DP,
                    AudioDeviceInfo.TYPE_BLE_HEADSET -> hasBt = true
                    AudioDeviceInfo.TYPE_WIRED_HEADSET,
                    AudioDeviceInfo.TYPE_WIRED_HEADPHONES,
                    AudioDeviceInfo.TYPE_USB_HEADSET -> hasWired = true
                }
            }
            val targetRoute = when {
                hasBt -> AudioRoute.BLUETOOTH_HEADSET
                hasWired -> AudioRoute.WIRED_HEADSET
                audioManager.isSpeakerphoneOn -> AudioRoute.SPEAKERPHONE
                else -> AudioRoute.EARPIECE
            }
            updateState(targetRoute, hasWired || hasBt, reason)
        } else {
            _state.value = computeCurrentState(reason)
        }
    }

    private fun updateState(route: AudioRoute, hasMic: Boolean, reason: String) {
        val isHeadset = (route == AudioRoute.WIRED_HEADSET || route == AudioRoute.BLUETOOTH_HEADSET)
        _state.value = AudioDeviceState(
            route = route,
            isHeadsetConnected = isHeadset,
            hasMicrophone = hasMic,
            isNoHeadphonesMode = !isHeadset,
            isPrivateCuePermitted = isHeadset,
            lastTransitionReason = reason
        )
    }

    @Suppress("DEPRECATION")
    private fun computeCurrentState(reason: String): AudioDeviceState {
        val isWired = audioManager.isWiredHeadsetOn
        val isBt = audioManager.isBluetoothScoOn || audioManager.isBluetoothA2dpOn
        val route = when {
            isBt -> AudioRoute.BLUETOOTH_HEADSET
            isWired -> AudioRoute.WIRED_HEADSET
            audioManager.isSpeakerphoneOn -> AudioRoute.SPEAKERPHONE
            else -> AudioRoute.EARPIECE
        }
        val isHeadset = (route == AudioRoute.WIRED_HEADSET || route == AudioRoute.BLUETOOTH_HEADSET)
        return AudioDeviceState(
            route = route,
            isHeadsetConnected = isHeadset,
            hasMicrophone = isHeadset,
            isNoHeadphonesMode = !isHeadset,
            isPrivateCuePermitted = isHeadset,
            lastTransitionReason = reason
        )
    }

    companion object {
        private const val TAG = "AudioDeviceMonitor"
    }
}
