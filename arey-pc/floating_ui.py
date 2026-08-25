import sys
import os
import math
import time
import logging
import keyboard
from PyQt6.QtCore import Qt, QTimer, QPoint, pyqtSignal, QObject, QRectF, QSize

logger = logging.getLogger("FloatingUI")
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QFrame, QGraphicsDropShadowEffect, QMenu
)
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QBrush, QFont, QPainterPath, 
    QLinearGradient, QRadialGradient, QCursor
)

class UIStateBridge(QObject):
    state_changed = pyqtSignal(str) # 'idle', 'listening', 'thinking', 'speaking'
    subtitle_changed = pyqtSignal(str, str) # role ('user', 'arey', 'status'), text
    device_status_changed = pyqtSignal(dict) # {'phone_battery': 10, 'phone_online': True, 'tv_online': True}
    trigger_voice_requested = pyqtSignal()

ui_bridge = UIStateBridge()

class GlassWaveVisualizer(QWidget):
    """
    Visualizador de ondas de sonido orgánicas de alta fidelidad a 60 FPS.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.state = "idle"
        self.tick = 0.0
        self.setFixedSize(110, 65)

    def set_state(self, state: str):
        self.state = state
        self.update()

    def step(self):
        self.tick += 0.06
        if self.tick > 100000:
            self.tick = 0.0
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        w, h = self.width(), self.height()
        mid_y = h / 2.0
        t = self.tick

        # Colores según el estado
        if self.state == "listening":
            base_col = QColor(0, 255, 170)    # Verde esmeralda neón
            glow_col = QColor(0, 200, 255, 60)
            amp_factor = 1.0
            num_bars = 7
        elif self.state == "thinking":
            base_col = QColor(80, 150, 255)   # Azul eléctrico
            glow_col = QColor(140, 80, 255, 60)
            amp_factor = 0.75
            num_bars = 7
        elif self.state == "speaking":
            base_col = QColor(210, 100, 255)  # Morado / Magenta neón
            glow_col = QColor(255, 80, 180, 70)
            amp_factor = 1.15
            num_bars = 7
        else: # 'idle'
            base_col = QColor(100, 120, 180)  # Azul grisáceo sutil
            glow_col = QColor(60, 80, 140, 30)
            amp_factor = 0.35
            num_bars = 7

        # 1. Resplandor de fondo
        radial = QRadialGradient(w / 2.0, mid_y, 40)
        radial.setColorAt(0.0, glow_col)
        radial.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.setBrush(QBrush(radial))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(int(w / 2.0 - 45), int(mid_y - 25), 90, 50)

        # 2. Barras de audio simétricas futuristas
        bar_width = 4.0
        bar_gap = 7.0
        total_width = num_bars * bar_width + (num_bars - 1) * bar_gap
        start_x = (w - total_width) / 2.0

        for i in range(num_bars):
            dist_from_center = abs(i - (num_bars // 2))
            center_weight = 1.0 - (dist_from_center * 0.18)

            if self.state == "listening":
                bar_h = (10 + 26 * center_weight * abs(math.sin(t * 6.0 + i * 0.85))) * amp_factor
            elif self.state == "thinking":
                bar_h = (12 + 18 * abs(math.sin(t * 8.0 + i * 1.2))) * amp_factor
            elif self.state == "speaking":
                bar_h = (10 + 30 * center_weight * abs(math.sin(t * 9.0 + i * 1.4) * math.cos(t * 4.0 + i))) * amp_factor
            else: # idle
                bar_h = (6 + 8 * center_weight * abs(math.sin(t * 2.0 + i * 0.5))) * amp_factor

            x = start_x + i * (bar_width + bar_gap)
            y = mid_y - (bar_h / 2.0)

            # Gradiente vertical por barra
            grad = QLinearGradient(x, y, x, y + bar_h)
            grad.setColorAt(0.0, base_col)
            grad.setColorAt(1.0, QColor(base_col.red(), base_col.green(), base_col.blue(), 100))

            painter.setBrush(QBrush(grad))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(QRectF(x, y, bar_width, bar_h), 2.0, 2.0)


class FloatingAreyCapsule(QWidget):
    """
    Widget de escritorio futurista en Glassmorphism flotante.
    """
    def __init__(self):
        super().__init__()
        self.drag_pos = QPoint()
        self.is_collapsed = False
        self.current_state = "idle"

        # Configuración de ventana flotante sin bordes
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        self.full_size = QSize(410, 135)
        self.collapsed_size = QSize(230, 48)
        self.setFixedSize(self.full_size)

        # Ubicación en la pantalla (esquina inferior derecha)
        screen = QApplication.primaryScreen().geometry()
        self.move(screen.width() - self.width() - 35, screen.height() - self.height() - 75)

        self._build_ui()

        # Timer de animación a 60 FPS
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self._on_anim_tick)
        self.anim_timer.start(16)

        # Conectar puente de eventos
        ui_bridge.state_changed.connect(self.set_state)
        ui_bridge.subtitle_changed.connect(self.set_subtitle)
        ui_bridge.device_status_changed.connect(self.update_devices)

        # Configurar atajo de teclado global (Alt+Espacio)
        self._setup_global_hotkey()

    def _setup_global_hotkey(self):
        def on_hotkey():
            ui_bridge.trigger_voice_requested.emit()

        try:
            keyboard.add_hotkey("alt+space", on_hotkey, suppress=False)
            logger.info("⌨️ Atajo global registrado: [Alt + Espacio]")
        except Exception as e:
            logger.warning(f"No se pudo registrar atajo global: {e}")

    def _build_ui(self):
        # Layout principal vertical
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(14, 10, 14, 10)
        self.main_layout.setSpacing(6)

        # ----------------- 1. HEADER SUPERIOR -----------------
        self.header_layout = QHBoxLayout()
        self.header_layout.setSpacing(8)

        # Indicador de estado del Servidor / Nube
        self.lbl_cloud = QLabel("🟢 AREY 2.0")
        self.lbl_cloud.setStyleSheet("color: #00ffaa; font-weight: bold; font-size: 11px; font-family: 'Segoe UI';")

        # Badge de Teléfono
        self.lbl_phone = QLabel("📱 Cel: Conectado")
        self.lbl_phone.setStyleSheet("color: #a0a5c0; font-size: 10px; background-color: rgba(255,255,255,0.06); border-radius: 4px; padding: 2px 6px;")

        # Badge de Smart TV
        self.lbl_tv = QLabel("📺 Smart TV: Lista")
        self.lbl_tv.setStyleSheet("color: #a0a5c0; font-size: 10px; background-color: rgba(255,255,255,0.06); border-radius: 4px; padding: 2px 6px;")

        self.btn_collapse = QPushButton("–")
        self.btn_collapse.setFixedSize(18, 18)
        self.btn_collapse.setStyleSheet("QPushButton { color: #8890b0; background: transparent; border: none; font-weight: bold; } QPushButton:hover { color: #ffffff; }")
        self.btn_collapse.clicked.connect(self.toggle_collapse)

        self.btn_close = QPushButton("✕")
        self.btn_close.setFixedSize(18, 18)
        self.btn_close.setStyleSheet("QPushButton { color: #8890b0; background: transparent; border: none; } QPushButton:hover { color: #ff5555; }")
        self.btn_close.clicked.connect(self.hide)

        self.header_layout.addWidget(self.lbl_cloud)
        self.header_layout.addWidget(self.lbl_phone)
        self.header_layout.addWidget(self.lbl_tv)
        self.header_layout.addStretch()
        self.header_layout.addWidget(self.btn_collapse)
        self.header_layout.addWidget(self.btn_close)

        # ----------------- 2. CUERPO: VISUALIZADOR + SUBTÍTULOS -----------------
        self.body_layout = QHBoxLayout()
        self.body_layout.setSpacing(12)

        self.visualizer = GlassWaveVisualizer(self)

        self.lbl_subtitle = QLabel("Di 'Arey' o presiona Alt + Espacio")
        self.lbl_subtitle.setWordWrap(True)
        self.lbl_subtitle.setStyleSheet("color: #dcdff0; font-size: 12px; font-family: 'Segoe UI'; font-weight: 500;")

        self.body_layout.addWidget(self.visualizer)
        self.body_layout.addWidget(self.lbl_subtitle, 1)

        # ----------------- 3. BOTÓN DE ACCIÓN RÁPIDA INFERIOR -----------------
        self.bottom_layout = QHBoxLayout()
        self.btn_talk = QPushButton("🎙️ Hablar con Arey (Alt + Espacio)")
        self.btn_talk.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_talk.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1a1e36, stop:1 #282d4d);
                color: #8be9fd;
                border: 1px solid rgba(139, 233, 253, 0.3);
                border-radius: 8px;
                padding: 5px 12px;
                font-size: 11px;
                font-weight: 600;
                font-family: 'Segoe UI';
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #22294c, stop:1 #353c66);
                border: 1px solid #8be9fd;
                color: #ffffff;
            }
        """)
        self.btn_talk.clicked.connect(lambda: ui_bridge.trigger_voice_requested.emit())

        self.lbl_status = QLabel("Listo")
        self.lbl_status.setStyleSheet("color: #6272a4; font-size: 10px;")

        self.bottom_layout.addWidget(self.btn_talk, 1)
        self.bottom_layout.addWidget(self.lbl_status)

        self.main_layout.addLayout(self.header_layout)
        self.main_layout.addLayout(self.body_layout)
        self.main_layout.addLayout(self.bottom_layout)

    def _on_anim_tick(self):
        self.visualizer.step()

    def set_state(self, state: str):
        self.current_state = state
        self.visualizer.set_state(state)
        state_text = {
            "idle": "Reposo",
            "listening": "🎤 Escuchando tu voz...",
            "thinking": "🧠 Pensando con IA...",
            "speaking": "🗣️ Hablando..."
        }.get(state, "Listo")
        self.lbl_status.setText(state_text)
        self.update()

    def set_subtitle(self, role: str, text: str):
        if role == "user":
            self.lbl_subtitle.setText(f"🗣️ <i>\"{text}\"</i>")
        elif role == "arey":
            self.lbl_subtitle.setText(f"✨ {text}")
        else:
            self.lbl_subtitle.setText(text)

    def update_devices(self, data: dict):
        if "phone_battery" in data:
            bat = data.get("phone_battery")
            self.lbl_phone.setText(f"📱 Cel: {bat}% 🔋" if bat is not None else "📱 Cel: Online")
            self.lbl_phone.setStyleSheet("color: #50fa7b; font-size: 10px; background-color: rgba(80,250,123,0.1); border-radius: 4px; padding: 2px 6px;")
        if "tv_online" in data:
            tv_ok = data.get("tv_online")
            self.lbl_tv.setText("📺 Smart TV: Online" if tv_ok else "📺 Smart TV: Offline")

    def toggle_collapse(self):
        self.is_collapsed = not self.is_collapsed
        if self.is_collapsed:
            self.lbl_subtitle.hide()
            self.btn_talk.hide()
            self.lbl_status.hide()
            self.setFixedSize(self.collapsed_size)
            self.btn_collapse.setText("+")
        else:
            self.lbl_subtitle.show()
            self.btn_talk.show()
            self.lbl_status.show()
            self.setFixedSize(self.full_size)
            self.btn_collapse.setText("–")

    # ==================== RENDERIZADO GLASSMORPHISM ====================

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        rect = QRectF(1, 1, self.width() - 2, self.height() - 2)

        # 1. Fondo de cristal oscuro traslúcido (#0e101a al 92% de opacidad)
        bg_brush = QBrush(QColor(14, 16, 26, 235))
        painter.setBrush(bg_brush)

        # 2. Borde neón adaptativo
        if self.current_state == "listening":
            border_pen = QPen(QColor(0, 255, 170, 180), 1.5)
        elif self.current_state == "thinking":
            border_pen = QPen(QColor(80, 150, 255, 180), 1.5)
        elif self.current_state == "speaking":
            border_pen = QPen(QColor(210, 100, 255, 180), 1.5)
        else:
            border_pen = QPen(QColor(60, 68, 100, 120), 1.0)

        painter.setPen(border_pen)
        painter.drawRoundedRect(rect, 14.0, 14.0)

    # ==================== ARRASTRE DE VENTANA ====================

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_pos)
            event.accept()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.toggle_collapse()
            event.accept()

def run_app():
    app = QApplication(sys.argv)
    window = FloatingAreyCapsule()
    window.show()
    return app, window

if __name__ == "__main__":
    app, window = run_app()
    sys.exit(app.exec())
