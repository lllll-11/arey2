import os
import json
import httpx
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("AreyTVController")
CACHE_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "devices_cache.json"))

DEFAULT_TV_CACHE = {
    "tv": {
        "ip": "192.168.1.5",
        "name": "Smart TV JVC 32 (Roku OS)",
        "protocol": "roku_ecp",
        "type": "smart_tv",
        "port": 8060
    }
}

class SmartTVController:
    """
    Controlador de alto rendimiento para Smart TV con caché de IP persistente (Roku ECP).
    """
    def __init__(self):
        self.cached_tv = self._load_cache()

    def _load_cache(self) -> Dict[str, Any]:
        if os.path.exists(CACHE_FILE):
            try:
                with open(CACHE_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("tv", DEFAULT_TV_CACHE["tv"])
            except Exception:
                pass
        self._save_cache(DEFAULT_TV_CACHE["tv"])
        return DEFAULT_TV_CACHE["tv"]

    def _save_cache(self, tv_data: Dict[str, Any]):
        try:
            with open(CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump({"tv": tv_data}, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.debug(f"Error guardando cache de TV: {e}")

    def update_cached_tv(self, ip: str, name: str = "Smart TV Roku", protocol: str = "roku_ecp"):
        tv_data = {"ip": ip, "name": name, "protocol": protocol, "type": "smart_tv", "port": 8060}
        self.cached_tv = tv_data
        self._save_cache(tv_data)
        logger.info(f"📺 Caché de TV actualizado: {name} en {ip}")

    async def get_active_tv(self) -> Dict[str, Any]:
        """Devuelve la TV en caché si responde en <800ms, o dispara re-escaneo."""
        ip = self.cached_tv.get("ip", "192.168.1.5")
        try:
            async with httpx.AsyncClient(timeout=0.8) as client:
                res = await client.get(f"http://{ip}:8060/query/device-info")
                if res.status_code == 200:
                    return self.cached_tv
        except Exception:
            pass

        # Si falló la IP cacheada, intentar escanear
        try:
            from network_scanner import network_scanner
            devices = await network_scanner.scan_all()
            tv = next((d for d in devices if "tv" in d.get("type", "").lower() or d.get("protocol") == "roku_ecp"), None)
            if tv:
                self.update_cached_tv(tv.get("ip"), tv.get("name", "Smart TV"))
                return tv
        except Exception:
            pass

        return self.cached_tv

    async def control_roku(self, ip: str, command: str, app_id: Optional[str] = None) -> Dict[str, Any]:
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

        app_map = {
            "netflix": "12",
            "youtube": "837",
            "spotify": "22297",
            "prime video": "13",
            "amazon": "13"
        }

        try:
            async with httpx.AsyncClient(timeout=1.5) as client:
                if command == "launch_app":
                    target_app = app_map.get(str(app_id).lower().strip(), app_id or "837")
                    resp = await client.post(f"http://{ip}:8060/launch/{target_app}")
                    if resp.status_code == 200:
                        return {"status": "success", "message": f"Abriendo app en la tele ({ip})."}
                else:
                    key = key_map.get(command.lower().strip(), command)
                    resp = await client.post(f"http://{ip}:8060/keypress/{key}")
                    if resp.status_code == 200:
                        return {"status": "success", "message": f"Comando '{command}' ejecutado en la tele."}

                return {"status": "error", "message": f"Respuesta de la tele: {resp.status_code}"}
        except Exception as e:
            logger.warning(f"Fallo al conectar a la TV en {ip}: {e}")
            return {"status": "error", "error": str(e)}

    async def send_tv_command(self, device: Optional[Dict[str, Any]], command: str, extra: Optional[str] = None) -> Dict[str, Any]:
        target = device or await self.get_active_tv()
        ip = target.get("ip", "192.168.1.5")
        return await self.control_roku(ip, command, app_id=extra)

tv_controller = SmartTVController()
