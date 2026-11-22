"""Vector Icon Provider for Lumination.

Draws crisp, modern Microsoft Office/Fluent-style vector icons using QPainter and QIcon.
Zero emojis, zero external file dependencies, perfectly crisp on high-DPI displays.
"""

from __future__ import annotations
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QPen, QBrush, QPolygonF, QPainterPath
from PySide6.QtCore import Qt, QPointF, QRectF


def create_undo_icon(color: str = "#334155", size: int = 24) -> QIcon:
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    pen = QPen(QColor(color), 2.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)

    path = QPainterPath()
    path.moveTo(size * 0.75, size * 0.70)
    path.cubicTo(size * 0.75, size * 0.35, size * 0.40, size * 0.35, size * 0.30, size * 0.45)
    painter.drawPath(path)

    arrow = QPainterPath()
    arrow.moveTo(size * 0.42, size * 0.32)
    arrow.lineTo(size * 0.25, size * 0.45)
    arrow.lineTo(size * 0.42, size * 0.58)
    painter.drawPath(arrow)

    painter.end()
    return QIcon(pix)


def create_redo_icon(color: str = "#334155", size: int = 24) -> QIcon:
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    pen = QPen(QColor(color), 2.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)

    path = QPainterPath()
    path.moveTo(size * 0.25, size * 0.70)
    path.cubicTo(size * 0.25, size * 0.35, size * 0.60, size * 0.35, size * 0.70, size * 0.45)
    painter.drawPath(path)

    arrow = QPainterPath()
    arrow.moveTo(size * 0.58, size * 0.32)
    arrow.lineTo(size * 0.75, size * 0.45)
    arrow.lineTo(size * 0.58, size * 0.58)
    painter.drawPath(arrow)

    painter.end()
    return QIcon(pix)


def create_add_point_icon(color: str = "#2563eb", size: int = 24) -> QIcon:
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    pen = QPen(QColor(color), 1.8)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)

    painter.drawEllipse(QRectF(size * 0.15, size * 0.15, size * 0.70, size * 0.70))
    painter.drawLine(QPointF(size * 0.5, size * 0.30), QPointF(size * 0.5, size * 0.70))
    painter.drawLine(QPointF(size * 0.30, size * 0.5), QPointF(size * 0.70, size * 0.5))

    painter.end()
    return QIcon(pix)


def create_delete_icon(color: str = "#dc2626", size: int = 24) -> QIcon:
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    pen = QPen(QColor(color), 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)

    painter.drawRect(QRectF(size * 0.28, size * 0.38, size * 0.44, size * 0.48))
    painter.drawLine(QPointF(size * 0.20, size * 0.38), QPointF(size * 0.80, size * 0.38))
    painter.drawRect(QRectF(size * 0.40, size * 0.24, size * 0.20, size * 0.14))
    painter.drawLine(QPointF(size * 0.42, size * 0.46), QPointF(size * 0.42, size * 0.76))
    painter.drawLine(QPointF(size * 0.58, size * 0.46), QPointF(size * 0.58, size * 0.76))

    painter.end()
    return QIcon(pix)


def create_zoom_in_icon(color: str = "#334155", size: int = 24) -> QIcon:
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    pen = QPen(QColor(color), 1.8)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)

    painter.drawEllipse(QRectF(size * 0.15, size * 0.15, size * 0.50, size * 0.50))
    painter.drawLine(QPointF(size * 0.55, size * 0.55), QPointF(size * 0.82, size * 0.82))
    painter.drawLine(QPointF(size * 0.40, size * 0.26), QPointF(size * 0.40, size * 0.54))
    painter.drawLine(QPointF(size * 0.26, size * 0.40), QPointF(size * 0.54, size * 0.40))

    painter.end()
    return QIcon(pix)


def create_zoom_out_icon(color: str = "#334155", size: int = 24) -> QIcon:
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    pen = QPen(QColor(color), 1.8)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)

    painter.drawEllipse(QRectF(size * 0.15, size * 0.15, size * 0.50, size * 0.50))
    painter.drawLine(QPointF(size * 0.55, size * 0.55), QPointF(size * 0.82, size * 0.82))
    painter.drawLine(QPointF(size * 0.26, size * 0.40), QPointF(size * 0.54, size * 0.40))

    painter.end()
    return QIcon(pix)


def create_reset_view_icon(color: str = "#334155", size: int = 24) -> QIcon:
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    pen = QPen(QColor(color), 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)

    painter.drawLine(QPointF(size * 0.20, size * 0.35), QPointF(size * 0.20, size * 0.20))
    painter.drawLine(QPointF(size * 0.20, size * 0.20), QPointF(size * 0.35, size * 0.20))
    painter.drawLine(QPointF(size * 0.80, size * 0.35), QPointF(size * 0.80, size * 0.20))
    painter.drawLine(QPointF(size * 0.80, size * 0.20), QPointF(size * 0.65, size * 0.20))
    painter.drawLine(QPointF(size * 0.20, size * 0.65), QPointF(size * 0.20, size * 0.80))
    painter.drawLine(QPointF(size * 0.20, size * 0.80), QPointF(size * 0.35, size * 0.80))
    painter.drawLine(QPointF(size * 0.80, size * 0.65), QPointF(size * 0.80, size * 0.80))
    painter.drawLine(QPointF(size * 0.80, size * 0.80), QPointF(size * 0.65, size * 0.80))

    painter.end()
    return QIcon(pix)


def create_center_room_icon(color: str = "#334155", size: int = 24) -> QIcon:
    """A room outline with a target in the middle: show the whole room again."""
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(QPen(QColor(color), 1.6))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawRect(QRectF(size * 0.18, size * 0.24, size * 0.64, size * 0.52))
    painter.drawEllipse(QRectF(size * 0.40, size * 0.40, size * 0.20, size * 0.20))
    painter.drawLine(QPointF(size * 0.50, size * 0.30), QPointF(size * 0.50, size * 0.38))
    painter.drawLine(QPointF(size * 0.50, size * 0.62), QPointF(size * 0.50, size * 0.70))
    painter.drawLine(QPointF(size * 0.26, size * 0.50), QPointF(size * 0.38, size * 0.50))
    painter.drawLine(QPointF(size * 0.62, size * 0.50), QPointF(size * 0.74, size * 0.50))
    painter.end()
    return QIcon(pix)


def create_zoom_cursor(zoom_in: bool):
    """Magnifier cursor with + or - for the zoom tools (hot spot in the lens centre)."""
    from PySide6.QtGui import QCursor

    size = 32
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    for color, width in (("#ffffff", 4.0), ("#0f172a", 2.0)):
        painter.setPen(QPen(QColor(color), width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(QRectF(3, 3, 18, 18))
        painter.drawLine(QPointF(18, 18), QPointF(28, 28))
        painter.drawLine(QPointF(7.5, 12), QPointF(16.5, 12))
        if zoom_in:
            painter.drawLine(QPointF(12, 7.5), QPointF(12, 16.5))
    painter.end()
    return QCursor(pix, 12, 12)


def create_chevron_left_icon(color: str = "#475569", size: int = 16) -> QIcon:
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    pen = QPen(QColor(color), 2.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)

    path = QPainterPath()
    path.moveTo(size * 0.65, size * 0.20)
    path.lineTo(size * 0.35, size * 0.50)
    path.lineTo(size * 0.65, size * 0.80)
    painter.drawPath(path)

    painter.end()
    return QIcon(pix)


def create_chevron_right_icon(color: str = "#475569", size: int = 16) -> QIcon:
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    pen = QPen(QColor(color), 2.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)

    path = QPainterPath()
    path.moveTo(size * 0.35, size * 0.20)
    path.lineTo(size * 0.65, size * 0.50)
    path.lineTo(size * 0.35, size * 0.80)
    painter.drawPath(path)

    painter.end()
    return QIcon(pix)
