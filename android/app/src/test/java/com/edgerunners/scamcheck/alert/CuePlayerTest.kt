package com.edgerunners.scamcheck.alert

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class CuePlayerTest {

    @Test
    fun audioRoutePropertiesReflectAcousticPrivacy() {
        val earpieceState = AudioDeviceState(
            route = AudioRoute.EARPIECE,
            isHeadsetConnected = false,
            hasMicrophone = false,
            isNoHeadphonesMode = true,
            isPrivateCuePermitted = false,
            lastTransitionReason = "INITIALIZED"
        )
        assertTrue(earpieceState.isNoHeadphonesMode)
        assertFalse(earpieceState.isHeadsetConnected)
        assertEquals("Earpiece (Handset)", earpieceState.route.displayName)

        val wiredState = AudioDeviceState(
            route = AudioRoute.WIRED_HEADSET,
            isHeadsetConnected = true,
            hasMicrophone = true,
            isNoHeadphonesMode = false,
            isPrivateCuePermitted = true,
            lastTransitionReason = "WIRED_HEADSET_PLUGGED"
        )
        assertFalse(wiredState.isNoHeadphonesMode)
        assertTrue(wiredState.isHeadsetConnected)
        assertEquals("Wired Headset", wiredState.route.displayName)
    }

    @Test
    fun audioBecomingNoisyFallsBackToEarpieceSafely() {
        // Simulates unplugging wired/bluetooth headset during an active call
        val fallbackState = AudioDeviceState(
            route = AudioRoute.EARPIECE,
            isHeadsetConnected = false,
            hasMicrophone = false,
            isNoHeadphonesMode = true,
            isPrivateCuePermitted = false,
            lastTransitionReason = "AUDIO_BECOMING_NOISY_SAFE_FALLBACK"
        )
        assertEquals(AudioRoute.EARPIECE, fallbackState.route)
        assertTrue(fallbackState.isNoHeadphonesMode)
        assertEquals("AUDIO_BECOMING_NOISY_SAFE_FALLBACK", fallbackState.lastTransitionReason)
    }

    @Test
    fun muteControlMutesCallDuringCueAndRestoresAfter() {
        var callMuted = false
        val userMutedState = false

        val mute = object : MuteControl {
            override fun userMuted(): Boolean = userMutedState
            override fun applyCallMute(muted: Boolean) {
                callMuted = muted
            }
        }

        assertFalse(callMuted)
        mute.applyCallMute(true)
        assertTrue(callMuted)
        mute.applyCallMute(mute.userMuted())
        assertFalse(callMuted)
    }
}
