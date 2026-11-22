"""Comparison with Selected Target Illuminance Panel.

Allows the user to specify a reference target illuminance (e.g., 500 lx)
and calculates comprehensive deviation metrics without legal compliance claims.
"""

from __future__ import annotations
from typing import Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QDoubleSpinBox,
    QPushButton,
    QGroupBox,
    QProgressBar,
    QFrame,
)

from models.project import LuminationProject
from analysis.comparison import TargetComparisonResult, compare_with_target
from i18n.translations import tr, TranslationManager


class TargetPanel(QWidget):
    """Panel for comparing physical measurements against a user-specified target illuminance.

    Signals:
        target_changed (float): Emitted when user sets/modifies the target illuminance.
    """
    target_changed = Signal(float)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        self.project: Optional[LuminationProject] = None

        # UI Elements
        group = QGroupBox(tr("target_group"), self)
        self.group = group
        g_layout = QVBoxLayout(group)
        g_layout.setSpacing(8)

        # Target input row
        input_row = QHBoxLayout()
        lbl_target = QLabel(tr("target_label"), self)
        self.lbl_target = lbl_target
        lbl_target.setStyleSheet("font-weight: 600;")
        self.spin_target = QDoubleSpinBox(self)
        self.spin_target.setRange(0, 50000)
        self.spin_target.setValue(500.0)
        self.spin_target.setSingleStep(50.0)
        self.spin_target.setSuffix(" lx")
        self.spin_target.valueChanged.connect(self._on_target_changed)

        input_row.addWidget(lbl_target)
        input_row.addWidget(self.spin_target)
        input_row.addStretch()

        # Preset buttons for convenience
        preset_row = QHBoxLayout()
        for val in [100, 200, 300, 500, 750, 1000]:
            btn = QPushButton(f"{val}", self)
            btn.setMaximumWidth(45)
            btn.setMinimumWidth(30)
            btn.setStyleSheet("padding: 2px 4px; font-size: 11px;")
            btn.clicked.connect(lambda checked=False, v=val: self.spin_target.setValue(v))
            preset_row.addWidget(btn)

        # Compliance Progress Bar
        self.lbl_progress = QLabel(tr("target_progress_none"), self)
        self.lbl_progress.setWordWrap(True)
        self.lbl_progress.setStyleSheet("font-size: 11px; font-weight: 600; color: #1e3a8a;")

        self.progress_bar = QProgressBar(self)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #cbd5e1;
                border-radius: 4px;
                text-align: center;
                height: 16px;
                background-color: #fee2e2;
                color: #0f172a;
                font-size: 10px;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background-color: #22c55e;
                border-radius: 3px;
            }
        """)

        # Metric Details Card Grid
        self.metrics_frame = QFrame(self)
        self.metrics_frame.setStyleSheet("""
            QFrame {
                background-color: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 6px;
                padding: 6px;
            }
        """)
        m_grid = QGridLayout(self.metrics_frame)
        m_grid.setSpacing(4)

        self.lbl_m_target = QLabel(tr("target_m_target", value="- lx"), self)
        self.lbl_m_avg = QLabel(tr("target_m_avg", value="- lx"), self)
        self.lbl_m_below = QLabel(tr("target_m_below", value="-"), self)
        self.lbl_m_above = QLabel(tr("target_m_above", value="-"), self)
        self.lbl_m_max_deficit = QLabel(tr("target_m_deficit", value="-"), self)
        self.lbl_m_max_surplus = QLabel(tr("target_m_surplus", value="-"), self)
        self.lbl_m_mae = QLabel(tr("target_m_mae", value="-"), self)
        self.lbl_m_avg_dev = QLabel(tr("target_m_dev", value="-"), self)

        # Wrap long values (German, Romanian) instead of cutting them off at the panel edge.
        for label in (self.lbl_m_target, self.lbl_m_avg, self.lbl_m_below, self.lbl_m_above,
                      self.lbl_m_max_deficit, self.lbl_m_max_surplus, self.lbl_m_mae, self.lbl_m_avg_dev):
            label.setWordWrap(True)
            label.setMinimumWidth(0)
        m_grid.setColumnStretch(0, 1)
        m_grid.setColumnStretch(1, 1)
        m_grid.addWidget(self.lbl_m_target, 0, 0)
        m_grid.addWidget(self.lbl_m_avg, 0, 1)
        m_grid.addWidget(self.lbl_m_below, 1, 0)
        m_grid.addWidget(self.lbl_m_above, 1, 1)
        m_grid.addWidget(self.lbl_m_max_deficit, 2, 0)
        m_grid.addWidget(self.lbl_m_max_surplus, 2, 1)
        m_grid.addWidget(self.lbl_m_mae, 3, 0)
        m_grid.addWidget(self.lbl_m_avg_dev, 3, 1)

        # Summary Note
        self.lbl_summary = QLabel(tr("target_summary_empty"), self)
        self.lbl_summary.setWordWrap(True)
        self.lbl_summary.setStyleSheet("background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 4px; padding: 6px; font-size: 11px; color: #334155;")

        g_layout.addLayout(input_row)
        g_layout.addLayout(preset_row)
        g_layout.addSpacing(4)
        g_layout.addWidget(self.lbl_progress)
        g_layout.addWidget(self.progress_bar)
        g_layout.addWidget(self.metrics_frame)
        g_layout.addWidget(self.lbl_summary)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.addWidget(group)
        main_layout.addStretch()
        TranslationManager.get_instance().language_changed.connect(self.retranslate_ui)

    def retranslate_ui(self, *_args) -> None:
        self.group.setTitle(tr("target_group"))
        self.lbl_target.setText(tr("target_label"))
        if self.project:
            self.update_analysis()

    def set_project(self, project: LuminationProject) -> None:
        """Set project reference and update target input."""
        self.project = project
        if project.target_lux and project.target_lux > 0:
            self.spin_target.blockSignals(True)
            self.spin_target.setValue(project.target_lux)
            self.spin_target.blockSignals(False)
        self.update_analysis()

    def update_analysis(self) -> None:
        """Recalculate target comparison and refresh widgets."""
        if not self.project:
            return

        target_val = self.spin_target.value()
        comp = compare_with_target(self.project.points, target_val)

        if comp is None:
            self.progress_bar.setValue(0)
            self.lbl_progress.setText(tr("target_progress_none"))
            self.lbl_m_target.setText(tr("target_m_target", value=f"{target_val:.0f} lx"))
            self.lbl_m_avg.setText(tr("target_m_avg", value="-"))
            self.lbl_m_below.setText(tr("target_m_below", value="-"))
            self.lbl_m_above.setText(tr("target_m_above", value="-"))
            self.lbl_m_max_deficit.setText(tr("target_m_deficit", value="-"))
            self.lbl_m_max_surplus.setText(tr("target_m_surplus", value="-"))
            self.lbl_m_mae.setText(tr("target_m_mae", value="-"))
            self.lbl_m_avg_dev.setText(tr("target_m_dev", value="-"))
            self.lbl_summary.setText(tr("target_summary_no_points", target=f"{target_val:.0f}"))
            return

        pct_above = int(round(comp.percentage_above_or_equal))
        self.progress_bar.setValue(pct_above)
        self.lbl_progress.setText(tr(
            "target_progress",
            above=comp.points_above_or_equal_target,
            total=comp.points_evaluated,
            pct=f"{comp.percentage_above_or_equal:.1f}",
        ))

        self.lbl_m_target.setText(tr("target_m_target", value=f"{comp.target_lux:.0f} lx"))
        self.lbl_m_avg.setText(tr("target_m_avg", value=f"{comp.e_avg:.1f} lx"))
        self.lbl_m_below.setText(tr("target_m_below", value=comp.points_below_target) + f" ({comp.percentage_below_target:.1f}%)")
        self.lbl_m_above.setText(tr("target_m_above", value=comp.points_above_or_equal_target) + f" ({comp.percentage_above_or_equal:.1f}%)")

        deficit_sub = tr("target_at_point", point=comp.max_deficit_point_id) if comp.max_deficit_point_id else ""
        self.lbl_m_max_deficit.setText(tr("target_m_deficit", value=f"-{comp.max_negative_deficit:.1f} lx") + deficit_sub)
        self.lbl_m_max_surplus.setText(tr("target_m_surplus", value=f"+{comp.max_positive_deviation:.1f} lx"))
        self.lbl_m_mae.setText(tr("target_m_mae", value=f"{comp.avg_absolute_deviation:.1f} lx"))
        self.lbl_m_avg_dev.setText(tr("target_m_dev", value=f"{comp.avg_deviation:+.1f} lx"))

        self.lbl_summary.setText(comp.summary_text)

    def _on_target_changed(self, val: float) -> None:
        if self.project:
            self.project.target_lux = val if val > 0 else None
            self.project.mark_modified()
        self.update_analysis()
        self.target_changed.emit(val)
