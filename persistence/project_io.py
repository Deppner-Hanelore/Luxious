"""Project File I/O Persistence.

Saves and loads Lumination project files (.luxproj or .json) in a clean,
documented JSON format.
"""

from __future__ import annotations
import json
import os
import tempfile
from typing import Dict, Any

from models.project import LuminationProject


def save_project(project: LuminationProject, file_path: str) -> None:
    """Save Lumination project to a JSON file (.luxproj)."""
    data = project.to_dict()
    dir_name = os.path.dirname(file_path)
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)

    _atomic_write_json(file_path, data)

    project.file_path = file_path
    project.is_dirty = False


def _atomic_write_json(file_path: str, data: Dict[str, Any]) -> None:
    """Replace a JSON file atomically, preserving the prior file on failure."""
    absolute_path = os.path.abspath(file_path)
    directory = os.path.dirname(absolute_path)
    os.makedirs(directory, exist_ok=True)
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=directory,
            prefix=f".{os.path.basename(file_path)}.",
            suffix=".tmp",
            delete=False,
        ) as stream:
            temporary_path = stream.name
            json.dump(data, stream, indent=2, ensure_ascii=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_path, absolute_path)
        temporary_path = None
        if hasattr(os, "O_DIRECTORY"):
            directory_fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
    finally:
        if temporary_path and os.path.exists(temporary_path):
            os.unlink(temporary_path)


def load_project(file_path: str) -> LuminationProject:
    """Load Lumination project from a JSON file."""
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"Project file not found: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    project = LuminationProject.from_dict(data)
    project.file_path = file_path
    project.is_dirty = False
    return project
