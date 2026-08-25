import base64
import logging
from typing import Optional
from google import genai
from google.genai import types
from app.config import settings

logger = logging.getLogger("AreyVision")

class VisionEngine:
    def __init__(self):
        self.client = None
        if settings.GEMINI_API_KEY:
            try:
                self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
            except Exception as e:
                logger.error(f"Error iniciando vision client: {e}")

    async def analyze_screen_or_image(self, image_base64: str, prompt: str = "Describe lo que ves y ayuda al usuario") -> str:
        """
        Analiza una imagen o captura de pantalla enviada desde la laptop o el teléfono usando Gemini Multimodal.
        """
        if not self.client:
            if settings.GEMINI_API_KEY:
                self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
            else:
                return "La clave de Gemini no está configurada."

        try:
            image_bytes = base64.b64decode(image_base64)
            image_part = types.Part.from_bytes(
                data=image_bytes,
                mime_type="image/jpeg"
            )

            system_prompt = (
                "Eres Arey, un asistente inteligente con capacidades de visión. "
                "El usuario te está mostrando la pantalla de su laptop o una foto de su cámara. "
                "Responde de forma clara, concisa, útil y en español natural."
            )

            response = await self.client.aio.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=[image_part, prompt],
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=0.4
                )
            )
            return response.text.strip() if response and response.text else "No pude interpretar la imagen."
        except Exception as e:
            logger.error(f"Error en análisis de visión: {e}")
            return f"Ocurrió un error al analizar la pantalla: {str(e)}"

vision_engine = VisionEngine()
