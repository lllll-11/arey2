import speech_recognition as sr
import logging

logger = logging.getLogger("AreyAudio")

def get_best_microphone():
    """
    Detecta automáticamente el mejor índice de micrófono físico Realtek / Windows.
    """
    try:
        names = sr.Microphone.list_microphone_names()
        for idx, name in enumerate(names):
            if "mic" in name.lower() and "realtek" in name.lower():
                logger.info(f"Usando micrófono físico: [{idx}] {name}")
                return sr.Microphone(device_index=idx)
    except Exception:
        pass
    return sr.Microphone()

shared_mic = get_best_microphone()
shared_recognizer = sr.Recognizer()
shared_recognizer.energy_threshold = 200
shared_recognizer.dynamic_energy_threshold = True
shared_recognizer.pause_threshold = 0.6
