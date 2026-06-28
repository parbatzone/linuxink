#!/usr/bin/env python3
"""
LinuxInk - Screen Annotation Tool
Entry point
"""

import sys
import os
import signal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Prefer X11; suppress noisy Qt debug output
os.environ.setdefault("QT_QPA_PLATFORM", "xcb")
os.environ.setdefault("QT_LOGGING_RULES", "*.debug=false;qt.qpa.*=false")

from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import Qt, QTimer

from src.core.app_controller import AppController
from src.core.config_manager import ConfigManager


def main():
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    app = QApplication(sys.argv)
    app.setApplicationName("LinuxInk")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("LinuxInk")

    # Load stylesheet
    style_path = os.path.join(os.path.dirname(__file__), "assets", "style.qss")
    if os.path.exists(style_path):
        with open(style_path, "r") as f:
            app.setStyleSheet(f.read())

    config = ConfigManager()

    try:
        controller = AppController(config)
        controller.start()
    except Exception as e:
        QMessageBox.critical(
            None,
            "LinuxInk — Startup Error",
            f"Failed to start LinuxInk:\n\n{e}\n\n"
            "Tip: if you see a display/platform error, try running:\n"
            "  QT_QPA_PLATFORM=xcb linuxink",
        )
        sys.exit(1)

    # Allow Ctrl+C to propagate
    timer = QTimer()
    timer.start(500)
    timer.timeout.connect(lambda: None)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
