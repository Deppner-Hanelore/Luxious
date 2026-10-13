"""Three-step, offline setup for a new room survey."""

from __future__ import annotations

import copy
from typing import Optional

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from models.project import LuminationProject
from models.room import Room
from persistence.csv_io import import_measurements_from_csv
from ui.dialogs.import_preview_dialog import ImportPreviewDialog


class SurveySetupDialog(QDialog):
    """Ask only for room, measurement points, and how readings will be supplied."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("New survey")
        self.setMinimumSize(520, 420)
        self._imported_project: Optional[LuminationProject] = None
        self._import_counts = (0, 0)
        self.pages = QStackedWidget(self)
        self.page_titles = ["1 of 3 · Room", "2 of 3 · Points", "3 of 3 · Readings"]

        room_page = QWidget(self)
        room_form = QFormLayout(room_page)
        self.name = QLineEdit("Room 1", room_page)
        self.author = QLineEdit(room_page)
        self.author.setPlaceholderText("Optional")
        self.length = self._number(1.0, 200.0, 6.0, 0.5, " m", room_page)
        self.width = self._number(1.0, 200.0, 4.0, 0.5, " m", room_page)
        self.height = self._number(1.5, 30.0, 2.8, 0.1, " m", room_page)
        self.plane = self._number(0.0, 10.0, 0.75, 0.05, " m", room_page)
        room_form.addRow("Room or project name", self.name)
        room_form.addRow("Surveyor name", self.author)
        room_form.addRow("Length", self.length)
        room_form.addRow("Width", self.width)
        room_form.addRow("Room height", self.height)
        room_form.addRow("Measurement plane height", self.plane)
        self.pages.addWidget(room_page)

        points_page = QWidget(self)
        points_form = QFormLayout(points_page)
        self.grid_mode = QComboBox(points_page)
        self.grid_mode.addItem("Number of points", "count")
        self.grid_mode.addItem("Distance between points", "spacing")
        self.cols = QSpinBox(points_page)
        self.cols.setRange(1, 50)
        self.cols.setValue(4)
        self.rows = QSpinBox(points_page)
        self.rows.setRange(1, 50)
        self.rows.setValue(3)
        self.margin = self._number(0.0, 10.0, 0.5, 0.1, " m", points_page)
        self.spacing_x = self._number(0.1, 20.0, 1.0, 0.1, " m", points_page)
        self.spacing_y = self._number(0.1, 20.0, 1.0, 0.1, " m", points_page)
        self.spacing_x.setEnabled(False)
        self.spacing_y.setEnabled(False)
        self.traversal = QComboBox(points_page)
        self.traversal.addItem("Serpentine (back and forth)", "serpentine")
        self.traversal.addItem("Row by row", "left_to_right")
        points_form.addRow("Set points by", self.grid_mode)
        points_form.addRow("Points across the room", self.cols)
        points_form.addRow("Rows", self.rows)
        points_form.addRow("Spacing across the room", self.spacing_x)
        points_form.addRow("Spacing between rows", self.spacing_y)
        points_form.addRow("Distance from walls", self.margin)
        points_form.addRow("Walking order", self.traversal)
        hint = QLabel("These points start as pending. You can change the grid later.", points_page)
        hint.setWordWrap(True)
        points_form.addRow(hint)
        self.pages.addWidget(points_page)

        readings_page = QWidget(self)
        readings_layout = QVBoxLayout(readings_page)
        readings_layout.addWidget(QLabel("Choose how readings will be added. You can start without a meter or internet."))
        self.reading_method = QComboBox(readings_page)
        self.reading_method.addItem("Enter readings manually", "manual")
        self.reading_method.addItem("Import readings from a CSV file…", "csv")
        readings_layout.addWidget(self.reading_method)
        self.setup_summary = QLabel(readings_page)
        self.setup_summary.setWordWrap(True)
        self.setup_summary.setStyleSheet("background: #f1f5f9; border: 1px solid #cbd5e1; padding: 10px;")
        readings_layout.addWidget(self.setup_summary)
        self.import_button = QPushButton("Choose CSV and preview…", readings_page)
        self.import_button.setMinimumHeight(44)
        self.import_button.clicked.connect(self._choose_csv)
        readings_layout.addWidget(self.import_button)
        self.import_status = QLabel("No file selected. You can also import later.", readings_page)
        self.import_status.setWordWrap(True)
        readings_layout.addWidget(self.import_status)
        readings_layout.addStretch(1)
        self.reading_method.currentIndexChanged.connect(self._on_reading_method_changed)
        self.import_button.hide()
        self.pages.addWidget(readings_page)

        self.step_label = QLabel(self.page_titles[0], self)
        self.step_label.setStyleSheet("font-weight: 600; font-size: 12pt;")
        self.back_button = QPushButton("Back", self)
        self.next_button = QPushButton("Next", self)
        self.next_button.setDefault(True)
        self.cancel_button = QPushButton("Cancel", self)
        self.back_button.clicked.connect(self._back)
        self.next_button.clicked.connect(self._next)
        self.cancel_button.clicked.connect(self.reject)
        nav = QHBoxLayout()
        nav.addWidget(self.back_button)
        nav.addStretch(1)
        nav.addWidget(self.cancel_button)
        nav.addWidget(self.next_button)
        layout = QVBoxLayout(self)
        layout.addWidget(self.step_label)
        layout.addWidget(self.pages, 1)
        layout.addLayout(nav)
        self._update_navigation()
        for field in (self.name, self.author):
            field.textChanged.connect(self._invalidate_import_preview)
        for field in (self.length, self.width, self.height, self.plane, self.margin, self.spacing_x, self.spacing_y):
            field.valueChanged.connect(self._invalidate_import_preview)
        for field in (self.cols, self.rows):
            field.valueChanged.connect(self._invalidate_import_preview)
        self.traversal.currentIndexChanged.connect(self._invalidate_import_preview)
        self.grid_mode.currentIndexChanged.connect(self._on_grid_mode_changed)

    def _on_grid_mode_changed(self, _index: int) -> None:
        count = self.grid_mode.currentData() == "count"
        self.cols.setEnabled(count)
        self.rows.setEnabled(count)
        self.spacing_x.setEnabled(not count)
        self.spacing_y.setEnabled(not count)
        self._invalidate_import_preview()

    @staticmethod
    def _number(minimum: float, maximum: float, value: float, step: float, suffix: str, parent: QWidget) -> QDoubleSpinBox:
        widget = QDoubleSpinBox(parent)
        widget.setRange(minimum, maximum)
        widget.setValue(value)
        widget.setSingleStep(step)
        widget.setSuffix(suffix)
        widget.setMinimumHeight(36)
        return widget

    def _back(self) -> None:
        self.pages.setCurrentIndex(max(0, self.pages.currentIndex() - 1))
        self._update_navigation()

    def _next(self) -> None:
        if self.pages.currentIndex() == 0 and self.plane.value() > self.height.value():
            QMessageBox.information(self, "Check measurement height", "The measurement plane must be at or below the room height.")
            return
        if self.pages.currentIndex() == 1 and 2 * self.margin.value() >= min(self.length.value(), self.width.value()):
            QMessageBox.information(self, "Check wall distance", "The distance from walls must leave space for measurement points inside the room.")
            return
        if self.pages.currentIndex() < 2:
            self.pages.setCurrentIndex(self.pages.currentIndex() + 1)
            self._update_navigation()
        else:
            if self.reading_method.currentData() == "csv" and self._imported_project is None:
                QMessageBox.information(
                    self,
                    "Preview the CSV first",
                    "Choose a CSV file and review its readings, or switch to manual entry.",
                )
                return
            self.accept()

    def _update_navigation(self) -> None:
        index = self.pages.currentIndex()
        self.step_label.setText(self.page_titles[index])
        self.back_button.setEnabled(index > 0)
        self.next_button.setText("Create survey" if index == 2 else "Next")
        if index == 2:
            self._update_setup_summary()

    def _update_setup_summary(self) -> None:
        source = "CSV import (previewed)" if self._imported_project is not None else str(self.reading_method.currentData())
        if source == "manual":
            source = "Manual entry"
        elif source == "csv":
            source = "CSV import (not yet previewed)"
        grid = (
            f"{self.cols.value()} columns × {self.rows.value()} rows"
            if self.grid_mode.currentData() == "count"
            else f"point spacing {self.spacing_x.value():g} × {self.spacing_y.value():g} m"
        )
        self.setup_summary.setText(
            f"Setup: {self.length.value():g} × {self.width.value():g} m room; "
            f"{grid}; "
            f"measurement plane {self.plane.value():g} m; "
            f"{self.margin.value():g} m from walls; source: {source}."
        )

    def _on_reading_method_changed(self, _index: int) -> None:
        is_csv = self.reading_method.currentData() == "csv"
        self.import_button.setVisible(is_csv)
        if not is_csv and self._imported_project is not None:
            self._imported_project = None
            self._import_counts = (0, 0)
            self.import_status.setText("Manual entry selected. Imported readings were removed from this draft.")
        self._update_setup_summary()

    def _build_project(self) -> LuminationProject:
        name = self.name.text().strip() or "Room 1"
        room = Room(
            name=name,
            length=self.length.value(),
            width=self.width.value(),
            height=self.height.value(),
            measurement_plane_height=self.plane.value(),
            wall_margin=self.margin.value(),
            grid_cols=self.cols.value(),
            grid_rows=self.rows.value(),
            traversal_order=str(self.traversal.currentData()),
        )
        project = LuminationProject(name=name, author=self.author.text().strip(), room=room, target_lux=None)
        project.regenerate_grid(
            mode=str(self.grid_mode.currentData()),
            rows=self.rows.value(),
            cols=self.cols.value(),
            spacing_x=self.spacing_x.value(),
            spacing_y=self.spacing_y.value(),
            wall_margin=self.margin.value(),
            centered_in_cells=True,
            traversal_order=str(self.traversal.currentData()),
        )
        return project

    def _choose_csv(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Import readings", "", "CSV Files (*.csv);;Text Files (*.txt);;All Files (*.*)"
        )
        if not file_path:
            return
        try:
            candidate = self._build_project()
            updated, created = import_measurements_from_csv(candidate, file_path)
            if not updated and not created:
                QMessageBox.information(self, "No readings found", "That file had no readings that could be imported.")
                return
            preview = ImportPreviewDialog(candidate, updated, created, self)
            if preview.exec() == QDialog.DialogCode.Accepted:
                self._imported_project = candidate
                self._import_counts = (updated, created)
                self.reading_method.setCurrentIndex(1)
                self.import_status.setText(f"Preview accepted: {updated} points updated, {created} added.")
                self._update_setup_summary()
        except Exception as exc:
            QMessageBox.critical(self, "Import failed", f"The survey was not changed.\n\n{exc}")

    def _invalidate_import_preview(self, *_args) -> None:
        if self._imported_project is not None:
            self._imported_project = None
            self._import_counts = (0, 0)
            self.import_status.setText("Setup changed. Review the CSV again or enter readings manually.")

    def get_created_project(self) -> LuminationProject:
        project = copy.deepcopy(self._imported_project) if self._imported_project is not None else self._build_project()
        project.is_dirty = True
        return project

    @property
    def import_counts(self) -> tuple[int, int]:
        return self._import_counts
