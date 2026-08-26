import os
import sys
import json
import logging
import threading
import asyncio
import webview
import keyboard

logger = logging.getLogger("AreyFloatingUI")
HTML_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "asistente_ui.html"))

class SignalCompat:
    def __init__(self, callback):
        self.callback = callback

    def emit(self, *args, **kwargs):
        try:
            self.callback(*args, **kwargs)
        except Exception as e:
            logger.debug(f"Error emitiendo senal UI: {e}")

class UIBridge:
    """
    Puente de comunicación bidireccional entre Python y la interfaz Web/HTML5.
    Soporta tanto llamadas directas como compatibilidad PyQt .emit()
    """
    def __init__(self):
        self.window = None
        self.on_wake_requested = None
        self.on_media_control = None

        # Señales compatibles con PyQt
        self.state_changed = SignalCompat(self.emit_state)
        self.subtitle_changed = SignalCompat(self.emit_subtitle)
        self.device_status_changed = SignalCompat(self._handle_device_status_dict)
        self.music_changed = SignalCompat(self.emit_music)

    def set_window(self, window):
        self.window = window

    def emit_state(self, mode: str):
        if self.window:
            try:
                self.window.evaluate_js(f"setMode('{mode}')")
            except Exception as e:
                logger.debug(f"Error evaluando state en UI: {e}")

    def emit_subtitle(self, speaker: str, text: str):
        if self.window:
            try:
                clean_text = json.dumps(text)
                self.window.evaluate_js(f"setSubtitle('{speaker}', {clean_text})")
            except Exception as e:
                logger.debug(f"Error evaluando subtitle en UI: {e}")

    def emit_devices(self, phone_online: bool, phone_batt: int, tv_online: bool = True):
        if self.window:
            try:
                self.window.evaluate_js(f"updateDevices({str(phone_online).lower()}, {phone_batt or 0}, {str(tv_online).lower()})")
            except Exception as e:
                logger.debug(f"Error evaluando devices en UI: {e}")

    def _handle_device_status_dict(self, data: dict):
        phone_batt = data.get("phone_battery")
        phone_online = data.get("phone_online", False)
        tv_online = data.get("tv_online", True)
        self.emit_devices(phone_online, phone_batt, tv_online)

    def emit_music(self, active: bool, title: str = "Spotify Music", artist: str = "Reproduciendo en PC"):
        if self.window:
            try:
                clean_title = json.dumps(title)
                clean_artist = json.dumps(artist)
                self.window.evaluate_js(f"updateMusicPlayer({str(active).lower()}, {clean_title}, {clean_artist})")
            except Exception as e:
                logger.debug(f"Error evaluando music en UI: {e}")

class JsApi:
    def __init__(self, bridge: UIBridge):
        self.bridge = bridge

    def on_orb_clicked(self):
        logger.info("🖱️ Orbe presionado por el usuario en la interfaz.")
        if self.bridge.on_wake_requested:
            self.bridge.on_wake_requested()

    def control_media(self, action: str):
        logger.info(f"🎵 Control multimedia desde la UI: {action}")
        if self.bridge.on_media_control:
            self.bridge.on_media_control(action)
        else:
            try:
                from pc_controller import pc_controller
                if action == "play_pause":
                    pc_controller.control_media("play_pause")
                elif action == "next":
                    pc_controller.control_media("next")
                elif action == "prev":
                    pc_controller.control_media("prev")
            except Exception as e:
                logger.debug(f"Error controlando media: {e}")

    def close_window(self):
        if self.bridge.window:
            self.bridge.window.destroy()

ui_bridge = UIBridge()

def start_floating_ui(on_wake_callback=None, on_media_callback=None):
    """
    Inicia la cápsula flotante Glassmorphic con WebKit/WebView2 nativo acelerado por GPU.
    """
    ui_bridge.on_wake_requested = on_wake_callback
    ui_bridge.on_media_control = on_media_callback

    js_api = JsApi(ui_bridge)

    # Atajo global Alt + Espacio
    try:
        def on_global_hotkey():
            logger.info("⌨️ Atajo global [Alt + Espacio] presionado.")
            if ui_bridge.on_wake_requested:
                ui_bridge.on_wake_requested()

        keyboard.add_hotkey("alt+space", on_global_hotkey)
    except Exception as e:
        logger.warning(f"No se pudo registrar atajo Alt+Espacio: {e}")

    # Crear ventana transparente sin bordes siempre visible
    window = webview.create_window(
        title="Arey Assistant",
        url=HTML_FILE,
        width=360,
        height=520,
        frameless=True,
        easy_drag=True,
        transparent=True,
        on_top=True,
        js_api=js_api
    )
    ui_bridge.set_window(window)

    webview.start(debug=False)

if __name__ == "__main__":
    start_floating_ui()
