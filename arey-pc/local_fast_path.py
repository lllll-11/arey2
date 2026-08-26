import re
import logging
from typing import Optional, Tuple
from pc_controller import pc_controller

logger = logging.getLogger("AreyFastPath")

class LocalFastPath:
    """
    Enrutador determinista local de ultrabaja latencia (< 1ms).
    Ejecuta comandos de hardware, volumen y control de Windows inmediatamente en la laptop.
    """
    def __init__(self):
        pass

    def try_execute_local(self, text: str) -> Optional[Tuple[str, str]]:
        """
        Analiza si el texto corresponde a un comando local determinista de Windows.
        Retorna (accion_ejecutada, respuesta_vocal) o None si requiere procesamiento de IA.
        """
        if not text:
            return None

        t = text.lower().strip().rstrip(".?!,")

        # ----------------- 1. CONTROL DE VOLUMEN -----------------
        # "pon volumen al 50", "volumen a 80", "subelo al 90", "súbelo al 100"
        match_vol = re.search(r'(?:pon|ajusta|sube|subelo|subelo\s*al|subele|baja|bajalo|bajalo\s*al|bajale)?\s*(?:el\s*)?(?:volumen)?\s*(?:al?|en|a)?\s*(\d{1,3})%?', t)
        if match_vol and match_vol.group(1):
            level = int(match_vol.group(1))
            pc_controller.set_volume(level)
            return ("set_volume", f"Volumen ajustado al {level}%.")

        if any(w in t for w in ["sube volumen", "sube el volumen", "subele al volumen", "subelo al", "súbelo al", "subelo", "súbelo", "subele", "súbele", "mas volumen", "más volumen"]):
            pc_controller.set_volume(80)
            return ("volume_up", "Listo, volumen subido.")

        if any(w in t for w in ["baja volumen", "baja el volumen", "bajale al volumen", "bajalo al", "bájalo al", "bajalo", "bájalo", "bajale", "bájale", "menos volumen"]):
            pc_controller.set_volume(30)
            return ("volume_down", "Listo, volumen bajado.")

        if any(w in t for w in ["silencio", "mute", "mutea", "mutear", "silencia"]):
            pc_controller.control_media("mute")
            return ("mute", "Audio silenciado.")

        # ----------------- 2. CONTROL MULTIMEDIA -----------------
        if t in ["pausa", "pausar", "pausa la musica", "pausa la cancion", "para"]:
            pc_controller.control_media("pause")
            return ("pause", "Pausado.")

        if t in ["play", "reproduce", "reanuda", "continua", "sigue"]:
            pc_controller.control_media("play")
            return ("play", "Reanudado.")

        if any(w in t for w in ["siguiente cancion", "siguiente pista", "pasa de cancion", "siguiente"]):
            pc_controller.control_media("next")
            return ("next_track", "Pista siguiente.")

        if any(w in t for w in ["anterior cancion", "cancion anterior", "anterior", "regresa la cancion"]):
            pc_controller.control_media("previous")
            return ("prev_track", "Pista anterior.")

        # ----------------- 3. ATAJOS DE SISTEMA -----------------
        if any(w in t for w in ["bloquea la laptop", "bloquea pc", "bloquea la compu", "bloquear"]):
            pc_controller.lock_workstation()
            return ("lock_pc", "Laptop bloqueada.")

        if any(w in t for w in ["muestra escritorio", "ver escritorio", "minimiza todo", "minimizar todo"]):
            pc_controller.press_hotkey("win+d")
            return ("show_desktop", "Escritorio mostrado.")

        if any(w in t for w in ["cierra ventana", "cerrar ventana", "cierra esto"]):
            pc_controller.press_hotkey("alt+f4")
            return ("close_window", "Ventana cerrada.")

        # ----------------- 4. ABRIR APLICACIONES COMUNES -----------------
        apps_direct = {
            "calculadora": ("calc", "Abriendo calculadora."),
            "calc": ("calc", "Abriendo calculadora."),
            "bloc de notas": ("notepad", "Abriendo Bloc de Notas."),
            "notepad": ("notepad", "Abriendo Bloc de Notas."),
            "spotify": ("spotify", "Abriendo Spotify."),
            "chrome": ("chrome", "Abriendo Google Chrome."),
            "navegador": ("chrome", "Abriendo navegador."),
            "visual studio code": ("code", "Abriendo VS Code."),
            "vs code": ("code", "Abriendo VS Code."),
            "discord": ("discord", "Abriendo Discord.")
        }

        for trigger, (app_name, voice_reply) in apps_direct.items():
            if t == f"abre {trigger}" or t == f"abrir {trigger}" or t == trigger:
                pc_controller.open_app(app_name)
                return (f"open_{app_name}", voice_reply)

        return None

local_fast_path = LocalFastPath()
