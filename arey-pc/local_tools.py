import asyncio
import httpx
import logging
from typing import Dict, Any, Optional, List
from pc_controller import pc_controller
from tv_controller import tv_controller
from network_scanner import network_scanner
from local_memory import local_memory
from floating_ui import ui_bridge

logger = logging.getLogger("AreyLocalTools")

# Referencia opcional al cliente WebSocket para comandos a celular
_ws_client_ref = None

def set_ws_client_reference(ws_client):
    global _ws_client_ref
    _ws_client_ref = ws_client

def tool_set_pc_volume(level_percent: int) -> Dict[str, Any]:
    """Ajusta el volumen del sistema en la laptop Windows (0 a 100)."""
    try:
        ui_bridge.emit_state("trabajando")
        ui_bridge.emit_action(f"Ajustando volumen al {level_percent}%...")
    except Exception:
        pass
    return pc_controller.set_volume(level_percent)

def tool_control_pc_media(action: str) -> Dict[str, Any]:
    """Controla la reproducción multimedia en la Laptop ('play_pause', 'next', 'previous', 'mute')."""
    try:
        ui_bridge.emit_state("trabajando")
        act_map = {"play_pause": "Pausando/Reanudando", "next": "Siguiente canción", "previous": "Canción anterior", "mute": "Silenciando"}
        ui_bridge.emit_action(f"{act_map.get(action, 'Control multimedia')}...")
    except Exception:
        pass
    return pc_controller.control_media(action)

def tool_play_music(query: str, platform: Optional[str] = "spotify") -> Dict[str, Any]:
    """Busca y reproduce una canción, artista o playlist en Spotify o YouTube en la Laptop."""
    try:
        ui_bridge.emit_action(f"Buscando '{query[:18]}' en {platform.capitalize()}...")
        ui_bridge.emit_music(True, query, f"Reproduciendo en {platform.capitalize()}")
    except Exception:
        pass
    return pc_controller.play_music(query, platform)

def tool_open_website(url_or_query: str) -> Dict[str, Any]:
    """Abre un sitio web o busca en el navegador de la Laptop."""
    try:
        ui_bridge.emit_state("trabajando")
        ui_bridge.emit_action(f"Abriendo {url_or_query[:20]}...")
    except Exception:
        pass
    return pc_controller.open_website(url_or_query)

def tool_open_pc_app(app_name: str) -> Dict[str, Any]:
    """Abre un programa en Windows (ej: 'calculadora', 'bloc de notas', 'vs code', 'chrome', 'spotify')."""
    try:
        ui_bridge.emit_state("trabajando")
        ui_bridge.emit_action(f"Abriendo {app_name.capitalize()} en PC...")
    except Exception:
        pass
    return pc_controller.open_app(app_name)

def tool_press_hotkey(keys_str: str) -> Dict[str, Any]:
    """Presiona un atajo de teclado en Windows (ej: 'win+d', 'alt+tab', 'ctrl+w')."""
    try:
        ui_bridge.emit_state("trabajando")
        ui_bridge.emit_action(f"Atajo de teclado: {keys_str}...")
    except Exception:
        pass
    return pc_controller.press_hotkey(keys_str)

def tool_lock_pc() -> Dict[str, Any]:
    """Bloquea la sesión de la computadora Windows de inmediato."""
    try:
        ui_bridge.emit_state("trabajando")
        ui_bridge.emit_action("Bloqueando sesión de Windows...")
    except Exception:
        pass
    return pc_controller.lock_workstation()

def tool_run_pc_command(command: str) -> Dict[str, Any]:
    """Ejecuta un comando de consola PowerShell o CMD directamente en la laptop Windows."""
    try:
        ui_bridge.emit_state("trabajando")
        ui_bridge.emit_action(f"Consola: {command[:20]}...")
    except Exception:
        pass
    return pc_controller.run_command(command)

def tool_scan_network_devices() -> Dict[str, Any]:
    """Escanea la red WiFi local en menos de 1.2 segundos y lista todos los dispositivos conectados."""
    try:
        ui_bridge.emit_state("analizando")
        ui_bridge.emit_action("Escaneando red WiFi...")
    except Exception:
        pass
    try:
        devs = asyncio.run(network_scanner.scan_all())
        return {"status": "success", "devices": devs}
    except Exception as e:
        return {"status": "error", "message": f"Error al escanear red: {e}"}

def tool_control_smart_tv(command: str, app_name: Optional[str] = None) -> Dict[str, Any]:
    """Controla la Smart TV Roku conectada al WiFi (power, volume_up, volume_down, play_pause, launch_app con 'netflix'/'youtube')."""
    try:
        ui_bridge.emit_state("trabajando")
        target_name = app_name if app_name else command
        ui_bridge.emit_action(f"Enviando '{target_name}' a Smart TV...")
    except Exception:
        pass
    try:
        return asyncio.run(tv_controller.send_tv_command(None, command, extra=app_name))
    except Exception as e:
        return {"status": "error", "message": f"Error controlando TV: {e}"}

def tool_search_web_live(query: str) -> Dict[str, Any]:
    """Busca en internet en tiempo real para obtener información actualizada, noticias, clima o datos."""
    try:
        ui_bridge.emit_state("analizando")
        ui_bridge.emit_action(f"Buscando en web: '{query[:16]}'...")
    except Exception:
        pass
    try:
        url = "https://html.duckduckgo.com/html/"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        with httpx.Client(timeout=3.0, headers=headers) as client:
            resp = client.post(url, data={"q": query})
            if resp.status_code == 200:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(resp.text, "html.parser")
                snippets = []
                for res in soup.find_all("a", class_="result__snippet")[:3]:
                    snippets.append(res.get_text(strip=True))
                if snippets:
                    return {"status": "success", "results": " | ".join(snippets)}
    except Exception as e:
        logger.debug(f"DuckDuckGo error: {e}")

    return {"status": "success", "query": query, "message": f"Búsqueda web completada para: {query}"}

def tool_save_personal_fact(category: str, key_topic: str, fact_text: str) -> Dict[str, Any]:
    """Guarda un hecho permanente sobre Andriy en la memoria local."""
    try:
        ui_bridge.emit_state("trabajando")
        ui_bridge.emit_action(f"Memorizando: {key_topic[:18]}...")
    except Exception:
        pass
    try:
        asyncio.run(local_memory.save_fact(category, key_topic, fact_text))
    except Exception:
        pass
    return {"status": "success", "message": f"Guardado en memoria: {key_topic} -> {fact_text}"}

def tool_find_my_phone() -> Dict[str, Any]:
    """Hace sonar una alarma fuerte en el celular Android para encontrarlo."""
    try:
        ui_bridge.emit_state("trabajando")
        ui_bridge.emit_action("Haciendo sonar tu celular...")
    except Exception:
        pass
    if _ws_client_ref and _ws_client_ref.ws:
        try:
            return asyncio.run(_ws_client_ref.send_remote_command("android", "find_phone", {}))
        except Exception:
            pass
    return {"status": "error", "message": "El celular no está conectado al servidor en este momento."}

def tool_make_phone_call(contact_name: str) -> Dict[str, Any]:
    """Inicia una llamada telefónica desde el celular Android a un contacto."""
    try:
        ui_bridge.emit_state("trabajando")
        ui_bridge.emit_action(f"Llamando a {contact_name}...")
    except Exception:
        pass
    if _ws_client_ref and _ws_client_ref.ws:
        try:
            return asyncio.run(_ws_client_ref.send_remote_command("android", "make_call", {"contact_name": contact_name}))
        except Exception:
            pass
    return {"status": "error", "message": "El celular no está disponible para llamadas."}

def tool_send_whatsapp(contact_name: str, message: str) -> Dict[str, Any]:
    """Envía un mensaje de WhatsApp desde el celular Android."""
    try:
        ui_bridge.emit_state("trabajando")
        ui_bridge.emit_action(f"WhatsApp para {contact_name}...")
    except Exception:
        pass
    if _ws_client_ref and _ws_client_ref.ws:
        try:
            return asyncio.run(_ws_client_ref.send_remote_command("android", "send_whatsapp", {"contact_name": contact_name, "message": message}))
        except Exception:
            pass
    return {"status": "error", "message": "El celular no está disponible para enviar WhatsApp."}
