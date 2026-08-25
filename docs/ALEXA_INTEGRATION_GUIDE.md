# 🗣️ Guía de Integración de Arey con Amazon Alexa

Esta guía te muestra cómo conectar tus dispositivos **Amazon Echo / Alexa** con el cerebro central de **Arey** para poder hablarle a cualquier Alexa y controlar tu teléfono y laptop con la misma memoria compartida.

---

## 🛠️ Paso 1: Crear una Skill Personalizada en Amazon Developer Console

1. Entra a [Alexa Developer Console](https://developer.amazon.com/alexa/console/ask) con tu cuenta de Amazon.
2. Haz clic en **"Create Skill"**.
3. Configuración inicial:
   - **Skill name**: `Arey`
   - **Primary locale**: `Spanish (ES)` o `Spanish (MX)` (el que uses en tu Alexa).
   - **Experience**: `Other` -> `Custom`.
   - **Hosting service**: Selecciona **`Provision your own`** (Proveer tu propio backend).
4. Haz clic en **"Create skill"** y selecciona la plantilla **"Start from Scratch"**.

---

## 🎯 Paso 2: Configurar la Invocación y los Intents

1. En el menú lateral izquierdo, ve a **Invocation > Skill Invocation Name**.
2. Escribe como nombre de invocación: **`arey`**. (Así podrás decir *"Alexa, abre arey"* o *"Alexa, dile a arey que llame a mamá"*).
3. Ve a **Interaction Model > Intents > Add Intent**.
4. Nombre del intent: **`AskAreyIntent`**.
5. Agrega un Slot:
   - Nombre: `command`
   - Tipo de Slot: `AMAZON.SearchQuery`
6. En **Sample Utterances**, añade frases como:
   - `{command}`
   - `dile que {command}`
   - `haz {command}`
   - `pide a arey {command}`
7. Haz clic en **"Save Model"** y luego en **"Build Model"**.

---

## 🌐 Paso 3: Conectar el Endpoint HTTPS de tu Servidor Arey

1. En el menú superior o lateral, haz clic en **Endpoint**.
2. Selecciona **`HTTPS`**.
3. En **Default Region**, pega la URL pública del endpoint de Alexa de tu servidor Arey:
   - `https://tu-usuario-arey-brain.hf.space/api/alexa` (si usas Hugging Face)
   - O `https://tu-dominio-render.com/api/alexa`
4. En el menú desplegable del certificado SSL, selecciona:
   - **"My development endpoint is a sub-domain of a domain that has a wildcard certificate from a certificate authority"**.
5. Haz clic en **"Save Endpoints"**.

---

## 🧪 Paso 4: Probar en tus Dispositivos Echo

1. Ve a la pestaña **Test** en la consola de Alexa.
2. Cambia la opción a **"Development"**.
3. Ahora puedes probarlo hablando a tu bocina Alexa vinculada a tu cuenta de Amazon:
   - *"Alexa, dile a Arey que suba el volumen de mi laptop"*
   - *"Alexa, dile a Arey que marque a Carlos"*
   - *"Alexa, dile a Arey que busque mi teléfono"*
