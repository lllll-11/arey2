import threading
import speech_recognition as sr
import logging

logger = logging.getLogger("AreyAudio")

# Mutex para garantizar que el micrófono nunca se acceda simultáneamente por dos hilos
mic_lock = threading.Lock()

def get_microphone():
    """
    Retorna una instancia limpia del micrófono físico Realtek / Windows.
    """
    try:
        names = sr.Microphone.list_microphone_names()
        for idx, name in enumerate(names):
            if "mic" in name.lower() and "realtek" in name.lower():
                return sr.Microphone(device_index=idx)
    except Exception:
        pass
    return sr.Microphone()

def create_recognizer():
    r = sr.Recognizer()
    # Sensibilidad óptima para capturar voz humana normal
    r.energy_threshold = 90
    r.dynamic_energy_threshold = False
    r.pause_threshold = 0.5
    r.non_speaking_duration = 0.3
    return r
