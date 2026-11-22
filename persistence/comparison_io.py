"""Load the values of a compared file (Luxious project, Excel or CSV grid) onto a survey."""

from __future__ import annotations

import os
from typing import Dict, Optional

from i18n.translations import tr
from models.project import LuminationProject
from persistence.table_io import TableError, check_table_fits, grid_layout, is_table_file, read_table


def comparison_values(project: LuminationProject, path: str) -> Dict[str, Optional[float]]:
    """Map each grid point ID of `project` to the compared file's reading at the same grid position.

    Raises TableError when the compared grid has a different number of rows or columns.
    """
    layout = grid_layout(project)
    if is_table_file(path):
        values = read_table(path)
        check_table_fits(values, layout)
        lookup = {
            (r, c): value
            for r, row in enumerate(values)
            for c, value in enumerate(row)
        }
    else:
        from persistence.project_io import load_project

        try:
            other = load_project(path)
        except Exception as exc:
            raise TableError(tr("table_err_unreadable", error=exc)) from exc
        other_layout = grid_layout(other)
        if (other_layout.rows, other_layout.cols) != (layout.rows, layout.cols):
            raise TableError(tr(
                "table_err_size",
                table_rows=other_layout.rows,
                table_cols=other_layout.cols,
                rows=layout.rows,
                cols=layout.cols,
            ))
        lookup = {
            key: (point.lux if point.is_measured else None)
            for key, point in other_layout.cells.items()
        }
    result = {point.id: lookup.get(key) for key, point in layout.cells.items()}
    if not any(value is not None for value in result.values()):
        raise TableError(tr("table_err_empty"))
    return result


def apply_comparison(project: LuminationProject, path: str) -> int:
    """Store the compared file's values on the survey; returns how many points got a value."""
    values = comparison_values(project, path)
    for point in project.points:
        point.expected_lux = values.get(point.id)
    project.comparison_file = os.path.basename(path)
    project.mark_modified()
    return sum(1 for value in values.values() if value is not None)
