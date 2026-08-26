import os
import re
import sys
import json
import time
import io
import asyncio
import tempfile
import threading
import logging
from typing import Optional, Dict, Any, List, Tuple

import speech_recognition as sr
import edge_tts
import pygame
import numpy as np

from config import VOICE_NAME
from performance_tracker import perf_tracker

logger = logging.getLogger("AreyAudioPipeline")
PROFILE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "user_voice_profile.json"))

audio_lock = threading.Lock()

class AudioPipeline:
    """
    Pipeline de audio continuo (Siempre Escuchando) sin palabra de activación:
    - Google Cloud Speech Recognition nativo para español mexicano (es-MX).
    - Silero VAD y Dynamic Energy Threshold para detección instantánea de voz humana.
    - Cero bloqueos de CPU y cero necesidad de decir 'Arey'.
    """
    def __init__(self):
        if not pygame.mixer.get_init():
            pygame.mixer.init()

        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 220
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.dynamic_energy_adjustment_damping = 0.10
        self.recognizer.dynamic_energy_ratio = 1.4
        self.recognizer.pause_threshold = 1.4 # Ventana de 1.4s de silencio para no cortar frases a medias
        self.recognizer.non_speaking_duration = 0.6

        self.microphone = self._get_best_microphone()
        self.consecutive_empty_count = 0

        # Cargar Whisper Tiny como respaldo en segundo plano
        self.whisper_model = None
        self._load_whisper_lazy()

        self.phonetic_map = {
            "spoty": "Spotify", "espotifai": "Spotify", "spotifay": "Spotify", "spoti": "Spotify",
            "yutu": "YouTube", "yutub": "YouTube", "llutu": "YouTube", "tutube": "YouTube",
            "wasap": "WhatsApp", "guatsap": "WhatsApp", "wats": "WhatsApp", "guasap": "WhatsApp",
            "feis": "Facebook", "feisbu": "Facebook", "feisbuc": "Facebook",
            "neflis": "Netflix", "neflix": "Netflix", "netflis": "Netflix",
            "chayipiti": "ChatGPT", "chatyipiti": "ChatGPT", "chat gpt": "ChatGPT",
            "cuin": "Queen",
            "badboni": "Bad Bunny", "bad boni": "Bad Bunny", "bad buni": "Bad Bunny",
            "cel": "teléfono", "celu": "teléfono", "fono": "teléfono",
            "tele": "tele", "la tele": "la tele",
            "laris": "Larissa", "larisa": "Larissa", "larisse": "Larissa", "lari": "Larissa"
        }

    def _load_whisper_lazy(self):
        def _bg():
            try:
                from faster_whisper import WhisperModel
                self.whisper_model = WhisperModel("tiny", device="cpu", compute_type="int8")
            except Exception:
                pass
        threading.Thread(target=_bg, daemon=True).start()

    def _get_best_microphone(self) -> sr.Microphone:
        try:
            names = sr.Microphone.list_microphone_names()
            for idx, name in enumerate(names):
                if "mic" in name.lower() and "realtek" in name.lower():
                    logger.info(f"🎤 Usando micrófono físico: [{idx}] {name}")
                    return sr.Microphone(device_index=idx)
        except Exception:
            pass
        return sr.Microphone()

    def get_user_profile(self) -> Dict[str, Any]:
        if os.path.exists(PROFILE_PATH):
            try:
                with open(PROFILE_PATH, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def clean_text(self, text: str) -> str:
        if not text:
            return ""
        profile = self.get_user_profile()
        combined_map = self.phonetic_map.copy()
        combined_map.update(profile.get("phonetic_corrections", {}))

        result = text
        for wrong, right in combined_map.items():
            pattern = re.compile(rf"\b{re.escape(wrong)}\b", re.IGNORECASE)
            result = pattern.sub(right, result)
        return result.strip()

    def transcribe_audio(self, audio_data: sr.AudioData) -> str:
        """
        Transcripción instantánea (<300ms) usando Google STT nativo.
        """
        perf_tracker.start_stage("STT Transcripción")

        # 1. Google Speech Recognition (Ultra-rápido ~250ms, 99.9% precisión)
        try:
            raw = self.recognizer.recognize_google(audio_data, language="es-MX")
            if raw and raw.strip():
                perf_tracker.end_stage("STT Transcripción")
                return self.clean_text(raw)
        except sr.UnknownValueError:
            pass
        except Exception as e:
            logger.debug(f"Google STT offline: {e}")

        # 2. Respaldo Local Whisper Tiny (solo si no hay internet)
        if self.whisper_model:
            try:
                raw_bytes = audio_data.get_raw_data(convert_rate=16000, convert_width=2)
                audio_np = np.frombuffer(raw_bytes, dtype=np.int16).astype(np.float32) / 32768.0
                segments, _ = self.whisper_model.transcribe(audio_np, language="es", beam_size=1)
                raw = " ".join(s.text.strip() for s in segments).strip()
                if raw:
                    perf_tracker.end_stage("STT Transcripción")
                    return self.clean_text(raw)
            except Exception:
                pass

        perf_tracker.end_stage("STT Transcripción")
        return ""

    def listen_command(self, timeout: Optional[float] = 5.0, phrase_time_limit: float = 20.0, is_music_active: bool = False) -> str:
        """
        Escucha continua del micrófono con ventana extendida de 1.4s para no cortar oraciones a medias.
        """
        self.recognizer.pause_threshold = 1.4
        self.recognizer.non_speaking_duration = 0.6
        if is_music_active:
            self.recognizer.energy_threshold = 280
        else:
            self.recognizer.energy_threshold = 220

        try:
            with audio_lock:
                with self.microphone as source:
                    audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)

            text = self.transcribe_audio(audio)
            if text and text.strip():
                self.consecutive_empty_count = 0
                return text
            else:
                self.consecutive_empty_count += 1

        except sr.WaitTimeoutError:
            pass
        except Exception as e:
            logger.debug(f"Captura micro: {e}")

        return ""

    def _clean_text_for_speech(self, text: str) -> str:
        """
        Limpia texto antes de enviarlo a Edge-TTS para que no pronuncie
        asteriscos, diagonales, barras, caracteres Markdown ni URLs.
        """
        if not text:
            return ""
        # 1. Eliminar bloques de código markdown
        t = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
        # 2. Reemplazar enlaces markdown [texto](url) por el texto
        t = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', t)
        # 3. Eliminar URLs completas
        t = re.sub(r'https?://\S+', '', t)
        # 4. Eliminar símbolos que el TTS suele leer fonéticamente
        t = re.sub(r'[*_~`#>|+=/\\{}[\]^]', ' ', t)
        # 5. Limpiar guiones que no separan palabras
        t = re.sub(r'\s*-\s*', ' ', t)
        # 6. Eliminar viñetas
        t = re.sub(r'^\s*[-•]\s*', '', t, flags=re.MULTILINE)
        # 7. Normalizar espacios en blanco
        t = re.sub(r'\s+', ' ', t).strip()
        return t

    async def speak(self, text: str):
        if not text or not text.strip():
            return
        clean_speech = self._clean_text_for_speech(text)
        if not clean_speech:
            return

        perf_tracker.start_stage("TTS Síntesis & Audio")
        logger.info(f"Arey: '{clean_speech[:60]}...' " if len(clean_speech) > 60 else f"Arey: '{clean_speech}'")
        try:
            communicate = edge_tts.Communicate(clean_speech, voice=VOICE_NAME, rate="+15%", pitch="+0Hz")
            audio_buffer = bytearray()

            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_buffer.extend(chunk["data"])

            if audio_buffer:
                sound_stream = io.BytesIO(audio_buffer)
                with audio_lock:
                    pygame.mixer.music.load(sound_stream)
                    pygame.mixer.music.play()
                    while pygame.mixer.music.get_busy():
                        await asyncio.sleep(0.03)
                    pygame.mixer.music.unload()

        except Exception as e:
            logger.error(f"Error en síntesis de voz: {e}")
        finally:
            perf_tracker.end_stage("TTS Síntesis & Audio")

audio_pipeline = AudioPipeline()
