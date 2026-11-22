"""Checks that the features removed in Phase 1 stay removed."""

import importlib.util

import matplotlib

matplotlib.use("Agg")
from matplotlib.figure import Figure
from matplotlib.patches import Rectangle

from models.project import LuminationProject
from models.room import Room
from ui.main_window import MainWindow


def _window(tmp_path):
    room = Room(length=6.0, width=4.0, wall_margin=0.5)
    project = LuminationProject(name="Phase 1", room=room)
    project.regenerate_grid(rows=2, cols=3, wall_margin=0.5)
    window = MainWindow(project)
    window.recovery_store.path = str(tmp_path / "recovery.json")
    return window


def _close(window):
    window.project.is_dirty = False
    window.recovery_store.discard()
    window.close()


def test_bluetooth_and_usb_code_is_gone(qapp, tmp_path):
    assert importlib.util.find_spec("measurement_sources") is None
    assert importlib.util.find_spec("ui.dialogs.hardware_connection_dialog") is None
    window = _window(tmp_path)
    assert not hasattr(window, "usb_source") and not hasattr(window, "bt_source")
    assert not hasattr(window.canvas_widget, "btn_hardware")
    _close(window)


def test_menu_bar_has_no_devices_or_csv_export_menu(qapp, tmp_path):
    window = _window(tmp_path)
    titles = [action.text().replace("&", "") for action in window.menuBar().actions()]
    assert "Devices" not in titles
    assert not any("Export" in title for title in titles)
    assert not hasattr(window, "act_export_img")
    assert not hasattr(window, "_on_export_image")
    _close(window)


def test_survey_bar_has_no_prev_or_skip_buttons(qapp, tmp_path):
    window = _window(tmp_path)
    bar = window.survey_widget
    assert not hasattr(bar, "btn_prev") and not hasattr(bar, "btn_next")
    assert bar.btn_next_unmeasured is not None
    _close(window)


def test_new_survey_window_has_no_height_fields(qapp):
    from ui.dialogs.survey_setup_dialog import SurveySetupDialog

    dialog = SurveySetupDialog()
    assert not hasattr(dialog, "height") or callable(dialog.height)
    assert not hasattr(dialog, "plane")
    project = dialog._build_project()
    assert project.room.length == dialog.length.value()
    dialog.deleteLater()


def test_map_has_no_dashed_wall_distance_line_or_switch(qapp, tmp_path):
    from visualization.map_plotter import render_room_map

    window = _window(tmp_path)
    assert not hasattr(window.layer_widget, "chk_margins")
    ax = Figure().add_subplot()
    render_room_map(ax, window.project)
    dashed = [
        patch for patch in ax.patches
        if isinstance(patch, Rectangle) and patch.get_linestyle() not in ("-", "solid")
    ]
    assert dashed == []
    _close(window)
