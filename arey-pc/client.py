import asyncio
import json
import logging
import websockets
from concurrent.futures import ThreadPoolExecutor

from config import SERVER_WS_URL, DEVICE_AUTH_TOKEN
from pc_controller import pc_controller
from voice_engine import voice_engine
from wake_word import wake_detector
from network_scanner import network_scanner
from tv_controller import tv_controller

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] AreyPC: %(message)s")
logger = logging.getLogger("AreyPCClient")

executor = ThreadPoolExecutor(max_workers=3)

class AreyPCClient:
    def __init__(self):
        self.ws = None
        self.running = True

    async def start(self):
        logger.info(f"Iniciando Agente de Laptop Arey. Conectando a {SERVER_WS_URL}...")
        while self.running:
            try:
                # Conectar al WebSocket del Servidor Arey
                async with websockets.connect(
                    f"{SERVER_WS_URL}?token={DEVICE_AUTH_TOKEN}",
                    ping_interval=20,
                    ping_timeout=20
                ) as ws:
                    self.ws = ws
                    logger.info("✅ Conexión establecida exitosamente con el cerebro de Arey.")

                    # Enviar estado inicial del sistema
                    await self._send_status()

                    # Ejecutar tareas concurrentes: receptor de comandos, escucha de voz y telemetría
                    listener_task = asyncio.create_task(self._listen_server_messages())
                    telemetry_task = asyncio.create_task(self._telemetry_loop())
                    voice_task = asyncio.create_task(self._voice_loop())

                    # Esperar hasta que alguna tarea falle o la conexión se cierre
                    done, pending = await asyncio.wait(
                        [listener_task, telemetry_task, voice_task],
                        return_when=asyncio.FIRST_EXCEPTION
                    )
                    for task in pending:
                        task.cancel()

            except (websockets.exceptions.ConnectionClosed, OSError) as e:
                logger.warning(f"Desconectado del servidor Arey ({e}). Reintentando en 5 segundos...")
                await asyncio.sleep(5)
            except Exception as e:
                logger.error(f"Error inesperado en cliente PC: {e}", exc_info=True)
                await asyncio.sleep(5)

    async def _send_status(self):
        if self.ws:
            status = pc_controller.get_system_status()
            await self.ws.send(json.dumps({
                "type": "status_update",
                "status": status
            }))

    async def _telemetry_loop(self):
        while self.running:
            await asyncio.sleep(60)
            await self._send_status()

    async def _listen_server_messages(self):
        """
        Escucha comandos remotos despachados por el Servidor Arey (desde el teléfono o Alexa).
        """
        while self.running:
            message_raw = await self.ws.recv()
            try:
                data = json.loads(message_raw)
            except Exception:
                continue

            msg_type = data.get("type")

            # 1. Ejecutar comando solicitado por el Servidor
            if msg_type == "command":
                request_id = data.get("request_id")
                action = data.get("action")
                params = data.get("params", {})
                logger.info(f"Comando remoto recibido: '{action}' con params: {params}")

                res = await self._execute_action(action, params)

                # Devolver respuesta al servidor
                await self.ws.send(json.dumps({
                    "type": "command_response",
                    "request_id": request_id,
                    "response": res
                }))

            # 2. Respuesta de voz generada por el Cerebro
            elif msg_type == "brain_reply":
                reply_text = data.get("text", "")
                if reply_text:
                    await voice_engine.speak(reply_text)

            # 3. Evento de recordatorio / alarma
            elif msg_type == "event" and data.get("event") == "reminder_alert":
                rem_data = data.get("data", {})
                rem_msg = rem_data.get("message", "Tienes un recordatorio pendiente.")
                await voice_engine.speak(f"Atención: {rem_msg}")

    async def _execute_action(self, action: str, params: dict) -> dict:
        """
        Ejecuta la acción solicitada en el sistema Windows.
        """
        if action == "set_volume":
            return pc_controller.set_volume(params.get("level_percent", 50))
        elif action == "open_app":
            return pc_controller.open_app(params.get("app_name", ""))
        elif action == "control_media":
            return pc_controller.control_media(params.get("action", "play_pause"))
        elif action == "lock_workstation":
            return pc_controller.lock_workstation()
        elif action == "capture_screen":
            res = pc_controller.capture_screen()
            query = params.get("query", "")
            if res.get("status") == "success":
                # Si se requiere análisis, enviar también para procesamiento
                return {"status": "success", "image_base64": res.get("image_base64"), "query": query}
            return res
        elif action == "run_command":
            return pc_controller.run_command(params.get("command", ""))
        elif action == "scan_network":
            devices = await network_scanner.scan_all()
            return {"status": "success", "devices": devices}
        elif action == "control_tv":
            cmd = params.get("command", "play_pause")
            app_name = params.get("app_name")
            # Buscar Smart TV en la red
            devices = await network_scanner.scan_all()
            tv = next((d for d in devices if "tv" in d.get("type", "").lower() or d.get("protocol") == "roku_ecp"), None)
            if tv:
                return await tv_controller.send_tv_command(tv, cmd, extra=app_name)
            return {"status": "error", "message": "No se encontró ninguna Smart TV activa en la red WiFi."}
        else:
            return {"status": "error", "message": f"Acción '{action}' no soportada en PC."}

    async def _voice_loop(self):
        """
        Bucle de escucha continua de voz: detecta 'Arey', escucha la orden y habla la respuesta.
        """
        loop = asyncio.get_running_loop()
        while self.running:
            # 1. Esperar detección de 'Arey' en hilo secundario
            detected = await loop.run_in_executor(executor, wake_detector.listen_for_wake_word)
            if detected:
                # Sonido de confirmación rápido
                await voice_engine.speak("¿Sí?")

                # 2. Escuchar la orden completa del usuario
                user_text = await loop.run_in_executor(executor, voice_engine.listen_speech)
                if user_text:
                    logger.info(f"Enviando consulta al cerebro de Arey: '{user_text}'")
                    if self.ws:
                        await self.ws.send(json.dumps({
                            "type": "voice_command",
                            "text": user_text
                        }))

if __name__ == "__main__":
    client = AreyPCClient()
    try:
        asyncio.run(client.start())
    except KeyboardInterrupt:
        logger.info("Agente de Laptop Arey detenido.")
