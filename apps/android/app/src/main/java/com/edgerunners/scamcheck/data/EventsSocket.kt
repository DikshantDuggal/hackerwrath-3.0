package com.edgerunners.scamcheck.data

import com.edgerunners.scamcheck.model.ConnectionState
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asSharedFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.put
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.Response
import okhttp3.WebSocket
import okhttp3.WebSocketListener

/**
 * The private warning channel (WSS /ws/app). Sends the auth message first, parses events,
 * and reconnects with backoff (1 s doubling to 15 s) until [stop] is called.
 */
class EventsSocket(
    private val http: OkHttpClient,
    private val baseUrl: String,
    private val scope: CoroutineScope,
) {
    private val _events = MutableSharedFlow<AppEvent>(extraBufferCapacity = 64)
    val events: SharedFlow<AppEvent> = _events.asSharedFlow()

    private val _connection = MutableStateFlow(ConnectionState.Disconnected)
    val connection: StateFlow<ConnectionState> = _connection.asStateFlow()

    @Volatile private var token: String? = null
    @Volatile private var socket: WebSocket? = null
    private var loop: Job? = null

    fun start(appToken: String) {
        token = appToken
        if (loop?.isActive == true) return
        loop = scope.launch {
            var backoffMs = 1_000L
            while (isActive && token != null) {
                _connection.value = ConnectionState.Connecting
                val closed = CompletableDeferred<Boolean>()
                socket = http.newWebSocket(Request.Builder().url(wsUrl()).build(), listener(closed))
                val wasOpen = closed.await()
                _connection.value = ConnectionState.Disconnected
                if (wasOpen) backoffMs = 1_000L
                delay(backoffMs)
                backoffMs = (backoffMs * 2).coerceAtMost(15_000L)
            }
        }
    }

    fun stop() {
        token = null
        loop?.cancel()
        loop = null
        socket?.close(1000, null)
        socket = null
        _connection.value = ConnectionState.Disconnected
    }

    private fun wsUrl(): String {
        val base = baseUrl.trimEnd('/')
        val ws = when {
            base.startsWith("https://") -> "wss://" + base.removePrefix("https://")
            base.startsWith("http://") -> "ws://" + base.removePrefix("http://")
            else -> base
        }
        return "$ws/ws/app"
    }

    private fun listener(closed: CompletableDeferred<Boolean>) = object : WebSocketListener() {
        private var opened = false

        override fun onOpen(webSocket: WebSocket, response: Response) {
            opened = true
            val auth = buildJsonObject {
                put("type", "auth")
                put("app_token", token.orEmpty())
            }
            webSocket.send(auth.toString())
            _connection.value = ConnectionState.Connected
        }

        override fun onMessage(webSocket: WebSocket, text: String) {
            EventParser.parse(text)?.let { _events.tryEmit(it) }
        }

        override fun onClosing(webSocket: WebSocket, code: Int, reason: String) {
            webSocket.close(code, null)
        }

        override fun onClosed(webSocket: WebSocket, code: Int, reason: String) {
            closed.complete(opened)
        }

        override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) {
            closed.complete(opened)
        }
    }
}
