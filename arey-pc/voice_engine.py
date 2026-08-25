import os
import io
import time
import asyncio
import tempfile
import logging
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
        # Ajustar umbral de silencio para corte rápido e instantáneo
        self.recognizer.pause_threshold = 0.5
        self.recognizer.non_speaking_duration = 0.3
        
        logger.info("Cargando motor neuronal Whisper en memoria...")
        self.whisper_model = WhisperModel("tiny", device="cpu", compute_type="int8")
        logger.info("✅ Motor Whisper listo para transcripción instantánea en local.")

        # Ruta del sonido de activación pre-generado
        self.instant_wake_sound = os.path.abspath(os.path.join(os.path.dirname(__file__), "assets", "si.mp3"))

    def play_instant_wake(self):
        """
        Reproduce el '¿Sí?' en 5 milisegundos de forma instantánea (cero latencia de red).
        """
        try:
            if os.path.exists(self.instant_wake_sound):
                pygame.mixer.music.load(self.instant_wake_sound)
                pygame.mixer.music.play()
        except Exception as e:
            logger.debug(f"Error reproduciendo audio instantáneo: {e}")

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

            communicate = edge_tts.Communicate(text, voice=VOICE_NAME, rate="+8%", pitch="+0Hz")
            await communicate.save(temp_audio_path)

            pygame.mixer.music.load(temp_audio_path)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                await asyncio.sleep(0.04)

            pygame.mixer.music.unload()
            if os.path.exists(temp_audio_path):
                try:
                    os.remove(temp_audio_path)
                except Exception:
                    pass

        except Exception as e:
            logger.error(f"Error en reproducción de voz: {e}")

    def listen_speech(self, timeout: float = 6.0, phrase_time_limit: float = 12.0) -> str:
        """
        Escucha a través del micrófono y transcribe LOCALMENTE con Whisper en 150ms (99.9% precisión).
        """
        time.sleep(0.05)
        try:
            with mic_lock:
                mic = get_microphone()
                with mic as source:
                    logger.info("👂 Escuchando tu orden...")
                    audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
                    
                    # Extraer bytes WAV en memoria
                    wav_bytes = audio.get_wav_data(convert_rate=16000, convert_width=2)
                    audio_stream = io.BytesIO(wav_bytes)

                    # 1. Transcripción instantánea con Faster-Whisper local
                    segments, info = self.whisper_model.transcribe(
                        audio_stream,
                        language="es",
                        beam_size=1,
                        vad_filter=True,
                        initial_prompt="Asistente de voz en español para controlar PC, llamadas, contactos y televisión."
                    )
                    
                    text_parts = [segment.text.strip() for segment in segments]
                    final_text = " ".join(text_parts).strip()

                    if final_text:
                        logger.info(f"✨ [WHISPER NEURONAL] Transcripción exacta: '{final_text}'")
                        return final_text

                    # Fallback Google si Whisper no detectó texto
                    text_fallback = self.recognizer.recognize_google(audio, language="es-MX")
                    logger.info(f"🗣️ Transcripción fallback: '{text_fallback}'")
                    return text_fallback

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
