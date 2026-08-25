import logging
import time
import speech_recognition as sr

logger = logging.getLogger("AreyPC")

# Solo se activa cuando dices explícitamente el nombre de Arey
STRICT_WAKE_WORDS = [
    "arey", "ari", "aree", "haré", "aré", "oye arey", "hey arey", "hola arey", "oye ari"
]

class WakeWordDetector:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 200
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold = 0.4
        self.is_running = True

    def listen_for_wake_word(self) -> bool:
        """
        Escucha en segundo plano y SOLO se activa cuando el usuario dice 'Arey'.
        """
        try:
            with sr.Microphone() as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.4)
                logger.info("🎤 [ESCUCHANDO EN SEGUNDO PLANO] Di 'Arey' para activarme...")

                while self.is_running:
                    try:
                        audio = self.recognizer.listen(source, timeout=None, phrase_time_limit=3.0)
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
                    except Exception:
                        time.sleep(0.2)
                        continue
        except Exception as e:
            logger.error(f"Error en micrófono: {e}")
            time.sleep(1)

        return False

wake_detector = WakeWordDetector()
