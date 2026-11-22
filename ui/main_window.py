"""Main Application Window for Lumination.

Luxious desktop survey interface:
- Edge-to-edge 2D room canvas covering 100% of central workspace
- Two clean collapsible side panels (Left: Layers & Target, Right: KPIs, DIALux, Table)
- Small sleek floating toggle buttons with chevron icons on the left and right edges
- Zero emojis anywhere — clean, crisp typography and vector icons
- Multi-language runtime translation (English, Romanian, German)
- Menu hierarchy: File, Survey, Language, Help
- Undo / Redo routed through the survey workflow policy
"""

from __future__ import annotations
import os
import time
import copy
import uuid
import math
from typing import Optional
from PySide6.QtCore import Qt, QSize, QSettings
from PySide6.QtGui import QCloseEvent
from PySide6.QtGui import QAction, QKeySequence, QIcon, QUndoStack
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QDockWidget,
    QTabWidget,
    QStatusBar,
    QMessageBox,
    QFileDialog,
    QLabel,
    QPushButton,
    QFrame,
    QStackedWidget,
    QToolBar,
    QScrollArea,
    QSizePolicy,
    QApplication,
)

from models.project import LuminationProject
from models.room import Room
from models.measurement import MeasurementPoint

from ui.room_canvas import RoomCanvasWidget
from ui.start_screen import StartScreenWidget
from ui.survey_mode_widget import SurveyModeWidget
from ui.measurement_table import MeasurementTableWidget
from ui.results_panel import ResultsPanel
from ui.target_panel import TargetPanel
from ui.comparison_panel import ComparisonPanel
from ui.layer_control_widget import LayerControlWidget
from ui.dialogs.survey_setup_dialog import SurveySetupDialog
from ui.dialogs.grid_generator_dialog import GridGeneratorDialog
from ui.dialogs.point_edit_dialog import PointEditDialog

from ui.icons import create_chevron_left_icon, create_chevron_right_icon
from utils.undo_commands import (
    SetMeasurementLuxCommand,
    AddPointCommand,
    DeletePointCommand,
    UpdatePointCommand,
    ReplaceProjectDataCommand,
    ClearMeasurementsCommand,
)
from ui.workflow_controller import Operation, WorkflowController, Workspace
from i18n.translations import tr, TranslationManager, current_language
from persistence.recovery import RecoveryStore


from utils.app_info import APP_NAME, APP_VERSION


class MainWindow(QMainWindow):
    """Main Application Window for Lumination."""

    def __init__(
        self,
        project: Optional[LuminationProject] = None,
        recovery_store: Optional[RecoveryStore] = None,
        settings: Optional[QSettings] = None,
    ) -> None:
        super().__init__()

        self._start_at_home = project is None
        self.project: LuminationProject = project if project is not None else self._create_empty_project()
        self.settings = settings or QSettings()
        self._is_updating: bool = False
        self.interp_result = None
        self.workflow_controller = WorkflowController()
        saved_resume = self.project.resume_state or {}
        saved_point = saved_resume.get("selected_point_id")
        valid_point_ids = {point.id for point in self.project.points}
        self.active_point_id: Optional[str] = saved_point if saved_point in valid_point_ids else None
        if self.active_point_id is None:
            self.active_point_id = next(
                (point.id for point in self.project.get_unmeasured_points()),
                self.project.points[0].id if self.project.points else None,
            )
        self.workflow_controller.select_point(self.active_point_id)
        self.recovery_store = recovery_store or RecoveryStore()
        self._discard_recovery_after_replace = False
        self._resume_candidate: Optional[LuminationProject] = None
        self._resume_kind: Optional[str] = None

        # Undo / Redo Stack
        self.undo_stack = QUndoStack(self)

        self.setWindowTitle(tr("mw_window_title", app=APP_NAME))
        self._save_status_key = "save_not_saved"
        self.resize(1380, 860)
        self.setMinimumSize(960, 600)

        # Create Core UI Widgets
        self.canvas_widget = RoomCanvasWidget(self)
        self.graph_window = None  # the large graph window, created on first use
        # Point highlighted on the map; None after clicking away (the reading bar keeps its point).
        self._map_point_id: Optional[str] = self.active_point_id
        self.survey_widget = SurveyModeWidget(self)
        self.survey_toolbar = QToolBar(tr("mw_survey_toolbar"), self)
        self.survey_toolbar.setMovable(False)
        self.survey_toolbar.setFloatable(False)
        self.survey_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.survey_toolbar.addWidget(self.survey_widget)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, self.survey_toolbar)
        self.start_screen = StartScreenWidget(self)
        self.start_screen.new_survey_requested.connect(self._on_new_project)
        self.start_screen.open_survey_requested.connect(self._on_open_project)
        self.start_screen.resume_requested.connect(self._on_resume_requested)
        self.start_screen.practice_requested.connect(self._on_practice_requested)
        self.table_widget = MeasurementTableWidget(self)
        self.results_panel = ResultsPanel(self)
        self.target_panel = TargetPanel(self)
        self.comparison_panel = ComparisonPanel(self)
        self.layer_widget = LayerControlWidget(self)

        # 1. Central Widget: Edge-to-Edge Canvas with Sleek Floating Edge Toggle Buttons
        central_container = QWidget(self)
        central_layout = QHBoxLayout(central_container)
        central_layout.setContentsMargins(0, 0, 0, 0)
        central_layout.setSpacing(0)

        # Small Left Edge Toggle Button
        self.btn_toggle_left = QPushButton(central_container)
        self.btn_toggle_left.setIcon(create_chevron_left_icon())
        self.btn_toggle_left.setFixedSize(16, 48)
        self.btn_toggle_left.setToolTip(tr("mw_tip_toggle_left"))
        self.btn_toggle_left.setStyleSheet("""
            QPushButton {
                background-color: #f1f5f9;
                border: 1px solid #cbd5e1;
                border-left: none;
                border-top-right-radius: 4px;
                border-bottom-right-radius: 4px;
            }
            QPushButton:hover { background-color: #e2e8f0; }
        """)
        self.btn_toggle_left.clicked.connect(self._toggle_dock_left)

        # Small Right Edge Toggle Button
        self.btn_toggle_right = QPushButton(central_container)
        self.btn_toggle_right.setIcon(create_chevron_right_icon())
        self.btn_toggle_right.setFixedSize(16, 48)
        self.btn_toggle_right.setToolTip(tr("mw_tip_toggle_right"))
        self.btn_toggle_right.setStyleSheet("""
            QPushButton {
                background-color: #f1f5f9;
                border: 1px solid #cbd5e1;
                border-right: none;
                border-top-left-radius: 4px;
                border-bottom-left-radius: 4px;
            }
            QPushButton:hover { background-color: #e2e8f0; }
        """)
        self.btn_toggle_right.clicked.connect(self._toggle_dock_right)

        # Canvas Wrapper
        canvas_wrapper = QWidget(central_container)
        c_vbox = QVBoxLayout(canvas_wrapper)
        c_vbox.setContentsMargins(2, 2, 2, 2)
        c_vbox.addWidget(self.canvas_widget)

        central_layout.addWidget(self.btn_toggle_left)
        central_layout.addWidget(canvas_wrapper, stretch=1)
        central_layout.addWidget(self.btn_toggle_right)

        self.main_workspace = central_container
        self.content_stack = QStackedWidget(self)
        self.content_stack.addWidget(self.start_screen)
        self.content_stack.addWidget(self.main_workspace)
        self.setCentralWidget(self.content_stack)

        # 2. Setup 2 Distinct Collapsible Side Panels (Left and Right)
        self._setup_docks()

        # 3. Setup Menus & Actions
        self._setup_menus()
        self.undo_stack.canUndoChanged.connect(self._on_history_changed)
        self.undo_stack.canRedoChanged.connect(self._on_history_changed)

        # 4. Setup Compact Status Bar
        self._setup_status_bar()

        # 5. Connect Signals
        self._connect_signals()
        self._sync_workflow_controls()

        # 6. Initial UI Data Bind
        self.load_project_into_ui(initial=True)
        if self._start_at_home:
            self._refresh_start_screen()
            self._show_start_screen()
        else:
            self._show_workspace()

        # 7. Connect Language Changes
        TranslationManager.get_instance().language_changed.connect(self.retranslate_ui)

        # Defer first computation to after window is shown
        from PySide6.QtCore import QTimer
        QTimer.singleShot(0, self.recalculate_and_refresh)

    @staticmethod
    def _create_empty_project() -> LuminationProject:
        """Create an empty, unmeasured in-memory placeholder for the start screen."""
        return LuminationProject(
            name=tr("project_new_default"),
            room=Room(name=tr("room_default_name"), length=6.0, width=4.0, height=2.8),
        )

    @staticmethod
    def _create_practice_project() -> LuminationProject:
        """Create clearly labeled sample data for practice, never for a new survey."""
        room = Room(name=tr("practice_room_name"), length=6.0, width=4.0, height=2.8, measurement_plane_height=0.75, wall_margin=0.5, traversal_order="serpentine")
        proj = LuminationProject(
            name=tr("practice_project_name"),
            room=room,
            target_lux=500.0,
            is_practice=True,
        )
        proj.regenerate_grid(mode="count", rows=3, cols=4, wall_margin=0.5, traversal_order="serpentine")

        sample_lux = [320, 370, 410, 430, 380, 450, 520, 500, 400, 490, 570, 540]
        sample_exp = [350, 400, 450, 450, 400, 500, 550, 500, 420, 500, 580, 550]
        for i, p in enumerate(proj.points):
            if i < len(sample_lux):
                p.lux = float(sample_lux[i])
                p.expected_lux = float(sample_exp[i])

        proj.comparison_file = tr("practice_compared_name")
        proj.is_dirty = False
        return proj

    def _show_start_screen(self) -> None:
        self.content_stack.setCurrentWidget(self.start_screen)
        self.dock_left.hide()
        self.dock_right.hide()
        self._sync_workflow_controls()

    def _show_workspace(self) -> None:
        self.content_stack.setCurrentWidget(self.main_workspace)
        # Both side panels start closed; the arrow buttons at the edges open them.
        self.dock_left.hide()
        self.dock_right.hide()
        self._sync_workflow_controls()
        self.recalculate_and_refresh()

    @staticmethod
    def _resume_details(project: LuminationProject, prefix: str) -> tuple[str, str]:
        measured = len(project.get_measured_points())
        total = len(project.points)
        title = f"{prefix}: {project.name}"
        detail = tr("start_resume_detail", measured=measured, total=total)
        return title, detail

    def _refresh_start_screen(self) -> None:
        self._resume_candidate = None
        self._resume_kind = None
        recovery_error: Optional[str] = None
        self.start_screen.btn_resume.setEnabled(True)

        try:
            recovered = self.recovery_store.load()
        except Exception as exc:
            recovered = None
            recovery_error = tr("start_recovery_unreadable", error=exc)

        if recovered is not None:
            recovered.project.resume_state = {
                "workspace": recovered.workspace,
                "selected_point_id": recovered.selected_point_id,
            }
            self._resume_candidate = recovered.project
            self._resume_kind = "recovery"
            title, detail = self._resume_details(recovered.project, tr("start_resume_recovered"))
            if recovered.saved_at:
                detail += tr("start_recovery_saved_at", when=recovered.saved_at)
            self.start_screen.show_resume(title, detail)
            return

        if recovery_error:
            self.start_screen.show_resume(tr("start_recovery_attention"), recovery_error)
            self.start_screen.btn_resume.setEnabled(False)
        else:
            self.start_screen.show_resume(None, None)

    def _on_resume_requested(self) -> None:
        if self._resume_candidate is None:
            return
        self._replace_project(self._resume_candidate)
        self._show_workspace()

    def _on_practice_requested(self) -> None:
        self._replace_project(self._create_practice_project())
        self._show_workspace()
        self.status_bar.showMessage(tr("status_practice_started"), 6000)

    def _setup_docks(self) -> None:
        """Configure 2 clean collapsible side panels on left and right."""
        # Panel 1: Left Dock (Layers & Visuals + Target Illuminance)
        self.dock_left = QDockWidget(self._tab_text("tab_layers"), self)
        self.dock_left.setObjectName("dock_left")
        self.dock_left.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetClosable |
            QDockWidget.DockWidgetFeature.DockWidgetMovable |
            QDockWidget.DockWidgetFeature.DockWidgetFloatable
        )
        self.dock_left.visibilityChanged.connect(self._on_left_dock_visibility_changed)

        self.left_tabs = QTabWidget(self.dock_left)
        self.left_tabs.addTab(self.layer_widget, self._tab_text("tab_layers"))
        self.left_tabs.addTab(self.target_panel, self._tab_text("tab_target"))
        left_scroll = QScrollArea(self.dock_left)
        left_scroll.setWidgetResizable(True)
        left_scroll.setWidget(self.left_tabs)
        self.dock_left.setWidget(left_scroll)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.dock_left)

        # Panel 2: Right Dock (Photometric KPIs + Measurements Schedule Table + DIALux)
        self.dock_right = QDockWidget(self._tab_text("tab_kpis"), self)
        self.dock_right.setObjectName("dock_right")
        self.dock_right.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetClosable |
            QDockWidget.DockWidgetFeature.DockWidgetMovable |
            QDockWidget.DockWidgetFeature.DockWidgetFloatable
        )
        self.dock_right.visibilityChanged.connect(self._on_right_dock_visibility_changed)

        self.right_tabs = QTabWidget(self.dock_right)
        self.right_tabs.addTab(self.results_panel, self._tab_text("tab_kpis"))
        self.right_tabs.addTab(self.table_widget, self._tab_text("tab_measurements"))
        self.right_tabs.addTab(self.comparison_panel, self._tab_text("tab_simulated"))
        right_scroll = QScrollArea(self.dock_right)
        right_scroll.setWidgetResizable(True)
        right_scroll.setWidget(self.right_tabs)
        self.dock_right.setWidget(right_scroll)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.dock_right)

    def _toggle_dock_left(self) -> None:
        opening = not self.dock_left.isVisible()
        if opening and self.width() < 1200:
            self.dock_right.hide()
        self.dock_left.setVisible(opening)
        if opening:
            self.resizeDocks([self.dock_left], [360], Qt.Orientation.Horizontal)

    def _toggle_dock_right(self) -> None:
        opening = not self.dock_right.isVisible()
        if opening and self.width() < 1200:
            self.dock_left.hide()
        self.dock_right.setVisible(opening)
        if opening:
            self.resizeDocks([self.dock_right], [420], Qt.Orientation.Horizontal)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if hasattr(self, "dock_left") and self.width() < 1200 and self.dock_left.isVisible() and self.dock_right.isVisible():
            self.dock_left.hide()
            self.resizeDocks([self.dock_right], [420], Qt.Orientation.Horizontal)

    def _on_left_dock_visibility_changed(self, visible: bool) -> None:
        self.btn_toggle_left.setIcon(create_chevron_left_icon() if visible else create_chevron_right_icon())

    def _on_right_dock_visibility_changed(self, visible: bool) -> None:
        self.btn_toggle_right.setIcon(create_chevron_right_icon() if visible else create_chevron_left_icon())

    def _setup_menus(self) -> None:
        """Create clean menu hierarchy: File, Survey, Language, Help."""
        menubar = self.menuBar()
        for menu_action in menubar.actions():
            old_menu = menu_action.menu()
            if old_menu:
                for old_action in old_menu.actions():
                    old_action.setShortcut(QKeySequence())
                    old_action.deleteLater()
                old_menu.deleteLater()
        menubar.clear()

        # 1. File Menu
        self.menu_file = menubar.addMenu(f"&{tr('menu_file')}")

        self.act_new = QAction(f"&{tr('menu_new_project')}", self)
        self.act_new.setShortcut(QKeySequence.StandardKey.New)
        self.act_new.triggered.connect(self._on_new_project)
        self.menu_file.addAction(self.act_new)

        self.act_open = QAction(f"&{tr('menu_open_project')}", self)
        self.act_open.setShortcut(QKeySequence.StandardKey.Open)
        self.act_open.triggered.connect(self._on_open_project)
        self.menu_file.addAction(self.act_open)

        self.act_save = QAction(f"&{tr('menu_save_project')}", self)
        self.act_save.setShortcut(QKeySequence.StandardKey.Save)
        self.act_save.triggered.connect(self._on_save_project)
        self.menu_file.addAction(self.act_save)

        self.act_save_as = QAction(f"{tr('menu_save_project_as')}", self)
        self.act_save_as.setShortcut(QKeySequence.StandardKey.SaveAs)
        self.act_save_as.triggered.connect(self._on_save_project_as)
        self.menu_file.addAction(self.act_save_as)

        self.menu_file.addSeparator()

        self.act_exit = QAction(tr("menu_exit"), self)
        self.act_exit.triggered.connect(self.close)
        self.menu_file.addAction(self.act_exit)

        self.menu_survey = menubar.addMenu(f"&{tr('menu_survey')}")
        self.act_generate_grid = QAction(tr("menu_change_grid"), self)
        self.act_generate_grid.triggered.connect(self._on_grid_requested)
        self.menu_survey.addAction(self.act_generate_grid)
        self.act_clear_measurements = QAction(tr("menu_clear_measurements"), self)
        self.act_clear_measurements.triggered.connect(self._on_clear_measurements)
        self.menu_survey.addAction(self.act_clear_measurements)

        # Undo / Redo are not in any menu (the map toolbar has the buttons); Ctrl+Z and Ctrl+Y
        # still work anywhere in the window.
        for old in (getattr(self, "act_undo", None), getattr(self, "act_redo", None)):
            if old is not None:
                self.removeAction(old)
                old.setShortcut(QKeySequence())
                old.deleteLater()
        self.act_undo = QAction(tr("menu_undo"), self)
        self.act_undo.setShortcut(QKeySequence.StandardKey.Undo)
        self.act_undo.triggered.connect(self._undo_if_allowed)
        self.addAction(self.act_undo)
        self.act_redo = QAction(tr("menu_redo"), self)
        self.act_redo.setShortcut(QKeySequence.StandardKey.Redo)
        self.act_redo.triggered.connect(self._redo_if_allowed)
        self.addAction(self.act_redo)

        # 3. Language Menu
        self.menu_lang = menubar.addMenu(f"&{tr('menu_language')}")

        self.act_lang_en = QAction("English (EN)", self)
        self.act_lang_en.triggered.connect(lambda: TranslationManager.get_instance().set_language("en"))
        self.menu_lang.addAction(self.act_lang_en)

        self.act_lang_ro = QAction("Română (RO)", self)
        self.act_lang_ro.triggered.connect(lambda: TranslationManager.get_instance().set_language("ro"))
        self.menu_lang.addAction(self.act_lang_ro)

        self.act_lang_de = QAction("Deutsch (DE)", self)
        self.act_lang_de.triggered.connect(lambda: TranslationManager.get_instance().set_language("de"))
        self.menu_lang.addAction(self.act_lang_de)

        # 4. Help Menu
        self.menu_help = menubar.addMenu(f"&{tr('menu_help')}")

        self.act_shortcuts = QAction(tr("menu_shortcuts"), self)
        self.act_shortcuts.triggered.connect(self._on_show_shortcuts)
        self.menu_help.addAction(self.act_shortcuts)

        self.act_methodology = QAction(tr("menu_methodology"), self)
        self.act_methodology.triggered.connect(self._on_show_methodology)
        self.menu_help.addAction(self.act_methodology)

        self.menu_help.addSeparator()

        self.act_about = QAction(tr("menu_about", app=APP_NAME), self)
        self.act_about.triggered.connect(self._on_about)
        self.menu_help.addAction(self.act_about)

    def _setup_status_bar(self) -> None:
        """Create clean, compact status bar positioned comfortably within viewport."""
        self.status_bar = QStatusBar(self)
        self.status_bar.setFixedHeight(22)
        self.status_bar.setStyleSheet("""
            QStatusBar {
                background-color: #f8fafc;
                border-top: 1px solid #e2e8f0;
                color: #334155;
                font-size: 11px;
            }
        """)
        self.setStatusBar(self.status_bar)

        self.lbl_project_status = QLabel(tr("status_ready"), self)
        self.lbl_project_status.setStyleSheet("color: #334155; font-size: 11px; padding: 0 6px;")

        self.lbl_save_status = QLabel(tr(self._save_status_key), self)
        self.lbl_save_status.setStyleSheet("color: #52606d; font-size: 11px; padding: 0 8px;")

        self.status_bar.addWidget(self.lbl_project_status, stretch=1)
        self.status_bar.addPermanentWidget(self.lbl_save_status)

    def _connect_signals(self) -> None:
        """Connect inter-widget signals."""
        self._connect_canvas(self.canvas_widget)
        self.canvas_widget.fullscreen_requested.connect(self.open_graph_window)
        self.survey_widget.measurement_saved.connect(self._on_measurement_recorded)
        self.survey_widget.point_navigated.connect(self._on_point_selected)

        self.table_widget.point_selected.connect(self._on_point_selected)
        self.table_widget.data_changed.connect(self.recalculate_and_refresh)
        self.table_widget.edit_requested.connect(self._on_table_edit_requested)

        self.results_panel.highlight_point_requested.connect(self._on_point_selected)
        self.target_panel.target_changed.connect(self._on_target_changed)
        self.comparison_panel.display_mode_changed.connect(self._on_display_settings_changed)
        self.comparison_panel.compare_requested.connect(self._on_compare_with_file)
        self.layer_widget.settings_changed.connect(self._on_display_settings_changed)

    def _connect_canvas(self, canvas: RoomCanvasWidget) -> None:
        canvas.point_selected.connect(self._on_point_selected)
        canvas.point_edit_requested.connect(self._on_point_edit_requested)
        canvas.point_add_requested.connect(self._on_point_add_requested)
        canvas.point_delete_requested.connect(self._on_point_delete_requested)
        canvas.measurement_saved.connect(self._on_measurement_recorded)
        canvas.point_deselected.connect(self._on_map_point_deselected)
        canvas.undo_requested.connect(self._undo_if_allowed)
        canvas.redo_requested.connect(self._redo_if_allowed)

    def _map_canvases(self) -> list:
        """The main map plus the large graph window's map while it is open."""
        canvases = [self.canvas_widget]
        if self.graph_window is not None and self.graph_window.isVisible():
            canvases.append(self.graph_window.canvas_widget)
        return canvases

    def open_graph_window(self) -> None:
        """Full screen: show the graph alone in a large window (the app window stays as it is)."""
        from ui.graph_window import GraphWindow

        if self.graph_window is None:
            self.graph_window = GraphWindow(self)
            self._connect_canvas(self.graph_window.canvas_widget)
        canvas = self.graph_window.canvas_widget
        canvas.set_editing_enabled(self.canvas_widget.editing_enabled)
        canvas.set_recording_enabled(self.canvas_widget.recording_enabled)
        canvas.btn_undo.setEnabled(self.undo_stack.canUndo())
        canvas.btn_redo.setEnabled(self.undo_stack.canRedo())
        canvas.set_project(self.project, interp_result=self.interp_result, selected_point_id=self._map_point_id)
        self.graph_window.show_large()

    def retranslate_ui(self) -> None:
        """Update window, menus, and side panel tabs when language switches."""
        self.setWindowTitle(tr("mw_window_title", app=APP_NAME))
        self._setup_menus()
        self.survey_toolbar.setWindowTitle(tr("mw_survey_toolbar"))
        self.btn_toggle_left.setToolTip(tr("mw_tip_toggle_left"))
        self.btn_toggle_right.setToolTip(tr("mw_tip_toggle_right"))
        self.lbl_save_status.setText(tr(self._save_status_key))
        if self.content_stack.currentWidget() is self.start_screen:
            self._refresh_start_screen()

        self.dock_left.setWindowTitle(self._tab_text("tab_layers"))
        self.left_tabs.setTabText(0, self._tab_text("tab_layers"))
        self.left_tabs.setTabText(1, self._tab_text("tab_target"))

        self.dock_right.setWindowTitle(self._tab_text("tab_kpis"))
        self.right_tabs.setTabText(0, self._tab_text("tab_kpis"))
        self.right_tabs.setTabText(1, self._tab_text("tab_measurements"))
        self.right_tabs.setTabText(2, self._tab_text("tab_simulated"))

        self.recalculate_and_refresh()
        self._sync_workflow_controls()

    def load_project_into_ui(self, initial: bool = False) -> None:
        """Bind project data to all UI components with signal guards."""
        if self._is_updating:
            return
        self._is_updating = True
        try:
            self.survey_widget.set_project(self.project, self.active_point_id)
            self.table_widget.set_project(self.project)
            self.layer_widget.set_project(self.project)
            self.target_panel.set_project(self.project)
            self.comparison_panel.set_project(self.project)
        finally:
            self._is_updating = False

        if not initial:
            self.recalculate_and_refresh()

    def recalculate_and_refresh(self) -> None:
        """Perform numerical statistics, 2D interpolation, and refresh canvas and panels."""
        if self._is_updating:
            return
        self._is_updating = True

        try:
            from analysis.statistics import calculate_statistics
            from analysis.interpolation import reconstruct_illuminance_field

            stats = calculate_statistics(self.project.points)
            self.results_panel.update_statistics(stats)
            self.target_panel.update_analysis()
            self.comparison_panel.update_analysis()

            display_mode = self.project.visualization_settings.display_mode
            active_points = self.project.points
            if display_mode == "expected":
                active_points = [MeasurementPoint(id=p.id, x=p.x, y=p.y, lux=p.expected_lux) for p in self.project.points if p.expected_lux is not None]
            elif display_mode == "difference":
                active_points = []
                for point in self.project.points:
                    if point.delta_lux is not None:
                        display_point = copy.copy(point)
                        display_point.lux = point.delta_lux  # Transient signed field, never a physical reading.
                        active_points.append(display_point)

            measured_count = len([p for p in active_points if p.lux is not None and math.isfinite(p.lux) and (p.lux >= 0 or display_mode == "difference")])

            if measured_count >= 3:
                self.interp_result = reconstruct_illuminance_field(
                    self.project.points if display_mode == "measured" else active_points,
                    self.project.room,
                    resolution=100,
                    method=self.project.visualization_settings.interpolation_method,
                    extrapolate_to_walls=True,
                    allow_negative=display_mode == "difference",
                )
            else:
                self.interp_result = None

            for canvas in self._map_canvases():
                canvas.set_project(
                    self.project,
                    interp_result=self.interp_result,
                    selected_point_id=self._map_point_id,
                )

            r = self.project.room
            n_meas = len(self.project.get_measured_points())
            n_tot = len(self.project.points)
            self.lbl_project_status.setText(tr(
                "status_summary",
                practice=tr("status_practice_prefix") if self.project.is_practice else "",
                length=r.length,
                width=r.width,
                area=r.area,
                measured=n_meas,
                total=n_tot,
                avg=f"{stats.e_avg:.0f}" if stats else "-",
                u0=f"{stats.uniformity_u0:.2f}" if stats else "-",
            ))
        finally:
            self._is_updating = False

    def _on_point_selected(self, point_id: str) -> None:
        if self._is_updating:
            return
        self._is_updating = True
        try:
            self.active_point_id = point_id
            self.workflow_controller.select_point(point_id)
            self.project.resume_state = {
                "workspace": self.workflow_controller.workspace.value,
                "selected_point_id": point_id,
            }
            self._map_point_id = point_id
            for canvas in self._map_canvases():
                canvas.set_selected_point_id(point_id)
            self.table_widget.select_point(point_id)
            self.survey_widget.set_active_point(point_id)
        finally:
            self._is_updating = False
        if self.project.is_dirty:
            self._write_recovery_snapshot()

    def _on_measurement_recorded(
        self,
        point_id: str,
        lux: Optional[float],
        operation_id: Optional[str] = None,
        device_name: str = "Manual Entry",  # stored value; shown translated in the table
        advance: bool = True,
        profile_id: Optional[str] = None,
    ) -> bool:
        """Validate and record one reading event, then advance to pending work."""
        point = self.project.find_point_by_id(point_id)
        if point is None or (lux is not None and (not math.isfinite(lux) or lux < 0)):
            return False
        is_correction = point.is_measured
        if lux is None and not is_correction:
            return False
        operation = Operation.CORRECT_READING if is_correction else Operation.RECORD_READING
        event_id = operation_id or str(uuid.uuid4())
        if not self.workflow_controller.claim_operation(event_id):
            return False
        cmd = SetMeasurementLuxCommand(
            project=self.project,
            point_id=point_id,
            new_lux=lux,
            new_device=device_name,
            callback=self._on_data_modified,
            workflow_operation=operation.value,
            new_sample_id=event_id,
            new_profile_id=profile_id,
        )
        self.undo_stack.push(cmd)
        if advance and lux is not None and not is_correction:
            next_point = self.workflow_controller.next_pending(
                [item.id for item in self.project.points],
                {item.id for item in self.project.get_measured_points()},
            )
            if next_point:
                self._on_point_selected(next_point)
            else:
                self.status_bar.showMessage(tr("status_survey_complete"), 5000)
        return True

    def _on_data_modified(self) -> None:
        """Callback when undo/redo modifies data."""
        valid_ids = {point.id for point in self.project.points}
        selected = self.workflow_controller.reconcile_points(valid_ids)
        if selected is None and self.project.points:
            selected = next(
                (point.id for point in self.project.get_unmeasured_points()),
                self.project.points[0].id,
            )
            self.workflow_controller.select_point(selected)
        self.active_point_id = selected
        self.survey_widget.set_project(self.project, selected)
        self.table_widget.refresh()
        if selected:
            self.table_widget.select_point(selected)
        self.recalculate_and_refresh()
        self._write_recovery_snapshot()
        self._sync_workflow_controls()

    def _on_target_changed(self, _value: float) -> None:
        self.recalculate_and_refresh()
        self._write_recovery_snapshot()

    def _on_display_settings_changed(self, _value=None) -> None:
        self.project.mark_modified()
        self.recalculate_and_refresh()
        self._write_recovery_snapshot()

    def _write_recovery_snapshot(self) -> None:
        try:
            self._save_resume_context()
            workspace_name = self.project.resume_state["workspace"]
            self.recovery_store.save(
                self.project,
                workspace=workspace_name,
                selected_point_id=self.active_point_id,
            )
            self._set_save_status("save_recovery_saved", tr("save_recovery_tip"))
        except Exception as exc:
            self._set_save_status("save_recovery_failed", tr("save_recovery_failed_tip", error=exc))

    def _show_only_language_menu(self, only_language: bool) -> None:
        """Start screen and new-survey setup: only the Language menu is offered."""
        for menu in (self.menu_file, self.menu_survey, self.menu_help):
            menu.menuAction().setVisible(not only_language)
        for action in (self.act_new, self.act_open, self.act_exit):
            action.setEnabled(not only_language)

    def _sync_workflow_controls(self) -> None:
        active = self.content_stack.currentWidget() is self.main_workspace
        self._show_only_language_menu(not active)
        self.survey_toolbar.setVisible(active)
        self.menu_survey.setEnabled(active)
        self.act_save.setEnabled(active)
        self.act_save_as.setEnabled(active)
        self.survey_widget.set_workflow_permissions(recording=active, correction=active)
        self.table_widget.set_edit_allowed(active)
        for canvas in self._map_canvases():
            canvas.set_editing_enabled(active)
            canvas.set_recording_enabled(active)
            canvas.btn_undo.setEnabled(self.undo_stack.canUndo())
            canvas.btn_redo.setEnabled(self.undo_stack.canRedo())
        self.act_generate_grid.setEnabled(active)
        self.act_clear_measurements.setEnabled(active)
        self.act_undo.setEnabled(self.undo_stack.canUndo())
        self.act_redo.setEnabled(self.undo_stack.canRedo())

    def _on_history_changed(self, _enabled: bool) -> None:
        self._sync_workflow_controls()

    def _undo_if_allowed(self) -> None:
        if self.undo_stack.canUndo():
            self.undo_stack.undo()

    def _redo_if_allowed(self) -> None:
        if self.undo_stack.canRedo():
            self.undo_stack.redo()

    def _on_table_edit_requested(self, point_id: str, column: int, value: object) -> None:
        point = self.project.find_point_by_id(point_id)
        if point is None:
            return
        if column == 3:
            updated = copy.deepcopy(point)
            if value is None:
                updated.clear_reading()
            else:
                updated.record_reading(float(value), device_name="Table Input")
        else:
            updated = copy.deepcopy(point)
            if column == 4:
                updated.expected_lux = None if value is None else float(value)
            elif column == 7:
                updated.notes = str(value)
            else:
                self.table_widget.refresh()
                return
        self.undo_stack.push(UpdatePointCommand(self.project, updated, self._on_data_modified))

    def _on_grid_requested(self) -> None:
        candidate = copy.deepcopy(self.project)
        dialog = GridGeneratorDialog(candidate, self)
        if dialog.exec() == GridGeneratorDialog.DialogCode.Accepted:
            command = ReplaceProjectDataCommand(
                self.project, candidate, "Change Measurement Grid", self._on_data_modified
            )
            self.undo_stack.push(command)
            next_point = next(
                (point.id for point in self.project.get_unmeasured_points()),
                self.project.points[0].id if self.project.points else None,
            )
            if next_point:
                self._on_point_selected(next_point)
            else:
                self.recalculate_and_refresh()

    def _on_clear_measurements(self) -> None:
        if self._ask_yes_no(tr("dlg_clear_title"), tr("dlg_clear_text")) != QMessageBox.StandardButton.Yes:
            return
        self.undo_stack.push(ClearMeasurementsCommand(self.project, self._on_data_modified))

    def _on_point_edit_requested(self, point_id: str) -> None:
        pt = self.project.find_point_by_id(point_id)
        if pt:
            dlg = PointEditDialog(copy.deepcopy(pt), self.project.room, self)
            if dlg.exec() == PointEditDialog.DialogCode.Accepted:
                self.undo_stack.push(UpdatePointCommand(self.project, dlg.point, self._on_data_modified))

    def _on_point_add_requested(self, x: float, y: float) -> None:
        candidate = copy.deepcopy(self.project)
        pt = candidate.add_custom_point(x, y, notes="Custom Sensor")  # stored; shown translated
        cmd = ReplaceProjectDataCommand(self.project, candidate, f"Add Point {pt.id}", self._on_data_modified)
        self.undo_stack.push(cmd)
        self._on_point_selected(pt.id)

    def _on_point_delete_requested(self, point_id: str) -> None:
        cmd = DeletePointCommand(self.project, point_id, callback=self._on_data_modified)
        self.undo_stack.push(cmd)
        remaining = {point.id for point in self.project.points}
        self.active_point_id = self.workflow_controller.reconcile_points(remaining)
        if self.active_point_id is None and self.project.points:
            self.active_point_id = self.project.points[0].id
            self.workflow_controller.select_point(self.active_point_id)
        if self.active_point_id:
            self._on_point_selected(self.active_point_id)
        else:
            self._map_point_id = None
            for canvas in self._map_canvases():
                canvas.set_selected_point_id(None)

    def _on_map_point_deselected(self) -> None:
        """Clicked away from a point on a map: no point is highlighted; the reading bar keeps it."""
        self._map_point_id = None
        for canvas in self._map_canvases():
            if canvas.selected_point_id is not None:
                canvas.set_selected_point_id(None)
            canvas.popup_editor.hide()

    # --- Menu Handlers ---

    def _confirm_project_replacement(self) -> bool:
        self._discard_recovery_after_replace = False
        if not self.project.is_dirty:
            return True
        result = self._ask_save_discard_cancel(tr("dlg_unsaved_replace"))
        if result == QMessageBox.StandardButton.Save:
            return self._on_save_project()
        if result == QMessageBox.StandardButton.Discard:
            self._discard_recovery_after_replace = True
            return True
        return False

    def _replace_project(self, project: LuminationProject) -> None:
        if self._discard_recovery_after_replace:
            self.recovery_store.discard()
        self._discard_recovery_after_replace = False
        self.project = project
        self.workflow_controller = WorkflowController()
        resume = project.resume_state or {}
        valid_ids = {point.id for point in project.points}
        point_id = resume.get("selected_point_id")
        if point_id not in valid_ids:
            point_id = next(
                (point.id for point in project.get_unmeasured_points()),
                project.points[0].id if project.points else None,
            )
        self.active_point_id = point_id
        self._map_point_id = point_id
        self.workflow_controller.select_point(point_id)
        self.undo_stack.clear()
        self._sync_workflow_controls()
        self.load_project_into_ui()
        self._set_save_status("save_saved_locally" if not project.is_dirty and project.file_path else "save_not_saved")

    def _on_new_project(self) -> None:
        dlg = SurveySetupDialog(self, settings=self.settings)
        self._show_only_language_menu(True)
        try:
            accepted = dlg.exec() == SurveySetupDialog.DialogCode.Accepted
        finally:
            self._sync_workflow_controls()
            dlg.deleteLater()
        if accepted:
            new_proj = dlg.get_created_project()
            if new_proj and self._confirm_project_replacement():
                self._replace_project(new_proj)
                self._show_workspace()
                updated, created = dlg.import_counts
                if updated or created:
                    self.status_bar.showMessage(
                        tr("status_created_with_import", updated=updated, created=created), 5000
                    )

    def _on_open_project(self) -> None:
        from persistence.project_io import load_project
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            tr("dlg_open_project_title", app=APP_NAME),
            "",
            ";;".join((
                tr("filter_all_supported"),
                tr("filter_project", app=APP_NAME),
                tr("filter_excel"),
                tr("filter_csv"),
                tr("filter_json"),
            )),
        )
        if file_path:
            from persistence.table_io import is_table_file
            if is_table_file(file_path):
                self._open_table(file_path)
                return
            if not self._confirm_project_replacement():
                return
            try:
                proj = load_project(file_path)
                self._replace_project(proj)
                self._show_workspace()
                self.status_bar.showMessage(tr("status_project_loaded", name=os.path.basename(file_path)), 4000)
            except Exception as e:
                QMessageBox.critical(self, tr("err_load_title"), tr("err_load_text", error=e))

    def _open_table(self, file_path: str) -> bool:
        """Build a new survey from an Excel or CSV grid of readings."""
        from persistence.table_io import TableError, project_from_table, read_table
        from ui.dialogs.table_setup_dialog import TableSetupDialog

        try:
            values = read_table(file_path)
        except TableError as exc:
            QMessageBox.warning(self, tr("table_err_title"), str(exc))
            return False
        rows, cols = len(values), max(len(row) for row in values)
        dialog = TableSetupDialog(rows, cols, self, settings=self.settings)
        accepted = dialog.exec() == TableSetupDialog.DialogCode.Accepted
        dialog.deleteLater()
        if not accepted:
            return False
        name = os.path.splitext(os.path.basename(file_path))[0]
        try:
            project = project_from_table(
                values,
                name,
                dialog.spacing_x.value(),
                dialog.spacing_y.value(),
                dialog.margin.value(),
                dialog.traversal_order,
            )
        except TableError as exc:
            QMessageBox.warning(self, tr("table_err_title"), str(exc))
            return False
        if not self._confirm_project_replacement():
            return False
        self._replace_project(project)
        self._show_workspace()
        self.status_bar.showMessage(tr("status_table_opened", name=os.path.basename(file_path)), 6000)
        return True

    def _on_compare_with_file(self) -> bool:
        """Compare the survey with a Luxious project, Excel or CSV grid of the same size."""
        from persistence.comparison_io import apply_comparison
        from persistence.table_io import TableError
        from utils.undo_commands import SetComparisonCommand

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            tr("cmp_dialog_title"),
            "",
            ";;".join((
                tr("filter_all_supported"),
                tr("filter_project", app=APP_NAME),
                tr("filter_excel"),
                tr("filter_csv"),
            )),
        )
        if not file_path:
            return False
        candidate = copy.deepcopy(self.project)
        try:
            count = apply_comparison(candidate, file_path)
        except TableError as exc:
            QMessageBox.warning(self, tr("table_err_title"), str(exc))
            return False
        self.undo_stack.push(SetComparisonCommand(self.project, candidate, callback=self._on_data_modified))
        self.status_bar.showMessage(tr("cmp_status_loaded", name=os.path.basename(file_path), count=count), 5000)
        return True

    def _save_resume_context(self) -> None:
        workspace = self.workflow_controller.workspace
        self.project.resume_state = {
            "workspace": workspace.value,
            "selected_point_id": self.active_point_id,
        }

    def _on_save_project(self) -> bool:
        self._save_resume_context()
        if not self.project.file_path:
            return self._ask_and_save_project()
        from persistence.project_io import save_project
        try:
            self.project.language = current_language()
            save_project(self.project, self.project.file_path)
            self.recovery_store.discard()
            self._set_save_status("save_saved_locally", self.project.file_path)
            self.status_bar.showMessage(tr("status_project_saved"), 3000)
            return True
        except Exception as e:
            self._set_save_status("save_failed", tr("save_failed_tip", error=e))
            QMessageBox.critical(self, tr("err_save_title"), tr("err_save_text", error=e))
            return False

    def _save_as_types(self) -> list:
        """(file filter, extension, kind) offered by Save As, in order."""
        return [
            (tr("filter_project", app=APP_NAME), ".luxproj", "project"),
            (tr("filter_csv"), ".csv", "csv"),
            (tr("filter_excel"), ".xlsx", "excel"),
            (tr("filter_pdf"), ".pdf", "pdf"),
            (tr("filter_png"), ".png", "png"),
        ]

    def _default_file_stem(self) -> str:
        stem = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in self.project.name.strip().lower())
        return stem.strip("_") or "survey"

    def _on_save_project_as(self) -> bool:
        """Save the survey as a project file, a CSV table or a PDF report."""
        types = self._save_as_types()
        file_path, selected = QFileDialog.getSaveFileName(
            self,
            tr("dlg_save_as_any"),
            self._default_file_stem() + ".luxproj",
            ";;".join(entry[0] for entry in types),
        )
        if not file_path:
            return False
        extension = os.path.splitext(file_path)[1].lower()
        kind = next((k for _f, ext, k in types if ext == extension), None)
        if kind is None:
            kind, ext = next(((k, e) for f, e, k in types if f == selected), ("project", ".luxproj"))
            file_path += ext
        if kind in ("csv", "excel"):
            return self._write_table(file_path, kind)
        if kind == "pdf":
            return self._write_pdf(file_path)
        if kind == "png":
            return self._write_png(file_path)
        return self._save_project_to(file_path)

    def _ask_and_save_project(self) -> bool:
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            tr("dlg_save_as_title", app=APP_NAME),
            self._default_file_stem() + ".luxproj",
            ";;".join((tr("filter_project", app=APP_NAME), tr("filter_all"))),
        )
        if not file_path:
            return False
        if not os.path.splitext(file_path)[1]:
            file_path += ".luxproj"
        return self._save_project_to(file_path)

    def _save_project_to(self, file_path: str) -> bool:
        self._save_resume_context()
        from persistence.project_io import save_project
        if file_path:
            try:
                self.project.language = current_language()
                save_project(self.project, file_path)
                self.recovery_store.discard()
                self._set_save_status("save_saved_locally", file_path)
                self.status_bar.showMessage(tr("status_saved_as", name=os.path.basename(file_path)), 4000)
                return True
            except Exception as e:
                self._set_save_status("save_failed", tr("save_failed_tip", error=e))
                QMessageBox.critical(self, tr("err_save_title"), tr("err_save_text", error=e))
                return False
        return False

    def closeEvent(self, event: QCloseEvent) -> None:
        """Protect dirty project changes before the window is closed."""
        if not self.project.is_dirty:
            event.accept()
            return

        result = self._ask_save_discard_cancel(tr("dlg_unsaved_close"))

        if result == QMessageBox.StandardButton.Save:
            if self._on_save_project():
                event.accept()
            else:
                event.ignore()
        elif result == QMessageBox.StandardButton.Discard:
            self.recovery_store.discard()
            event.accept()
        else:
            event.ignore()

    def _write_table(self, file_path: str, kind: str) -> bool:
        """Save the readings as a grid table (CSV or Excel), in the layout File > Open reads back."""
        from persistence.table_io import write_table
        try:
            extra = write_table(self.project, file_path)
        except Exception as e:
            error_key = "err_export_excel" if kind == "excel" else "err_export_csv"
            QMessageBox.critical(self, tr("err_export_title"), tr(error_key, error=e))
            return False
        if extra:
            QMessageBox.warning(
                self,
                tr("table_extra_points_title"),
                tr("table_extra_points_text", points=", ".join(point.id for point in extra)),
            )
        status_key = "status_saved_excel" if kind == "excel" else "status_saved_csv"
        self.status_bar.showMessage(tr(status_key, name=os.path.basename(file_path)), 5000)
        return True

    def _write_png(self, file_path: str) -> bool:
        """The main map exactly as shown (current zoom), with its colour bar, as a PNG image."""
        figure = self.canvas_widget.figure
        try:
            figure.savefig(file_path, format="png", dpi=200, facecolor=figure.get_facecolor(), bbox_inches="tight")
        except Exception as e:
            QMessageBox.critical(self, tr("err_export_title"), tr("err_export_png", error=e))
            return False
        self.status_bar.showMessage(tr("status_saved_png", name=os.path.basename(file_path)), 5000)
        return True

    def _write_pdf(self, file_path: str) -> bool:
        from reporting.pdf_report import generate_pdf_report
        try:
            generate_pdf_report(self.project, file_path, lang=current_language())
        except Exception as e:
            QMessageBox.critical(self, tr("err_pdf_title"), tr("err_pdf", error=e))
            return False
        self.status_bar.showMessage(tr("status_saved_pdf", name=os.path.basename(file_path)), 5000)
        return True

    def _on_show_shortcuts(self) -> None:
        def key(action: QAction) -> str:
            return action.shortcut().toString(QKeySequence.SequenceFormat.NativeText)

        items = [
            tr("help_sc_click"),
            tr("help_sc_enter"),
            tr("help_sc_delete"),
            tr("help_sc_undo", key=key(self.act_undo)),
            tr("help_sc_redo", key=key(self.act_redo)),
            tr("help_sc_save", key=key(self.act_save)),
            tr("help_sc_open", key=key(self.act_open)),
            tr("help_sc_new", key=key(self.act_new)),
            tr("help_sc_wheel"),
            tr("help_sc_escape"),
        ]
        QMessageBox.information(
            self,
            tr("help_shortcuts_title"),
            f"<h3>{tr('help_shortcuts_heading', app=APP_NAME)}</h3><ul>"
            + "".join(f"<li>{item}</li>" for item in items)
            + "</ul>",
        )

    def _on_show_methodology(self) -> None:
        QMessageBox.information(self, tr("help_method_title"), tr("help_method_body", app=APP_NAME))

    def _on_about(self) -> None:
        QMessageBox.about(
            self,
            tr("menu_about", app=APP_NAME),
            f"<h2>{APP_NAME}</h2>"
            f"<p><b>{tr('about_subtitle')}</b></p>"
            f"<p>{tr('about_version', version=APP_VERSION)}</p>"
            f"<p>{tr('about_text')}</p>",
        )

    # --- Message helpers with translated buttons (Qt ships no Romanian strings) ---

    @staticmethod
    def _tab_text(key: str) -> str:
        """Tab labels treat '&' as a shortcut marker, so show a literal ampersand."""
        return tr(key).replace("&", "&&")

    def _set_save_status(self, key: str, tooltip: str = "") -> None:
        self._save_status_key = key
        self.lbl_save_status.setText(tr(key))
        self.lbl_save_status.setToolTip(tooltip)

    def _ask_yes_no(self, title: str, text: str) -> QMessageBox.StandardButton:
        box = QMessageBox(QMessageBox.Icon.Question, title, text, parent=self)
        box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        box.setDefaultButton(QMessageBox.StandardButton.No)
        box.button(QMessageBox.StandardButton.Yes).setText(tr("btn_yes"))
        box.button(QMessageBox.StandardButton.No).setText(tr("btn_no"))
        return QMessageBox.StandardButton(box.exec())

    def _ask_save_discard_cancel(self, question: str) -> QMessageBox.StandardButton:
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Warning)
        box.setWindowTitle(tr("dlg_unsaved_title"))
        box.setText(tr("dlg_unsaved_text"))
        box.setInformativeText(question)
        box.setStandardButtons(
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel
        )
        box.setDefaultButton(QMessageBox.StandardButton.Save)
        box.button(QMessageBox.StandardButton.Save).setText(tr("btn_save"))
        box.button(QMessageBox.StandardButton.Discard).setText(tr("btn_discard"))
        box.button(QMessageBox.StandardButton.Cancel).setText(tr("btn_cancel"))
        return QMessageBox.StandardButton(box.exec())
