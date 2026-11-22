"""Review CSV changes on a detached project before committing them."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from models.project import LuminationProject
from i18n.translations import tr


class ImportPreviewDialog(QDialog):
    """Show the resulting readings and allow the user to cancel the import."""

    def __init__(
        self,
        project: LuminationProject,
        updated_count: int,
        created_count: int,
        parent: Optional[QDialog] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("preview_title"))
        self.setMinimumSize(640, 420)

        summary = QLabel(tr("preview_summary", updated=updated_count, created=created_count))
        summary.setWordWrap(True)
        self.table = QTableWidget(len(project.points), 5, self)
        self.table.setHorizontalHeaderLabels([tr("preview_col_point"), tr("col_x"), tr("col_y"), tr("col_lux"), tr("col_expected")])
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        for row, point in enumerate(project.points):
            values = (
                point.id,
                f"{point.x:g}",
                f"{point.y:g}",
                tr("preview_pending") if point.lux is None else f"{point.lux:g}",
                "-" if point.expected_lux is None else f"{point.expected_lux:g}",
            )
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(row, col, item)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Ok,
            self,
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText(tr("preview_apply"))
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText(tr("btn_cancel"))
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addWidget(summary)
        layout.addWidget(self.table, 1)
        layout.addWidget(buttons)
