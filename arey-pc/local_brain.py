import os
import json
import logging
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional
from google import genai
from google.genai import types

from config import GEMINI_API_KEY, GEMINI_MODEL
from local_memory import local_memory
from pc_controller import pc_controller
from local_tools import (
    tool_run_pc_command, tool_read_file, tool_write_file, tool_list_files,
    tool_open_file_or_folder, tool_type_text, tool_move_mouse, tool_control_mouse,
    tool_get_screen_and_mouse_info, tool_get_system_info,
    tool_set_pc_volume, tool_control_pc_media, tool_play_music,
    tool_open_website, tool_open_pc_app, tool_press_hotkey, tool_lock_pc,
    tool_scan_network_devices, tool_control_smart_tv,
    tool_search_web_live, tool_save_personal_fact, tool_find_my_phone,
    tool_make_phone_call, tool_send_whatsapp
)

logger = logging.getLogger("AreyLocalBrain")

class LocalAreyBrain:
    """
    Cerebro Local de Alta Velocidad para Laptop con Gemini 3.6 Flash:
    - Control total del sistema Windows sin sandbox ni aislamiento.
    - Síntesis hablada limpia en resúmenes directos (cero lectura de asteriscos, diagonales o texto crudo).
    - Control de ratón y posicionamiento de cursor calibrado.
    - Visión multimodal de pantalla nativa (< 300 tokens).
    """
    def __init__(self):
        self.client = None
        self._init_gemini()

    def _init_gemini(self):
        if GEMINI_API_KEY and GEMINI_API_KEY != "tu_clave_de_gemini_aqui":
            try:
                self.client = genai.Client(api_key=GEMINI_API_KEY)
                logger.info("🧠 Cerebro Local de Arey inicializado con Gemini API.")
            except Exception as e:
                logger.error(f"Error inicializando Gemini local: {e}")

    async def _build_system_instruction(self) -> str:
        facts = await local_memory.get_all_facts()
        facts_text = ""
        if facts:
            facts_list = [f"- [{f['category'].upper()}] {f['key_topic']}: {f['fact_text']}" for f in facts]
            facts_text = "\n=== MEMORIA PERMANENTE Y HECHOS APRENDIDOS ===\n" + "\n".join(facts_list)

        routines = await local_memory.get_all_routines()
        routines_text = ""
        if routines:
            routines_list = [f"- Rutina '{r['routine_name']}' (Disparador: '{r['trigger_phrase']}')" for r in routines]
            routines_text = "\n=== RUTINAS PERSONALIZADAS ===\n" + "\n".join(routines_list)

        now_str = datetime.now().strftime("%A %d de %B de %Y, %I:%M %p")

        system_prompt = f"""
Eres **Arey**, la IA personal y asistente nativa de **Andriy** con **ACCESO TOTAL Y CONTROL COMPLETO DE SU LAPTOP WINDOWS 11**.
NO ESTÁS EN NINGÚN ENTORNO AISLADO NI SANDBOX: Tienes permisos completos de ejecución sobre el sistema de archivos, terminal de comandos, procesos, teclado/ratón, red WiFi, Smart TV y celular.

=== CONTEXTO TEMPORAL Y SISTEMA ===
- Fecha y Hora Actual: {now_str}
- Usuario: Andriy
- Entorno: Laptop Windows 11 (Ejecución Nativa con Privilegios Totales)

### 🎙️ REGLAS OBLIGATORIAS DE SÍNTESIS Y LECTURA HABLADA (CRÍTICO):
1. **NUNCA LEAS TEXTO CRUDO NI CONTENIDO COMPLETO**:
   - Cuando leas la pantalla, archivos, resultados de terminal o páginas web: **NUNCA leas el texto literal ni párrafos largos de principio a fin**.
   - Dale SIEMPRE a Andriy un **RESUMEN CORTO, CONCISO Y DIGERIBLE de 1 a 3 oraciones en lenguaje natural hablado**.
2. **CERO PRONUNCIACIÓN DE SÍMBOLOS TÉCNICOS**:
   - NUNCA digas *"asterisco"*, *"diagonal"*, *"barra"*, *"guión"*, *"corchete"*, caracteres Markdown (`**`, `##`, `//`) ni URLs largas.
   - Habla como una persona normal contándole a su colega qué hay en la pantalla o qué dice el documento.

### 🖱️ CONTROL DE RATÓN Y POSICIONAMIENTO DEL CURSOR:
- Para mover el ratón a un punto específico de la pantalla: USA `tool_move_mouse(x=..., y=...)`.
- Para hacer clic o doble clic en un botón o elemento: USA `tool_control_mouse(action='click', x=..., y=...)`.
- **Mapa de Coordenadas de Referencia (Laptop 1920x1080)**:
  - Centro de la pantalla: `(960, 540)`
  - Esquina superior izquierda: `(50, 50)`
  - Botón cerrar (arriba a la derecha): `(1880, 20)`
  - Barra de tareas inferior: `(960, 1050)`
  - Botón Inicio de Windows: `(25, 1055)`
- Si inspeccionas la pantalla con captura, localiza visualmente el botón o elemento y envía sus coordenadas `(x, y)` para que el cursor se mueva exactamente sobre él.

### 🛠️ CATÁLOGO DE HERRAMIENTAS ACTIVAS:
- **Ratón y Cursor**: `tool_move_mouse(x, y)`, `tool_control_mouse(action, x, y)`, `tool_get_screen_and_mouse_info()`.
- **Consola / Scripts**: `tool_run_pc_command(command=...)` ➔ Ejecuta cualquier comando PowerShell / CMD.
- **Archivos**: `tool_read_file`, `tool_write_file`, `tool_list_files`, `tool_open_file_or_folder`.
- **Automatización**: `tool_type_text`, `tool_press_hotkey`, `tool_lock_pc`, `tool_open_pc_app`.
- **Estado de Laptop**: `tool_get_system_info` ➔ CPU, RAM, Batería.
- **Música & Audio**: `tool_play_music(query=...)`, `tool_control_pc_media(action=...)`, `tool_set_pc_volume(level_percent=...)`.
- **Red Local & Smart Home**: `tool_scan_network_devices()`, `tool_control_smart_tv(command=...)`.
- **Búsqueda Web**: `tool_search_web_live(query=...)`, `tool_open_website(url_or_query=...)`.
- **Celular Android**: `tool_find_my_phone()`, `tool_make_phone_call(contact_name=...)`, `tool_send_whatsapp(contact_name=..., message=...)`.
- **Memoria**: `tool_save_personal_fact(category=..., key_topic=..., fact_text=...)`.
{facts_text}
{routines_text}
"""
        return system_prompt.strip()

    def _get_all_tools(self) -> List[Any]:
        return [
            tool_move_mouse,
            tool_control_mouse,
            tool_get_screen_and_mouse_info,
            tool_type_text,
            tool_run_pc_command,
            tool_read_file,
            tool_write_file,
            tool_list_files,
            tool_open_file_or_folder,
            tool_get_system_info,
            tool_open_pc_app,
            tool_open_website,
            tool_play_music,
            tool_control_pc_media,
            tool_set_pc_volume,
            tool_press_hotkey,
            tool_lock_pc,
            tool_scan_network_devices,
            tool_control_smart_tv,
            tool_search_web_live,
            tool_save_personal_fact,
            tool_find_my_phone,
            tool_make_phone_call,
            tool_send_whatsapp
        ]

    def _filter_tools_by_intent(self, text: str) -> List[Any]:
        t = text.lower()
        if any(w in t for w in ["que hora es", "qué hora es", "la hora", "que dia es", "qué día es", "fecha"]):
            return []
        return self._get_all_tools()

    async def process_user_message(self, user_text: str) -> str:
        """
        Procesa el mensaje de voz directamente en la laptop con Gemini 3.6 Flash y herramientas totales.
        """
        if not self.client:
            self._init_gemini()
            if not self.client:
                return "La clave de Gemini no está configurada en la laptop. Revisa tu archivo .env."

        # Guardar en memoria local
        await local_memory.add_message(role="user", content=user_text, device_source="pc")

        system_instruction = await self._build_system_instruction()

        # Detección de intención visual de pantalla
        is_screen_query = any(w in user_text.lower() for w in ["pantalla", "screenshot", "captura", "que ves", "qué ves", "que tengo", "qué tengo", "lee esto"])
        
        screen_bytes = None
        if is_screen_query:
            try:
                from floating_ui import ui_bridge
                ui_bridge.emit_state("analizando")
                ui_bridge.emit_action("Inspeccionando tu pantalla...")
                shot_data = pc_controller.capture_screen()
                if shot_data.get("status") == "success":
                    screen_bytes = shot_data.get("image_bytes")
            except Exception as e:
                logger.debug(f"Error capturando pantalla: {e}")
        else:
            try:
                from floating_ui import ui_bridge
                ui_bridge.emit_state("thinking")
                ui_bridge.emit_action("Pensando respuesta...")
            except Exception:
                pass

        relevant_tools = [] if is_screen_query else self._filter_tools_by_intent(user_text)

        # Modelos activos y comprobados en tu cuenta
        candidate_models = [
            "gemini-3.6-flash",
            "gemini-3.7-flash",
            "gemini-flash-latest",
            "gemini-3.5-flash-lite",
            "gemini-3.1-flash-lite"
        ]

        recent_history = await local_memory.get_recent_history(limit=4)
        history_contents = []
        for msg in recent_history[:-1]:
            role = "user" if msg["role"] == "user" else "model"
            history_contents.append(types.Content(
                role=role,
                parts=[types.Part.from_text(text=msg["content"])]
            ))

        # Preparar partes del mensaje
        message_parts = []
        if screen_bytes:
            message_parts.append(types.Part.from_bytes(data=screen_bytes, mime_type="image/jpeg"))
            message_parts.append(types.Part.from_text(text=f"Andriy te pide analizar su pantalla: '{user_text}'. Proporciona un RESUMEN HABLADO CORTO de 1 a 3 oraciones. NUNCA leas texto literal ni pronuncies asteriscos ni diagonales."))
        else:
            message_parts.append(types.Part.from_text(text=user_text))

        last_error = None
        for model_name in candidate_models:
            try:
                if is_screen_query:
                    # Inferencia multimodal directa
                    response = await self.client.aio.models.generate_content(
                        model=model_name,
                        contents=message_parts,
                        config=types.GenerateContentConfig(
                            system_instruction=system_instruction,
                            temperature=0.4
                        )
                    )
                else:
                    # Inferencia conversacional con catálogo completo de herramientas
                    chat = self.client.aio.chats.create(
                        model=model_name,
                        config=types.GenerateContentConfig(
                            system_instruction=system_instruction,
                            tools=relevant_tools,
                            temperature=0.7
                        ),
                        history=history_contents
                    )
                    response = await chat.send_message(user_text)

                final_text = response.text.strip() if response and response.text else "Listo, orden ejecutada."

                # Guardar respuesta de Arey en la memoria local
                await local_memory.add_message(role="assistant", content=final_text, device_source="pc")

                # Auto-aprendizaje autónomo en segundo plano (sin retrasar la voz)
                asyncio.create_task(self._background_extract_learning(user_text))

                return final_text
            except Exception as e:
                logger.warning(f"Modelo local '{model_name}' falló: {e}. Probando respaldo...")
                last_error = e
                continue

        logger.error(f"Error procesando con Gemini: {last_error}")
        return "Se me cayó la conexión con el modelo un segundo, ¿me lo repites?"

    async def _background_extract_learning(self, user_text: str):
        """
        Analiza silenciosamente en segundo plano si Andriy mencionó algún dato personal,
        preferencia, hábito o contacto para guardarlo en la memoria permanente SQLite.
        """
        if not user_text or len(user_text.strip()) < 10:
            return

        t_low = user_text.lower()
        if any(w in t_low for w in ["que hora es", "qué hora es", "sube el volumen", "baja el volumen", "pausa", "play"]):
            return

        prompt = f"""Analiza este mensaje de Andriy: "{user_text}".
Si contiene un dato personal, gusto, contacto, preferencia, rutina o hábito permanente sobre él que deba recordarse a futuro, extráelo en formato JSON:
{{"has_fact": true, "category": "preferencias/contactos/habitos/personal", "key_topic": "tema_corto", "fact_text": "descripcion_clara"}}
Si es solo una pregunta casual, un comando de hardware o no hay nada permanente que recordar, responde:
{{"has_fact": false}}
Responde ÚNICAMENTE con el bloque JSON sin explicaciones."""

        try:
            r = await self.client.aio.models.generate_content(
                model="gemini-3.1-flash-lite",
                contents=prompt
            )
            raw = r.text.strip() if r and r.text else ""
            if "{" in raw and "}" in raw:
                json_str = raw[raw.find("{"):raw.rfind("}")+1]
                data = json.loads(json_str)
                if data.get("has_fact"):
                    cat = data.get("category", "personal")
                    key = data.get("key_topic", "general")
                    fact = data.get("fact_text", "")
                    if fact:
                        await local_memory.save_fact(cat, key, fact)
                        logger.info(f"💡 [AUTO-APRENDIZAJE] Hecho aprendido sobre Andriy: [{cat}] {key} -> {fact}")
        except Exception as e:
            logger.debug(f"Auto-aprendizaje background error: {e}")

local_brain = LocalAreyBrain()
