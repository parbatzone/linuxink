"""
Enhanced AnnotationToolbar - floating, draggable toolbar with Pensela-like features
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QSlider, QLabel, QColorDialog, QFrame, QToolTip,
    QSizePolicy, QSpacerItem, QButtonGroup
)
from PyQt6.QtCore import Qt, QPoint, pyqtSignal, QSize, QTimer
from PyQt6.QtGui import (
    QColor, QPainter, QBrush, QPen, QIcon, QPixmap,
    QFont, QCursor, QLinearGradient
)


TOOLS = [
    ("pen",         "✏",  "Pen (P)"),
    ("highlighter", "🖍", "Highlighter (H)"),
    ("eraser",      "🧹", "Eraser (E)"),
    ("line",        "╱",  "Line (L)"),
    ("rectangle",   "▭",  "Rectangle (R)"),
    ("circle",      "◯",  "Circle (C)"),
    ("triangle",    "△",  "Triangle (Shift+T)"),
    ("arrow",       "→",  "Arrow (A)"),
    ("star",        "★",  "Star (Shift+S)"),
    ("text",        "T",  "Text (T)"),
    ("laser",       "◉",  "Laser Pointer (Space)"),
]


class ColorSwatch(QWidget):
    """Clickable color swatch"""
    clicked = pyqtSignal()

    def __init__(self, color="#FF0000", parent=None):
        super().__init__(parent)
        self.color = QColor(color)
        self.setFixedSize(32, 32)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setToolTip("Pick color")

    def set_color(self, color):
        self.color = QColor(color)
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(QBrush(self.color))
        p.setPen(QPen(QColor(255, 255, 255, 80), 1.5))
        p.drawRoundedRect(2, 2, 28, 28, 6, 6)
        p.end()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()


class ToolButton(QPushButton):
    def __init__(self, icon_text, tooltip, tool_id, parent=None):
        super().__init__(icon_text, parent)
        self.tool_id = tool_id
        self.setCheckable(True)
        self.setFixedSize(40, 40)
        self.setToolTip(tooltip)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        font = QFont("Noto Color Emoji", 16)
        self.setFont(font)
        self.setStyleSheet("""
            QPushButton {
                background: rgba(255,255,255,0.07);
                border: 1.5px solid rgba(255,255,255,0.12);
                border-radius: 8px;
                color: #FFFFFF;
                font-size: 16px;
            }
            QPushButton:hover {
                background: rgba(232,67,147,0.25);
                border-color: rgba(232,67,147,0.6);
            }
            QPushButton:checked {
                background: rgba(232,67,147,0.45);
                border-color: #E84393;
            }
        """)


class AnnotationToolbar(QWidget):
    # Signals relayed to canvas
    tool_changed     = pyqtSignal(str)
    color_changed    = pyqtSignal(str)
    size_changed     = pyqtSignal(int)
    opacity_changed  = pyqtSignal(float)
    undo_requested   = pyqtSignal()
    redo_requested   = pyqtSignal()
    clear_requested  = pyqtSignal()
    screenshot_requested = pyqtSignal()
    save_requested   = pyqtSignal()
    close_requested  = pyqtSignal()

    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self._drag_pos = None
        self._active = False
        self._current_color = config.get("defaults", "color") or "#FF0000"
        self._current_tool = "pen"

        self._setup_window()
        self._build_ui()

    def _setup_window(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedWidth(64)
        self.setMouseTracking(True)

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(8, 8, 8, 8)
        outer.setSpacing(4)

        # Drag handle
        handle = QLabel("⠿")
        handle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        handle.setFixedHeight(20)
        handle.setStyleSheet("color: rgba(255,255,255,0.5); font-size: 16px;")
        outer.addWidget(handle)

        # Tool buttons (scrollable area for many tools)
        self._btn_group = QButtonGroup(self)
        self._btn_group.setExclusive(True)
        self._tool_buttons = {}
        
        # Create two columns for tools
        tools_layout = QVBoxLayout()
        tools_layout.setSpacing(4)
        
        for tool_id, icon, tip in TOOLS:
            btn = ToolButton(icon, tip, tool_id)
            btn.clicked.connect(lambda checked, t=tool_id: self._on_tool(t))
            tools_layout.addWidget(btn)
            self._btn_group.addButton(btn)
            self._tool_buttons[tool_id] = btn

        self._tool_buttons["pen"].setChecked(True)
        outer.addLayout(tools_layout)

        # Divider
        outer.addWidget(self._divider())

        # Color swatch
        self._color_swatch = ColorSwatch(self._current_color)
        self._color_swatch.clicked.connect(self._pick_color)
        outer.addWidget(self._color_swatch)

        # Preset colors
        for preset in ["#FF0000", "#FFFF00", "#00FF00", "#0080FF", "#FFFFFF"]:
            sw = ColorSwatch(preset)
            sw.setFixedSize(28, 28)
            sw.clicked.connect(lambda c=preset: self._set_color(c))
            sw.setToolTip(preset)
            outer.addWidget(sw)

        # Divider
        outer.addWidget(self._divider())

        # Brush size
        size_label = self._icon_label("⊙")
        outer.addWidget(size_label)
        self._size_slider = QSlider(Qt.Orientation.Vertical)
        self._size_slider.setRange(1, 40)
        self._size_slider.setValue(self.config.get("defaults", "brush_size") or 4)
        self._size_slider.setFixedHeight(80)
        self._size_slider.setToolTip("Brush size")
        self._size_slider.valueChanged.connect(lambda v: self.size_changed.emit(v))
        self._size_slider.setStyleSheet("""
            QSlider::groove:vertical { background: rgba(255,255,255,0.15); width: 6px; border-radius: 3px; }
            QSlider::handle:vertical { background: #E84393; width: 14px; height: 14px; margin: 0 -4px; border-radius: 7px; }
            QSlider::sub-page:vertical { background: rgba(232,67,147,0.5); border-radius: 3px; }
        """)
        outer.addWidget(self._size_slider, alignment=Qt.AlignmentFlag.AlignHCenter)

        # Opacity
        op_label = self._icon_label("◑")
        outer.addWidget(op_label)
        self._opacity_slider = QSlider(Qt.Orientation.Vertical)
        self._opacity_slider.setRange(10, 100)
        self._opacity_slider.setValue(100)
        self._opacity_slider.setFixedHeight(60)
        self._opacity_slider.setToolTip("Opacity")
        self._opacity_slider.valueChanged.connect(lambda v: self.opacity_changed.emit(v / 100.0))
        self._opacity_slider.setStyleSheet(self._size_slider.styleSheet())
        outer.addWidget(self._opacity_slider, alignment=Qt.AlignmentFlag.AlignHCenter)

        outer.addWidget(self._divider())

        # Action buttons
        for icon, tip, sig in [
            ("↩", "Undo (Ctrl+Z)", self.undo_requested),
            ("↪", "Redo (Ctrl+Y)", self.redo_requested),
            ("🗑", "Clear all (Ctrl+Shift+X)", self.clear_requested),
            ("📷", "Screenshot (Ctrl+Shift+S)", self.screenshot_requested),
            ("💾", "Save annotations", self.save_requested),
        ]:
            btn = self._action_btn(icon, tip)
            btn.clicked.connect(sig.emit)
            outer.addWidget(btn)

        outer.addWidget(self._divider())

        # Close overlay button
        close_btn = self._action_btn("✕", "Hide overlay (Ctrl+Shift+D)", color="#FF4466")
        close_btn.clicked.connect(self.close_requested.emit)
        outer.addWidget(close_btn)

        outer.addStretch()
        self.adjustSize()

    def _divider(self):
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFixedHeight(1)
        line.setStyleSheet("background: rgba(255,255,255,0.12); border: none;")
        return line

    def _icon_label(self, icon):
        lbl = QLabel(icon)
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setStyleSheet("color: rgba(255,255,255,0.5); font-size: 13px;")
        return lbl

    def _action_btn(self, icon, tip, color=None):
        btn = QPushButton(icon)
        btn.setFixedSize(40, 36)
        btn.setToolTip(tip)
        btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        hover_bg = f"rgba({','.join(str(int(c*255)) for c in QColor(color or '#E84393').getRgbF()[:3])},0.3)" if color else "rgba(232,67,147,0.25)"
        border = color or "#E84393"
        btn.setStyleSheet(f"""
            QPushButton {{
                background: rgba(255,255,255,0.06);
                border: 1.5px solid rgba(255,255,255,0.1);
                border-radius: 8px;
                color: white;
                font-size: 15px;
            }}
            QPushButton:hover {{
                background: {hover_bg};
                border-color: {border};
            }}
        """)
        return btn

    def _on_tool(self, tool_id):
        self._current_tool = tool_id
        self.tool_changed.emit(tool_id)

    def _pick_color(self):
        color = QColorDialog.getColor(
            QColor(self._current_color), self,
            "Choose Color",
            QColorDialog.ColorDialogOption.ShowAlphaChannel
        )
        if color.isValid():
            self._set_color(color.name())

    def _set_color(self, color_str):
        self._current_color = color_str
        self._color_swatch.set_color(color_str)
        self.color_changed.emit(color_str)

    def set_active(self, active: bool):
        self._active = active

    def update_undo_redo_state(self, can_undo: bool, can_redo: bool):
        pass  # Could visually disable buttons; left for future

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        grad = QLinearGradient(0, 0, 0, self.height())
        grad.setColorAt(0, QColor(20, 16, 35, 230))
        grad.setColorAt(1, QColor(10, 8, 22, 230))
        p.setBrush(grad)
        p.setPen(QPen(QColor(232, 67, 147, 80), 1.5))
        p.drawRoundedRect(0, 0, self.width() - 1, self.height() - 1, 14, 14)
        p.end()

    # Drag to reposition
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.pos()

    def mouseMoveEvent(self, event):
        if self._drag_pos and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
