package com.edgerunners.scamcheck.alert

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class AudioDeviceMonitorTest {

    @Test
    fun initialState_defaultsToNoHeadphonesEarpiece() {
        val state = AudioDeviceState()
        assertEquals(AudioRoute.EARPIECE, state.route)
        assertTrue("No headphones mode should be active by default", state.isNoHeadphonesMode)
        assertFalse("Headset should not be reported connected by default", state.isHeadsetConnected)
        assertFalse("Private cue should not be permitted without headset", state.isPrivateCuePermitted)
    }

    @Test
    fun wiredHeadsetPlugged_enablesPrivateCuesAndDisablesNoHeadphonesMode() {
        val state = AudioDeviceState(
            route = AudioRoute.WIRED_HEADSET,
            isHeadsetConnected = true,
            hasMicrophone = true,
            isNoHeadphonesMode = false,
            isPrivateCuePermitted = true,
            lastTransitionReason = "WIRED_HEADSET_PLUGGED"
        )
        assertEquals(AudioRoute.WIRED_HEADSET, state.route)
        assertFalse(state.isNoHeadphonesMode)
        assertTrue(state.isHeadsetConnected)
        assertTrue(state.isPrivateCuePermitted)
        assertTrue(state.hasMicrophone)
        assertEquals("WIRED_HEADSET_PLUGGED", state.lastTransitionReason)
    }

    @Test
    fun bluetoothHeadsetConnected_enablesPrivateBluetoothRoute() {
        val state = AudioDeviceState(
            route = AudioRoute.BLUETOOTH_HEADSET,
            isHeadsetConnected = true,
            hasMicrophone = true,
            isNoHeadphonesMode = false,
            isPrivateCuePermitted = true,
            lastTransitionReason = "BLUETOOTH_SCO_CONNECTED"
        )
        assertEquals(AudioRoute.BLUETOOTH_HEADSET, state.route)
        assertFalse(state.isNoHeadphonesMode)
        assertTrue(state.isHeadsetConnected)
        assertTrue(state.isPrivateCuePermitted)
        assertEquals("BLUETOOTH_SCO_CONNECTED", state.lastTransitionReason)
    }

    @Test
    fun audioBecomingNoisy_unplugTransitionFallsBackSafelyToEarpiece() {
        // Simulates headset unplugged mid-call (ACTION_AUDIO_BECOMING_NOISY)
        val state = AudioDeviceState(
            route = AudioRoute.EARPIECE,
            isHeadsetConnected = false,
            hasMicrophone = false,
            isNoHeadphonesMode = true,
            isPrivateCuePermitted = false,
            lastTransitionReason = "AUDIO_BECOMING_NOISY_SAFE_FALLBACK"
        )
        assertEquals(AudioRoute.EARPIECE, state.route)
        assertTrue("Fallback must enforce noHeadphonesMode for acoustic protection", state.isNoHeadphonesMode)
        assertFalse("Headset is disconnected", state.isHeadsetConnected)
        assertFalse("Private cues disabled on earpiece fallback", state.isPrivateCuePermitted)
        assertEquals("AUDIO_BECOMING_NOISY_SAFE_FALLBACK", state.lastTransitionReason)
    }

    @Test
    fun speakerphoneMode_markedAsNoHeadphonesWithPublicAcousticGuard() {
        val state = AudioDeviceState(
            route = AudioRoute.SPEAKERPHONE,
            isHeadsetConnected = false,
            hasMicrophone = false,
            isNoHeadphonesMode = true,
            isPrivateCuePermitted = false,
            lastTransitionReason = "USER_ENABLED_SPEAKERPHONE"
        )
        assertEquals(AudioRoute.SPEAKERPHONE, state.route)
        assertTrue(state.isNoHeadphonesMode)
        assertFalse(state.isPrivateCuePermitted)
    }
}
