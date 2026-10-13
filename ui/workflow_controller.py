"""Central workflow state and mutation policy for a room survey.

This module contains no widgets and performs no project mutations. UI handlers
ask the controller before invoking a command, so mouse, table, and shortcut
paths can share the same rules.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from collections import deque
from typing import Optional


class Workspace(str, Enum):
    SURVEY = "survey"
    REVIEW = "review"
    EDIT = "edit"


class Operation(str, Enum):
    NAVIGATE = "navigate"
    RECORD_READING = "record_reading"
    CORRECT_READING = "correct_reading"
    CHANGE_POINT = "change_point"
    CHANGE_ROOM_OR_GRID = "change_room_or_grid"
    IMPORT_READINGS = "import_readings"
    SAVE = "save"
    EXPORT = "export"
    CHANGE_TARGET = "change_target"
    CHANGE_DISPLAY = "change_display"


@dataclass(frozen=True)
class WorkflowSnapshot:
    """Small, serializable view state; never contains a live source object."""

    workspace: Workspace
    selected_point_id: Optional[str]
    edit_return_workspace: Optional[Workspace] = None
    edit_return_point_id: Optional[str] = None


class WorkflowController:
    """Own workspace transitions, edit return state, and action permissions."""

    _EDIT_ONLY = frozenset(
        {
            Operation.CORRECT_READING,
            Operation.CHANGE_POINT,
            Operation.CHANGE_ROOM_OR_GRID,
            Operation.IMPORT_READINGS,
        }
    )

    def __init__(self) -> None:
        self.workspace = Workspace.SURVEY
        self.selected_point_id: Optional[str] = None
        self._edit_return_workspace: Optional[Workspace] = None
        self._edit_return_point_id: Optional[str] = None
        self._seen_operations: set[str] = set()
        self._operation_order: deque[str] = deque()

    def claim_operation(self, operation_id: str) -> bool:
        """Accept each capture event ID once during this application session."""
        if not operation_id or operation_id in self._seen_operations:
            return False
        self._seen_operations.add(operation_id)
        self._operation_order.append(operation_id)
        if len(self._operation_order) > 2048:
            expired = self._operation_order.popleft()
            self._seen_operations.discard(expired)
        return True

    def allows(self, operation: Operation) -> bool:
        """Return whether an operation may run in the current workspace."""
        if operation in (
            Operation.SAVE,
            Operation.EXPORT,
            Operation.NAVIGATE,
            Operation.CHANGE_TARGET,
            Operation.CHANGE_DISPLAY,
        ):
            return True
        if operation == Operation.RECORD_READING:
            return self.workspace in (Workspace.SURVEY, Workspace.EDIT)
        if operation in self._EDIT_ONLY:
            return self.workspace == Workspace.EDIT
        return False

    def select_point(self, point_id: Optional[str]) -> None:
        """Track the point selected by either map or accessible list/table."""
        self.selected_point_id = point_id

    def enter_review(self) -> None:
        if self.workspace != Workspace.EDIT:
            self.workspace = Workspace.REVIEW

    def enter_survey(self) -> None:
        if self.workspace != Workspace.EDIT:
            self.workspace = Workspace.SURVEY

    def enter_edit(self) -> None:
        if self.workspace == Workspace.EDIT:
            return
        self._edit_return_workspace = self.workspace
        self._edit_return_point_id = self.selected_point_id
        self.workspace = Workspace.EDIT

    def leave_edit(self, valid_point_ids: set[str]) -> Optional[str]:
        """Restore prior workspace and selected point, falling back if deleted."""
        if self.workspace != Workspace.EDIT:
            return self.selected_point_id

        self.workspace = self._edit_return_workspace or Workspace.SURVEY
        preferred = self._edit_return_point_id
        self.selected_point_id = preferred if preferred in valid_point_ids else None
        self._edit_return_workspace = None
        self._edit_return_point_id = None
        return self.selected_point_id

    def reconcile_points(self, valid_point_ids: set[str]) -> Optional[str]:
        """Clear a stale selection after point deletion or project replacement."""
        if self.selected_point_id not in valid_point_ids:
            self.selected_point_id = None
        return self.selected_point_id

    def next_pending(self, ordered_point_ids: list[str], measured_ids: set[str]) -> Optional[str]:
        """Find the next pending point after selection, wrapping only to skipped work.

        Fully measured surveys return ``None`` so capture completion cannot wrap
        to the first point and overwrite it.
        """
        if not ordered_point_ids:
            return None
        start = ordered_point_ids.index(self.selected_point_id) if self.selected_point_id in ordered_point_ids else -1
        for offset in range(1, len(ordered_point_ids) + 1):
            point_id = ordered_point_ids[(start + offset) % len(ordered_point_ids)]
            if point_id not in measured_ids:
                return point_id
        return None

    def snapshot(self) -> WorkflowSnapshot:
        """Return the minimal UI state suitable for future versioned persistence."""
        return WorkflowSnapshot(
            workspace=self.workspace,
            selected_point_id=self.selected_point_id,
            edit_return_workspace=self._edit_return_workspace,
            edit_return_point_id=self._edit_return_point_id,
        )

    def restore(self, snapshot: WorkflowSnapshot, valid_point_ids: set[str]) -> None:
        """Restore view state, safely falling back from missing/deleted points."""
        self.workspace = snapshot.workspace
        self.selected_point_id = (
            snapshot.selected_point_id
            if snapshot.selected_point_id in valid_point_ids
            else None
        )
        self._edit_return_workspace = snapshot.edit_return_workspace
        self._edit_return_point_id = (
            snapshot.edit_return_point_id
            if snapshot.edit_return_point_id in valid_point_ids
            else None
        )
