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


class _ValueLabel(QLabel):
    """The value of a card; for minimum and maximum it can be clicked to select that point."""

    clicked = Signal()

    def __init__(self, text: str, clickable: bool, parent: QWidget) -> None:
        super().__init__(text, parent)
        self.clickable = clickable
        self.setObjectName("kpiValueLink" if clickable else "kpiValue")
        if clickable:
            self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mouseReleaseEvent(self, event) -> None:
        if self.clickable and event.button() == Qt.MouseButton.LeftButton and self.rect().contains(event.position().toPoint()):
            self.clicked.emit()
        super().mouseReleaseEvent(event)


class KPICard(QFrame):
    """Card showing one lighting result.

    Only cards created with ``clickable=True`` (minimum and maximum) react to the mouse, and only
    on their value: hovering shows it as a link and a click selects that point. Every other card
    and every other part of a card is plain text with no hover or click effect.
    """

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
        self.setObjectName("kpiCard")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        # Selectors are limited to this card and its own labels, so the labels inside (QLabel is a
        # QFrame too) no longer pick up borders and hover highlights meant for the card.
        self.setStyleSheet(f"""
            QFrame#kpiCard {{
                background-color: #ffffff;
                border: 1px solid #e2e8f0;
                border-left: 3.5px solid {accent_color};
                border-radius: 4px;
                padding: 4px 8px;
            }}
            QLabel {{ border: none; background: transparent; padding: 0px; }}
            QLabel#kpiTitle {{ font-size: 9px; font-weight: 700; color: #64748b; letter-spacing: 0.5px; }}
            QLabel#kpiValue, QLabel#kpiValueLink {{ font-size: 16px; font-weight: 700; color: #0f172a; }}
            QLabel#kpiValueLink:hover {{ color: {accent_color}; text-decoration: underline; }}
            QLabel#kpiSub {{ font-size: 9px; color: #64748b; }}
        """)

        self.lbl_title = QLabel(title.upper(), self)
        self.lbl_title.setObjectName("kpiTitle")

        self.lbl_value = _ValueLabel(value, clickable, self)
        self.lbl_value.clicked.connect(self.clicked.emit)

        self.lbl_sub = QLabel(subtitle, self)
        self.lbl_sub.setObjectName("kpiSub")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(1)
        layout.addWidget(self.lbl_title)
        layout.addWidget(self.lbl_value, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self.lbl_sub)

    def set_title(self, title: str) -> None:
        self.lbl_title.setText(title.upper())

    def set_content(self, value: str, subtitle: str = "") -> None:
        self.lbl_value.setText(value)
        self.lbl_sub.setText(subtitle)


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

        self.card_avg = KPICard(tr("kpi_card_avg"), "-", tr("kpi_sub_target_none"), accent_color="#2563eb", parent=self)
        self.card_u0 = KPICard(tr("kpi_card_u0"), "-", tr("kpi_sub_u0"), accent_color="#16a34a", parent=self)
        self.card_min = KPICard(tr("kpi_card_min"), "-", tr("kpi_sub_locate"), accent_color="#0284c7", clickable=True, parent=self)
        self.card_max = KPICard(tr("kpi_card_max"), "-", tr("kpi_sub_locate"), accent_color="#dc2626", clickable=True, parent=self)

        self.card_min.clicked.connect(self._on_min_card_clicked)
        for card in (self.card_min, self.card_max):
            card.lbl_value.setToolTip(tr("kpi_sub_locate"))
        self.card_max.clicked.connect(self._on_max_card_clicked)

        p_layout.addWidget(self.card_avg, 0, 0)
        p_layout.addWidget(self.card_u0, 0, 1)
        p_layout.addWidget(self.card_min, 1, 0)
        p_layout.addWidget(self.card_max, 1, 1)

        # 2. Secondary Metrics Table
        self.group_sec = QGroupBox(tr("kpi_extended"), self)
        s_layout = QGridLayout(self.group_sec)
        s_layout.setSpacing(4)

        self.card_u1 = KPICard(tr("kpi_card_u1"), "-", tr("kpi_sub_u1"), accent_color="#8b5cf6", parent=self)
        self.card_std = KPICard(tr("kpi_card_std"), "-", tr("kpi_sub_dispersion"), accent_color="#64748b", parent=self)
        self.card_med = KPICard(tr("kpi_card_median"), "-", tr("kpi_sub_percentile"), accent_color="#0d9488", parent=self)
        self.card_range = KPICard(tr("kpi_card_range"), "-", tr("kpi_sub_range"), accent_color="#f59e0b", parent=self)

        s_layout.addWidget(self.card_u1, 0, 0)
        s_layout.addWidget(self.card_std, 0, 1)
        s_layout.addWidget(self.card_med, 1, 0)
        s_layout.addWidget(self.card_range, 1, 1)

        # 3. Status Footer
        self.lbl_points_status = QLabel(tr("kpi_points_none"), self)
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
        self.group_sec.setTitle(tr("kpi_extended"))
        self.card_avg.set_title(tr("kpi_card_avg"))
        self.card_u0.set_title(tr("kpi_card_u0"))
        self.card_min.set_title(tr("kpi_card_min"))
        self.card_max.set_title(tr("kpi_card_max"))
        for card in (self.card_min, self.card_max):
            card.lbl_value.setToolTip(tr("kpi_sub_locate"))
        self.card_u1.set_title(tr("kpi_card_u1"))
        self.card_std.set_title(tr("kpi_card_std"))
        self.card_med.set_title(tr("kpi_card_median"))
        self.card_range.set_title(tr("kpi_card_range"))
        self.update_statistics(self.stats)

    def update_statistics(self, stats: Optional[StatisticalSummary]) -> None:
        """Update KPI cards with newly computed statistical results."""
        self.stats = stats
        if stats is None or stats.count == 0:
            self.card_avg.set_content("-", tr("kpi_sub_target_none"))
            self.card_u0.set_content("-", tr("kpi_sub_u0"))
            self.card_min.set_content("-", tr("kpi_sub_locate"))
            self.card_max.set_content("-", tr("kpi_sub_locate"))
            self.card_u1.set_content("-", tr("kpi_sub_u1"))
            self.card_std.set_content("-", tr("kpi_sub_dispersion"))
            self.card_med.set_content("-", tr("kpi_sub_percentile"))
            self.card_range.set_content("-", tr("kpi_sub_range"))
            self.lbl_points_status.setText(tr("kpi_points_none"))
            return

        self.card_avg.set_content(f"{stats.e_avg:.1f} lx", tr("kpi_sub_count", count=stats.count))
        self.card_u0.set_content(f"{stats.uniformity_u0:.3f}", tr("kpi_sub_u0_values", emin=f"{stats.e_min:.0f}", eavg=f"{stats.e_avg:.0f}"))

        min_sub = tr("kpi_sub_at_point", point=stats.min_point_id) if stats.min_point_id else ""
        self.card_min.set_content(f"{stats.e_min:.1f} lx", min_sub)

        max_sub = tr("kpi_sub_at_point", point=stats.max_point_id) if stats.max_point_id else ""
        self.card_max.set_content(f"{stats.e_max:.1f} lx", max_sub)

        self.card_u1.set_content(f"{stats.uniformity_u1:.3f}", tr("kpi_sub_u1"))
        self.card_std.set_content(f"{stats.std_dev:.1f} lx", tr("kpi_sub_cv", cv=f"{(stats.std_dev/stats.e_avg*100):.1f}") if stats.e_avg > 0 else "")
        self.card_med.set_content(f"{stats.median:.1f} lx", tr("kpi_sub_percentile"))
        self.card_range.set_content(f"{stats.range_val:.1f} lx", f"Δ: {stats.e_max - stats.e_min:.0f} lx")

        pct = (stats.count / stats.total_points * 100.0) if stats.total_points > 0 else 0.0
        self.lbl_points_status.setText(tr("kpi_points_status", count=stats.count, total=stats.total_points, pct=f"{pct:.0f}"))

    def _on_min_card_clicked(self) -> None:
        if self.stats and self.stats.min_point_id:
            self.highlight_point_requested.emit(self.stats.min_point_id)

    def _on_max_card_clicked(self) -> None:
        if self.stats and self.stats.max_point_id:
            self.highlight_point_requested.emit(self.stats.max_point_id)
