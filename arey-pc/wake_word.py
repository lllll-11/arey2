import logging
import time
import threading
import speech_recognition as sr
from audio_manager import get_microphone, create_recognizer, mic_lock

logger = logging.getLogger("AreyPC")

# Fonética amplia para detectar 'Arey' en cualquier pronunciación
WAKE_WORDS = [
    "arey", "ari", "aree", "haré", "aré", "are", "aire", "área", "area",
    "hari", "harry", "oye arey", "hey arey", "hola arey", "oye ari", "hey ari",
    "oye", "hey", "hola", "a ver", "aver", "ey", "dime", "asistente", "alexa"
]

class WakeWordDetector:
    def __init__(self):
        self.recognizer = create_recognizer()
        self.is_running = True
        self.manual_trigger = threading.Event()

    def trigger_manually(self):
        """
        Activa la escucha de inmediato cuando el usuario hace clic en el orbe flotante.
        """
        self.manual_trigger.set()

    def listen_for_wake_word(self) -> bool:
        """
        Escucha en segundo plano con alta sensibilidad y detecta 'Arey' o clic en el orbe.
        """
        if self.manual_trigger.is_set():
            self.manual_trigger.clear()
            logger.info("✨ ¡Activación manual por clic en el orbe!")
            return True

        try:
            with mic_lock:
                mic = get_microphone()
                with mic as source:
                    logger.info("🎤 [ESCUCHANDO EN SEGUNDO PLANO] Di 'Arey' o haz clic en el orbe...")

                    while self.is_running:
                        if self.manual_trigger.is_set():
                            self.manual_trigger.clear()
                            logger.info("✨ ¡Activación manual por clic en el orbe!")
                            return True

                        try:
                            audio = self.recognizer.listen(source, timeout=0.8, phrase_time_limit=3.0)
                            try:
                                text = self.recognizer.recognize_google(audio, language="es-MX").lower().strip()
                                logger.info(f"🔊 Escuchado: '{text}'")

                                # Comprobar coincidencia fonética
                                words = text.split()
                                if any(w in WAKE_WORDS for w in words) or any(ww in text for ww in WAKE_WORDS):
                                    logger.info(f"✨ ¡Palabra de activación detectada! -> '{text}'")
                                    return True
                            except sr.UnknownValueError:
                                continue
                            except sr.RequestError:
                                time.sleep(0.3)
                                continue
                        except sr.WaitTimeoutError:
                            continue
                        except Exception as ex:
                            logger.debug(f"Ciclo wake: {ex}")
                            time.sleep(0.1)
                            continue
        except Exception as e:
            logger.error(f"Error en micrófono: {e}")
            time.sleep(1)

        return False

wake_detector = WakeWordDetector()
