"""Point Measurement Quick-Edit Dialog.

Fast modal dialog to enter or modify a physical lux meter reading for a single point.
"""

from __future__ import annotations
from typing import Optional
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QGridLayout,
    QLabel,
    QLineEdit,
    QDoubleSpinBox,
    QDialogButtonBox,
    QGroupBox,
)

from models.measurement import MeasurementPoint
from models.room import Room


class PointEditDialog(QDialog):
    """Modal dialog for editing a single measurement point."""

    def __init__(
        self,
        point: MeasurementPoint,
        room: Room,
        parent: Optional[QDialog] = None,
    ) -> None:
        super().__init__(parent)
        self.point = point
        self.room = room
        self.setWindowTitle(f"Edit Measurement — {point.id}")
        self.setMinimumWidth(360)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        group = QGroupBox(f"Point {point.id} Details", self)
        g_layout = QGridLayout(group)
        g_layout.setSpacing(6)

        # Coordinate X
        self.spin_x = QDoubleSpinBox(self)
        self.spin_x.setRange(0.0, room.length)
        self.spin_x.setValue(point.x)
        self.spin_x.setSingleStep(0.1)
        self.spin_x.setSuffix(" m")
        self.spin_x.setEnabled(not point.locked_coordinates)

        # Coordinate Y
        self.spin_y = QDoubleSpinBox(self)
        self.spin_y.setRange(0.0, room.width)
        self.spin_y.setValue(point.y)
        self.spin_y.setSingleStep(0.1)
        self.spin_y.setSuffix(" m")
        self.spin_y.setEnabled(not point.locked_coordinates)

        # Measured Lux
        self.spin_lux = QDoubleSpinBox(self)
        self.spin_lux.setRange(-1.0, 100000.0)
        self.spin_lux.setSpecialValueText("")
        self.spin_lux.setValue(point.lux if point.lux is not None else -1.0)
        self.spin_lux.setSingleStep(10.0)
        self.spin_lux.setSuffix(" lx")
        self.spin_lux.selectAll()

        # Expected Lux
        self.spin_exp = QDoubleSpinBox(self)
        self.spin_exp.setRange(-1.0, 100000.0)
        self.spin_exp.setSpecialValueText("")
        self.spin_exp.setValue(point.expected_lux if point.expected_lux is not None else -1.0)
        self.spin_exp.setSingleStep(10.0)
        self.spin_exp.setSuffix(" lx")

        # Notes
        self.txt_notes = QLineEdit(point.notes, self)
        self._initial_values = {
            "x": self.spin_x.value(),
            "y": self.spin_y.value(),
            "lux": self.spin_lux.value(),
            "expected": self.spin_exp.value(),
        }

        g_layout.addWidget(QLabel("X Coordinate:"), 0, 0)
        g_layout.addWidget(self.spin_x, 0, 1)
        g_layout.addWidget(QLabel("Y Coordinate:"), 1, 0)
        g_layout.addWidget(self.spin_y, 1, 1)
        g_layout.addWidget(QLabel("<b>Measured Lux:</b>"), 2, 0)
        g_layout.addWidget(self.spin_lux, 2, 1)
        g_layout.addWidget(QLabel("Expected / DIALux Lux:"), 3, 0)
        g_layout.addWidget(self.spin_exp, 3, 1)
        g_layout.addWidget(QLabel("Notes:"), 4, 0)
        g_layout.addWidget(self.txt_notes, 4, 1)

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self
        )
        button_box.accepted.connect(self._on_accept)
        button_box.rejected.connect(self.reject)

        layout.addWidget(group)
        layout.addWidget(button_box)

        # Auto-focus the measured lux spinbox
        self.spin_lux.setFocus()

    def _on_accept(self) -> None:
        if not self.point.locked_coordinates:
            if self.spin_x.value() != self._initial_values["x"]:
                self.point.x = self.spin_x.value()
            if self.spin_y.value() != self._initial_values["y"]:
                self.point.y = self.spin_y.value()

        lux_val = self.spin_lux.value()
        if lux_val != self._initial_values["lux"]:
            if lux_val < 0:
                self.point.clear_reading()
            else:
                self.point.record_reading(lux_val, device_name="Manual Entry")

        exp_val = self.spin_exp.value()
        if exp_val != self._initial_values["expected"]:
            self.point.expected_lux = exp_val if exp_val >= 0 else None

        self.point.notes = self.txt_notes.text().strip()
        self.accept()
