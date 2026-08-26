import os
import sys
import json
import time
import speech_recognition as sr
from faster_whisper import WhisperModel
import pygame
import edge_tts
import asyncio

PROFILE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "user_voice_profile.json"))

DEFAULT_PROFILE = {
    "calibrated_energy_threshold": 80,
    "user_name": "Andriy",
    "custom_wake_words": ["arey", "ari", "aree", "haré", "aré", "are", "aire", "oye arey", "hey arey", "hola arey", "oye ari"],
    "vocabulary_keywords": [
        "Arey", "Larissa", "Spotify", "Netflix", "YouTube", "WhatsApp", 
        "teléfono", "celular", "alarma", "linterna", "batería", "pantalla", 
        "volumen", "música", "tele", "televisión", "JVC", "Roku", "contacto"
    ],
    "phonetic_corrections": {
        "laris": "Larissa",
        "larisa": "Larissa",
        "larisse": "Larissa",
        "ari": "Arey",
        "haré": "Arey",
        "aré": "Arey",
        "are": "Arey",
        "spoty": "Spotify",
        "spoti": "Spotify",
        "cel": "teléfono"
    }
}

def load_voice_profile():
    if os.path.exists(PROFILE_PATH):
        try:
            with open(PROFILE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return DEFAULT_PROFILE.copy()

def save_voice_profile(profile):
    with open(PROFILE_PATH, "w", encoding="utf-8") as f:
        json.dump(profile, f, ensure_ascii=False, indent=2)

async def speak_text(text: str):
    print(f"\n🗣️ Arey: {text}")
    try:
        comm = edge_tts.Communicate(text, voice="es-MX-DaliaNeural", rate="+10%")
        tmp = os.path.abspath("temp_train.mp3")
        await comm.save(tmp)
        if not pygame.mixer.get_init():
            pygame.mixer.init()
        pygame.mixer.music.load(tmp)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            await asyncio.sleep(0.05)
        pygame.mixer.music.unload()
        if os.path.exists(tmp):
            os.remove(tmp)
    except Exception as e:
        print(f"(Audio no disponible: {e})")

def run_training():
    print("=" * 60)
    print("      🎙️ ASISTENTE DE ENTRENAMIENTO Y CALIBRACIÓN DE VOZ DE AREY")
    print("=" * 60)
    print("\nVamos a calibrar el micrófono y registrar tu voz para que Arey")
    print("te entienda a la primera con tu tono, acento y palabras clave.\n")

    profile = load_voice_profile()
    r = sr.Recognizer()
    r.dynamic_energy_threshold = False

    # 1. Calibración del ruido ambiente y micrófono
    asyncio.run(speak_text("Hola. Vamos a calibrar tu micrófono. Por favor quédate en silencio un segundo."))
    print("\n[1/3] 🤫 Calibrando ruido ambiental... (Guarda silencio 2 segundos)")
    
    with sr.Microphone() as source:
        r.adjust_for_ambient_noise(source, duration=2.0)
        ambient_energy = r.energy_threshold
        # Umbral optimizado: ligeramente por encima del ruido base
        target_energy = max(70, min(140, int(ambient_energy * 1.2)))
        profile["calibrated_energy_threshold"] = target_energy
        print(f"✅ Micrófono calibrado con éxito. Sensibilidad: {target_energy}")

    print("\n[2/3] 🧠 Cargando modelo de reconocimiento Whisper 'small'...")
    whisper = WhisperModel("small", device="cpu", compute_type="int8")

    # 3. Pruebas de pronunciación guiadas
    phrases_to_train = [
        ("Arey", "Di claramente el nombre: 'Arey'"),
        ("Busca mi teléfono", "Di la orden: 'Busca mi teléfono'"),
        ("Llama a Larissa", "Di la orden: 'Llama a Larissa' (o el nombre de tu contacto favorito)"),
        ("Pon música en Spotify", "Di: 'Pon música en Spotify'"),
        ("Apaga la tele", "Di: 'Apaga la tele'")
    ]

    asyncio.run(speak_text("Ahora te pediré que repitas unas frases cortas con tu tono de voz normal."))

    print("\n[3/3] 🗣️ Registro de patrones de voz:")
    for expected, instruction in phrases_to_train:
        print(f"\n👉 {instruction}")
        asyncio.run(speak_text(f"Por favor di: {expected}"))
        
        with sr.Microphone() as source:
            r.energy_threshold = target_energy
            print("🔴 [GRABANDO] Habla ahora...")
            try:
                audio = r.listen(source, timeout=6.0, phrase_time_limit=4.0)
                wav_bytes = audio.get_wav_data(convert_rate=16000, convert_width=2)
                
                # Guardar WAV temporal
                tmp_wav = "train_sample.wav"
                with open(tmp_wav, "wb") as f:
                    f.write(wav_bytes)
                
                segs, _ = whisper.transcribe(
                    tmp_wav, language="es", beam_size=1,
                    initial_prompt=", ".join(profile["vocabulary_keywords"])
                )
                detected = " ".join(s.text.strip() for s in segs).strip()
                print(f"👂 Escuchado: '{detected}'")

                # Agregar variaciones detectadas al perfil del usuario
                det_clean = detected.lower().strip()
                if det_clean and det_clean not in profile["custom_wake_words"] and "arey" in expected.lower():
                    profile["custom_wake_words"].append(det_clean)
                
                # Agregar palabras clave detectadas
                for word in expected.split():
                    if len(word) > 2 and word not in profile["vocabulary_keywords"]:
                        profile["vocabulary_keywords"].append(word)

                if os.path.exists(tmp_wav):
                    os.remove(tmp_wav)

            except Exception as e:
                print(f"⚠️ No se capturó audio: {e}")

    # Guardar perfil personalizado
    save_voice_profile(profile)
    print("\n" + "=" * 60)
    print("🎉 ¡ENTRENAMIENTO COMPLETADO CON ÉXITO!")
    print(f"Tu perfil de voz ha sido guardado en: {PROFILE_PATH}")
    print("=" * 60)
    asyncio.run(speak_text("¡Listo! Ya registré tu voz y tus palabras. Ahora te entenderé mucho mejor."))

if __name__ == "__main__":
    run_training()
