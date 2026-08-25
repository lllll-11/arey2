import logging
import speech_recognition as sr
from config import WAKE_WORDS

logger = logging.getLogger("WakeWord")

class WakeWordDetector:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 250
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold = 0.5
        self.is_running = True

    def listen_for_wake_word(self) -> bool:
        """
        Escucha continuamente en segundo plano hasta detectar la palabra de activación 'Arey'.
        """
        with sr.Microphone() as source:
            # Calibrar brevemente ruido de fondo
            self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
            logger.info("Esperando palabra de activación 'Arey'...")

            while self.is_running:
                try:
                    # Escuchar fragmento corto
                    audio = self.recognizer.listen(source, timeout=3.0, phrase_time_limit=3.0)
                    try:
                        text = self.recognizer.recognize_google(audio, language="es-MX").lower()
                        # Comprobar si contiene alguna de las palabras clave
                        if any(w in text for w in WAKE_WORDS):
                            logger.info(f"¡Activación detectada! -> '{text}'")
                            return True
                    except (sr.UnknownValueError, sr.WaitTimeoutError):
                        continue
                except sr.WaitTimeoutError:
                    continue
                except Exception as e:
                    logger.debug(f"Ciclo wake word: {e}")
                    continue

        return False

wake_detector = WakeWordDetector()
