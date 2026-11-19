"""Undo / Redo Command Architecture for Lumination.

Uses PySide6.QtGui.QUndoCommand and QUndoStack to support full multi-level
undo/redo for measurement edits, point additions, point deletions, and grid modifications.
"""

from __future__ import annotations
from typing import Optional, List, Callable, Any
import copy
from datetime import datetime
from PySide6.QtGui import QUndoCommand, QUndoStack

from models.project import LuminationProject
from models.measurement import MeasurementPoint
from models.room import Room


class SetMeasurementLuxCommand(QUndoCommand):
    """Command for recording/editing a lux reading on a point."""

    def __init__(
        self,
        project: LuminationProject,
        point_id: str,
        new_lux: Optional[float],
        new_device: Optional[str] = None,
        callback: Optional[Callable[[], None]] = None,
        workflow_operation: str = "record_reading",
        new_sample_id: Optional[str] = None,
        new_profile_id: Optional[str] = None,
    ) -> None:
        super().__init__(f"Edit Measurement {point_id}")
        self.project = project
        self.point_id = point_id
        self.new_lux = new_lux
        self.new_device = new_device
        self.callback = callback
        self.workflow_operation = workflow_operation
        self.new_timestamp = datetime.now().isoformat()
        self.new_sample_id = new_sample_id
        self.new_profile_id = new_profile_id

        pt = project.find_point_by_id(point_id)
        if pt:
            self.old_lux = pt.lux
            self.old_timestamp = pt.timestamp
            self.old_device = pt.device_name
            self.old_sample_id = pt.source_sample_id
            self.old_profile_id = pt.source_profile_id
            self.old_outlier = pt.is_possible_outlier
            self.old_reason = pt.outlier_reason
        else:
            self.old_lux = None
            self.old_timestamp = None
            self.old_device = None
            self.old_sample_id = None
            self.old_profile_id = None
            self.old_outlier = False
            self.old_reason = ""

    def redo(self) -> None:
        pt = self.project.find_point_by_id(self.point_id)
        if pt:
            if self.new_lux is not None:
                pt.record_reading(
                    self.new_lux,
                    timestamp=self.new_timestamp,
                    device_name=self.new_device,
                    source_sample_id=self.new_sample_id,
                    source_profile_id=self.new_profile_id,
                )
            else:
                pt.clear_reading()
            self.project.mark_modified()
            if self.callback:
                self.callback()

    def undo(self) -> None:
        pt = self.project.find_point_by_id(self.point_id)
        if pt:
            pt.lux = self.old_lux
            pt.timestamp = self.old_timestamp
            pt.device_name = self.old_device
            pt.source_sample_id = self.old_sample_id
            pt.source_profile_id = self.old_profile_id
            pt.is_possible_outlier = self.old_outlier
            pt.outlier_reason = self.old_reason
            self.project.mark_modified()
            if self.callback:
                self.callback()


class AddPointCommand(QUndoCommand):
    """Command for adding a custom measurement point."""

    def __init__(
        self,
        project: LuminationProject,
        point: MeasurementPoint,
        callback: Optional[Callable[[], None]] = None,
    ) -> None:
        super().__init__(f"Add Point {point.id}")
        self.project = project
        self.point = copy.deepcopy(point)
        self.callback = callback
        self.workflow_operation = "change_point"

    def redo(self) -> None:
        if not self.project.find_point_by_id(self.point.id):
            self.project.points.append(copy.deepcopy(self.point))
            self.project.mark_modified()
            if self.callback:
                self.callback()

    def undo(self) -> None:
        self.project.points = [p for p in self.project.points if p.id != self.point.id]
        self.project.mark_modified()
        if self.callback:
            self.callback()


class DeletePointCommand(QUndoCommand):
    """Command for deleting a measurement point."""

    def __init__(
        self,
        project: LuminationProject,
        point_id: str,
        callback: Optional[Callable[[], None]] = None,
    ) -> None:
        super().__init__(f"Delete Point {point_id}")
        self.project = project
        self.point_id = point_id
        self.callback = callback
        self.workflow_operation = "change_point"

        pt = project.find_point_by_id(point_id)
        self.deleted_point = copy.deepcopy(pt) if pt else None
        self.deleted_index = 0
        if pt:
            for idx, p in enumerate(project.points):
                if p.id == point_id:
                    self.deleted_index = idx
                    break

    def redo(self) -> None:
        if self.deleted_point:
            self.project.points = [p for p in self.project.points if p.id != self.point_id]
            self.project.mark_modified()
            if self.callback:
                self.callback()

    def undo(self) -> None:
        if self.deleted_point:
            # Reinsert at original index if possible
            insert_pos = min(self.deleted_index, len(self.project.points))
            self.project.points.insert(insert_pos, copy.deepcopy(self.deleted_point))
            self.project.mark_modified()
            if self.callback:
                self.callback()


class UpdatePointCommand(QUndoCommand):
    """Replace one point with validated dialog/table values as a single edit."""

    workflow_operation = "change_point"

    def __init__(
        self,
        project: LuminationProject,
        updated_point: MeasurementPoint,
        callback: Optional[Callable[[], None]] = None,
    ) -> None:
        super().__init__(f"Edit Point {updated_point.id}")
        self.project = project
        self.point_id = updated_point.id
        self.callback = callback
        current = project.find_point_by_id(self.point_id)
        self.before = copy.deepcopy(current) if current else None
        self.after = copy.deepcopy(updated_point)

    def _apply(self, point: Optional[MeasurementPoint]) -> None:
        if point is None:
            return
        for index, current in enumerate(self.project.points):
            if current.id == self.point_id:
                self.project.points[index] = copy.deepcopy(point)
                self.project.mark_modified()
                if self.callback:
                    self.callback()
                return

    def redo(self) -> None:
        self._apply(self.after)

    def undo(self) -> None:
        self._apply(self.before)


class ReplaceProjectDataCommand(QUndoCommand):
    """Atomically replace room/grid/point data, used by import and grid edits."""

    workflow_operation = "change_point"

    def __init__(
        self,
        project: LuminationProject,
        replacement: LuminationProject,
        text: str,
        callback: Optional[Callable[[], None]] = None,
    ) -> None:
        super().__init__(text)
        self.project = project
        self.callback = callback
        self.before_room = copy.deepcopy(project.room)
        self.before_points = copy.deepcopy(project.points)
        self.after_room = copy.deepcopy(replacement.room)
        self.after_points = copy.deepcopy(replacement.points)

    def _apply(self, room: Room, points: List[MeasurementPoint]) -> None:
        self.project.room = copy.deepcopy(room)
        self.project.points = copy.deepcopy(points)
        self.project.mark_modified()
        if self.callback:
            self.callback()

    def redo(self) -> None:
        self._apply(self.after_room, self.after_points)

    def undo(self) -> None:
        self._apply(self.before_room, self.before_points)


class ClearMeasurementsCommand(QUndoCommand):
    """Clear all measured values while preserving point geometry and undo data."""

    workflow_operation = "change_point"

    def __init__(
        self,
        project: LuminationProject,
        callback: Optional[Callable[[], None]] = None,
    ) -> None:
        super().__init__("Clear Measurements")
        self.project = project
        self.callback = callback
        self.before = copy.deepcopy(project.points)
        self.after = copy.deepcopy(project.points)
        for point in self.after:
            point.clear_reading()

    def _apply(self, points: List[MeasurementPoint]) -> None:
        self.project.points = copy.deepcopy(points)
        self.project.mark_modified()
        if self.callback:
            self.callback()

    def redo(self) -> None:
        self._apply(self.after)

    def undo(self) -> None:
        self._apply(self.before)
