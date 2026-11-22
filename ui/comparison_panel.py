"""Comparison panel: compare the survey with another Luxious project, Excel or CSV grid.

The compared file can be an earlier survey of the same room or a similar room.
Points are matched by grid position; the panel shows averages, the difference
and the depreciation of the light, and controls which map is shown.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QGroupBox,
    QLabel,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

from analysis.comparison import compare_with_file
from i18n.translations import TranslationManager, tr
from models.project import LuminationProject


class ComparisonPanel(QWidget):
    """Load a file to compare with, show the results and choose the map view.

    Signals:
        display_mode_changed (str): "measured", "expected" (compared file) or "difference".
        compare_requested (): the user wants to pick a file to compare with.
    """

    display_mode_changed = Signal(str)
    compare_requested = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.project: Optional[LuminationProject] = None

        self.file_group = QGroupBox(self)
        file_layout = QVBoxLayout(self.file_group)
        self.btn_compare = QPushButton(self)
        self.btn_compare.setMinimumHeight(40)
        self.btn_compare.clicked.connect(self.compare_requested.emit)
        self.lbl_file = QLabel(self)
        self.lbl_file.setWordWrap(True)
        file_layout.addWidget(self.btn_compare)
        file_layout.addWidget(self.lbl_file)

        self.mode_group = QGroupBox(self)
        mode_layout = QVBoxLayout(self.mode_group)
        self.btn_group = QButtonGroup(self)
        self.rb_measured = QRadioButton(self)
        self.rb_expected = QRadioButton(self)
        self.rb_difference = QRadioButton(self)
        self.rb_measured.setChecked(True)
        for index, button in enumerate((self.rb_measured, self.rb_expected, self.rb_difference)):
            self.btn_group.addButton(button, index)
            mode_layout.addWidget(button)
        self.btn_group.idClicked.connect(self._on_mode_radio_clicked)

        self.results_group = QGroupBox(self)
        results_layout = QVBoxLayout(self.results_group)
        self.lbl_points = QLabel(self)
        self.lbl_compared_avg = QLabel(self)
        self.lbl_current_avg = QLabel(self)
        self.lbl_difference = QLabel(self)
        self.lbl_depreciation = QLabel(self)
        self.lbl_depreciation.setWordWrap(True)
        for label in (self.lbl_points, self.lbl_compared_avg, self.lbl_current_avg,
                      self.lbl_difference, self.lbl_depreciation):
            results_layout.addWidget(label)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.addWidget(self.file_group)
        main_layout.addWidget(self.mode_group)
        main_layout.addWidget(self.results_group)
        main_layout.addStretch()

        self.retranslate_ui()
        TranslationManager.get_instance().language_changed.connect(self.retranslate_ui)

    def retranslate_ui(self, *_args) -> None:
        self.file_group.setTitle(tr("cmp_file_group"))
        self.btn_compare.setText(tr("cmp_btn_compare"))
        self.mode_group.setTitle(tr("cmp_mode_group"))
        self.rb_measured.setText(tr("cmp_rb_measured"))
        self.rb_expected.setText(tr("cmp_rb_expected"))
        self.rb_difference.setText(tr("cmp_rb_difference"))
        self.results_group.setTitle(tr("cmp_results_group"))
        self.update_analysis()

    def set_project(self, project: LuminationProject) -> None:
        self.project = project
        mode = project.visualization_settings.display_mode
        self.btn_group.blockSignals(True)
        {"expected": self.rb_expected, "difference": self.rb_difference}.get(mode, self.rb_measured).setChecked(True)
        self.btn_group.blockSignals(False)
        self.update_analysis()

    def set_display_mode(self, mode: str) -> None:
        if mode not in ("expected", "difference"):
            mode = "measured"
        {"expected": self.rb_expected, "difference": self.rb_difference}.get(mode, self.rb_measured).setChecked(True)
        if self.project:
            self.project.visualization_settings.display_mode = mode
            self.project.mark_modified()
        self.display_mode_changed.emit(mode)

    def update_analysis(self) -> None:
        name = self.project.comparison_file if self.project else None
        has_values = bool(self.project and any(p.expected_lux is not None for p in self.project.points))
        if name:
            self.lbl_file.setText(tr("cmp_file_name", name=name))
        elif has_values:
            self.lbl_file.setText(tr("cmp_file_unnamed"))
        else:
            self.lbl_file.setText(tr("cmp_no_file"))
        for button in (self.rb_expected, self.rb_difference):
            button.setEnabled(has_values)
        if not has_values and self.project and self.project.visualization_settings.display_mode != "measured":
            self.project.visualization_settings.display_mode = "measured"
            self.btn_group.blockSignals(True)
            self.rb_measured.setChecked(True)
            self.btn_group.blockSignals(False)

        result = compare_with_file(self.project.points) if self.project else None
        if result is None:
            self.lbl_points.setText(tr("cmp_points", value="-"))
            self.lbl_compared_avg.setText(tr("cmp_compared_avg", value="-"))
            self.lbl_current_avg.setText(tr("cmp_current_avg", value="-"))
            self.lbl_difference.setText(tr("cmp_difference", value="-"))
            self.lbl_depreciation.setText(tr("cmp_depreciation", value="-"))
            return
        self.lbl_points.setText(tr("cmp_points", value=result.points_compared))
        self.lbl_compared_avg.setText(tr("cmp_compared_avg", value=f"{result.compared_avg:.1f} lx"))
        self.lbl_current_avg.setText(tr("cmp_current_avg", value=f"{result.current_avg:.1f} lx"))
        self.lbl_difference.setText(tr(
            "cmp_difference",
            value=f"{result.difference_lux:+.1f} lx ({result.difference_pct:+.1f}%)",
        ))
        if result.has_depreciation:
            self.lbl_depreciation.setText(tr("cmp_depreciation", value=f"{result.depreciation_pct:.1f}%"))
        else:
            self.lbl_depreciation.setText(tr("cmp_no_depreciation", pct=f"{result.difference_pct:.1f}"))

    def _on_mode_radio_clicked(self, id_val: int) -> None:
        self.set_display_mode({1: "expected", 2: "difference"}.get(id_val, "measured"))
