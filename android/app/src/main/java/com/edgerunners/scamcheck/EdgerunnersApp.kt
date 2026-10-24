package com.edgerunners.scamcheck

import android.app.Application
import android.util.Log
import com.edgerunners.scamcheck.alert.AlertNotifier
import com.edgerunners.scamcheck.alert.AudioDeviceMonitor
import com.edgerunners.scamcheck.alert.CuePlayer
import com.edgerunners.scamcheck.alert.Haptics
import com.edgerunners.scamcheck.call.TwilioCallController
import com.edgerunners.scamcheck.data.ApiClient
import com.edgerunners.scamcheck.data.EventsSocket
import com.edgerunners.scamcheck.data.SessionStore
import com.google.firebase.FirebaseApp
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import okhttp3.OkHttpClient
import java.util.concurrent.TimeUnit

class EdgerunnersApp : Application() {
    lateinit var container: AppContainer
        private set

    override fun onCreate() {
        super.onCreate()
        val calling = initFirebase()
        container = AppContainer(this, callingEnabled = calling)
    }

    private fun initFirebase(): Boolean {
        return try {
            FirebaseApp.initializeApp(this)
            true
        } catch (e: IllegalStateException) {
            Log.w("EdgerunnersApp", "Firebase not configured", e)
            false
        }
    }
}

/** Manual dependency wiring; one instance per process. */
class AppContainer(app: Application, callingEnabled: Boolean) {
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Main.immediate)
    private val http = OkHttpClient.Builder()
        .connectTimeout(10, TimeUnit.SECONDS)
        .readTimeout(20, TimeUnit.SECONDS)
        .pingInterval(15, TimeUnit.SECONDS)
        .build()

    val session = SessionStore(app)
    val api = ApiClient(http, BuildConfig.API_BASE_URL)
    val socket = EventsSocket(http, BuildConfig.API_BASE_URL, scope)
    val notifier = AlertNotifier(app)
    val audioMonitor = AudioDeviceMonitor(app).also { it.startMonitoring() }
    val twilio: TwilioCallController? = if (callingEnabled) TwilioCallController(app) else null
    val controller = AppController(
        app = app,
        api = api,
        socket = socket,
        session = session,
        twilio = twilio,
        cues = CuePlayer(app, audioMonitor),
        haptics = Haptics(app),
        notifier = notifier,
        scope = scope,
    )
}
