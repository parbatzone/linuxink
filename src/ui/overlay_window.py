"""
OverlayWindow - full-screen transparent window for drawing on top of everything
"""

import os
import datetime
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QApplication, QFileDialog, QMessageBox
from PyQt6.QtCore import Qt, QRect, QTimer, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QPixmap


class OverlayWindow(QWidget):
    # Emit when Escape is pressed so the controller can sync toolbar state
    closed_by_escape = pyqtSignal()

    def __init__(self, config, canvas_class, parent=None):
        super().__init__(parent)
        self.config = config
        self.canvas_class = canvas_class
        self._setup_window()
        self._setup_canvas()

    def _setup_window(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)

        # Cover all monitors
        screen_geo = QRect()
        for screen in QApplication.screens():
            screen_geo = screen_geo.united(screen.geometry())
        self.setGeometry(screen_geo)
        self.setMouseTracking(True)

    def _setup_canvas(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.canvas = self.canvas_class(self)
        layout.addWidget(self.canvas)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 0))
        painter.end()

    def take_screenshot(self):
        """Capture screen WITH annotations"""
        self.hide()
        QTimer.singleShot(150, self._capture_and_restore)

    def _capture_and_restore(self):
        screen = QApplication.primaryScreen()
        screenshot = screen.grabWindow(0)

        annotations = self.canvas.get_flat_image()
        if not annotations.isNull():
            painter = QPainter(screenshot)
            painter.drawPixmap(0, 0, annotations)
            painter.end()

        self.show()

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = os.path.expanduser(f"~/Pictures/linuxink_{timestamp}.png")

        # Ensure ~/Pictures exists
        os.makedirs(os.path.expanduser("~/Pictures"), exist_ok=True)

        path, _ = QFileDialog.getSaveFileName(
            None, "Save Screenshot", default_name,
            "PNG Image (*.png);;JPEG Image (*.jpg);;All Files (*)"
        )
        if path:
            if screenshot.save(path):
                QMessageBox.information(None, "Saved", f"Screenshot saved to:\n{path}")
            else:
                QMessageBox.critical(None, "Error", f"Could not save to:\n{path}")

    def save_annotations(self):
        """Save just the annotation layer"""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = os.path.expanduser(f"~/Pictures/annotations_{timestamp}.png")
        os.makedirs(os.path.expanduser("~/Pictures"), exist_ok=True)

        path, _ = QFileDialog.getSaveFileName(
            None, "Save Annotations", default_name,
            "PNG Image (*.png);;All Files (*)"
        )
        if path:
            annotations = self.canvas.get_flat_image()
            if annotations.save(path):
                QMessageBox.information(None, "Saved", f"Annotations saved to:\n{path}")
            else:
                QMessageBox.critical(None, "Error", f"Could not save to:\n{path}")

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.hide()
            self.closed_by_escape.emit()  # Let controller sync toolbar
        else:
            super().keyPressEvent(event)
