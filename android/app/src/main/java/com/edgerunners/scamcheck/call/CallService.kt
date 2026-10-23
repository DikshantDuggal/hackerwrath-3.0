package com.edgerunners.scamcheck.call

import android.Manifest
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.content.pm.ServiceInfo
import android.os.Build
import android.os.IBinder
import android.util.Log
import androidx.core.app.ServiceCompat
import androidx.core.content.ContextCompat
import com.edgerunners.scamcheck.EdgerunnersApp
import com.edgerunners.scamcheck.alert.AlertNotifier

/** Keeps the call and its warnings alive while the user switches to another app. */
class CallService : Service() {
    override fun onBind(intent: Intent?): IBinder? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        val app = application as EdgerunnersApp
        val language = app.container.controller.state.value.settings.language
        val notification = app.container.notifier.ongoingCall(language)
        try {
            ServiceCompat.startForeground(
                this,
                AlertNotifier.CALL_ID,
                notification,
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) ServiceInfo.FOREGROUND_SERVICE_TYPE_MICROPHONE else 0,
            )
        } catch (e: RuntimeException) {
            Log.w("CallService", "could not start in the foreground", e)
            stopSelf()
        }
        return START_NOT_STICKY
    }

    companion object {
        /** Needs the microphone permission (Android 14 requires it for this service type). */
        fun start(context: Context) {
            val granted = ContextCompat.checkSelfPermission(context, Manifest.permission.RECORD_AUDIO) ==
                PackageManager.PERMISSION_GRANTED
            if (!granted) return
            try {
                ContextCompat.startForegroundService(context, Intent(context, CallService::class.java))
            } catch (e: RuntimeException) {
                Log.w("CallService", "could not start", e)
            }
        }

        fun stop(context: Context) {
            context.stopService(Intent(context, CallService::class.java))
        }
    }
}
