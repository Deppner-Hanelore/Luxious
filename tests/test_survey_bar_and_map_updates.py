"""Menu without modes, Ctrl+Z/Ctrl+Y, compact reading bar, colour bar and PNG export."""

import pytest
from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QImage
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from models.project import LuminationProject
from models.room import Room


def _window(tmp_path, measured=True):
    from persistence.recovery import RecoveryStore
    from ui.main_window import MainWindow

    project = LuminationProject(name="Updates", room=Room(length=6.0, width=4.0, wall_margin=0.5))
    project.regenerate_grid(rows=3, cols=4, wall_margin=0.5)
    if measured:
        for index, point in enumerate(project.points):
            point.record_reading(300.0 + 20 * index)
    window = MainWindow(project, recovery_store=RecoveryStore(str(tmp_path / "r.json")),
                        settings=QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat))
    window.resize(1300, 850)
    window.show()
    QApplication.processEvents()
    return window


def _close(window):
    window.project.is_dirty = False
    window.close()


def test_survey_menu_has_no_modes_or_undo_and_panels_start_closed(qapp, tmp_path):
    window = _window(tmp_path)
    texts = [a.text() for a in window.menu_survey.actions() if not a.isSeparator()]
    assert texts == [window.act_generate_grid.text(), window.act_clear_measurements.text()]
    assert not hasattr(window, "act_enter_review") and not hasattr(window, "act_enter_survey")
    assert window.survey_toolbar.isVisible()
    assert not window.dock_left.isVisible() and not window.dock_right.isVisible()
    _close(window)


def test_ctrl_z_and_ctrl_y_still_work_without_menu_entries(qapp, tmp_path):
    window = _window(tmp_path)
    count = len(window.project.points)
    window._on_point_add_requested(1.0, 1.0)
    assert len(window.project.points) == count + 1
    window.activateWindow()
    window.canvas_widget.setFocus()
    QTest.keyClick(window, Qt.Key.Key_Z, Qt.KeyboardModifier.ControlModifier)
    assert len(window.project.points) == count
    QTest.keyClick(window, Qt.Key.Key_Y, Qt.KeyboardModifier.ControlModifier)
    assert len(window.project.points) == count + 1
    _close(window)


def test_reading_field_is_compact_with_both_buttons_on_its_line(qapp, tmp_path):
    window = _window(tmp_path)
    bar = window.survey_widget
    assert bar.edit_lux.width() <= 150
    field_row = bar.edit_lux.geometry().center().y()
    for button in (bar.btn_save_next, bar.btn_next_unmeasured):
        assert abs(button.geometry().center().y() - field_row) <= 4
        assert button.geometry().left() > bar.edit_lux.geometry().right()
    assert bar.btn_next_unmeasured.geometry().left() > bar.btn_save_next.geometry().right()
    _close(window)


def test_colour_bar_only_on_the_main_map(qapp, tmp_path):
    window = _window(tmp_path)
    cax = window.canvas_widget.cax
    assert cax is not None and cax.get_visible()
    assert cax.get_ylabel() == "Illuminance (lx)"
    window.open_graph_window()
    assert window.graph_window.canvas_widget.cax is None
    window.graph_window.close()
    _close(window)
    empty = _window(tmp_path, measured=False)
    assert not empty.canvas_widget.cax.get_visible()  # nothing to explain yet
    _close(empty)


def test_png_is_the_map_as_zoomed_on_screen_with_colour_bar(qapp, tmp_path, monkeypatch):
    window = _window(tmp_path)
    full = tmp_path / "full.png"
    zoomed = tmp_path / "zoomed.png"
    for path, zoom in ((full, None), (zoomed, 3.0)):
        if zoom:
            window.canvas_widget.zoom_at(1.0, 1.0, zoom)
        monkeypatch.setattr("ui.main_window.QFileDialog.getSaveFileName", lambda *_a, p=path: (str(p), ""))
        window.act_save_as.trigger()
        assert path.exists() and QImage(str(path)).width() > 500
    assert full.read_bytes() != zoomed.read_bytes()
    assert window.project.file_path is None  # an image, not the project file
    _close(window)
