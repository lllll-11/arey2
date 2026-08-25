import sys
import math
import time
from PyQt6.QtCore import Qt, QTimer, QPoint, pyqtSignal, QObject
from PyQt6.QtWidgets import QApplication, QWidget, QMenu
from PyQt6.QtGui import QPainter, QColor, QRadialGradient, QLinearGradient, QBrush, QPen, QPainterPath

class OrbStateBridge(QObject):
    state_changed = pyqtSignal(str) # 'idle', 'listening', 'thinking', 'speaking'

state_bridge = OrbStateBridge()

class FloatingAreyOrb(QWidget):
    """
    Widget flotante circular con animaciones fluidas a 60 FPS.
    Estados:
      - 'idle': Respiración sutil en azul/morado neón.
      - 'listening': Ondas acústicas expansivas verdes/cian brillantes mientras escucha.
      - 'thinking': Giro orbital acelerado mientras Gemini procesa.
      - 'speaking': Ondas vocales orgánicas fluidas mientras Arey habla.
    """
    def __init__(self):
        super().__init__()
        self.state = "idle" # 'idle', 'listening', 'thinking', 'speaking'
        self.tick = 0.0
        self.drag_position = QPoint()

        # Configuración de ventana flotante transparente sin bordes
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.SubWindow
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)

        # Dimensiones del widget
        self.size_px = 120
        self.resize(self.size_px, self.size_px)

        # Posicionar en la esquina inferior derecha de la pantalla
        screen = QApplication.primaryScreen().geometry()
        self.move(screen.width() - self.size_px - 35, screen.height() - self.size_px - 85)

        # Temporizador de animación a 60 FPS (16ms)
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self._animate_step)
        self.anim_timer.start(16)

        # Conectar puente de estados
        state_bridge.state_changed.connect(self.set_state_slot)

    def set_state_slot(self, new_state: str):
        self.state = new_state
        self.update()

    def _animate_step(self):
        self.tick += 0.05
        if self.tick > 100000:
            self.tick = 0.0
        self.update()

    # ==================== EVENTOS DE RATÓN (ARRASTRAR Y SOLTAR) ====================

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
        elif event.button() == Qt.MouseButton.RightButton:
            self._show_context_menu(event.globalPosition().toPoint())

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()

    def _show_context_menu(self, pos):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #1e1e2e;
                color: #cdd6f4;
                border: 1px solid #45475a;
                border-radius: 8px;
                padding: 4px;
                font-family: 'Segoe UI', sans-serif;
                font-size: 12px;
            }
            QMenu::item {
                padding: 6px 16px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #313244;
                color: #89b4fa;
            }
        """)
        action_idle = menu.addAction("💤 Estado: Reposo")
        action_idle.triggered.connect(lambda: state_bridge.state_changed.emit("idle"))
        action_listen = menu.addAction("🎤 Estado: Escuchando")
        action_listen.triggered.connect(lambda: state_bridge.state_changed.emit("listening"))
        action_speak = menu.addAction("🗣️ Estado: Hablando")
        action_speak.triggered.connect(lambda: state_bridge.state_changed.emit("speaking"))
        menu.addSeparator()
        action_exit = menu.addAction("❌ Ocultar Widget")
        action_exit.triggered.connect(self.hide)
        menu.exec(pos)

    # ==================== DIBUJADO DE ANIMACIONES FLUIDAS ====================

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        center_x = self.width() / 2.0
        center_y = self.height() / 2.0
        base_radius = 28.0

        t = self.tick

        # ----------------- 1. ESTADO: LISTENING (ESCUCHANDO - ONDAS EXPANSIVAS CIAN/ESMERALDA) -----------------
        if self.state == "listening":
            # Ondas concéntricas expansivas pulsantes
            for i in range(3):
                wave_t = (t * 1.5 + i * 1.0) % 3.0
                wave_radius = base_radius + (wave_t * 16.0)
                alpha = int(max(0, min(220, (1.0 - (wave_t / 3.0)) * 220)))
                
                pen = QPen(QColor(0, 255, 180, alpha), 2.5)
                painter.setPen(pen)
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawEllipse(QPoint(int(center_x), int(center_y)), int(wave_radius), int(wave_radius))

            # Núcleo brillante activo
            glow_radius = base_radius + math.sin(t * 5.0) * 3.5
            grad = QRadialGradient(center_x, center_y, glow_radius)
            grad.setColorAt(0.0, QColor(0, 255, 200, 255))
            grad.setColorAt(0.5, QColor(0, 180, 240, 230))
            grad.setColorAt(0.9, QColor(0, 100, 200, 150))
            grad.setColorAt(1.0, QColor(0, 50, 150, 0))

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(grad))
            painter.drawEllipse(QPoint(int(center_x), int(center_y)), int(glow_radius + 4), int(glow_radius + 4))

            # Centro blanco vibrante
            inner_pen = QPen(QColor(255, 255, 255, 240), 2.0)
            painter.setPen(inner_pen)
            painter.setBrush(QColor(255, 255, 255, 180))
            painter.drawEllipse(QPoint(int(center_x), int(center_y)), 10, 10)

        # ----------------- 2. ESTADO: SPEAKING (HABLANDO - ONDAS VOCALES MORADAS/ROSA) -----------------
        elif self.state == "speaking":
            # Ondas vocales dinámicas multidimensionales
            for i in range(4):
                freq = 3.0 + i * 1.5
                radius_var = math.sin(t * freq + i) * 6.0
                wave_r = base_radius + 8.0 + radius_var
                
                alpha = int(140 - i * 30)
                pen = QPen(QColor(180, 100, 255, alpha), 2.0)
                painter.setPen(pen)
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawEllipse(QPoint(int(center_x), int(center_y)), int(wave_r + i * 4), int(wave_r + i * 4))

            # Gradiente de voz estilo Siri / Jarvis
            grad = QRadialGradient(center_x, center_y, base_radius + 6.0)
            grad.setColorAt(0.0, QColor(255, 110, 180, 255))
            grad.setColorAt(0.4, QColor(160, 60, 255, 230))
            grad.setColorAt(0.8, QColor(80, 30, 200, 180))
            grad.setColorAt(1.0, QColor(40, 10, 120, 0))

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(grad))
            pulse = math.sin(t * 8.0) * 4.0
            painter.drawEllipse(QPoint(int(center_x), int(center_y)), int(base_radius + pulse), int(base_radius + pulse))

            # Partículas orbitales de voz
            for p in range(5):
                angle = (t * 4.0 + p * (2 * math.pi / 5))
                px = center_x + math.cos(angle) * (base_radius + 2)
                py = center_y + math.sin(angle) * (base_radius + 2)
                painter.setBrush(QColor(255, 255, 255, 230))
                painter.drawEllipse(QPoint(int(px), int(py)), 3, 3)

        # ----------------- 3. ESTADO: THINKING (PROCESANDO - GIRO ORBITAL) -----------------
        elif self.state == "thinking":
            # Anillo de rotación de luz
            orbit_radius = base_radius + 8.0
            pen = QPen(QColor(100, 150, 255, 80), 2.0)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(QPoint(int(center_x), int(center_y)), int(orbit_radius), int(orbit_radius))

            # Satélites giratorios rápidos
            for s in range(3):
                angle = t * 6.0 + s * (2 * math.pi / 3)
                sx = center_x + math.cos(angle) * orbit_radius
                sy = center_y + math.sin(angle) * orbit_radius
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QColor(0, 230, 255, 240))
                painter.drawEllipse(QPoint(int(sx), int(sy)), 4, 4)

            # Núcleo pulsante azul
            grad = QRadialGradient(center_x, center_y, base_radius)
            grad.setColorAt(0.0, QColor(0, 180, 255, 240))
            grad.setColorAt(0.6, QColor(30, 60, 180, 180))
            grad.setColorAt(1.0, QColor(10, 20, 80, 0))
            painter.setBrush(QBrush(grad))
            painter.drawEllipse(QPoint(int(center_x), int(center_y)), int(base_radius), int(base_radius))

        # ----------------- 4. ESTADO: IDLE (REPOSO - RESPIRACIÓN AZUL SUAVE) -----------------
        else: # 'idle'
            # Suave halo exterior respirando lentamente
            breath = math.sin(t * 2.0) * 3.0
            halo_radius = base_radius + 10.0 + breath
            grad_halo = QRadialGradient(center_x, center_y, halo_radius)
            grad_halo.setColorAt(0.0, QColor(100, 130, 255, 90))
            grad_halo.setColorAt(0.7, QColor(60, 40, 180, 40))
            grad_halo.setColorAt(1.0, QColor(20, 10, 80, 0))

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(grad_halo))
            painter.drawEllipse(QPoint(int(center_x), int(center_y)), int(halo_radius), int(halo_radius))

            # Núcleo principal de cristal neón
            grad_core = QRadialGradient(center_x, center_y, base_radius)
            grad_core.setColorAt(0.0, QColor(120, 180, 255, 230))
            grad_core.setColorAt(0.5, QColor(70, 90, 220, 200))
            grad_core.setColorAt(0.85, QColor(30, 30, 120, 170))
            grad_core.setColorAt(1.0, QColor(10, 10, 60, 0))

            painter.setBrush(QBrush(grad_core))
            painter.drawEllipse(QPoint(int(center_x), int(center_y)), int(base_radius), int(base_radius))

            # Borde sutil brillante
            pen_border = QPen(QColor(180, 220, 255, 120), 1.5)
            painter.setPen(pen_border)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(QPoint(int(center_x), int(center_y)), int(base_radius), int(base_radius))

            # Pequeño destello de luz interior
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(255, 255, 255, 190))
            painter.drawEllipse(QPoint(int(center_x - 7), int(center_y - 7)), 3, 3)

def run_floating_orb_app():
    """
    Función de arranque de la interfaz gráfica flotante.
    """
    app = QApplication(sys.argv)
    orb = FloatingAreyOrb()
    orb.show()
    return app, orb

if __name__ == "__main__":
    app, orb = run_floating_orb_app()
    sys.exit(app.exec())
