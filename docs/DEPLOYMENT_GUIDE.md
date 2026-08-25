# 🚀 Guía de Despliegue del Servidor Arey (100% Gratis)

Esta guía te explica cómo alojar el cerebro central de **Arey** en la nube de forma **totalmente gratuita**, con soporte 24/7 para WebSockets y llamadas a Gemini 3.5 Flash.

---

## 🔑 Paso 1: Obtener tu Clave de API Gratuita de Google AI Studio

1. Ve a [Google AI Studio](https://aistudio.google.com/).
2. Inicia sesión con tu cuenta de Google.
3. Haz clic en el botón azul **"Get API Key"** (Obtener clave de API).
4. Crea una nueva clave o selecciona un proyecto de Google Cloud existente.
5. Copia la clave generada (empieza por `AIzaSy...`).

---

## 🌐 Opción A: Despliegue 24/7 en Hugging Face Spaces (Recomendada)

Hugging Face Spaces ofrece contenedores Docker gratuitos 24/7 con 16 GB de RAM, 2 vCPU y certificado SSL automático sin costo.

1. Entra a [Hugging Face](https://huggingface.co/) y crea una cuenta si no tienes una.
2. Ve a [huggingface.co/spaces](https://huggingface.co/spaces) y haz clic en **"Create new Space"**.
3. Configuración del Space:
   - **Space name**: `arey-brain` (o el nombre que elijas).
   - **License**: `mit` o `apache-2.0`.
   - **Space SDK**: Selecciona **`Docker`** -> **`Blank`**.
   - **Space Hardware**: `Free (CPU basic - 2 vCPU · 16 GB RAM)`.
   - **Privacy**: `Public` (o `Private` si deseas).
4. Haz clic en **"Create Space"**.
5. Ve a la pestaña **"Files"** de tu nuevo Space y sube todos los archivos dentro de la carpeta `arey-server/`:
   - `app/` (con todos sus archivos y subcarpetas)
   - `Dockerfile`
   - `requirements.txt`
6. Ve a la pestaña **"Settings"** de tu Space, baja a la sección **"Variables and secrets"** y agrega un secreto:
   - Nombre: `GEMINI_API_KEY`
   - Valor: *Pega tu clave de Google AI Studio*
   - Nombre (opcional): `GEMINI_MODEL` con valor `gemini-3.5-flash`
7. ¡Listo! Hugging Face construirá la imagen en 1 minuto.
8. Tu URL será:
   - **REST / Web**: `https://<tu-usuario>-arey-brain.hf.space`
   - **WebSocket (PC y Android)**: `wss://<tu-usuario>-arey-brain.hf.space/ws/device/<pc|android>`

---

## 🌐 Opción B: Despliegue en Render.com (Gratis)

1. Sube tu código a un repositorio de GitHub (público o privado).
2. Entra a [Render.com](https://render.com/) e inicia sesión.
3. Haz clic en **"New"** -> **"Web Service"**.
4. Conecta tu repositorio y selecciona la subcarpeta `arey-server`.
5. Configura:
   - **Runtime**: `Python` o `Docker`.
   - **Build Command**: `pip install -r requirements.txt` (si usas Python)
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Instance Type**: `Free`.
6. En **Environment Variables**, añade:
   - `GEMINI_API_KEY`: *Tu clave de Google AI Studio*
   - `GEMINI_MODEL`: `gemini-3.5-flash`
7. Haz clic en **"Create Web Service"**.

---

## 💻 Opción C: Ejecución Local en tu Laptop con Cloudflare Tunnel

Si prefieres que el servidor corra directamente en tu laptop sin depender de la nube:

1. Entra a la carpeta `arey-server`:
   ```bash
   cd arey-server
   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
   ```
2. Crea el archivo `.env` copiando `.env.example` y pega tu `GEMINI_API_KEY`.
3. Inicia el servidor:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```
4. Para conectar tu teléfono desde fuera de casa, puedes usar el túnel gratuito de Cloudflare:
   ```bash
   cloudflared tunnel --url http://localhost:8000
   ```
   Te dará una URL segura `https://xxx.trycloudflare.com` que puedes poner en tu app de Android.
