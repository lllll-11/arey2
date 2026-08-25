import json
import logging
from contextlib import asynccontextmanager
from typing import Dict, Any, List, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.config import settings
from app.ai.memory import memory_manager
from app.ai.brain import arey_brain
from app.ai.vision import vision_engine
from app.devices.broker import device_broker
from app.devices.state import device_state_manager
from app.scheduler.timer import scheduler
from app.integrations.alexa import AlexaHandler

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("AreyServer")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Iniciando Arey Server Brain...")
    await memory_manager.init_db()
    scheduler.start()
    yield
    logger.info("Apagando Arey Server...")
    scheduler.stop()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== MODELOS Pydantic ====================

class ChatRequest(BaseModel):
    message: str
    device_source: str = "web"

class ChatResponse(BaseModel):
    reply: str
    device_source: str

class VisionRequest(BaseModel):
    image_base64: str
    prompt: Optional[str] = "Describe lo que ves y ayuda al usuario"

class ContactItem(BaseModel):
    name: str
    phone: str

class SyncContactsRequest(BaseModel):
    contacts: List[ContactItem]

# ==================== WEBSOCKET EN TIEMPO REAL ====================

@app.websocket("/ws/device/{device_type}")
async def websocket_device_endpoint(
    websocket: WebSocket,
    device_type: str,
    token: Optional[str] = Query(None)
):
    """
    Canal de comunicación bidireccional en tiempo real para Laptop (pc), Teléfono (android) y Web.
    """
    await websocket.accept()
    client_ip = websocket.client.host if websocket.client else "unknown"
    await device_broker.register_connection(device_type, websocket, client_info={"ip": client_ip})

    try:
        while True:
            raw_data = await websocket.receive_text()
            try:
                msg = json.loads(raw_data)
            except Exception:
                continue

            msg_type = msg.get("type", "")

            # 1. Respuesta a un comando enviado previamente por el servidor
            if msg_type == "command_response":
                request_id = msg.get("request_id")
                response_data = msg.get("response", {})
                if request_id:
                    device_broker.resolve_response(request_id, response_data)

            # 2. Comando de voz o texto originado desde este dispositivo
            elif msg_type in ["voice_command", "text_message"]:
                user_text = msg.get("text", "").strip()
                if user_text:
                    logger.info(f"Mensaje recibido de {device_type.upper()}: '{user_text}'")
                    reply = await arey_brain.process_user_message(user_text, device_source=device_type)
                    # Devolver la respuesta a este dispositivo
                    await websocket.send_text(json.dumps({
                        "type": "brain_reply",
                        "text": reply,
                        "original_query": user_text
                    }))

            # 3. Actualización de estado del dispositivo (batería, volumen, app activa)
            elif msg_type == "status_update":
                status_data = msg.get("status", {})
                device_state_manager.update_device_status(device_type, online=True, extra_data=status_data)

            # 4. Sincronización de contactos desde el teléfono
            elif msg_type == "sync_contacts":
                contacts_list = msg.get("contacts", [])
                count = await memory_manager.sync_contacts(contacts_list)
                logger.info(f"Sincronizados {count} contactos desde {device_type}.")
                await websocket.send_text(json.dumps({
                    "type": "sync_ack",
                    "count": count
                }))

            # 5. Captura de pantalla enviada para análisis de visión
            elif msg_type == "screen_capture_analysis":
                img_b64 = msg.get("image_base64")
                prompt = msg.get("prompt", "Analiza la pantalla")
                analysis = await vision_engine.analyze_screen_or_image(img_b64, prompt)
                await websocket.send_text(json.dumps({
                    "type": "brain_reply",
                    "text": analysis
                }))

    except WebSocketDisconnect:
        device_broker.unregister_connection(device_type)
    except Exception as e:
        logger.error(f"Error en websocket con {device_type}: {e}")
        device_broker.unregister_connection(device_type)


# ==================== ENDPOINTS REST ====================

@app.get("/")
async def root():
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "status": "online",
        "model": settings.GEMINI_MODEL,
        "devices": device_state_manager.get_all_devices()
    }

@app.get("/health")
async def health():
    return {"status": "ok", "gemini_model": settings.GEMINI_MODEL}

@app.post("/api/chat", response_model=ChatResponse)
async def api_chat(req: ChatRequest):
    """
    Interactúa con el cerebro de Arey por REST.
    """
    reply = await arey_brain.process_user_message(req.message, device_source=req.device_source)
    return ChatResponse(reply=reply, device_source=req.device_source)

@app.post("/api/vision")
async def api_vision(req: VisionRequest):
    """
    Analiza una imagen o captura enviada por REST.
    """
    analysis = await vision_engine.analyze_screen_or_image(req.image_base64, req.prompt or "")
    return {"analysis": analysis}

@app.get("/api/devices")
async def get_devices():
    """
    Retorna el estado de todos los dispositivos conectados.
    """
    return device_state_manager.get_all_devices()

@app.post("/api/contacts/sync")
async def sync_contacts(req: SyncContactsRequest):
    """
    Sincroniza contactos del usuario con la memoria de Arey.
    """
    contacts_dicts = [{"name": c.name, "phone": c.phone} for c in req.contacts]
    count = await memory_manager.sync_contacts(contacts_dicts)
    return {"status": "success", "synced_count": count}

@app.get("/api/memory/facts")
async def get_facts():
    """
    Retorna la base de hechos aprendidos por Arey sobre el usuario.
    """
    facts = await memory_manager.get_all_facts()
    return {"facts": facts}

@app.get("/api/memory/routines")
async def get_routines():
    """
    Retorna las rutinas y macros aprendidas.
    """
    routines = await memory_manager.get_all_routines()
    return {"routines": routines}

@app.get("/api/memory/history")
async def get_history(limit: int = 30):
    """
    Retorna el historial unificado continuo de conversación.
    """
    history = await memory_manager.get_recent_history(limit=limit)
    return {"history": history}

@app.post("/api/alexa")
async def alexa_webhook(payload: Dict[str, Any] = Body(...)):
    """
    Webhook para solicitudes de Amazon Alexa Skill.
    """
    return await AlexaHandler.handle_alexa_request(payload)
