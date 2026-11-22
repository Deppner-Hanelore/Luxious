"""New Project / Room Creation Wizard Dialog.

Enables user to specify real room dimensions (length, width, height, working plane height),
wall margins, target illuminance, and grid definition by point counts or distance in meters.
"""

from __future__ import annotations
from typing import Optional, Tuple
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QLineEdit,
    QDoubleSpinBox,
    QSpinBox,
    QPushButton,
    QGroupBox,
    QRadioButton,
    QComboBox,
    QDialogButtonBox,
    QWidget,
)

from models.project import LuminationProject
from models.room import Room
from i18n.translations import tr


class NewProjectDialog(QDialog):
    """Dialog for creating a new lighting survey project and room."""

    def __init__(self, parent: Optional[QDialog] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("dlg_new_project_title"))
        self.setMinimumWidth(500)

        # 1. Project Info Group
        info_group = QGroupBox("Project Information", self)
        i_layout = QGridLayout(info_group)
        i_layout.setSpacing(6)

        self.txt_name = QLineEdit("Office Room Survey", self)
        self.txt_author = QLineEdit("", self)
        self.txt_author.setPlaceholderText("Engineer / Surveyor Name")

        i_layout.addWidget(QLabel(tr("dlg_room_name")), 0, 0)
        i_layout.addWidget(self.txt_name, 0, 1)
        i_layout.addWidget(QLabel("Surveyor / Author:"), 1, 0)
        i_layout.addWidget(self.txt_author, 1, 1)

        # 2. Room Dimensions Group
        geom_group = QGroupBox("Room Real Dimensions (Meters)", self)
        g_layout = QGridLayout(geom_group)
        g_layout.setSpacing(6)

        self.spin_length = QDoubleSpinBox(self)
        self.spin_length.setRange(1.0, 200.0)
        self.spin_length.setValue(6.0)
        self.spin_length.setSingleStep(0.5)
        self.spin_length.setSuffix(" m")

        self.spin_width = QDoubleSpinBox(self)
        self.spin_width.setRange(1.0, 200.0)
        self.spin_width.setValue(4.0)
        self.spin_width.setSingleStep(0.5)
        self.spin_width.setSuffix(" m")

        self.spin_height = QDoubleSpinBox(self)
        self.spin_height.setRange(1.5, 30.0)
        self.spin_height.setValue(2.80)
        self.spin_height.setSingleStep(0.1)
        self.spin_height.setSuffix(" m")

        self.spin_plane = QDoubleSpinBox(self)
        self.spin_plane.setRange(0.0, 10.0)
        self.spin_plane.setValue(0.75)
        self.spin_plane.setSingleStep(0.05)
        self.spin_plane.setSuffix(" m")

        self.spin_margin = QDoubleSpinBox(self)
        self.spin_margin.setRange(0.0, 10.0)
        self.spin_margin.setValue(0.50)
        self.spin_margin.setSingleStep(0.1)
        self.spin_margin.setSuffix(" m")

        self.spin_target = QDoubleSpinBox(self)
        self.spin_target.setRange(0.0, 50000.0)
        self.spin_target.setValue(500.0)
        self.spin_target.setSingleStep(50.0)
        self.spin_target.setSuffix(" lx")

        g_layout.addWidget(QLabel(tr("dlg_room_length")), 0, 0)
        g_layout.addWidget(self.spin_length, 0, 1)
        g_layout.addWidget(QLabel(tr("dlg_room_width")), 0, 2)
        g_layout.addWidget(self.spin_width, 0, 3)

        g_layout.addWidget(QLabel(tr("dlg_room_height")), 1, 0)
        g_layout.addWidget(self.spin_height, 1, 1)
        g_layout.addWidget(QLabel(tr("dlg_plane_height")), 1, 2)
        g_layout.addWidget(self.spin_plane, 1, 3)

        g_layout.addWidget(QLabel(tr("dlg_wall_margin")), 2, 0)
        g_layout.addWidget(self.spin_margin, 2, 1)
        g_layout.addWidget(QLabel(tr("dlg_target_lux")), 2, 2)
        g_layout.addWidget(self.spin_target, 2, 3)

        # 3. Measurement Grid Generation Group
        grid_group = QGroupBox("Initial Measurement Grid Definition", self)
        gr_layout = QVBoxLayout(grid_group)
        gr_layout.setSpacing(6)

        mode_row = QHBoxLayout()
        self.rb_count = QRadioButton(tr("dlg_grid_by_count"), self)
        self.rb_spacing = QRadioButton(tr("dlg_grid_by_spacing"), self)
        self.rb_count.setChecked(True)
        mode_row.addWidget(self.rb_count)
        mode_row.addWidget(self.rb_spacing)
        gr_layout.addLayout(mode_row)

        # Count inputs
        self.count_widget = QWidget(self)
        c_grid = QGridLayout(self.count_widget)
        self.spin_cols = QSpinBox(self)
        self.spin_cols.setRange(1, 50)
        self.spin_cols.setValue(4)
        self.spin_rows = QSpinBox(self)
        self.spin_rows.setRange(1, 50)
        self.spin_rows.setValue(3)
        c_grid.addWidget(QLabel("Columns along X:"), 0, 0)
        c_grid.addWidget(self.spin_cols, 0, 1)
        c_grid.addWidget(QLabel("Rows along Y:"), 0, 2)
        c_grid.addWidget(self.spin_rows, 0, 3)
        gr_layout.addWidget(self.count_widget)

        # Spacing inputs
        self.spacing_widget = QWidget(self)
        s_grid = QGridLayout(self.spacing_widget)
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
        s_grid.addWidget(QLabel(tr("dlg_spacing_x")), 0, 0)
        s_grid.addWidget(self.spin_sx, 0, 1)
        s_grid.addWidget(QLabel(tr("dlg_spacing_y")), 0, 2)
        s_grid.addWidget(self.spin_sy, 0, 3)
        self.spacing_widget.setEnabled(False)
        gr_layout.addWidget(self.spacing_widget)

        # Mode toggles
        self.rb_count.toggled.connect(lambda chk: self.count_widget.setEnabled(chk))
        self.rb_spacing.toggled.connect(lambda chk: self.spacing_widget.setEnabled(chk))

        # Traversal order selector
        trav_row = QHBoxLayout()
        trav_row.addWidget(QLabel(tr("dlg_traversal_order")))
        self.combo_traversal = QComboBox(self)
        self.combo_traversal.addItem(tr("dlg_traversal_serpentine"), "serpentine")
        self.combo_traversal.addItem(tr("dlg_traversal_left_to_right"), "left_to_right")
        trav_row.addWidget(self.combo_traversal)
        gr_layout.addLayout(trav_row)

        # Standard Dialog Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        # Main Layout
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)
        main_layout.addWidget(info_group)
        main_layout.addWidget(geom_group)
        main_layout.addWidget(grid_group)
        main_layout.addSpacing(6)
        main_layout.addWidget(button_box)

    def get_created_project(self) -> LuminationProject:
        """Construct and return the newly configured LuminationProject."""
        traversal = self.combo_traversal.currentData()
        room = Room(
            name=self.txt_name.text().strip() or "Room 1",
            length=self.spin_length.value(),
            width=self.spin_width.value(),
            height=self.spin_height.value(),
            measurement_plane_height=self.spin_plane.value(),
            wall_margin=self.spin_margin.value(),
            grid_cols=self.spin_cols.value(),
            grid_rows=self.spin_rows.value(),
            traversal_order=traversal,
        )

        project = LuminationProject(
            name=self.txt_name.text().strip() or "New Lighting Project",
            author=self.txt_author.text().strip(),
            room=room,
            target_lux=self.spin_target.value() if self.spin_target.value() > 0 else None,
        )

        if self.rb_count.isChecked():
            project.regenerate_grid(
                mode="count",
                rows=self.spin_rows.value(),
                cols=self.spin_cols.value(),
                wall_margin=self.spin_margin.value(),
                centered_in_cells=True,
                traversal_order=traversal,
            )
        else:
            project.regenerate_grid(
                mode="spacing",
                spacing_x=self.spin_sx.value(),
                spacing_y=self.spin_sy.value(),
                wall_margin=self.spin_margin.value(),
                centered_in_cells=True,
                traversal_order=traversal,
            )

        return project

    def create_project(self) -> LuminationProject:
        return self.get_created_project()
