import sys
import os
import threading
import asyncio
import json
import logging
import websockets
from concurrent.futures import ThreadPoolExecutor

from PyQt6.QtWidgets import QApplication

from config import SERVER_WS_URL, DEVICE_AUTH_TOKEN
from pc_controller import pc_controller
from audio_pipeline import audio_pipeline
from network_scanner import network_scanner
from tv_controller import tv_controller
from floating_ui import FloatingAreyCapsule, ui_bridge
from local_fast_path import local_fast_path
from performance_tracker import perf_tracker

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] AreyPC: %(message)s")
logger = logging.getLogger("AreyPCClient")

executor = ThreadPoolExecutor(max_workers=4)

class AreyPCClient:
    """
    Cliente Central de Laptop Arey 2.0:
    Coordina la interfaz Glassmorphism, el pipeline de audio, el control de Windows y la sincronización en la nube.
    """
    def __init__(self):
        self.ws = None
        self.running = True
        self.is_processing_voice = False
        self.force_wake_event = threading.Event()

    async def start(self):
        logger.info(f"🚀 Iniciando Agente de Laptop Arey 2.0. Conectando a {SERVER_WS_URL}...")
        
        # Conectar disparador manual (Alt+Espacio o Clic)
        ui_bridge.trigger_voice_requested.connect(self.trigger_manual_voice)

        # Iniciar bucle de escucha de voz permanente (una sola vez)
        asyncio.create_task(self._voice_loop())

        while self.running:
            try:
                async with websockets.connect(
                    f"{SERVER_WS_URL}?token={DEVICE_AUTH_TOKEN}",
                    ping_interval=20,
                    ping_timeout=20
                ) as ws:
                    self.ws = ws
                    logger.info("✅ Conexión establecida exitosamente con el cerebro de Arey.")
                    ui_bridge.subtitle_changed.emit("status", "Conectado. Di 'Arey' o presiona Alt + Espacio")

                    # Enviar estado inicial del sistema
                    await self._send_status()

                    # Escuchar mensajes remotos y telemetría
                    listener_task = asyncio.create_task(self._listen_server_messages())
                    telemetry_task = asyncio.create_task(self._telemetry_loop())

                    done, pending = await asyncio.wait(
                        [listener_task, telemetry_task],
                        return_when=asyncio.FIRST_EXCEPTION
                    )
                    for task in pending:
                        task.cancel()

            except (websockets.exceptions.ConnectionClosed, OSError) as e:
                logger.warning(f"Desconectado del servidor ({e}). Reintentando en 4s...")
                ui_bridge.subtitle_changed.emit("status", "Reconectando con la nube de Arey...")
                await asyncio.sleep(4)
            except Exception as e:
                logger.error(f"Error inesperado en cliente PC: {e}", exc_info=True)
                await asyncio.sleep(4)

    def trigger_manual_voice(self):
        """Activa la escucha de inmediato desde el atajo Alt+Espacio o el botón de la UI."""
        logger.info("⚡ Activación manual por Atajo Alt+Espacio / Botón UI")
        self.force_wake_event.set()

    async def _send_status(self):
        if self.ws:
            status = pc_controller.get_system_status()
            await self.ws.send(json.dumps({
                "type": "status_update",
                "status": status
            }))

    async def _telemetry_loop(self):
        while self.running:
            await asyncio.sleep(45)
            await self._send_status()

    async def _listen_server_messages(self):
        """
        Escucha comandos remotos y respuestas del cerebro en la nube.
        """
        while self.running:
            try:
                message_raw = await self.ws.recv()
            except Exception:
                break

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

                if self.ws:
                    await self.ws.send(json.dumps({
                        "type": "command_response",
                        "request_id": request_id,
                        "response": res
                    }))

            # 2. Respuesta de voz generada por el Cerebro de Arey
            elif msg_type == "brain_reply":
                perf_tracker.end_stage("Red / Cloud Inferencia")
                reply_text = data.get("text", "")
                if reply_text:
                    ui_bridge.state_changed.emit("speaking")
                    ui_bridge.subtitle_changed.emit("arey", reply_text)
                    await audio_pipeline.speak(reply_text)
                    ui_bridge.state_changed.emit("idle")
                    self.is_processing_voice = False
                    perf_tracker.print_summary(reply_text)

            # 3. Telemetría de dispositivos (Celular, Smart TV)
            elif msg_type == "devices_update":
                devices = data.get("devices", {})
                android = devices.get("android", {})
                ui_bridge.device_status_changed.emit({
                    "phone_battery": android.get("status", {}).get("battery"),
                    "phone_online": android.get("online", False),
                    "tv_online": True
                })

            # 4. Recordatorios / Alarmas
            elif msg_type == "event" and data.get("event") == "reminder_alert":
                rem_msg = data.get("data", {}).get("message", "Tienes un recordatorio pendiente.")
                ui_bridge.state_changed.emit("speaking")
                ui_bridge.subtitle_changed.emit("arey", f"Recordatorio: {rem_msg}")
                await audio_pipeline.speak(f"Atención: {rem_msg}")
                ui_bridge.state_changed.emit("idle")

    async def _execute_action(self, action: str, params: dict) -> dict:
        """
        Ejecuta acciones en el sistema Windows y Smart TV.
        """
        if action == "set_volume":
            return pc_controller.set_volume(params.get("level_percent", 50))
        elif action == "open_app":
            return pc_controller.open_app(params.get("app_name", ""))
        elif action == "control_media":
            return pc_controller.control_media(params.get("action", "play_pause"))
        elif action == "play_music":
            return pc_controller.play_music(params.get("query", ""), params.get("platform", "spotify"))
        elif action == "open_website":
            return pc_controller.open_website(params.get("url_or_query", ""))
        elif action == "press_hotkey":
            return pc_controller.press_hotkey(params.get("keys_str", ""))
        elif action == "lock_workstation":
            return pc_controller.lock_workstation()
        elif action == "capture_screen":
            res = pc_controller.capture_screen()
            query = params.get("query", "")
            if res.get("status") == "success":
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
            devices = await network_scanner.scan_all()
            tv = next((d for d in devices if "tv" in d.get("type", "").lower() or d.get("protocol") == "roku_ecp"), None)
            if tv:
                return await tv_controller.send_tv_command(tv, cmd, extra=app_name)
            return {"status": "error", "message": "No se encontró ninguna Smart TV activa en la red WiFi."}
        else:
            return {"status": "error", "message": f"Acción '{action}' no soportada en PC."}

    async def _voice_loop(self):
        """
        Bucle de escucha continua: reacciona a 'Arey', Alt+Espacio o Clic.
        Integra Fast-Path local (< 10ms) y observabilidad de latencia por etapas.
        """
        loop = asyncio.get_running_loop()
        while self.running:
            if not self.is_processing_voice:
                ui_bridge.state_changed.emit("idle")

            # 1. Comprobar si se activó por atajo o esperar por voz
            is_manual = self.force_wake_event.is_set()
            if is_manual:
                self.force_wake_event.clear()
                detected = True
            else:
                detected = await loop.run_in_executor(executor, audio_pipeline.listen_for_wake_word)

            if detected:
                perf_tracker.start_pipeline()
                self.is_processing_voice = True
                ui_bridge.state_changed.emit("listening")
                ui_bridge.subtitle_changed.emit("status", "Escuchando... Habla ahora")
                audio_pipeline.play_instant_wake()

                # 2. Escuchar la orden con Whisper Small (int8) + Silero VAD
                user_text = await loop.run_in_executor(executor, audio_pipeline.listen_command)

                if user_text and user_text.strip():
                    logger.info(f"🗣️ Orden recibida: '{user_text}'")
                    ui_bridge.subtitle_changed.emit("user", user_text)

                    # 3. FAST-PATH LOCAL: ¿Es un comando determinista de PC? (< 10ms)
                    perf_tracker.start_stage("Fast-Path Router")
                    local_match = local_fast_path.try_execute_local(user_text)
                    perf_tracker.end_stage("Fast-Path Router")

                    if local_match:
                        action_name, reply_text = local_match
                        logger.info(f"⚡ FAST-PATH LOCAL EJECUTADO: '{action_name}'")
                        ui_bridge.state_changed.emit("speaking")
                        ui_bridge.subtitle_changed.emit("arey", reply_text)
                        await audio_pipeline.speak(reply_text)
                        ui_bridge.state_changed.emit("idle")
                        self.is_processing_voice = False
                        perf_tracker.print_summary(user_text)
                        continue

                    # 4. Si requiere razonamiento / IA, enviar al servidor Cloud
                    ui_bridge.state_changed.emit("thinking")
                    perf_tracker.start_stage("Red / Cloud Inferencia")

                    if self.ws:
                        await self.ws.send(json.dumps({
                            "type": "voice_command",
                            "text": user_text
                        }))
                    else:
                        ui_bridge.subtitle_changed.emit("status", "Servidor no conectado temporalmente")
                        self.is_processing_voice = False
                else:
                    if audio_pipeline.should_suggest_recalibration():
                        ui_bridge.subtitle_changed.emit("status", "Tip: Puedes recalibrar tu micrófono ejecutando 'entrenar_voz.bat'")
                    else:
                        ui_bridge.subtitle_changed.emit("status", "No escuché ninguna orden. Di 'Arey' para intentar de nuevo")
                    ui_bridge.state_changed.emit("idle")
                    self.is_processing_voice = False

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Crear y mostrar la cápsula Glassmorphic flotante
    capsule = FloatingAreyCapsule()
    capsule.show()

    # Iniciar cliente de red y audio en un hilo asíncrono
    client = AreyPCClient()
    client_thread = threading.Thread(
        target=lambda: asyncio.run(client.start()),
        daemon=True
    )
    client_thread.start()

    logger.info("✨ Arey 2.0 iniciado con éxito con interfaz Glassmorphism.")
    sys.exit(app.exec())
