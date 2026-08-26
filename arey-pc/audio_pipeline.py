import os
import re
import io
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
from faster_whisper import WhisperModel

from config import VOICE_NAME
from performance_tracker import perf_tracker

logger = logging.getLogger("AreyAudioPipeline")
PROFILE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "user_voice_profile.json"))

# Candado mutex para acceso exclusivo al hardware de audio
audio_lock = threading.Lock()

class AudioPipeline:
    """
    Pipeline de audio profesional con Faster-Whisper Small (int8),
    Silero VAD de alta precisión y observabilidad de latencia por etapas.
    """
    def __init__(self):
        if not pygame.mixer.get_init():
            pygame.mixer.init()

        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 85
        self.recognizer.dynamic_energy_threshold = False
        self.recognizer.pause_threshold = 0.40
        self.recognizer.non_speaking_duration = 0.20

        self.microphone = self._get_best_microphone()
        self.consecutive_empty_count = 0

        # Cargar modelo neuronal Faster-Whisper Small (cuantizado int8 para CPU)
        logger.info("🧠 Cargando modelo neuronal Faster-Whisper 'small' (int8)...")
        try:
            self.whisper = WhisperModel("small", device="cpu", compute_type="int8")
            logger.info("✅ Whisper 'small' listo con máxima precisión fonética.")
        except Exception as e:
            logger.warning(f"Fallback a 'base' por error en small ({e})...")
            self.whisper = WhisperModel("base", device="cpu", compute_type="int8")

        self.assets_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "assets"))
        os.makedirs(self.assets_dir, exist_ok=True)
        self.instant_wake_file = os.path.join(self.assets_dir, "si.mp3")

        self.base_wake_words = [
            "arey", "ari", "aree", "haré", "aré", "are", "aire", "área",
            "hari", "harry", "oye arey", "hey arey", "hola arey", "oye ari",
            "oye", "hey", "dime", "asistente"
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
            logger.debug(f"Error reproduciendo confirmación: {e}")

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

    def transcribe_audio_bytes(self, wav_bytes: bytes) -> str:
        """Transcribe audio con Whisper y Silero VAD activo para recortar silencios."""
        perf_tracker.start_stage("Whisper STT (Small)")
        profile = self.get_user_profile()
        keywords = profile.get("vocabulary_keywords", ["Arey", "Spotify", "YouTube", "Larissa", "teléfono", "tele", "Netflix"])
        prompt = f"Asistente personal en español. Palabras y comandos: {', '.join(keywords)}"

        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                f.write(wav_bytes)
                tmp_path = f.name

            # Silero VAD optimizado
            segments, _ = self.whisper.transcribe(
                tmp_path,
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
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass

    def listen_for_wake_word(self, timeout: float = 0.5, phrase_time_limit: float = 2.5) -> bool:
        profile = self.get_user_profile()
        wake_words = list(set(self.base_wake_words + profile.get("custom_wake_words", [])))
        threshold = profile.get("calibrated_energy_threshold", 85)
        self.recognizer.energy_threshold = threshold

        try:
            with audio_lock:
                with self.microphone as source:
                    try:
                        audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
                        wav_bytes = audio.get_wav_data(convert_rate=16000, convert_width=2)
                        text = self.transcribe_audio_bytes(wav_bytes).lower().strip()
                        if text:
                            logger.info(f"🔊 Escuchado en vivo: '{text}'")
                        if text and any(w in text for w in wake_words):
                            logger.info(f"✨ ¡Palabra de activación detectada! -> '{text}'")
                            return True
                    except sr.WaitTimeoutError:
                        return False
                    except Exception:
                        return False
        except Exception as e:
            logger.error(f"Error en micrófono: {e}")
            time.sleep(0.3)
        return False

    def listen_command(self, timeout: float = 5.0, phrase_time_limit: float = 10.0) -> str:
        time.sleep(0.04)
        perf_tracker.start_stage("Captura VAD Mic")
        try:
            with audio_lock:
                with self.microphone as source:
                    logger.info("👂 Escuchando tu orden...")
                    audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
                    wav_bytes = audio.get_wav_data(convert_rate=16000, convert_width=2)

                perf_tracker.end_stage("Captura VAD Mic")
                text = self.transcribe_audio_bytes(wav_bytes)

                if text and text.strip():
                    self.consecutive_empty_count = 0
                    logger.info(f"✨ Transcripción exacta: '{text}'")
                    return text
                else:
                    self.consecutive_empty_count += 1

                # Fallback Google si Whisper devuelve vacío
                try:
                    fallback = self.recognizer.recognize_google(audio, language="es-MX")
                    logger.info(f"🗣️ Google fallback: '{fallback}'")
                    self.consecutive_empty_count = 0
                    return self.clean_text(fallback)
                except Exception:
                    pass

        except sr.WaitTimeoutError:
            self.consecutive_empty_count += 1
            perf_tracker.end_stage("Captura VAD Mic")
            logger.info("Tiempo de espera agotado.")
        except sr.UnknownValueError:
            self.consecutive_empty_count += 1
            perf_tracker.end_stage("Captura VAD Mic")
            logger.info("Audio no distinguible.")
        except Exception as e:
            self.consecutive_empty_count += 1
            perf_tracker.end_stage("Captura VAD Mic")
            logger.warning(f"Error al capturar voz: {e}")

        return ""

    def should_suggest_recalibration(self) -> bool:
        return self.consecutive_empty_count >= 3

    async def speak(self, text: str):
        if not text or not text.strip():
            return
        perf_tracker.start_stage("TTS Síntesis & Audio")
        logger.info(f"Arey: '{text[:60]}...' " if len(text) > 60 else f"Arey: '{text}'")
        try:
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as fp:
                temp_path = fp.name

            communicate = edge_tts.Communicate(text, voice=VOICE_NAME, rate="+10%", pitch="+0Hz")
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
            logger.error(f"Error en síntesis de voz: {e}")
        finally:
            perf_tracker.end_stage("TTS Síntesis & Audio")

audio_pipeline = AudioPipeline()
