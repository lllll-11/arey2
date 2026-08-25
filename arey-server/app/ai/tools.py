import json
import logging
from typing import Dict, Any, List
import httpx
from app.devices.broker import device_broker
from app.ai.memory import memory_manager
from app.devices.state import device_state_manager

logger = logging.getLogger("AreyTools")

# ==================== IMPLEMENTACIONES DE HERRAMIENTAS ====================

async def tool_make_phone_call(contact_name_or_number: str) -> Dict[str, Any]:
    """
    Realiza una llamada telefónica en el teléfono Android a un número o nombre de contacto.
    """
    phone_number = contact_name_or_number
    # Si parece un nombre, buscar en contactos sincronizados
    if not any(c.isdigit() for c in contact_name_or_number):
        contact = await memory_manager.search_contact(contact_name_or_number)
        if contact:
            phone_number = contact["phone_number"]
            contact_name = contact["name"]
        else:
            return {"status": "error", "message": f"No encontré el contacto '{contact_name_or_number}' en la agenda del teléfono."}
    else:
        contact_name = phone_number

    res = await device_broker.send_command(
        device_type="android",
        action="make_call",
        params={"phone_number": phone_number, "contact_name": contact_name}
    )
    return res

async def tool_send_sms(contact_name_or_number: str, message: str) -> Dict[str, Any]:
    """
    Envía un mensaje de texto SMS a través del teléfono Android.
    """
    phone_number = contact_name_or_number
    if not any(c.isdigit() for c in contact_name_or_number):
        contact = await memory_manager.search_contact(contact_name_or_number)
        if contact:
            phone_number = contact["phone_number"]
        else:
            return {"status": "error", "message": f"No encontré a '{contact_name_or_number}' en tus contactos."}

    res = await device_broker.send_command(
        device_type="android",
        action="send_sms",
        params={"phone_number": phone_number, "message": message}
    )
    return res

async def tool_send_whatsapp(contact_name_or_number: str, message: str) -> Dict[str, Any]:
    """
    Envía un mensaje por WhatsApp a través del teléfono Android.
    """
    phone_number = contact_name_or_number
    if not any(c.isdigit() for c in contact_name_or_number):
        contact = await memory_manager.search_contact(contact_name_or_number)
        if contact:
            phone_number = contact["phone_number"]
        else:
            return {"status": "error", "message": f"No se encontró el contacto '{contact_name_or_number}' para WhatsApp."}

    res = await device_broker.send_command(
        device_type="android",
        action="send_whatsapp",
        params={"phone_number": phone_number, "message": message}
    )
    return res

async def tool_find_my_phone() -> Dict[str, Any]:
    """
    Activa una alarma sonora a volumen máximo y linterna estroboscópica en el teléfono para localizarlo.
    """
    res = await device_broker.send_command(
        device_type="android",
        action="find_phone",
        params={"duration_seconds": 20}
    )
    return res

async def tool_get_phone_status() -> Dict[str, Any]:
    """
    Obtiene el estado actual del teléfono Android (batería, cargando, volumen, linterna).
    """
    res = await device_broker.send_command(
        device_type="android",
        action="get_status"
    )
    return res

async def tool_set_phone_flashlight(turn_on: bool) -> Dict[str, Any]:
    """
    Enciende o apaga la linterna del teléfono Android.
    """
    res = await device_broker.send_command(
        device_type="android",
        action="set_flashlight",
        params={"turn_on": turn_on}
    )
    return res

async def tool_set_phone_volume(level_percent: int) -> Dict[str, Any]:
    """
    Ajusta el volumen del teléfono Android (0 a 100).
    """
    res = await device_broker.send_command(
        device_type="android",
        action="set_volume",
        params={"level_percent": max(0, min(100, level_percent))}
    )
    return res

async def tool_open_phone_app(app_name: str) -> Dict[str, Any]:
    """
    Abre una aplicación específica en el teléfono Android (ej: WhatsApp, YouTube, Spotify, Cámara, Google Maps).
    """
    res = await device_broker.send_command(
        device_type="android",
        action="open_app",
        params={"app_name": app_name}
    )
    return res

async def tool_read_phone_notifications() -> Dict[str, Any]:
    """
    Lee las notificaciones recientes recibidas en el teléfono Android.
    """
    res = await device_broker.send_command(
        device_type="android",
        action="get_notifications"
    )
    return res

# ----------------- HERRAMIENTAS PARA LAPTOP / WINDOWS -----------------

async def tool_open_pc_app(app_name: str) -> Dict[str, Any]:
    """
    Abre una aplicación o programa en la Laptop / PC Windows (ej: Chrome, Spotify, Visual Studio Code, Word, Calculadora).
    """
    res = await device_broker.send_command(
        device_type="pc",
        action="open_app",
        params={"app_name": app_name}
    )
    return res

async def tool_set_pc_volume(level_percent: int) -> Dict[str, Any]:
    """
    Ajusta el volumen principal de la Laptop / PC (0 a 100).
    """
    res = await device_broker.send_command(
        device_type="pc",
        action="set_volume",
        params={"level_percent": max(0, min(100, level_percent))}
    )
    return res

async def tool_control_pc_media(action: str) -> Dict[str, Any]:
    """
    Controla la reproducción multimedia en la PC: 'play_pause', 'next', 'previous', 'mute'.
    """
    res = await device_broker.send_command(
        device_type="pc",
        action="control_media",
        params={"action": action}
    )
    return res

async def tool_lock_pc() -> Dict[str, Any]:
    """
    Bloquea la sesión de Windows en la Laptop / PC.
    """
    res = await device_broker.send_command(
        device_type="pc",
        action="lock_workstation"
    )
    return res

async def tool_take_pc_screenshot_and_analyze(query: str) -> Dict[str, Any]:
    """
    Toma una captura de la pantalla de la Laptop / PC y la envía al servidor para que Arey analice lo que se está viendo.
    """
    res = await device_broker.send_command(
        device_type="pc",
        action="capture_screen",
        params={"query": query},
        timeout=15.0
    )
    return res

async def tool_run_pc_command(command_or_script: str) -> Dict[str, Any]:
    """
    Ejecuta un comando de PowerShell / CMD o script generado dinámicamente en la Laptop.
    """
    res = await device_broker.send_command(
        device_type="pc",
        action="run_command",
        params={"command": command_or_script}
    )
    return res

async def tool_scan_network_devices() -> Dict[str, Any]:
    """
    Escanea la red WiFi local en busca de Smart TVs (Roku, LG, Samsung), bocinas y dispositivos inteligentes.
    """
    res = await device_broker.send_command(
        device_type="pc",
        action="scan_network",
        timeout=8.0
    )
    return res

async def tool_control_smart_tv(command: str, app_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Controla la Smart TV conectada a la red WiFi (encender, apagar, volumen, silenciar, pausar, abrir Netflix/YouTube).
    command: 'power', 'play', 'pause', 'play_pause', 'volume_up', 'volume_down', 'mute', 'home', 'launch_app'
    app_name: 'netflix', 'youtube', 'spotify', 'prime video' (si command es 'launch_app')
    """
    res = await device_broker.send_command(
        device_type="pc",
        action="control_tv",
        params={"command": command, "app_name": app_name}
    )
    return res

# ----------------- HERRAMIENTAS DE AUTO-APRENDIZAJE Y MEMORIA -----------------

async def tool_learn_new_routine(routine_name: str, trigger_phrase: str, actions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Aprende una nueva rutina o macro por voz creada por el usuario (ej: 'Modo Cine', 'Salí de casa').
    actions es una lista de pasos como: [{"device": "pc", "action": "set_volume", "params": {"level_percent": 70}}, ...]
    """
    success = await memory_manager.save_routine(routine_name, trigger_phrase, actions)
    if success:
        return {"status": "success", "message": f"He aprendido la nueva rutina '{routine_name}'. Ahora se activará cada vez que digas '{trigger_phrase}'."}
    return {"status": "error", "message": "No se pudo guardar la rutina en la base de datos."}

async def tool_save_personal_fact(category: str, key_topic: str, fact: str) -> Dict[str, Any]:
    """
    Guarda un nuevo hecho o preferencia en la memoria a largo plazo de Arey (ej: gustos, cumpleaños, reglas, datos personales).
    category: 'personal', 'preference', 'family', 'rule', 'work', 'habit'
    """
    success = await memory_manager.save_fact(category, key_topic, fact)
    if success:
        return {"status": "success", "message": f"Dato guardado en mi memoria permanente: [{key_topic}] {fact}"}
    return {"status": "error", "message": "Error al guardar en memoria."}

async def tool_search_web_live(query: str) -> Dict[str, Any]:
    """
    Busca información en internet en tiempo real para noticias, clima, cotizaciones, deportes y datos actualizados.
    """
    try:
        url = f"https://html.duckduckgo.com/html/?q={query}"
        async with httpx.AsyncClient(timeout=8.0, headers={"User-Agent": "Mozilla/5.0"}) as client:
            resp = await client.get(url)
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.text, "html.parser")
            results = []
            for r in soup.find_all("a", class_="result__snippet", limit=4):
                results.append(r.get_text(strip=True))
            snippet_text = " \n".join(results) if results else "No se encontraron resultados directos."
            return {"status": "success", "query": query, "results": snippet_text}
    except Exception as e:
        return {"status": "error", "error": f"Error en búsqueda web: {str(e)}"}

async def tool_set_reminder(trigger_time_iso: str, message: str, target_device: str = "all") -> Dict[str, Any]:
    """
    Programa un recordatorio o alarma para una fecha/hora específica (formato ISO 8601).
    """
    rem_id = await memory_manager.add_reminder(trigger_time_iso, message, target_device)
    return {"status": "success", "reminder_id": rem_id, "message": f"Recordatorio programado para {trigger_time_iso}: '{message}'"}


# ==================== MAPEO PARA GEMINI FUNCTION CALLING ====================

TOOL_FUNCTIONS_MAP = {
    "make_phone_call": tool_make_phone_call,
    "send_sms": tool_send_sms,
    "send_whatsapp": tool_send_whatsapp,
    "find_my_phone": tool_find_my_phone,
    "get_phone_status": tool_get_phone_status,
    "set_phone_flashlight": tool_set_phone_flashlight,
    "set_phone_volume": tool_set_phone_volume,
    "open_phone_app": tool_open_phone_app,
    "read_phone_notifications": tool_read_phone_notifications,
    "open_pc_app": tool_open_pc_app,
    "set_pc_volume": tool_set_pc_volume,
    "control_pc_media": tool_control_pc_media,
    "lock_pc": tool_lock_pc,
    "take_pc_screenshot_and_analyze": tool_take_pc_screenshot_and_analyze,
    "run_pc_command": tool_run_pc_command,
    "scan_network_devices": tool_scan_network_devices,
    "control_smart_tv": tool_control_smart_tv,
    "learn_new_routine": tool_learn_new_routine,
    "save_personal_fact": tool_save_personal_fact,
    "search_web_live": tool_search_web_live,
    "set_reminder": tool_set_reminder
}
