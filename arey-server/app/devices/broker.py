import asyncio
import json
import uuid
import logging
from typing import Dict, Any, Optional
from fastapi import WebSocket
from app.devices.state import device_state_manager

logger = logging.getLogger("AreyBroker")

class DeviceBroker:
    def __init__(self):
        # Mapeo de device_type -> WebSocket
        self.active_connections: Dict[str, WebSocket] = {}
        # Mapeo de request_id -> asyncio.Future para esperar respuesta de comandos
        self.pending_requests: Dict[str, asyncio.Future] = {}

    async def register_connection(self, device_type: str, websocket: WebSocket, client_info: Optional[Dict[str, Any]] = None):
        # Si ya había una conexión previa para este tipo, cerrarla limpiamente
        if device_type in self.active_connections:
            try:
                await self.active_connections[device_type].close()
            except Exception:
                pass
        
        self.active_connections[device_type] = websocket
        device_state_manager.update_device_status(device_type, online=True, extra_data=client_info)
        logger.info(f"Dispositivo conectado: {device_type.upper()}")

    def unregister_connection(self, device_type: str):
        if device_type in self.active_connections:
            del self.active_connections[device_type]
            device_state_manager.update_device_status(device_type, online=False)
            logger.info(f"Dispositivo desconectado: {device_type.upper()}")

    def is_device_online(self, device_type: str) -> bool:
        return device_type in self.active_connections

    async def send_command(
        self,
        device_type: str,
        action: str,
        params: Optional[Dict[str, Any]] = None,
        wait_for_response: bool = True,
        timeout: float = 12.0
    ) -> Dict[str, Any]:
        """
        Envía un comando JSON al dispositivo indicado y espera la respuesta si es necesario.
        """
        if device_type not in self.active_connections:
            return {
                "success": False,
                "error": f"El dispositivo '{device_type}' no está conectado actualmente a Arey."
            }

        websocket = self.active_connections[device_type]
        request_id = str(uuid.uuid4())
        payload = {
            "type": "command",
            "request_id": request_id,
            "action": action,
            "params": params or {}
        }

        if wait_for_response:
            loop = asyncio.get_event_loop()
            future = loop.create_future()
            self.pending_requests[request_id] = future

            try:
                await websocket.send_text(json.dumps(payload))
                result = await asyncio.wait_for(future, timeout=timeout)
                return result
            except asyncio.TimeoutError:
                logger.warning(f"Timeout esperando respuesta de {device_type} para la acción {action}")
                return {
                    "success": False,
                    "error": f"El dispositivo {device_type} tardó demasiado en responder al comando '{action}'."
                }
            except Exception as e:
                logger.error(f"Error enviando comando a {device_type}: {e}")
                return {"success": False, "error": str(e)}
            finally:
                if request_id in self.pending_requests:
                    del self.pending_requests[request_id]
        else:
            try:
                await websocket.send_text(json.dumps(payload))
                return {"success": True, "message": f"Comando '{action}' enviado exitosamente a {device_type}."}
            except Exception as e:
                return {"success": False, "error": str(e)}

    def resolve_response(self, request_id: str, response_data: Dict[str, Any]):
        """
        Llamado cuando un dispositivo envía una respuesta a un comando previo.
        """
        if request_id in self.pending_requests:
            future = self.pending_requests[request_id]
            if not future.done():
                future.set_result(response_data)

    async def broadcast_event(self, event_type: str, data: Dict[str, Any], exclude_device: Optional[str] = None):
        """
        Transmite un evento a todos los dispositivos conectados.
        """
        payload = json.dumps({
            "type": "event",
            "event": event_type,
            "data": data
        })
        for dev_type, ws in list(self.active_connections.items()):
            if dev_type != exclude_device:
                try:
                    await ws.send_text(payload)
                except Exception as e:
                    logger.error(f"Error al transmitir a {dev_type}: {e}")

device_broker = DeviceBroker()
