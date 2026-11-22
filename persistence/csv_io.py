"""CSV export of illuminance measurements in the grid table layout (see persistence.table_io)."""

from __future__ import annotations

from typing import List

from models.measurement import MeasurementPoint
from models.project import LuminationProject
from persistence.table_io import write_table


def export_measurements_to_csv(project: LuminationProject, file_path: str) -> List[MeasurementPoint]:
    """Write a plain-text CSV grid; returns hand-added points that have no place in the grid."""
    return write_table(project, file_path)
