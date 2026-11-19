"""Results Summary KPI Dashboard Panel.

Displays prominently:
- Average illuminance (E_avg)
- Minimum illuminance (E_min) with interactive point highlight
- Maximum illuminance (E_max) with interactive point highlight
- Uniformity U_0 = E_min / E_avg and U_1
- Standard deviation, Median, Range, Point Count
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
    QFrame,
    QPushButton,
    QGroupBox,
)

from analysis.statistics import StatisticalSummary
from i18n.translations import tr, TranslationManager


class KPICard(QFrame):
    """Clean visual card displaying a single lighting KPI metric."""

    clicked = Signal()

    def __init__(
        self,
        title: str,
        value: str = "-",
        subtitle: str = "",
        accent_color: str = "#2563eb",
        clickable: bool = False,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.clickable = clickable
        self.setFrameShape(QFrame.Shape.StyledPanel)

        if clickable:
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: #ffffff;
                border: 1px solid #e2e8f0;
                border-left: 3.5px solid {accent_color};
                border-radius: 4px;
                padding: 4px 8px;
            }}
            QFrame:hover {{
                border-color: {accent_color};
                background-color: #fafafa;
            }}
        """)

        self.lbl_title = QLabel(title.upper(), self)
        self.lbl_title.setStyleSheet("font-size: 9px; font-weight: 700; color: #64748b; letter-spacing: 0.5px;")

        self.lbl_value = QLabel(value, self)
        self.lbl_value.setStyleSheet("font-size: 16px; font-weight: 700; color: #0f172a;")

        self.lbl_sub = QLabel(subtitle, self)
        self.lbl_sub.setStyleSheet("font-size: 9px; color: #64748b;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(1)
        layout.addWidget(self.lbl_title)
        layout.addWidget(self.lbl_value)
        layout.addWidget(self.lbl_sub)

    def set_title(self, title: str) -> None:
        self.lbl_title.setText(title.upper())

    def set_content(self, value: str, subtitle: str = "") -> None:
        self.lbl_value.setText(value)
        self.lbl_sub.setText(subtitle)

    def mousePressEvent(self, event) -> None:
        if self.clickable and event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class ResultsPanel(QWidget):
    """Photometric results summary panel.

    Signals:
        highlight_point_requested (str): Emitted when user clicks Min/Max card to focus on point.
    """
    highlight_point_requested = Signal(str)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        self.stats: Optional[StatisticalSummary] = None

        # 1. Primary Metrics Grid
        self.group_primary = QGroupBox(tr("kpi_summary"), self)
        p_layout = QGridLayout(self.group_primary)
        p_layout.setSpacing(6)

        self.card_avg = KPICard("Average (Eavg)", "-", "Target: -", accent_color="#2563eb", parent=self)
        self.card_u0 = KPICard("Uniformity (U0)", "-", "Emin / Eavg", accent_color="#16a34a", parent=self)
        self.card_min = KPICard("Minimum (Emin)", "-", "Click to locate", accent_color="#0284c7", clickable=True, parent=self)
        self.card_max = KPICard("Maximum (Emax)", "-", "Click to locate", accent_color="#dc2626", clickable=True, parent=self)

        self.card_min.clicked.connect(self._on_min_card_clicked)
        self.card_max.clicked.connect(self._on_max_card_clicked)

        p_layout.addWidget(self.card_avg, 0, 0)
        p_layout.addWidget(self.card_u0, 0, 1)
        p_layout.addWidget(self.card_min, 1, 0)
        p_layout.addWidget(self.card_max, 1, 1)

        # 2. Secondary Metrics Table
        self.group_sec = QGroupBox("Extended Photometric Metrics", self)
        s_layout = QGridLayout(self.group_sec)
        s_layout.setSpacing(4)

        self.card_u1 = KPICard("Uniformity U1", "-", "Emin / Emax", accent_color="#8b5cf6", parent=self)
        self.card_std = KPICard("Std Dev (σ)", "-", "Dispersion", accent_color="#64748b", parent=self)
        self.card_med = KPICard("Median Lux", "-", "50th percentile", accent_color="#0d9488", parent=self)
        self.card_range = KPICard("Range", "-", "Emax - Emin", accent_color="#f59e0b", parent=self)

        s_layout.addWidget(self.card_u1, 0, 0)
        s_layout.addWidget(self.card_std, 0, 1)
        s_layout.addWidget(self.card_med, 1, 0)
        s_layout.addWidget(self.card_range, 1, 1)

        # 3. Status Footer
        self.lbl_points_status = QLabel("0 / 0 points measured", self)
        self.lbl_points_status.setStyleSheet("color: #475569; font-size: 10px; padding: 2px;")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(6, 6, 6, 6)
        main_layout.setSpacing(6)
        main_layout.addWidget(self.group_primary)
        main_layout.addWidget(self.group_sec)
        main_layout.addWidget(self.lbl_points_status)
        main_layout.addStretch()

        TranslationManager.get_instance().language_changed.connect(self.retranslate_ui)

    def retranslate_ui(self) -> None:
        """Update KPI headers on language switch."""
        self.group_primary.setTitle(tr("kpi_summary"))
        self.card_avg.set_title(tr("kpi_e_avg"))
        self.card_u0.set_title(tr("kpi_u0"))
        self.card_min.set_title(tr("kpi_e_min"))
        self.card_max.set_title(tr("kpi_e_max"))
        self.card_u1.set_title(tr("kpi_u1"))
        self.card_std.set_title(tr("kpi_std_dev"))
        self.card_med.set_title(tr("kpi_median"))
        self.card_range.set_title(tr("kpi_range"))
        if self.stats:
            self.update_statistics(self.stats)

    def update_statistics(self, stats: Optional[StatisticalSummary]) -> None:
        """Update KPI cards with newly computed statistical results."""
        self.stats = stats
        if stats is None or stats.count == 0:
            self.card_avg.set_content("-", "Target: -")
            self.card_u0.set_content("-", "Emin / Eavg")
            self.card_min.set_content("-", "Click to locate")
            self.card_max.set_content("-", "Click to locate")
            self.card_u1.set_content("-", "Emin / Emax")
            self.card_std.set_content("-", "Dispersion")
            self.card_med.set_content("-", "50th percentile")
            self.card_range.set_content("-", "Emax - Emin")
            self.lbl_points_status.setText("0 / 0 points measured")
            return

        self.card_avg.set_content(f"{stats.e_avg:.1f} lx", f"Count: {stats.count}")
        self.card_u0.set_content(f"{stats.uniformity_u0:.3f}", f"Emin/Eavg: {stats.e_min:.0f}/{stats.e_avg:.0f}")

        min_sub = f"at {stats.min_point_id}" if stats.min_point_id else ""
        self.card_min.set_content(f"{stats.e_min:.1f} lx", min_sub)

        max_sub = f"at {stats.max_point_id}" if stats.max_point_id else ""
        self.card_max.set_content(f"{stats.e_max:.1f} lx", max_sub)

        self.card_u1.set_content(f"{stats.uniformity_u1:.3f}", "Emin / Emax")
        self.card_std.set_content(f"{stats.std_dev:.1f} lx", f"CV: {(stats.std_dev/stats.e_avg*100):.1f}%" if stats.e_avg > 0 else "")
        self.card_med.set_content(f"{stats.median:.1f} lx", "50th percentile")
        self.card_range.set_content(f"{stats.range_val:.1f} lx", f"Δ: {stats.e_max - stats.e_min:.0f} lx")

        pct = (stats.count / stats.total_points * 100.0) if stats.total_points > 0 else 0.0
        self.lbl_points_status.setText(f"{stats.count} of {stats.total_points} points measured ({pct:.0f}%)")

    def _on_min_card_clicked(self) -> None:
        if self.stats and self.stats.min_point_id:
            self.highlight_point_requested.emit(self.stats.min_point_id)

    def _on_max_card_clicked(self) -> None:
        if self.stats and self.stats.max_point_id:
            self.highlight_point_requested.emit(self.stats.max_point_id)
