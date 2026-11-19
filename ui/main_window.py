"""Main Application Window for Lumination.

Luxious desktop survey interface:
- Edge-to-edge 2D room canvas covering 100% of central workspace
- Two clean collapsible side panels (Left: Layers & Target, Right: KPIs, DIALux, Table)
- Small sleek floating toggle buttons with chevron icons on the left and right edges
- USB/Bluetooth discovery with capture disabled until a meter profile is qualified
- Zero emojis anywhere — clean, crisp typography and vector icons
- Multi-language runtime translation (English, Romanian, German)
- Menu hierarchy: File, CSV & Export, Devices, Language, Help
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
from measurement_sources.base import MeasurementSource
from measurement_sources.manual import ManualMeasurementSource
from measurement_sources.usb_serial import USBSerialMeterSource
from measurement_sources.bluetooth_meter import BluetoothMeterSource
from measurement_sources.device_session import MeasurementSample

from ui.room_canvas import RoomCanvasWidget
from ui.start_screen import StartScreenWidget
from ui.survey_mode_widget import SurveyModeWidget
from ui.measurement_table import MeasurementTableWidget
from ui.results_panel import ResultsPanel
from ui.target_panel import TargetPanel
from ui.comparison_panel import ComparisonPanel
from ui.layer_control_widget import LayerControlWidget
from ui.dialogs.survey_setup_dialog import SurveySetupDialog
from ui.dialogs.import_preview_dialog import ImportPreviewDialog
from ui.dialogs.grid_generator_dialog import GridGeneratorDialog
from ui.dialogs.point_edit_dialog import PointEditDialog
from ui.dialogs.export_dialog import ExportDialog
from ui.dialogs.hardware_connection_dialog import HardwareConnectionDialog

from ui.icons import create_chevron_left_icon, create_chevron_right_icon, create_bluetooth_icon
from utils.undo_commands import (
    SetMeasurementLuxCommand,
    AddPointCommand,
    DeletePointCommand,
    UpdatePointCommand,
    ReplaceProjectDataCommand,
    ClearMeasurementsCommand,
)
from ui.workflow_controller import Operation, WorkflowController, Workspace
from i18n.translations import tr, TranslationManager
from persistence.recovery import RecoveryStore


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
        if saved_resume.get("workspace") == Workspace.REVIEW.value:
            self.workflow_controller.enter_review()
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
        self._missing_recent_path: Optional[str] = None

        # Undo / Redo Stack
        self.undo_stack = QUndoStack(self)

        self.setWindowTitle("Lumination — Real-Room Illuminance Survey & Photometric Reconstruction")
        self.resize(1380, 860)
        self.setMinimumSize(960, 600)

        # Hardware Lux Meter Sources Setup (USB Serial + Bluetooth BLE)
        self.manual_source = ManualMeasurementSource(self)
        self.usb_source = USBSerialMeterSource(self)
        self.bt_source = BluetoothMeterSource(self)

        self.usb_source.live_reading_stream.connect(self._on_hardware_stream)
        self.bt_source.live_reading_stream.connect(self._on_hardware_stream)
        self.usb_source.connection_status_changed.connect(self._on_hardware_status_changed)
        self.bt_source.connection_status_changed.connect(self._on_hardware_status_changed)

        # Create Core UI Widgets
        self.canvas_widget = RoomCanvasWidget(self)
        self.survey_widget = SurveyModeWidget(self)
        self.survey_toolbar = QToolBar("Survey controls", self)
        self.survey_toolbar.setMovable(False)
        self.survey_toolbar.setFloatable(False)
        self.survey_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.survey_toolbar.addWidget(self.survey_widget)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, self.survey_toolbar)
        self._edit_return_focus = None
        self.start_screen = StartScreenWidget(self)
        self.start_screen.new_survey_requested.connect(self._on_new_project)
        self.start_screen.open_survey_requested.connect(self._on_open_project)
        self.start_screen.locate_project_requested.connect(self._on_open_project)
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
        self.btn_toggle_left.setToolTip("Toggle Left Panel (Layers & Target)")
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
        self.btn_toggle_right.setToolTip("Toggle Right Panel (KPIs & Measurements)")
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
            name="New survey",
            room=Room(name="Room 1", length=6.0, width=4.0, height=2.8),
        )

    @staticmethod
    def _create_practice_project() -> LuminationProject:
        """Create clearly labeled sample data for practice, never for a new survey."""
        room = Room(name="Office 201", length=6.0, width=4.0, height=2.8, measurement_plane_height=0.75, wall_margin=0.5, traversal_order="serpentine")
        proj = LuminationProject(
            name="Practice — Office Illuminance Survey",
            room=room,
            target_lux=500.0,
            is_practice=True,
        )
        proj.regenerate_grid(mode="count", rows=3, cols=4, wall_margin=0.5, centered_in_cells=True, traversal_order="serpentine")

        sample_lux = [320, 370, 410, 430, 380, 450, 520, 500, 400, 490, 570, 540]
        sample_exp = [350, 400, 450, 450, 400, 500, 550, 500, 420, 500, 580, 550]
        for i, p in enumerate(proj.points):
            if i < len(sample_lux):
                p.lux = float(sample_lux[i])
                p.expected_lux = float(sample_exp[i])

        proj.is_dirty = False
        return proj

    def _show_start_screen(self) -> None:
        self.content_stack.setCurrentWidget(self.start_screen)
        self.dock_left.hide()
        self.dock_right.hide()
        self._sync_workflow_controls()

    def _show_workspace(self) -> None:
        self.content_stack.setCurrentWidget(self.main_workspace)
        if self.workflow_controller.workspace == Workspace.SURVEY:
            self.dock_left.hide()
            self.dock_right.hide()
        else:
            self._show_detail_docks()
        self._sync_workflow_controls()
        self.recalculate_and_refresh()

    @staticmethod
    def _resume_details(project: LuminationProject, prefix: str) -> tuple[str, str]:
        measured = len(project.get_measured_points())
        total = len(project.points)
        title = f"{prefix}: {project.name}"
        detail = f"{measured} of {total} readings recorded. Stored on this computer."
        return title, detail

    def _refresh_start_screen(self) -> None:
        self._resume_candidate = None
        self._resume_kind = None
        self._missing_recent_path = None
        recovery_error: Optional[str] = None
        self.start_screen.btn_resume.setEnabled(True)

        try:
            recovered = self.recovery_store.load()
        except Exception as exc:
            recovered = None
            recovery_error = f"The local recovery file could not be read: {exc}"

        if recovered is not None:
            recovered.project.resume_state = {
                "workspace": recovered.workspace,
                "selected_point_id": recovered.selected_point_id,
            }
            self._resume_candidate = recovered.project
            self._resume_kind = "recovery"
            title, detail = self._resume_details(recovered.project, "Resume recovered survey")
            if recovered.saved_at:
                detail += f" Last recovery saved {recovered.saved_at}."
            self.start_screen.show_resume(title, detail)
            self.start_screen.show_missing_project(None)
            return

        last_path = str(self.settings.value("last_project_path", "") or "")
        if last_path and os.path.isfile(last_path):
            try:
                recent = self._load_project_from_path(last_path)
            except Exception:
                self._missing_recent_path = last_path
            else:
                self._resume_candidate = recent
                self._resume_kind = "recent"
                title, detail = self._resume_details(recent, "Resume last survey")
                self.start_screen.show_resume(title, detail)
        elif last_path:
            self._missing_recent_path = last_path
        if self._resume_candidate is None:
            if recovery_error:
                self.start_screen.show_resume("Recovery needs attention", recovery_error)
                self.start_screen.btn_resume.setEnabled(False)
            else:
                self.start_screen.show_resume(None, None)
        self.start_screen.show_missing_project(self._missing_recent_path)

    def _load_project_from_path(self, file_path: str) -> LuminationProject:
        from persistence.project_io import load_project

        return load_project(file_path)

    def _on_resume_requested(self) -> None:
        if self._resume_candidate is None:
            return
        self._replace_project(self._resume_candidate)
        self._show_workspace()

    def _on_practice_requested(self) -> None:
        self._replace_project(self._create_practice_project())
        self._show_workspace()
        self.status_bar.showMessage("Practice survey — all sample readings are simulated.", 6000)

    def _setup_docks(self) -> None:
        """Configure 2 clean collapsible side panels on left and right."""
        # Panel 1: Left Dock (Layers & Visuals + Target Illuminance)
        self.dock_left = QDockWidget(tr("tab_layers"), self)
        self.dock_left.setObjectName("dock_left")
        self.dock_left.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetClosable |
            QDockWidget.DockWidgetFeature.DockWidgetMovable |
            QDockWidget.DockWidgetFeature.DockWidgetFloatable
        )
        self.dock_left.visibilityChanged.connect(self._on_left_dock_visibility_changed)

        self.left_tabs = QTabWidget(self.dock_left)
        self.left_tabs.addTab(self.layer_widget, tr("tab_layers"))
        self.left_tabs.addTab(self.target_panel, tr("tab_target"))
        left_scroll = QScrollArea(self.dock_left)
        left_scroll.setWidgetResizable(True)
        left_scroll.setWidget(self.left_tabs)
        self.dock_left.setWidget(left_scroll)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.dock_left)

        # Panel 2: Right Dock (Photometric KPIs + Measurements Schedule Table + DIALux)
        self.dock_right = QDockWidget(tr("tab_kpis"), self)
        self.dock_right.setObjectName("dock_right")
        self.dock_right.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetClosable |
            QDockWidget.DockWidgetFeature.DockWidgetMovable |
            QDockWidget.DockWidgetFeature.DockWidgetFloatable
        )
        self.dock_right.visibilityChanged.connect(self._on_right_dock_visibility_changed)

        self.right_tabs = QTabWidget(self.dock_right)
        self.right_tabs.addTab(self.results_panel, tr("tab_kpis"))
        self.right_tabs.addTab(self.table_widget, tr("tab_measurements"))
        self.right_tabs.addTab(self.comparison_panel, tr("tab_simulated"))
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

    def _show_detail_docks(self) -> None:
        self.dock_left.setVisible(self.width() >= 1200)
        self.dock_right.show()
        self.resizeDocks([self.dock_left, self.dock_right], [360, 420], Qt.Orientation.Horizontal)

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
        """Create clean menu hierarchy: File, CSV & Export, Devices, Language, Help."""
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
        self.act_exit.setShortcut(QKeySequence.StandardKey.Quit)
        self.act_exit.triggered.connect(self.close)
        self.menu_file.addAction(self.act_exit)

        self.menu_survey = menubar.addMenu("&Survey")
        self.act_enter_survey = QAction("Survey", self)
        self.act_enter_survey.triggered.connect(self._enter_survey_workspace)
        self.menu_survey.addAction(self.act_enter_survey)
        self.act_enter_review = QAction("Review", self)
        self.act_enter_review.triggered.connect(self._enter_review_workspace)
        self.menu_survey.addAction(self.act_enter_review)
        self.act_edit_survey = QAction("Edit survey…", self)
        self.act_edit_survey.triggered.connect(self._enter_edit_workspace)
        self.menu_survey.addAction(self.act_edit_survey)
        self.act_done_editing = QAction("Done editing", self)
        self.act_done_editing.triggered.connect(self._leave_edit_workspace)
        self.menu_survey.addAction(self.act_done_editing)
        self.menu_survey.addSeparator()
        self.act_generate_grid = QAction("Change measurement grid…", self)
        self.act_generate_grid.triggered.connect(self._on_grid_requested)
        self.menu_survey.addAction(self.act_generate_grid)
        self.act_clear_measurements = QAction("Clear measurements…", self)
        self.act_clear_measurements.triggered.connect(self._on_clear_measurements)
        self.menu_survey.addAction(self.act_clear_measurements)
        self.menu_survey.addSeparator()
        self.act_undo = QAction("Undo", self)
        self.act_undo.setShortcut(QKeySequence.StandardKey.Undo)
        self.act_undo.triggered.connect(self._undo_if_allowed)
        self.menu_survey.addAction(self.act_undo)
        self.act_redo = QAction("Redo", self)
        self.act_redo.setShortcut(QKeySequence.StandardKey.Redo)
        self.act_redo.triggered.connect(self._redo_if_allowed)
        self.menu_survey.addAction(self.act_redo)

        # 2. CSV & Export Menu
        self.menu_export = menubar.addMenu(f"&{tr('menu_csv_export')}")

        self.act_import_csv = QAction(tr("menu_import_csv"), self)
        self.act_import_csv.triggered.connect(self._on_import_csv)
        self.menu_export.addAction(self.act_import_csv)

        self.act_export_csv = QAction(tr("menu_export_csv"), self)
        self.act_export_csv.triggered.connect(self._on_export_csv)
        self.menu_export.addAction(self.act_export_csv)

        self.menu_export.addSeparator()

        self.act_export_pdf = QAction(tr("menu_export_pdf"), self)
        self.act_export_pdf.setShortcut(QKeySequence.StandardKey.Print)
        self.act_export_pdf.triggered.connect(self._on_export_pdf)
        self.menu_export.addAction(self.act_export_pdf)

        self.act_export_img = QAction(tr("menu_export_image"), self)
        self.act_export_img.triggered.connect(self._on_export_image)
        self.menu_export.addAction(self.act_export_img)

        # 3. Devices Menu (Hardware Connectivity)
        self.menu_devices = menubar.addMenu("&Devices")

        self.act_connect_meter = QAction("Device connections…", self)
        self.act_connect_meter.setIcon(create_bluetooth_icon())
        self.act_connect_meter.triggered.connect(self._on_open_hardware_dialog)
        self.menu_devices.addAction(self.act_connect_meter)

        # 4. Language Menu
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

        # 5. Help Menu
        self.menu_help = menubar.addMenu(f"&{tr('menu_help')}")

        self.act_shortcuts = QAction(tr("menu_shortcuts"), self)
        self.act_shortcuts.triggered.connect(self._on_show_shortcuts)
        self.menu_help.addAction(self.act_shortcuts)

        self.act_methodology = QAction(tr("menu_methodology"), self)
        self.act_methodology.triggered.connect(self._on_show_methodology)
        self.menu_help.addAction(self.act_methodology)

        self.menu_help.addSeparator()

        self.act_about = QAction(tr("menu_about"), self)
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

        self.lbl_project_status = QLabel("Ready", self)
        self.lbl_project_status.setStyleSheet("color: #334155; font-size: 11px; padding: 0 6px;")

        self.lbl_hardware_status = QLabel("Meter: Disconnected", self)
        self.lbl_hardware_status.setStyleSheet("color: #64748b; font-size: 11px; font-weight: 600; padding: 0 8px;")
        self.lbl_save_status = QLabel("Not saved", self)
        self.lbl_save_status.setStyleSheet("color: #52606d; font-size: 11px; padding: 0 8px;")

        self.status_bar.addWidget(self.lbl_project_status, stretch=1)
        self.status_bar.addPermanentWidget(self.lbl_save_status)
        self.status_bar.addPermanentWidget(self.lbl_hardware_status)

    def _connect_signals(self) -> None:
        """Connect inter-widget signals."""
        self.canvas_widget.point_selected.connect(self._on_point_selected)
        self.canvas_widget.point_edit_requested.connect(self._on_point_edit_requested)
        self.canvas_widget.point_add_requested.connect(self._on_point_add_requested)
        self.canvas_widget.point_delete_requested.connect(self._on_point_delete_requested)
        self.canvas_widget.measurement_saved.connect(self._on_measurement_recorded)
        self.survey_widget.measurement_saved.connect(self._on_measurement_recorded)
        self.survey_widget.point_navigated.connect(self._on_point_selected)
        self.canvas_widget.hardware_connect_requested.connect(self._on_open_hardware_dialog)
        self.canvas_widget.undo_requested.connect(self._undo_if_allowed)
        self.canvas_widget.redo_requested.connect(self._redo_if_allowed)

        self.table_widget.point_selected.connect(self._on_point_selected)
        self.table_widget.data_changed.connect(self.recalculate_and_refresh)
        self.table_widget.edit_requested.connect(self._on_table_edit_requested)

        self.results_panel.highlight_point_requested.connect(self._on_point_selected)
        self.target_panel.target_changed.connect(self._on_target_changed)
        self.comparison_panel.display_mode_changed.connect(self._on_display_settings_changed)
        self.layer_widget.settings_changed.connect(self._on_display_settings_changed)

    def retranslate_ui(self) -> None:
        """Update window, menus, and side panel tabs when language switches."""
        self.setWindowTitle(f"Lumination — {tr('dlg_new_project_title')} [{self.project.name}]")
        self._setup_menus()

        self.dock_left.setWindowTitle(tr("tab_layers"))
        self.left_tabs.setTabText(0, tr("tab_layers"))
        self.left_tabs.setTabText(1, tr("tab_target"))

        self.dock_right.setWindowTitle(tr("tab_kpis"))
        self.right_tabs.setTabText(0, tr("tab_kpis"))
        self.right_tabs.setTabText(1, tr("tab_measurements"))
        self.right_tabs.setTabText(2, tr("tab_simulated"))

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
                    extrapolate_to_walls=False,
                    allow_negative=display_mode == "difference",
                )
            else:
                self.interp_result = None

            self.canvas_widget.set_project(
                self.project,
                interp_result=self.interp_result,
                selected_point_id=self.active_point_id,
            )

            r = self.project.room
            n_meas = len(self.project.get_measured_points())
            n_tot = len(self.project.points)
            u0_str = f"U₀: {stats.uniformity_u0:.2f}" if stats else "U₀: -"
            avg_str = f"Avg: {stats.e_avg:.0f} lx" if stats else "Avg: - lx"

            practice_prefix = "PRACTICE — " if self.project.is_practice else ""
            self.lbl_project_status.setText(
                f"{practice_prefix}{r.length:.1f}×{r.width:.1f}m ({r.area:.1f}m²) | "
                f"{n_meas}/{n_tot} measured | {avg_str} | {u0_str}"
            )
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
            self.canvas_widget.set_selected_point_id(point_id)
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
        device_name: str = "Manual Entry",
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
        if not self.workflow_controller.allows(operation):
            self.status_bar.showMessage("Enter Edit mode to change an existing reading.", 5000)
            return False
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
                self.status_bar.showMessage("Survey complete. Every point has a reading.", 5000)
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
        if self.workflow_controller.allows(Operation.CHANGE_TARGET):
            self.recalculate_and_refresh()
            self._write_recovery_snapshot()

    def _on_display_settings_changed(self, _value=None) -> None:
        if self.workflow_controller.allows(Operation.CHANGE_DISPLAY):
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
            self.lbl_save_status.setText("Recovery saved locally")
            self.lbl_save_status.setToolTip("The current working copy is stored in the local recovery file.")
        except Exception as exc:
            self.lbl_save_status.setText("Recovery save failed")
            self.lbl_save_status.setToolTip(f"The change remains in memory. Recovery could not be saved: {exc}")

    def _sync_workflow_controls(self) -> None:
        active = self.content_stack.currentWidget() is self.main_workspace
        editing = self.workflow_controller.workspace == Workspace.EDIT
        surveying = self.workflow_controller.workspace == Workspace.SURVEY
        self.survey_toolbar.setVisible(active and self.workflow_controller.workspace != Workspace.REVIEW)
        self.menu_survey.setEnabled(active)
        self.menu_export.setEnabled(active)
        self.menu_devices.setEnabled(active)
        self.act_save.setEnabled(active)
        self.act_save_as.setEnabled(active)
        self.survey_widget.set_workflow_permissions(
            recording=surveying or editing,
            correction=editing,
        )
        self.table_widget.set_edit_allowed(editing)
        self.canvas_widget.set_editing_enabled(editing)
        self.canvas_widget.set_recording_enabled(active and (surveying or editing))
        self.canvas_widget.btn_undo.setEnabled(
            self.undo_stack.canUndo() and self._command_allowed(undo=True)
        )
        self.canvas_widget.btn_redo.setEnabled(
            self.undo_stack.canRedo() and self._command_allowed(undo=False)
        )
        self.act_done_editing.setEnabled(editing)
        self.act_edit_survey.setEnabled(not editing)
        self.act_generate_grid.setEnabled(editing)
        self.act_clear_measurements.setEnabled(editing)
        self.act_import_csv.setEnabled(editing)
        self.act_enter_review.setEnabled(not editing)
        self.act_enter_survey.setEnabled(not editing)
        self.act_undo.setEnabled(self.undo_stack.canUndo() and self._command_allowed(undo=True))
        self.act_redo.setEnabled(self.undo_stack.canRedo() and self._command_allowed(undo=False))

    def _on_history_changed(self, _enabled: bool) -> None:
        self._sync_workflow_controls()

    def _enter_survey_workspace(self) -> None:
        self.workflow_controller.enter_survey()
        self.dock_left.hide()
        self.dock_right.hide()
        self._sync_workflow_controls()
        self.status_bar.showMessage("Survey mode", 2500)

    def _enter_review_workspace(self) -> None:
        self.workflow_controller.enter_review()
        self._show_detail_docks()
        self._sync_workflow_controls()
        self.status_bar.showMessage("Review mode. Enter Edit mode to change survey data.", 4000)

    def _enter_edit_workspace(self) -> None:
        if self.workflow_controller.workspace != Workspace.EDIT:
            self._edit_return_focus = QApplication.focusWidget()
        self.workflow_controller.enter_edit()
        self._show_detail_docks()
        self._sync_workflow_controls()
        self.status_bar.showMessage("Edit mode. Survey changes are undoable.", 4000)

    def _leave_edit_workspace(self) -> None:
        point_id = self.workflow_controller.leave_edit({point.id for point in self.project.points})
        if point_id is None and self.project.points:
            point_id = next(
                (point.id for point in self.project.get_unmeasured_points()),
                self.project.points[0].id,
            )
        self._sync_workflow_controls()
        if point_id:
            self._on_point_selected(point_id)
        if self.workflow_controller.workspace == Workspace.SURVEY:
            self.dock_left.hide()
            self.dock_right.hide()
        if self._edit_return_focus is not None and self._edit_return_focus.isVisible():
            self._edit_return_focus.setFocus()
        self._edit_return_focus = None
        self.status_bar.showMessage("Returned to the previous workspace.", 3000)

    def _command_allowed(self, undo: bool) -> bool:
        index = self.undo_stack.index() - 1 if undo else self.undo_stack.index()
        if index < 0 or index >= self.undo_stack.count():
            return False
        command_object = self.undo_stack.command(index)
        operation_name = getattr(command_object, "workflow_operation", "change_point")
        try:
            operation = Operation(operation_name)
        except ValueError:
            return False
        return self.workflow_controller.allows(operation)

    def _undo_if_allowed(self) -> None:
        if self.undo_stack.canUndo() and self._command_allowed(undo=True):
            self.undo_stack.undo()
        elif self.undo_stack.canUndo():
            self.status_bar.showMessage("Enter Edit mode to undo survey structure changes.", 4000)

    def _redo_if_allowed(self) -> None:
        if self.undo_stack.canRedo() and self._command_allowed(undo=False):
            self.undo_stack.redo()
        elif self.undo_stack.canRedo():
            self.status_bar.showMessage("Enter Edit mode to redo survey structure changes.", 4000)

    def _on_table_edit_requested(self, point_id: str, column: int, value: object) -> None:
        if not self.workflow_controller.allows(Operation.CHANGE_POINT):
            self.status_bar.showMessage("Choose Survey → Edit survey before changing table values.", 5000)
            self.table_widget.refresh()
            return
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
        if not self.workflow_controller.allows(Operation.CHANGE_ROOM_OR_GRID):
            return
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
        if not self.workflow_controller.allows(Operation.CHANGE_POINT):
            return
        if QMessageBox.question(
            self,
            "Clear measurements",
            "Clear every recorded lux value? You can undo this action.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        ) != QMessageBox.StandardButton.Yes:
            return
        self.undo_stack.push(ClearMeasurementsCommand(self.project, self._on_data_modified))

    def _on_point_edit_requested(self, point_id: str) -> None:
        if not self.workflow_controller.allows(Operation.CHANGE_POINT):
            self.status_bar.showMessage("Choose Survey → Edit survey to change point details.", 5000)
            return
        pt = self.project.find_point_by_id(point_id)
        if pt:
            dlg = PointEditDialog(copy.deepcopy(pt), self.project.room, self)
            if dlg.exec() == PointEditDialog.DialogCode.Accepted:
                self.undo_stack.push(UpdatePointCommand(self.project, dlg.point, self._on_data_modified))

    def _on_point_add_requested(self, x: float, y: float) -> None:
        if not self.workflow_controller.allows(Operation.CHANGE_POINT):
            self.status_bar.showMessage("Choose Survey → Edit survey before adding a point.", 5000)
            return
        candidate = copy.deepcopy(self.project)
        pt = candidate.add_custom_point(x, y, notes="Custom Sensor")
        cmd = ReplaceProjectDataCommand(self.project, candidate, f"Add Point {pt.id}", self._on_data_modified)
        self.undo_stack.push(cmd)
        self._on_point_selected(pt.id)

    def _on_point_delete_requested(self, point_id: str) -> None:
        if not self.workflow_controller.allows(Operation.CHANGE_POINT):
            self.status_bar.showMessage("Choose Survey → Edit survey before deleting a point.", 5000)
            return
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
            self.canvas_widget.set_selected_point_id(None)

    def _on_open_hardware_dialog(self) -> None:
        dlg = HardwareConnectionDialog(self.usb_source, self.bt_source, self)
        dlg.reading_captured.connect(self._on_hardware_reading_captured)
        dlg.exec()

    def _on_hardware_reading_captured(self, sample: MeasurementSample) -> None:
        """Capture one validated, identified meter sample into the active point."""
        if not self.active_point_id and self.project.points:
            self.active_point_id = next(
                (point.id for point in self.project.get_unmeasured_points()),
                None,
            )
            self.workflow_controller.select_point(self.active_point_id)

        if self.active_point_id:
            self._on_measurement_recorded(
                self.active_point_id,
                sample.lux,
                operation_id=sample.sample_id,
                device_name=(
                    f"Practice ({sample.profile_id or sample.source_id})"
                    if sample.simulated
                    else sample.profile_id or sample.source_id
                ),
                profile_id=sample.profile_id,
            )

    def _on_hardware_stream(self, lux: float) -> None:
        """Handle continuous stream reading from connected USB or Bluetooth meter."""
        source_name = "USB" if self.usb_source.is_connected else "Bluetooth"
        self.lbl_hardware_status.setText(
            f"Meter: {source_name} raw stream — no verified profile; capture unavailable"
        )
        self.lbl_hardware_status.setStyleSheet("color: #92400e; font-size: 11px; font-weight: 600; padding: 0 8px;")
        self.lbl_hardware_status.setToolTip(f"Unverified stream value: {lux:.1f} lx")

    def _on_hardware_status_changed(self, connected: bool, desc: str) -> None:
        lower_desc = desc.lower()
        if any(term in lower_desc for term in ("unverified", "unsupported", "no qualified", "no verified", "simulated")):
            self.lbl_hardware_status.setText(f"Meter: {desc}")
            self.lbl_hardware_status.setStyleSheet("color: #92400e; font-size: 11px; font-weight: 600; padding: 0 8px;")
        elif connected:
            self.lbl_hardware_status.setText(f"Meter: {desc}")
            self.lbl_hardware_status.setStyleSheet("color: #16a34a; font-size: 11px; font-weight: bold; padding: 0 8px;")
        else:
            self.lbl_hardware_status.setText("Meter: Disconnected")
            self.lbl_hardware_status.setStyleSheet("color: #64748b; font-size: 11px; font-weight: 600; padding: 0 8px;")

    # --- Menu Handlers ---

    def _confirm_project_replacement(self) -> bool:
        self._discard_recovery_after_replace = False
        if not self.project.is_dirty:
            return True
        choice = QMessageBox(self)
        choice.setIcon(QMessageBox.Icon.Warning)
        choice.setWindowTitle("Unsaved survey")
        choice.setText("This survey has changes that are not saved to its project file.")
        choice.setInformativeText("Save before replacing it?")
        choice.setStandardButtons(
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel
        )
        choice.setDefaultButton(QMessageBox.StandardButton.Save)
        result = choice.exec()
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
        if resume.get("workspace") == Workspace.REVIEW.value:
            self.workflow_controller.enter_review()
        valid_ids = {point.id for point in project.points}
        point_id = resume.get("selected_point_id")
        if point_id not in valid_ids:
            point_id = next(
                (point.id for point in project.get_unmeasured_points()),
                project.points[0].id if project.points else None,
            )
        self.active_point_id = point_id
        self.workflow_controller.select_point(point_id)
        self.undo_stack.clear()
        self._sync_workflow_controls()
        self.load_project_into_ui()
        self.lbl_save_status.setText("Saved locally" if not project.is_dirty and project.file_path else "Not saved")

    def _on_new_project(self) -> None:
        dlg = SurveySetupDialog(self)
        if dlg.exec() == SurveySetupDialog.DialogCode.Accepted:
            new_proj = dlg.get_created_project()
            if new_proj and self._confirm_project_replacement():
                self._replace_project(new_proj)
                self._show_workspace()
                updated, created = dlg.import_counts
                if updated or created:
                    self.status_bar.showMessage(
                        f"Survey created with {updated} imported readings and {created} imported points.", 5000
                    )

    def _on_open_project(self) -> None:
        from persistence.project_io import load_project
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Lumination Project",
            "",
            "Lumination Project (*.luxproj);;JSON Files (*.json);;All Files (*.*)",
        )
        if file_path:
            if not self._confirm_project_replacement():
                return
            try:
                proj = load_project(file_path)
                self._replace_project(proj)
                self.settings.setValue("last_project_path", file_path)
                self._show_workspace()
                self.status_bar.showMessage(f"Project loaded: {os.path.basename(file_path)}", 4000)
            except Exception as e:
                QMessageBox.critical(self, "Load Error", f"Failed to load project file:\n{e}")

    def _save_resume_context(self) -> None:
        workspace = self.workflow_controller.workspace
        if workspace == Workspace.EDIT:
            workspace = self.workflow_controller.snapshot().edit_return_workspace or Workspace.SURVEY
        self.project.resume_state = {
            "workspace": workspace.value,
            "selected_point_id": self.active_point_id,
        }

    def _on_save_project(self) -> bool:
        self._save_resume_context()
        if not self.project.file_path:
            return self._on_save_project_as()
        from persistence.project_io import save_project
        try:
            save_project(self.project, self.project.file_path)
            self.settings.setValue("last_project_path", self.project.file_path)
            self.recovery_store.discard()
            self.lbl_save_status.setText("Saved locally")
            self.lbl_save_status.setToolTip(self.project.file_path)
            self.status_bar.showMessage("Project saved successfully.", 3000)
            return True
        except Exception as e:
            self.lbl_save_status.setText("Save failed")
            self.lbl_save_status.setToolTip(f"Changes remain in memory. Save failed: {e}")
            QMessageBox.critical(self, "Save Error", f"Failed to save project:\n{e}")
            return False

    def _on_save_project_as(self) -> bool:
        self._save_resume_context()
        from persistence.project_io import save_project
        default_name = f"{self.project.name.replace(' ', '_').lower()}.luxproj"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Lumination Project As",
            default_name,
            "Lumination Project (*.luxproj);;All Files (*.*)",
        )
        if file_path:
            try:
                save_project(self.project, file_path)
                self.settings.setValue("last_project_path", file_path)
                self.recovery_store.discard()
                self.lbl_save_status.setText("Saved locally")
                self.lbl_save_status.setToolTip(file_path)
                self.status_bar.showMessage(f"Saved as: {os.path.basename(file_path)}", 4000)
                return True
            except Exception as e:
                self.lbl_save_status.setText("Save failed")
                self.lbl_save_status.setToolTip(f"Changes remain in memory. Save failed: {e}")
                QMessageBox.critical(self, "Save Error", f"Failed to save project file:\n{e}")
                return False
        return False

    def closeEvent(self, event: QCloseEvent) -> None:
        """Protect dirty project changes before the window is closed."""
        if not self.project.is_dirty:
            event.accept()
            return

        choice = QMessageBox(self)
        choice.setIcon(QMessageBox.Icon.Warning)
        choice.setWindowTitle("Unsaved survey")
        choice.setText("This survey has changes that are not saved to its project file.")
        choice.setInformativeText("Save the project before closing?")
        choice.setStandardButtons(
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel
        )
        choice.setDefaultButton(QMessageBox.StandardButton.Save)
        result = choice.exec()

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

    def _on_import_csv(self) -> None:
        if not self.workflow_controller.allows(Operation.IMPORT_READINGS):
            self.status_bar.showMessage("Choose Survey → Edit survey before importing measurements.", 5000)
            return
        from persistence.csv_io import import_measurements_from_csv
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Measurements CSV",
            "",
            "CSV Files (*.csv);;Text Files (*.txt);;All Files (*.*)",
        )
        if file_path:
            try:
                candidate = copy.deepcopy(self.project)
                upd, crt = import_measurements_from_csv(candidate, file_path)
                if not upd and not crt:
                    self.status_bar.showMessage("The file contained no importable measurements.", 5000)
                    return
                preview = ImportPreviewDialog(candidate, upd, crt, self)
                if preview.exec() != ImportPreviewDialog.DialogCode.Accepted:
                    return
                self.undo_stack.push(
                    ReplaceProjectDataCommand(
                        self.project,
                        candidate,
                        "Import Measurements",
                        self._on_data_modified,
                    )
                )
                self.status_bar.showMessage(
                    f"Import applied: {upd} points updated, {crt} new points added.", 5000
                )
            except Exception as e:
                QMessageBox.critical(self, "Import Error", f"Failed to import CSV:\n{e}")

    def _on_export_csv(self) -> None:
        from persistence.csv_io import export_measurements_to_csv
        default_name = f"{self.project.name.replace(' ', '_').lower()}_measurements.csv"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Measurements to CSV",
            default_name,
            "CSV Files (*.csv);;All Files (*.*)",
        )
        if file_path:
            try:
                export_measurements_to_csv(self.project, file_path)
                QMessageBox.information(self, "Export Successful", f"Measurements exported to:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Failed to export CSV:\n{e}")

    def _on_export_pdf(self) -> None:
        from reporting.pdf_report import generate_pdf_report
        default_name = f"{self.project.name.replace(' ', '_').lower()}_report.pdf"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export PDF Survey Report",
            default_name,
            "PDF Documents (*.pdf);;All Files (*.*)",
        )
        if file_path:
            try:
                generate_pdf_report(self.project, file_path)
                QMessageBox.information(self, "PDF Report Generated", f"Report saved successfully to:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "PDF Export Error", f"Failed to generate PDF report:\n{e}")

    def _on_export_image(self) -> None:
        from reporting.chart_exporter import export_room_map_image
        default_name = f"{self.project.name.replace(' ', '_').lower()}_map.png"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export High-Resolution Map Image",
            default_name,
            "PNG Images (*.png);;JPEG Images (*.jpg);;PDF Document (*.pdf);;All Files (*.*)",
        )
        if file_path:
            try:
                img_bytes = export_room_map_image(self.project, dpi=300)
                with open(file_path, "wb") as f:
                    f.write(img_bytes)
                QMessageBox.information(self, "Export Successful", f"High-resolution map saved to:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Failed to save image:\n{e}")

    def _on_show_shortcuts(self) -> None:
        QMessageBox.information(
            self,
            "Keyboard Shortcuts Reference",
            "<h3>Lumination Keyboard Shortcuts</h3>"
            "<ul>"
            "<li><b>Click point</b>: Select a point; enter pending readings in Survey, or correct recorded readings in Edit</li>"
            "<li><b>Enter in the reading field</b>: Record a valid reading and select the next pending point</li>"
            "<li><b>Backspace / Delete on the map in Edit mode</b>: Delete the selected point</li>"
            "<li><b>Ctrl + Z</b>: Undo last action</li>"
            f"<li><b>{self.act_redo.shortcut().toString(QKeySequence.SequenceFormat.NativeText)}</b>: Redo undone action</li>"
            "<li><b>Ctrl + S</b>: Save project</li>"
            "<li><b>Ctrl + O</b>: Open project</li>"
            "<li><b>Ctrl + N</b>: Create new room project</li>"
            "<li><b>Mouse Wheel</b>: Zoom in / Zoom out on room canvas</li>"
            "<li><b>Escape</b>: Exit custom point placement mode / close editor tag</li>"
            "</ul>",
        )

    def _on_show_methodology(self) -> None:
        QMessageBox.information(
            self,
            "Measurement & Reconstruction Methodology",
            "<h3>Physical Illuminance Reconstruction</h3>"
            "<p>Lumination is designed for real physical lux meter surveys.</p>"
            "<p><b>Spatial Interpolation:</b> 2D Scipy spatial algorithms (Linear, Cubic, RBF) "
            "reconstruct the continuous illuminance field across the room measurement plane from discrete physical readings.</p>"
            "<p><b>Scientific Integrity:</b> Raw physical measurements remain immutable. "
            "Interpolated values represent mathematical estimates and are clearly distinguished from recorded points.</p>",
        )

    def _on_about(self) -> None:
        QMessageBox.about(
            self,
            "About Lumination",
            "<h2>Lumination</h2>"
            "<p><b>Real-Room Illuminance Survey & Photometric Analysis</b></p>"
            "<p>Version 1.4.0</p>"
            "<p>Engineered for precision physical lighting audits, hardware lux meter acquisition, and spatial illuminance reconstruction.</p>",
        )
