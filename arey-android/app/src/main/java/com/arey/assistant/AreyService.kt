package com.arey.assistant

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.os.Build
import android.os.IBinder
import android.util.Log
import androidx.core.app.NotificationCompat
import com.google.gson.Gson
import com.google.gson.reflect.TypeToken
import kotlinx.coroutines.*
import okhttp3.*
import java.util.concurrent.TimeUnit

class AreyService : Service() {

    private val tag = "AreyService"
    private val channelId = "arey_assistant_channel"
    private val notificationId = 101

    private lateinit var deviceController: DeviceController
    private var webSocket: WebSocket? = null
    private val client = OkHttpClient.Builder()
        .readTimeout(0, TimeUnit.MILLISECONDS)
        .pingInterval(20, TimeUnit.SECONDS)
        .build()

    private val gson = Gson()
    private val serviceScope = CoroutineScope(Dispatchers.IO + Job())

    override fun onCreate() {
        super.onCreate()
        deviceController = DeviceController(this)
        createNotificationChannel()
        startForeground(notificationId, buildNotification("Arey está activo y conectado."))
        connectWebSocket()
    }

    private fun getSavedServerUrl(): String {
        val prefs = getSharedPreferences("arey_prefs", Context.MODE_PRIVATE)
        return prefs.getString("server_ws_url", "ws://10.0.2.2:8000/ws/device/android") ?: "ws://10.0.2.2:8000/ws/device/android"
    }

    private fun connectWebSocket() {
        val url = getSavedServerUrl()
        Log.d(tag, "Conectando al servidor Arey en: $url")

        val request = Request.Builder().url(url).build()
        webSocket = client.newWebSocket(request, object : WebSocketListener() {
            override fun onOpen(webSocket: WebSocket, response: Response) {
                Log.d(tag, "✅ Conexión WebSocket establecida con Arey.")
                // Enviar estado inicial del teléfono
                sendStatusUpdate()
            }

            override fun onMessage(webSocket: WebSocket, text: String) {
                Log.d(tag, "Mensaje recibido del servidor: $text")
                handleServerMessage(text)
            }

            override fun onClosing(webSocket: WebSocket, code: Int, reason: String) {
                Log.d(tag, "Cerrando WebSocket: $reason")
            }

            override fun onClosed(webSocket: WebSocket, code: Int, reason: String) {
                Log.d(tag, "WebSocket cerrado. Reintentando...")
                scheduleReconnect()
            }

            override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) {
                Log.e(tag, "Error de WebSocket: ${t.message}. Reintentando en 5s...")
                scheduleReconnect()
            }
        })
    }

    private fun scheduleReconnect() {
        serviceScope.launch {
            delay(5000)
            connectWebSocket()
        }
    }

    private fun sendStatusUpdate() {
        val status = deviceController.getDeviceStatus()
        val payload = mapOf(
            "type" to "status_update",
            "status" to status
        )
        webSocket?.send(gson.toJson(payload))
    }

    private fun handleServerMessage(jsonText: String) {
        try {
            val type = object : TypeToken<Map<String, Any>>() {}.type
            val data: Map<String, Any> = gson.fromJson(jsonText, type)
            val msgType = data["type"] as? String

            if (msgType == "command") {
                val requestId = data["request_id"] as? String ?: ""
                val action = data["action"] as? String ?: ""
                @Suppress("UNCHECKED_CAST")
                val params = data["params"] as? Map<String, Any> ?: emptyMap()

                val result = executeDeviceAction(action, params)

                val responsePayload = mapOf(
                    "type" to "command_response",
                    "request_id" to requestId,
                    "response" to result
                )
                webSocket?.send(gson.toJson(responsePayload))
            }
        } catch (e: Exception) {
            Log.e(tag, "Error procesando comando: ${e.message}")
        }
    }

    private fun executeDeviceAction(action: String, params: Map<String, Any>): Map<String, Any> {
        return when (action) {
            "make_call" -> {
                val number = params["phone_number"] as? String ?: ""
                deviceController.makePhoneCall(number)
            }
            "send_sms" -> {
                val number = params["phone_number"] as? String ?: ""
                val msg = params["message"] as? String ?: ""
                deviceController.sendSMS(number, msg)
            }
            "send_whatsapp" -> {
                val number = params["phone_number"] as? String ?: ""
                val msg = params["message"] as? String ?: ""
                deviceController.sendWhatsApp(number, msg)
            }
            "find_phone" -> {
                val duration = (params["duration_seconds"] as? Number)?.toInt() ?: 20
                deviceController.triggerFindPhoneAlarm(duration)
            }
            "set_flashlight" -> {
                val turnOn = params["turn_on"] as? Boolean ?: true
                deviceController.setFlashlight(turnOn)
            }
            "set_volume" -> {
                val level = (params["level_percent"] as? Number)?.toInt() ?: 50
                deviceController.setVolume(level)
            }
            "open_app" -> {
                val app = params["app_name"] as? String ?: ""
                deviceController.openApp(app)
            }
            "get_status" -> {
                mapOf("status" to "success", "data" to deviceController.getDeviceStatus())
            }
            else -> mapOf("status" to "error", "message" to "Acción '$action' no soportada en Android.")
        }
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                channelId,
                "Arey Assistant Service",
                NotificationManager.IMPORTANCE_LOW
            ).apply {
                description = "Mantiene a Arey conectado para llamadas y control de dispositivos"
            }
            val manager = getSystemService(NotificationManager::class.java)
            manager.createNotificationChannel(channel)
        }
    }

    private fun buildNotification(text: String): Notification {
        val pendingIntent = PendingIntent.getActivity(
            this,
            0,
            Intent(this, MainActivity::class.java),
            PendingIntent.FLAG_IMMUTABLE
        )
        return NotificationCompat.Builder(this, channelId)
            .setContentTitle("Arey Assistant")
            .setContentText(text)
            .setSmallIcon(android.R.drawable.ic_menu_call)
            .setContentIntent(pendingIntent)
            .setOngoing(true)
            .build()
    }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onDestroy() {
        serviceScope.cancel()
        webSocket?.close(1000, "Service stopped")
        super.onDestroy()
    }
}
