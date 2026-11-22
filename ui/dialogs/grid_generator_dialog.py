"""Grid Generator & Room Reconfiguration Dialog.

Allows regenerating the measurement grid by point count or spacing in meters,
configuring serpentine walking traversal order, and preserving existing readings.
"""

from __future__ import annotations
from typing import Optional
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QSpinBox,
    QDoubleSpinBox,
    QCheckBox,
    QRadioButton,
    QComboBox,
    QButtonGroup,
    QGroupBox,
    QDialogButtonBox,
)

from models.project import LuminationProject
from i18n.translations import tr


class GridGeneratorDialog(QDialog):
    """Dialog to regenerate regular measurement grid points."""

    def __init__(self, project: LuminationProject, parent: Optional[QDialog] = None) -> None:
        super().__init__(parent)
        self.project = project
        self.setWindowTitle(tr("grid_title"))
        self.setMinimumWidth(440)

        # Mode Selection
        mode_group = QGroupBox(tr("grid_mode_group"), self)
        m_layout = QVBoxLayout(mode_group)
        self.rb_count = QRadioButton(tr("grid_by_count"), self)
        self.rb_spacing = QRadioButton(tr("grid_by_spacing"), self)
        self.rb_count.setChecked(True)
        m_layout.addWidget(self.rb_count)
        m_layout.addWidget(self.rb_spacing)

        # Count parameters
        self.count_group = QGroupBox(tr("grid_counts"), self)
        cg_layout = QGridLayout(self.count_group)
        self.spin_cols = QSpinBox(self)
        self.spin_cols.setRange(1, 50)
        self.spin_cols.setValue(project.room.grid_cols)
        self.spin_rows = QSpinBox(self)
        self.spin_rows.setRange(1, 50)
        self.spin_rows.setValue(project.room.grid_rows)
        cg_layout.addWidget(QLabel(tr("grid_cols")), 0, 0)
        cg_layout.addWidget(self.spin_cols, 0, 1)
        cg_layout.addWidget(QLabel(tr("grid_rows")), 1, 0)
        cg_layout.addWidget(self.spin_rows, 1, 1)

        # Spacing parameters
        self.spacing_group = QGroupBox(tr("grid_spacing_group"), self)
        sg_layout = QGridLayout(self.spacing_group)
        self.spin_sx = QDoubleSpinBox(self)
        self.spin_sx.setRange(0.1, 20.0)
        self.spin_sx.setValue(1.0)
        self.spin_sx.setSingleStep(0.2)
        self.spin_sx.setSuffix(" m")

        self.spin_sy = QDoubleSpinBox(self)
        self.spin_sy.setRange(0.1, 20.0)
        self.spin_sy.setValue(1.0)
        self.spin_sy.setSingleStep(0.2)
        self.spin_sy.setSuffix(" m")

        sg_layout.addWidget(QLabel(tr("grid_spacing_x")), 0, 0)
        sg_layout.addWidget(self.spin_sx, 0, 1)
        sg_layout.addWidget(QLabel(tr("grid_spacing_y")), 1, 0)
        sg_layout.addWidget(self.spin_sy, 1, 1)
        self.spacing_group.setEnabled(False)

        # Mode toggle connect
        self.rb_count.toggled.connect(lambda chk: self.count_group.setEnabled(chk))
        self.rb_spacing.toggled.connect(lambda chk: self.spacing_group.setEnabled(chk))

        # Margin, Traversal & Preservation Options
        opt_group = QGroupBox(tr("grid_options").replace("&", "&&"), self)
        o_layout = QGridLayout(opt_group)

        o_layout.addWidget(QLabel(tr("grid_traversal")), 0, 0)
        self.combo_traversal = QComboBox(self)
        self.combo_traversal.addItem(tr("grid_traversal_serpentine"), "serpentine")
        self.combo_traversal.addItem(tr("grid_traversal_rows"), "left_to_right")
        if project.room.traversal_order == "left_to_right":
            self.combo_traversal.setCurrentIndex(1)
        else:
            self.combo_traversal.setCurrentIndex(0)
        o_layout.addWidget(self.combo_traversal, 0, 1)

        o_layout.addWidget(QLabel(tr("grid_margin")), 1, 0)
        self.spin_margin = QDoubleSpinBox(self)
        self.spin_margin.setRange(0.0, 10.0)
        self.spin_margin.setValue(project.room.wall_margin)
        self.spin_margin.setSingleStep(0.1)
        self.spin_margin.setSuffix(" m")
        o_layout.addWidget(self.spin_margin, 1, 1)

        self.chk_preserve = QCheckBox(tr("grid_preserve"), self)
        self.chk_preserve.setChecked(True)
        o_layout.addWidget(self.chk_preserve, 2, 0, 1, 2)

        # Dialog Buttons
        btn_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            Qt.Orientation.Horizontal,
            self,
        )
        btn_box.button(QDialogButtonBox.StandardButton.Ok).setText(tr("btn_ok"))
        btn_box.button(QDialogButtonBox.StandardButton.Cancel).setText(tr("btn_cancel"))
        btn_box.accepted.connect(self._on_accept)
        btn_box.rejected.connect(self.reject)

        # Assembly
        layout = QVBoxLayout(self)
        layout.addWidget(mode_group)
        layout.addWidget(self.count_group)
        layout.addWidget(self.spacing_group)
        layout.addWidget(opt_group)
        layout.addWidget(btn_box)

    def _on_accept(self) -> None:
        """Apply grid regeneration to project."""
        mode = "count" if self.rb_count.isChecked() else "spacing"
        margin = self.spin_margin.value()
        order = self.combo_traversal.currentData()
        self.project.room.traversal_order = order

        if mode == "count":
            rows = self.spin_rows.value()
            cols = self.spin_cols.value()
            self.project.regenerate_grid(
                mode="count",
                rows=rows,
                cols=cols,
                wall_margin=margin,
                preserve_existing=self.chk_preserve.isChecked(),
                traversal_order=order,
            )
        else:
            sx = self.spin_sx.value()
            sy = self.spin_sy.value()
            self.project.regenerate_grid(
                mode="spacing",
                spacing_x=sx,
                spacing_y=sy,
                wall_margin=margin,
                preserve_existing=self.chk_preserve.isChecked(),
                traversal_order=order,
            )

        self.accept()
