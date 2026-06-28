#!/usr/bin/env python3
"""
LinuxInk - A lightweight, hotkey-driven screen annotation overlay for Linux.

A professional presentation annotation tool with freehand drawing, shapes,
highlighting, and instant screenshots. Built with PyQt6.

Author: LinuxInk Team
License: MIT
"""

import sys
import json
from datetime import datetime
from pathlib import Path
from enum import Enum
from dataclasses import dataclass
from typing import List, Tuple, Optional

from PyQt6.QtCore import Qt, QPoint, QRect, QTimer, QSize
from PyQt6.QtGui import (
    QPainter, QPen, QColor, QFont, QBrush, QPixmap,
    QIcon, QPainterPath
)
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFrame, QButtonGroup, QMessageBox, QFileDialog
)
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QShortcut, QKeySequence


# ============================================================================
# DATA STRUCTURES
# ============================================================================

class ToolType(Enum):
    """Available drawing tools."""
    PEN = "pen"
    LINE = "line"
    RECTANGLE = "rectangle"
    CIRCLE = "circle"
    ARROW = "arrow"
    HIGHLIGHTER = "highlighter"
    TEXT = "text"


@dataclass
class Point:
    """A 2D point."""
    x: int
    y: int

    def to_qpoint(self) -> QPoint:
        """Convert to PyQt6 QPoint."""
        return QPoint(self.x, self.y)

    @classmethod
    def from_qpoint(cls, qp: QPoint) -> "Point":
        """Create from PyQt6 QPoint."""
        return cls(qp.x(), qp.y())


@dataclass
class Annotation:
    """Base annotation object. Subclassed for each tool type."""
    tool_type: ToolType
    color: QColor
    width: int

    def draw(self, painter: QPainter):
        """Draw this annotation. Override in subclasses."""
        pass

    def contains_point(self, p: Point) -> bool:
        """Check if this annotation contains a point. Override in subclasses."""
        return False


@dataclass
class PenAnnotation(Annotation):
    """Freehand pen stroke."""
    points: List[Point] = None

    def __post_init__(self):
        if self.points is None:
            self.points = []

    def draw(self, painter: QPainter):
        if len(self.points) < 2:
            return
        pen = QPen(self.color, self.width, Qt.PenStyle.SolidLine)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        path = QPainterPath()
        path.moveTo(self.points[0].to_qpoint())
        for p in self.points[1:]:
            path.lineTo(p.to_qpoint())
        painter.drawPath(path)

    def contains_point(self, p: Point) -> bool:
        """Check if point is near the path."""
        for point in self.points:
            dist = ((point.x - p.x) ** 2 + (point.y - p.y) ** 2) ** 0.5
            if dist <= self.width + 5:
                return True
        return False


@dataclass
class LineAnnotation(Annotation):
    """Straight line."""
    start: Point = None
    end: Point = None

    def draw(self, painter: QPainter):
        if self.start is None or self.end is None:
            return
        pen = QPen(self.color, self.width, Qt.PenStyle.SolidLine)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.drawLine(self.start.to_qpoint(), self.end.to_qpoint())

    def contains_point(self, p: Point) -> bool:
        """Check if point is near the line."""
        if self.start is None or self.end is None:
            return False
        # Distance from point to line segment
        dx = self.end.x - self.start.x
        dy = self.end.y - self.start.y
        if dx == 0 and dy == 0:
            dist = ((p.x - self.start.x) ** 2 + (p.y - self.start.y) ** 2) ** 0.5
            return dist <= self.width + 5
        t = max(0, min(1, ((p.x - self.start.x) * dx + (p.y - self.start.y) * dy) / (dx * dx + dy * dy)))
        closest_x = self.start.x + t * dx
        closest_y = self.start.y + t * dy
        dist = ((p.x - closest_x) ** 2 + (p.y - closest_y) ** 2) ** 0.5
        return dist <= self.width + 5


@dataclass
class RectangleAnnotation(Annotation):
    """Rectangle outline."""
    start: Point = None
    end: Point = None

    def draw(self, painter: QPainter):
        if self.start is None or self.end is None:
            return
        pen = QPen(self.color, self.width, Qt.PenStyle.SolidLine)
        painter.setPen(pen)
        rect = QRect(self.start.to_qpoint(), self.end.to_qpoint())
        painter.drawRect(rect)

    def contains_point(self, p: Point) -> bool:
        """Check if point is on the rectangle outline."""
        if self.start is None or self.end is None:
            return False
        x1, x2 = min(self.start.x, self.end.x), max(self.start.x, self.end.x)
        y1, y2 = min(self.start.y, self.end.y), max(self.start.y, self.end.y)
        margin = self.width + 5
        on_h_edge = (abs(p.y - y1) <= margin or abs(p.y - y2) <= margin) and x1 <= p.x <= x2
        on_v_edge = (abs(p.x - x1) <= margin or abs(p.x - x2) <= margin) and y1 <= p.y <= y2
        return on_h_edge or on_v_edge


@dataclass
class CircleAnnotation(Annotation):
    """Circle/ellipse outline."""
    start: Point = None
    end: Point = None

    def draw(self, painter: QPainter):
        if self.start is None or self.end is None:
            return
        pen = QPen(self.color, self.width, Qt.PenStyle.SolidLine)
        painter.setPen(pen)
        rect = QRect(self.start.to_qpoint(), self.end.to_qpoint())
        painter.drawEllipse(rect)

    def contains_point(self, p: Point) -> bool:
        """Check if point is on the circle outline."""
        if self.start is None or self.end is None:
            return False
        cx = (self.start.x + self.end.x) / 2
        cy = (self.start.y + self.end.y) / 2
        rx = abs(self.end.x - self.start.x) / 2
        ry = abs(self.end.y - self.start.y) / 2
        if rx == 0 or ry == 0:
            return False
        dist_from_ellipse = abs((((p.x - cx) / rx) ** 2 + ((p.y - cy) / ry) ** 2) ** 0.5 - 1)
        return dist_from_ellipse <= (self.width + 5) / max(rx, ry)


@dataclass
class ArrowAnnotation(Annotation):
    """Arrow with line and arrowhead."""
    start: Point = None
    end: Point = None

    def draw(self, painter: QPainter):
        if self.start is None or self.end is None:
            return
        pen = QPen(self.color, self.width, Qt.PenStyle.SolidLine)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.drawLine(self.start.to_qpoint(), self.end.to_qpoint())

        # Draw arrowhead
        import math
        dx = self.end.x - self.start.x
        dy = self.end.y - self.start.y
        angle = math.atan2(dy, dx)
        arrow_size = max(10, self.width * 3)
        p1_x = self.end.x - arrow_size * math.cos(angle - math.pi / 6)
        p1_y = self.end.y - arrow_size * math.sin(angle - math.pi / 6)
        p2_x = self.end.x - arrow_size * math.cos(angle + math.pi / 6)
        p2_y = self.end.y - arrow_size * math.sin(angle + math.pi / 6)
        painter.drawLine(self.end.to_qpoint(), QPoint(int(p1_x), int(p1_y)))
        painter.drawLine(self.end.to_qpoint(), QPoint(int(p2_x), int(p2_y)))

    def contains_point(self, p: Point) -> bool:
        """Check if point is near the arrow."""
        if self.start is None or self.end is None:
            return False
        dx = self.end.x - self.start.x
        dy = self.end.y - self.start.y
        if dx == 0 and dy == 0:
            dist = ((p.x - self.start.x) ** 2 + (p.y - self.start.y) ** 2) ** 0.5
            return dist <= self.width + 5
        t = max(0, min(1, ((p.x - self.start.x) * dx + (p.y - self.start.y) * dy) / (dx * dx + dy * dy)))
        closest_x = self.start.x + t * dx
        closest_y = self.start.y + t * dy
        dist = ((p.x - closest_x) ** 2 + (p.y - closest_y) ** 2) ** 0.5
        return dist <= self.width + 5


@dataclass
class HighlighterAnnotation(Annotation):
    """Semi-transparent highlighter."""
    points: List[Point] = None

    def __post_init__(self):
        if self.points is None:
            self.points = []

    def draw(self, painter: QPainter):
        if len(self.points) < 2:
            return
        # Make color semi-transparent
        color = QColor(self.color)
        color.setAlpha(100)
        pen = QPen(color, self.width * 2, Qt.PenStyle.SolidLine)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        path = QPainterPath()
        path.moveTo(self.points[0].to_qpoint())
        for p in self.points[1:]:
            path.lineTo(p.to_qpoint())
        painter.drawPath(path)

    def contains_point(self, p: Point) -> bool:
        """Check if point is near the path."""
        for point in self.points:
            dist = ((point.x - p.x) ** 2 + (point.y - p.y) ** 2) ** 0.5
            if dist <= self.width * 2 + 5:
                return True
        return False


@dataclass
class TextAnnotation(Annotation):
    """Text label."""
    position: Point = None
    text: str = ""

    def draw(self, painter: QPainter):
        if self.position is None or not self.text:
            return
        font = QFont("Arial", max(8, self.width * 2))
        painter.setFont(font)
        painter.setPen(self.color)
        painter.drawText(self.position.to_qpoint(), self.text)

    def contains_point(self, p: Point) -> bool:
        """Check if point is near the text."""
        if self.position is None or not self.text:
            return False
        font = QFont("Arial", max(8, self.width * 2))
        metrics = painter.fontMetrics() if hasattr(self, 'painter') else None
        # Simple bounding box check
        dist = ((p.x - self.position.x) ** 2 + (p.y - self.position.y) ** 2) ** 0.5
        return dist <= 50


# ============================================================================
# FLOATING TOOLBAR
# ============================================================================

class FloatingToolbar(QFrame):
    """Collapsible floating toolbar docked to the right edge."""

    tool_changed = pyqtSignal(ToolType)
    color_changed = pyqtSignal(QColor)
    width_changed = pyqtSignal(int)
    clear_all = pyqtSignal()
    undo = pyqtSignal()
    redo = pyqtSignal()
    spotlight_toggle = pyqtSignal(bool)

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setStyleSheet("""
            QFrame { background-color: #2b3e50; border-radius: 8px; }
            QPushButton {
                background-color: #34495e;
                color: white;
                border: 1px solid #7f8c8d;
                border-radius: 4px;
                padding: 6px;
                font-size: 11px;
            }
            QPushButton:hover { background-color: #3d556e; }
            QPushButton:pressed { background-color: #2a3f55; }
            QPushButton:checked {
                background-color: #e74c3c;
                border: 1px solid #c0392b;
            }
            QLabel { color: #ecf0f1; font-size: 10px; }
        """)

        self.collapsed = False
        self.current_tool = ToolType.PEN
        self.current_color = QColor("red")
        self.current_width = 2

        self._setup_ui()
        self._move_to_right_edge()

    def _setup_ui(self):
        """Build toolbar UI."""
        layout = QVBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # Toggle button
        toggle_btn = QPushButton("◄")
        toggle_btn.setMaximumWidth(30)
        toggle_btn.clicked.connect(self._toggle_collapse)
        layout.addWidget(toggle_btn)

        self.content_layout = QVBoxLayout()
        self.content_layout.setSpacing(6)

        # Tools section
        layout.addWidget(QLabel("TOOLS"))
        self.tool_buttons = {}
        for tool in ToolType:
            btn = QPushButton(tool.value.upper())
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, t=tool: self._select_tool(t))
            self.tool_buttons[tool] = btn
            self.content_layout.addWidget(btn)
        self.tool_buttons[ToolType.PEN].setChecked(True)

        # Colors section
        layout.addWidget(QLabel("COLORS"))
        self.color_buttons = {}
        colors = [
            ("Red", QColor("red")),
            ("Green", QColor("green")),
            ("Blue", QColor("blue")),
            ("Yellow", QColor("yellow")),
            ("White", QColor("white")),
            ("Orange", QColor("orange")),
            ("Cyan", QColor("cyan")),
        ]
        for label, color in colors:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setStyleSheet(f"""
                QPushButton {{ background-color: {color.name()}; }}
                QPushButton:checked {{ border: 2px solid white; }}
            """)
            btn.clicked.connect(lambda checked, c=color: self._select_color(c))
            self.color_buttons[color.name()] = btn
            self.content_layout.addWidget(btn)
        self.color_buttons["red"].setChecked(True)

        # Width section
        layout.addWidget(QLabel("WIDTH"))
        self.width_buttons = {}
        widths = [("Thin", 2), ("Medium", 5), ("Thick", 10)]
        for label, w in widths:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, width=w: self._select_width(width))
            self.width_buttons[w] = btn
            self.content_layout.addWidget(btn)
        self.width_buttons[2].setChecked(True)

        # Actions section
        layout.addWidget(QLabel("ACTIONS"))
        undo_btn = QPushButton("Undo (Ctrl+Z)")
        undo_btn.clicked.connect(self.undo.emit)
        self.content_layout.addWidget(undo_btn)

        redo_btn = QPushButton("Redo (Ctrl+Y)")
        redo_btn.clicked.connect(self.redo.emit)
        self.content_layout.addWidget(redo_btn)

        clear_btn = QPushButton("Clear All (F7)")
        clear_btn.clicked.connect(self.clear_all.emit)
        self.content_layout.addWidget(clear_btn)

        spotlight_btn = QPushButton("Spotlight (F10)")
        spotlight_btn.clicked.connect(lambda: self.spotlight_toggle.emit(True))
        self.content_layout.addWidget(spotlight_btn)

        layout.addLayout(self.content_layout)
        layout.addStretch()
        self.setLayout(layout)

    def _toggle_collapse(self):
        """Toggle toolbar collapse."""
        self.collapsed = not self.collapsed
        for widget in self.content_layout.parentWidget().findChildren(QWidget):
            if widget != self and widget.parent() is not self.content_layout.parentWidget():
                widget.setVisible(not self.collapsed)

    def _select_tool(self, tool: ToolType):
        """Select a drawing tool."""
        for t, btn in self.tool_buttons.items():
            btn.setChecked(t == tool)
        self.current_tool = tool
        self.tool_changed.emit(tool)

    def _select_color(self, color: QColor):
        """Select a color."""
        for name, btn in self.color_buttons.items():
            btn.setChecked(name == color.name())
        self.current_color = color
        self.color_changed.emit(color)

    def _select_width(self, width: int):
        """Select stroke width."""
        for w, btn in self.width_buttons.items():
            btn.setChecked(w == width)
        self.current_width = width
        self.width_changed.emit(width)

    def _move_to_right_edge(self):
        """Position toolbar at right edge of screen."""
        screen = QApplication.primaryScreen()
        geom = screen.geometry()
        self.move(geom.width() - self.width() - 20, 50)


# ============================================================================
# MAIN ANNOTATION OVERLAY
# ============================================================================

class AnnotationOverlay(QMainWindow):
    """Main fullscreen transparent overlay for annotations."""

    def __init__(self):
        super().__init__()

        # Window properties
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        # State
        self.annotations: List[Annotation] = []
        self.undo_stack: List[List[Annotation]] = []
        self.redo_stack: List[List[Annotation]] = []
        self.current_tool = ToolType.PEN
        self.current_color = QColor("red")
        self.current_width = 2
        self.is_drawing = False
        self.drawing_start = None
        self.current_annotation = None
        self.is_passthrough = False
        self.selected_annotation = None
        self.is_spotlight_active = False
        self.spotlight_radius = 100

        # Text input state
        self.text_input_mode = False
        self.text_input_position = None

        # Toolbar
        self.toolbar = FloatingToolbar()
        self.toolbar.tool_changed.connect(self._on_tool_changed)
        self.toolbar.color_changed.connect(self._on_color_changed)
        self.toolbar.width_changed.connect(self._on_width_changed)
        self.toolbar.clear_all.connect(self._clear_all)
        self.toolbar.undo.connect(self._undo)
        self.toolbar.redo.connect(self._redo)
        self.toolbar.spotlight_toggle.connect(self._toggle_spotlight)

        # Setup fullscreen
        self._setup_fullscreen()

        # Hotkeys
        self._setup_hotkeys()

        # Mouse tracking
        self.setMouseTracking(True)

        self.show()
        self.toolbar.show()

    def _setup_fullscreen(self):
        """Setup fullscreen overlay."""
        screen = QApplication.primaryScreen()
        geom = screen.geometry()
        self.setGeometry(geom)

    def _setup_hotkeys(self):
        """Register global hotkeys."""
        QShortcut(QKeySequence(Qt.Key.Key_F6), self, self._toggle_passthrough)
        QShortcut(QKeySequence(Qt.Key.Key_F7), self, self._clear_all)
        QShortcut(QKeySequence(Qt.Key.Key_F8), self, self._undo)
        QShortcut(QKeySequence(Qt.Modifier.CTRL + Qt.Key.Key_Z), self, self._undo)
        QShortcut(QKeySequence(Qt.Key.Key_F9), self, self._save_screenshot)
        QShortcut(QKeySequence(Qt.Modifier.CTRL + Qt.Key.Key_Y), self, self._redo)
        QShortcut(QKeySequence(Qt.Key.Key_F10), self, self._toggle_spotlight)
        QShortcut(QKeySequence(Qt.Key.Key_Escape), self, self.close)
        QShortcut(QKeySequence(Qt.Key.Key_Delete), self, self._delete_selected)

    def _toggle_passthrough(self):
        """Toggle between active and passthrough mode."""
        self.is_passthrough = not self.is_passthrough
        if self.is_passthrough:
            self.setWindowFlag(Qt.WindowType.WindowTransparentForInput, True)
        else:
            self.setWindowFlag(Qt.WindowType.WindowTransparentForInput, False)
        self.show()
        self._show_toast(f"Mode: {'Passthrough' if self.is_passthrough else 'Active'}")

    def _toggle_spotlight(self):
        """Toggle spotlight mode."""
        self.is_spotlight_active = not self.is_spotlight_active
        self.update()
        self._show_toast(f"Spotlight: {'ON' if self.is_spotlight_active else 'OFF'}")

    def _on_tool_changed(self, tool: ToolType):
        """Handle tool change from toolbar."""
        self.current_tool = tool

    def _on_color_changed(self, color: QColor):
        """Handle color change from toolbar."""
        self.current_color = color

    def _on_width_changed(self, width: int):
        """Handle width change from toolbar."""
        self.current_width = width

    def _clear_all(self):
        """Clear all annotations."""
        if self.annotations:
            self.undo_stack.append([ann for ann in self.annotations])
            self.redo_stack.clear()
            self.annotations.clear()
            self.selected_annotation = None
            self.update()

    def _undo(self):
        """Undo last annotation."""
        if self.annotations or self.undo_stack:
            self.redo_stack.append([ann for ann in self.annotations])
            if self.undo_stack:
                self.annotations = [ann for ann in self.undo_stack.pop()]
            else:
                self.annotations.clear()
            self.selected_annotation = None
            self.update()

    def _redo(self):
        """Redo last undone annotation."""
        if self.redo_stack:
            self.undo_stack.append([ann for ann in self.annotations])
            self.annotations = [ann for ann in self.redo_stack.pop()]
            self.selected_annotation = None
            self.update()

    def _delete_selected(self):
        """Delete selected annotation."""
        if self.selected_annotation and self.selected_annotation in self.annotations:
            self.undo_stack.append([ann for ann in self.annotations])
            self.redo_stack.clear()
            self.annotations.remove(self.selected_annotation)
            self.selected_annotation = None
            self.update()

    def _save_screenshot(self):
        """Save fullscreen screenshot with annotations."""
        screen = QApplication.primaryScreen()
        screenshot = screen.grabWindow(0)

        # Draw annotations onto screenshot
        painter = QPainter(screenshot)
        for ann in self.annotations:
            ann.draw(painter)
        painter.end()

        # Save to Desktop
        desktop = Path.home() / "Desktop"
        desktop.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filepath = desktop / f"linuxink_{timestamp}.png"
        screenshot.save(str(filepath))

        self._show_toast(f"Saved to Desktop")

    def _show_toast(self, message: str):
        """Show temporary notification toast."""
        # Simple implementation: print to terminal and briefly highlight
        print(f"[LinuxInk] {message}")
        # TODO: Implement visual toast in corner

    def mousePressEvent(self, event):
        """Handle mouse press."""
        if self.is_passthrough:
            super().mousePressEvent(event)
            return

        pos = Point.from_qpoint(event.pos())

        if event.button() == Qt.MouseButton.LeftButton:
            # Check if clicking on existing annotation (select mode)
            for ann in reversed(self.annotations):
                if ann.contains_point(pos):
                    self.selected_annotation = ann
                    self.update()
                    return

            # Start new annotation
            self.is_drawing = True
            self.drawing_start = pos
            self.undo_stack.append([ann for ann in self.annotations])
            self.redo_stack.clear()
            self.selected_annotation = None

            if self.current_tool == ToolType.PEN:
                self.current_annotation = PenAnnotation(
                    tool_type=ToolType.PEN,
                    color=self.current_color,
                    width=self.current_width,
                    points=[pos]
                )
            elif self.current_tool == ToolType.HIGHLIGHTER:
                self.current_annotation = HighlighterAnnotation(
                    tool_type=ToolType.HIGHLIGHTER,
                    color=self.current_color,
                    width=self.current_width,
                    points=[pos]
                )
            elif self.current_tool == ToolType.LINE:
                self.current_annotation = LineAnnotation(
                    tool_type=ToolType.LINE,
                    color=self.current_color,
                    width=self.current_width,
                    start=pos,
                    end=pos
                )
            elif self.current_tool == ToolType.RECTANGLE:
                self.current_annotation = RectangleAnnotation(
                    tool_type=ToolType.RECTANGLE,
                    color=self.current_color,
                    width=self.current_width,
                    start=pos,
                    end=pos
                )
            elif self.current_tool == ToolType.CIRCLE:
                self.current_annotation = CircleAnnotation(
                    tool_type=ToolType.CIRCLE,
                    color=self.current_color,
                    width=self.current_width,
                    start=pos,
                    end=pos
                )
            elif self.current_tool == ToolType.ARROW:
                self.current_annotation = ArrowAnnotation(
                    tool_type=ToolType.ARROW,
                    color=self.current_color,
                    width=self.current_width,
                    start=pos,
                    end=pos
                )
            elif self.current_tool == ToolType.TEXT:
                self.current_annotation = TextAnnotation(
                    tool_type=ToolType.TEXT,
                    color=self.current_color,
                    width=self.current_width,
                    position=pos,
                    text=""
                )
                self.text_input_mode = True

    def mouseMoveEvent(self, event):
        """Handle mouse move."""
        if self.is_passthrough:
            super().mouseMoveEvent(event)
            return

        if self.is_drawing and self.current_annotation:
            pos = Point.from_qpoint(event.pos())

            if isinstance(self.current_annotation, (PenAnnotation, HighlighterAnnotation)):
                self.current_annotation.points.append(pos)
            elif isinstance(self.current_annotation, (LineAnnotation, ArrowAnnotation)):
                self.current_annotation.end = pos
            elif isinstance(self.current_annotation, (RectangleAnnotation, CircleAnnotation)):
                self.current_annotation.end = pos

            self.update()

    def mouseReleaseEvent(self, event):
        """Handle mouse release."""
        if self.is_passthrough:
            super().mouseReleaseEvent(event)
            return

        if event.button() == Qt.MouseButton.LeftButton and self.is_drawing:
            if self.current_annotation:
                self.annotations.append(self.current_annotation)
            self.is_drawing = False
            self.current_annotation = None
            self.update()

    def keyPressEvent(self, event):
        """Handle key press for text input."""
        if self.text_input_mode and self.current_annotation:
            if event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
                self.annotations.append(self.current_annotation)
                self.text_input_mode = False
                self.current_annotation = None
                self.update()
            elif event.key() == Qt.Key.Key_Backspace:
                self.current_annotation.text = self.current_annotation.text[:-1]
                self.update()
            elif not event.text().isprintable() or event.text() == ' ':
                pass
            else:
                self.current_annotation.text += event.text()
                self.update()
        else:
            super().keyPressEvent(event)

    def paintEvent(self, event):
        """Paint annotations and overlay."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        # Draw spotlight if active
        if self.is_spotlight_active:
            self._draw_spotlight(painter)

        # Draw all annotations
        for ann in self.annotations:
            ann.draw(painter)

        # Draw current annotation being drawn
        if self.current_annotation:
            self.current_annotation.draw(painter)

        # Draw selection highlight
        if self.selected_annotation:
            painter.setPen(QPen(QColor(255, 255, 255, 128), 2, Qt.PenStyle.DashLine))
            if isinstance(self.selected_annotation, PenAnnotation):
                for p in self.selected_annotation.points:
                    painter.drawEllipse(p.to_qpoint(), 3, 3)

        painter.end()

    def _draw_spotlight(self, painter: QPainter):
        """Draw spotlight effect."""
        # Dark overlay
        painter.fillRect(self.rect(), QColor(0, 0, 0, 200))

        # Clear circle around cursor
        pos = self.mapFromGlobal(self.cursor().pos())
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
        painter.drawEllipse(pos, self.spotlight_radius, self.spotlight_radius)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)


# ============================================================================
# APPLICATION ENTRY POINT
# ============================================================================

def main():
    """Launch LinuxInk."""
    app = QApplication(sys.argv)
    overlay = AnnotationOverlay()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
