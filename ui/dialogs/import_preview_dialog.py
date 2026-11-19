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
        self.setWindowTitle("Review imported readings")
        self.setMinimumSize(640, 420)

        summary = QLabel(
            f"Preview: {updated_count} existing points updated; "
            f"{created_count} points added. Cancel leaves this survey unchanged."
        )
        summary.setWordWrap(True)
        self.table = QTableWidget(len(project.points), 5, self)
        self.table.setHorizontalHeaderLabels(["Point", "X (m)", "Y (m)", "Measured (lx)", "Expected (lx)"])
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        for row, point in enumerate(project.points):
            values = (
                point.id,
                f"{point.x:g}",
                f"{point.y:g}",
                "Pending" if point.lux is None else f"{point.lux:g}",
                "—" if point.expected_lux is None else f"{point.expected_lux:g}",
            )
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(row, col, item)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Ok,
            self,
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Apply import")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addWidget(summary)
        layout.addWidget(self.table, 1)
        layout.addWidget(buttons)
