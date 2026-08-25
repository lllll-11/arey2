# 📱 Guía de Instalación y Configuración de la App Android para Arey

Esta app actúa como el puente físico para que Arey pueda controlar tu teléfono: **marcar llamadas telefónicas**, enviar mensajes por WhatsApp/SMS, hacer sonar la alarma para encontrar el teléfono, controlar volumen, linterna y escuchar tu voz.

---

## 🛠️ Paso 1: Compilar la App en Android Studio o Generar el APK

1. Abre **Android Studio** en tu PC.
2. Selecciona **"Open"** y abre la carpeta `arey-android/`.
3. Espera a que Gradle sincronice las dependencias automáticamente.
4. Conecta tu teléfono Android a la PC por cable USB con la **Depuración por USB activada** (en Opciones de desarrollador).
5. Haz clic en el botón verde **"Run" (▶️)** para instalarla directamente en tu teléfono.
   - *Alternativa*: Puedes ir a **Build > Build Bundle(s) / APK(s) > Build APK(s)** y pasar el archivo `.apk` generado a tu teléfono.

---

## ⚙️ Paso 2: Conceder Permisos Esenciales en tu Teléfono

Para que Arey tenga control total sin interrupciones, asegúrate de otorgar los siguientes permisos cuando la app los solicite:

1. **Llamadas Telefónicas (`CALL_PHONE`)**:
   - Permite que Arey marque y llame a tus contactos automáticamente cuando se lo pidas desde la laptop, el teléfono o Alexa.
2. **Contactos (`READ_CONTACTS`)**:
   - Permite sincronizar los nombres y teléfonos con la memoria compartida de Arey para que entienda comandos como *"Llama a Mamá"* o *"Mándale un mensaje a Carlos"*.
3. **SMS y Mensajería (`SEND_SMS`)**:
   - Permite redactar y enviar mensajes.
4. **Micrófono y Audio (`RECORD_AUDIO`)**:
   - Para que el teléfono reaccione a tus órdenes de voz.
5. **Cámara (`CAMERA / FLASH`)**:
   - Para encender la linterna y activar la luz parpadeante de localización.
6. **Optimización de Batería (Muy Importante)**:
   - Ve a **Ajustes de Android > Aplicaciones > Arey Assistant > Batería > Sin Restricciones** (o Desactivar optimización de batería). Esto garantiza que el servicio en segundo plano siga conectado 24/7 incluso con la pantalla apagada.

---

## 🔗 Paso 3: Conectar la App al Servidor Central

1. Abre la app **Arey Assistant** en tu teléfono.
2. En el campo **"URL del Servidor Central"**, escribe la dirección WebSocket de tu servidor:
   - Si tu servidor está en Hugging Face:
     `wss://tu-usuario-arey-brain.hf.space/ws/device/android`
   - Si tu servidor está en tu red local (misma WiFi):
     `ws://192.168.1.XX:8000/ws/device/android`
3. Presiona el botón azul **"Conectar y Activar Servicio 24/7"**.
4. Presiona el botón verde **"Sincronizar Contactos con Arey"** para que Arey aprenda tu agenda telefónica.
5. Verás una notificación fija en la barra de estado indicando que **Arey Assistant está activo y conectado**.
