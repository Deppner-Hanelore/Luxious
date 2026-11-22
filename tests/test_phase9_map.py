"""Phase 9: map axes and grid, colour to the walls, zoom tools, center room, Add point + Done, graph window."""

from types import SimpleNamespace

import numpy as np
import pytest
from matplotlib.figure import Figure
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from analysis.interpolation import reconstruct_illuminance_field
from i18n.translations import TranslationManager, tr
from models.project import LuminationProject
from models.room import Room
from visualization.map_plotter import render_room_map


def _project():
    project = LuminationProject(name="Map", room=Room(length=6.5, width=4.0, wall_margin=0.5))
    project.regenerate_grid(rows=3, cols=4, wall_margin=0.5)
    for index, point in enumerate(project.points):
        point.record_reading(300.0 + 25 * index)
    return project


def _grid_lines(ax):
    return [line for line in ax.lines if line.get_zorder() == 6]


def test_axes_start_at_the_walls_and_show_no_negative_numbers():
    ax = Figure().add_subplot()
    render_room_map(ax, _project())
    assert list(ax.xaxis.get_majorticklocs()) == [0, 1, 2, 3, 4, 5, 6, 6.5]
    assert list(ax.yaxis.get_majorticklocs()) == [0, 1, 2, 3, 4]
    formatter = ax.xaxis.get_major_formatter()
    assert formatter(-1.0, 0) == "" and formatter(0.0, 0) == "0"


def test_metric_grid_is_visible_inside_the_room_and_fully_hidden_when_off():
    project = _project()
    ax = Figure().add_subplot()
    render_room_map(ax, project)
    lines = _grid_lines(ax)
    assert len(lines) == 6 + 3  # x = 1..6 and y = 1..3 metres
    for line in lines:
        xs, ys = line.get_xdata(), line.get_ydata()
        assert min(xs) >= 0 and max(xs) <= 6.5 and min(ys) >= 0 and max(ys) <= 4.0
    project.visualization_settings.show_grid = False
    render_room_map(ax, project)
    assert _grid_lines(ax) == []


@pytest.mark.parametrize("method", ["linear", "cubic", "rbf", "nearest"])
def test_colour_reaches_the_walls(method):
    project = _project()
    result = reconstruct_illuminance_field(project.points, project.room, resolution=60,
                                           method=method, extrapolate_to_walls=True)
    assert not np.isnan(result.grid_z).any()


def test_colour_scale_uses_only_real_readings():
    project = _project()
    ax = Figure().add_subplot()
    render_room_map(ax, project)
    mesh = ax.collections[0]
    readings = [p.lux for p in project.points]
    assert mesh.norm.vmin == pytest.approx(min(readings)) and mesh.norm.vmax == pytest.approx(max(readings))


def _canvas(qapp):
    from ui.room_canvas import RoomCanvasWidget

    canvas = RoomCanvasWidget()
    canvas.resize(900, 600)
    canvas.set_editing_enabled(True)
    canvas.set_project(_project())
    canvas.show()
    QApplication.processEvents()
    canvas.reset_view()
    return canvas


def test_zoom_tools_zoom_at_the_clicked_spot_with_their_own_cursor(qapp):
    canvas = _canvas(qapp)
    before = canvas.ax.get_xlim()
    canvas.btn_zoom_in.click()
    assert canvas.active_tool == "zoom_in" and canvas.btn_zoom_in.isChecked()
    assert canvas.canvas.cursor().pixmap().width() > 0  # magnifier cursor
    canvas._on_mouse_click(SimpleNamespace(xdata=1.0, ydata=1.0))
    after = canvas.ax.get_xlim()
    assert (after[1] - after[0]) == pytest.approx((before[1] - before[0]) / 1.5)
    rel_before = (1.0 - before[0]) / (before[1] - before[0])
    rel_after = (1.0 - after[0]) / (after[1] - after[0])
    assert rel_after == pytest.approx(rel_before)  # the clicked spot stays under the cursor
    canvas.btn_zoom_out.click()
    assert canvas.active_tool == "zoom_out" and not canvas.btn_zoom_in.isChecked()
    canvas._on_mouse_click(SimpleNamespace(xdata=1.0, ydata=1.0))
    assert canvas.ax.get_xlim()[1] - canvas.ax.get_xlim()[0] == pytest.approx(before[1] - before[0])
    canvas.btn_zoom_out.click()  # clicking the tool again switches it off
    assert canvas.active_tool is None
    canvas.close()


def test_center_room_shows_the_whole_room_again(qapp):
    canvas = _canvas(qapp)
    canvas.zoom_at(2.0, 2.0, 4.0)
    canvas.btn_center_room.click()
    xlim, ylim = canvas.ax.get_xlim(), canvas.ax.get_ylim()
    assert xlim[0] <= 0 and xlim[1] >= 6.5 and ylim[0] <= 0 and ylim[1] >= 4.0
    canvas.close()


def test_add_point_stays_on_until_done_and_tools_exclude_each_other(qapp):
    canvas = _canvas(qapp)
    added = []
    canvas.point_add_requested.connect(lambda x, y: added.append((x, y)))
    assert not canvas.btn_done.isEnabled()
    canvas.btn_add_point.click()
    assert canvas.placement_mode and canvas.btn_done.isEnabled()
    canvas._on_mouse_click(SimpleNamespace(xdata=2.2, ydata=2.7))
    canvas._on_mouse_click(SimpleNamespace(xdata=4.4, ydata=1.3))
    assert len(added) == 2 and canvas.placement_mode
    canvas.btn_zoom_in.click()
    assert not canvas.placement_mode and not canvas.btn_add_point.isChecked() and not canvas.btn_done.isEnabled()
    canvas.btn_add_point.click()
    canvas.btn_done.click()
    assert not canvas.placement_mode and canvas.active_tool is None and not canvas.btn_done.isEnabled()
    canvas.close()


def test_tool_labels_follow_the_language(qapp):
    canvas = _canvas(qapp)
    TranslationManager.get_instance().set_language("ro", persist=False)
    for button, key in ((canvas.btn_zoom_in, "canvas_tip_zoom_in"), (canvas.btn_zoom_out, "canvas_tip_zoom_out"),
                        (canvas.btn_center_room, "canvas_tip_center_room"), (canvas.btn_fullscreen, "canvas_tip_fullscreen"),
                        (canvas.btn_add_point, "canvas_tip_add_point"), (canvas.btn_done, "canvas_tip_done")):
        assert button.toolTip() == tr(key, "ro")
    assert canvas.btn_done.text() == "Gata"
    assert "(+)" not in tr("canvas_tip_zoom_in", "en")
    canvas.close()


def test_full_screen_opens_large_graph_window_where_readings_work(qapp, tmp_path):
    from persistence.recovery import RecoveryStore
    from ui.main_window import MainWindow

    window = MainWindow(_project(), recovery_store=RecoveryStore(str(tmp_path / "r.json")),
                        settings=QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat))
    window.show()
    QApplication.processEvents()
    window.canvas_widget.btn_fullscreen.click()
    graph = window.graph_window
    assert graph.isVisible() and not window.isFullScreen()
    area = window.screen().availableGeometry()
    assert graph.width() == int(area.width() * 0.8) and graph.height() == int(area.height() * 0.8)
    assert not graph.canvas_widget.btn_fullscreen.isVisible()
    point = window.project.points[0]
    graph.canvas_widget._on_mouse_click(SimpleNamespace(xdata=point.x, ydata=point.y))
    assert graph.canvas_widget.popup_editor.isVisible()
    graph.canvas_widget.measurement_saved.emit(point.id, 777.0)
    assert window.project.find_point_by_id(point.id).lux == 777.0
    assert window.canvas_widget.project is window.project
    graph.canvas_widget.btn_zoom_in.click()
    assert graph.canvas_widget.active_tool == "zoom_in"
    graph.close()
    window.project.is_dirty = False
    window.close()


def test_toolbar_hover_labels_are_the_tool_names(qapp):
    canvas = _canvas(qapp)
    names = {
        canvas.btn_undo: "Undo", canvas.btn_redo: "Redo", canvas.btn_add_point: "Add point",
        canvas.btn_done: "Done", canvas.btn_delete_point: "Delete point", canvas.btn_zoom_in: "Zoom in",
        canvas.btn_zoom_out: "Zoom out", canvas.btn_center_room: "Center room", canvas.btn_fullscreen: "Full screen",
    }
    for button, name in names.items():
        assert button.toolTip() == name
    TranslationManager.get_instance().set_language("de", persist=False)
    assert canvas.btn_zoom_in.toolTip() == "Vergrößern" and canvas.btn_delete_point.toolTip() == "Punkt löschen"
    canvas.close()


def test_toolbar_labels_appear_as_soon_as_the_mouse_enters(qapp):
    from PySide6.QtCore import QPoint, Qt
    from PySide6.QtGui import QCursor
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QToolTip

    canvas = _canvas(qapp)
    canvas.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)  # keep other windows from covering it
    canvas.show()
    canvas.raise_()
    canvas.activateWindow()
    QTest.qWait(100)
    for button in (canvas.btn_zoom_in, canvas.btn_undo):  # an active tool and a greyed-out one
        QToolTip.hideText()
        QCursor.setPos(canvas.mapToGlobal(QPoint(-50, -50)))
        QTest.qWait(50)
        QCursor.setPos(button.mapToGlobal(QPoint(8, 8)))
        QTest.qWait(200)  # Qt's own delay is about 700 ms; the label must already be there
        if QApplication.widgetAt(QCursor.pos()) is not button:
            pytest.skip("the button is not under the mouse here (cursor fixed or another window on top)")
        assert QToolTip.isVisible() and QToolTip.text() == button.toolTip()
    QToolTip.hideText()
    canvas.close()
