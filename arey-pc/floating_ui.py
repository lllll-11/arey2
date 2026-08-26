import os
import sys
import math
import json
import logging
import threading
from typing import Dict, Any, List

from PyQt6.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout, QHBoxLayout, QPushButton
from PyQt6.QtCore import Qt, QTimer, QPoint, QPointF, pyqtSignal, QObject
from PyQt6.QtGui import (
    QPainter, QRadialGradient, QColor, QPainterPath, QPen, QBrush, 
    QFont, QCursor, QPainterPathStroker
)
import keyboard

logger = logging.getLogger("AreyFloatingUI")

# ==================== PALETA DE 5 MODOS CON COLORES DE AURA ====================
MODES_CONFIG = {
    "escuchando": {
        "title": "Escuchando...",
        "colors": [QColor("#00f2fe"), QColor("#4facfe"), QColor("#0066ff"), QColor("#00c6ff")],
        "aura": QColor(0, 242, 254, 160),
        "speed": 0.055,
        "reactivity": 0.42,
        "base_radius": 56,
        "freq1": 3, "freq2": 5, "freq3": 7
    },
    "pensando": {
        "title": "Pensando...",
        "colors": [QColor("#a855f7"), QColor("#7c3aed"), QColor("#6366f1"), QColor("#c084fc")],
        "aura": QColor(168, 85, 247, 160),
        "speed": 0.09,
        "reactivity": 0.22,
        "base_radius": 52,
        "freq1": 4, "freq2": 6, "freq3": 9
    },
    "trabajando": {
        "title": "Trabajando...",
        "colors": [QColor("#f59e0b"), QColor("#d97706"), QColor("#f97316"), QColor("#fbbf24")],
        "aura": QColor(245, 158, 11, 160),
        "speed": 0.04,
        "reactivity": 0.14,
        "base_radius": 58,
        "freq1": 2, "freq2": 4, "freq3": 6
    },
    "analizando": {
        "title": "Analizando...",
        "colors": [QColor("#10b981"), QColor("#059669"), QColor("#06b6d4"), QColor("#34d399")],
        "aura": QColor(16, 185, 129, 160),
        "speed": 0.075,
        "reactivity": 0.28,
        "base_radius": 54,
        "freq1": 5, "freq2": 8, "freq3": 12
    },
    "hablando": {
        "title": "Hablando...",
        "colors": [QColor("#ec4899"), QColor("#f43f5e"), QColor("#fb7185"), QColor("#e11d48")],
        "aura": QColor(236, 72, 153, 170),
        "speed": 0.065,
        "reactivity": 0.52,
        "base_radius": 60,
        "freq1": 3, "freq2": 5, "freq3": 8
    },
    "musica": {
        "title": "Reproduciendo Música...",
        "colors": [QColor("#1ed760"), QColor("#1db954"), QColor("#00d2ff"), QColor("#10b981")],
        "aura": QColor(30, 215, 96, 160),
        "speed": 0.08,
        "reactivity": 0.46,
        "base_radius": 58,
        "freq1": 4, "freq2": 7, "freq3": 10
    }
}

def lerp_color(c1: QColor, c2: QColor, factor: float) -> QColor:
    r = int(c1.red() + factor * (c2.red() - c1.red()))
    g = int(c1.green() + factor * (c2.green() - c1.green()))
    b = int(c1.blue() + factor * (c2.blue() - c1.blue()))
    a = int(c1.alpha() + factor * (c2.alpha() - c1.alpha()))
    return QColor(r, g, b, a)

class UIBridge(QObject):
    state_changed = pyqtSignal(str)
    subtitle_changed = pyqtSignal(str, str)
    device_status_changed = pyqtSignal(dict)
    music_changed = pyqtSignal(bool, str, str)

    def emit_state(self, mode: str):
        self.state_changed.emit(mode)

    def emit_subtitle(self, speaker: str, text: str):
        self.subtitle_changed.emit(speaker, text)

    def emit_action(self, action_text: str):
        self.subtitle_changed.emit("action", action_text)

    def emit_devices(self, phone_online: bool, phone_batt: int, tv_online: bool = True):
        self.device_status_changed.emit({
            "phone_online": phone_online,
            "phone_battery": phone_batt,
            "tv_online": tv_online
        })

    def emit_music(self, active: bool, title: str = "Spotify Music", artist: str = "Reproduciendo"):
        self.music_changed.emit(active, title, artist)

ui_bridge = UIBridge()

class FloatingLiquidOrb(QWidget):
    """
    Orbe líquido ultra-minimalista 100% transparente con física fluida continua a 60 FPS,
    auras dinámicas interpoladas y cero cajas rectangulares.
    """
    def __init__(self, on_wake_callback=None, on_media_callback=None):
        super().__init__()
        self.on_wake_callback = on_wake_callback
        self.on_media_callback = on_media_callback

        # 1. Configuración de ventana 100% transparente en Windows DWM
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.SubWindow
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)

        self.setFixedSize(280, 340)

        # Posicionar en la esquina inferior derecha
        screen = QApplication.primaryScreen().geometry()
        self.move(screen.width() - 320, screen.height() - 390)

        # Estado del Orbe
        self.current_mode_key = "escuchando"
        self.time_val = 0.0
        self.current_colors = [QColor(c) for c in MODES_CONFIG["escuchando"]["colors"]]
        self.current_aura = QColor(MODES_CONFIG["escuchando"]["aura"])

        # Subtítulos y estado
        self.subtitle_speaker = ""
        self.subtitle_text = "Di \"Arey\" o presiona Alt + Espacio"
        self.subtitle_opacity = 1.0
        self.is_music_active = False
        self.music_title = "Spotify Music"
        self.music_artist = "Reproduciendo"

        # Arrastre de ventana
        self.drag_position = QPoint()

        # Timer de animación a 60 FPS
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self._on_animation_frame)
        self.anim_timer.start(16) # ~60 FPS

        # Conectar señales del bridge
        ui_bridge.state_changed.connect(self.set_mode)
        ui_bridge.subtitle_changed.connect(self.set_subtitle)
        ui_bridge.music_changed.connect(self.set_music)

        # Atajo global Alt + Espacio
        try:
            keyboard.add_hotkey("alt+space", self._on_hotkey)
        except Exception as e:
            logger.debug(f"Error registrando hotkey: {e}")

    def _on_hotkey(self):
        if self.on_wake_callback:
            self.on_wake_callback()

    def set_mode(self, mode_str: str):
        mapped = mode_str.lower()
        if mapped in ["listening", "idle"]:
            target = "escuchando"
        elif mapped == "thinking":
            target = "pensando"
        elif mapped == "working":
            target = "trabajando"
        elif mapped == "analyzing":
            target = "analizando"
        elif mapped == "speaking":
            target = "hablando"
        elif mapped == "music":
            target = "musica"
        else:
            target = "escuchando"

        self.current_mode_key = target
        self.subtitle_opacity = 1.0

    def set_subtitle(self, speaker: str, text: str):
        self.subtitle_speaker = speaker
        self.subtitle_text = text if text else "Di \"Arey\" o presiona Alt + Espacio"
        self.subtitle_opacity = 1.0
        self.update()

    def set_music(self, active: bool, title: str = "Spotify Music", artist: str = "Reproduciendo"):
        self.is_music_active = active
        self.music_title = title
        self.music_artist = artist
        if active:
            self.set_mode("musica")
        else:
            if self.current_mode_key == "musica":
                self.set_mode("escuchando")
        self.update()

    def _on_animation_frame(self):
        cfg = MODES_CONFIG.get(self.current_mode_key, MODES_CONFIG["escuchando"])
        self.time_val += cfg["speed"]

        # Interpolación suave de color (0.08 por frame)
        for i in range(4):
            self.current_colors[i] = lerp_color(self.current_colors[i], cfg["colors"][i], 0.08)
        self.current_aura = lerp_color(self.current_aura, cfg["aura"], 0.08)

        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()

    def mouseReleaseEvent(self, event):
        # Si fue un clic simple sin arrastre, activar Arey
        if event.button() == Qt.MouseButton.LeftButton:
            if self.on_wake_callback:
                self.on_wake_callback()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        width = self.width()
        center_x = width / 2.0
        center_y = 120.0

        cfg = MODES_CONFIG.get(self.current_mode_key, MODES_CONFIG["escuchando"])

        # 1. DIBUJAR AURA DIFUMINADA RESPLANDECIENTE (100% transparente en los bordes)
        aura_radius = cfg["base_radius"] + 42.0
        aura_grad = QRadialGradient(QPointF(center_x, center_y), aura_radius)
        aura_grad.setColorAt(0.0, QColor(self.current_aura.red(), self.current_aura.green(), self.current_aura.blue(), 140))
        aura_grad.setColorAt(0.5, QColor(self.current_aura.red(), self.current_aura.green(), self.current_aura.blue(), 60))
        aura_grad.setColorAt(0.85, QColor(self.current_aura.red(), self.current_aura.green(), self.current_aura.blue(), 15))
        aura_grad.setColorAt(1.0, QColor(0, 0, 0, 0)) # Borde completamente transparente

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(aura_grad))
        painter.drawEllipse(QPointF(center_x, center_y), aura_radius, aura_radius)

        # 2. DIBUJAR ESFERA LÍQUIDA ORGÁNICA (FÍSICA FLUIDA 120 PUNTOS)
        dynamic_react = math.sin(self.time_val * 6.0) * cfg["reactivity"] + (cfg["reactivity"] * 0.5)
        base_radius = cfg["base_radius"] + (dynamic_react * 10.0)
        points = 120

        orb_path = QPainterPath()

        for i in range(points + 1):
            angle = (i / float(points)) * math.pi * 2.0
            wave1 = math.sin(angle * cfg["freq1"] + self.time_val * 2.0) * (6.0 + dynamic_react * 14.0)
            wave2 = math.cos(angle * cfg["freq2"] - self.time_val * 1.5) * (4.0 + dynamic_react * 10.0)
            wave3 = math.sin(angle * cfg["freq3"] + self.time_val * 3.0) * 2.5

            r = base_radius + wave1 + wave2 + wave3
            x = center_x + math.cos(angle) * r
            y = center_y + math.sin(angle) * r

            if i == 0:
                orb_path.moveTo(x, y)
            else:
                orb_path.lineTo(x, y)

        orb_path.closeSubpath()

        # Gradiente radial de líquido interno
        grad_center_x = center_x + math.sin(self.time_val) * 14.0
        grad_center_y = center_y + math.cos(self.time_val) * 14.0
        orb_grad = QRadialGradient(QPointF(grad_center_x, grad_center_y), base_radius + 26.0)
        orb_grad.setColorAt(0.0, self.current_colors[0])
        orb_grad.setColorAt(0.35, self.current_colors[1])
        orb_grad.setColorAt(0.7, self.current_colors[2])
        orb_grad.setColorAt(1.0, self.current_colors[3])

        painter.setBrush(QBrush(orb_grad))
        painter.drawPath(orb_path)

        # 3. BRILLO ESPECULAR 3D INTERNO
        spec_grad = QRadialGradient(QPointF(center_x - 12.0, center_y - 18.0), base_radius)
        spec_grad.setColorAt(0.0, QColor(255, 255, 255, 175))
        spec_grad.setColorAt(0.35, QColor(255, 255, 255, 38))
        spec_grad.setColorAt(1.0, QColor(255, 255, 255, 0))
        painter.setBrush(QBrush(spec_grad))
        painter.drawPath(orb_path)

        # 4. PARTÍCULAS FLOTANTES DE ENERGÍA
        for p in range(4):
            p_angle = self.time_val * 0.7 + (p * math.pi / 2.0)
            p_dist = base_radius + 12.0 + math.sin(self.time_val * 2.0 + p) * 6.0
            px = center_x + math.cos(p_angle) * p_dist
            py = center_y + math.sin(p_angle) * p_dist
            p_size = 1.8 + math.sin(self.time_val + p) * 0.8
            painter.setBrush(QBrush(QColor(255, 255, 255, 190)))
            painter.drawEllipse(QPointF(px, py), p_size, p_size)

        # 5. PÍLDORA FLOTANTE DE SUBTÍTULOS / ESTADO (GLASSMORPHIC ULTRA-LIGERA)
        pill_y = 230
        pill_height = 30
        pill_width = 250
        pill_x = int(center_x - pill_width / 2.0)

        pill_path = QPainterPath()
        pill_path.addRoundedRect(float(pill_x), float(pill_y), float(pill_width), float(pill_height), 15.0, 15.0)

        # Fondo glass negro translúcido
        painter.setBrush(QBrush(QColor(10, 12, 18, 185)))
        painter.setPen(QPen(QColor(255, 255, 255, 35), 1))
        painter.drawPath(pill_path)

        # Punto de modo
        dot_color = self.current_colors[0]
        painter.setBrush(QBrush(dot_color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(pill_x + 14, pill_y + 15), 3.5, 3.5)

        # Texto de estado
        painter.setPen(QPen(QColor(240, 240, 245, 235)))
        font = QFont("Outfit", 9, QFont.Weight.DemiBold)
        painter.setFont(font)

        display_text = self.subtitle_text
        if len(display_text) > 34:
            display_text = display_text[:32] + "..."

        painter.drawText(
            pill_x + 24, pill_y, pill_width - 32, pill_height,
            int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft),
            display_text
        )

        # 6. REPRODUCTOR CONDICIONAL (SOLO SI HAY MÚSICA)
        if self.is_music_active:
            m_y = 270
            m_h = 48
            m_w = 230
            m_x = int(center_x - m_w / 2.0)

            m_path = QPainterPath()
            m_path.addRoundedRect(float(m_x), float(m_y), float(m_w), float(m_h), 14.0, 14.0)

            painter.setBrush(QBrush(QColor(12, 14, 20, 190)))
            painter.setPen(QPen(QColor(30, 215, 96, 60), 1))
            painter.drawPath(m_path)

            # Icono disco de vinilo verde
            painter.setBrush(QBrush(QColor(30, 215, 96, 220)))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPointF(m_x + 18, m_y + 24), 8.0, 8.0)
            painter.setBrush(QBrush(QColor(0, 0, 0)))
            painter.drawEllipse(QPointF(m_x + 18, m_y + 24), 2.5, 2.5)

            # Título de música
            painter.setPen(QPen(QColor(255, 255, 255)))
            m_font = QFont("Outfit", 8, QFont.Weight.Bold)
            painter.setFont(m_font)
            painter.drawText(m_x + 34, m_y + 8, m_w - 40, 16, int(Qt.AlignmentFlag.AlignLeft), self.music_title[:20])

            painter.setPen(QPen(QColor(30, 215, 96)))
            m_subfont = QFont("Outfit", 7, QFont.Weight.Medium)
            painter.setFont(m_subfont)
            painter.drawText(m_x + 34, m_y + 26, m_w - 40, 14, int(Qt.AlignmentFlag.AlignLeft), "En reproducción en PC")

def start_floating_ui(on_wake_callback=None, on_media_callback=None):
    """
    Inicia la aplicación de escritorio PyQt6 con el orbe líquido 100% transparente.
    """
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)

    orb = FloatingLiquidOrb(on_wake_callback=on_wake_callback, on_media_callback=on_media_callback)
    orb.show()

    app.exec()

if __name__ == "__main__":
    start_floating_ui()
