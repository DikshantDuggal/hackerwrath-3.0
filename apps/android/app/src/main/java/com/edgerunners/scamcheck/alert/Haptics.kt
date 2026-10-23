package com.edgerunners.scamcheck.alert

import android.content.Context
import android.os.Build
import android.os.VibrationEffect
import android.os.Vibrator
import android.os.VibratorManager

/** Three long pulses: different from a normal notification buzz. */
class Haptics(context: Context) {
    private val vibrator: Vibrator? = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
        context.getSystemService(VibratorManager::class.java)?.defaultVibrator
    } else {
        @Suppress("DEPRECATION")
        context.getSystemService(Context.VIBRATOR_SERVICE) as? Vibrator
    }

    fun warn() {
        val v = vibrator ?: return
        if (!v.hasVibrator()) return
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            v.vibrate(VibrationEffect.createWaveform(PATTERN, -1))
        } else {
            @Suppress("DEPRECATION")
            v.vibrate(PATTERN, -1)
        }
    }

    private companion object {
        val PATTERN = longArrayOf(0, 450, 200, 450, 200, 450)
    }
}
