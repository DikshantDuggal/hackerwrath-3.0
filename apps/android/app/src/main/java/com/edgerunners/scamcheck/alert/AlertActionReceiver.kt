package com.edgerunners.scamcheck.alert

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import com.edgerunners.scamcheck.EdgerunnersApp

/** "End call" from the heads-up notification. */
class AlertActionReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action == ACTION_END_CALL) {
            (context.applicationContext as EdgerunnersApp).container.controller.endCall()
        }
    }

    companion object {
        const val ACTION_END_CALL = "com.edgerunners.scamcheck.END_CALL"
    }
}
