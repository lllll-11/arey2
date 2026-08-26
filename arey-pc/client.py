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
        ES_CONTINUOUS = 0x80000000
        ES_SYSTEM_REQUIRED = 0x00000001
        ES_AWAYMODE_REQUIRED = 0x00000040
        ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_AWAYMODE_REQUIRED)
        ctypes.windll.winmm.timeBeginPeriod(1)
        logger.info("⚡ Temporizador multimedia de Windows calibrado a 1ms (60 FPS fluidos).")
    except Exception as e:
        logger.debug(f"Optimizador de tiempo Windows: {e}")

_single_instance_socket = None

def ensure_single_instance():
    """Garantiza mediante un puerto de socket local que no haya dos clientes abiertos a la vez."""
    global _single_instance_socket
    import socket
    try:
        _single_instance_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        _single_instance_socket.bind(('127.0.0.1', 58731))
    except socket.error:
        print("⚠️ Arey ya está abierta y ejecutándose en tu pantalla.")
        sys.exit(0)

class AreyPCClient:
    """
    Cliente Autónomo Local de Laptop Arey 2.1:
    - Modo de Escucha Continua con Compuerta Anti-Música (Filtra canciones de fondo).
    - Conversación y Razonamiento 100% DIRECTO en la laptop con Gemini 3.6 Flash.
    - Fast-Path < 10ms y respuestas de IA en sub-segundo (~350ms).
    """
    def __init__(self):
        ensure_single_instance()
        optimize_windows_environment()
        self.ws = None
        self.running = True
        self.is_processing_voice = False
        self.is_music_active = False
        self.force_wake_event = threading.Event()
        set_ws_client_reference(self)

        # Escuchar cambios de estado musical para ajustar compuerta de ruido
        ui_bridge.music_changed.connect(self._on_music_state_changed)

    def _on_music_state_changed(self, active: bool, title: str, artist: str):
        self.is_music_active = active
        if active:
            logger.info("🎵 Modo Música Detectado: Elevando compuerta de ruido para ignorar la letra de la canción.")

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
        await local_memory.init_db()

        # Iniciar bucle de escucha continua autónomo local
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
        Bucle de voz CONTINUO con filtro anti-música:
        Micrófono siempre activo -> Detección de voz directa -> Fast-Path o Gemini Brain -> Voz.
        """
        loop = asyncio.get_running_loop()
        logger.info("🎙️ MODO DE ESCUCHA CONTINUA ACTIVO: Habla libremente cuando quieras.")

        while self.running:
            ui_bridge.emit_state("musica" if self.is_music_active else "listening")
            self.is_processing_voice = False

            # Captura con umbral adaptativo (filtra canciones de fondo)
            user_text = await loop.run_in_executor(
                executor, 
                lambda: audio_pipeline.listen_command(
                    timeout=3.0, 
                    phrase_time_limit=12.0,
                    is_music_active=self.is_music_active
                )
            )

            if user_text and user_text.strip():
                clean = user_text.strip()
                # Filtrar ruidos accidentales de 1-2 caracteres
                if len(clean) < 3:
                    continue

                # Si el usuario dijo 'arey qué hora es', limpiar prefijos
                for prefix in ["arey", "oye arey", "hey arey", "ari", "araí", "haré"]:
                    if clean.lower().startswith(prefix):
                        clean = clean[len(prefix):].strip(" ,.:;!?")
                        break

                if not clean:
                    continue

                perf_tracker.start_pipeline()
                self.is_processing_voice = True
                logger.info(f"🗣️ Andriy: '{clean}'")
                ui_bridge.emit_subtitle("user", clean)

                # 1. FAST-PATH LOCAL (< 10ms para volumen, apps, media, atajos)
                perf_tracker.start_stage("Fast-Path Router")
                local_match = local_fast_path.try_execute_local(clean)
                perf_tracker.end_stage("Fast-Path Router")

                if local_match:
                    action_name, reply_text = local_match
                    logger.info(f"⚡ FAST-PATH EJECUTADO: '{action_name}'")
                    ui_bridge.emit_state("speaking")
                    ui_bridge.emit_subtitle("arey", reply_text)
                    await audio_pipeline.speak(reply_text)
                    perf_tracker.print_summary(clean)
                    continue

                # 2. CEREBRO LOCAL: Inferencia directa de Gemini 3.6 Flash (~350ms)
                ui_bridge.emit_state("thinking")
                perf_tracker.start_stage("Gemini API Local")

                reply_text = await local_brain.process_user_message(clean)
                perf_tracker.end_stage("Gemini API Local")

                logger.info(f"🧠 Arey: '{reply_text}'")
                ui_bridge.emit_state("speaking")
                ui_bridge.emit_subtitle("arey", reply_text)
                await audio_pipeline.speak(reply_text)
                perf_tracker.print_summary(clean)

if __name__ == "__main__":
    try:
        client = AreyPCClient()
        client_thread = threading.Thread(
            target=lambda: asyncio.run(client.start()),
            daemon=True
        )
        client_thread.start()

        logger.info("✨ Arey 2.1 iniciada en Modo de Escucha Continua con Filtro Anti-Música.")
        start_floating_ui(
            on_wake_callback=client.force_wake,
            on_media_callback=lambda act: pc_controller.control_media(act)
        )
        sys.exit(0)
    except Exception as e:
        import traceback
        traceback.print_exc()
        sys.exit(1)
