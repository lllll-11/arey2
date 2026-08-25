import logging
import time
import threading
import tempfile
import os
import wave
import struct
import speech_recognition as sr
from audio_manager import get_microphone, create_recognizer, mic_lock

logger = logging.getLogger("AreyPC")

WAKE_WORDS = [
    "arey", "ari", "aree", "haré", "aré", "are", "aire",
    "hari", "harry", "oye arey", "hey arey", "hola arey",
    "oye", "hey", "dime", "asistente"
]

class WakeWordDetector:
    def __init__(self):
        # Reconocedor ultraliviano solo para detectar la palabra de activación
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 80
        self.recognizer.dynamic_energy_threshold = False
        self.recognizer.pause_threshold = 0.3      # Cortar rápido tras silencio
        self.recognizer.non_speaking_duration = 0.2
        self.is_running = True
        self.manual_trigger = threading.Event()

        # Pre-cargar Whisper tiny en memoria para reutilizarlo sin reiniciar
        try:
            from faster_whisper import WhisperModel
            self._whisper = WhisperModel("tiny", device="cpu", compute_type="int8")
            logger.info("Whisper tiny listo para wake word!")
            self._use_whisper = True
        except Exception:
            self._use_whisper = False

    def trigger_manually(self):
        self.manual_trigger.set()

    def _quick_transcribe(self, audio) -> str:
        """Transcripción rápida con Whisper tiny local (sin internet, ~150ms)."""
        if not self._use_whisper:
            return ""
        tmp_path = None
        try:
            wav_bytes = audio.get_wav_data(convert_rate=16000, convert_width=2)
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                f.write(wav_bytes)
                tmp_path = f.name
            segs, _ = self._whisper.transcribe(
                tmp_path, language="es", beam_size=1,
                vad_filter=True
            )
            return " ".join(s.text.strip() for s in segs).lower().strip()
        except Exception:
            return ""
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try: os.remove(tmp_path)
                except: pass

    def listen_for_wake_word(self) -> bool:
        if self.manual_trigger.is_set():
            self.manual_trigger.clear()
            logger.info("Activacion manual por clic en el orbe!")
            return True

        try:
            with mic_lock:
                mic = get_microphone()
                with mic as source:
                    logger.info("Escuchando... Di 'Arey' o haz clic en el orbe.")
                    while self.is_running:
                        if self.manual_trigger.is_set():
                            self.manual_trigger.clear()
                            return True
                        try:
                            audio = self.recognizer.listen(
                                source, timeout=0.5, phrase_time_limit=2.5
                            )
                            # Transcripción local instantánea con Whisper tiny
                            text = self._quick_transcribe(audio)
                            if text:
                                logger.info(f"Wake escucho: '{text}'")
                            if text and any(w in text for w in WAKE_WORDS):
                                logger.info(f"ACTIVADO! -> '{text}'")
                                return True
                        except sr.WaitTimeoutError:
                            continue
                        except Exception as ex:
                            logger.debug(f"wake loop: {ex}")
                            time.sleep(0.05)
        except Exception as e:
            logger.error(f"Error microfono wake: {e}")
            time.sleep(0.5)
        return False

wake_detector = WakeWordDetector()
