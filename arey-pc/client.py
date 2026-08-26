import sys
import os
import threading
import asyncio
import json
import logging
import websockets
from concurrent.futures import ThreadPoolExecutor

from config import SERVER_WS_URL, DEVICE_AUTH_TOKEN
from pc_controller import pc_controller
from audio_pipeline import audio_pipeline
from network_scanner import network_scanner
from tv_controller import tv_controller
from floating_ui import start_floating_ui, ui_bridge
from local_fast_path import local_fast_path
from performance_tracker import perf_tracker

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] AreyPC: %(message)s")
logger = logging.getLogger("AreyPCClient")

executor = ThreadPoolExecutor(max_workers=4)

class AreyPCClient:
    """
    Cliente Central de Laptop Arey 2.1:
    Coordina la interfaz Glassmorphism HTML5 ultra-minimalista,
    el pipeline de audio, el control de Windows y la sincronización en la nube.
    """
    def __init__(self):
        self.ws = None
        self.running = True
        self.is_processing_voice = False
        self.force_wake_event = threading.Event()

    def force_wake(self):
        """Activación manual por clic en la esfera o atajo Alt+Espacio."""
        logger.info("⚡ Activación manual de voz activada.")
        self.force_wake_event.set()

    async def start(self):
        """
        Bucle principal de conexión y escucha WebSocket hacia el Servidor Cloud.
        """
        voice_task = asyncio.create_task(self._voice_loop())

        while self.running:
            try:
                logger.info(f"Conectando al servidor Arey Cloud en {SERVER_WS_URL}...")
                async with websockets.connect(
                    f"{SERVER_WS_URL}?token={DEVICE_AUTH_TOKEN}"
                ) as ws:
                    self.ws = ws
                    logger.info("✅ Conectado exitosamente con el Cerebro Central de Arey.")
                    ui_bridge.emit_subtitle("status", "Conectado al Cerebro Central • Listo")

                    # Enviar telemetría inicial
                    await self.ws.send(json.dumps({
                        "type": "status_update",
                        "status": pc_controller.get_system_stats()
                    }))

                    # Escuchar mensajes del servidor
                    await self._listen_server_messages()

            except (websockets.ConnectionClosed, ConnectionRefusedError, OSError) as e:
                logger.warning(f"Conexión perdida con el servidor ({e}). Reintentando en 3s...")
                self.ws = None
                ui_bridge.emit_subtitle("status", "Reconectando con el Servidor...")
                await asyncio.sleep(3)
            except Exception as e:
                logger.error(f"Error inesperado en cliente: {e}", exc_info=True)
                await asyncio.sleep(3)

    async def _listen_server_messages(self):
        while self.running and self.ws:
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

                if action in ["scan_network", "capture_screen"]:
                    ui_bridge.emit_state("analyzing")
                else:
                    ui_bridge.emit_state("working")

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
                    ui_bridge.emit_state("speaking")
                    ui_bridge.emit_subtitle("arey", reply_text)
                    await audio_pipeline.speak(reply_text)
                    ui_bridge.emit_state("idle")
                    self.is_processing_voice = False
                    perf_tracker.print_summary(reply_text)

            # 3. Telemetría de dispositivos (Celular, Smart TV)
            elif msg_type == "devices_update":
                devices = data.get("devices", {})
                android = devices.get("android", {})
                phone_batt = android.get("status", {}).get("battery")
                phone_online = android.get("online", False)
                ui_bridge.emit_devices(phone_online, phone_batt, True)

            # 4. Recordatorios / Alarmas
            elif msg_type == "event" and data.get("event") == "reminder_alert":
                rem_msg = data.get("data", {}).get("message", "Tienes un recordatorio pendiente.")
                ui_bridge.emit_state("speaking")
                ui_bridge.emit_subtitle("arey", f"Recordatorio: {rem_msg}")
                await audio_pipeline.speak(f"Atención: {rem_msg}")
                ui_bridge.emit_state("idle")

    async def _execute_action(self, action: str, params: dict) -> dict:
        """
        Ejecuta acciones en el sistema Windows y Smart TV.
        """
        if action == "set_volume":
            return pc_controller.set_volume(params.get("level_percent", 50))
        elif action == "open_app":
            return pc_controller.open_app(params.get("app_name", ""))
        elif action == "control_media":
            cmd = params.get("action", "play_pause")
            if cmd in ["pause", "stop"]:
                ui_bridge.emit_music(False)
            return pc_controller.control_media(cmd)
        elif action == "play_music":
            q = params.get("query", "Spotify")
            p = params.get("platform", "spotify")
            ui_bridge.emit_music(True, q, f"Reproduciendo en {p.capitalize()}")
            return pc_controller.play_music(q, p)
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
                ui_bridge.emit_state("idle")

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
                ui_bridge.emit_state("listening")
                ui_bridge.emit_subtitle("status", "Escuchando... Habla ahora")
                audio_pipeline.play_instant_wake()

                # 2. Escuchar la orden con Whisper Small (int8) + Silero VAD
                user_text = await loop.run_in_executor(executor, audio_pipeline.listen_command)

                if user_text and user_text.strip():
                    logger.info(f"🗣️ Orden recibida: '{user_text}'")
                    ui_bridge.emit_subtitle("user", user_text)

                    # 3. FAST-PATH LOCAL: ¿Es un comando determinista de PC? (< 10ms)
                    perf_tracker.start_stage("Fast-Path Router")
                    local_match = local_fast_path.try_execute_local(user_text)
                    perf_tracker.end_stage("Fast-Path Router")

                    if local_match:
                        action_name, reply_text = local_match
                        logger.info(f"⚡ FAST-PATH LOCAL EJECUTADO: '{action_name}'")
                        ui_bridge.emit_state("speaking")
                        ui_bridge.emit_subtitle("arey", reply_text)
                        await audio_pipeline.speak(reply_text)
                        ui_bridge.emit_state("idle")
                        self.is_processing_voice = False
                        perf_tracker.print_summary(user_text)
                        continue

                    # 4. Si requiere razonamiento / IA, enviar al servidor Cloud
                    ui_bridge.emit_state("thinking")
                    perf_tracker.start_stage("Red / Cloud Inferencia")

                    if self.ws:
                        await self.ws.send(json.dumps({
                            "type": "voice_command",
                            "text": user_text
                        }))
                    else:
                        ui_bridge.emit_subtitle("status", "Servidor no conectado temporalmente")
                        self.is_processing_voice = False
                else:
                    if audio_pipeline.should_suggest_recalibration():
                        ui_bridge.emit_subtitle("status", "Tip: Puedes recalibrar tu micrófono ejecutando 'entrenar_voz.bat'")
                    else:
                        ui_bridge.emit_subtitle("status", "No escuché ninguna orden. Di 'Arey' para intentar de nuevo")
                    ui_bridge.emit_state("idle")
                    self.is_processing_voice = False

if __name__ == "__main__":
    client = AreyPCClient()
    client_thread = threading.Thread(
        target=lambda: asyncio.run(client.start()),
        daemon=True
    )
    client_thread.start()

    logger.info("✨ Arey 2.1 iniciado con interfaz ultra-minimalista Livi DJ.")
    start_floating_ui(
        on_wake_callback=client.force_wake,
        on_media_callback=lambda act: pc_controller.control_media(act)
    )
