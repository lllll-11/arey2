package com.arey.assistant

import android.Manifest
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.widget.Button
import android.widget.EditText
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import com.google.gson.Gson
import kotlinx.coroutines.*
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody

class MainActivity : AppCompatActivity() {

    private lateinit var etServerUrl: EditText
    private lateinit var tvStatus: TextView
    private lateinit var btnSaveConnect: Button
    private lateinit var btnSyncContacts: Button
    private lateinit var btnTestCall: Button
    private lateinit var btnTestAlarm: Button
    private lateinit var btnVoiceCommand: Button

    private lateinit var deviceController: DeviceController
    private lateinit var contactsSync: ContactsSync
    private lateinit var voiceRecognizer: VoiceRecognizer
    private val httpClient = OkHttpClient()

    private val requiredPermissions = arrayOf(
        Manifest.permission.CALL_PHONE,
        Manifest.permission.READ_CONTACTS,
        Manifest.permission.SEND_SMS,
        Manifest.permission.RECORD_AUDIO,
        Manifest.permission.CAMERA
    )

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        deviceController = DeviceController(this)
        contactsSync = ContactsSync(this)

        initViews()
        checkAndRequestPermissions()
        initVoiceRecognizer()
    }

    private fun initViews() {
        etServerUrl = findViewById(R.id.etServerUrl)
        tvStatus = findViewById(R.id.tvStatus)
        btnSaveConnect = findViewById(R.id.btnSaveConnect)
        btnSyncContacts = findViewById(R.id.btnSyncContacts)
        btnTestCall = findViewById(R.id.btnTestCall)
        btnTestAlarm = findViewById(R.id.btnTestAlarm)
        btnVoiceCommand = findViewById(R.id.btnVoiceCommand)

        val prefs = getSharedPreferences("arey_prefs", Context.MODE_PRIVATE)
        val savedUrl = prefs.getString("server_ws_url", "ws://10.0.2.2:8000/ws/device/android")
        etServerUrl.setText(savedUrl)

        btnSaveConnect.setOnClickListener {
            val url = etServerUrl.text.toString().trim()
            if (url.isNotBlank()) {
                prefs.edit().putString("server_ws_url", url).apply()
                startAreyService()
                Toast.makeText(this, "Servicio iniciado y conectado a Arey.", Toast.LENGTH_SHORT).show()
                tvStatus.text = "Estado: Servicio Activo 24/7"
            }
        }

        btnSyncContacts.setOnClickListener {
            syncContactsToServer()
        }

        btnTestCall.setOnClickListener {
            // Ejemplo de llamada de prueba (puedes ingresar el número)
            deviceController.makePhoneCall("1234567890")
        }

        btnTestAlarm.setOnClickListener {
            deviceController.triggerFindPhoneAlarm(durationSeconds = 5)
        }

        btnVoiceCommand.setOnClickListener {
            voiceRecognizer.startListening()
        }
    }

    private fun startAreyService() {
        val serviceIntent = Intent(this, AreyService::class.java)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            startForegroundService(serviceIntent)
        } else {
            startService(serviceIntent)
        }
    }

    private fun syncContactsToServer() {
        val contacts = contactsSync.readContacts()
        if (contacts.isEmpty()) {
            Toast.makeText(this, "No se encontraron contactos para sincronizar.", Toast.LENGTH_SHORT).show()
            return
        }

        val prefs = getSharedPreferences("arey_prefs", Context.MODE_PRIVATE)
        val wsUrl = prefs.getString("server_ws_url", "") ?: ""
        val httpUrl = wsUrl.replace("ws://", "http://").replace("wss://", "https://").substringBefore("/ws") + "/api/contacts/sync"

        CoroutineScope(Dispatchers.IO).launch {
            try {
                val jsonPayload = Gson().toJson(mapOf("contacts" to contacts))
                val body = jsonPayload.toRequestBody("application/json".toMediaType())
                val request = Request.Builder().url(httpUrl).post(body).build()
                val response = httpClient.newCall(request).execute()

                withContext(Dispatchers.Main) {
                    if (response.isSuccessful) {
                        Toast.makeText(this@MainActivity, "✅ Sincronizados ${contacts.size} contactos con Arey.", Toast.LENGTH_LONG).show()
                    } else {
                        Toast.makeText(this@MainActivity, "Error al sincronizar: ${response.code}", Toast.LENGTH_SHORT).show()
                    }
                }
            } catch (e: Exception) {
                withContext(Dispatchers.Main) {
                    Toast.makeText(this@MainActivity, "Error conectando al servidor: ${e.message}", Toast.LENGTH_SHORT).show()
                }
            }
        }
    }

    private fun initVoiceRecognizer() {
        voiceRecognizer = VoiceRecognizer(this) { spokenText ->
            Toast.makeText(this, "Arey escuchó: $spokenText", Toast.LENGTH_SHORT).show()
            // Enviar al servidor HTTP o por Service
        }
        voiceRecognizer.init()
    }

    private fun checkAndRequestPermissions() {
        val missingPermissions = requiredPermissions.filter {
            ContextCompat.checkSelfPermission(this, it) != PackageManager.PERMISSION_GRANTED
        }

        if (missingPermissions.isNotEmpty()) {
            ActivityCompat.requestPermissions(this, missingPermissions.toTypedArray(), 1001)
        }
    }

    override fun onDestroy() {
        voiceRecognizer.destroy()
        super.onDestroy()
    }
}
