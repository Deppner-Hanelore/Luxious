"""Layer & Visual Preferences Control Widget.

Controls layer toggles (Heatmap, Isolux Contours, Measurement Points, Text Values,
Grid, Margins), colormap selection, contour interval, and scientific interpolation method.
"""

from __future__ import annotations
from typing import Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QLabel,
    QGroupBox,
)

from models.project import LuminationProject, VisualizationSettings
from visualization.color_maps import AVAILABLE_COLORMAPS
from i18n.translations import tr, TranslationManager


class LayerControlWidget(QWidget):
    """Widget for configuring 2D map layers, styling, and interpolation options.

    Signals:
        settings_changed (): Emitted when any visual preference is toggled.
    """
    settings_changed = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        self.project: Optional[LuminationProject] = None
        self._block_signals = False

        # Layer Toggles Group
        self.layer_group = QGroupBox(tr("layers_group"), self)
        l_layout = QVBoxLayout(self.layer_group)
        l_layout.setSpacing(4)

        self.chk_heatmap = QCheckBox(tr("layers_heatmap"), self)
        self.chk_contours = QCheckBox(tr("layers_contours"), self)
        self.chk_points = QCheckBox(tr("layers_points"), self)
        self.chk_values = QCheckBox(tr("layers_values"), self)
        self.chk_grid = QCheckBox(tr("layers_grid"), self)

        self.chk_values.setChecked(False)  # Off by default for clean map
        for chk in (self.chk_heatmap, self.chk_contours, self.chk_points, self.chk_grid):
            chk.setChecked(True)

        for chk in (self.chk_heatmap, self.chk_contours, self.chk_points, self.chk_values, self.chk_grid):
            chk.toggled.connect(self._on_layer_toggled)
            l_layout.addWidget(chk)

        # Scientific Options Group
        self.sci_group = QGroupBox(tr("layers_sci_group"), self)
        s_layout = QVBoxLayout(self.sci_group)
        s_layout.setSpacing(4)

        # Interpolation Method
        self.lbl_interp = QLabel(tr("layers_interp"), self)
        self.lbl_interp.setStyleSheet("font-weight: 600; font-size: 11px;")
        self.combo_interp = QComboBox(self)
        for method in ("linear", "cubic", "rbf", "nearest"):
            self.combo_interp.addItem(tr(f"layers_interp_{method}"), method)
        self.combo_interp.currentIndexChanged.connect(self._on_interp_changed)

        # Colormap
        self.lbl_cmap = QLabel(tr("layers_cmap"), self)
        self.lbl_cmap.setStyleSheet("font-weight: 600; font-size: 11px;")
        self.combo_cmap = QComboBox(self)
        for key in AVAILABLE_COLORMAPS:
            self.combo_cmap.addItem(tr(f"cmap_{key}"), key)
        self.combo_cmap.currentIndexChanged.connect(self._on_cmap_changed)

        # Contour Interval
        self.lbl_contour = QLabel(tr("layers_contour_step"), self)
        self.lbl_contour.setStyleSheet("font-weight: 600; font-size: 11px;")
        self.spin_contour = QDoubleSpinBox(self)
        self.spin_contour.setRange(5, 5000)
        self.spin_contour.setValue(50.0)
        self.spin_contour.setSingleStep(25.0)
        self.spin_contour.setSuffix(" lx")
        self.spin_contour.valueChanged.connect(self._on_contour_interval_changed)

        s_layout.addWidget(self.lbl_interp)
        s_layout.addWidget(self.combo_interp)
        s_layout.addWidget(self.lbl_cmap)
        s_layout.addWidget(self.combo_cmap)
        s_layout.addWidget(self.lbl_contour)
        s_layout.addWidget(self.spin_contour)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(6, 6, 6, 6)
        main_layout.setSpacing(6)
        main_layout.addWidget(self.layer_group)
        main_layout.addWidget(self.sci_group)
        main_layout.addStretch()

        TranslationManager.get_instance().language_changed.connect(self.retranslate_ui)

    def retranslate_ui(self, *_args) -> None:
        """Update strings on language change."""
        self.layer_group.setTitle(tr("layers_group"))
        self.chk_heatmap.setText(tr("layers_heatmap"))
        self.chk_contours.setText(tr("layers_contours"))
        self.chk_points.setText(tr("layers_points"))
        self.chk_values.setText(tr("layers_values"))
        self.chk_grid.setText(tr("layers_grid"))
        self.sci_group.setTitle(tr("layers_sci_group"))
        self.lbl_interp.setText(tr("layers_interp"))
        self.lbl_cmap.setText(tr("layers_cmap"))
        self.lbl_contour.setText(tr("layers_contour_step"))
        for index in range(self.combo_interp.count()):
            self.combo_interp.setItemText(index, tr(f"layers_interp_{self.combo_interp.itemData(index)}"))
        for index in range(self.combo_cmap.count()):
            self.combo_cmap.setItemText(index, tr(f"cmap_{self.combo_cmap.itemData(index)}"))

    def set_project(self, project: LuminationProject) -> None:
        """Bind project visualization settings to UI controls."""
        self.project = project
        s = project.visualization_settings

        self._block_signals = True
        try:
            self.chk_heatmap.setChecked(s.show_heatmap)
            self.chk_contours.setChecked(s.show_contours)
            self.chk_points.setChecked(s.show_points)
            self.chk_values.setChecked(s.show_values)
            self.chk_grid.setChecked(s.show_grid)

            idx = self.combo_interp.findData(s.interpolation_method)
            if idx >= 0:
                self.combo_interp.setCurrentIndex(idx)

            idx_cmap = self.combo_cmap.findData(s.colormap)
            if idx_cmap >= 0:
                self.combo_cmap.setCurrentIndex(idx_cmap)

            self.spin_contour.setValue(s.contour_interval)
        finally:
            self._block_signals = False

    def _on_layer_toggled(self) -> None:
        if self._block_signals or not self.project:
            return
        s = self.project.visualization_settings
        s.show_heatmap = self.chk_heatmap.isChecked()
        s.show_contours = self.chk_contours.isChecked()
        s.show_points = self.chk_points.isChecked()
        s.show_values = self.chk_values.isChecked()
        s.show_grid = self.chk_grid.isChecked()
        self.settings_changed.emit()

    def _on_interp_changed(self) -> None:
        if self._block_signals or not self.project:
            return
        method = self.combo_interp.currentData()
        self.project.visualization_settings.interpolation_method = method
        self.settings_changed.emit()

    def _on_cmap_changed(self) -> None:
        if self._block_signals or not self.project:
            return
        cmap = self.combo_cmap.currentData()
        self.project.visualization_settings.colormap = cmap
        self.settings_changed.emit()

    def _on_contour_interval_changed(self, val: float) -> None:
        if self._block_signals or not self.project:
            return
        self.project.visualization_settings.contour_interval = val
        self.settings_changed.emit()
