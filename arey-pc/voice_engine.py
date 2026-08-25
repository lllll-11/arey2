import os
import io
import time
import asyncio
import tempfile
import logging
import numpy as np
import speech_recognition as sr
import edge_tts
import pygame
from faster_whisper import WhisperModel

from config import VOICE_NAME
from audio_manager import get_microphone, create_recognizer, mic_lock

logger = logging.getLogger("VoiceEngine")

class VoiceEngine:
    def __init__(self):
        pygame.mixer.init()
        self.recognizer = create_recognizer()

        logger.info("Cargando motor neuronal Whisper...")
        self.whisper_model = WhisperModel("base", device="cpu", compute_type="int8")
        logger.info("Motor Whisper listo!")

        self.instant_wake_sound = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "assets", "si.mp3")
        )

    def play_instant_wake(self):
        try:
            if os.path.exists(self.instant_wake_sound):
                pygame.mixer.music.load(self.instant_wake_sound)
                pygame.mixer.music.play()
        except Exception as e:
            logger.debug(f"Error audio instantáneo: {e}")

    async def speak(self, text: str):
        if not text or not text.strip():
            return
        logger.info(f"Arey diciendo: '{text}'")
        try:
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as fp:
                temp_path = fp.name

            communicate = edge_tts.Communicate(text, voice=VOICE_NAME, rate="+8%", pitch="+0Hz")
            await communicate.save(temp_path)

            pygame.mixer.music.load(temp_path)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                await asyncio.sleep(0.04)
            pygame.mixer.music.unload()

            try:
                os.remove(temp_path)
            except Exception:
                pass
        except Exception as e:
            logger.error(f"Error en voz: {e}")

    def _transcribe_whisper(self, wav_bytes: bytes) -> str:
        """
        Transcribe WAV bytes con Faster-Whisper guardando en archivo temporal.
        Faster-Whisper requiere ruta de archivo, no BytesIO.
        """
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                f.write(wav_bytes)
                tmp_path = f.name

            segments, _ = self.whisper_model.transcribe(
                tmp_path,
                language="es",
                beam_size=1,
                vad_filter=True,
                initial_prompt="Asistente personal en español. Comandos de voz, nombres, acciones cotidianas."
            )
            text = " ".join(s.text.strip() for s in segments).strip()
            return text
        except Exception as e:
            logger.warning(f"Whisper falló: {e}")
            return ""
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass

    def listen_speech(self, timeout: float = 6.0, phrase_time_limit: float = 12.0) -> str:
        time.sleep(0.05)
        try:
            with mic_lock:
                mic = get_microphone()
                with mic as source:
                    logger.info("👂 Escuchando tu orden...")
                    audio = self.recognizer.listen(
                        source, timeout=timeout, phrase_time_limit=phrase_time_limit
                    )

                    wav_bytes = audio.get_wav_data(convert_rate=16000, convert_width=2)

                    # 1. Whisper local con archivo temporal (correcto)
                    result = self._transcribe_whisper(wav_bytes)
                    if result:
                        logger.info(f"✨ [WHISPER] '{result}'")
                        return result

                    # 2. Fallback Google Speech
                    result = self.recognizer.recognize_google(audio, language="es-MX")
                    logger.info(f"🗣️ [Google] '{result}'")
                    return result

        except sr.WaitTimeoutError:
            logger.info("Tiempo de espera agotado.")
            return ""
        except sr.UnknownValueError:
            logger.info("No se entendió el audio.")
            return ""
        except Exception as e:
            logger.warning(f"Error capturando voz: {e}")
            return ""

voice_engine = VoiceEngine()
