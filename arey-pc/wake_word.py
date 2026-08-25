import logging
import speech_recognition as sr
from config import WAKE_WORDS

logger = logging.getLogger("WakeWord")

# Palabras fonéticas para detectar la activación de Arey fácilmente
EXTENDED_WAKE_WORDS = [
    "arey", "ari", "aree", "haré", "aré", "aire", "harry", "are", 
    "oye arey", "hey arey", "hola arey", "oye", "hey", "hola"
]

class WakeWordDetector:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 150
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.dynamic_energy_adjustment_damping = 0.15
        self.recognizer.pause_threshold = 0.4
        self.is_running = True

    def listen_for_wake_word(self) -> bool:
        """
        Escucha continuamente en segundo plano hasta detectar la palabra de activación 'Arey'.
        """
        try:
            with sr.Microphone() as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.4)
                logger.info("🎤 [MIC LISTO] Di 'Arey' o 'Oye Arey' en voz alta...")

                while self.is_running:
                    try:
                        audio = self.recognizer.listen(source, timeout=3.0, phrase_time_limit=3.0)
                        try:
                            text = self.recognizer.recognize_google(audio, language="es-MX").lower().strip()
                            logger.debug(f"Audio captado: '{text}'")
                            
                            # Comprobar si coincide con 'Arey' o variantes
                            if any(w in text for w in EXTENDED_WAKE_WORDS):
                                logger.info(f"✨ ¡Activación detectada! -> '{text}'")
                                return True
                        except (sr.UnknownValueError, sr.WaitTimeoutError):
                            continue
                    except sr.WaitTimeoutError:
                        continue
                    except Exception:
                        continue
        except Exception as e:
            logger.error(f"Error accediendo al micrófono: {e}")

        return False

wake_detector = WakeWordDetector()
