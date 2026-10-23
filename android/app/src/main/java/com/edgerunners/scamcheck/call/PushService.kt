package com.edgerunners.scamcheck.call

import com.edgerunners.scamcheck.EdgerunnersApp
import com.google.firebase.messaging.FirebaseMessagingService
import com.google.firebase.messaging.RemoteMessage

/** Receives Twilio's incoming-call pushes and new FCM tokens. */
class PushService : FirebaseMessagingService() {
    private val container get() = (application as EdgerunnersApp).container

    override fun onMessageReceived(message: RemoteMessage) {
        container.twilio?.handlePush(message.data)
    }

    override fun onNewToken(token: String) {
        container.controller.onFcmToken(token)
    }
}
