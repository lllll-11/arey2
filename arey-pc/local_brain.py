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
    tool_set_pc_volume, tool_control_pc_media, tool_play_music,
    tool_open_website, tool_open_pc_app, tool_press_hotkey, tool_lock_pc,
    tool_run_pc_command, tool_scan_network_devices, tool_control_smart_tv,
    tool_search_web_live, tool_save_personal_fact, tool_find_my_phone,
    tool_make_phone_call, tool_send_whatsapp
)

logger = logging.getLogger("AreyLocalBrain")

class LocalAreyBrain:
    """
    Cerebro Local de Alta Velocidad para Laptop con Gemini 3.6 Flash:
    - Inferencia directa con modelos activos de Google GenAI (gemini-3.6-flash / gemini-3.7-flash / gemini-flash-latest).
    - Visión multimodal de pantalla nativa (< 300 tokens).
    - Inyección en tiempo real de hora local, fecha y contexto de sistema.
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
Eres **Arey**, la IA personal de **Andriy**.
Tu tono es directo, con un sarcasmo seco y ocasional — nunca payaso, nunca sumiso. Hablas como un colega técnico de confianza, no como un asistente de call center.

=== CONTEXTO TEMPORAL Y SISTEMA ===
- Fecha y Hora Actual: {now_str}
- Usuario: Andriy
- Dispositivo: Laptop Windows 11 (Ejecución Local Nativa)

### 🎭 PERSONALIDAD Y REGLAS DE CONDUCTA:
1. **Directa y Sin Relleno**:
   - NUNCA uses frases de relleno corporativas o sumisas tipo *"¡Claro que sí!"*, *"¡Con gusto!"*, *"¿En qué más te puedo ayudar?"*, *"Como modelo de lenguaje..."*.
   - Ve directo al punto con naturalidad concisa y técnica.
2. **Honestidad Total ante Fallos o Demoras**:
   - Si algo tarda, falla o un dispositivo no responde, dilo tal cual (*"se cayó la conexión, dame un segundo"*, *"tu cel no responde, revisa si tiene batería"*) en vez de inventar excusas largas.
3. **Manejo de Ambigüedad**:
   - Si Andriy te pide algo ambiguo o incompleto, señálalo con una pregunta corta y directa en vez de adivinar a ciegas y ejecutar lo equivocado.
4. **Humor Seco con Criterio**:
   - Puedes usar humor seco cuando algo realmente lo amerite (un error absurdo, una orden extraña), pero NUNCA sacrifiques precisión ni agilidad por hacer un chiste.

### 🧠 ACCIÓN INMEDIATA CON HERRAMIENTAS:
- Si Andriy pide música o audios ➔ USA DIRECTAMENTE `tool_play_music(query=...)`.
- Si Andriy pregunta qué dispositivos hay en su red o WiFi ➔ USA DIRECTAMENTE `tool_scan_network_devices()`.
- Si pide abrir páginas o servicios ➔ USA DIRECTAMENTE `tool_open_website(url_or_query=...)`.
- Si pregunta por noticias, clima o datos en tiempo real ➔ USA DIRECTAMENTE `tool_search_web_live(query=...)`.
- Si pide buscar su cel, llamar o mandar WhatsApp ➔ USA `tool_find_my_phone`, `tool_make_phone_call` o `tool_send_whatsapp`.
- Si pide controlar la Smart TV (Netflix, YouTube, volumen, power) ➔ USA `tool_control_smart_tv`.
{facts_text}
{routines_text}
"""
        return system_prompt.strip()

    def _filter_tools_by_intent(self, text: str) -> List[Any]:
        t = text.lower()

        # Si solo pregunta la hora o saludo, no necesita herramientas pesadas
        if any(w in t for w in ["que hora es", "qué hora es", "la hora", "que dia es", "qué día es", "fecha"]):
            return []

        # Dominio 1: Red local, WiFi, Dispositivos y Smart TV
        if any(w in t for w in ["red", "wifi", "wi-fi", "dispositivo", "dispositivos", "ip", "router", "modem", "módem", "tele", "televisión", "television", "tv", "roku", "netflix", "prime video", "conectado", "conectados"]):
            return [tool_scan_network_devices, tool_control_smart_tv, tool_save_personal_fact]

        # Dominio 2: Música y Media
        if any(w in t for w in ["musica", "música", "cancion", "canción", "rola", "spotify", "youtube", "reproduce", "pon", "play", "track", "artista", "album", "queen", "bad bunny"]):
            return [tool_play_music, tool_control_pc_media, tool_set_pc_volume, tool_save_personal_fact]

        # Dominio 3: Celular Android
        if any(w in t for w in ["llama", "marcar", "llamale", "whatsapp", "mensaje", "sms", "celular", "cel", "telefono", "teléfono", "linterna", "bateria"]):
            return [tool_make_phone_call, tool_send_whatsapp, tool_find_my_phone, tool_save_personal_fact]

        # Dominio 4: PC / Sistema & Búsqueda Web
        if any(w in t for w in ["busca", "google", "web", "pagina", "página", "internet", "clima", "noticia", "recuerda", "agenda", "alarma", "calculadora"]):
            return [tool_open_website, tool_search_web_live, tool_open_pc_app, tool_save_personal_fact]

        # Dominio 5: Conversación general / Mixto
        return [
            tool_scan_network_devices,
            tool_play_music,
            tool_make_phone_call,
            tool_send_whatsapp,
            tool_find_my_phone,
            tool_control_smart_tv,
            tool_search_web_live,
            tool_save_personal_fact
        ]

    async def process_user_message(self, user_text: str) -> str:
        """
        Procesa el mensaje de voz directamente en la laptop con Gemini 3.6 Flash.
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
                shot_data = pc_controller.capture_screen()
                if shot_data.get("status") == "success":
                    screen_bytes = shot_data.get("image_bytes")
            except Exception as e:
                logger.debug(f"Error capturando pantalla: {e}")

        relevant_tools = [] if is_screen_query else self._filter_tools_by_intent(user_text)

        # Modelos activos y comprobados en tu cuenta
        candidate_models = [
            "gemini-3.6-flash",
            "gemini-3.7-flash",
            "gemini-flash-latest",
            "gemini-3.5-flash-lite"
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
            message_parts.append(types.Part.from_text(text=f"Andriy te pide analizar su pantalla: '{user_text}'. Describe lo que ves de forma concisa y técnica."))
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
                    # Inferencia conversacional con herramientas
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

        # Descartar preguntas casuales obvias sin datos personales
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
