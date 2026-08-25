# 🌌 AREY AI - Asistente Inteligente Multi-Dispositivo con Auto-Aprendizaje

**Arey** es un ecosistema de Inteligencia Artificial centralizado impulsado por **Gemini 3.5 Flash**, diseñado para controlar tu **Laptop (Windows)**, tu **Teléfono (Android)** y dispositivos **Alexa / Smart Home** bajo una **memoria única y compartida**, **activación por voz ("Arey")** y un motor de **Auto-Aprendizaje Autónomo**.

---

## 🌟 Características Principales

- 🧠 **Cerebro Central con Memoria Única**: No existen chats separados. Todo lo que hablas o haces en tu laptop, teléfono o Alexa se sincroniza en una sola línea de tiempo continua.
- 🗣️ **Activación por Voz Manos Libres ("Arey")**: La laptop y el celular escuchan cuando dices *"Arey"* o *"Oye Arey"*, procesan tu comando y responden con voz neuronal ultra realista (**Edge-TTS**).
- 📱 **Control Total de tu Teléfono Android**:
  - 📞 **Llamadas telefónicas directas**: *"Arey, marca a Mamá"* o *"Arey, llama al 5512345678"*.
  - 💬 **Mensajería**: Enviar SMS y abrir WhatsApp con mensajes redactados.
  - 🚨 **"Encuentra mi teléfono"**: Si no encuentras tu cel, dile a la laptop *"Arey, ¿dónde está mi teléfono?"* y el celular sonará a volumen máximo con la linterna parpadeando aunque esté en silencio.
  - 🔦 **Control de Hardware**: Linterna, volumen, porcentaje de batería y apertura de aplicaciones (YouTube, Spotify, Mapas, Cámara).
  - 📇 **Sincronización de Agenda**: Aprende tus contactos para llamarlos por su nombre.
- 💻 **Control Total de tu Laptop Windows**:
  - 🔊 Ajustar volumen, silenciar, pausar o cambiar canciones (Spotify, YouTube, VLC).
  - 🚀 Abrir aplicaciones (Chrome, VS Code, Bloc de notas, Calculadora, Explorador).
  - 🔒 Bloquear la sesión de Windows al instante.
  - 👁️ **Visión de Pantalla (Screen Vision)**: *"Arey, ¿qué error sale en mi pantalla?"* o *"Arey, resume este documento"*.
- 📈 **Auto-Aprendizaje Autónomo (Self-Learning)**:
  - 💡 **Extracción de Hechos**: Memoriza gustos, fechas, reglas y datos de tus seres queridos automáticamente.
  - 📋 **Creación Dinámica de Rutinas**: *"Arey, aprende una rutina: cuando diga 'Modo Cine', pon el volumen de la laptop al 70%, apaga la luz y abre Netflix"*.
- ☁️ **Alojamiento en la Nube 100% Gratuito**: Listo para desplegar en **Hugging Face Spaces (24/7 Gratis con Docker)** o **Render**.

---

## 📂 Estructura del Repositorio

```
arey2/
├── arey-server/                     # Cerebro Central en FastAPI (Nube / Local)
│   ├── app/
│   │   ├── main.py                  # Servidor con WebSockets y REST
│   │   ├── config.py                # Configuración y variables de entorno
│   │   ├── ai/
│   │   │   ├── brain.py             # Gemini 3.5 Flash con Function Calling
│   │   │   ├── memory.py            # Base de datos SQLite y memoria unificada
│   │   │   ├── learning.py          # Motor de Auto-Aprendizaje y Rutinas
│   │   │   ├── tools.py             # Herramientas para Teléfono, PC y Web
│   │   │   └── vision.py            # Análisis multimodal de pantalla
│   │   ├── devices/
│   │   │   ├── broker.py            # Enrutador WebSocket en tiempo real
│   │   │   └── state.py             # Estado y telemetría de dispositivos
│   │   ├── scheduler/
│   │   │   └── timer.py             # Alarmas y recordatorios en segundo plano
│   │   └── integrations/
│   │       └── alexa.py             # Integración con Amazon Alexa Skill
│   ├── Dockerfile                   # Despliegue listo para Hugging Face / Render
│   └── requirements.txt
│
├── arey-pc/                         # Agente de Fondo para Laptop (Windows)
│   ├── client.py                    # Conexión WebSocket y receptor de órdenes
│   ├── wake_word.py                 # Detector de voz "Arey"
│   ├── voice_engine.py              # Síntesis Edge-TTS y Reconocimiento de voz
│   ├── pc_controller.py             # Acciones nativas en Windows
│   ├── requirements.txt
│   └── start_pc_agent.bat           # Lanzador en un clic
│
├── arey-android/                    # App Android Nativa en Kotlin
│   ├── app/src/main/
│   │   ├── AndroidManifest.xml      # Permisos de llamadas, SMS, linterna
│   │   ├── java/com/arey/assistant/
│   │   │   ├── MainActivity.kt      # Interfaz y sincronización de contactos
│   │   │   ├── AreyService.kt       # Servicio 24/7 en segundo plano
│   │   │   ├── DeviceController.kt  # Ejecutor de llamadas, SMS, linterna
│   │   │   ├── ContactsSync.kt      # Sincronizador de agenda
│   │   │   └── VoiceRecognizer.kt   # Reconocedor de voz
│   │   └── res/                     # Layouts Material3 e iconos
│   ├── build.gradle.kts
│   └── settings.gradle.kts
│
└── docs/
    ├── DEPLOYMENT_GUIDE.md          # Cómo desplegar el servidor gratis 24/7
    ├── ANDROID_SETUP_GUIDE.md       # Cómo instalar la app en tu teléfono
    └── ALEXA_INTEGRATION_GUIDE.md   # Conexión con bocinas Alexa Echo
```

---

## ⚡ Guía de Inicio Rápido

### 1. Iniciar el Servidor Central
1. Ve a `arey-server/`.
2. Crea tu archivo `.env` a partir de `.env.example` y coloca tu `GEMINI_API_KEY` gratuita de [Google AI Studio](https://aistudio.google.com/).
3. Ejecuta el servidor:
   ```bash
   pip install -r requirements.txt
   uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```
4. *(Opcional para 24/7 en la nube)*: Sigue la [Guía de Despliegue Gratuito](docs/DEPLOYMENT_GUIDE.md).

### 2. Iniciar el Agente de Laptop (Windows)
1. Ve a la carpeta `arey-pc/`.
2. Haz doble clic en **`start_pc_agent.bat`**.
3. ¡Di en voz alta **"Arey"** y pídele lo que quieras!

### 3. Instalar la App en tu Teléfono (Android)
1. Sigue la [Guía de Configuración Android](docs/ANDROID_SETUP_GUIDE.md).
2. Abre la app, escribe la URL del servidor y presiona **"Conectar y Activar Servicio 24/7"**.
3. Presiona **"Sincronizar Contactos con Arey"**.

---

## 🗣️ Ejemplos de lo que puedes decirle a Arey

- *"Arey, marca a Mamá por favor."*
- *"Arey, ¿dónde está mi teléfono?"* *(Tu celular comenzará a sonar y parpadear).*
- *"Arey, sube el volumen de mi laptop al 80% y abre Spotify."*
- *"Arey, ¿qué error sale en mi pantalla?"*
- *"Arey, mándale un WhatsApp a Carlos diciéndole que ya voy saliendo."*
- *"Arey, aprende una rutina: cuando diga 'Modo Estudio', pon la compu en silencio y abre VS Code."*
- *"Arey, recuérdame en 20 minutos revisar el correo."*
