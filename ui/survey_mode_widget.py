"""Survey / Measurement Mode Fast Entry Widget.

Optimized for real-world room walking workflow:
- Current point target tracking with coordinates
- High-efficiency Enter-to-advance entry (sequential walking traversal)
- Previous / Next navigation controls
- Survey progress indicator (e.g. 18 / 30 points completed)
- Non-destructive outlier warning alerts
- No emojis, clean readable typography
- Full i18n support (English, Romanian, German)
"""

from __future__ import annotations
import math
from typing import Optional, List
from PySide6.QtCore import Qt, Signal, QLocale
from PySide6.QtGui import QDoubleValidator
from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QLineEdit,
    QComboBox,
    QPushButton,
    QProgressBar,
    QFrame,
)

from models.project import LuminationProject
from models.measurement import MeasurementPoint
from analysis.outliers import evaluate_spatial_outliers
from i18n.translations import tr, TranslationManager


class SurveyModeWidget(QFrame):
    """Interactive top/bottom survey bar for physical walkthrough data entry.

    Signals:
        measurement_saved (str, float): Emitted when lux value is saved for a point (point_id, lux).
        point_navigated (str): Emitted when active point selection moves (point_id).
    """
    measurement_saved = Signal(str, float)
    point_navigated = Signal(str)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        self.project: Optional[LuminationProject] = None
        self.active_point_id: Optional[str] = None
        self.recording_allowed = True
        self.correction_allowed = False

        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet("""
            SurveyModeWidget {
                background-color: #ffffff;
                border: 1px solid #cbd5e1;
                border-radius: 6px;
                padding: 4px 10px;
            }
        """)

        # 1. Point Info & Target Indicator
        self.lbl_point_id = QLabel(f"{tr('survey_point')} --", self)
        self.lbl_point_id.setStyleSheet("font-size: 13px; font-weight: bold; color: #1e3a8a;")

        self.lbl_coords = QLabel("(X: -- m, Y: -- m)", self)
        self.lbl_coords.setStyleSheet("font-size: 11px; color: #64748b;")

        # 2. Lux Entry SpinBox
        self.edit_lux = QLineEdit(self)
        self.edit_lux.setObjectName("manualLuxEntry")
        self.edit_lux.setPlaceholderText("Enter lux")
        self.edit_lux.setAccessibleName("Manual illuminance reading in lux")
        self.edit_lux.setValidator(QDoubleValidator(0.0, 150000.0, -1, self))
        self._set_input_locale()
        self.edit_lux.setMinimumSize(112, 48)
        self.edit_lux.setStyleSheet("font-size: 13px; font-weight: bold; padding: 3px 6px;")
        self.lbl_lux_unit = QLabel("lx", self)

        # 3. Action Buttons (No emojis, crisp readable text)
        self.btn_save_next = QPushButton(f"{tr('survey_record_next')} (Enter)", self)
        self.btn_save_next.setMinimumHeight(48)
        self.btn_save_next.setStyleSheet("""
            QPushButton {
                background-color: #2563eb;
                color: #ffffff;
                font-weight: bold;
                padding: 5px 12px;
                border-radius: 4px;
                border: 1px solid #1d4ed8;
            }
            QPushButton:hover { background-color: #1d4ed8; }
            QPushButton:disabled {
                background-color: #e2e8f0;
                color: #52606d;
                border-color: #cbd5e1;
            }
        """)
        self.btn_prev = QPushButton(tr("survey_prev"), self)
        self.btn_next = QPushButton(tr("survey_next"), self)
        self.btn_next_unmeasured = QPushButton(tr("survey_next_unmeasured"), self)
        self.btn_prev.setMinimumHeight(44)
        self.btn_next.setText(tr("survey_skip_point"))
        self.btn_next.setMinimumHeight(44)
        self.btn_next_unmeasured.setMinimumHeight(44)
        self.combo_points = QComboBox(self)
        self.combo_points.setAccessibleName(tr("survey_select_point"))
        self.combo_points.setMinimumHeight(44)

        self.btn_save_next.clicked.connect(self._save_and_advance)
        self.btn_prev.clicked.connect(self._go_previous)
        self.btn_next.clicked.connect(self._go_next)
        self.btn_next_unmeasured.clicked.connect(self._go_next_unmeasured)
        self.combo_points.currentIndexChanged.connect(self._on_point_combo_changed)

        # Connect Enter key inside spinbox
        self.edit_lux.returnPressed.connect(self._save_and_advance)

        # 4. Progress bar & completion counter
        self.lbl_progress = QLabel(f"{tr('survey_progress')} 0 / 0 (0%)", self)
        self.lbl_progress.setStyleSheet("font-size: 11px; font-weight: 600; color: #334155;")

        self.progress_bar = QProgressBar(self)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setMaximumWidth(130)
        self.progress_bar.setMaximumHeight(14)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #cbd5e1;
                border-radius: 3px;
                background-color: #f1f5f9;
            }
            QProgressBar::chunk {
                background-color: #16a34a;
                border-radius: 2px;
            }
        """)

        # 5. Outlier Alert Banner (hidden by default)
        self.lbl_outlier_warning = QLabel("", self)
        self.lbl_outlier_warning.setStyleSheet("""
            color: #b45309;
            background-color: #fef3c7;
            border: 1px solid #fde68a;
            border-radius: 4px;
            padding: 3px 8px;
            font-size: 11px;
            font-weight: 600;
        """)
        self.lbl_outlier_warning.setVisible(False)

        # Layout Assembly
        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(6)

        top_row.addWidget(self.lbl_point_id)
        top_row.addWidget(self.lbl_coords)
        top_row.addWidget(self.combo_points)
        top_row.addStretch()
        top_row.addWidget(self.lbl_progress)
        top_row.addWidget(self.progress_bar)

        control_row = QHBoxLayout()
        control_row.setContentsMargins(0, 0, 0, 0)
        control_row.setSpacing(8)
        self.lbl_reading_tag = QLabel(tr("survey_reading"), self)
        self.lbl_source_mode = QLabel("Manual entry", self)
        self.lbl_source_mode.setObjectName("manualSourceLabel")
        self.lbl_source_mode.setAccessibleName("Selected reading source: manual entry")
        self.lbl_source_mode.setToolTip("Enter a lux value from the instrument display. No connection is required.")
        control_row.addWidget(self.lbl_reading_tag)
        control_row.addWidget(self.lbl_source_mode)
        control_row.addWidget(self.edit_lux)
        control_row.addWidget(self.lbl_lux_unit)
        control_row.addWidget(self.btn_save_next)
        control_row.addStretch()

        navigation_row = QHBoxLayout()
        navigation_row.setContentsMargins(0, 0, 0, 0)
        navigation_row.setSpacing(8)
        navigation_row.addWidget(self.btn_prev)
        navigation_row.addWidget(self.btn_next)
        navigation_row.addWidget(self.btn_next_unmeasured)
        navigation_row.addStretch()

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(2, 2, 2, 2)
        main_layout.setSpacing(3)
        main_layout.addLayout(top_row)
        main_layout.addLayout(control_row)
        main_layout.addLayout(navigation_row)
        main_layout.addWidget(self.lbl_outlier_warning)

        TranslationManager.get_instance().language_changed.connect(self.retranslate_ui)

    def retranslate_ui(self) -> None:
        """Update strings on language change."""
        self.lbl_reading_tag.setText(tr("survey_reading"))
        self.btn_save_next.setText(f"{tr('survey_record_next')} (Enter)")
        self.btn_prev.setText(tr("survey_prev"))
        self.btn_next.setText(tr("survey_skip_point"))
        self.btn_next_unmeasured.setText(tr("survey_next_unmeasured"))
        self.btn_save_next.setText(f"{tr('survey_record_next')} (Enter)")
        self.combo_points.setAccessibleName(tr("survey_select_point"))
        draft, valid_draft = self.edit_lux.locale().toDouble(self.edit_lux.text())
        point = self.project.find_point_by_id(self.active_point_id) if self.project and self.active_point_id else None
        self._set_input_locale()
        if self.project:
            self.set_project(self.project, self.active_point_id)
        if valid_draft and point and not point.is_measured:
            self.edit_lux.setText(self.edit_lux.locale().toString(draft, 'g', 17))

    def _set_input_locale(self) -> None:
        language = TranslationManager.get_instance().current_language
        locale = QLocale({"en": "en_US", "ro": "ro_RO", "de": "de_DE"}[language])
        locale.setNumberOptions(QLocale.NumberOption.OmitGroupSeparator | QLocale.NumberOption.RejectGroupSeparator)
        self.edit_lux.setLocale(locale)
        self.edit_lux.validator().setLocale(locale)

    def set_project(self, project: LuminationProject, active_point_id: Optional[str] = None) -> None:
        """Bind project reference and activate point."""
        self.project = project
        self.combo_points.blockSignals(True)
        self.combo_points.clear()
        for point in project.points:
            state = tr("survey_recorded") if point.is_measured else tr("survey_pending")
            self.combo_points.addItem(f"{point.id} · {state}", point.id)
        self.combo_points.blockSignals(False)
        if active_point_id:
            self.set_active_point(active_point_id)
        elif project and project.points:
            self.set_active_point(project.points[0].id)
        else:
            self.set_active_point(None)
        self.update_progress()

    def set_active_point(self, point_id: Optional[str]) -> None:
        """Highlight and load the given measurement point into the fast entry bar."""
        self.active_point_id = point_id
        if not self.project or not point_id:
            self.lbl_point_id.setText(f"{tr('survey_point')} --")
            self.lbl_coords.setText("(X: -- m, Y: -- m)")
            self.lbl_outlier_warning.setVisible(False)
            self.edit_lux.clear()
            self.btn_save_next.setEnabled(False)
            self._update_navigation_controls()
            return

        pt = self.project.find_point_by_id(point_id)
        if pt:
            status_str = f"[{tr('survey_recorded')}]" if pt.is_measured else f"[{tr('survey_pending')}]"
            self.lbl_point_id.setText(f"{tr('survey_point')} {pt.id} {status_str}")
            self.lbl_coords.setText(f"(X: {pt.x:.2f} m, Y: {pt.y:.2f} m)")

            self.edit_lux.blockSignals(True)
            if pt.is_measured and pt.lux is not None:
                self.edit_lux.setText(self.edit_lux.locale().toString(pt.lux, 'g', 17))
            else:
                self.edit_lux.clear()
            self.edit_lux.blockSignals(False)
            combo_index = self.combo_points.findData(point_id)
            if combo_index >= 0:
                self.combo_points.blockSignals(True)
                self.combo_points.setCurrentIndex(combo_index)
                self.combo_points.blockSignals(False)
            self.btn_save_next.setEnabled(
                self.recording_allowed and (not pt.is_measured or self.correction_allowed)
            )
            self.btn_save_next.setToolTip("Use Edit survey to correct a recorded reading." if pt.is_measured else "Record this value for the selected point.")

            # Show outlier badge if flagged
            if pt.is_possible_outlier and pt.outlier_reason:
                self.lbl_outlier_warning.setText(f"{tr('survey_possible_outlier')} {pt.outlier_reason}")
                self.lbl_outlier_warning.setVisible(True)
            else:
                self.lbl_outlier_warning.setVisible(False)

        self.update_progress()
        self._update_navigation_controls()

    def update_progress(self) -> None:
        """Update progress bar and completion count."""
        if not self.project or not self.project.points:
            self.lbl_progress.setText(f"{tr('survey_progress')} 0 / 0 (0%)")
            self.progress_bar.setValue(0)
            return

        total = len(self.project.points)
        measured = len(self.project.get_measured_points())
        pct = int(round((measured / total) * 100)) if total > 0 else 0

        self.lbl_progress.setText(f"{tr('survey_progress')} {measured} / {total} ({pct}%)")
        self.progress_bar.setValue(pct)

    def _save_and_advance(self) -> None:
        """Save current lux reading, check outliers, and advance to next consecutive point."""
        if not self.project or not self.active_point_id:
            return

        pt = self.project.find_point_by_id(self.active_point_id)
        if not pt or not self.recording_allowed or (pt.is_measured and not self.correction_allowed):
            return

        raw_value = self.edit_lux.text().strip()
        if not raw_value:
            self.lbl_outlier_warning.setText("Enter a reading first. A blank field remains pending.")
            self.lbl_outlier_warning.setVisible(True)
            return
        lux_val, ok = self.edit_lux.locale().toDouble(raw_value)
        if not ok or not math.isfinite(lux_val) or lux_val < 0 or lux_val > 150000:
            self.lbl_outlier_warning.setText("Enter a valid lux value from 0 to 150000.")
            self.lbl_outlier_warning.setVisible(True)
            return
        self.measurement_saved.emit(pt.id, lux_val)
        self.update_progress()

    def _go_previous(self) -> None:
        """Navigate to previous point in project point sequence."""
        if not self.project or not self.project.points:
            return
        cur_idx = self._get_current_index()
        if cur_idx <= 0:
            return
        prev_idx = cur_idx - 1
        target_id = self.project.points[prev_idx].id
        self.set_active_point(target_id)
        self.point_navigated.emit(target_id)

    def _go_next(self) -> None:
        """Leave this point pending and navigate to the next pending point."""
        self._go_next_unmeasured()

    def _go_next_unmeasured(self) -> None:
        """Find and navigate to the next unmeasured point following current sequence."""
        if not self.project or not self.project.points:
            return

        cur_idx = self._get_current_index()
        pts = self.project.points
        n = len(pts)

        for step in range(1, n + 1):
            idx = (cur_idx + step) % n
            if not pts[idx].is_measured:
                target_id = pts[idx].id
                self.set_active_point(target_id)
                self.point_navigated.emit(target_id)
                return

        self.lbl_point_id.setText(tr("survey_complete"))

    def _get_current_index(self) -> int:
        if not self.project or not self.active_point_id:
            return 0
        for i, p in enumerate(self.project.points):
            if p.id == self.active_point_id:
                return i
        return 0

    def _on_point_combo_changed(self, index: int) -> None:
        point_id = self.combo_points.itemData(index)
        if point_id:
            self.set_active_point(str(point_id))
            self.point_navigated.emit(str(point_id))

    def set_workflow_permissions(self, recording: bool, correction: bool) -> None:
        self.recording_allowed = recording
        self.correction_allowed = correction
        point = self.project.find_point_by_id(self.active_point_id) if self.project and self.active_point_id else None
        self.btn_save_next.setEnabled(
            bool(recording and point and (not point.is_measured or correction))
        )
        self.edit_lux.setEnabled(self.btn_save_next.isEnabled())

    def _update_navigation_controls(self) -> None:
        points = self.project.points if self.project else []
        has_other_pending = any(not p.is_measured and p.id != self.active_point_id for p in points)
        self.btn_prev.setEnabled(bool(points) and self._get_current_index() > 0)
        self.btn_next.setEnabled(has_other_pending)
        self.btn_next_unmeasured.setEnabled(has_other_pending)
        self.combo_points.setEnabled(bool(points))
        self.set_workflow_permissions(self.recording_allowed, self.correction_allowed)
