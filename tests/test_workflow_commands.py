"""Undo behavior for survey mutations routed through workflow commands."""

from PySide6.QtGui import QUndoStack

from models.measurement import MeasurementPoint
from models.project import LuminationProject
from models.room import Room
from ui.workflow_controller import WorkflowController
from utils.undo_commands import (
    ClearMeasurementsCommand,
    ReplaceProjectDataCommand,
    UpdatePointCommand,
)


def test_point_update_and_clear_are_reversible_with_reading_provenance():
    project = LuminationProject(room=Room(length=5.0, width=4.0))
    point = MeasurementPoint(id="P1", x=1.0, y=1.0, lux=420.0, device_name="Meter A")
    project.points = [point]
    stack = QUndoStack()
    updated = MeasurementPoint(id="P1", x=1.0, y=1.0, lux=0.0, notes="retaken")

    stack.push(UpdatePointCommand(project, updated))
    assert project.points[0].lux == 0.0
    assert project.points[0].notes == "retaken"
    stack.undo()
    assert project.points[0].lux == 420.0
    assert project.points[0].device_name == "Meter A"

    stack.clear()
    stack.push(ClearMeasurementsCommand(project))
    assert project.points[0].lux is None
    assert project.points[0].device_name is None
    stack.undo()
    assert project.points[0].lux == 420.0
    assert project.points[0].device_name == "Meter A"


def test_grid_or_import_data_replacement_is_one_undoable_transaction():
    project = LuminationProject(room=Room(length=5.0, width=4.0))
    project.regenerate_grid(rows=1, cols=2, wall_margin=0.0)
    replacement = LuminationProject(room=Room(length=5.0, width=4.0))
    replacement.regenerate_grid(rows=2, cols=3, wall_margin=0.0)
    stack = QUndoStack()

    stack.push(ReplaceProjectDataCommand(project, replacement, "Change grid"))
    assert len(project.points) == 6
    stack.undo()
    assert len(project.points) == 2
    stack.redo()
    assert len(project.points) == 6


def test_capture_operation_ids_are_idempotent_with_bounded_history():
    workflow = WorkflowController()
    assert workflow.claim_operation("sample-1")
    assert not workflow.claim_operation("sample-1")
    assert workflow.claim_operation("sample-2")
