"""Grid tables of lux readings in CSV and Excel.

Layout: one cell per measurement point, laid out like the room seen from above.
Cell A1 is the top-left point, B1 the next point in the first row, and so on.
An empty cell is a point that has not been measured yet. Numbers may use a
decimal point or a decimal comma.
"""

from __future__ import annotations

import csv
import io
import math
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

from i18n.translations import tr
from models.measurement import MeasurementPoint
from models.project import LuminationProject
from models.room import Room

EXCEL_SUFFIXES = (".xlsx", ".xlsm")
CSV_SUFFIXES = (".csv", ".txt")
TABLE_SUFFIXES = EXCEL_SUFFIXES + CSV_SUFFIXES
TABLE_DEVICE_NAME = "Table Input"

Grid = List[List[Optional[float]]]


class TableError(ValueError):
    """A table that cannot be used; the message is shown to the user as is."""


@dataclass
class GridLayout:
    """Where each grid point of a survey sits in the table."""

    rows: int
    cols: int
    cells: Dict[Tuple[int, int], MeasurementPoint] = field(default_factory=dict)
    extra_points: List[MeasurementPoint] = field(default_factory=list)


def is_table_file(path: str) -> bool:
    return path.lower().endswith(TABLE_SUFFIXES)


def cell_name(row: int, col: int) -> str:
    """Spreadsheet name of a zero-based cell, e.g. (0, 0) -> A1, (3, 27) -> AB4."""
    letters = ""
    col += 1
    while col:
        col, rest = divmod(col - 1, 26)
        letters = chr(65 + rest) + letters
    return f"{letters}{row + 1}"


# ---------------------------------------------------------------- reading

def _parse_cell(value, row: int, col: int) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, bool):
        raise TableError(tr("table_err_text_cell", cell=cell_name(row, col), value=value))
    if isinstance(value, (int, float)):
        number = float(value)
    else:
        text = str(value).strip().replace(" ", "").replace(" ", "")
        if not text:
            return None
        try:
            number = float(text.replace(",", "."))
        except ValueError:
            raise TableError(tr("table_err_text_cell", cell=cell_name(row, col), value=str(value).strip())) from None
    if not math.isfinite(number):
        raise TableError(tr("table_err_text_cell", cell=cell_name(row, col), value=value))
    if number < 0:
        raise TableError(tr("table_err_negative", cell=cell_name(row, col), value=f"{number:g}"))
    return number


def _raw_rows_from_csv(path: str) -> List[List[str]]:
    with open(path, "r", encoding="utf-8-sig", newline="") as handle:
        content = handle.read()
    # Semicolons are used where the decimal separator is a comma (Romanian, German Excel);
    # in that case the commas inside cells are decimals, not separators.
    if ";" in content:
        delimiter = ";"
    elif "\t" in content:
        delimiter = "\t"
    else:
        delimiter = ","
    return [list(row) for row in csv.reader(io.StringIO(content), delimiter=delimiter)]


def _raw_rows_from_excel(path: str) -> List[list]:
    from openpyxl import load_workbook

    workbook = load_workbook(path, read_only=True, data_only=True)
    try:
        sheet = workbook.active if workbook.active is not None else workbook.worksheets[0]
        return [list(row) for row in sheet.iter_rows(values_only=True)]
    finally:
        workbook.close()


def read_table(path: str) -> Grid:
    """Read a grid of readings. Raises TableError with a message naming the bad cell."""
    try:
        raw = _raw_rows_from_excel(path) if path.lower().endswith(EXCEL_SUFFIXES) else _raw_rows_from_csv(path)
    except TableError:
        raise
    except Exception as exc:  # unreadable or not a table at all
        raise TableError(tr("table_err_unreadable", error=exc)) from exc

    grid: Grid = [[_parse_cell(value, r, c) for c, value in enumerate(row)] for r, row in enumerate(raw)]
    # The grid extends to the last row and column that hold a reading.
    last_row = max((r for r, row in enumerate(grid) if any(v is not None for v in row)), default=-1)
    last_col = max((c for row in grid for c, v in enumerate(row) if v is not None), default=-1)
    if last_row < 0:
        raise TableError(tr("table_err_empty"))
    return [
        [(row[c] if c < len(row) else None) for c in range(last_col + 1)]
        for row in grid[: last_row + 1]
    ]


# ---------------------------------------------------------------- survey <-> grid

def grid_layout(project: LuminationProject) -> GridLayout:
    """Place every generated grid point in a (row, column) cell; row 0 is the top of the room."""
    grid_points = [p for p in project.points if p.locked_coordinates]
    extra = [p for p in project.points if not p.locked_coordinates]
    xs = sorted({round(p.x, 3) for p in grid_points})
    ys = sorted({round(p.y, 3) for p in grid_points}, reverse=True)
    cells: Dict[Tuple[int, int], MeasurementPoint] = {}
    for point in grid_points:
        key = (ys.index(round(point.y, 3)), xs.index(round(point.x, 3)))
        if key in cells:
            extra.append(point)
        else:
            cells[key] = point
    return GridLayout(rows=len(ys), cols=len(xs), cells=cells, extra_points=extra)


def project_to_grid(project: LuminationProject) -> Tuple[Grid, List[MeasurementPoint]]:
    """Readings laid out as the table; also returns points that have no place in it."""
    layout = grid_layout(project)
    grid: Grid = [[None] * layout.cols for _ in range(layout.rows)]
    for (row, col), point in layout.cells.items():
        grid[row][col] = point.lux if point.is_measured else None
    return grid, layout.extra_points


def check_table_fits(values: Grid, layout: GridLayout) -> None:
    """Refuse a table with more rows or columns than the survey's grid.

    Missing rows or columns at the bottom or right are allowed: those points
    simply have no reading yet (a spreadsheet does not keep empty edge cells).
    """
    table_rows = len(values)
    table_cols = max((len(row) for row in values), default=0)
    if table_rows > layout.rows or table_cols > layout.cols or layout.rows == 0:
        raise TableError(tr(
            "table_err_size",
            table_rows=table_rows,
            table_cols=table_cols,
            rows=layout.rows,
            cols=layout.cols,
        ))


def apply_table_to_project(project: LuminationProject, values: Grid) -> int:
    """Write table readings onto the survey's grid points. Returns how many points got a reading."""
    layout = grid_layout(project)
    check_table_fits(values, layout)
    updated = 0
    for row_index, row in enumerate(values):
        for col_index, value in enumerate(row):
            point = layout.cells.get((row_index, col_index))
            if point is None or value is None:
                continue
            point.record_reading(value, device_name=TABLE_DEVICE_NAME)
            updated += 1
    return updated


def room_size_for_table(rows: int, cols: int, spacing_x: float, spacing_y: float, margin: float) -> Tuple[float, float]:
    """Room length and width when the points are `spacing` apart and `margin` from the walls."""
    return (cols - 1) * spacing_x + 2 * margin, (rows - 1) * spacing_y + 2 * margin


def project_from_table(
    values: Grid,
    name: str,
    spacing_x: float,
    spacing_y: float,
    margin: float,
    traversal_order: str = "serpentine",
) -> LuminationProject:
    """Build a new survey whose grid matches the table, then fill in its readings."""
    rows = len(values)
    cols = max(len(row) for row in values)
    length, width = room_size_for_table(rows, cols, spacing_x, spacing_y, margin)
    if length <= 0 or width <= 0:
        raise TableError(tr("table_err_no_room"))
    room = Room(name=name, length=length, width=width, wall_margin=margin,
                grid_rows=rows, grid_cols=cols, traversal_order=traversal_order)
    project = LuminationProject(name=name, room=room)
    project.regenerate_grid(mode="count", rows=rows, cols=cols, wall_margin=margin, traversal_order=traversal_order)
    apply_table_to_project(project, values)
    project.is_dirty = True
    return project


# ---------------------------------------------------------------- writing

def _format_number(value: float) -> str:
    text = f"{round(value, 3):.3f}".rstrip("0").rstrip(".")
    return text or "0"


def _add_comparison_sheet(workbook, project: LuminationProject) -> None:
    """Second sheet with the comparison results, only when the survey was compared with a file."""
    from analysis.comparison import compare_with_file

    result = compare_with_file(project.points)
    if result is None:
        return
    sheet = workbook.create_sheet(tr("xl_sheet_comparison")[:31])
    if result.has_depreciation:
        depreciation = f"{result.depreciation_pct:.1f}%"
    else:
        depreciation = tr("pdf_cmp_no_depreciation", pct=f"{result.difference_pct:.1f}")
    rows = [
        (tr("pdf_cmp_file"), project.comparison_file or "-"),
        (tr("pdf_cmp_points"), result.points_compared),
        (tr("pdf_cmp_compared_avg"), round(result.compared_avg, 1)),
        (tr("pdf_cmp_current_avg"), round(result.current_avg, 1)),
        (tr("pdf_cmp_difference"), f"{result.difference_lux:+.1f} lx ({result.difference_pct:+.1f}%)"),
        (tr("pdf_cmp_depreciation"), depreciation),
    ]
    for label, value in rows:
        sheet.append([label.rstrip(":"), value])
    sheet.append([])
    sheet.append([tr("xl_compared_values")])
    layout = grid_layout(project)
    for r in range(layout.rows):
        row = []
        for c in range(layout.cols):
            point = layout.cells.get((r, c))
            row.append(None if point is None or point.expected_lux is None else round(point.expected_lux, 3))
        sheet.append(row)
    sheet.column_dimensions["A"].width = 34
    sheet.column_dimensions["B"].width = 28


def write_table(project: LuminationProject, path: str) -> List[MeasurementPoint]:
    """Save the readings as a grid table (CSV or Excel by extension).

    Returns the points added by hand that do not fit the grid (not written).
    """
    grid, extra = project_to_grid(project)
    if path.lower().endswith(EXCEL_SUFFIXES):
        from openpyxl import Workbook

        workbook = Workbook()
        sheet = workbook.active
        sheet.title = tr("xl_sheet_measurements")[:31]
        for r, row in enumerate(grid, start=1):
            for c, value in enumerate(row, start=1):
                if value is not None:
                    sheet.cell(row=r, column=c, value=round(value, 3))
        _add_comparison_sheet(workbook, project)
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        workbook.save(path)
    else:
        # UTF-8 with a byte order mark so Excel shows any non-English text correctly; plain text otherwise.
        with open(path, "w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.writer(handle)
            for row in grid:
                writer.writerow(["" if value is None else _format_number(value) for value in row])
    return extra
