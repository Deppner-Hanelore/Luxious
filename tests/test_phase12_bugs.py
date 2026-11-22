"""Phase 12: regression checks for the bugs fixed in this phase."""

from types import SimpleNamespace

import pytest
from matplotlib.figure import Figure
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication, QGroupBox

from models.project import LuminationProject
from models.room import Room
from persistence.project_io import save_project
from visualization.map_plotter import render_room_map


def _project():
    project = LuminationProject(name="Bugs", room=Room(length=6.0, width=4.0, wall_margin=0.5))
    project.regenerate_grid(rows=2, cols=3, wall_margin=0.5)
    for index, point in enumerate(project.points):
        point.record_reading(400.0 + 10 * index)
    return project


def _window(tmp_path, project=None):
    from persistence.recovery import RecoveryStore
    from ui.main_window import MainWindow

    window = MainWindow(project or _project(), recovery_store=RecoveryStore(str(tmp_path / "r.json")),
                        settings=QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat))
    window.resize(1200, 800)
    window.show()
    QApplication.processEvents()
    return window


def test_permanent_lux_labels_switch_draws_the_values():
    project = _project()
    for shown in (True, False):
        project.visualization_settings.show_values = shown
        ax = Figure().add_subplot()
        render_room_map(ax, project)
        labels = [t.get_text() for t in ax.texts if t.get_text().isdigit()]
        assert sorted(labels) == (sorted(f"{p.lux:.0f}" for p in project.points) if shown else [])


def test_reading_box_opens_right_above_the_point(qapp, tmp_path):
    window = _window(tmp_path)
    canvas = window.canvas_widget
    point = window.project.points[4]
    canvas._on_mouse_click(SimpleNamespace(xdata=point.x, ydata=point.y))
    target = canvas._data_to_widget(point.x, point.y)
    box = canvas.popup_editor.geometry()
    assert canvas.popup_editor.isVisible()
    assert abs(box.center().x() - target.x()) <= 2
    assert 0 <= target.y() - box.bottom() <= 12
    window.project.is_dirty = False
    window.close()


def test_points_are_hit_by_screen_distance_at_any_zoom(qapp, tmp_path):
    window = _window(tmp_path)
    canvas = window.canvas_widget
    point = window.project.points[0]
    canvas.zoom_at(point.x, point.y, 0.2)  # far out: 0.2 m is only a few pixels now
    near = canvas.ax.transData.inverted().transform(canvas.ax.transData.transform((point.x, point.y)) + (6, 0))
    assert canvas._find_nearest_point(*near) is point
    canvas.reset_view()
    canvas.zoom_at(point.x, point.y, 20)  # far in: 0.15 m is many pixels away now
    assert canvas._find_nearest_point(point.x + 0.15, point.y) is None
    window.project.is_dirty = False
    window.close()


def test_undoing_a_comparison_returns_the_map_to_your_survey(qapp, tmp_path, monkeypatch):
    other = _project()
    path = str(tmp_path / "other.luxproj")
    save_project(other, path)
    window = _window(tmp_path)
    monkeypatch.setattr("ui.main_window.QFileDialog.getOpenFileName", lambda *_a: (path, ""))
    panel = window.comparison_panel
    panel.btn_compare.click()
    panel.rb_expected.click()
    assert window.project.visualization_settings.display_mode == "expected"
    window._undo_if_allowed()
    assert window.project.visualization_settings.display_mode == "measured"
    assert panel.rb_measured.isChecked() and not panel.rb_expected.isEnabled()
    window.project.is_dirty = False
    window.close()


def test_ampersands_stay_visible_in_buttons_and_titles(qapp, tmp_path):
    from ui.dialogs.grid_generator_dialog import GridGeneratorDialog

    window = _window(tmp_path)
    assert window.survey_widget.btn_save_next.text().startswith("Record && next")
    dialog = GridGeneratorDialog(window.project, window)
    titles = [box.title() for box in dialog.findChildren(QGroupBox)]
    assert any("&&" in title for title in titles)
    dialog.deleteLater()
    window.project.is_dirty = False
    window.close()


def test_map_toolbar_has_no_empty_box_around_the_position_label(qapp, tmp_path):
    window = _window(tmp_path)
    style = window.canvas_widget.action_bar.styleSheet()
    assert "QFrame#mapActionBar" in style and "\n            QFrame {" not in style
    window.project.is_dirty = False
    window.close()
