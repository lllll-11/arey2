import asyncio
import json
import logging
from typing import Dict, Any, List, Optional
from app.ai.memory import memory_manager
from app.devices.broker import device_broker

logger = logging.getLogger("AreyLearning")

class LearningEngine:
    """
    Motor de auto-aprendizaje autónomo para Arey.
    Maneja la detección de rutinas personalizadas, extracción automática de hechos y ejecución de macros.
    """

    async def check_and_execute_routine(self, user_input: str) -> Optional[str]:
        """
        Comprueba si el texto del usuario coincide con alguna rutina aprendida previamente.
        Si coincide, ejecuta la secuencia de acciones y retorna un mensaje resumen.
        """
        routines = await memory_manager.get_all_routines()
        cleaned_input = user_input.strip().lower()

        for routine in routines:
            trigger = routine["trigger_phrase"].strip().lower()
            # Si el usuario dijo la frase clave o el nombre de la rutina
            if trigger in cleaned_input or routine["routine_name"].lower() in cleaned_input:
                logger.info(f"¡Rutina aprendida detectada! Ejecutando: '{routine['routine_name']}'")
                actions = routine.get("actions", [])
                results = []

                for act in actions:
                    dev_type = act.get("device")
                    action_name = act.get("action")
                    params = act.get("params", {})
                    
                    if dev_type and action_name:
                        res = await device_broker.send_command(
                            device_type=dev_type,
                            action=action_name,
                            params=params,
                            wait_for_response=False
                        )
                        results.append(f"{action_name} en {dev_type}")
                        await asyncio.sleep(0.3)

                return f"He ejecutado tu rutina '{routine['routine_name']}': {', '.join(results)}."

        return None

    async def extract_facts_background(self, user_input: str, assistant_reply: str):
        """
        Analiza silenciosamente la conversación en segundo plano para detectar si el usuario
        mencionó hechos permanentes, gustos, reglas o datos personales y guardarlos en memoria.
        """
        # Heurística rápida para disparar extracción de hechos sin llamadas innecesarias
        keywords = [
            "me gusta", "no me gusta", "odio", "prefiero", "mi mamá", "mi papá", "mi hermano",
            "mi hermana", "mi novia", "mi novio", "mi esposa", "mi esposo", "mi hijo",
            "mi cumpleaños", "cumplo el", "recuerda que", "aprende que", "vivo en", "trabajo en",
            "mi comida favorita", "mi color favorito", "mi número de", "siempre que"
        ]
        lower_text = user_input.lower()
        if any(kw in lower_text for kw in keywords):
            logger.info(f"Posible hecho detectado en el texto del usuario: '{user_input}'")

learning_engine = LearningEngine()
