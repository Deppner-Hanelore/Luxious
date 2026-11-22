"""Automated UI Integration and Workflow Tests with PySide6 / QTest."""

import os
import pytest
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import Qt, QSettings, QCoreApplication, QEvent
from PySide6.QtGui import QCloseEvent
from PySide6.QtTest import QTest

from models.room import Room
from models.project import LuminationProject
from models.measurement import MeasurementPoint
from ui.main_window import MainWindow
from ui.dialogs.new_project_dialog import NewProjectDialog
from ui.dialogs.grid_generator_dialog import GridGeneratorDialog
from ui.dialogs.survey_setup_dialog import SurveySetupDialog
from ui.dialogs.import_preview_dialog import ImportPreviewDialog
from persistence.recovery import RecoveryStore


@pytest.fixture(scope="session")
def qapp():
    """Ensure QApplication instance is running."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_main_window_lifecycle(qapp, tmp_path):
    """Verify MainWindow creation, data loading, point editing, and calculations."""
    window = MainWindow(MainWindow._create_practice_project())
    window.show()
    qapp.processEvents()

    # Check project is loaded
    assert window.project is not None
    assert len(window.project.points) == 12

    # Check statistical calculations on default project
    stats = window.results_panel.stats
    assert stats is not None
    assert stats.count == 12
    assert stats.e_min == 320.0
    assert stats.e_max == 570.0
    assert pytest.approx(stats.uniformity_u0, 0.01) == 320.0 / stats.e_avg

    # Check target comparison
    assert window.target_panel.project.target_lux == 500.0

    # Simulate changing a measurement in point 0 (P1)
    p1 = window.project.points[0]
    p1.record_reading(600.0)
    window.table_widget.data_changed.emit()

    # Recalculated stats should update
    new_stats = window.results_panel.stats
    assert new_stats.e_min == 370.0  # P1 is now 600, so new min is P2 (370)
    assert new_stats.e_max == 600.0

    # Test switching display mode to difference
    window.comparison_panel.set_display_mode("difference")
    assert window.project.visualization_settings.display_mode == "difference"

    # Test saving project
    save_path = str(tmp_path / "ui_saved_project.luxproj")
    window.project.file_path = save_path
    window._on_save_project()
    assert os.path.exists(save_path)

    window.close()


def test_fresh_launch_shows_actions_without_sample_measurements(qapp, tmp_path):
    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    window = MainWindow(
        recovery_store=RecoveryStore(str(tmp_path / "recovery.json")),
        settings=settings,
    )

    assert window.content_stack.currentWidget() is window.start_screen
    assert window.project.points == []
    assert not window.project.is_practice
    assert not window.start_screen.btn_new.isHidden()
    assert not window.start_screen.btn_open.isHidden()
    assert window.start_screen.btn_resume.isHidden()

    window.start_screen.btn_practice.click()
    assert window.content_stack.currentWidget() is window.main_workspace
    assert window.project.is_practice
    assert len(window.project.get_measured_points()) > 0
    assert "PRACTICE" in window.lbl_project_status.text()

    window.project.is_dirty = False
    window.recovery_store.discard()
    window.close()


def test_start_screen_resumes_local_recovery(qapp, tmp_path):
    recovery = RecoveryStore(str(tmp_path / "recovery.json"))
    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    project = LuminationProject(name="Night shift", room=Room(length=4.0, width=3.0))
    project.points = [MeasurementPoint(id="P1", x=1.0, y=1.0, lux=320.0)]
    recovery.save(project, workspace="survey", selected_point_id="P1")

    window = MainWindow(recovery_store=recovery, settings=settings)
    assert window.content_stack.currentWidget() is window.start_screen
    assert not window.start_screen.btn_resume.isHidden()
    assert "Night shift" in window.start_screen.lbl_resume_title.text()

    window.start_screen.btn_resume.click()
    assert window.content_stack.currentWidget() is window.main_workspace
    assert window.project.name == "Night shift"
    assert window.project.is_dirty
    assert window.active_point_id == "P1"

    window.project.is_dirty = False
    recovery.discard()
    window.close()


def test_start_screen_does_not_reopen_or_look_for_the_last_project(qapp, tmp_path):
    from persistence.project_io import save_project

    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    saved_path = str(tmp_path / "saved.luxproj")
    saved = LuminationProject(name="Saved shift", room=Room(length=4.0, width=3.0))
    saved.points = [MeasurementPoint(id="P1", x=1.0, y=1.0, lux=250.0)]
    save_project(saved, saved_path)
    settings.setValue("last_project_path", saved_path)  # left by older versions; now ignored
    recovery = RecoveryStore(str(tmp_path / "recovery.json"))
    window = MainWindow(recovery_store=recovery, settings=settings)
    assert window.start_screen.btn_resume.isHidden()
    assert "Saved shift" not in window.start_screen.lbl_resume_title.text()
    assert not hasattr(window.start_screen, "btn_locate")
    assert not hasattr(window.start_screen, "lbl_missing")
    window.close()

    settings.setValue("last_project_path", str(tmp_path / "deleted.luxproj"))
    other = MainWindow(recovery_store=recovery, settings=settings)
    assert other.start_screen.btn_resume.isHidden()
    other.close()


def test_three_step_survey_setup_preserves_room_and_creates_pending_grid(qapp):
    dialog = SurveySetupDialog()
    dialog.name.setText("Warehouse A")
    dialog.length.setValue(18.0)
    dialog._next()
    dialog.cols.setValue(5)
    dialog.rows.setValue(2)
    dialog._next()
    dialog._back()
    assert dialog.length.value() == 18.0
    assert dialog.cols.value() == 5
    dialog._next()
    project = dialog.get_created_project()

    assert len(project.points) == 10
    assert all(point.lux is None for point in project.points)
    assert project.target_lux is None
    assert project.room.length == 18.0
    assert project.name == "Warehouse A"
    assert "18 × 4 m room" in dialog.setup_summary.text()
    assert "Manual entry" in dialog.setup_summary.text()
    dialog.close()


def test_survey_setup_does_not_create_with_unreviewed_csv(qapp, monkeypatch):
    dialog = SurveySetupDialog()
    dialog.pages.setCurrentIndex(2)
    dialog.reading_method.setCurrentIndex(1)
    monkeypatch.setattr("ui.dialogs.survey_setup_dialog.QMessageBox.information", lambda *_args: None)

    dialog._next()

    assert dialog.result() == int(SurveySetupDialog.DialogCode.Rejected)
    assert dialog.get_created_project().get_measured_points() == []
    dialog.close()


def test_table_import_preview_cancel_and_apply_in_new_survey_window(qapp, tmp_path, monkeypatch):
    table = tmp_path / "readings.csv"
    table.write_text("410,420\n430,\n", encoding="utf-8")
    dialog = SurveySetupDialog()
    dialog.cols.setValue(2)
    dialog.rows.setValue(2)
    monkeypatch.setattr("ui.dialogs.survey_setup_dialog.QFileDialog.getOpenFileName", lambda *_args: (str(table), ""))

    monkeypatch.setattr(ImportPreviewDialog, "exec", lambda _dialog: int(ImportPreviewDialog.DialogCode.Rejected))
    dialog._choose_csv()
    assert dialog.get_created_project().get_measured_points() == []

    monkeypatch.setattr(ImportPreviewDialog, "exec", lambda _dialog: int(ImportPreviewDialog.DialogCode.Accepted))
    dialog._choose_csv()
    project = dialog.get_created_project()
    readings = {(round(p.x, 2), round(p.y, 2)): p.lux for p in project.points}
    top, bottom = max(y for _x, y in readings), min(y for _x, y in readings)
    left, right = min(x for x, _y in readings), max(x for x, _y in readings)
    assert readings[(left, top)] == 410 and readings[(right, top)] == 420
    assert readings[(left, bottom)] == 430 and readings[(right, bottom)] is None
    dialog.close()
    dialog.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)


def test_dirty_close_cancel_and_save_failure_keep_window_open(qapp, tmp_path, monkeypatch):
    window = MainWindow(LuminationProject(name="Close guard", room=Room(length=4.0, width=3.0)))
    window.recovery_store.path = str(tmp_path / "recovery.json")
    window.project.mark_modified()

    monkeypatch.setattr(
        "ui.main_window.QMessageBox.exec",
        lambda _dialog: int(QMessageBox.StandardButton.Cancel),
    )
    event = QCloseEvent()
    window.closeEvent(event)
    assert not event.isAccepted()

    monkeypatch.setattr(
        "ui.main_window.QMessageBox.exec",
        lambda _dialog: int(QMessageBox.StandardButton.Save),
    )
    window._on_save_project = lambda: False
    event = QCloseEvent()
    window.closeEvent(event)
    assert not event.isAccepted()

    window.deleteLater()
    qapp.processEvents()


def test_measurement_policy_zero_deduplication_undo_and_final_point(qapp, tmp_path):
    project = LuminationProject(name="Capture policy", room=Room(length=4.0, width=3.0))
    project.points = [
        MeasurementPoint(id="P1", x=1.0, y=1.0),
        MeasurementPoint(id="P2", x=2.0, y=1.0),
    ]
    window = MainWindow(project)
    window.recovery_store.path = str(tmp_path / "recovery.json")
    window._on_point_selected("P1")

    assert window._on_measurement_recorded("P1", 0.0, operation_id="event-1")
    assert project.find_point_by_id("P1").lux == 0.0
    assert window.active_point_id == "P2"
    assert not window._on_measurement_recorded("P2", 500.0, operation_id="event-1")
    assert project.find_point_by_id("P2").lux is None

    assert window._on_measurement_recorded("P2", 500.0, operation_id="event-2")
    assert window.active_point_id == "P2"

    window._undo_if_allowed()
    assert project.find_point_by_id("P2").lux is None
    window._redo_if_allowed()
    assert project.find_point_by_id("P2").lux == 500.0

    assert not window._on_measurement_recorded("P1", -1.0, operation_id="failed-retake")
    assert project.find_point_by_id("P1").lux == 0.0
    assert window._on_measurement_recorded("P1", 450.0, operation_id="retake")
    window._undo_if_allowed()
    assert project.find_point_by_id("P1").lux == 0.0

    window._on_point_delete_requested("P2")
    assert project.find_point_by_id("P2") is None
    assert window.active_point_id == "P1"
    window._undo_if_allowed()
    assert project.find_point_by_id("P2") is not None
    window.project.is_dirty = False
    window.recovery_store.discard()
    window.close()


def test_measurement_table_edits_are_undoable_without_edit_mode(qapp, tmp_path):
    project = LuminationProject(name="Table policy", room=Room(length=4.0, width=3.0))
    project.points = [MeasurementPoint(id="P1", x=1.0, y=1.0)]
    window = MainWindow(project)
    window.recovery_store.path = str(tmp_path / "recovery.json")
    index = window.table_widget.model.index(0, 3)

    assert window.table_widget.model.setData(index, "0", Qt.ItemDataRole.EditRole)
    assert project.points[0].lux == 0.0
    window._undo_if_allowed()
    assert project.points[0].lux is None

    window.project.is_dirty = False
    window.recovery_store.discard()
    window.close()


def test_survey_bar_blank_zero_skip_and_deliberate_correction(qapp, tmp_path):
    project = LuminationProject(name="Field run", room=Room(length=4.0, width=3.0))
    project.points = [
        MeasurementPoint(id="P1", x=1.0, y=1.0),
        MeasurementPoint(id="P2", x=2.0, y=1.0),
    ]
    window = MainWindow(project)
    window.recovery_store.path = str(tmp_path / "recovery.json")
    bar = window.survey_widget

    assert bar.edit_lux.text() == ""
    bar.btn_save_next.click()
    assert project.points[0].lux is None

    bar.edit_lux.setText("0")
    bar.btn_save_next.click()
    assert project.points[0].lux == 0.0
    assert window.active_point_id == "P2"

    bar.combo_points.setCurrentIndex(0)
    assert bar.btn_save_next.isEnabled()
    bar.edit_lux.setText("12.5")
    bar.btn_save_next.click()
    assert project.points[0].lux == 12.5
    window._undo_if_allowed()
    assert project.points[0].lux == 0.0

    window.project.is_dirty = False
    window.recovery_store.discard()
    window.close()


def test_five_point_manual_survey_finishes_without_wrapping(qapp, tmp_path):
    project = LuminationProject(name="Five point run", room=Room(length=8.0, width=4.0))
    project.points = [
        MeasurementPoint(id=f"P{index}", x=float(index), y=1.0)
        for index in range(1, 6)
    ]
    window = MainWindow(project)
    window.recovery_store.path = str(tmp_path / "recovery.json")

    for index in range(1, 6):
        assert window.active_point_id == f"P{index}"
        window.survey_widget.edit_lux.setText(str(index * 100))
        window.survey_widget.btn_save_next.click()

    assert len(project.get_measured_points()) == 5
    assert window.active_point_id == "P5"
    assert "Survey complete" in window.status_bar.currentMessage()
    window.project.is_dirty = False
    window.recovery_store.discard()
    window.close()
