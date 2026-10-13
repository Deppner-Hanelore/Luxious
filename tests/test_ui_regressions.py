"""Feature and interaction regressions discovered by the field-UI audit."""
import copy

import numpy as np
import pytest
from PySide6.QtCore import Qt, QCoreApplication, QEvent, QSettings
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import QApplication, QMessageBox

from i18n.translations import TranslationManager
from measurement_sources.device_session import DeviceSession
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


def test_language_switch_preserves_permissions_and_unique_shortcuts(window):
    window.act_enter_review.trigger()
    for language in ['ro', 'de', 'en']:
        TranslationManager.get_instance().set_language(language)
        assert not window.act_generate_grid.isEnabled()
        assert not window.act_import_csv.isEnabled()
        assert not window.survey_widget.btn_save_next.isEnabled()
        save_actions = [a for a in window.findChildren(QAction)
                        if a.shortcut() == QKeySequence(QKeySequence.StandardKey.Save)]
        assert len(save_actions) == 1


def test_empty_project_clears_selection_and_disables_capture_and_navigation(window):
    window._replace_project(LuminationProject(name='Empty', room=Room()))
    bar = window.survey_widget
    assert bar.active_point_id is None
    assert bar.edit_lux.text() == ''
    for button in [bar.btn_save_next, bar.btn_prev, bar.btn_next, bar.btn_next_unmeasured]:
        assert not button.isEnabled()


def test_skip_last_returns_to_skipped_pending_point_without_writing(window):
    window.project.points[1].record_reading(200)
    window._on_point_selected('P3')
    window.survey_widget.btn_next.click()
    assert window.active_point_id == 'P1'
    assert window.project.points[0].lux is None
    assert window.project.points[2].lux is None


def test_edit_done_restores_survey_layout_focus_and_zoom(window):
    bar = window.survey_widget
    bar.edit_lux.setFocus()
    window.canvas_widget._zoom(1.5)
    before = window.canvas_widget.ax.get_xlim(), window.canvas_widget.ax.get_ylim()
    window.act_edit_survey.trigger()
    window._on_point_selected('P2')
    window.act_done_editing.trigger()
    assert window.active_point_id == 'P1'
    assert not window.dock_left.isVisible() and not window.dock_right.isVisible()
    assert window.canvas_widget.ax.get_xlim() == before[0]
    assert window.canvas_widget.ax.get_ylim() == before[1]
    assert QApplication.focusWidget() is bar.edit_lux


def test_selected_device_sample_reaches_main_window_with_provenance(window):
    session = DeviceSession()
    session.select_source('usb', profile_id='qualified-test-profile', supported=True,
                          connected=True, freshness_seconds=2)
    sample = session.update_sample('usb', 420)
    window._on_hardware_reading_captured(sample)
    window._on_hardware_reading_captured(sample)
    point = window.project.points[0]
    assert point.lux == 420
    assert point.source_profile_id == 'qualified-test-profile'
    assert point.source_sample_id == sample.sample_id
    assert window.project.points[1].lux is None


def test_german_decimal_entry_and_unrounded_correction(window):
    TranslationManager.get_instance().set_language('de')
    window.survey_widget.edit_lux.setText('123,456789')
    window.survey_widget.btn_save_next.click()
    assert window.project.points[0].lux == 123.456789
    window.act_edit_survey.trigger()
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


def test_save_from_review_and_edit_keeps_resume_workspace(window, tmp_path):
    window.project.file_path = str(tmp_path / 'review.luxproj')
    window.act_enter_review.trigger()
    window.act_save.trigger()
    assert load_project(window.project.file_path).resume_state['workspace'] == 'review'
    window.act_edit_survey.trigger()
    window._write_recovery_snapshot()
    assert window.recovery_store.load().workspace == 'review'
    window.act_save.trigger()
    assert load_project(window.project.file_path).resume_state['workspace'] == 'review'


def test_structure_buttons_clear_and_history_still_work(window, monkeypatch):
    window.act_edit_survey.trigger()
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
    monkeypatch.setattr(QMessageBox, 'question', lambda *_args: QMessageBox.StandardButton.Yes)
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


@pytest.mark.parametrize('action,suffix', [('act_export_csv', '.csv'), ('act_export_pdf', '.pdf'), ('act_export_img', '.png')])
def test_export_menu_actions_produce_files(window, tmp_path, monkeypatch, action, suffix):
    for point in window.project.points:
        point.record_reading(100)
    output = tmp_path / ('export' + suffix)
    monkeypatch.setattr('ui.main_window.QFileDialog.getSaveFileName', lambda *_args: (str(output), ''))
    monkeypatch.setattr(QMessageBox, 'information', lambda *_args: None)
    errors = []
    monkeypatch.setattr(QMessageBox, 'critical', lambda *_args: errors.append(_args))
    getattr(window, action).trigger()
    assert not errors
    assert output.exists() and output.stat().st_size > 50


@pytest.mark.parametrize('language', ['en', 'ro', 'de'])
@pytest.mark.parametrize('size', [(960, 600), (1380, 860), (1920, 1080)])
def test_survey_controls_fit_in_every_workspace_and_language(window, language, size):
    from ui.styles import MAIN_STYLESHEET
    window.setStyleSheet(MAIN_STYLESHEET)
    TranslationManager.get_instance().set_language(language)
    window.resize(*size)
    for mode in ['survey', 'review', 'edit']:
        getattr(window, f'_enter_{mode}_workspace')()
        QApplication.instance().processEvents()
        assert window.minimumSizeHint().width() <= window.width()
        assert window.minimumSizeHint().height() <= window.height()
        if mode != 'review':
            for button in [window.survey_widget.btn_save_next, window.survey_widget.btn_prev,
                           window.survey_widget.btn_next, window.survey_widget.btn_next_unmeasured]:
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


def test_map_popup_obeys_workspace_and_blank_map_click_preserves_selection(window):
    from types import SimpleNamespace
    canvas = window.canvas_widget
    canvas._on_mouse_click(SimpleNamespace(xdata=1, ydata=1))
    assert canvas.popup_editor.isVisible()
    window.act_enter_review.trigger()
    canvas._on_mouse_click(SimpleNamespace(xdata=1, ydata=1))
    assert not canvas.popup_editor.isVisible()
    canvas._on_mouse_click(SimpleNamespace(xdata=3, ydata=2))
    assert canvas.selected_point_id == window.active_point_id == 'P1'


def test_new_setup_retains_spacing_grid_and_optional_author(window):
    from ui.dialogs.survey_setup_dialog import SurveySetupDialog
    dialog = SurveySetupDialog()
    dialog.author.setText('Surveyor A')
    dialog.grid_mode.setCurrentIndex(1)
    dialog.spacing_x.setValue(1.25)
    dialog.spacing_y.setValue(0.75)
    project = dialog.get_created_project()
    assert project.author == 'Surveyor A'
    assert project.room.grid_cols == 4
    assert project.room.grid_rows == 4
    assert all(point.lux is None for point in project.points)


def test_start_screen_disables_project_only_actions(window):
    window._show_start_screen()
    assert not window.menu_survey.isEnabled()
    assert not window.menu_export.isEnabled()
    assert not window.act_save.isEnabled()
    assert not window.survey_toolbar.isVisible()
    assert window.act_new.isEnabled() and window.act_open.isEnabled()


def test_grid_menu_applies_one_undoable_change(window, monkeypatch):
    from ui.dialogs.grid_generator_dialog import GridGeneratorDialog
    window.act_edit_survey.trigger()
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


def test_device_dialog_keeps_capture_readable_and_disables_empty_connections(window, monkeypatch):
    from ui.dialogs.hardware_connection_dialog import HardwareConnectionDialog
    monkeypatch.setattr(window.usb_source, 'list_available_ports', lambda: [])
    dialog = HardwareConnectionDialog(window.usb_source, window.bt_source)
    dialog.show()
    QApplication.instance().processEvents()
    assert dialog.btn_capture.width() >= dialog.btn_capture.minimumSizeHint().width()
    assert not dialog.btn_connect_usb.isEnabled()
    assert not dialog.btn_connect_bt.isEnabled()
    assert not dialog.btn_capture.isEnabled()
    dialog.close()
    dialog.deleteLater()
