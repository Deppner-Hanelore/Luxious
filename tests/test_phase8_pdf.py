"""Phase 8: the PDF report has no long dashes and only the sections that apply."""

import pytest

from models.project import LuminationProject
from models.room import Room
from persistence.table_io import grid_layout
from reporting.pdf_report import clean_text, generate_pdf_report

LONG_DASHES = "—–‒―−"


def _project(target=None, compared=False):
    project = LuminationProject(name="Office — floor 2 – east", room=Room(length=6.0, width=4.0, wall_margin=0.5),
                                author="Ana — lighting", target_lux=target)
    project.regenerate_grid(rows=2, cols=3, wall_margin=0.5)
    for index, point in enumerate(sorted(grid_layout(project).cells.items())):
        point[1].record_reading(380.0 + 15 * index)
        point[1].notes = "near window – west side"
        if compared:
            point[1].expected_lux = 450.0
    if compared:
        project.comparison_file = "older — 2024.xlsx"
        project.visualization_settings.display_mode = "difference"  # negative values on the map
    return project


def test_clean_text_replaces_every_long_dash():
    assert clean_text("a—b–c‒d―e−f") == "a-b-c-d-e-f"


@pytest.mark.parametrize("lang", ["en", "ro", "de"])
def test_report_text_has_no_long_dashes(tmp_path, lang):
    fitz = pytest.importorskip("fitz")
    path = tmp_path / f"{lang}.pdf"
    generate_pdf_report(_project(target=500, compared=True), str(path), lang=lang)
    text = "".join(page.get_text() for page in fitz.open(str(path)))
    assert text.strip()
    assert not any(dash in text for dash in LONG_DASHES)
    assert "Office - floor 2 - east" in text


def test_sections_appear_only_when_they_apply(tmp_path):
    fitz = pytest.importorskip("fitz")

    def text(project):
        path = tmp_path / "r.pdf"
        generate_pdf_report(project, str(path), lang="en")
        return " ".join("".join(page.get_text() for page in fitz.open(str(path))).split()).lower()

    plain = text(_project())
    assert "comparison with selected target illuminance" not in plain
    assert "comparison with another file" not in plain
    assert "ceiling height" not in plain and "working plane height" not in plain
    assert "distance from walls" in plain
    full = text(_project(target=500, compared=True))
    assert "comparison with selected target illuminance" in full
    assert "comparison with another file" in full


@pytest.mark.parametrize("lang, words", [
    ("en", ["Illuminance survey report", "Page 1 of", "Depreciation of the light"]),
    ("ro", ["Raport de măsurare a iluminării", "Pagina 1 din", "Deprecierea iluminării"]),
    ("de", ["Bericht zur Beleuchtungsmessung", "Seite 1 von", "Rückgang der Beleuchtung"]),
])
def test_report_layout_follows_the_selected_language(tmp_path, lang, words):
    fitz = pytest.importorskip("fitz")
    path = tmp_path / f"{lang}.pdf"
    generate_pdf_report(_project(target=500, compared=True), str(path), lang=lang)
    text = " ".join("".join(page.get_text() for page in fitz.open(str(path))).split()).lower()
    for word in words:
        assert word.lower() in text, word
