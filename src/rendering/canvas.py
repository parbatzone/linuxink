"""
DrawingCanvas - transparent drawing surface with full annotation tools
"""

import math
from PyQt6.QtWidgets import QWidget, QInputDialog
from PyQt6.QtCore import Qt, QPointF, QRectF, pyqtSignal, QTimer
from PyQt6.QtGui import (
    QPainter, QPen, QColor, QBrush, QPixmap,
    QPainterPath, QFont, QTabletEvent, QPaintEvent
)


class Stroke:
    """Represents a single drawing operation"""
    def __init__(self, tool, color, size, opacity, points=None,
                 text=None, font_size=16):
        self.tool = tool
        self.color = QColor(color)
        self.size = size
        self.opacity = opacity
        self.points = points or []
        self.text = text
        self.font_size = font_size


class DrawingCanvas(QWidget):
    history_changed = pyqtSignal(bool, bool)  # can_undo, can_redo

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.setAttribute(Qt.WidgetAttribute.WA_AcceptTouchEvents, True)

        self.current_tool = "pen"
        self.current_color = QColor("#FF0000")
        self.brush_size = 4
        self.opacity = 1.0

        self._drawing = False
        self._current_stroke = None
        self._start_point = QPointF()
        self._last_point = QPointF()
        self._preview_end = QPointF()

        self._strokes = []
        self._redo_stack = []

        self._buffer = None

        self._tablet_pressure = 1.0

        self._laser_timer = QTimer()
        self._laser_timer.timeout.connect(self._hide_laser)
        self._laser_visible = False
        self._laser_pos = QPointF()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._init_buffer()

    def _init_buffer(self):
        self._buffer = QPixmap(self.size())
        self._buffer.fill(Qt.GlobalColor.transparent)
        self._redraw_buffer()

    def _redraw_buffer(self):
        if self._buffer is None:
            return
        self._buffer.fill(Qt.GlobalColor.transparent)
        painter = QPainter(self._buffer)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        for stroke in self._strokes:
            self._paint_stroke(painter, stroke)
        painter.end()

    # ── Tool API ─────────────────────────────────────────────────────────────

    def set_tool(self, tool: str):
        self.current_tool = tool

    def set_color(self, color: str):
        self.current_color = QColor(color)

    def set_brush_size(self, size: int):
        self.brush_size = size

    def set_opacity(self, opacity: float):
        self.opacity = opacity

    def undo(self):
        if self._strokes:
            self._redo_stack.append(self._strokes.pop())
            self._redraw_buffer()
            self.update()
            self._emit_history()

    def redo(self):
        if self._redo_stack:
            self._strokes.append(self._redo_stack.pop())
            self._redraw_buffer()
            self.update()
            self._emit_history()

    def clear_all(self):
        if self._strokes:
            self._redo_stack.clear()
            self._strokes.clear()
            self._redraw_buffer()
            self.update()
            self._emit_history()

    def get_flat_image(self) -> QPixmap:
        if self._buffer:
            return self._buffer.copy()
        return QPixmap(self.size())

    def _emit_history(self):
        self.history_changed.emit(bool(self._strokes), bool(self._redo_stack))

    # ── Mouse / Tablet Events ─────────────────────────────────────────────────

    def tabletEvent(self, event: QTabletEvent):
        self._tablet_pressure = event.pressure()
        pos = QPointF(event.position())
        if event.type() == QTabletEvent.Type.TabletPress:
            self._begin_stroke(pos)
        elif event.type() == QTabletEvent.Type.TabletMove:
            self._continue_stroke(pos)
        elif event.type() == QTabletEvent.Type.TabletRelease:
            self._end_stroke(pos)
        event.accept()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._begin_stroke(QPointF(event.position()))

    def mouseMoveEvent(self, event):
        if self.current_tool == "laser":
            self._laser_pos = QPointF(event.position())
            self._laser_visible = True
            self._laser_timer.start(600)
            self.update()
        elif self._drawing:
            self._continue_stroke(QPointF(event.position()))

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._drawing:
            self._end_stroke(QPointF(event.position()))

    # ── Stroke lifecycle ──────────────────────────────────────────────────────

    def _begin_stroke(self, pos: QPointF):
        if self.current_tool == "text":
            self._place_text(pos)
            return
        if self.current_tool == "laser":
            return
        self._drawing = True
        self._start_point = pos
        self._last_point = pos
        self._preview_end = pos
        self._current_stroke = Stroke(
            tool=self.current_tool,
            color=self.current_color.name(),
            size=self._effective_size(),
            opacity=self.opacity,
            points=[pos],
        )
        self._redo_stack.clear()

    def _continue_stroke(self, pos: QPointF):
        if not self._drawing or not self._current_stroke:
            return
        self._preview_end = pos
        if self.current_tool in ("pen", "highlighter", "eraser"):
            self._current_stroke.points.append(pos)
            self._paint_incremental(self._last_point, pos)
        self._last_point = pos
        self.update()

    def _end_stroke(self, pos: QPointF):
        if not self._drawing or not self._current_stroke:
            return
        self._drawing = False
        self._preview_end = pos

        shape_tools = ("line", "rectangle", "circle", "arrow", "triangle", "star")
        if self.current_tool in shape_tools:
            self._current_stroke.points = [self._start_point, pos]
            painter = QPainter(self._buffer)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            self._paint_stroke(painter, self._current_stroke)
            painter.end()

        self._strokes.append(self._current_stroke)
        self._current_stroke = None
        self.update()
        self._emit_history()

    def _place_text(self, pos: QPointF):
        text, ok = QInputDialog.getText(self, "Add Text", "Enter text:")
        if ok and text:
            stroke = Stroke(
                tool="text",
                color=self.current_color.name(),
                size=self.brush_size,
                opacity=self.opacity,
                points=[pos],
                text=text,
                font_size=max(12, self.brush_size * 3),
            )
            self._strokes.append(stroke)
            self._redo_stack.clear()
            painter = QPainter(self._buffer)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            self._paint_stroke(painter, stroke)
            painter.end()
            self.update()
            self._emit_history()

    def _effective_size(self) -> int:
        p = self._tablet_pressure if self._tablet_pressure > 0 else 1.0
        return max(1, int(self.brush_size * p))

    # ── Painting ──────────────────────────────────────────────────────────────

    def _paint_incremental(self, p1: QPointF, p2: QPointF):
        if self._buffer is None:
            return
        stroke = self._current_stroke
        painter = QPainter(self._buffer)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._apply_pen(painter, stroke)
        if stroke.tool == "eraser":
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
            pen = QPen(Qt.GlobalColor.transparent, stroke.size,
                       Qt.PenStyle.SolidLine,
                       Qt.PenCapStyle.RoundCap,
                       Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
        painter.drawLine(p1, p2)
        painter.end()

    def _paint_stroke(self, painter: QPainter, stroke: Stroke):
        self._apply_pen(painter, stroke)

        if stroke.tool == "eraser":
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
            pen = QPen(Qt.GlobalColor.transparent, stroke.size,
                       Qt.PenStyle.SolidLine,
                       Qt.PenCapStyle.RoundCap,
                       Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
        elif stroke.tool == "highlighter":
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)

        if stroke.tool in ("pen", "highlighter", "eraser"):
            pts = stroke.points
            if len(pts) >= 2:
                path = QPainterPath()
                path.moveTo(pts[0])
                if len(pts) == 2:
                    path.lineTo(pts[1])
                else:
                    for i in range(1, len(pts) - 1):
                        mid = (pts[i] + pts[i + 1]) / 2
                        path.quadTo(pts[i], mid)
                    path.lineTo(pts[-1])
                painter.drawPath(path)
            elif len(pts) == 1:
                r = stroke.size / 2
                painter.drawEllipse(pts[0], r, r)

        elif stroke.tool == "line" and len(stroke.points) >= 2:
            painter.drawLine(stroke.points[0], stroke.points[-1])

        elif stroke.tool == "rectangle" and len(stroke.points) >= 2:
            painter.setBrush(Qt.BrushStyle.NoBrush)
            rect = QRectF(stroke.points[0], stroke.points[-1]).normalized()
            painter.drawRect(rect)

        elif stroke.tool == "circle" and len(stroke.points) >= 2:
            painter.setBrush(Qt.BrushStyle.NoBrush)
            rect = QRectF(stroke.points[0], stroke.points[-1]).normalized()
            painter.drawEllipse(rect)

        elif stroke.tool == "triangle" and len(stroke.points) >= 2:
            self._draw_triangle(painter, stroke.points[0], stroke.points[-1])

        elif stroke.tool == "star" and len(stroke.points) >= 2:
            self._draw_star(painter, stroke.points[0], stroke.points[-1])

        elif stroke.tool == "arrow" and len(stroke.points) >= 2:
            self._draw_arrow(painter, stroke.points[0], stroke.points[-1])

        elif stroke.tool == "text" and stroke.text:
            color = QColor(stroke.color)
            color.setAlphaF(stroke.opacity)
            painter.setPen(color)
            font = QFont("Sans Serif", stroke.font_size)
            font.setBold(True)
            painter.setFont(font)
            painter.drawText(stroke.points[0], stroke.text)

        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)

    def _apply_pen(self, painter: QPainter, stroke: Stroke):
        color = QColor(stroke.color)
        if stroke.tool == "highlighter":
            color.setAlphaF(min(stroke.opacity * 0.45, 0.45))
        else:
            color.setAlphaF(stroke.opacity)
        pen = QPen(color, stroke.size,
                   Qt.PenStyle.SolidLine,
                   Qt.PenCapStyle.RoundCap,
                   Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    def _draw_triangle(self, painter: QPainter, p1: QPointF, p2: QPointF):
        """Draw a triangle from bounding box (p1=top-left, p2=bottom-right)"""
        painter.setBrush(Qt.BrushStyle.NoBrush)
        # Top-center, bottom-left, bottom-right
        top   = QPointF((p1.x() + p2.x()) / 2, p1.y())
        bot_l = QPointF(p1.x(), p2.y())
        bot_r = QPointF(p2.x(), p2.y())
        path = QPainterPath()
        path.moveTo(top)
        path.lineTo(bot_l)
        path.lineTo(bot_r)
        path.closeSubpath()
        painter.drawPath(path)

    def _draw_star(self, painter: QPainter, p1: QPointF, p2: QPointF):
        """Draw a 5-pointed star inside the bounding box"""
        painter.setBrush(Qt.BrushStyle.NoBrush)
        cx = (p1.x() + p2.x()) / 2
        cy = (p1.y() + p2.y()) / 2
        r_outer = max(abs(p2.x() - p1.x()), abs(p2.y() - p1.y())) / 2
        r_inner = r_outer * 0.4
        path = QPainterPath()
        for i in range(10):
            angle = math.pi / 2 + i * math.pi / 5
            r = r_outer if i % 2 == 0 else r_inner
            x = cx + r * math.cos(angle)
            y = cy - r * math.sin(angle)
            pt = QPointF(x, y)
            if i == 0:
                path.moveTo(pt)
            else:
                path.lineTo(pt)
        path.closeSubpath()
        painter.drawPath(path)

    def _draw_arrow(self, painter: QPainter, p1: QPointF, p2: QPointF):
        painter.drawLine(p1, p2)
        dx = p2.x() - p1.x()
        dy = p2.y() - p1.y()
        length = math.hypot(dx, dy)
        if length < 1:
            return
        ux, uy = dx / length, dy / length
        head = 18 + painter.pen().width() * 2
        angle = 0.4
        ax1 = p2.x() - head * (ux * math.cos(angle) + uy * math.sin(angle))
        ay1 = p2.y() - head * (uy * math.cos(angle) - ux * math.sin(angle))
        ax2 = p2.x() - head * (ux * math.cos(-angle) + uy * math.sin(-angle))
        ay2 = p2.y() - head * (uy * math.cos(-angle) - ux * math.sin(-angle))
        painter.drawLine(p2, QPointF(ax1, ay1))
        painter.drawLine(p2, QPointF(ax2, ay2))

    def _hide_laser(self):
        self._laser_visible = False
        self._laser_timer.stop()
        self.update()

    def paintEvent(self, event: QPaintEvent):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if self._buffer:
            painter.drawPixmap(0, 0, self._buffer)

        # Live shape preview
        shape_tools = ("line", "rectangle", "circle", "arrow", "triangle", "star")
        if self._drawing and self._current_stroke and self.current_tool in shape_tools:
            preview = Stroke(
                tool=self.current_tool,
                color=self.current_color.name(),
                size=self.brush_size,
                opacity=self.opacity * 0.65,
                points=[self._start_point, self._preview_end],
            )
            self._paint_stroke(painter, preview)

        # Laser pointer
        if self._laser_visible and self.current_tool == "laser":
            glow = QColor(self.current_color)
            glow.setAlphaF(0.2)
            painter.setBrush(glow)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(self._laser_pos, 22, 22)
            painter.setBrush(self.current_color)
            painter.drawEllipse(self._laser_pos, 8, 8)

        painter.end()
