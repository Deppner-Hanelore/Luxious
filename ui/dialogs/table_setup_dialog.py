"""Ask how far apart the points in an opened table were and how far from the walls."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from i18n.translations import tr
from persistence.table_io import room_size_for_table


class TableSetupDialog(QDialog):
    """The table gives the number of points; this window gives their spacing in metres."""

    DEFAULTS_GROUP = "new_survey_defaults"

    def __init__(self, rows: int, cols: int, parent: Optional[QWidget] = None,
                 settings: Optional[QSettings] = None) -> None:
        super().__init__(parent)
        self.rows = rows
        self.cols = cols
        self.setWindowTitle(tr("table_setup_title"))
        self.setMinimumWidth(460)

        store = settings if settings is not None else QSettings()
        store.beginGroup(self.DEFAULTS_GROUP)
        try:
            spacing_x = float(store.value("spacing_x", 1.0) or 1.0)
            spacing_y = float(store.value("spacing_y", spacing_x) or spacing_x)
            margin = float(store.value("margin", 0.5) or 0.0)
        except (TypeError, ValueError):
            spacing_x, spacing_y, margin = 1.0, 1.0, 0.5
        finally:
            store.endGroup()
        self.traversal_order = str((settings if settings is not None else QSettings()).value(
            f"{self.DEFAULTS_GROUP}/traversal", "serpentine") or "serpentine")

        intro = QLabel(tr("table_setup_intro", rows=rows, cols=cols), self)
        intro.setWordWrap(True)
        self.spacing_x = self._number(spacing_x, 0.05)
        self.spacing_y = self._number(spacing_y, 0.05)
        self.margin = self._number(margin, 0.0)
        form = QFormLayout()
        form.addRow(tr("setup_spacing_x"), self.spacing_x)
        form.addRow(tr("setup_spacing_y"), self.spacing_y)
        form.addRow(tr("setup_margin"), self.margin)
        self.lbl_room = QLabel(self)
        self.lbl_room.setStyleSheet("background: #f1f5f9; border: 1px solid #cbd5e1; padding: 8px;")

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText(tr("table_setup_ok"))
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText(tr("btn_cancel"))
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(intro)
        layout.addLayout(form)
        layout.addWidget(self.lbl_room)
        layout.addWidget(buttons)
        for spin in (self.spacing_x, self.spacing_y, self.margin):
            spin.valueChanged.connect(self._update_room_size)
        self._update_room_size()

    def _number(self, value: float, minimum: float) -> QDoubleSpinBox:
        spin = QDoubleSpinBox(self)
        spin.setRange(minimum, 50.0)
        spin.setDecimals(2)
        spin.setSingleStep(0.1)
        spin.setSuffix(" m")
        spin.setValue(value)
        spin.setMinimumHeight(36)
        return spin

    def room_size(self) -> tuple:
        return room_size_for_table(self.rows, self.cols, self.spacing_x.value(), self.spacing_y.value(), self.margin.value())

    def _update_room_size(self) -> None:
        length, width = self.room_size()
        self.lbl_room.setText(tr("table_setup_room", length=f"{length:.2f}", width=f"{width:.2f}"))
