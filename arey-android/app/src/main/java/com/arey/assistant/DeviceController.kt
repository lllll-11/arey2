package com.arey.assistant

import android.content.Context
import android.content.Intent
import android.hardware.camera2.CameraManager
import android.media.AudioAttributes
import android.media.AudioManager
import android.media.Ringtone
import android.media.RingtoneManager
import android.net.Uri
import android.os.BatteryManager
import android.os.Build
import android.os.VibrationEffect
import android.os.Vibrator
import android.telephony.SmsManager
import android.util.Log
import kotlinx.coroutines.*

class DeviceController(private val context: Context) {

    private val tag = "DeviceController"
    private var isFlashlightOn = false
    private var alarmRingtone: Ringtone? = null

    /**
     * Realiza una llamada telefónica directa al número indicado.
     */
    fun makePhoneCall(phoneNumber: String): Map<String, Any> {
        return try {
            val cleanNumber = phoneNumber.replace(" ", "").replace("-", "")
            val intent = Intent(Intent.ACTION_CALL).apply {
                data = Uri.parse("tel:$cleanNumber")
                flags = Intent.FLAG_ACTIVITY_NEW_TASK
            }
            context.startActivity(intent)
            mapOf("status" to "success", "message" to "Marcando llamada a $cleanNumber")
        } catch (e: Exception) {
            Log.e(tag, "Error al realizar llamada: ${e.message}")
            mapOf("status" to "error", "error" to (e.message ?: "Error al llamar"))
        }
    }

    /**
     * Envía un mensaje SMS de forma directa y silenciosa.
     */
    fun sendSMS(phoneNumber: String, message: String): Map<String, Any> {
        return try {
            val smsManager = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                context.getSystemService(SmsManager::class.java)
            } else {
                @Suppress("DEPRECATION")
                SmsManager.getDefault()
            }
            smsManager.sendTextMessage(phoneNumber, null, message, null, null)
            mapOf("status" to "success", "message" to "SMS enviado a $phoneNumber")
        } catch (e: Exception) {
            Log.e(tag, "Error al enviar SMS: ${e.message}")
            mapOf("status" to "error", "error" to (e.message ?: "Error SMS"))
        }
    }

    /**
     * Abre WhatsApp listo con el chat y mensaje hacia el número indicado.
     */
    fun sendWhatsApp(phoneNumber: String, message: String): Map<String, Any> {
        return try {
            val cleanNumber = phoneNumber.replace("+", "").replace(" ", "")
            val uri = Uri.parse("https://api.whatsapp.com/send?phone=$cleanNumber&text=${Uri.encode(message)}")
            val intent = Intent(Intent.ACTION_VIEW, uri).apply {
                flags = Intent.FLAG_ACTIVITY_NEW_TASK
            }
            context.startActivity(intent)
            mapOf("status" to "success", "message" to "WhatsApp abierto hacia $cleanNumber")
        } catch (e: Exception) {
            mapOf("status" to "error", "error" to (e.message ?: "Error WhatsApp"))
        }
    }

    /**
     * Activa una alarma sonora estridente al 100% de volumen y parpadeo de linterna para localizar el teléfono.
     */
    fun triggerFindPhoneAlarm(durationSeconds: Int = 20): Map<String, Any> {
        CoroutineScope(Dispatchers.Default).launch {
            try {
                val audioManager = context.getSystemService(Context.AUDIO_SERVICE) as AudioManager
                // Subir volumen al máximo
                val maxVolume = audioManager.getStreamMaxVolume(AudioManager.STREAM_ALARM)
                audioManager.setStreamVolume(AudioManager.STREAM_ALARM, maxVolume, 0)

                val alarmUri = RingtoneManager.getDefaultUri(RingtoneManager.TYPE_ALARM)
                    ?: RingtoneManager.getDefaultUri(RingtoneManager.TYPE_RINGTONE)
                
                alarmRingtone = RingtoneManager.getRingtone(context, alarmUri)
                alarmRingtone?.audioAttributes = AudioAttributes.Builder()
                    .setUsage(AudioAttributes.USAGE_ALARM)
                    .setContentType(AudioAttributes.CONTENT_TYPE_SONIFICATION)
                    .build()
                
                alarmRingtone?.play()

                val vibrator = context.getSystemService(Context.VIBRATOR_SERVICE) as Vibrator
                val cameraManager = context.getSystemService(Context.CAMERA_SERVICE) as CameraManager
                val cameraId = cameraManager.cameraIdList.firstOrNull()

                // Ciclo de parpadeo y vibración durante los segundos especificados
                val loops = durationSeconds * 2
                for (i in 0 until loops) {
                    if (alarmRingtone?.isPlaying != true) alarmRingtone?.play()
                    
                    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                        vibrator.vibrate(VibrationEffect.createOneShot(300, VibrationEffect.DEFAULT_AMPLITUDE))
                    } else {
                        @Suppress("DEPRECATION")
                        vibrator.vibrate(300)
                    }

                    if (cameraId != null) {
                        try {
                            cameraManager.setTorchMode(cameraId, i % 2 == 0)
                        } catch (_: Exception) {}
                    }
                    delay(500)
                }

                // Apagar linterna al terminar
                if (cameraId != null) {
                    try { cameraManager.setTorchMode(cameraId, false) } catch (_: Exception) {}
                }
                alarmRingtone?.stop()

            } catch (e: Exception) {
                Log.e(tag, "Error en alarma: ${e.message}")
            }
        }
        return mapOf("status" to "success", "message" to "Alarma de localización activada en el teléfono.")
    }

    /**
     * Enciende o apaga la linterna.
     */
    fun setFlashlight(turnOn: Boolean): Map<String, Any> {
        return try {
            val cameraManager = context.getSystemService(Context.CAMERA_SERVICE) as CameraManager
            val cameraId = cameraManager.cameraIdList.firstOrNull()
            if (cameraId != null) {
                cameraManager.setTorchMode(cameraId, turnOn)
                isFlashlightOn = turnOn
                mapOf("status" to "success", "flashlight" to turnOn)
            } else {
                mapOf("status" to "error", "message" to "No se encontró flash en la cámara")
            }
        } catch (e: Exception) {
            mapOf("status" to "error", "error" to (e.message ?: "Error linterna"))
        }
    }

    /**
     * Ajusta el volumen del teléfono (0 a 100).
     */
    fun setVolume(levelPercent: Int): Map<String, Any> {
        return try {
            val audioManager = context.getSystemService(Context.AUDIO_SERVICE) as AudioManager
            val maxVol = audioManager.getStreamMaxVolume(AudioManager.STREAM_MUSIC)
            val target = (maxVol * (levelPercent / 100.0)).toInt()
            audioManager.setStreamVolume(AudioManager.STREAM_MUSIC, target, AudioManager.FLAG_SHOW_UI)
            mapOf("status" to "success", "volume" to levelPercent)
        } catch (e: Exception) {
            mapOf("status" to "error", "error" to (e.message ?: "Error volumen"))
        }
    }

    /**
     * Abre una aplicación instalada (ej: YouTube, Spotify, Maps).
     */
    fun openApp(appName: String): Map<String, Any> {
        val packageMap = mapOf(
            "whatsapp" to "com.whatsapp",
            "youtube" to "com.google.android.youtube",
            "spotify" to "com.spotify.music",
            "camara" to "com.android.camera",
            "camera" to "com.android.camera",
            "maps" to "com.google.android.apps.maps",
            "chrome" to "com.android.chrome",
            "fotos" to "com.google.android.apps.photos",
            "calculadora" to "com.google.android.calculator"
        )
        val packageName = packageMap[appName.lowercase().trim()] ?: appName
        return try {
            val launchIntent = context.packageManager.getLaunchIntentForPackage(packageName)
            if (launchIntent != null) {
                launchIntent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                context.startActivity(launchIntent)
                mapOf("status" to "success", "message" to "Abriendo $appName en el teléfono")
            } else {
                mapOf("status" to "error", "message" to "No se encontró la app $appName")
            }
        } catch (e: Exception) {
            mapOf("status" to "error", "error" to (e.message ?: "Error al abrir app"))
        }
    }

    /**
     * Retorna telemetría del teléfono: porcentaje de batería, si está cargando y volumen.
     */
    fun getDeviceStatus(): Map<String, Any> {
        val batteryManager = context.getSystemService(Context.BATTERY_SERVICE) as BatteryManager
        val batteryLevel = batteryManager.getIntProperty(BatteryManager.BATTERY_PROPERTY_CAPACITY)
        val isCharging = batteryManager.isCharging

        val audioManager = context.getSystemService(Context.AUDIO_SERVICE) as AudioManager
        val currentVol = audioManager.getStreamVolume(AudioManager.STREAM_MUSIC)
        val maxVol = audioManager.getStreamMaxVolume(AudioManager.STREAM_MUSIC)
        val volPercent = if (maxVol > 0) (currentVol * 100 / maxVol) else 0

        return mapOf(
            "battery" to batteryLevel,
            "is_charging" to isCharging,
            "volume" to volPercent,
            "flashlight" to isFlashlightOn
        )
    }
}
