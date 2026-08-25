import os
import time
import asyncio
import tempfile
import logging
import speech_recognition as sr
import edge_tts
import pygame
import httpx
from config import VOICE_NAME, SERVER_HTTP_URL
from audio_manager import get_microphone, create_recognizer, mic_lock

logger = logging.getLogger("VoiceEngine")

class VoiceEngine:
    def __init__(self):
        pygame.mixer.init()
        self.recognizer = create_recognizer()

    async def speak(self, text: str):
        """
        Sintetiza la voz usando la red neuronal de Edge-TTS (calidad humana 100% gratuita).
        """
        if not text or not text.strip():
            return

        logger.info(f"Arey diciendo: '{text}'")
        try:
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as fp:
                temp_audio_path = fp.name

            communicate = edge_tts.Communicate(text, voice=VOICE_NAME, rate="+6%", pitch="+0Hz")
            await communicate.save(temp_audio_path)

            pygame.mixer.music.load(temp_audio_path)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                await asyncio.sleep(0.05)

            pygame.mixer.music.unload()
            if os.path.exists(temp_audio_path):
                try:
                    os.remove(temp_audio_path)
                except Exception:
                    pass

        except Exception as e:
            logger.error(f"Error en reproducción de voz: {e}")

    def listen_speech(self, timeout: float = 8.0, phrase_time_limit: float = 15.0) -> str:
        """
        Escucha a través del micrófono seguro y transcribe con Gemini 3.6 Flash.
        """
        time.sleep(0.1)
        try:
            with mic_lock:
                mic = get_microphone()
                with mic as source:
                    logger.info("👂 Escuchando tu orden...")
                    audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
                    wav_bytes = audio.get_wav_data(convert_rate=16000, convert_width=2)

                    # 1. Transcribir con Gemini 3.6 Flash (Ultra preciso)
                    try:
                        with httpx.Client(timeout=8.0) as client:
                            files = {"audio_file": ("command.wav", wav_bytes, "audio/wav")}
                            resp = client.post(f"{SERVER_HTTP_URL}/api/transcribe", files=files)
                            if resp.status_code == 200:
                                transcribed_text = resp.json().get("text", "").strip()
                                if transcribed_text:
                                    logger.info(f"✨ Transcripción Gemini: '{transcribed_text}'")
                                    return transcribed_text
                    except Exception as ex:
                        logger.debug(f"Fallback a Google Speech: {ex}")

                    # 2. Fallback si no hay conexión
                    text = self.recognizer.recognize_google(audio, language="es-MX")
                    logger.info(f"🗣️ Dijiste (Google): '{text}'")
                    return text

        except sr.WaitTimeoutError:
            logger.info("Tiempo de espera agotado.")
            return ""
        except sr.UnknownValueError:
            logger.info("Audio no distinguible.")
            return ""
        except Exception as e:
            logger.warning(f"Error al capturar voz: {e}")
            return ""

voice_engine = VoiceEngine()
