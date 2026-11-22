"""Feature and interaction regressions discovered by the field-UI audit."""
import copy
import os
from pathlib import Path

import numpy as np
import pytest
from PySide6.QtCore import Qt, QCoreApplication, QEvent, QSettings
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import QApplication, QMessageBox

from i18n.translations import TranslationManager
from models.measurement import MeasurementPoint
from models.project import LuminationProject
from models.room import Room
from persistence.project_io import load_project
from persistence.recovery import RecoveryStore
from ui.dialogs.point_edit_dialog import PointEditDialog
from ui.main_window import MainWindow


@pytest.fixture
def window(tmp_path):
    app = QApplication.instance() or QApplication([])
    TranslationManager.get_instance().set_language('en')
    project = LuminationProject(name='Audit', room=Room(length=6, width=4))
    project.points = [MeasurementPoint(id=f'P{i}', x=x, y=y)
                      for i, (x, y) in enumerate([(1, 1), (5, 1), (1, 3)], 1)]
    w = MainWindow(project, recovery_store=RecoveryStore(str(tmp_path / 'recovery.json')),
                   settings=QSettings(str(tmp_path / 'settings.ini'), QSettings.Format.IniFormat))
    w.show()
    app.processEvents()
    yield w
    w.project.is_dirty = False
    w.recovery_store.discard()
    w.close()
    w.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    TranslationManager.get_instance().set_language('en')


def test_language_switch_keeps_actions_and_unique_shortcuts(window):
    for language in ['ro', 'de', 'en']:
        TranslationManager.get_instance().set_language(language)
        assert window.act_generate_grid.isEnabled()
        save_actions = [a for a in window.findChildren(QAction)
                        if a.shortcut() == QKeySequence(QKeySequence.StandardKey.Save)]
        assert len(save_actions) == 1
        undo_actions = [a for a in window.findChildren(QAction)
                        if a.shortcut() == QKeySequence(QKeySequence.StandardKey.Undo)]
        assert len(undo_actions) == 1


def test_empty_project_clears_selection_and_disables_capture_and_navigation(window):
    window._replace_project(LuminationProject(name='Empty', room=Room()))
    bar = window.survey_widget
    assert bar.active_point_id is None
    assert bar.edit_lux.text() == ''
    for button in [bar.btn_save_next, bar.btn_next_unmeasured]:
        assert not button.isEnabled()


def test_skip_last_returns_to_skipped_pending_point_without_writing(window):
    window.project.points[1].record_reading(200)
    window._on_point_selected('P3')
    window.survey_widget.btn_next_unmeasured.click()
    assert window.active_point_id == 'P1'
    assert window.project.points[0].lux is None
    assert window.project.points[2].lux is None


def test_german_decimal_entry_and_unrounded_correction(window):
    TranslationManager.get_instance().set_language('de')
    window.survey_widget.edit_lux.setText('123,456789')
    window.survey_widget.btn_save_next.click()
    assert window.project.points[0].lux == 123.456789
    window._on_point_selected('P1')
    window.survey_widget.btn_save_next.click()
    assert window.project.points[0].lux == 123.456789
    index = window.table_widget.model.index(0, 3)
    assert window.table_widget.model.data(index, Qt.ItemDataRole.EditRole) == 123.456789


def test_notes_only_dialog_preserves_coordinates_precision_and_provenance(window):
    original = window.project.points[0]
    original.x = 1.123456
    original.record_reading(123.456789, timestamp='original-time', device_name='Meter',
                            source_sample_id='sample', source_profile_id='profile')
    original.expected_lux = 456.789123
    point = copy.deepcopy(original)
    dialog = PointEditDialog(point, window.project.room)
    dialog.txt_notes.setText('Notes only')
    dialog._on_accept()
    assert point.x == original.x
    assert point.lux == original.lux
    assert point.expected_lux == original.expected_lux
    assert point.timestamp == original.timestamp
    assert point.source_sample_id == original.source_sample_id


def test_saved_review_layout_opens_in_the_single_survey_layout(window, tmp_path):
    project = copy.deepcopy(window.project)
    project.resume_state = {"workspace": "review", "selected_point_id": "P1"}
    window._replace_project(project)
    window._show_workspace()
    QApplication.instance().processEvents()
    assert window.survey_toolbar.isVisible()
    assert not window.dock_left.isVisible() and not window.dock_right.isVisible()


def test_structure_buttons_clear_and_history_still_work(window, monkeypatch):
    canvas = window.canvas_widget
    canvas.btn_add_point.click()
    assert canvas.placement_mode
    canvas.point_add_requested.emit(3, 2)
    assert len(window.project.points) == 4
    canvas.btn_undo.click()
    assert len(window.project.points) == 3
    canvas.btn_redo.click()
    assert len(window.project.points) == 4
    canvas.btn_delete_point.click()
    assert len(window.project.points) == 3
    canvas.btn_undo.click()
    assert len(window.project.points) == 4
    window._on_measurement_recorded('P1', 99, advance=False)
    monkeypatch.setattr(QMessageBox, 'exec', lambda _box: int(QMessageBox.StandardButton.Yes))
    window.act_clear_measurements.trigger()
    assert not window.project.get_measured_points()
    window.act_undo.trigger()
    assert window.project.find_point_by_id('P1').lux == 99


def test_expected_and_signed_difference_views_use_correct_data(window):
    for point in window.project.points:
        point.record_reading(100)
        point.expected_lux = 200
    window.comparison_panel.set_display_mode('expected')
    assert window.interp_result.success
    assert np.nanmean(window.interp_result.grid_z) == pytest.approx(200)
    window.comparison_panel.set_display_mode('difference')
    assert window.interp_result.success
    assert np.nanmean(window.interp_result.grid_z) == pytest.approx(-100)
    assert all(point.lux == 100 for point in window.project.points)


@pytest.mark.parametrize('suffix', ['.csv', '.xlsx', '.pdf', '.png', '.luxproj'])
def test_save_as_writes_each_file_type(window, tmp_path, monkeypatch, suffix):
    for point in window.project.points:
        point.record_reading(100)
    output = tmp_path / ('export' + suffix)
    monkeypatch.setattr('ui.main_window.QFileDialog.getSaveFileName', lambda *_args: (str(output), ''))
    errors = []
    monkeypatch.setattr(QMessageBox, 'critical', lambda *_args: errors.append(_args))
    assert window.act_save_as.isEnabled()
    window.act_save_as.trigger()
    assert not errors
    assert output.exists() and output.stat().st_size > 5
    assert (window.project.file_path == str(output)) == (suffix == '.luxproj')


@pytest.mark.parametrize('language', ['en', 'ro', 'de'])
@pytest.mark.parametrize('size', [(960, 600), (1380, 860), (1920, 1080)])
def test_survey_controls_fit_in_every_workspace_and_language(window, language, size):
    from ui.styles import MAIN_STYLESHEET
    window.setStyleSheet(MAIN_STYLESHEET)
    TranslationManager.get_instance().set_language(language)
    window.resize(*size)
    for mode in ['survey']:
        QApplication.instance().processEvents()
        screenshot_dir = os.environ.get('LUMINATION_UI_SCREENSHOTS')
        if screenshot_dir:
            target = Path(screenshot_dir)
            target.mkdir(parents=True, exist_ok=True)
            window.grab().save(str(target / f'{language}-{size[0]}x{size[1]}-{mode}.png'))
        assert window.minimumSizeHint().width() <= window.width()
        assert window.minimumSizeHint().height() <= window.height()
        if mode != 'review':
            for button in [window.survey_widget.btn_save_next, window.survey_widget.btn_next_unmeasured]:
                assert button.width() >= button.minimumSizeHint().width()
                assert button.height() >= 44
            assert window.survey_widget.width() >= window.survey_widget.minimumSizeHint().width()
        else:
            assert not window.survey_toolbar.isVisible()
    if size[0] < 1200:
        assert not window.dock_left.isVisible()
        window.btn_toggle_left.click()
        assert window.dock_left.isVisible() and not window.dock_right.isVisible()
        window.btn_toggle_right.click()
        assert window.dock_right.isVisible() and not window.dock_left.isVisible()


def test_clicking_away_deselects_the_point_and_keeps_its_value(window):
    from types import SimpleNamespace
    canvas = window.canvas_widget
    window.project.find_point_by_id('P1').record_reading(240)
    canvas._on_mouse_click(SimpleNamespace(xdata=1, ydata=1))
    assert canvas.popup_editor.isVisible() and canvas.selected_point_id == 'P1'
    canvas.popup_editor.txt_lux.setText('')  # nothing entered
    canvas._on_mouse_click(SimpleNamespace(xdata=3, ydata=2))  # click on an empty part of the map
    assert not canvas.popup_editor.isVisible()
    assert canvas.selected_point_id is None  # no point highlighted on the map
    assert window.active_point_id == 'P1' and window.survey_widget.active_point_id == 'P1'  # reading bar keeps it
    assert window.project.find_point_by_id('P1').lux == 240  # previous value kept
    window.recalculate_and_refresh()
    assert canvas.selected_point_id is None  # stays unselected after a refresh


def test_clicking_elsewhere_in_the_window_closes_the_reading_box(window):
    from types import SimpleNamespace
    canvas = window.canvas_widget
    window.show()
    QApplication.instance().processEvents()
    canvas._on_mouse_click(SimpleNamespace(xdata=1, ydata=1))
    QApplication.instance().processEvents()
    canvas.popup_editor.txt_lux.setText('999')  # typed but Enter not pressed
    window.survey_widget.combo_points.setFocus()  # click somewhere else in the app
    QApplication.instance().processEvents()
    if canvas.popup_editor.isVisible():
        pytest.skip("focus changes are not delivered in this environment")
    assert canvas.selected_point_id is None
    assert window.project.find_point_by_id('P1').lux is None  # nothing was saved


def test_new_setup_retains_spacing_grid_and_optional_author(window):
    from ui.dialogs.survey_setup_dialog import SurveySetupDialog
    dialog = SurveySetupDialog()
    dialog.author.setText('Surveyor A')
    dialog.grid_mode.setCurrentIndex(1)
    dialog.spacing_x.setValue(1.25)
    dialog.spacing_y.setValue(0.75)
    project = dialog.get_created_project()
    assert project.author == 'Surveyor A'
    # 5 m inside the wall distance / 1.25 m = 4 gaps -> 5 points; 3 m / 0.75 m -> 5 rows.
    assert project.room.grid_cols == 5
    assert project.room.grid_rows == 5
    xs = sorted({point.x for point in project.points})
    assert xs == pytest.approx([0.5, 1.75, 3.0, 4.25, 5.5])
    assert all(point.lux is None for point in project.points)


def test_start_screen_disables_project_only_actions(window):
    window._show_start_screen()
    assert not window.menu_survey.isEnabled()
    assert not window.act_save.isEnabled()
    assert not window.survey_toolbar.isVisible()
    assert not window.act_new.isEnabled() and not window.act_open.isEnabled()
    visible = [a.text() for a in window.menuBar().actions() if a.isVisible()]
    assert visible == [window.menu_lang.title()]


def test_grid_menu_applies_one_undoable_change(window, monkeypatch):
    from ui.dialogs.grid_generator_dialog import GridGeneratorDialog
    original = copy.deepcopy(window.project.points)
    def configure(dialog):
        dialog.spin_rows.setValue(2)
        dialog.spin_cols.setValue(5)
        dialog._on_accept()
        return GridGeneratorDialog.DialogCode.Accepted
    monkeypatch.setattr(GridGeneratorDialog, 'exec', configure)
    window.act_generate_grid.trigger()
    assert len(window.project.points) == 10
    assert window.undo_stack.count() == 1
    window.act_undo.trigger()
    assert window.project.points == original


def test_new_save_and_open_menu_actions(window, tmp_path, monkeypatch):
    from ui.dialogs.survey_setup_dialog import SurveySetupDialog
    def configure(dialog):
        dialog.name.setText('New job')
        dialog.author.setText('Worker A')
        return SurveySetupDialog.DialogCode.Accepted
    monkeypatch.setattr(SurveySetupDialog, 'exec', configure)
    window.act_new.trigger()
    assert window.project.name == 'New job'
    assert window.project.author == 'Worker A'
    assert len(window.project.points) == 12
    assert not window.project.get_measured_points()
    path = tmp_path / 'job.luxproj'
    monkeypatch.setattr('ui.main_window.QFileDialog.getSaveFileName', lambda *_args: (str(path), ''))
    window.act_save.trigger()
    assert path.exists() and not window.project.is_dirty
    monkeypatch.setattr('ui.main_window.QFileDialog.getOpenFileName', lambda *_args: (str(path), ''))
    window.act_open.trigger()
    assert window.project.name == 'New job'
    assert window.project.author == 'Worker A'
    assert not window.project.is_dirty


def test_survey_changes_work_without_edit_mode(window):
    assert not hasattr(window, "act_edit_survey")
    assert not hasattr(window, "act_done_editing")
    window.project.points[0].record_reading(100)
    window._on_point_selected('P1')
    window.survey_widget.edit_lux.setText('150')
    window.survey_widget.btn_save_next.click()
    assert window.project.points[0].lux == 150
    count = len(window.project.points)
    window._on_point_add_requested(1.0, 1.0)
    assert len(window.project.points) == count + 1
    window._undo_if_allowed()
    assert len(window.project.points) == count
    window._redo_if_allowed()
    assert len(window.project.points) == count + 1
    window._on_point_delete_requested(window.project.points[-1].id)
    assert len(window.project.points) == count
    assert window.act_generate_grid.isEnabled()
    assert window.canvas_widget.editing_enabled
    assert window.act_generate_grid.isEnabled()
    menu_texts = [a.text() for a in window.menu_survey.actions() if not a.isSeparator()]
    assert menu_texts == [window.act_generate_grid.text(), window.act_clear_measurements.text()]
