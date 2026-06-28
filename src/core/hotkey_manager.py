"""
HotkeyManager - global and local hotkey registration
"""

from PyQt6.QtWidgets import QShortcut, QApplication
from PyQt6.QtGui import QKeySequence
from PyQt6.QtCore import QObject, Qt


class HotkeyManager(QObject):
    def __init__(self, config, controller):
        super().__init__()
        self.config = config
        self.controller = controller
        self.shortcuts = []

    def setup(self):
        # We attach shortcuts to the toolbar widget so they work app-wide
        toolbar = self.controller.toolbar
        canvas = self.controller.overlay.canvas

        hotkeys = self.config.get("hotkeys") or {}

        mappings = [
            (hotkeys.get("toggle_overlay", "Ctrl+Shift+D"), self.controller.toggle_overlay),
            (hotkeys.get("undo", "Ctrl+Z"), canvas.undo),
            (hotkeys.get("redo", "Ctrl+Y"), canvas.redo),
            (hotkeys.get("clear", "Ctrl+Shift+X"), canvas.clear_all),
            (hotkeys.get("screenshot", "Ctrl+Shift+S"), self.controller.overlay.take_screenshot),
            (hotkeys.get("pen", "P"), lambda: canvas.set_tool("pen")),
            (hotkeys.get("highlighter", "H"), lambda: canvas.set_tool("highlighter")),
            (hotkeys.get("eraser", "E"), lambda: canvas.set_tool("eraser")),
            (hotkeys.get("line", "L"), lambda: canvas.set_tool("line")),
            (hotkeys.get("rectangle", "R"), lambda: canvas.set_tool("rectangle")),
            (hotkeys.get("circle", "C"), lambda: canvas.set_tool("circle")),
            (hotkeys.get("arrow", "A"), lambda: canvas.set_tool("arrow")),
            (hotkeys.get("triangle", "Shift+T"), lambda: canvas.set_tool("triangle")),
            (hotkeys.get("star", "Shift+S"), lambda: canvas.set_tool("star")),
            (hotkeys.get("laser", "Space"), lambda: canvas.set_tool("laser")),
            (hotkeys.get("text", "T"), lambda: canvas.set_tool("text")),
        ]

        for key_seq, callback in mappings:
            sc = QShortcut(QKeySequence(key_seq), toolbar)
            sc.setContext(Qt.ShortcutContext.ApplicationShortcut)
            sc.activated.connect(callback)
            self.shortcuts.append(sc)
