import logging
import time
import speech_recognition as sr
from config import WAKE_WORDS

logger = logging.getLogger("AreyPC")

EXTENDED_WAKE_WORDS = [
    "arey", "ari", "aree", "haré", "aré", "aire", "harry", "are", 
    "oye arey", "hey arey", "hola arey", "oye", "hey", "hola", "alexa"
]

class WakeWordDetector:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 180
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold = 0.5
        self.is_running = True

    def listen_for_wake_word(self) -> bool:
        """
        Escucha continuamente en segundo plano hasta detectar la palabra de activación 'Arey'.
        """
        try:
            with sr.Microphone() as source:
                logger.info("🎤 Calibrando micrófono...")
                self.recognizer.adjust_for_ambient_noise(source, duration=0.6)
                logger.info("🎤 [MICRÓFONO LISTO] Puedes hablar: di 'Arey' u 'Oye Arey'...")

                while self.is_running:
                    try:
                        # Escuchar fragmento de audio
                        audio = self.recognizer.listen(source, timeout=None, phrase_time_limit=4.0)
                        try:
                            text = self.recognizer.recognize_google(audio, language="es-MX").lower().strip()
                            logger.info(f"🔊 Escuché: '{text}'")
                            
                            # Comprobar si contiene 'Arey' o palabras clave
                            if any(w in text for w in EXTENDED_WAKE_WORDS):
                                logger.info(f"✨ ¡Activación detectada! -> '{text}'")
                                return True
                        except sr.UnknownValueError:
                            # Sonido no reconocido como palabra, continuar escuchando
                            continue
                        except sr.RequestError as e:
                            logger.warning(f"Error de conexión en reconocimiento: {e}")
                            time.sleep(1)
                            continue
                    except sr.WaitTimeoutError:
                        continue
                    except Exception as e:
                        logger.debug(f"Ciclo audio: {e}")
                        time.sleep(0.5)
                        continue
        except Exception as e:
            logger.error(f"Error accediendo al micrófono: {e}")
            time.sleep(2) # Evitar bucle rápido si el dispositivo está ocupado

        return False

wake_detector = WakeWordDetector()
