"""Interactive 2D Room Plan & Illuminance Canvas Widget.

Features:
- Edge-to-edge drawing covering 100% of the main canvas
- Compact, icon-only action bar (Microsoft Office/Excel aesthetic, zero emojis)
- In-place floating popup tag for instant clicking and editing lux values with consecutive Enter-to-advance
- Hover inspection showing clean lux reading & coordinates (no P1/P2 clutter)
- Keyboard shortcuts: Backspace/Delete to remove, Ctrl+Z/Ctrl+Y for Undo/Redo
- Smart placement mode with room dimension guides and symmetry snapping
"""

from __future__ import annotations
import math
from typing import Optional, Tuple, Dict, Any, List
import numpy as np
from PySide6.QtCore import Qt, Signal, QPoint, QPointF, QLocale, QEvent
from PySide6.QtGui import QCursor, QKeySequence, QAction
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QLineEdit,
    QFrame,
    QToolTip,
    QSizePolicy,
)

import matplotlib
matplotlib.use("QtAgg")
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg

from models.project import LuminationProject
from models.measurement import MeasurementPoint
from analysis.interpolation import InterpolationResult
from visualization.map_plotter import render_room_map
from ui.icons import (
    create_undo_icon,
    create_redo_icon,
    create_add_point_icon,
    create_delete_icon,
    create_zoom_in_icon,
    create_zoom_out_icon,
    create_reset_view_icon,
    create_center_room_icon,
    create_zoom_cursor,
)
from i18n.translations import tr, TranslationManager


class PointPopupEditor(QFrame):
    """Sleek in-place floating popup tag for entering/modifying lux readings directly on a point."""
    value_submitted = Signal(str, float)  # point_id, lux
    closed = Signal()
    dismissed = Signal()  # the field lost focus without a value being entered

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.point_id: Optional[str] = None

        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet("""
            PointPopupEditor {
                background-color: #ffffff;
                border: 1.5px solid #0f172a;
                border-radius: 4px;
                padding: 2px 4px;
            }
            QLineEdit {
                border: 1px solid #cbd5e1;
                border-radius: 2px;
                padding: 2px 4px;
                font-size: 11px;
                font-weight: bold;
                color: #0f172a;
                background-color: #f8fafc;
            }
            QLineEdit:focus {
                border: 1px solid #2563eb;
                background-color: #ffffff;
            }
            QLabel {
                font-size: 10px;
                font-weight: 600;
                color: #475569;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(3, 2, 3, 2)
        layout.setSpacing(3)

        self.txt_lux = QLineEdit(self)
        self.txt_lux.setPlaceholderText("Lux")
        self.txt_lux.setMaximumWidth(75)
        self.txt_lux.returnPressed.connect(self._submit)
        self.txt_lux.installEventFilter(self)

        lbl_suffix = QLabel("lx", self)

        layout.addWidget(self.txt_lux)
        layout.addWidget(lbl_suffix)

        self.hide()

    def show_for_point(self, point: MeasurementPoint, screen_pos: QPoint) -> None:
        """Position popup editor directly above the clicked point."""
        self.point_id = point.id
        locale = QLocale({"en": "en_US", "ro": "ro_RO", "de": "de_DE"}[TranslationManager.get_instance().current_language])
        locale.setNumberOptions(QLocale.NumberOption.OmitGroupSeparator | QLocale.NumberOption.RejectGroupSeparator)
        self.txt_lux.setLocale(locale)
        cur_val = locale.toString(point.lux, 'g', 17) if point.lux is not None else ""
        self.txt_lux.setText(cur_val)
        self.adjustSize()

        # Center popup above the point
        x = max(10, screen_pos.x() - self.width() // 2)
        y = max(10, screen_pos.y() - self.height() - 6)
        self.move(x, y)
        self.show()
        self.raise_()
        self.txt_lux.setFocus()
        self.txt_lux.selectAll()

    def eventFilter(self, watched, event) -> bool:
        if watched is self.txt_lux and event.type() == QEvent.Type.FocusOut and self.isVisible():
            # Clicking anywhere else closes the box and keeps the point's previous value.
            if event.reason() not in (Qt.FocusReason.ActiveWindowFocusReason, Qt.FocusReason.PopupFocusReason):
                self.hide()
                self.dismissed.emit()
        return super().eventFilter(watched, event)

    def _submit(self) -> None:
        """Submit the entered lux value and notify canvas."""
        text = self.txt_lux.text().strip()
        if self.point_id:
            try:
                val, valid = self.txt_lux.locale().toDouble(text)
                if valid and math.isfinite(val) and val >= 0:
                    self.value_submitted.emit(self.point_id, val)
            except ValueError:
                pass


class RoomCanvasWidget(QWidget):
    """Interactive room canvas widget with compact icon toolbar, hover tooltips, and in-place point editor."""

    point_selected = Signal(str)
    point_deselected = Signal()
    point_edit_requested = Signal(str)
    point_add_requested = Signal(float, float)
    point_delete_requested = Signal(str)
    measurement_saved = Signal(str, float)
    cursor_position_changed = Signal(float, float)
    undo_requested = Signal()
    redo_requested = Signal()
    fullscreen_requested = Signal()

    ZOOM_STEP = 1.5  # each click with a zoom tool

    def __init__(self, parent: Optional[QWidget] = None, show_fullscreen_button: bool = True,
                 show_colorbar: bool = True) -> None:
        super().__init__(parent)
        self.active_tool: Optional[str] = None  # None, "zoom_in", "zoom_out" or "add_point"

        self.project: Optional[LuminationProject] = None
        self.interp_result: Optional[InterpolationResult] = None
        self.selected_point_id: Optional[str] = None
        self.placement_mode: bool = False
        self.editing_enabled: bool = False
        self.recording_enabled: bool = True
        self._view_room_key = None

        # Placement snapping state
        self._preview_pos: Optional[Tuple[float, float]] = None
        self._snapped_pos: Optional[Tuple[float, float]] = None
        self._snap_guides: List[Tuple[Tuple[float, float], Tuple[float, float]]] = []
        self._snap_label: Optional[str] = None

        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        # 1. Matplotlib Figure & Canvas (maximizes graph edge-to-edge)
        self.figure = Figure(figsize=(10, 7), dpi=100, facecolor="#f8fafc")
        self.figure.subplots_adjust(left=0.04, right=0.96, top=0.96, bottom=0.06)

        self.ax = self.figure.add_subplot(1, 1, 1)
        # Colour bar on the right of the map: colours from the lowest to the highest value.
        self.cax = None
        if show_colorbar:
            from mpl_toolkits.axes_grid1 import make_axes_locatable

            self.cax = make_axes_locatable(self.ax).append_axes("right", size="3.5%", pad=0.35)
            self.cax.set_visible(False)

        self.canvas = FigureCanvasQTAgg(self.figure)
        self.canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.canvas.setMouseTracking(True)

        self.canvas.mpl_connect("button_press_event", self._on_mouse_click)
        self.canvas.mpl_connect("motion_notify_event", self._on_mouse_motion)
        self.canvas.mpl_connect("scroll_event", self._on_scroll)
        self.canvas.mpl_connect("axes_leave_event", self._on_axes_leave)

        # 2. In-Place Floating Popup Editor
        self.popup_editor = PointPopupEditor(self)
        self.popup_editor.value_submitted.connect(self._on_popup_value_submitted)
        self.popup_editor.dismissed.connect(self.deselect)

        # 3. Compact Icon-Only Action Bar (Microsoft Office style)
        self.action_bar = QFrame(self)
        self.action_bar.setObjectName("mapActionBar")
        self.action_bar.setFixedHeight(32)
        self.action_bar.setStyleSheet("""
            QFrame#mapActionBar {
                background-color: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 4px;
                padding: 1px 4px;
            }
            QPushButton {
                background-color: transparent;
                border: 1px solid transparent;
                border-radius: 3px;
                padding: 2px 4px;
                min-width: 24px;
                max-width: 24px;
                min-height: 22px;
                max-height: 22px;
            }
            QPushButton:hover {
                background-color: #f1f5f9;
                border-color: #cbd5e1;
            }
            QPushButton:pressed {
                background-color: #e2e8f0;
            }
            QPushButton:checked {
                background-color: #dbeafe;
                border-color: #3b82f6;
            }
            QPushButton#doneButton {
                min-width: 44px;
                max-width: 120px;
                font-size: 11px;
                font-weight: 600;
                color: #1d4ed8;
                border-color: #93c5fd;
            }
            QPushButton#doneButton:disabled {
                color: #94a3b8;
                border-color: #e2e8f0;
            }
        """)

        bar_layout = QHBoxLayout(self.action_bar)
        bar_layout.setContentsMargins(2, 2, 2, 2)
        bar_layout.setSpacing(3)

        # Undo / Redo
        self.btn_undo = QPushButton(self)
        self.btn_undo.setIcon(create_undo_icon())
        self.btn_undo.clicked.connect(self.undo_requested.emit)

        self.btn_redo = QPushButton(self)
        self.btn_redo.setIcon(create_redo_icon())
        self.btn_redo.clicked.connect(self.redo_requested.emit)

        # Add / Done / Delete
        self.btn_add_point = QPushButton(self)
        self.btn_add_point.setIcon(create_add_point_icon())
        self.btn_add_point.setCheckable(True)
        self.btn_add_point.clicked.connect(lambda checked: self.set_tool("add_point" if checked else None))

        # "Done" ends Add point; it can only be pressed while Add point is on.
        self.btn_done = QPushButton(self)
        self.btn_done.setObjectName("doneButton")
        self.btn_done.setEnabled(False)
        self.btn_done.clicked.connect(lambda: self.set_tool(None))

        self.btn_delete_point = QPushButton(self)
        self.btn_delete_point.setIcon(create_delete_icon())
        self.btn_delete_point.clicked.connect(self._delete_selected_point)

        # Zoom tools: switch one on, then click the map where you want to zoom.
        self.btn_zoom_in = QPushButton(self)
        self.btn_zoom_in.setIcon(create_zoom_in_icon())
        self.btn_zoom_in.setCheckable(True)
        self.btn_zoom_in.clicked.connect(lambda checked: self.set_tool("zoom_in" if checked else None))

        self.btn_zoom_out = QPushButton(self)
        self.btn_zoom_out.setIcon(create_zoom_out_icon())
        self.btn_zoom_out.setCheckable(True)
        self.btn_zoom_out.clicked.connect(lambda checked: self.set_tool("zoom_out" if checked else None))

        # Center room: show the whole room again.
        self.btn_reset_view = QPushButton(self)
        self.btn_reset_view.setIcon(create_center_room_icon())
        self.btn_reset_view.clicked.connect(self.reset_view)
        self.btn_center_room = self.btn_reset_view

        # Full screen: the graph alone in a large window.
        self.btn_fullscreen = QPushButton(self)
        self.btn_fullscreen.setIcon(create_reset_view_icon())
        self.btn_fullscreen.clicked.connect(self.fullscreen_requested.emit)
        self.btn_fullscreen.setVisible(show_fullscreen_button)
        self._zoom_in_cursor = create_zoom_cursor(True)
        self._zoom_out_cursor = create_zoom_cursor(False)

        self._apply_tooltips()
        TranslationManager.get_instance().language_changed.connect(self._on_language_changed)
        # Toolbar labels appear as soon as the mouse is over a tool (no tooltip delay).
        self._toolbar_buttons = (
            self.btn_undo, self.btn_redo, self.btn_add_point, self.btn_done, self.btn_delete_point,
            self.btn_zoom_in, self.btn_zoom_out, self.btn_reset_view, self.btn_fullscreen,
        )
        for button in self._toolbar_buttons:
            button.installEventFilter(self)

        # Compact status label
        self.lbl_cursor_status = QLabel("", self)
        self.lbl_cursor_status.setStyleSheet("font-size: 11px; color: #64748b; font-weight: 500; padding: 0 6px;")

        bar_layout.addWidget(self.btn_undo)
        bar_layout.addWidget(self.btn_redo)
        bar_layout.addSpacing(6)
        bar_layout.addWidget(self.btn_add_point)
        bar_layout.addWidget(self.btn_done)
        bar_layout.addWidget(self.btn_delete_point)
        bar_layout.addSpacing(6)
        bar_layout.addWidget(self.btn_zoom_in)
        bar_layout.addWidget(self.btn_zoom_out)
        bar_layout.addWidget(self.btn_reset_view)
        bar_layout.addWidget(self.btn_fullscreen)
        bar_layout.addStretch()
        bar_layout.addWidget(self.lbl_cursor_status)

        # Assembly
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(2, 2, 2, 2)
        main_layout.setSpacing(2)
        main_layout.addWidget(self.action_bar)
        main_layout.addWidget(self.canvas, stretch=1)

    def eventFilter(self, watched, event) -> bool:
        """Show a toolbar button's label immediately when the mouse enters it."""
        if watched in getattr(self, "_toolbar_buttons", ()) and event.type() == QEvent.Type.Enter:
            tip = watched.toolTip()
            if tip:
                QToolTip.showText(watched.mapToGlobal(QPoint(0, watched.height() + 2)), tip, watched)
        return super().eventFilter(watched, event)

    def _apply_tooltips(self) -> None:
        self.btn_undo.setToolTip(tr("canvas_tip_undo", key=QKeySequence(QKeySequence.StandardKey.Undo).toString(QKeySequence.SequenceFormat.NativeText)))
        self.btn_redo.setToolTip(tr("canvas_tip_redo", key=QKeySequence(QKeySequence.StandardKey.Redo).toString(QKeySequence.SequenceFormat.NativeText)))
        self.btn_add_point.setToolTip(tr("canvas_tip_add_point"))
        self.btn_delete_point.setToolTip(tr("canvas_tip_delete_point"))
        self.btn_zoom_in.setToolTip(tr("canvas_tip_zoom_in"))
        self.btn_zoom_out.setToolTip(tr("canvas_tip_zoom_out"))
        self.btn_reset_view.setToolTip(tr("canvas_tip_center_room"))
        self.btn_fullscreen.setToolTip(tr("canvas_tip_fullscreen"))
        self.btn_done.setText(tr("canvas_done"))
        self.btn_done.setToolTip(tr("canvas_tip_done"))
        self.popup_editor.txt_lux.setPlaceholderText(tr("canvas_tooltip_lux"))

    def _on_language_changed(self, *_args) -> None:
        self._apply_tooltips()
        self.lbl_cursor_status.clear()
        if self.project:
            self.redraw()

    def set_project(
        self,
        project: LuminationProject,
        interp_result: Optional[InterpolationResult] = None,
        selected_point_id: Optional[str] = None,
    ) -> None:
        """Set project and render map."""
        self.project = project
        self.interp_result = interp_result
        self.selected_point_id = selected_point_id
        self.btn_delete_point.setEnabled(self.editing_enabled and selected_point_id is not None)
        self.redraw()

    def set_selected_point_id(self, point_id: Optional[str]) -> None:
        """Update active selection and refresh."""
        self.selected_point_id = point_id
        self.btn_delete_point.setEnabled(self.editing_enabled and point_id is not None)
        self.redraw()

    def set_editing_enabled(self, enabled: bool) -> None:
        self.editing_enabled = enabled
        self.btn_add_point.setEnabled(enabled)
        self.btn_delete_point.setEnabled(enabled and self.selected_point_id is not None)
        if not enabled and self.placement_mode:
            self.set_tool(None)

    def set_recording_enabled(self, enabled: bool) -> None:
        self.recording_enabled = enabled
        if not enabled:
            self.popup_editor.hide()

    def set_tool(self, tool: Optional[str]) -> None:
        """Switch on one map tool (zoom in, zoom out or add point), or none; only one at a time."""
        if tool == "add_point" and not self.editing_enabled:
            tool = None
        was_placing = self.placement_mode
        self.active_tool = tool
        self.placement_mode = tool == "add_point"
        self.btn_add_point.setChecked(tool == "add_point")
        self.btn_zoom_in.setChecked(tool == "zoom_in")
        self.btn_zoom_out.setChecked(tool == "zoom_out")
        self.btn_done.setEnabled(tool == "add_point")
        self.popup_editor.hide()
        cursor = {
            "zoom_in": self._zoom_in_cursor,
            "zoom_out": self._zoom_out_cursor,
            "add_point": QCursor(Qt.CursorShape.CrossCursor),
        }.get(tool)
        if cursor is not None:
            self.canvas.setCursor(cursor)
        else:
            self.canvas.unsetCursor()
        if not self.placement_mode:
            self._preview_pos = None
            self._snapped_pos = None
            self._snap_guides = []
            self._snap_label = None
        if was_placing != self.placement_mode:
            self.redraw()

    def set_placement_mode(self, enabled: bool) -> None:
        """Turn the Add point tool on or off (it stays on until Done)."""
        self.set_tool("add_point" if enabled else None)

    def zoom_at(self, x: float, y: float, factor: float) -> None:
        """Zoom by `factor` (>1 in, <1 out) keeping the clicked map position under the cursor."""
        xlim = self.ax.get_xlim()
        ylim = self.ax.get_ylim()
        new_w = (xlim[1] - xlim[0]) / factor
        new_h = (ylim[1] - ylim[0]) / factor
        rel_x = (x - xlim[0]) / (xlim[1] - xlim[0])
        rel_y = (y - ylim[0]) / (ylim[1] - ylim[0])
        self.ax.set_xlim(x - rel_x * new_w, x + (1 - rel_x) * new_w)
        self.ax.set_ylim(y - rel_y * new_h, y + (1 - rel_y) * new_h)
        self.canvas.draw_idle()

    def reset_view(self) -> None:
        """Center room: show the whole room again."""
        if not self.project:
            return
        r = self.project.room
        margin_offset = max(0.20, min(r.length, r.width) * 0.04)
        self.ax.set_xlim(-margin_offset, r.length + margin_offset)
        self.ax.set_ylim(-margin_offset, r.width + margin_offset)
        self.canvas.draw_idle()

    def _zoom(self, factor: float) -> None:
        """Zoom in or out around current view center."""
        xlim = self.ax.get_xlim()
        ylim = self.ax.get_ylim()
        cx = (xlim[0] + xlim[1]) / 2.0
        cy = (ylim[0] + ylim[1]) / 2.0
        new_w = (xlim[1] - xlim[0]) / factor
        new_h = (ylim[1] - ylim[0]) / factor
        self.ax.set_xlim(cx - new_w / 2.0, cx + new_w / 2.0)
        self.ax.set_ylim(cy - new_h / 2.0, cy + new_h / 2.0)
        self.canvas.draw_idle()

    def _delete_selected_point(self) -> None:
        if self.selected_point_id:
            self.popup_editor.hide()
            self.point_delete_requested.emit(self.selected_point_id)

    def keyPressEvent(self, event) -> None:
        """Handle keyboard shortcuts: Backspace/Delete to remove, Undo/Redo."""
        if event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            if self.selected_point_id and not self.popup_editor.isVisible():
                self.point_delete_requested.emit(self.selected_point_id)
                event.accept()
                return
        elif event.matches(QKeySequence.StandardKey.Undo):
            self.undo_requested.emit()
            event.accept()
            return
        elif event.matches(QKeySequence.StandardKey.Redo):
            self.redo_requested.emit()
            event.accept()
            return
        elif event.key() == Qt.Key.Key_Escape:
            if self.placement_mode:
                self.set_tool(None)
            self.popup_editor.hide()
            event.accept()
            return

        super().keyPressEvent(event)

    def _on_scroll(self, event) -> None:
        """Mouse wheel zoom centered on cursor position."""
        if event.xdata is None or event.ydata is None:
            return
        factor = 1.15 if event.button == "up" else 0.87
        xlim = self.ax.get_xlim()
        ylim = self.ax.get_ylim()
        x, y = event.xdata, event.ydata
        new_w = (xlim[1] - xlim[0]) / factor
        new_h = (ylim[1] - ylim[0]) / factor
        rel_x = (x - xlim[0]) / (xlim[1] - xlim[0])
        rel_y = (y - ylim[0]) / (ylim[1] - ylim[0])
        self.ax.set_xlim(x - rel_x * new_w, x + (1 - rel_x) * new_w)
        self.ax.set_ylim(y - rel_y * new_h, y + (1 - rel_y) * new_h)
        self.canvas.draw_idle()

    def _on_mouse_motion(self, event) -> None:
        """Handle interactive hover tooltip and placement symmetry snapping."""
        if event.xdata is None or event.ydata is None or not self.project:
            return

        rx, ry = float(event.xdata), float(event.ydata)
        self.cursor_position_changed.emit(rx, ry)

        room = self.project.room
        if not room.is_inside(rx, ry):
            self.lbl_cursor_status.setText(f"{rx:.2f} m, {ry:.2f} m")
            return

        # 1. Placement Mode Snapping
        if self.placement_mode:
            self._calculate_snapping(rx, ry)
            active_x, active_y = self._snapped_pos or (rx, ry)
            self.lbl_cursor_status.setText(
                f"X: {active_x:.2f} m, Y: {active_y:.2f} m {self._snap_label or ''}"
            )
            self.redraw()
            return

        # 2. Normal Mode Hover Inspection (Clean lux & coordinates, NO P1/P2 prefix)
        nearest_pt = self._find_nearest_point(rx, ry)
        if nearest_pt:
            val_str = f"{nearest_pt.lux:.1f} lx" if nearest_pt.is_measured and nearest_pt.lux is not None else tr("canvas_unmeasured")
            self.lbl_cursor_status.setText(
                f"{val_str} (X: {nearest_pt.x:.2f} m, Y: {nearest_pt.y:.2f} m)"
            )
            QToolTip.showText(
                QCursor.pos(),
                f"<b>{val_str}</b><br>({nearest_pt.x:.2f}, {nearest_pt.y:.2f}) m",
                self.canvas,
            )
            return

        # 3. Sample interpolated raster under cursor
        est_lux = self._sample_interpolated_lux(rx, ry)
        if est_lux is not None:
            self.lbl_cursor_status.setText(
                tr("canvas_estimated", lux=f"{est_lux:.1f}", x=f"{rx:.2f}", y=f"{ry:.2f}")
            )
        else:
            self.lbl_cursor_status.setText(f"X: {rx:.2f} m, Y: {ry:.2f} m")

    def _calculate_snapping(self, rx: float, ry: float) -> None:
        """Calculate snapping to room centerlines and symmetry opposite of existing points."""
        room = self.project.room
        snap_threshold = 0.20

        snapped_x = rx
        snapped_y = ry
        self._snap_guides = []
        snap_reasons = []

        # Room Centerlines
        cx = room.length / 2.0
        cy = room.width / 2.0
        if abs(rx - cx) <= snap_threshold:
            snapped_x = cx
            self._snap_guides.append(((cx, 0), (cx, room.width)))
            snap_reasons.append(tr("canvas_snap_center_x"))
        if abs(ry - cy) <= snap_threshold:
            snapped_y = cy
            self._snap_guides.append(((0, cy), (room.length, cy)))
            snap_reasons.append(tr("canvas_snap_center_y"))

        # Symmetry / Mirror of other points
        for p in self.project.points:
            sym_x = room.length - p.x
            sym_y = room.width - p.y

            if math.hypot(rx - sym_x, ry - sym_y) <= snap_threshold:
                snapped_x = sym_x
                snapped_y = sym_y
                self._snap_guides.append(((p.x, p.y), (sym_x, sym_y)))
                snap_reasons.append(tr("canvas_snap_symmetry"))
                break
            elif math.hypot(rx - sym_x, ry - p.y) <= snap_threshold:
                snapped_x = sym_x
                snapped_y = p.y
                self._snap_guides.append(((p.x, p.y), (sym_x, p.y)))
                snap_reasons.append(tr("canvas_snap_h_mirror"))
                break
            elif math.hypot(rx - p.x, ry - sym_y) <= snap_threshold:
                snapped_x = p.x
                snapped_y = sym_y
                self._snap_guides.append(((p.x, p.y), (p.x, sym_y)))
                snap_reasons.append(tr("canvas_snap_v_mirror"))
                break

        self._preview_pos = (rx, ry)
        if snap_reasons:
            self._snapped_pos = (round(snapped_x, 3), round(snapped_y, 3))
            self._snap_label = f"[{' + '.join(snap_reasons)}]"
        else:
            self._snapped_pos = None
            self._snap_label = None

    def _sample_interpolated_lux(self, x: float, y: float) -> Optional[float]:
        """Sample 2D interpolated raster value at (x, y)."""
        if self.interp_result is None or self.interp_result.grid_z is None:
            return None
        gx = self.interp_result.grid_x
        gy = self.interp_result.grid_y
        gz = self.interp_result.grid_z
        if len(gx) == 0 or len(gy) == 0:
            return None

        ix = int(round((x - gx[0, 0]) / (gx[0, -1] - gx[0, 0]) * (gx.shape[1] - 1)))
        iy = int(round((y - gy[0, 0]) / (gy[-1, 0] - gy[0, 0]) * (gy.shape[0] - 1)))
        if 0 <= iy < gz.shape[0] and 0 <= ix < gz.shape[1]:
            val = gz[iy, ix]
            if not np.isnan(val):
                return float(val)
        return None

    def _on_axes_leave(self, event) -> None:
        if self.placement_mode:
            self._preview_pos = None
            self._snapped_pos = None
            self._snap_guides = []
            self._snap_label = None
            self.redraw()

    def _on_mouse_click(self, event) -> None:
        """Handle clicking points to open in-place editor popup or place custom point."""
        if event.xdata is None or event.ydata is None or not self.project:
            return

        rx, ry = float(event.xdata), float(event.ydata)

        # Zoom tools: each click zooms at the clicked spot.
        if self.active_tool in ("zoom_in", "zoom_out"):
            factor = self.ZOOM_STEP if self.active_tool == "zoom_in" else 1.0 / self.ZOOM_STEP
            self.zoom_at(rx, ry, factor)
            return

        # Add point stays on after each point until Done is pressed.
        if self.placement_mode:
            if self.project.room.is_inside(rx, ry):
                final_x, final_y = self._snapped_pos or (rx, ry)
                self.point_add_requested.emit(final_x, final_y)
            return

        # Normal Mode: Check if point clicked
        clicked_pt = self._find_nearest_point(rx, ry)
        if clicked_pt:
            if getattr(event, "dblclick", False) and self.editing_enabled:
                # Double-click opens the full point editor (coordinates, lux, notes);
                # a single click keeps using the quick inline popup below.
                self.point_edit_requested.emit(clicked_pt.id)
                return
            self.selected_point_id = clicked_pt.id
            self.point_selected.emit(clicked_pt.id)
            if self.recording_enabled and (not clicked_pt.is_measured or self.editing_enabled):
                self._open_popup_for_point(clicked_pt)
            else:
                self.popup_editor.hide()
            self.redraw()
        else:
            self.deselect()

    def deselect(self) -> None:
        """Clicked away from a point: close the reading box, unselect it, keep its value."""
        self.popup_editor.hide()
        if self.selected_point_id is not None:
            self.selected_point_id = None
            self.btn_delete_point.setEnabled(False)
            self.redraw()
            self.point_deselected.emit()

    def _open_popup_for_point(self, point: MeasurementPoint) -> None:
        """Convert point (x, y) coordinates to display pixels and show floating editor."""
        self.popup_editor.show_for_point(point, self._data_to_widget(point.x, point.y))

    def _data_to_widget(self, x: float, y: float) -> QPoint:
        """Map position (metres) -> position inside this widget, on scaled screens too."""
        disp_x, disp_y = self.ax.transData.transform((x, y))
        ratio = self.canvas.devicePixelRatioF() or 1.0
        on_canvas = QPoint(int(round(disp_x / ratio)), int(round(self.canvas.height() - disp_y / ratio)))
        return self.canvas.mapTo(self, on_canvas)

    def _on_popup_value_submitted(self, point_id: str, lux_val: float) -> None:
        """Request a save; navigation is decided centrally by MainWindow."""
        self.measurement_saved.emit(point_id, lux_val)
        self.popup_editor.hide()
        self.redraw()

    HIT_RADIUS_PX = 12  # how close (on screen) a click must be to select a point

    def _find_nearest_point(self, x: float, y: float, max_dist: Optional[float] = None) -> Optional[MeasurementPoint]:
        """Closest point within HIT_RADIUS_PX screen pixels of (x, y), at any zoom level."""
        if not self.project:
            return None
        ratio = self.canvas.devicePixelRatioF() or 1.0
        click_x, click_y = self.ax.transData.transform((x, y))
        best_pt = None
        best_d = float(self.HIT_RADIUS_PX)
        for p in self.project.points:
            px, py = self.ax.transData.transform((p.x, p.y))
            d = math.hypot(px - click_x, py - click_y) / ratio
            if d <= best_d:
                best_d = d
                best_pt = p
        return best_pt

    def redraw(self) -> None:
        """Render the room map onto canvas."""
        if not self.project:
            return

        room_key = (id(self.project), self.project.room.length, self.project.room.width)
        view = (self.ax.get_xlim(), self.ax.get_ylim()) if room_key == self._view_room_key else None

        rendered = render_room_map(
            ax=self.ax,
            project=self.project,
            interp_result=self.interp_result,
            selected_point_id=self.selected_point_id,
            placement_mode=self.placement_mode,
            preview_pos=self._preview_pos,
            snapped_pos=self._snapped_pos,
            snap_guides=self._snap_guides,
            snap_label=self._snap_label,
            colorbar_ax=self.cax,
        )
        if self.cax is not None:
            # Shown only while the map has colours to explain.
            has_colours = rendered.get("mesh") is not None and self.project.visualization_settings.show_colorbar
            if not has_colours:
                self.cax.clear()
            self.cax.set_visible(has_colours)

        if view is not None:
            self.ax.set_xlim(view[0])
            self.ax.set_ylim(view[1])
        self._view_room_key = room_key

        self.canvas.draw_idle()
