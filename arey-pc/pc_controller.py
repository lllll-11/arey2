import os
import sys
import subprocess
import ctypes
import io
import base64
import logging
import urllib.parse
import webbrowser
from typing import Dict, Any
from PIL import ImageGrab
import pyautogui
import psutil

logger = logging.getLogger("PCController")

class PCController:
    """
    Controlador de acciones nativas y avanzadas del sistema operativo Windows para Arey.
    """

    @staticmethod
    def set_volume(level_percent: int) -> Dict[str, Any]:
        """
        Ajusta el volumen del sistema en Windows.
        """
        try:
            level = max(0, min(100, int(level_percent)))
            ps_script = f"""
            $obj = New-Object -ComObject WScript.Shell
            1..50 | ForEach-Object {{ $obj.SendKeys([char]174) }}
            1..{int(level / 2)} | ForEach-Object {{ $obj.SendKeys([char]175) }}
            """
            subprocess.run(["powershell", "-NoProfile", "-Command", ps_script], creationflags=subprocess.CREATE_NO_WINDOW)
            return {"status": "success", "message": f"Volumen de la laptop ajustado a {level}%."}
        except Exception as e:
            logger.error(f"Error ajustando volumen: {e}")
            return {"status": "error", "error": str(e)}

    @staticmethod
    def control_media(action: str) -> Dict[str, Any]:
        """
        Controla la reproducción multimedia de Windows ('play_pause', 'next', 'previous', 'mute').
        """
        try:
            act = action.lower().strip()
            if act in ["play_pause", "play", "pause"]:
                pyautogui.press("playpause")
                return {"status": "success", "message": "Reproducción pausada / reanudada en la laptop."}
            elif act in ["next", "siguiente"]:
                pyautogui.press("nexttrack")
                return {"status": "success", "message": "Pista siguiente reproducida."}
            elif act in ["previous", "anterior", "prev"]:
                pyautogui.press("prevtrack")
                return {"status": "success", "message": "Pista anterior reproducida."}
            elif act in ["mute", "silencio"]:
                pyautogui.press("volumemute")
                return {"status": "success", "message": "Silencio activado/desactivado."}
            else:
                return {"status": "error", "message": f"Acción multimedia '{action}' no reconocida."}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    @staticmethod
    def play_music(query: str, platform: str = "spotify") -> Dict[str, Any]:
        """
        Busca y reproduce música en Spotify o YouTube.
        """
        try:
            q_clean = query.strip()
            encoded = urllib.parse.quote(q_clean)
            if platform.lower() == "spotify" or "spotify" in q_clean.lower():
                try:
                    subprocess.Popen(f"start spotify:search:{encoded}", shell=True)
                    return {"status": "success", "message": f"Buscando y reproduciendo '{q_clean}' en Spotify."}
                except Exception:
                    webbrowser.open(f"https://open.spotify.com/search/{encoded}")
                    return {"status": "success", "message": f"Abriendo Spotify Web para '{q_clean}'."}
            else:
                webbrowser.open(f"https://www.youtube.com/results?search_query={encoded}")
                return {"status": "success", "message": f"Buscando '{q_clean}' en YouTube."}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    @staticmethod
    def open_website(url_or_query: str) -> Dict[str, Any]:
        """
        Abre una página web o búsqueda en el navegador predeterminado.
        """
        try:
            target = url_or_query.strip()
            if not target.startswith("http://") and not target.startswith("https://"):
                if "." in target and " " not in target:
                    target = f"https://{target}"
                else:
                    target = f"https://www.google.com/search?q={urllib.parse.quote(target)}"
            webbrowser.open(target)
            return {"status": "success", "message": f"Abriendo {target} en tu navegador."}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    @staticmethod
    def open_app(app_name: str) -> Dict[str, Any]:
        """
        Abre una aplicación de Windows por su nombre o comando.
        """
        app_map = {
            "chrome": "start chrome",
            "google chrome": "start chrome",
            "navegador": "start https://www.google.com",
            "spotify": "start spotify:",
            "musica": "start spotify:",
            "vs code": "code",
            "vscode": "code",
            "visual studio code": "code",
            "bloc de notas": "notepad",
            "notepad": "notepad",
            "calculadora": "calc",
            "calc": "calc",
            "explorador": "explorer",
            "archivos": "explorer",
            "terminal": "start wt",
            "cmd": "start cmd",
            "powershell": "start powershell",
            "discord": "start discord:",
            "word": "start winword",
            "excel": "start excel",
            "whatsapp": "start whatsapp:"
        }
        
        target = app_map.get(app_name.lower().strip(), app_name)
        try:
            subprocess.Popen(f"start {target}" if not target.startswith("start ") else target, shell=True)
            return {"status": "success", "message": f"Abriendo '{app_name}' en la laptop."}
        except Exception as e:
            logger.error(f"Error abriendo aplicación '{app_name}': {e}")
            return {"status": "error", "error": str(e)}

    @staticmethod
    def lock_workstation() -> Dict[str, Any]:
        """
        Bloquea la sesión de Windows.
        """
        try:
            ctypes.windll.user32.LockWorkStation()
            return {"status": "success", "message": "Laptop bloqueada correctamente."}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    @staticmethod
    def press_hotkey(keys_str: str) -> Dict[str, Any]:
        """
        Presiona una combinación de teclas (ej: 'win+d' para ver escritorio, 'alt+tab', 'ctrl+w').
        """
        try:
            keys = [k.strip().lower() for k in keys_str.split("+")]
            pyautogui.hotkey(*keys)
            return {"status": "success", "message": f"Atajo de teclado '{keys_str}' ejecutado."}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    @staticmethod
    def capture_screen() -> Dict[str, Any]:
        """
        Toma una captura de la pantalla optimizada y comprimida para análisis con IA.
        """
        try:
            screenshot = ImageGrab.grab()
            screenshot.thumbnail((1280, 720))
            buffer = io.BytesIO()
            screenshot.save(buffer, format="JPEG", quality=60)
            img_bytes = buffer.getvalue()
            img_b64 = base64.b64encode(img_bytes).decode("utf-8")
            return {"status": "success", "image_bytes": img_bytes, "image_base64": img_b64}
        except Exception as e:
            logger.error(f"Error al capturar pantalla: {e}")
            return {"status": "error", "error": str(e)}

    @staticmethod
    def run_command(command: str) -> Dict[str, Any]:
        """
        Ejecuta un comando de consola en Windows de forma controlada.
        """
        try:
            res = subprocess.run(
                ["powershell", "-NoProfile", "-Command", command],
                capture_output=True,
                text=True,
                timeout=15,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            output = res.stdout if res.stdout else res.stderr
            return {
                "status": "success" if res.returncode == 0 else "error",
                "output": output.strip() if output else "Comando ejecutado sin salida."
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    @staticmethod
    def get_system_status() -> Dict[str, Any]:
        """
        Obtiene telemetría de la laptop: batería, CPU, RAM.
        """
        try:
            battery = psutil.sensors_battery()
            battery_percent = int(battery.percent) if battery else None
            is_charging = battery.power_plugged if battery else None
            cpu_usage = psutil.cpu_percent(interval=0.1)
            ram_usage = psutil.virtual_memory().percent
            
            return {
                "battery": battery_percent,
                "is_charging": is_charging,
                "cpu_percent": cpu_usage,
                "ram_percent": ram_usage
            }
        except Exception:
            return {}

    @staticmethod
    def get_system_stats() -> Dict[str, Any]:
        return PCController.get_system_status()

pc_controller = PCController()
