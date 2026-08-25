import logging
import time
import speech_recognition as sr
from audio_manager import get_microphone, create_recognizer, mic_lock

logger = logging.getLogger("AreyPC")

STRICT_WAKE_WORDS = [
    "arey", "ari", "aree", "haré", "aré", "oye arey", "hey arey", "hola arey", "oye ari"
]

class WakeWordDetector:
    def __init__(self):
        self.recognizer = create_recognizer()
        self.is_running = True

    def listen_for_wake_word(self) -> bool:
        """
        Escucha en segundo plano y detecta de forma estricta la palabra 'Arey'.
        """
        try:
            with mic_lock:
                mic = get_microphone()
                with mic as source:
                    self.recognizer.adjust_for_ambient_noise(source, duration=0.4)
                    logger.info("🎤 [ESCUCHANDO EN SEGUNDO PLANO] Di 'Arey' para activarme...")

                    while self.is_running:
                        try:
                            audio = self.recognizer.listen(source, timeout=None, phrase_time_limit=3.5)
                            try:
                                text = self.recognizer.recognize_google(audio, language="es-MX").lower().strip()
                                
                                # Comprobar estrictamente si contiene la palabra 'Arey'
                                words = text.split()
                                if any(w in STRICT_WAKE_WORDS for w in words) or any(sw in text for sw in STRICT_WAKE_WORDS):
                                    logger.info(f"✨ ¡Palabra de activación detectada! -> '{text}'")
                                    return True
                            except sr.UnknownValueError:
                                continue
                            except sr.RequestError:
                                time.sleep(0.5)
                                continue
                        except sr.WaitTimeoutError:
                            continue
                        except Exception as ex:
                            logger.debug(f"Ciclo wake: {ex}")
                            time.sleep(0.2)
                            continue
        except Exception as e:
            logger.error(f"Error en micrófono: {e}")
            time.sleep(1)

        return False

wake_detector = WakeWordDetector()
