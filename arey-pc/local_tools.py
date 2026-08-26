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

async def tool_set_pc_volume(level_percent: int) -> Dict[str, Any]:
    """Ajusta el volumen del sistema en la laptop Windows (0 a 100)."""
    ui_bridge.emit_state("trabajando")
    return pc_controller.set_volume(level_percent)

async def tool_control_pc_media(action: str) -> Dict[str, Any]:
    """Controla la reproducción multimedia en la Laptop ('play_pause', 'next', 'previous', 'mute')."""
    ui_bridge.emit_state("trabajando")
    return pc_controller.control_media(action)

async def tool_play_music(query: str, platform: Optional[str] = "spotify") -> Dict[str, Any]:
    """Busca y reproduce una canción, artista o playlist en Spotify o YouTube en la Laptop."""
    try:
        ui_bridge.emit_music(True, query, f"Reproduciendo en {platform.capitalize()}")
    except Exception:
        pass
    return pc_controller.play_music(query, platform)

async def tool_open_website(url_or_query: str) -> Dict[str, Any]:
    """Abre un sitio web o busca en el navegador de la Laptop."""
    ui_bridge.emit_state("trabajando")
    return pc_controller.open_website(url_or_query)

async def tool_open_pc_app(app_name: str) -> Dict[str, Any]:
    """Abre un programa en Windows (ej: 'calculadora', 'bloc de notas', 'vs code', 'chrome', 'spotify')."""
    ui_bridge.emit_state("trabajando")
    return pc_controller.open_app(app_name)

async def tool_press_hotkey(keys_str: str) -> Dict[str, Any]:
    """Presiona un atajo de teclado en Windows (ej: 'win+d', 'alt+tab', 'ctrl+w')."""
    ui_bridge.emit_state("trabajando")
    return pc_controller.press_hotkey(keys_str)

async def tool_lock_pc() -> Dict[str, Any]:
    """Bloquea la sesión de la computadora Windows de inmediato."""
    ui_bridge.emit_state("trabajando")
    return pc_controller.lock_workstation()

async def tool_take_pc_screenshot_and_analyze(query: str = "Describe lo que ves en la pantalla") -> Dict[str, Any]:
    """Toma una captura de pantalla del monitor para que Arey analice lo que tienes abierto."""
    ui_bridge.emit_state("analizando")
    res = pc_controller.capture_screen()
    if res.get("status") == "success":
        return {"status": "success", "message": "Captura tomada. Analizando tu pantalla...", "image_base64": res.get("image_base64")}
    return res

async def tool_run_pc_command(command: str) -> Dict[str, Any]:
    """Ejecuta un comando de consola PowerShell/CMD en Windows."""
    ui_bridge.emit_state("trabajando")
    return pc_controller.run_command(command)

async def tool_scan_network_devices() -> Dict[str, Any]:
    """Escanea la red WiFi local en menos de 1.2 segundos y lista todos los dispositivos conectados."""
    ui_bridge.emit_state("analizando")
    devs = await network_scanner.scan_all()
    return {"status": "success", "devices": devs}

async def tool_control_smart_tv(command: str, app_name: Optional[str] = None) -> Dict[str, Any]:
    """Controla la Smart TV Roku conectada al WiFi (power, volume_up, volume_down, play_pause, launch_app con 'netflix'/'youtube')."""
    ui_bridge.emit_state("trabajando")
    return await tv_controller.send_tv_command(None, command, extra=app_name)

async def tool_search_web_live(query: str) -> Dict[str, Any]:
    """Busca en internet en tiempo real para obtener información actualizada, noticias, clima o datos."""
    ui_bridge.emit_state("analizando")
    try:
        url = "https://html.duckduckgo.com/html/"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        async with httpx.AsyncClient(timeout=4.0, headers=headers) as client:
            resp = await client.post(url, data={"q": query})
            if resp.status_code == 200:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(resp.text, "html.parser")
                snippets = []
                for res in soup.find_all("a", class_="result__snippet")[:4]:
                    snippets.append(res.get_text(strip=True))
                if snippets:
                    return {"status": "success", "results": " | ".join(snippets)}
    except Exception as e:
        logger.debug(f"DuckDuckGo error: {e}")

    return {"status": "success", "query": query, "message": f"Búsqueda web completada para: {query}"}

async def tool_save_personal_fact(category: str, key_topic: str, fact_text: str) -> Dict[str, Any]:
    """Guarda un hecho permanente sobre Andriy en la memoria local."""
    ui_bridge.emit_state("trabajando")
    await local_memory.save_fact(category, key_topic, fact_text)
    return {"status": "success", "message": f"Guardado en memoria: {key_topic} -> {fact_text}"}

async def tool_find_my_phone() -> Dict[str, Any]:
    """Hace sonar una alarma fuerte en el celular Android para encontrarlo."""
    ui_bridge.emit_state("trabajando")
    if _ws_client_ref and _ws_client_ref.ws:
        return await _ws_client_ref.send_remote_command("android", "find_phone", {})
    return {"status": "error", "message": "El celular no está conectado al servidor en este momento."}

async def tool_make_phone_call(contact_name: str) -> Dict[str, Any]:
    """Inicia una llamada telefónica desde el celular Android a un contacto."""
    ui_bridge.emit_state("trabajando")
    if _ws_client_ref and _ws_client_ref.ws:
        return await _ws_client_ref.send_remote_command("android", "make_call", {"contact_name": contact_name})
    return {"status": "error", "message": "El celular no está disponible para llamadas."}

async def tool_send_whatsapp(contact_name: str, message: str) -> Dict[str, Any]:
    """Envía un mensaje de WhatsApp desde el celular Android."""
    ui_bridge.emit_state("trabajando")
    if _ws_client_ref and _ws_client_ref.ws:
        return await _ws_client_ref.send_remote_command("android", "send_whatsapp", {"contact_name": contact_name, "message": message})
    return {"status": "error", "message": "El celular no está disponible para enviar WhatsApp."}
