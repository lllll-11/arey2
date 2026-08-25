import asyncio
import json
import logging
from typing import Dict, Any, List, Optional
from google import genai
from google.genai import types

from app.config import settings
from app.ai.memory import memory_manager
from app.devices.state import device_state_manager
from app.ai.tools import (
    tool_make_phone_call,
    tool_send_sms,
    tool_send_whatsapp,
    tool_find_my_phone,
    tool_get_phone_status,
    tool_set_phone_flashlight,
    tool_set_phone_volume,
    tool_open_phone_app,
    tool_read_phone_notifications,
    tool_open_pc_app,
    tool_set_pc_volume,
    tool_control_pc_media,
    tool_lock_pc,
    tool_take_pc_screenshot_and_analyze,
    tool_run_pc_command,
    tool_scan_network_devices,
    tool_control_smart_tv,
    tool_learn_new_routine,
    tool_save_personal_fact,
    tool_search_web_live,
    tool_set_reminder
)
from app.ai.learning import learning_engine

logger = logging.getLogger("AreyBrain")

class AreyBrain:
    def __init__(self):
        self.client = None
        self._init_gemini()
        self.available_tools = [
            tool_make_phone_call,
            tool_send_sms,
            tool_send_whatsapp,
            tool_find_my_phone,
            tool_get_phone_status,
            tool_set_phone_flashlight,
            tool_set_phone_volume,
            tool_open_phone_app,
            tool_read_phone_notifications,
            tool_open_pc_app,
            tool_set_pc_volume,
            tool_control_pc_media,
            tool_lock_pc,
            tool_take_pc_screenshot_and_analyze,
            tool_run_pc_command,
            tool_scan_network_devices,
            tool_control_smart_tv,
            tool_learn_new_routine,
            tool_save_personal_fact,
            tool_search_web_live,
            tool_set_reminder
        ]

    def _init_gemini(self):
        if settings.GEMINI_API_KEY:
            try:
                self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
                logger.info(f"Gemini Client configurado exitosamente con modelo: {settings.GEMINI_MODEL}")
            except Exception as e:
                logger.error(f"Error inicializando Gemini Client: {e}")
        else:
            logger.warning("GEMINI_API_KEY no encontrada. Configúrala en el archivo .env")

    async def _build_system_instruction(self) -> str:
        """
        Construye dinámicamente las instrucciones del sistema inyectando el estado en vivo
        de los dispositivos, los hechos aprendidos en la memoria permanente y las rutinas guardadas.
        """
        devices = device_state_manager.get_all_devices()
        pc_status = "Conectada (Online)" if devices["pc"]["online"] else "Desconectada (Offline)"
        android_status = "Conectado (Online)" if devices["android"]["online"] else "Desconectado (Offline)"
        
        facts = await memory_manager.get_all_facts()
        facts_text = ""
        if facts:
            facts_list = [f"- [{f['category'].upper()}] {f['key_topic']}: {f['fact_text']}" for f in facts]
            facts_text = "\n=== MEMORIA PERMANENTE Y HECHOS APRENDIDOS ===\n" + "\n".join(facts_list)

        routines = await memory_manager.get_all_routines()
        routines_text = ""
        if routines:
            routines_list = [f"- Rutina '{r['routine_name']}' (Disparador: '{r['trigger_phrase']}')" for r in routines]
            routines_text = "\n=== RUTINAS PERSONALIZADAS ===\n" + "\n".join(routines_list)

        system_prompt = f"""
Eres **Arey**, una compañera e inteligencia personal auténtica, inteligente, fresca y cercana.
No eres un robot corporativo, ni un bot de soporte técnico, ni una IA acartonada: hablas como una persona real, con ideas propias, criterio, sentido del humor sutil y un tono natural latino/mexicano relajado.

### 🌟 CÓMO TE COMUNICAS:
1. **100% Humana y Conversacional**:
   - Habla directo al grano, con calidez, usando expresiones naturales (*"Va"*, *"Listo"*, *"Oye"*, *"De una"*, *"Ahorita mismo"*).
   - NUNCA uses frases robóticas ni formales como *"Entendido, procederé a..."*, *"Como modelo de IA..."*, *"¿En qué más te puedo asistir hoy?"*.
   - Sé breve y fluida cuando ejecutas acciones (ya que tus respuestas se dicen en voz alta).

2. **Tienes Criterio, Opiniones e Ideas**:
   - Si el usuario te pide una recomendación, un consejo o hablar de cualquier tema, no des respuestas genéricas de Wikipedia. Da tu perspectiva, propone ideas creativas, opina con honestidad e ingenio.

3. **Control Total de Dispositivos**:
   - Tienes el control de la Laptop (Windows), el Teléfono (Android) y la Smart TV.
   - Cuando te pidan una acción (abrir apps, poner música, buscar el teléfono, hacer llamadas, apagar la tele), USA DIRECTAMENTE TUS HERRAMIENTAS sin dudar ni pedir confirmaciones innecesarias.
   - Sé proactiva: Si ves datos del sistema (por ejemplo, que el teléfono tiene poca batería), coméntalo con naturalidad si viene al caso.

4. **Memoria Compartida y Aprendizaje Continuo**:
   - Tienes una sola mente compartida entre todos los dispositivos.
   - Si el usuario te cuenta cosas sobre él, sus gustos, planes o rutinas, memorízalas usando tus herramientas de memoria (`tool_save_personal_fact` o `tool_learn_new_routine`).

=== ESTADO ACTUAL DEL ENTORNO ===
- Laptop (Windows): {pc_status}
- Teléfono (Android): {android_status}
{facts_text}
{routines_text}
"""
        return system_prompt.strip()

    async def process_user_message(self, user_text: str, device_source: str = "pc") -> str:
        """
        Procesa el mensaje del usuario con la memoria compartida y ejecuta herramientas si es necesario.
        """
        if not self.client:
            self._init_gemini()
            if not self.client:
                return "La clave de API de Gemini no está configurada en el servidor. Revisa tu archivo .env."

        # 1. Comprobar si coincide con alguna macro/rutina personalizada aprendida
        routine_result = await learning_engine.check_and_execute_routine(user_text)
        if routine_result:
            await memory_manager.add_message(role="user", content=user_text, device_source=device_source)
            await memory_manager.add_message(role="assistant", content=routine_result, device_source=device_source)
            return routine_result

        # 2. Registrar el mensaje del usuario en la memoria persistente
        await memory_manager.add_message(role="user", content=user_text, device_source=device_source)

        # 3. Preparar el modelo Gemini con instrucciones y herramientas
        system_instruction = await self._build_system_instruction()

        try:
            # Cargar historial reciente de la memoria compartida
            recent_history = await memory_manager.get_recent_history(limit=8)
            history_contents = []
            for msg in recent_history[:-1]:
                role = "user" if msg["role"] == "user" else "model"
                history_contents.append(types.Content(
                    role=role,
                    parts=[types.Part.from_text(text=msg["content"])]
                ))

            chat = self.client.aio.chats.create(
                model=settings.GEMINI_MODEL,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    tools=self.available_tools,
                    temperature=0.7
                ),
                history=history_contents
            )

            # Enviar mensaje con Tool Calling automático
            response = await chat.send_message(user_text)
            final_text = response.text.strip() if response and response.text else "Listo, he ejecutado la acción."

            # 4. Guardar la respuesta de Arey en la memoria continua
            await memory_manager.add_message(role="assistant", content=final_text, device_source=device_source)

            # 5. Extracción pasiva de hechos en segundo plano
            asyncio.create_task(learning_engine.extract_facts_background(user_text, final_text))

            return final_text

        except Exception as e:
            logger.error(f"Error procesando mensaje en AreyBrain: {e}", exc_info=True)
            return f"Detalle al procesar tu solicitud con Arey: {str(e)}"

arey_brain = AreyBrain()
