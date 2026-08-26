import os
import re
import sys
import json
import time
import asyncio
import tempfile
import threading
import logging
from typing import Optional, Dict, Any, List

import speech_recognition as sr
import edge_tts
import pygame
import numpy as np
from faster_whisper import WhisperModel

from config import VOICE_NAME
from performance_tracker import perf_tracker

logger = logging.getLogger("AreyAudioPipeline")
PROFILE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "user_voice_profile.json"))

audio_lock = threading.Lock()

class AudioPipeline:
    """
    Pipeline de audio de alta precisión fonética con Faster-Whisper 'small' (int8),
    Silero VAD y procesamiento en memoria RAM sin escritura en disco.
    """
    def __init__(self):
        if not pygame.mixer.get_init():
            pygame.mixer.init()

        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 80
        self.recognizer.dynamic_energy_threshold = False
        self.recognizer.pause_threshold = 0.85 # Margen cómodo de pausas naturales
        self.recognizer.non_speaking_duration = 0.35

        self.microphone = self._get_best_microphone()
        self.consecutive_empty_count = 0

        # Cargar Faster-Whisper Small cuantizado en int8 para CPU
        logger.info("🧠 Cargando modelo neuronal Faster-Whisper 'small' (int8)...")
        try:
            self.whisper = WhisperModel("small", device="cpu", compute_type="int8")
            logger.info("✅ Faster-Whisper 'small' listo con máxima precisión fonética.")
        except Exception as e:
            logger.warning(f"Fallback a 'base' por error ({e})...")
            self.whisper = WhisperModel("base", device="cpu", compute_type="int8")

        self.assets_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "assets"))
        os.makedirs(self.assets_dir, exist_ok=True)
        self.instant_wake_file = os.path.join(self.assets_dir, "si.mp3")

        self.base_wake_words = [
            "arey", "ari", "aree", "haré", "aré", "are", "aire", "área",
            "hari", "harry", "araí", "arai", "oye arey", "hey arey", "hola arey",
            "oye ari", "oye", "hey", "dime", "asistente"
        ]
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
            "tele": "tele", "la tele": "la tele", "pantalla": "tele",
            "laris": "Larissa", "larisa": "Larissa", "larisse": "Larissa", "lari": "Larissa"
        }

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

    def play_instant_wake(self):
        try:
            if os.path.exists(self.instant_wake_file):
                pygame.mixer.music.load(self.instant_wake_file)
                pygame.mixer.music.play()
        except Exception as e:
            logger.debug(f"Error confirmación: {e}")

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
        Transcripción neuronal directa en memoria RAM con Faster-Whisper Small + Silero VAD.
        """
        perf_tracker.start_stage("Whisper STT (Small)")
        profile = self.get_user_profile()
        keywords = profile.get("vocabulary_keywords", ["Arey", "Andriy", "Spotify", "YouTube", "Larissa", "teléfono", "tele", "Netflix", "Roku", "Queen"])
        prompt = f"Asistente personal Arey en español para Andriy. Palabras y comandos: {', '.join(keywords)}"

        try:
            raw_bytes = audio_data.get_raw_data(convert_rate=16000, convert_width=2)
            audio_np = np.frombuffer(raw_bytes, dtype=np.int16).astype(np.float32) / 32768.0

            segments, _ = self.whisper.transcribe(
                audio_np,
                language="es",
                beam_size=1,
                vad_filter=True,
                vad_parameters=dict(
                    min_silence_duration_ms=250,
                    speech_pad_ms=80,
                    threshold=0.45
                ),
                initial_prompt=prompt
            )
            raw = " ".join(s.text.strip() for s in segments).strip()
            perf_tracker.end_stage("Whisper STT (Small)")
            return self.clean_text(raw)
        except Exception as e:
            logger.warning(f"Whisper transcribe error: {e}")
            perf_tracker.end_stage("Whisper STT (Small)")
            return ""

    def listen_for_wake_word(self, timeout: float = 0.8, phrase_time_limit: float = 2.5) -> bool:
        profile = self.get_user_profile()
        wake_words = list(set(self.base_wake_words + profile.get("custom_wake_words", [])))
        threshold = profile.get("calibrated_energy_threshold", 80)
        self.recognizer.energy_threshold = threshold

        try:
            with audio_lock:
                with self.microphone as source:
                    try:
                        audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
                    except sr.WaitTimeoutError:
                        return False

            text = self.transcribe_audio(audio).lower().strip()
            if text:
                logger.info(f"🔊 Escuchado: '{text}'")
                if any(w in text for w in wake_words):
                    logger.info(f"✨ ¡Palabra de activación detectada! -> '{text}'")
                    return True
        except Exception:
            time.sleep(0.1)
        return False

    def listen_command(self, timeout: float = 6.0, phrase_time_limit: float = 12.0) -> str:
        time.sleep(0.02)
        perf_tracker.start_stage("Captura Micrófono")
        try:
            with audio_lock:
                with self.microphone as source:
                    logger.info("👂 Escuchando tu orden...")
                    audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)

            perf_tracker.end_stage("Captura Micrófono")
            text = self.transcribe_audio(audio)

            if text and text.strip():
                self.consecutive_empty_count = 0
                logger.info(f"✨ Transcripción exacta: '{text}'")
                return text
            else:
                self.consecutive_empty_count += 1

        except sr.WaitTimeoutError:
            self.consecutive_empty_count += 1
            perf_tracker.end_stage("Captura Micrófono")
            logger.info("Tiempo de espera agotado.")
        except Exception as e:
            self.consecutive_empty_count += 1
            perf_tracker.end_stage("Captura Micrófono")
            logger.warning(f"Error captura: {e}")

        return ""

    def should_suggest_recalibration(self) -> bool:
        return self.consecutive_empty_count >= 4

    async def speak(self, text: str):
        if not text or not text.strip():
            return
        perf_tracker.start_stage("TTS Síntesis & Audio")
        logger.info(f"Arey: '{text[:60]}...' " if len(text) > 60 else f"Arey: '{text}'")
        try:
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as fp:
                temp_path = fp.name

            communicate = edge_tts.Communicate(text, voice=VOICE_NAME, rate="+15%", pitch="+0Hz")
            await communicate.save(temp_path)

            pygame.mixer.music.load(temp_path)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                await asyncio.sleep(0.03)

            pygame.mixer.music.unload()
            try:
                os.remove(temp_path)
            except Exception:
                pass
        except Exception as e:
            logger.error(f"Error en síntesis de voz: {e}")
        finally:
            perf_tracker.end_stage("TTS Síntesis & Audio")

audio_pipeline = AudioPipeline()
