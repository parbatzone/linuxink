"""
AppController - orchestrates overlay, toolbar, and hotkeys
"""

from PyQt6.QtWidgets import QSystemTrayIcon, QMenu, QApplication
from PyQt6.QtGui import QIcon, QAction, QPixmap, QPainter, QColor, QFont
from PyQt6.QtCore import QObject, Qt, QSize

from src.ui.overlay_window import OverlayWindow
from src.rendering.canvas import DrawingCanvas
from src.ui.toolbar import AnnotationToolbar
from src.core.hotkey_manager import HotkeyManager


class AppController(QObject):
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.overlay = None
        self.toolbar = None
        self.tray = None
        self.hotkey_manager = None
        self._overlay_visible = False

    def start(self):
        self.overlay = OverlayWindow(self.config, canvas_class=DrawingCanvas)
        self.toolbar = AnnotationToolbar(self.config)
        self.toolbar.show()

        self._connect_toolbar_to_overlay()

        self.hotkey_manager = HotkeyManager(self.config, self)
        self.hotkey_manager.setup()

        self._setup_tray()

        self.overlay.hide()
        self._overlay_visible = False

    def toggle_overlay(self):
        if self._overlay_visible:
            self._hide_overlay()
        else:
            self._show_overlay()

    def _show_overlay(self):
        self.overlay.show()
        self.overlay.raise_()
        self.overlay.activateWindow()
        self._overlay_visible = True
        self.toolbar.set_active(True)

    def _hide_overlay(self):
        self.overlay.hide()
        self._overlay_visible = False
        self.toolbar.set_active(False)

    def _connect_toolbar_to_overlay(self):
        tb = self.toolbar
        ov = self.overlay

        tb.tool_changed.connect(ov.canvas.set_tool)
        tb.color_changed.connect(ov.canvas.set_color)
        tb.size_changed.connect(ov.canvas.set_brush_size)
        tb.opacity_changed.connect(ov.canvas.set_opacity)
        tb.undo_requested.connect(ov.canvas.undo)
        tb.redo_requested.connect(ov.canvas.redo)
        tb.clear_requested.connect(ov.canvas.clear_all)
        tb.screenshot_requested.connect(ov.take_screenshot)
        tb.save_requested.connect(ov.save_annotations)
        tb.close_requested.connect(self.toggle_overlay)

        # Sync toolbar when overlay is hidden via Escape key
        ov.closed_by_escape.connect(self._on_escape_hide)

        ov.canvas.history_changed.connect(tb.update_undo_redo_state)

    def _on_escape_hide(self):
        self._overlay_visible = False
        self.toolbar.set_active(False)

    def _setup_tray(self):
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return

        self.tray = QSystemTrayIcon(self)

        pix = QPixmap(32, 32)
        pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(QColor("#E84393"))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(2, 2, 28, 28)
        p.setPen(QColor("white"))
        font = QFont("Arial", 16, QFont.Weight.Bold)
        p.setFont(font)
        p.drawText(pix.rect(), Qt.AlignmentFlag.AlignCenter, "✏")
        p.end()
        self.tray.setIcon(QIcon(pix))
        self.tray.setToolTip("LinuxInk — Screen Annotation Tool")

        menu = QMenu()
        toggle_act = QAction("Toggle Overlay  (Ctrl+Shift+D)", self)
        toggle_act.triggered.connect(self.toggle_overlay)
        menu.addAction(toggle_act)

        show_tb_act = QAction("Show Toolbar", self)
        show_tb_act.triggered.connect(self.toolbar.show)
        menu.addAction(show_tb_act)

        menu.addSeparator()

        quit_act = QAction("Quit LinuxInk", self)
        quit_act.triggered.connect(QApplication.instance().quit)
        menu.addAction(quit_act)

        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._tray_activated)
        self.tray.show()

    def _tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.toggle_overlay()
