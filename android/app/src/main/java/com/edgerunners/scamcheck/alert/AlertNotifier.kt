package com.edgerunners.scamcheck.alert

import android.Manifest
import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.content.res.Configuration
import android.content.res.Resources
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import androidx.core.content.ContextCompat
import com.edgerunners.scamcheck.MainActivity
import com.edgerunners.scamcheck.R
import com.edgerunners.scamcheck.model.AppLanguage
import com.edgerunners.scamcheck.model.RequestType
import com.edgerunners.scamcheck.model.RiskLevel
import java.util.Locale

/** Heads-up warnings over other apps (for example the UPI app) and the ongoing-call notice. */
class AlertNotifier(private val context: Context) {

    fun createChannels() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return
        val nm = context.getSystemService(NotificationManager::class.java) ?: return
        nm.createNotificationChannel(
            NotificationChannel(CHANNEL_ALERTS, context.getString(R.string.channel_alerts), NotificationManager.IMPORTANCE_HIGH).apply {
                description = context.getString(R.string.channel_alerts_desc)
                enableVibration(false) // the app plays its own distinct pattern
                setSound(null, null)   // and its own chime, on the call audio path
            }
        )
        nm.createNotificationChannel(
            NotificationChannel(CHANNEL_CALL, context.getString(R.string.channel_call), NotificationManager.IMPORTANCE_LOW)
        )
    }

    fun showAlert(type: RequestType, level: RiskLevel, language: AppLanguage) {
        if (!canNotify()) return
        val res = localized(language)
        val title = res.getString(if (level == RiskLevel.High) R.string.level_high else R.string.level_possible)
        val (headline, body) = alertText(res, type)
        val notification = NotificationCompat.Builder(context, CHANNEL_ALERTS)
            .setSmallIcon(R.drawable.ic_stat_shield)
            .setContentTitle(title)
            .setContentText(headline)
            .setStyle(NotificationCompat.BigTextStyle().bigText("$headline\n$body"))
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .setCategory(NotificationCompat.CATEGORY_CALL)
            .setAutoCancel(true)
            .setContentIntent(openAppIntent())
            .addAction(0, res.getString(R.string.end_call), endCallIntent())
            .build()
        try {
            NotificationManagerCompat.from(context).notify(ALERT_ID, notification)
        } catch (_: SecurityException) {
            // Permission revoked between the check and the call.
        }
    }

    fun cancelAlert() {
        NotificationManagerCompat.from(context).cancel(ALERT_ID)
    }

    fun ongoingCall(language: AppLanguage): Notification =
        NotificationCompat.Builder(context, CHANNEL_CALL)
            .setSmallIcon(R.drawable.ic_stat_shield)
            .setContentTitle(localized(language).getString(R.string.call_notification))
            .setOngoing(true)
            .setContentIntent(openAppIntent())
            .build()

    private fun canNotify(): Boolean =
        Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU ||
            ContextCompat.checkSelfPermission(context, Manifest.permission.POST_NOTIFICATIONS) == PackageManager.PERMISSION_GRANTED

    private fun openAppIntent(): PendingIntent = PendingIntent.getActivity(
        context, 0,
        Intent(context, MainActivity::class.java).addFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP),
        PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT,
    )

    private fun endCallIntent(): PendingIntent = PendingIntent.getBroadcast(
        context, 1,
        Intent(context, AlertActionReceiver::class.java).setAction(AlertActionReceiver.ACTION_END_CALL),
        PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT,
    )

    private fun localized(language: AppLanguage): Resources {
        val config = Configuration(context.resources.configuration).apply { setLocale(Locale(language.code)) }
        return context.createConfigurationContext(config).resources
    }

    companion object {
        const val CHANNEL_ALERTS = "scam_alerts"
        const val CHANNEL_CALL = "ongoing_call"
        const val ALERT_ID = 42
        const val CALL_ID = 41

        /** Title and body for a request type, shared with the in-app alert. */
        fun alertText(res: Resources, type: RequestType): Pair<String, String> = when (type) {
            RequestType.QrReceive -> res.getString(R.string.alert_qr_title) to res.getString(R.string.alert_receive_body)
            RequestType.PinReceive -> res.getString(R.string.alert_pin_title) to res.getString(R.string.alert_receive_body)
            RequestType.OtpShare -> res.getString(R.string.alert_otp_title) to res.getString(R.string.alert_otp_body)
            RequestType.RemoteAccess -> res.getString(R.string.alert_remote_title) to res.getString(R.string.alert_remote_body)
        }
    }
}
