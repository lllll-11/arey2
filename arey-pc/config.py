import os
from dotenv import load_dotenv

ENV_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), ".env"))
SERVER_ENV = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "arey-server", ".env"))

if os.path.exists(ENV_PATH):
    load_dotenv(ENV_PATH)
elif os.path.exists(SERVER_ENV):
    load_dotenv(SERVER_ENV)
else:
    load_dotenv()

# Inteligencia Artificial Gemini Local Directa
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")

# Dirección del Servidor Arey en la Nube (Opcional para telemetría y celular)
SERVER_WS_URL = os.getenv("AREY_SERVER_WS_URL", "wss://arey2-1.onrender.com/ws/device/pc")
SERVER_HTTP_URL = os.getenv("AREY_SERVER_HTTP_URL", "https://arey2-1.onrender.com")
DEVICE_AUTH_TOKEN = os.getenv("DEVICE_AUTH_TOKEN", "arey-secret-token-2026")

# Configuración de Voz
VOICE_NAME = os.getenv("VOICE_NAME", "es-MX-DaliaNeural")
WAKE_WORDS = ["arey", "oye arey", "hey arey", "ari", "aree"]
MICROPHONE_INDEX = None
