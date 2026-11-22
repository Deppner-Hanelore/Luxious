"""Phase 7: compare a survey with a Luxious project, Excel or CSV file of the same grid."""

import pytest
from PySide6.QtCore import QSettings

from analysis.comparison import compare_with_file
from models.project import LuminationProject
from models.room import Room
from persistence.comparison_io import apply_comparison
from persistence.project_io import save_project
from persistence.table_io import TableError, grid_layout, write_table


def _project(values, rows=2, cols=3, name="Room A"):
    project = LuminationProject(name=name, room=Room(length=6.0, width=4.0, wall_margin=0.5))
    project.regenerate_grid(rows=rows, cols=cols, wall_margin=0.5)
    cells = grid_layout(project).cells
    for (r, c), value in zip(sorted(cells), values):
        if value is not None:
            cells[(r, c)].record_reading(value)
    return project


def test_depreciation_is_measured_against_the_compared_file():
    survey = _project([400, 400, 400, 400, 400, 400])
    for point in survey.points:
        point.expected_lux = 500.0
    result = compare_with_file(survey.points)
    assert result.points_compared == 6
    assert (result.compared_avg, result.current_avg) == (500.0, 400.0)
    assert result.difference_lux == pytest.approx(-100.0)
    assert result.has_depreciation and result.depreciation_pct == pytest.approx(20.0)


def test_no_depreciation_when_survey_is_brighter_and_no_values_are_invented():
    survey = _project([600, 600, None, None, None, None])
    survey.points[0].expected_lux = 500.0
    survey.points[1].expected_lux = 500.0
    survey.points[2].expected_lux = 500.0  # no reading here: not used
    result = compare_with_file(survey.points)
    assert result.points_compared == 2
    assert not result.has_depreciation and result.depreciation_pct == 0.0
    assert result.difference_pct == pytest.approx(20.0)
    assert compare_with_file(_project([400] * 6).points) is None


@pytest.mark.parametrize("suffix", [".luxproj", ".xlsx", ".csv"])
def test_compare_with_each_file_type_matches_by_grid_position(tmp_path, suffix):
    other = _project([500, 510, 520, 530, 540, 550], name="Older")
    path = str(tmp_path / f"older{suffix}")
    if suffix == ".luxproj":
        save_project(other, path)
    else:
        write_table(other, path)
    survey = _project([400, 410, 420, 430, 440, 450])
    assert apply_comparison(survey, path) == 6
    cells = grid_layout(survey).cells
    assert cells[(0, 0)].expected_lux == 500 and cells[(1, 2)].expected_lux == 550
    assert survey.comparison_file == f"older{suffix}"


def test_different_grid_size_is_refused_with_both_sizes(tmp_path):
    other = _project([500] * 8, rows=2, cols=4)
    path = str(tmp_path / "other.luxproj")
    save_project(other, path)
    with pytest.raises(TableError, match="2 rows and 4 columns.*2 rows and 3 columns"):
        apply_comparison(_project([400] * 6), path)


def test_pdf_and_excel_include_comparison_only_when_made(tmp_path):
    from openpyxl import load_workbook
    from reporting.pdf_report import generate_pdf_report

    plain = _project([400] * 6)
    write_table(plain, str(tmp_path / "plain.xlsx"))
    assert load_workbook(str(tmp_path / "plain.xlsx")).sheetnames == ["Measurements"]
    generate_pdf_report(plain, str(tmp_path / "plain.pdf"), lang="en")

    compared = _project([400] * 6)
    for point in compared.points:
        point.expected_lux = 500.0
    compared.comparison_file = "older.xlsx"
    write_table(compared, str(tmp_path / "cmp.xlsx"))
    book = load_workbook(str(tmp_path / "cmp.xlsx"))
    assert book.sheetnames == ["Measurements", "Comparison"]
    assert book["Comparison"]["B1"].value == "older.xlsx"
    generate_pdf_report(compared, str(tmp_path / "cmp.pdf"), lang="en")

    fitz = pytest.importorskip("fitz")  # PyMuPDF reads the PDF text when it is installed
    plain_text = "".join(page.get_text() for page in fitz.open(str(tmp_path / "plain.pdf")))
    cmp_text = "".join(page.get_text() for page in fitz.open(str(tmp_path / "cmp.pdf")))
    plain_text, cmp_text = plain_text.lower(), " ".join(cmp_text.split()).lower()
    assert "depreciation" not in plain_text and "compared" not in plain_text
    assert "depreciation of the light" in cmp_text and "20.0" in cmp_text


def test_compare_button_loads_file_and_undo_restores(qapp, tmp_path, monkeypatch):
    from persistence.recovery import RecoveryStore
    from ui.main_window import MainWindow

    other = _project([500] * 6)
    path = str(tmp_path / "older.luxproj")
    save_project(other, path)
    window = MainWindow(_project([400] * 6), recovery_store=RecoveryStore(str(tmp_path / "r.json")),
                        settings=QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat))
    panel = window.comparison_panel
    assert not panel.rb_expected.isEnabled()
    monkeypatch.setattr("ui.main_window.QFileDialog.getOpenFileName", lambda *_a: (path, ""))
    panel.btn_compare.click()
    assert panel.rb_expected.isEnabled()
    assert "older.luxproj" in panel.lbl_file.text()
    assert "20.0%" in panel.lbl_depreciation.text()
    window._undo_if_allowed()
    assert all(p.expected_lux is None for p in window.project.points)
    assert window.project.comparison_file is None
    window.project.is_dirty = False
    window.close()
