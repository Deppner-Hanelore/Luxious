"""Separate, locally durable recovery snapshots for interrupted surveys."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
import os
from typing import Optional

from PySide6.QtCore import QStandardPaths

from models.project import LuminationProject
from persistence.project_io import _atomic_write_json


@dataclass(frozen=True)
class RecoverySnapshot:
    project: LuminationProject
    workspace: str
    selected_point_id: Optional[str]
    saved_at: str


class RecoveryStore:
    """Keep the latest working copy outside the user's named project file."""

    def __init__(self, path: Optional[str] = None) -> None:
        if path is None:
            app_data = QStandardPaths.writableLocation(
                QStandardPaths.StandardLocation.AppDataLocation
            )
            if not app_data:
                app_data = os.path.join(os.path.expanduser("~"), ".local", "share", "Lumination")
            path = os.path.join(app_data, "recovery.json")
        self.path = os.path.abspath(path)

    def save(
        self,
        project: LuminationProject,
        workspace: str = "survey",
        selected_point_id: Optional[str] = None,
    ) -> None:
        """Atomically persist the current model and stable UI resume context."""
        if workspace not in ("survey", "review"):
            workspace = "survey"
        point_ids = {point.id for point in project.points}
        if selected_point_id not in point_ids:
            selected_point_id = None
        data = {
            "recovery_version": 1,
            "saved_at": datetime.now().isoformat(),
            "project": project.to_dict(),
            "resume": {
                "workspace": workspace,
                "selected_point_id": selected_point_id,
            },
        }
        _atomic_write_json(self.path, data)

    def load(self) -> Optional[RecoverySnapshot]:
        """Read a valid recovery snapshot, or return None when absent."""
        if not os.path.isfile(self.path):
            return None
        with open(self.path, "r", encoding="utf-8") as stream:
            data = json.load(stream)
        if data.get("recovery_version") != 1:
            raise ValueError("This recovery snapshot version is not supported.")
        project = LuminationProject.from_dict(data["project"])
        resume = data.get("resume", {})
        workspace = resume.get("workspace", "survey")
        if workspace not in ("survey", "review"):
            workspace = "survey"
        selected_id = resume.get("selected_point_id")
        if selected_id not in {point.id for point in project.points}:
            selected_id = None
        project.is_dirty = True
        return RecoverySnapshot(
            project=project,
            workspace=workspace,
            selected_point_id=selected_id,
            saved_at=str(data.get("saved_at", "")),
        )

    def discard(self) -> None:
        """Remove a recovery snapshot after named save or explicit discard."""
        try:
            os.remove(self.path)
        except FileNotFoundError:
            pass
