"""Project Data Model.

Orchestrates the room, measurement points, target illuminance,
visualization preferences, and metadata.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
import math

from models.room import Room
from models.measurement import MeasurementPoint


@dataclass
class VisualizationSettings:
    """Settings controlling 2D map and contour rendering."""
    show_heatmap: bool = True
    show_contours: bool = True
    show_points: bool = True
    show_values: bool = True
    show_grid: bool = True
    show_wall_margins: bool = True
    show_colorbar: bool = True
    colormap: str = "viridis"  # viridis, plasma, turbo, inferno, coolwarm, jet
    contour_interval: float = 50.0  # lx
    interpolation_method: str = "linear"  # linear (default), cubic, rbf, nearest
    display_mode: str = "measured"  # "measured", "expected", "difference"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "show_heatmap": self.show_heatmap,
            "show_contours": self.show_contours,
            "show_points": self.show_points,
            "show_values": self.show_values,
            "show_grid": self.show_grid,
            "show_wall_margins": self.show_wall_margins,
            "show_colorbar": self.show_colorbar,
            "colormap": self.colormap,
            "contour_interval": self.contour_interval,
            "interpolation_method": self.interpolation_method,
            "display_mode": self.display_mode,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> VisualizationSettings:
        return cls(
            show_heatmap=bool(data.get("show_heatmap", True)),
            show_contours=bool(data.get("show_contours", True)),
            show_points=bool(data.get("show_points", True)),
            show_values=bool(data.get("show_values", True)),
            show_grid=bool(data.get("show_grid", True)),
            show_wall_margins=bool(data.get("show_wall_margins", True)),
            show_colorbar=bool(data.get("show_colorbar", True)),
            colormap=str(data.get("colormap", "viridis")),
            contour_interval=float(data.get("contour_interval", 50.0)),
            interpolation_method=str(data.get("interpolation_method", "linear")),
            display_mode=str(data.get("display_mode", "measured")),
        )


@dataclass
class LuminationProject:
    """Complete project model containing room parameters, points, and settings.

    Attributes:
        name: Name of the project/room.
        room: Physical room model.
        points: List of all measurement points.
        target_lux: Optional reference/target illuminance for comparison (e.g. 500 lx).
        description: Notes or project description.
        author: Name of surveyor/engineer.
        created_at: ISO timestamp of creation.
        modified_at: ISO timestamp of last modification.
        visualization_settings: Map display preferences.
        file_path: Absolute path to saved file (None if unsaved).
        is_dirty: Flag indicating unsaved modifications.
    """
    name: str = "New Lighting Project"
    room: Room = field(default_factory=lambda: Room(length=6.0, width=4.0, height=2.8))
    points: List[MeasurementPoint] = field(default_factory=list)
    target_lux: Optional[float] = None
    description: str = ""
    author: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    modified_at: str = field(default_factory=lambda: datetime.now().isoformat())
    visualization_settings: VisualizationSettings = field(default_factory=VisualizationSettings)
    file_path: Optional[str] = None
    is_dirty: bool = False
    resume_state: Optional[Dict[str, Any]] = None
    is_practice: bool = False

    def mark_modified(self) -> None:
        """Mark project as containing unsaved changes and update timestamp."""
        self.modified_at = datetime.now().isoformat()
        self.is_dirty = True

    def get_measured_points(self) -> List[MeasurementPoint]:
        """Return list of points that have a recorded lux value."""
        return [p for p in self.points if p.is_measured]

    def get_unmeasured_points(self) -> List[MeasurementPoint]:
        """Return list of points awaiting lux readings."""
        return [p for p in self.points if not p.is_measured]

    def find_point_by_id(self, point_id: str) -> Optional[MeasurementPoint]:
        """Find a point by its ID."""
        for p in self.points:
            if p.id == point_id:
                return p
        return None

    def find_nearest_point(self, x: float, y: float, max_distance: float = 0.5) -> Optional[MeasurementPoint]:
        """Find the closest point to (x, y) within a maximum radius."""
        best_pt: Optional[MeasurementPoint] = None
        min_dist = float("inf")
        for p in self.points:
            d = math.hypot(p.x - x, p.y - y)
            if d < min_dist and d <= max_distance:
                min_dist = d
                best_pt = p
        return best_pt

    def add_custom_point(
        self,
        x: float,
        y: float,
        lux: Optional[float] = None,
        expected_lux: Optional[float] = None,
        point_id: Optional[str] = None,
        notes: str = "Custom point",
    ) -> MeasurementPoint:
        """Add a custom user-placed measurement point with unlocked coordinates."""
        if not self.room.is_inside(x, y):
            raise ValueError(f"Point coordinates ({x:.2f}, {y:.2f}) are outside room boundaries (0..{self.room.length}, 0..{self.room.width}).")

        if not point_id:
            # Generate next available ID
            existing_ids = {p.id for p in self.points}
            idx = 1
            while f"P{idx}" in existing_ids or f"C{idx}" in existing_ids:
                idx += 1
            point_id = f"C{idx}"

        pt = MeasurementPoint(
            id=point_id,
            x=round(x, 4),
            y=round(y, 4),
            lux=lux,
            expected_lux=expected_lux,
            locked_coordinates=False,  # Custom points can be repositioned
            notes=notes,
        )
        self.points.append(pt)
        self.mark_modified()
        return pt

    def remove_point(self, point_id: str) -> bool:
        """Remove a point by ID. Returns True if removed."""
        initial_len = len(self.points)
        self.points = [p for p in self.points if p.id != point_id]
        if len(self.points) != initial_len:
            self.mark_modified()
            return True
        return False

    def clear_all_measurements(self) -> None:
        """Clear lux readings from all points without removing the coordinates."""
        for p in self.points:
            p.clear_reading()
        self.mark_modified()

    def regenerate_grid(
        self,
        mode: str = "count",
        rows: Optional[int] = None,
        cols: Optional[int] = None,
        spacing_x: Optional[float] = None,
        spacing_y: Optional[float] = None,
        wall_margin: Optional[float] = None,
        centered_in_cells: bool = True,
        preserve_existing_readings: bool = False,
        preserve_existing: bool = False,
        traversal_order: Optional[str] = None,
    ) -> None:
        """Regenerate regular grid points for the room."""
        preserve = preserve_existing_readings or preserve_existing
        old_readings: Dict[Tuple[float, float], Tuple[Optional[float], Optional[float]]] = {}
        if preserve:
            for p in self.points:
                old_readings[(round(p.x, 2), round(p.y, 2))] = (p.lux, p.expected_lux)

        new_points = self.room.generate_grid_points(
            mode=mode,
            rows=rows,
            cols=cols,
            spacing_x=spacing_x,
            spacing_y=spacing_y,
            wall_margin=wall_margin,
            centered_in_cells=centered_in_cells,
            traversal_order=traversal_order,
        )

        if preserve:
            for pt in new_points:
                key = (round(pt.x, 2), round(pt.y, 2))
                if key in old_readings:
                    pt.lux, pt.expected_lux = old_readings[key]

        self.points = new_points
        self.mark_modified()

    def to_dict(self) -> Dict[str, Any]:
        """Serialize project to dictionary."""
        data = {
            "format_version": "1.1",
            "name": self.name,
            "description": self.description,
            "author": self.author,
            "is_practice": self.is_practice,
            "created_at": self.created_at,
            "modified_at": self.modified_at,
            "target_lux": self.target_lux,
            "room": self.room.to_dict(),
            "points": [p.to_dict() for p in self.points],
            "visualization_settings": self.visualization_settings.to_dict(),
        }
        if self.resume_state is not None:
            workspace = self.resume_state.get("workspace", "survey")
            if workspace not in ("survey", "review"):
                workspace = "survey"
            selected_id = self.resume_state.get("selected_point_id")
            valid_ids = {point.id for point in self.points}
            if selected_id not in valid_ids:
                selected_id = None
            data["extensions"] = {
                "org.luxious.resume": {
                    "version": 1,
                    "workspace": workspace,
                    "selected_point_id": selected_id,
                }
            }
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> LuminationProject:
        """Create LuminationProject from dictionary."""
        format_version = str(data.get("format_version", "1.0"))
        try:
            major_version = int(format_version.split(".", 1)[0])
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Unsupported project format version: {format_version}") from exc
        if major_version > 1:
            raise ValueError(
                f"Project format {format_version} is newer than this version of Luxious supports. "
                "Update Luxious to open this file."
            )

        room = Room.from_dict(data["room"])
        points = [MeasurementPoint.from_dict(p) for p in data.get("points", [])]
        vis_settings = VisualizationSettings.from_dict(data.get("visualization_settings", {}))
        extensions = data.get("extensions", {})
        if not isinstance(extensions, dict):
            extensions = {}
        extension = extensions.get("org.luxious.resume", {})
        if not isinstance(extension, dict):
            extension = {}
        resume_state = None
        if extension.get("version") == 1:
            workspace = extension.get("workspace", "survey")
            if workspace not in ("survey", "review"):
                workspace = "survey"
            selected_id = extension.get("selected_point_id")
            valid_ids = {point.id for point in points}
            resume_state = {
                "workspace": workspace,
                "selected_point_id": selected_id if selected_id in valid_ids else None,
            }

        return cls(
            name=str(data.get("name", "Unnamed Project")),
            description=str(data.get("description", "")),
            author=str(data.get("author", "")),
            is_practice=bool(data.get("is_practice", False)),
            created_at=str(data.get("created_at", datetime.now().isoformat())),
            modified_at=str(data.get("modified_at", datetime.now().isoformat())),
            target_lux=float(data["target_lux"]) if data.get("target_lux") is not None else None,
            room=room,
            points=points,
            visualization_settings=vis_settings,
            resume_state=resume_state,
        )
