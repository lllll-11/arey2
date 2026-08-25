import os
import asyncio
import tempfile
import logging
import speech_recognition as sr
import edge_tts
import pygame
from config import VOICE_NAME

logger = logging.getLogger("VoiceEngine")

class VoiceEngine:
    def __init__(self):
        pygame.mixer.init()
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 300
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold = 0.8

    async def speak(self, text: str):
        """
        Sintetiza la voz usando la red neuronal de Edge-TTS (calidad humana 100% gratuita).
        """
        if not text or not text.strip():
            return

        logger.info(f"Arey diciendo: '{text}'")
        try:
            # Crear archivo de audio temporal
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as fp:
                temp_audio_path = fp.name

            communicate = edge_tts.Communicate(text, voice=VOICE_NAME)
            await communicate.save(temp_audio_path)

            # Reproducir audio con pygame
            pygame.mixer.music.load(temp_audio_path)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                await asyncio.sleep(0.05)

            pygame.mixer.music.unload()
            if os.path.exists(temp_audio_path):
                os.remove(temp_audio_path)

        except Exception as e:
            logger.error(f"Error en reproducción de voz: {e}")

    def listen_speech(self, timeout: float = 6.0, phrase_time_limit: float = 12.0) -> str:
        """
        Escucha a través del micrófono y convierte voz a texto usando reconocimiento en español.
        """
        with sr.Microphone() as source:
            try:
                logger.info("Escuchando comando del usuario...")
                audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
                text = self.recognizer.recognize_google(audio, language="es-MX")
                logger.info(f"Usuario dijo: '{text}'")
                return text
            except sr.WaitTimeoutError:
                return ""
            except sr.UnknownValueError:
                return ""
            except Exception as e:
                logger.warning(f"Error al reconocer voz: {e}")
                return ""

voice_engine = VoiceEngine()
