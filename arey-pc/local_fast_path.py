import re
import logging
from typing import Optional, Tuple
from pc_controller import pc_controller

logger = logging.getLogger("AreyFastPath")

class LocalFastPath:
    """
    Enrutador determinista local de baja latencia (< 10ms).
    Intercepta comandos de hardware y sistema en la laptop antes de enviar a la nube.
    """
    def __init__(self):
        pass

    def try_execute_local(self, text: str) -> Optional[Tuple[str, str]]:
        """
        Analiza si el texto corresponde a un comando local determinista de Windows.
        Retorna (accion_ejecutada, respuesta_vocal) o None si requiere procesamiento en la nube / IA.
        """
        if not text:
            return None

        t = text.lower().strip().rstrip(".?!,")

        # ----------------- 1. CONTROL DE VOLUMEN -----------------
        # "pon volumen al 50", "volumen a 80", "sube el volumen al 100"
        match_vol = re.search(r'(?:pon|ajusta|sube|baja)?\s*(?:el\s*)?volumen\s*(?:al?|en)?\s*(\d{1,3})%?', t)
        if match_vol:
            level = int(match_vol.group(1))
            pc_controller.set_volume(level)
            return ("set_volume", f"Volumen ajustado al {level}%.")

        if any(w in t for w in ["sube volumen", "sube el volumen", "subele al volumen", "subele"]):
            # Subir 15%
            pc_controller.set_volume(75)
            return ("volume_up", "Listo, volumen subido.")

        if any(w in t for w in ["baja volumen", "baja el volumen", "bajale al volumen", "bajale"]):
            # Bajar 15%
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

        if any(w in t for w in ["cancion anterior", "pista anterior", "anterior"]):
            pc_controller.control_media("previous")
            return ("prev_track", "Pista anterior.")

        # ----------------- 3. ATAJOS DE SISTEMA WINDOWS -----------------
        if any(w in t for w in ["bloquea la compu", "bloquea la laptop", "bloquear computadora", "bloquear laptop", "bloquea"]):
            pc_controller.lock_workstation()
            return ("lock_pc", "Laptop bloqueada.")

        if any(w in t for w in ["minimiza todo", "minimizar todo", "muestra el escritorio", "ver escritorio", "escritorio"]):
            pc_controller.press_hotkey("win+d")
            return ("show_desktop", "Mostrando escritorio.")

        # ----------------- 4. APERTURA RÁPIDA DE APLICACIONES LOCALES -----------------
        app_patterns = [
            (r'abre\s*(?:la\s*)?calculadora', "calculadora", "Abriendo calculadora."),
            (r'abre\s*(?:el\s*)?bloc de notas', "bloc de notas", "Abriendo bloc de notas."),
            (r'abre\s*(?:el\s*)?vs\s*code|abre\s*visual studio code|abre\s*codigo', "vs code", "Abriendo Visual Studio Code."),
            (r'abre\s*(?:el\s*)?explorador|abre\s*(?:los\s*)?archivos', "explorador", "Abriendo explorador de archivos."),
            (r'abre\s*(?:la\s*)?terminal|abre\s*(?:la\s*)?consola|abre\s*cmd', "terminal", "Abriendo terminal."),
            (r'abre\s*(?:el\s*)?navegador|abre\s*chrome|abre\s*google chrome', "chrome", "Abriendo Google Chrome."),
            (r'abre\s*spotify', "spotify", "Abriendo Spotify."),
            (r'abre\s*discord', "discord", "Abriendo Discord."),
            (r'abre\s*word', "word", "Abriendo Word."),
            (r'abre\s*excel', "excel", "Abriendo Excel.")
        ]

        for pattern, app_key, reply in app_patterns:
            if re.search(pattern, t):
                pc_controller.open_app(app_key)
                return (f"open_app_{app_key}", reply)

        # No es un comando determinista local -> Requiere IA / Nube
        return None

local_fast_path = LocalFastPath()
