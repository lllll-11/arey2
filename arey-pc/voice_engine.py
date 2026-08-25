import os
import json
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
PROFILE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "user_voice_profile.json"))

def get_voice_profile():
    if os.path.exists(PROFILE_PATH):
        try:
            with open(PROFILE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "vocabulary_keywords": ["Arey", "Larissa", "Spotify", "Netflix", "YouTube", "teléfono", "celular", "alarma", "linterna", "volumen", "música", "tele"],
        "phonetic_corrections": {"laris": "Larissa", "larisa": "Larissa", "ari": "Arey", "haré": "Arey", "spoty": "Spotify", "cel": "teléfono"}
    }

class VoiceEngine:
    def __init__(self):
        pygame.mixer.init()
        self.recognizer = create_recognizer()
        self.recognizer.pause_threshold = 0.5
        self.recognizer.non_speaking_duration = 0.3

        logger.info("Cargando Whisper tiny para transcripcion rapida...")
        self.whisper_model = WhisperModel("tiny", device="cpu", compute_type="int8")
        logger.info("Whisper tiny listo!")

        self.instant_wake_sound = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "assets", "si.mp3")
        )

    def play_instant_wake(self):
        try:
            if os.path.exists(self.instant_wake_sound):
                pygame.mixer.music.load(self.instant_wake_sound)
                pygame.mixer.music.play()
        except Exception as e:
            logger.debug(f"Error audio wake: {e}")

    async def speak(self, text: str):
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
            try: os.remove(temp_path)
            except: pass
        except Exception as e:
            logger.error(f"Error en voz: {e}")

    def _apply_corrections(self, text: str, profile: dict) -> str:
        import re
        corrections = {
            "spoty": "Spotify", "espotifai": "Spotify", "spotifay": "Spotify", "spoti": "Spotify",
            "yutu": "YouTube", "yutub": "YouTube", "llutu": "YouTube", "tutube": "YouTube",
            "wasap": "WhatsApp", "guatsap": "WhatsApp", "wats": "WhatsApp", "guasap": "WhatsApp",
            "feis": "Facebook", "feisbu": "Facebook", "feisbuc": "Facebook",
            "neflis": "Netflix", "neflix": "Netflix", "netflis": "Netflix",
            "chayipiti": "ChatGPT", "chatyipiti": "ChatGPT", "chat gpt": "ChatGPT",
            "cuin": "Queen",
            "badboni": "Bad Bunny", "bad boni": "Bad Bunny", "bad buni": "Bad Bunny",
            "cel": "teléfono", "celu": "teléfono", "fono": "teléfono",
            "tele": "tele", "pantalla": "tele",
            "laris": "Larissa", "larisa": "Larissa", "larisse": "Larissa", "lari": "Larissa"
        }
        corrections.update(profile.get("phonetic_corrections", {}))

        result_text = text
        for wrong, right in corrections.items():
            pattern = re.compile(rf"\b{re.escape(wrong)}\b", re.IGNORECASE)
            result_text = pattern.sub(right, result_text)

        return result_text

    def _transcribe(self, wav_bytes: bytes) -> str:
        """Transcripción local con Whisper tiny personalizada con el vocabulario del usuario."""
        profile = get_voice_profile()
        keywords = profile.get("vocabulary_keywords", [])
        prompt = f"Asistente personal Arey en español. Vocabulario clave: {', '.join(keywords)}"

        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                f.write(wav_bytes)
                tmp_path = f.name
            segs, _ = self.whisper_model.transcribe(
                tmp_path,
                language="es",
                beam_size=1,
                vad_filter=True,
                initial_prompt=prompt
            )
            raw_text = " ".join(s.text.strip() for s in segs).strip()
            # Aplicar corrección fonética personalizada
            final_text = self._apply_corrections(raw_text, profile)
            return final_text
        except Exception as e:
            logger.warning(f"Whisper error: {e}")
            return ""
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try: os.remove(tmp_path)
                except: pass

    def listen_speech(self, timeout: float = 5.0, phrase_time_limit: float = 8.0) -> str:
        time.sleep(0.05)
        try:
            with mic_lock:
                mic = get_microphone()
                with mic as source:
                    logger.info("Escuchando orden...")
                    audio = self.recognizer.listen(
                        source, timeout=timeout, phrase_time_limit=phrase_time_limit
                    )
                    wav_bytes = audio.get_wav_data(convert_rate=16000, convert_width=2)

                result = self._transcribe(wav_bytes)
                if result:
                    logger.info(f"Transcrito: '{result}'")
                    return result

                # Fallback Google solo si Whisper devuelve vacío
                try:
                    fallback = self.recognizer.recognize_google(audio, language="es-MX")
                    logger.info(f"Google fallback: '{fallback}'")
                    return fallback
                except Exception:
                    return ""

        except sr.WaitTimeoutError:
            return ""
        except sr.UnknownValueError:
            return ""
        except Exception as e:
            logger.warning(f"Error voz: {e}")
            return ""

voice_engine = VoiceEngine()
