"""Room Geometry and Coordinate Space Model.

Defines a rectangular physical room with real dimensions (length, width, height),
working plane height, wall boundary margins, and top-to-bottom serpentine measurement grid generation.
"""

from __future__ import annotations
import math
from typing import List, Optional, Tuple, Dict, Any
import numpy as np

from models.measurement import MeasurementPoint


class Room:
    """Rectangular room physical model with coordinate space definition."""

    def __init__(
        self,
        name: str = "Room 1",
        length: float = 6.0,
        width: float = 4.0,
        height: float = 2.80,
        measurement_plane_height: float = 0.75,
        wall_margin: float = 0.50,
        grid_rows: int = 3,
        grid_cols: int = 4,
        grid_spacing_x: Optional[float] = None,
        grid_spacing_y: Optional[float] = None,
        traversal_order: str = "serpentine",
    ) -> None:
        self.name = name
        self.length = max(0.1, float(length))
        self.width = max(0.1, float(width))
        self.height = max(0.5, float(height))
        self.measurement_plane_height = max(0.0, float(measurement_plane_height))
        self.wall_margin = max(0.0, float(wall_margin))

        self.grid_rows = max(1, int(grid_rows))
        self.grid_cols = max(1, int(grid_cols))
        self.grid_spacing_x = float(grid_spacing_x) if grid_spacing_x is not None else None
        self.grid_spacing_y = float(grid_spacing_y) if grid_spacing_y is not None else None
        self.traversal_order = traversal_order

    @property
    def area(self) -> float:
        """Floor surface area in square meters."""
        return self.length * self.width

    @property
    def effective_area(self) -> float:
        """Survey measurement area in square meters excluding wall margins."""
        eff_l = max(0.0, self.length - 2.0 * self.wall_margin)
        eff_w = max(0.0, self.width - 2.0 * self.wall_margin)
        return eff_l * eff_w

    @property
    def room_index_k(self) -> float:
        """Room Index k = (L * W) / (H_work * (L + W))."""
        h_work = max(0.1, self.height - self.measurement_plane_height)
        return (self.length * self.width) / (h_work * (self.length + self.width))

    @property
    def en12464_recommended_points(self) -> int:
        """Calculate EN 12464-1 recommended minimum grid points based on room index."""
        k = self.room_index_k
        if k < 1.0:
            return 9  # 3x3
        elif k < 2.0:
            return 16  # 4x4
        elif k < 3.0:
            return 25  # 5x5
        else:
            return 36  # 6x6

    @property
    def effective_length(self) -> float:
        """Length of measurement area excluding wall margins."""
        return max(0.1, self.length - 2.0 * self.wall_margin)

    @property
    def effective_width(self) -> float:
        """Width of measurement area excluding wall margins."""
        return max(0.1, self.width - 2.0 * self.wall_margin)

    def is_inside(self, x: float, y: float) -> bool:
        """Check if coordinates (x, y) are inside the physical room boundaries."""
        return 0.0 <= x <= self.length and 0.0 <= y <= self.width

    def generate_grid_points(
        self,
        mode: str = "count",
        rows: Optional[int] = None,
        cols: Optional[int] = None,
        spacing_x: Optional[float] = None,
        spacing_y: Optional[float] = None,
        wall_margin: Optional[float] = None,
        centered_in_cells: bool = False,
        traversal_order: Optional[str] = None,
    ) -> List[MeasurementPoint]:
        """Generate a regular grid of measurement points with top-to-bottom snake/serpentine walking traversal.

        Row 1 (Top visual row, Y_max): Left to Right
        Row 2 (Middle visual row, Y_mid): Right to Left (immediately below Row 1)
        Row 3 (Bottom visual row, Y_min): Left to Right (immediately below Row 2)
        """
        margin = self.wall_margin if wall_margin is None else float(wall_margin)
        if margin * 2 >= self.length or margin * 2 >= self.width:
            margin = 0.0

        eff_len = self.length - 2.0 * margin
        eff_wid = self.width - 2.0 * margin

        if mode == "spacing":
            sx = spacing_x or self.grid_spacing_x or 1.0
            sy = spacing_y or self.grid_spacing_y or sx
            sx = max(0.05, float(sx))
            sy = max(0.05, float(sy))

            # Points on the wall-distance line: N spacings need N + 1 points.
            extra = 0 if centered_in_cells else 1
            n_cols = max(1, min(100, int(round(eff_len / sx)) + extra))
            n_rows = max(1, min(100, int(round(eff_wid / sy)) + extra))
        else:
            n_rows = max(1, min(100, int(rows or self.grid_rows)))
            n_cols = max(1, min(100, int(cols or self.grid_cols)))

        # Sanity cap
        if n_rows * n_cols > 2500:
            n_rows = min(50, n_rows)
            n_cols = min(50, n_cols)

        self.grid_rows = n_rows
        self.grid_cols = n_cols
        self.wall_margin = margin
        order = traversal_order or self.traversal_order

        points: List[MeasurementPoint] = []
        point_idx = 1

        if centered_in_cells:
            # Points located at centers of equal sub-cells
            dx = eff_len / n_cols
            dy = eff_wid / n_rows
            xs = [margin + (i + 0.5) * dx for i in range(n_cols)]
            # Generate Ys descending from TOP (Y_max) down to BOTTOM (Y_min)
            ys = [margin + (n_rows - 1 - j + 0.5) * dy for j in range(n_rows)]
        else:
            # Points located at grid intersections
            if n_cols == 1:
                xs = [margin + eff_len / 2.0]
            else:
                xs = np.linspace(margin, self.length - margin, n_cols).tolist()

            if n_rows == 1:
                ys = [margin + eff_wid / 2.0]
            else:
                # Descending from top wall to bottom wall
                ys = np.linspace(self.width - margin, margin, n_rows).tolist()

        # Generate points visual row by visual row (Top to Bottom)
        for j, y_val in enumerate(ys):
            # Row index j: 0 = Top row (Row 1), 1 = Next row down (Row 2), 2 = Bottom row (Row 3)
            if order == "serpentine" and (j % 2 == 1):
                # Row 2 (j=1): Right to Left
                cur_xs = list(reversed(xs))
                col_indices = list(reversed(range(len(xs))))
            else:
                # Row 1 (j=0), Row 3 (j=2): Left to Right
                cur_xs = list(xs)
                col_indices = list(range(len(xs)))

            for k, x_val in enumerate(cur_xs):
                col_i = col_indices[k]
                pt = MeasurementPoint(
                    id=f"P{point_idx}",
                    x=round(float(x_val), 4),
                    y=round(float(y_val), 4),
                    lux=None,
                    expected_lux=None,
                    locked_coordinates=True,
                    notes=f"Grid (Col {col_i+1}, Row {j+1})",
                )
                points.append(pt)
                point_idx += 1

        return points

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "length": self.length,
            "width": self.width,
            "height": self.height,
            "measurement_plane_height": self.measurement_plane_height,
            "wall_margin": self.wall_margin,
            "grid_rows": self.grid_rows,
            "grid_cols": self.grid_cols,
            "grid_spacing_x": self.grid_spacing_x,
            "grid_spacing_y": self.grid_spacing_y,
            "traversal_order": self.traversal_order,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Room:
        return cls(
            name=data.get("name", "Room 1"),
            length=data.get("length", 6.0),
            width=data.get("width", 4.0),
            height=data.get("height", 2.80),
            measurement_plane_height=data.get("measurement_plane_height", 0.75),
            wall_margin=data.get("wall_margin", 0.50),
            grid_rows=data.get("grid_rows", 3),
            grid_cols=data.get("grid_cols", 4),
            grid_spacing_x=data.get("grid_spacing_x"),
            grid_spacing_y=data.get("grid_spacing_y"),
            traversal_order=data.get("traversal_order", "serpentine"),
        )
