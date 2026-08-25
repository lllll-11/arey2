import logging
from typing import Dict, Any
from app.ai.brain import arey_brain

logger = logging.getLogger("AreyAlexa")

class AlexaHandler:
    @staticmethod
    async def handle_alexa_request(payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Procesa solicitudes provenientes de Amazon Alexa Skill y las conecta con el cerebro central de Arey.
        """
        request_type = payload.get("request", {}).get("type", "")
        
        if request_type == "LaunchRequest":
            return AlexaHandler._build_alexa_response(
                speech_text="Hola, soy Arey. Tus dispositivos están sincronizados. ¿Qué deseas que haga?",
                should_end_session=False
            )

        elif request_type == "IntentRequest":
            intent = payload.get("request", {}).get("intent", {})
            intent_name = intent.get("name", "")

            if intent_name in ["AMAZON.StopIntent", "AMAZON.CancelIntent"]:
                return AlexaHandler._build_alexa_response("Hasta luego.", should_end_session=True)
            elif intent_name == "AMAZON.HelpIntent":
                return AlexaHandler._build_alexa_response(
                    "Puedes pedirme que llame a alguien, que controle tu laptop, que busque tu teléfono o cualquier pregunta.",
                    should_end_session=False
                )
            
            # Obtener el comando o frase dicha por el usuario a Alexa
            slots = intent.get("slots", {})
            user_query = ""
            for slot_data in slots.values():
                if "value" in slot_data:
                    user_query = slot_data["value"]
                    break

            if not user_query:
                user_query = "Hola Arey"

            # Procesar con el cerebro único de Arey
            reply = await arey_brain.process_user_message(user_query, device_source="alexa")
            return AlexaHandler._build_alexa_response(reply, should_end_session=True)

        elif request_type == "SessionEndedRequest":
            return AlexaHandler._build_alexa_response("", should_end_session=True)

        return AlexaHandler._build_alexa_response("No entendí la solicitud.", should_end_session=True)

    @staticmethod
    def _build_alexa_response(speech_text: str, should_end_session: bool = True) -> Dict[str, Any]:
        return {
            "version": "1.0",
            "response": {
                "outputSpeech": {
                    "type": "PlainText",
                    "text": speech_text
                },
                "shouldEndSession": should_end_session
            }
        }
