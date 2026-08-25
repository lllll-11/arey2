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

logger = logging.getLogger("AreyAudioPipeline")
PROFILE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "user_voice_profile.json"))

# Candado mutex para acceso exclusivo al hardware de audio
audio_lock = threading.Lock()

class AudioPipeline:
    """
    Pipeline de audio profesional, robusto y sin bloqueos de hardware.
    Gestiona la escucha en segundo plano, la transcripción local con Whisper (150ms)
    y la síntesis de voz neural con Edge-TTS y pygame.
    """
    def __init__(self):
        # 1. Inicializar subsistema de reproducción de audio
        if not pygame.mixer.get_init():
            pygame.mixer.init()

        # 2. Configurar reconocedor de audio de baja latencia
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 85
        self.recognizer.dynamic_energy_threshold = False
        self.recognizer.pause_threshold = 0.45
        self.recognizer.non_speaking_duration = 0.25

        # 3. Detectar micrófono óptimo de Windows / Realtek
        self.microphone = self._get_best_microphone()

        # 4. Cargar modelo neuronal Faster-Whisper en memoria (100% local, cero internet)
        logger.info("🧠 Cargando modelo neuronal Whisper en memoria...")
        self.whisper = WhisperModel("tiny", device="cpu", compute_type="int8")
        logger.info("✅ Whisper local listo para transcripción instantánea.")

        # 5. Cargar sonidos de activación pre-generados
        self.assets_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "assets"))
        os.makedirs(self.assets_dir, exist_ok=True)
        self.instant_wake_file = os.path.join(self.assets_dir, "si.mp3")

        # Diccionario fonético y palabras de activación base
        self.base_wake_words = [
            "arey", "ari", "aree", "haré", "aré", "are", "aire", "área",
            "hari", "harry", "oye arey", "hey arey", "hola arey", "oye ari",
            "oye", "hey", "dime", "asistente"
        ]
        self.phonetic_map = {
            "spoty": "Spotify", "espotifai": "Spotify", "spotifay": "Spotify", "spoti": "Spotify",
            "yutu": "YouTube", "yutub": "YouTube", "llutu": "YouTube", "tutube": "YouTube",
            "wasap": "WhatsApp", "guatsap": "WhatsApp", "wats": "WhatsApp", "guasap": "WhatsApp",
            "feis": "Facebook", "feisbu": "Facebook",
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
        """Reproduce el audio de confirmación '¿Sí?' en 5ms."""
        try:
            if os.path.exists(self.instant_wake_file):
                pygame.mixer.music.load(self.instant_wake_file)
                pygame.mixer.music.play()
        except Exception as e:
            logger.debug(f"Error reproduciendo confirmación: {e}")

    def clean_text(self, text: str) -> str:
        """Aplica correcciones fonéticas y de modismos al texto transcrito."""
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
        """Transcribe un fragmento de audio WAV en memoria con Whisper local."""
        profile = self.get_user_profile()
        keywords = profile.get("vocabulary_keywords", ["Arey", "Spotify", "YouTube", "Larissa", "teléfono", "tele"])
        prompt = f"Asistente personal en español. Palabras: {', '.join(keywords)}"

        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                f.write(wav_bytes)
                tmp_path = f.name

            segments, _ = self.whisper.transcribe(
                tmp_path,
                language="es",
                beam_size=1,
                vad_filter=True,
                initial_prompt=prompt
            )
            raw = " ".join(s.text.strip() for s in segments).strip()
            return self.clean_text(raw)
        except Exception as e:
            logger.warning(f"Whisper transcribe error: {e}")
            return ""
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass

    def listen_for_wake_word(self, timeout: float = 0.5, phrase_time_limit: float = 2.5) -> bool:
        """Escucha continua de baja latencia para detectar 'Arey'."""
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
        """Escucha la orden del usuario después de la confirmación y devuelve el texto transcrito."""
        time.sleep(0.05)
        try:
            with audio_lock:
                with self.microphone as source:
                    logger.info("👂 Escuchando tu orden...")
                    audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
                    wav_bytes = audio.get_wav_data(convert_rate=16000, convert_width=2)

                text = self.transcribe_audio_bytes(wav_bytes)
                if text:
                    logger.info(f"✨ Transcripción exacta: '{text}'")
                    return text

                # Fallback Google si Whisper devuelve vacío
                try:
                    fallback = self.recognizer.recognize_google(audio, language="es-MX")
                    logger.info(f"🗣️ Google fallback: '{fallback}'")
                    return self.clean_text(fallback)
                except Exception:
                    return ""

        except sr.WaitTimeoutError:
            logger.info("Tiempo de espera agotado.")
            return ""
        except sr.UnknownValueError:
            logger.info("Audio no distinguible.")
            return ""
        except Exception as e:
            logger.warning(f"Error al capturar voz: {e}")
            return ""

    async def speak(self, text: str):
        """Sintetiza la respuesta de voz con Edge-TTS y la reproduce con pygame."""
        if not text or not text.strip():
            return
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

audio_pipeline = AudioPipeline()
