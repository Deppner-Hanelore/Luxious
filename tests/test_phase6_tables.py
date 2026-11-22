"""Phase 6: Excel and CSV grid tables (A1 = top-left point)."""

import pytest
from PySide6.QtCore import QSettings

from models.project import LuminationProject
from models.room import Room
from persistence.table_io import (
    TableError,
    apply_table_to_project,
    cell_name,
    grid_layout,
    project_from_table,
    read_table,
    room_size_for_table,
    write_table,
)


def _project(rows=2, cols=3):
    project = LuminationProject(name="Tables", room=Room(length=6.0, width=4.0, wall_margin=0.5))
    project.regenerate_grid(rows=rows, cols=cols, wall_margin=0.5)
    return project


def _cell(project, row, col):
    return grid_layout(project).cells[(row, col)]


def test_cell_names():
    assert [cell_name(0, 0), cell_name(0, 1), cell_name(3, 2), cell_name(0, 26)] == ["A1", "B1", "C4", "AA1"]


@pytest.mark.parametrize("suffix", [".csv", ".xlsx"])
def test_round_trip_keeps_layout_and_empty_cells(tmp_path, suffix):
    project = _project()
    _cell(project, 0, 0).record_reading(410)
    _cell(project, 0, 2).record_reading(395.5)
    _cell(project, 1, 1).record_reading(0)
    path = str(tmp_path / f"t{suffix}")
    assert write_table(project, path) == []
    values = read_table(path)
    assert values == [[410, None, 395.5], [None, 0, None]][: len(values)] or values == [[410, None, 395.5], [None, 0]]
    fresh = _project()
    assert apply_table_to_project(fresh, values) == 3
    assert _cell(fresh, 0, 0).lux == 410 and _cell(fresh, 0, 2).lux == 395.5 and _cell(fresh, 1, 1).lux == 0
    assert _cell(fresh, 1, 0).lux is None


def test_csv_is_plain_text_with_bom_and_commas(tmp_path):
    project = _project(1, 3)
    for col, lux in enumerate((410.0, 420.25, 433.1)):
        _cell(project, 0, col).record_reading(lux)
    path = tmp_path / "plain.csv"
    write_table(project, str(path))
    raw = path.read_bytes()
    assert raw.startswith(b"\xef\xbb\xbf")
    assert raw[3:].decode("utf-8").strip() == "410,420.25,433.1"


def test_decimal_comma_and_semicolons_are_read(tmp_path):
    path = tmp_path / "de.csv"
    path.write_text("412,5;400\n;380,25\n", encoding="utf-8")
    assert read_table(str(path)) == [[412.5, 400.0], [None, 380.25]]


def test_text_cell_stops_import_and_names_the_cell(tmp_path):
    path = tmp_path / "bad.csv"
    path.write_text("400,410\n420,lamp\n", encoding="utf-8")
    with pytest.raises(TableError, match="B2"):
        read_table(str(path))
    path.write_text("400,-3\n", encoding="utf-8")
    with pytest.raises(TableError, match="B1"):
        read_table(str(path))


def test_excel_text_cell_is_named(tmp_path):
    from openpyxl import Workbook

    workbook = Workbook()
    workbook.active["A1"] = 400
    workbook.active["C3"] = "n/a"
    path = str(tmp_path / "bad.xlsx")
    workbook.save(path)
    with pytest.raises(TableError, match="C3"):
        read_table(path)


def test_larger_table_than_survey_is_refused(tmp_path):
    path = tmp_path / "big.csv"
    path.write_text("1,2,3,4\n5,6,7,8\n", encoding="utf-8")
    with pytest.raises(TableError, match="2 rows and 4 columns"):
        apply_table_to_project(_project(2, 3), read_table(str(path)))


def test_new_survey_from_table_uses_spacing_and_wall_distance():
    values = [[400, 410, 420, 430], [440, None, 460, 470], [480, 490, 500, 510]]
    project = project_from_table(values, "From table", 1.5, 1.0, 0.5)
    assert room_size_for_table(3, 4, 1.5, 1.0, 0.5) == (5.5, 3.0)
    assert (project.room.length, project.room.width) == (5.5, 3.0)
    assert len(project.points) == 12 and len(project.get_measured_points()) == 11
    top_left = _cell(project, 0, 0)
    assert (top_left.x, top_left.y, top_left.lux) == (0.5, 2.5, 400)
    bottom_right = _cell(project, 2, 3)
    assert (bottom_right.x, bottom_right.y, bottom_right.lux) == (5.0, 0.5, 510)


def test_hand_added_points_are_reported_not_written(tmp_path):
    project = _project()
    extra = project.add_custom_point(3.1, 2.2)
    assert [p.id for p in write_table(project, str(tmp_path / "x.csv"))] == [extra.id]


def test_file_open_builds_survey_from_table(qapp, tmp_path, monkeypatch):
    from persistence.recovery import RecoveryStore
    from ui.dialogs.table_setup_dialog import TableSetupDialog
    from ui.main_window import MainWindow

    path = tmp_path / "office.xlsx"
    project = _project(2, 3)
    for (row, col), point in grid_layout(project).cells.items():
        point.record_reading(300 + 10 * row + col)
    write_table(project, str(path))

    window = MainWindow(recovery_store=RecoveryStore(str(tmp_path / "r.json")),
                        settings=QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat))
    monkeypatch.setattr("ui.main_window.QFileDialog.getOpenFileName", lambda *_a: (str(path), ""))

    def accept(dialog):
        dialog.spacing_x.setValue(2.0)
        dialog.spacing_y.setValue(1.5)
        dialog.margin.setValue(1.0)
        return int(TableSetupDialog.DialogCode.Accepted)

    monkeypatch.setattr(TableSetupDialog, "exec", accept)
    window._on_open_project()
    opened = window.project
    assert opened.name == "office"
    assert (opened.room.length, opened.room.width) == (6.0, 3.5)
    assert _cell(opened, 1, 2).lux == 312
    assert window.content_stack.currentWidget() is window.main_workspace
    window.project.is_dirty = False
    window.close()
