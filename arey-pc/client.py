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
from local_brain import local_brain
from local_memory import local_memory
from local_tools import set_ws_client_reference
from performance_tracker import perf_tracker

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] AreyPC: %(message)s")
logger = logging.getLogger("AreyPCClient")

executor = ThreadPoolExecutor(max_workers=4)

def optimize_windows_environment():
    """
    Eleva la prioridad del proceso a ALTA (High Priority Class) y configura
    los accesos de hardware para audio en tiempo real y anti-suspensión.
    """
    try:
        import psutil
        p = psutil.Process(os.getpid())
        p.nice(psutil.HIGH_PRIORITY_CLASS)
        logger.info("🚀 Prioridad del proceso elevada a ALTA (High Priority Class).")
    except Exception as e:
        logger.debug(f"No se pudo elevar prioridad del proceso: {e}")

    try:
        import ctypes
        # Evitar que Windows ponga en suspensión o throttling el hilo de audio
        ES_CONTINUOUS = 0x80000000
        ES_SYSTEM_REQUIRED = 0x00000001
        ES_AWAYMODE_REQUIRED = 0x00000040
        ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_AWAYMODE_REQUIRED)

        # Aumentar precisión del reloj de Windows a 1ms para 60 FPS ultra fluidos
        ctypes.windll.winmm.timeBeginPeriod(1)
        logger.info("⚡ Temporizador multimedia de Windows calibrado a 1ms (60 FPS fluidos).")
    except Exception as e:
        logger.debug(f"Optimizador de tiempo Windows: {e}")

class AreyPCClient:
    """
    Cliente Autónomo Local de Laptop Arey 2.1:
    - Conversación y Razonamiento 100% DIRECTO en la laptop con Gemini API y Whisper Small.
    - Cero dependencia de Render para hablar, pensar o ejecutar acciones de PC y Smart TV.
    - Puente WebSocket secundario solo para telemetría y control de celular Android.
    """
    def __init__(self):
        optimize_windows_environment()
        self.ws = None
        self.running = True
        self.is_processing_voice = False
        self.force_wake_event = threading.Event()
        set_ws_client_reference(self)

    def force_wake(self):
        """Activación manual por clic en la esfera o atajo Alt+Espacio."""
        logger.info("⚡ Activación manual de voz activada.")
        self.force_wake_event.set()

    async def send_remote_command(self, device_type: str, action: str, params: dict) -> dict:
        """Envía un comando remoto al celular a través del broker de la nube si está conectado."""
        if not self.ws:
            return {"status": "error", "message": "Celular desconectado del servidor."}
        try:
            await self.ws.send(json.dumps({
                "type": "remote_device_command",
                "target_device": device_type,
                "action": action,
                "params": params
            }))
            return {"status": "success", "message": f"Comando '{action}' enviado a tu {device_type}."}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def start(self):
        """
        Bucle de conexión en segundo plano hacia Render (solo para enlace con Celular y telemetría).
        """
        # Inicializar base de datos de memoria local
        await local_memory.init_db()

        # Iniciar bucle de escucha de voz autónomo local
        asyncio.create_task(self._voice_loop())

        # Conexión opcional a la nube para telemetría
        while self.running:
            try:
                logger.info(f"Sincronizando con puente de nube en {SERVER_WS_URL}...")
                async with websockets.connect(
                    f"{SERVER_WS_URL}?token={DEVICE_AUTH_TOKEN}"
                ) as ws:
                    self.ws = ws
                    logger.info("☁️ Puente con la nube conectado (Celular & Telemetría sincronizados).")

                    # Enviar telemetría inicial
                    await self.ws.send(json.dumps({
                        "type": "status_update",
                        "status": pc_controller.get_system_stats()
                    }))

                    # Escuchar telemetría del celular
                    await self._listen_cloud_telemetry()

            except (websockets.ConnectionClosed, ConnectionRefusedError, OSError):
                self.ws = None
                await asyncio.sleep(5)
            except Exception as e:
                logger.debug(f"Error en puente de nube: {e}")
                self.ws = None
                await asyncio.sleep(5)

    async def _listen_cloud_telemetry(self):
        while self.running and self.ws:
            try:
                message_raw = await self.ws.recv()
                data = json.loads(message_raw)
                msg_type = data.get("type")

                # Telemetría de celular
                if msg_type == "devices_update":
                    devices = data.get("devices", {})
                    android = devices.get("android", {})
                    phone_batt = android.get("status", {}).get("battery")
                    phone_online = android.get("online", False)
                    ui_bridge.emit_devices(phone_online, phone_batt, True)

            except Exception:
                break

    async def _voice_loop(self):
        """
        Bucle de voz 100% LOCAL:
        Micrófono -> Whisper Small local -> Fast-Path o Local Gemini Brain -> Edge-TTS local.
        Latencia total: ~400-600ms para IA, < 10ms para comandos de PC.
        """
        loop = asyncio.get_running_loop()
        while self.running:
            if not self.is_processing_voice:
                ui_bridge.emit_state("idle")

            # 1. Comprobar si se activó por atajo o escuchar en vivo
            is_manual = self.force_wake_event.is_set()
            if is_manual:
                self.force_wake_event.clear()
                detected, direct_cmd = True, ""
            else:
                detected, direct_cmd = await loop.run_in_executor(executor, audio_pipeline.listen_for_wake_word)

            if detected:
                perf_tracker.start_pipeline()
                self.is_processing_voice = True
                ui_bridge.emit_state("listening")

                # 2. Si el usuario dijo la orden completa de un solo golpe, ejecutar de inmediato
                if direct_cmd and len(direct_cmd.strip()) > 1:
                    user_text = direct_cmd
                    logger.info(f"⚡ COMANDO EN UN SOLO ALIENTO DETECTADO: '{user_text}'")
                else:
                    ui_bridge.emit_subtitle("status", "Escuchando... Habla ahora")
                    audio_pipeline.play_instant_wake()
                    user_text = await loop.run_in_executor(executor, audio_pipeline.listen_command)

                if user_text and user_text.strip():
                    logger.info(f"🗣️ Andriy: '{user_text}'")
                    ui_bridge.emit_subtitle("user", user_text)

                    # 3. FAST-PATH LOCAL (< 10ms para volumen, apps, media, atajos)
                    perf_tracker.start_stage("Fast-Path Router")
                    local_match = local_fast_path.try_execute_local(user_text)
                    perf_tracker.end_stage("Fast-Path Router")

                    if local_match:
                        action_name, reply_text = local_match
                        logger.info(f"⚡ FAST-PATH EJECUTADO: '{action_name}'")
                        ui_bridge.emit_state("speaking")
                        ui_bridge.emit_subtitle("arey", reply_text)
                        await audio_pipeline.speak(reply_text)
                        ui_bridge.emit_state("idle")
                        self.is_processing_voice = False
                        perf_tracker.print_summary(user_text)
                        continue

                    # 4. CEREBRO LOCAL: Inferencia directa de Gemini API en la Laptop (~350ms)
                    ui_bridge.emit_state("thinking")
                    perf_tracker.start_stage("Gemini API Local")

                    reply_text = await local_brain.process_user_message(user_text)
                    perf_tracker.end_stage("Gemini API Local")

                    logger.info(f"🧠 Arey: '{reply_text}'")
                    ui_bridge.emit_state("speaking")
                    ui_bridge.emit_subtitle("arey", reply_text)
                    await audio_pipeline.speak(reply_text)

                    ui_bridge.emit_state("idle")
                    self.is_processing_voice = False
                    perf_tracker.print_summary(user_text)

                else:
                    if audio_pipeline.should_suggest_recalibration():
                        ui_bridge.emit_subtitle("status", "Tip: Calibra tu micrófono con 'entrenar_voz.bat'")
                    else:
                        ui_bridge.emit_subtitle("status", "No escuché ninguna orden. Di 'Arey'")
                    ui_bridge.emit_state("idle")
                    self.is_processing_voice = False

if __name__ == "__main__":
    client = AreyPCClient()
    client_thread = threading.Thread(
        target=lambda: asyncio.run(client.start()),
        daemon=True
    )
    client_thread.start()

    logger.info("✨ Arey 2.1 iniciada en Modo Autónomo Local (Cero Latencia de Nube).")
    start_floating_ui(
        on_wake_callback=client.force_wake,
        on_media_callback=lambda act: pc_controller.control_media(act)
    )
