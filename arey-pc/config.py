import os
from dotenv import load_dotenv

load_dotenv()

# Dirección del Servidor Arey (en local o en la nube gratuita ej: wss://tu-espacio.hf.space)
SERVER_WS_URL = os.getenv("AREY_SERVER_WS_URL", "ws://localhost:8000/ws/device/pc")
SERVER_HTTP_URL = os.getenv("AREY_SERVER_HTTP_URL", "http://localhost:8000")
DEVICE_AUTH_TOKEN = os.getenv("DEVICE_AUTH_TOKEN", "arey-secret-token-2026")

# Configuración de Voz
VOICE_NAME = os.getenv("VOICE_NAME", "es-MX-DaliaNeural") # Voz neuronal en español ultra realista de Edge-TTS
WAKE_WORDS = ["arey", "oye arey", "hey arey", "ari", "aree"]
MICROPHONE_INDEX = None # None para micrófono predeterminado de Windows
