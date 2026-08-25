import logging
import time
import speech_recognition as sr
from config import WAKE_WORDS

logger = logging.getLogger("AreyPC")

# Palabras clave de activación (nombre de Arey)
WAKE_KEYWORDS = [
    "arey", "ari", "aree", "haré", "aré", "aire", "harry", "are", 
    "oye arey", "hey arey", "hola arey", "oye ari", "hey ari", "oye", "alexa"
]

# Acciones directas que activan la ejecución inmediata aunque no digas 'Arey'
DIRECT_COMMAND_TRIGGERS = [
    "teléfono", "telefono", "celular", "busca mi", "dónde está", "donde esta",
    "abre", "abrir", "pon ", "reproduce", "apaga", "prende", "encender",
    "volumen", "silencia", "pausa", "continua", "qué hora", "que hora",
    "clima", "cómo estás", "como estas", "quién eres", "quien eres", "alarma"
]

class WakeWordDetector:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 180
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold = 0.5
        self.is_running = True

    def listen_for_wake_word_or_command(self) -> dict:
        """
        Escucha continuamente. Si detecta 'Arey' o una orden directa (ej: 'busca mi teléfono'),
        lo procesa al instante.
        Retorna dict con:
          - 'activated': bool
          - 'direct_command': str (si el usuario ya dijo la orden completa, ej: 'busca mi teléfono')
        """
        try:
            with sr.Microphone() as source:
                logger.info("🎤 Calibrando micrófono...")
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                logger.info("🎤 [MICRÓFONO LISTO] Di 'Arey' o una orden directa (ej: 'busca mi teléfono')...")

                while self.is_running:
                    try:
                        audio = self.recognizer.listen(source, timeout=None, phrase_time_limit=5.0)
                        try:
                            text = self.recognizer.recognize_google(audio, language="es-MX").lower().strip()
                            logger.info(f"🔊 Escuché: '{text}'")
                            
                            # 1. Comprobar si contiene 'Arey'
                            contains_wake = any(w in text for w in WAKE_KEYWORDS)
                            # 2. Comprobar si es una orden directa
                            is_direct_cmd = any(c in text for c in DIRECT_COMMAND_TRIGGERS)

                            if contains_wake or is_direct_cmd:
                                logger.info(f"✨ ¡Activación detectada! -> '{text}'")
                                
                                # Limpiar la palabra de activación del texto si la incluye
                                cleaned_cmd = text
                                for w in WAKE_KEYWORDS:
                                    cleaned_cmd = cleaned_cmd.replace(w, "").strip()

                                # Si después de quitar 'Arey' aún queda una orden (ej: 'busca mi teléfono')
                                if len(cleaned_cmd) > 2:
                                    return {"activated": True, "direct_command": cleaned_cmd}
                                else:
                                    # Solo dijo 'Arey', pedirle la orden
                                    return {"activated": True, "direct_command": None}

                        except sr.UnknownValueError:
                            continue
                        except sr.RequestError as e:
                            logger.warning(f"Error de conexión en reconocimiento: {e}")
                            time.sleep(1)
                            continue
                    except sr.WaitTimeoutError:
                        continue
                    except Exception as e:
                        logger.debug(f"Ciclo audio: {e}")
                        time.sleep(0.3)
                        continue
        except Exception as e:
            logger.error(f"Error accediendo al micrófono: {e}")
            time.sleep(2)

        return {"activated": False, "direct_command": None}

wake_detector = WakeWordDetector()
