import sys
import math
import time
from PyQt6.QtCore import Qt, QTimer, QPoint, pyqtSignal, QObject, QRectF
from PyQt6.QtWidgets import QApplication, QWidget, QMenu, QLabel, QVBoxLayout
from PyQt6.QtGui import QPainter, QColor, QPen, QPainterPath, QFont, QLinearGradient, QBrush

class OrbStateBridge(QObject):
    state_changed = pyqtSignal(str)  # 'idle', 'listening', 'thinking', 'speaking'

state_bridge = OrbStateBridge()

# Paleta de colores
BG_COLOR       = QColor(28, 28, 32)       # Fondo gris oscuro
BORDER_COLOR   = QColor(70, 70, 85)       # Borde gris delgado
BORDER_ACTIVE  = QColor(130, 130, 160)    # Borde iluminado activo
TEXT_COLOR     = QColor(190, 190, 205)    # Texto sutil
LINE_IDLE      = QColor(80, 90, 120)      # Línea reposo: azul grisáceo
LINE_LISTEN    = QColor(0, 220, 160)      # Línea escuchando: verde esmeralda
LINE_THINK     = QColor(80, 160, 255)     # Línea pensando: azul eléctrico
LINE_SPEAK     = QColor(200, 100, 255)    # Línea hablando: morado vivo

LABEL_MAP = {
    "idle":      "Reposo",
    "listening": "Escuchando...",
    "thinking":  "Procesando...",
    "speaking":  "Hablando..."
}

class FloatingAreyOrb(QWidget):
    """
    Widget flotante cuadrado con ondas de sonido animadas.
    """
    def __init__(self):
        super().__init__()
        self.state = "idle"
        self.tick = 0.0
        self.drag_position = QPoint()
        self.press_time = 0.0

        # --- Ventana flotante sin bordes del sistema ---
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setFixedSize(180, 130)

        # Posición: esquina inferior derecha
        screen = QApplication.primaryScreen().geometry()
        self.move(screen.width() - 210, screen.height() - 180)

        # Animación a 60 FPS
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self._tick)
        self.anim_timer.start(16)

        # Conectar cambio de estado
        state_bridge.state_changed.connect(self._on_state_changed)

    def _on_state_changed(self, new_state: str):
        self.state = new_state
        self.update()

    def _tick(self):
        self.tick += 0.045
        if self.tick > 1e6:
            self.tick = 0.0
        self.update()

    # ─────────────── Ratón ───────────────

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self.press_time = time.time()
            event.accept()
        elif event.button() == Qt.MouseButton.RightButton:
            self._show_context_menu(event.globalPosition().toPoint())

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if (time.time() - self.press_time) < 0.25:
                try:
                    from wake_word import wake_detector
                    wake_detector.trigger_manually()
                except Exception:
                    pass
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()

    def _show_context_menu(self, pos):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #1c1c20;
                color: #bebebd;
                border: 1px solid #46465a;
                border-radius: 6px;
                padding: 3px;
                font-family: 'Segoe UI', sans-serif;
                font-size: 12px;
            }
            QMenu::item { padding: 5px 14px; border-radius: 3px; }
            QMenu::item:selected { background-color: #2e2e3a; color: #8ab4fa; }
        """)
        menu.addAction("Ocultar").triggered.connect(self.hide)
        menu.exec(pos)

    # ─────────────── Dibujo ───────────────

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        w, h = self.width(), self.height()
        t = self.tick

        # 1. Fondo gris oscuro con esquinas redondeadas
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(BG_COLOR)
        painter.drawRoundedRect(0, 0, w, h, 10, 10)

        # 2. Borde del cuadrado
        is_active = self.state != "idle"
        border_col = BORDER_ACTIVE if is_active else BORDER_COLOR
        pen_border = QPen(border_col, 1.5)
        painter.setPen(pen_border)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(1, 1, w - 2, h - 2, 9, 9)

        # 3. Zona de ondas (ocupa el 75% superior del widget)
        wave_top    = 14
        wave_bottom = int(h * 0.80)
        wave_mid    = (wave_top + wave_bottom) // 2
        margin      = 18

        self._draw_waves(painter, t, margin, wave_top, w - margin, wave_bottom, wave_mid)

        # 4. Etiqueta de estado
        self._draw_label(painter, w, h)

    def _get_wave_color(self):
        return {
            "idle":      LINE_IDLE,
            "listening": LINE_LISTEN,
            "thinking":  LINE_THINK,
            "speaking":  LINE_SPEAK,
        }.get(self.state, LINE_IDLE)

    def _draw_waves(self, painter, t, x_left, y_top, x_right, y_bottom, y_mid):
        color     = self._get_wave_color()
        amplitude = (y_bottom - y_top) / 2.0 - 2
        width_px  = x_right - x_left
        state     = self.state

        # Configuración de líneas según estado
        configs = {
            "idle": [
                # (fase, amplitud_factor, grosor, alpha, freq)
                (0.0,  0.22, 2.0, 90,  1.0),
                (1.1,  0.12, 1.3, 55,  1.0),
                (-0.8, 0.08, 1.0, 35,  1.0),
            ],
            "listening": [
                (0.0,  0.85, 3.5, 255, 1.0),
                (0.7,  0.55, 2.5, 180, 1.3),
                (-0.5, 0.30, 1.8, 110, 0.7),
                (1.4,  0.18, 1.2, 65,  1.6),
            ],
            "thinking": [
                (0.0,  0.60, 2.8, 230, 2.5),
                (0.9,  0.45, 2.0, 160, 3.0),
                (-0.7, 0.25, 1.5, 100, 1.8),
            ],
            "speaking": [
                (0.0,  1.0,  4.0, 255, 1.0),
                (0.5,  0.70, 3.0, 200, 1.8),
                (-0.4, 0.45, 2.2, 140, 2.4),
                (1.1,  0.25, 1.5, 80,  0.6),
                (-1.2, 0.15, 1.0, 50,  3.2),
            ],
        }.get(state, [
            (0.0, 0.22, 2.0, 90, 1.0),
        ])

        # Modulación de amplitud global en vivo
        if state == "idle":
            amp_mod = 0.8 + 0.2 * math.sin(t * 1.5)
        elif state == "listening":
            amp_mod = 0.8 + 0.2 * math.sin(t * 6.0) + 0.1 * math.sin(t * 13.0)
        elif state == "thinking":
            amp_mod = 0.7 + 0.3 * abs(math.sin(t * 8.0))
        else:  # speaking
            amp_mod = 0.7 + 0.3 * math.sin(t * 9.0) + 0.15 * math.sin(t * 17.0)

        n_points = 120

        for phase, amp_factor, thickness, alpha, freq in configs:
            path = QPainterPath()
            for i in range(n_points + 1):
                x = x_left + (i / n_points) * width_px
                # Onda sinusoidal con variación de armónicos
                y_offset = (
                    amplitude * amp_factor * amp_mod *
                    math.sin(freq * 2 * math.pi * (i / n_points) * 2.5 + t * 4.5 + phase)
                )
                if state == "speaking":
                    y_offset += (
                        amplitude * amp_factor * amp_mod * 0.3 *
                        math.sin(freq * 2 * math.pi * (i / n_points) * 5.0 - t * 7.0 + phase)
                    )
                y = y_mid + y_offset
                if i == 0:
                    path.moveTo(x, y)
                else:
                    path.lineTo(x, y)

            line_color = QColor(color)
            line_color.setAlpha(alpha)
            pen = QPen(line_color, thickness, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(path)

    def _draw_label(self, painter, w, h):
        label_text = LABEL_MAP.get(self.state, "")
        color = self._get_wave_color()
        label_color = QColor(color)
        label_color.setAlpha(210)

        font = QFont("Segoe UI", 8)
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.0)
        painter.setFont(font)
        painter.setPen(label_color)

        painter.drawText(
            QRectF(0, h - 22, w, 18),
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter,
            label_text
        )

        # Nombre "Arey" en gris tenue arriba
        font_title = QFont("Segoe UI", 7)
        painter.setFont(font_title)
        painter.setPen(QColor(100, 100, 115, 180))
        painter.drawText(
            QRectF(0, 2, w, 13),
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter,
            "AREY"
        )


def run_floating_orb_app():
    app = QApplication(sys.argv)
    orb = FloatingAreyOrb()
    orb.show()
    return app, orb


if __name__ == "__main__":
    app, orb = run_floating_orb_app()
    # Demostración de estados para previsualización
    states = ["idle", "listening", "thinking", "speaking"]
    idx = [0]
    def cycle():
        state_bridge.state_changed.emit(states[idx[0] % len(states)])
        idx[0] += 1
    timer = QTimer()
    timer.timeout.connect(cycle)
    timer.start(2200)
    sys.exit(app.exec())
