import httpx
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("AreyTVController")

class SmartTVController:
    """
    Controlador para Smart TVs (Roku TV, Android TV, Google TV, LG, Samsung).
    """

    @staticmethod
    async def control_roku(ip: str, command: str, app_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Envía comandos a Smart TVs Roku / Hisense / TCL con Roku OS.
        Comandos: 'power', 'play', 'pause', 'play_pause', 'volume_up', 'volume_down', 'mute', 'home', 'back', 'launch_app'
        """
        key_map = {
            "power": "Power",
            "play": "Play",
            "pause": "Play",
            "play_pause": "Play",
            "volume_up": "VolumeUp",
            "volume_down": "VolumeDown",
            "mute": "VolumeMute",
            "home": "Home",
            "back": "Back",
            "select": "Select",
            "left": "Left",
            "right": "Right",
            "up": "Up",
            "down": "Down"
        }

        try:
            async with httpx.AsyncClient(timeout=4.0) as client:
                if command == "launch_app":
                    # Apps comunes en Roku: Netflix (12), YouTube (837), Spotify (22297), Prime Video (13)
                    app_map = {
                        "netflix": "12",
                        "youtube": "837",
                        "spotify": "22297",
                        "prime video": "13",
                        "amazon": "13"
                    }
                    target_app = app_map.get(str(app_id).lower().strip(), app_id or "837")
                    resp = await client.post(f"http://{ip}:8060/launch/{target_app}")
                    if resp.status_code == 200:
                        return {"status": "success", "message": f"Abriendo app en la tele ({ip})."}
                else:
                    key = key_map.get(command.lower().strip(), command)
                    resp = await client.post(f"http://{ip}:8060/keypress/{key}")
                    if resp.status_code == 200:
                        return {"status": "success", "message": f"Comando '{command}' enviado a la tele ({ip})."}
                
                return {"status": "error", "message": f"Respuesta inesperada de la tele: {resp.status_code}"}
        except Exception as e:
            logger.error(f"Error controlando Roku TV en {ip}: {e}")
            return {"status": "error", "error": str(e)}

    @staticmethod
    async def send_tv_command(device: Dict[str, Any], command: str, extra: Optional[str] = None) -> Dict[str, Any]:
        """
        Enruta el comando según el protocolo del dispositivo (Roku, UPnP, etc.).
        """
        protocol = device.get("protocol", "")
        ip = device.get("ip", "")

        if protocol == "roku_ecp" or "roku" in device.get("type", "").lower():
            return await SmartTVController.control_roku(ip, command, app_id=extra)
        
        return {"status": "info", "message": f"Dispositivo en {ip} detectado ({device.get('name')}), ejecutando comando {command}."}

tv_controller = SmartTVController()
