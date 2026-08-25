import os
from dotenv import load_dotenv

load_dotenv()

# Dirección del Servidor Arey en la Nube 24/7 (Render)
SERVER_WS_URL = os.getenv("AREY_SERVER_WS_URL", "wss://arey2-1.onrender.com/ws/device/pc")
SERVER_HTTP_URL = os.getenv("AREY_SERVER_HTTP_URL", "https://arey2-1.onrender.com")
DEVICE_AUTH_TOKEN = os.getenv("DEVICE_AUTH_TOKEN", "arey-secret-token-2026")

# Configuración de Voz
VOICE_NAME = os.getenv("VOICE_NAME", "es-MX-DaliaNeural") # Voz neuronal en español ultra realista de Edge-TTS
WAKE_WORDS = ["arey", "oye arey", "hey arey", "ari", "aree"]
MICROPHONE_INDEX = None # None para micrófono predeterminado de Windows
