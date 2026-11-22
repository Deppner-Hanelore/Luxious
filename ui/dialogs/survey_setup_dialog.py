"""Three-step, offline setup for a new room survey."""

from __future__ import annotations

import copy
from typing import Optional

from PySide6.QtCore import QSettings

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
    QMenuBar,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from models.project import LuminationProject
from models.room import Room
from i18n.translations import tr, TranslationManager, LANGUAGE_NAMES, SUPPORTED_LANGUAGES
from persistence.table_io import TableError, apply_table_to_project, read_table
from ui.dialogs.import_preview_dialog import ImportPreviewDialog


class SurveySetupDialog(QDialog):
    """Ask only for room, measurement points, and how readings will be supplied."""

    DEFAULTS_GROUP = "new_survey_defaults"

    def __init__(self, parent: Optional[QWidget] = None, settings: Optional[QSettings] = None) -> None:
        super().__init__(parent)
        self._settings = settings if settings is not None else QSettings()
        self.setWindowTitle(tr("setup_title"))
        self.setMinimumSize(520, 420)
        # The pair of fields that "Set points by" does not use is switched off; make that visible
        # (greyed text and background, greyed label) so only the active pair looks usable.
        self.setStyleSheet("""
            QSpinBox:disabled, QDoubleSpinBox:disabled {
                color: #94a3b8;
                background-color: #f1f5f9;
                border-color: #e2e8f0;
            }
            QLabel:disabled { color: #94a3b8; }
        """)
        self._imported_project: Optional[LuminationProject] = None
        self._import_counts = (0, 0)
        self.pages = QStackedWidget(self)
        self.page_titles = [tr("setup_step_room"), tr("setup_step_points"), tr("setup_step_readings")]
        self._import_status = ("setup_no_file", {})

        room_page = QWidget(self)
        room_form = QFormLayout(room_page)
        self.room_form = room_form
        self.name = QLineEdit(tr("room_default_name"), room_page)
        self.author = QLineEdit(room_page)
        self.author.setPlaceholderText(tr("setup_optional"))
        self.length = self._number(1.0, 200.0, 6.0, 0.5, " m", room_page)
        self.width = self._number(1.0, 200.0, 4.0, 0.5, " m", room_page)
        room_form.addRow(tr("setup_name"), self.name)
        room_form.addRow(tr("setup_surveyor"), self.author)
        room_form.addRow(tr("setup_length"), self.length)
        room_form.addRow(tr("setup_width"), self.width)
        self.pages.addWidget(room_page)

        points_page = QWidget(self)
        points_form = QFormLayout(points_page)
        self.points_form = points_form
        self.grid_mode = QComboBox(points_page)
        self.grid_mode.addItem(tr("setup_mode_count"), "count")
        self.grid_mode.addItem(tr("setup_mode_spacing"), "spacing")
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
        self.traversal.addItem(tr("setup_traversal_serpentine"), "serpentine")
        self.traversal.addItem(tr("setup_traversal_rows"), "left_to_right")
        points_form.addRow(tr("setup_points_by"), self.grid_mode)
        points_form.addRow(tr("setup_cols"), self.cols)
        points_form.addRow(tr("setup_rows"), self.rows)
        points_form.addRow(tr("setup_spacing_x"), self.spacing_x)
        points_form.addRow(tr("setup_spacing_y"), self.spacing_y)
        points_form.addRow(tr("setup_margin"), self.margin)
        points_form.addRow(tr("setup_walking_order"), self.traversal)
        hint = QLabel(tr("setup_points_hint"), points_page)
        self.points_hint = hint
        hint.setWordWrap(True)
        points_form.addRow(hint)
        self.pages.addWidget(points_page)

        readings_page = QWidget(self)
        readings_layout = QVBoxLayout(readings_page)
        self.readings_intro = QLabel(tr("setup_readings_intro"))
        self.readings_intro.setWordWrap(True)
        readings_layout.addWidget(self.readings_intro)
        self.reading_method = QComboBox(readings_page)
        self.reading_method.addItem(tr("setup_method_manual"), "manual")
        self.reading_method.addItem(tr("setup_method_csv"), "csv")
        readings_layout.addWidget(self.reading_method)
        self.setup_summary = QLabel(readings_page)
        self.setup_summary.setWordWrap(True)
        self.setup_summary.setStyleSheet("background: #f1f5f9; border: 1px solid #cbd5e1; padding: 10px;")
        readings_layout.addWidget(self.setup_summary)
        self.import_button = QPushButton(tr("setup_choose_csv"), readings_page)
        self.import_button.setMinimumHeight(44)
        self.import_button.clicked.connect(self._choose_csv)
        readings_layout.addWidget(self.import_button)
        self.import_status = QLabel(tr("setup_no_file"), readings_page)
        self.import_status.setWordWrap(True)
        readings_layout.addWidget(self.import_status)
        readings_layout.addStretch(1)
        self.reading_method.currentIndexChanged.connect(self._on_reading_method_changed)
        self.import_button.hide()
        self.pages.addWidget(readings_page)

        self.step_label = QLabel(self.page_titles[0], self)
        self.step_label.setStyleSheet("font-weight: 600; font-size: 12pt;")
        self.back_button = QPushButton(tr("setup_back"), self)
        self.next_button = QPushButton(tr("setup_next"), self)
        self.next_button.setDefault(True)
        self.cancel_button = QPushButton(tr("btn_cancel"), self)
        self.back_button.clicked.connect(self._back)
        self.next_button.clicked.connect(self._next)
        self.cancel_button.clicked.connect(self.reject)
        nav = QHBoxLayout()
        nav.addWidget(self.back_button)
        nav.addStretch(1)
        nav.addWidget(self.cancel_button)
        nav.addWidget(self.next_button)
        layout = QVBoxLayout(self)
        # Only the Language menu is offered while a new survey is being set up.
        self.menu_bar = QMenuBar(self)
        self.menu_lang = self.menu_bar.addMenu(tr("menu_language"))
        for code in SUPPORTED_LANGUAGES:
            action = self.menu_lang.addAction(f"{LANGUAGE_NAMES[code]} ({code.upper()})")
            action.triggered.connect(lambda _checked=False, c=code: TranslationManager.get_instance().set_language(c))
        layout.setMenuBar(self.menu_bar)
        layout.addWidget(self.step_label)
        layout.addWidget(self.pages, 1)
        layout.addLayout(nav)
        self._load_defaults()
        self._update_navigation()
        for field in (self.name, self.author):
            field.textChanged.connect(self._invalidate_import_preview)
        for field in (self.length, self.width, self.margin, self.spacing_x, self.spacing_y):
            field.valueChanged.connect(self._invalidate_import_preview)
        for field in (self.cols, self.rows):
            field.valueChanged.connect(self._invalidate_import_preview)
        self.traversal.currentIndexChanged.connect(self._invalidate_import_preview)
        self.grid_mode.currentIndexChanged.connect(self._on_grid_mode_changed)
        TranslationManager.get_instance().language_changed.connect(self.retranslate_ui)

    def retranslate_ui(self, *_args) -> None:
        """Re-apply every text in the active language (the window stays open while switching)."""
        self.setWindowTitle(tr("setup_title"))
        self.menu_lang.setTitle(tr("menu_language"))
        self.page_titles = [tr("setup_step_room"), tr("setup_step_points"), tr("setup_step_readings")]
        self.author.setPlaceholderText(tr("setup_optional"))
        for form, rows in (
            (self.room_form, ((self.name, "setup_name"), (self.author, "setup_surveyor"),
                              (self.length, "setup_length"), (self.width, "setup_width"))),
            (self.points_form, ((self.grid_mode, "setup_points_by"), (self.cols, "setup_cols"),
                                (self.rows, "setup_rows"), (self.spacing_x, "setup_spacing_x"),
                                (self.spacing_y, "setup_spacing_y"), (self.margin, "setup_margin"),
                                (self.traversal, "setup_walking_order"))),
        ):
            for field, key in rows:
                label = form.labelForField(field)
                if label is not None:
                    label.setText(tr(key))
        for combo, keys in (
            (self.grid_mode, {"count": "setup_mode_count", "spacing": "setup_mode_spacing"}),
            (self.traversal, {"serpentine": "setup_traversal_serpentine", "left_to_right": "setup_traversal_rows"}),
            (self.reading_method, {"manual": "setup_method_manual", "csv": "setup_method_csv"}),
        ):
            for index in range(combo.count()):
                combo.setItemText(index, tr(keys[combo.itemData(index)]))
        self.points_hint.setText(tr("setup_points_hint"))
        self.readings_intro.setText(tr("setup_readings_intro"))
        self.import_button.setText(tr("setup_choose_csv"))
        key, values = self._import_status
        self.import_status.setText(tr(key, **values))
        self.back_button.setText(tr("setup_back"))
        self.cancel_button.setText(tr("btn_cancel"))
        self._update_navigation()
        self._update_setup_summary()

    def _load_defaults(self) -> None:
        """Start from the choices made the last time a survey was created (all but the name)."""
        store = self._settings
        store.beginGroup(self.DEFAULTS_GROUP)
        try:
            def number(key, widget, cast=float):
                value = store.value(key)
                if value is None:
                    return
                try:
                    widget.setValue(cast(value))
                except (TypeError, ValueError):
                    pass

            def choice(key, combo):
                index = combo.findData(store.value(key))
                if index >= 0:
                    combo.setCurrentIndex(index)

            author = store.value("author")
            if isinstance(author, str):
                self.author.setText(author)
            number("length", self.length)
            number("width", self.width)
            number("margin", self.margin)
            number("cols", self.cols, int)
            number("rows", self.rows, int)
            number("spacing_x", self.spacing_x)
            number("spacing_y", self.spacing_y)
            choice("grid_mode", self.grid_mode)
            choice("traversal", self.traversal)
        finally:
            store.endGroup()
        self._on_grid_mode_changed(self.grid_mode.currentIndex())

    def save_defaults(self) -> None:
        """Remember this window's choices (except the survey name) for the next new survey."""
        store = self._settings
        store.beginGroup(self.DEFAULTS_GROUP)
        try:
            store.setValue("author", self.author.text().strip())
            store.setValue("length", self.length.value())
            store.setValue("width", self.width.value())
            store.setValue("margin", self.margin.value())
            store.setValue("cols", self.cols.value())
            store.setValue("rows", self.rows.value())
            store.setValue("spacing_x", self.spacing_x.value())
            store.setValue("spacing_y", self.spacing_y.value())
            store.setValue("grid_mode", self.grid_mode.currentData())
            store.setValue("traversal", self.traversal.currentData())
        finally:
            store.endGroup()
        store.sync()

    def _set_import_status(self, key: str, **values) -> None:
        self._import_status = (key, values)
        self.import_status.setText(tr(key, **values))

    def _on_grid_mode_changed(self, _index: int) -> None:
        count = self.grid_mode.currentData() == "count"
        for field, active in ((self.cols, count), (self.rows, count),
                              (self.spacing_x, not count), (self.spacing_y, not count)):
            field.setEnabled(active)
            label = self.points_form.labelForField(field)
            if label is not None:
                label.setEnabled(active)
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
        if self.pages.currentIndex() == 1 and 2 * self.margin.value() >= min(self.length.value(), self.width.value()):
            QMessageBox.information(self, tr("setup_check_walls_title"), tr("setup_check_walls_text"))
            return
        if self.pages.currentIndex() < 2:
            self.pages.setCurrentIndex(self.pages.currentIndex() + 1)
            self._update_navigation()
        else:
            if self.reading_method.currentData() == "csv" and self._imported_project is None:
                QMessageBox.information(
                    self,
                    tr("setup_preview_first_title"),
                    tr("setup_preview_first_text"),
                )
                return
            self.save_defaults()
            self.accept()

    def _update_navigation(self) -> None:
        index = self.pages.currentIndex()
        self.step_label.setText(self.page_titles[index])
        self.back_button.setEnabled(index > 0)
        self.next_button.setText(tr("setup_create") if index == 2 else tr("setup_next"))
        if index == 2:
            self._update_setup_summary()

    def _update_setup_summary(self) -> None:
        if self._imported_project is not None:
            source = tr("setup_source_previewed")
        elif self.reading_method.currentData() == "csv":
            source = tr("setup_source_not_previewed")
        else:
            source = tr("setup_source_manual")
        grid = (
            tr("setup_grid_count", cols=self.cols.value(), rows=self.rows.value())
            if self.grid_mode.currentData() == "count"
            else tr("setup_grid_spacing", sx=f"{self.spacing_x.value():g}", sy=f"{self.spacing_y.value():g}")
        )
        self.setup_summary.setText(tr(
            "setup_summary",
            length=f"{self.length.value():g}",
            width=f"{self.width.value():g}",
            grid=grid,
            margin=f"{self.margin.value():g}",
            source=source,
        ))

    def _on_reading_method_changed(self, _index: int) -> None:
        is_csv = self.reading_method.currentData() == "csv"
        self.import_button.setVisible(is_csv)
        if not is_csv and self._imported_project is not None:
            self._imported_project = None
            self._import_counts = (0, 0)
            self._set_import_status("setup_manual_removed")
        self._update_setup_summary()

    def _build_project(self) -> LuminationProject:
        name = self.name.text().strip() or tr("room_default_name")
        room = Room(
            name=name,
            length=self.length.value(),
            width=self.width.value(),
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
            centered_in_cells=False,
            traversal_order=str(self.traversal.currentData()),
        )
        return project

    def _choose_csv(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self, tr("setup_import_title"), "", ";;".join((tr("filter_tables"), tr("filter_excel"), tr("filter_csv")))
        )
        if not file_path:
            return
        try:
            candidate = self._build_project()
            updated = apply_table_to_project(candidate, read_table(file_path))
            created = 0
            if not updated:
                QMessageBox.information(self, tr("setup_no_readings_title"), tr("setup_no_readings_text"))
                return
            preview = ImportPreviewDialog(candidate, updated, created, self)
            accepted = preview.exec() == QDialog.DialogCode.Accepted
            preview.deleteLater()
            if accepted:
                self._imported_project = candidate
                self._import_counts = (updated, created)
                self.reading_method.setCurrentIndex(1)
                self._set_import_status("setup_preview_accepted", updated=updated, created=created)
                self._update_setup_summary()
        except TableError as exc:
            QMessageBox.warning(self, tr("table_err_title"), str(exc))
        except Exception as exc:
            QMessageBox.critical(self, tr("setup_import_failed_title"), tr("setup_import_failed_text", error=exc))

    def _invalidate_import_preview(self, *_args) -> None:
        if self._imported_project is not None:
            self._imported_project = None
            self._import_counts = (0, 0)
            self._set_import_status("setup_changed")

    def get_created_project(self) -> LuminationProject:
        project = copy.deepcopy(self._imported_project) if self._imported_project is not None else self._build_project()
        project.is_dirty = True
        return project

    @property
    def import_counts(self) -> tuple[int, int]:
        return self._import_counts
