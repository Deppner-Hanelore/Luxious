"""Non-Destructive Spatial Outlier Awareness.

Analyzes physical measurement points and detects suspicious localized spikes or drops
relative to spatial neighbours without modifying or deleting user data.
"""

from __future__ import annotations
import math
from typing import List, Sequence, Tuple
import numpy as np

from models.measurement import MeasurementPoint
from i18n.translations import tr
from models.room import Room


def evaluate_spatial_outliers(
    points: Sequence[MeasurementPoint],
    room: Room,
    neighbour_radius: Optional[float] = None,
    relative_threshold: float = 0.50,  # Flag if differs > 50% from local median
) -> List[MeasurementPoint]:
    """Identify potential spatial outliers in physical lux readings non-destructively.

    Args:
        points: Collection of measurement points.
        room: Physical room model.
        neighbour_radius: Max distance to consider as a local neighbour (defaults to ~1.8 * grid spacing).
        relative_threshold: Relative fractional difference threshold from neighbour median.

    Returns:
        List of points flagged as possible outliers.
    """
    measured = [p for p in points if p.is_measured and p.lux is not None and p.lux >= 0]
    if len(measured) < 4:
        # Not enough points for reliable spatial outlier detection
        for p in points:
            p.is_possible_outlier = False
            p.outlier_reason = ""
        return []

    # Estimate typical spacing from room dimensions
    est_spacing = max(0.5, math.sqrt(room.area / len(points)))
    radius = neighbour_radius or (est_spacing * 1.85)

    flagged: List[MeasurementPoint] = []

    for p in measured:
        # Find neighbours within radius (excluding self)
        neighbours: List[MeasurementPoint] = []
        for other in measured:
            if other.id != p.id:
                dist = math.hypot(p.x - other.x, p.y - other.y)
                if dist <= radius:
                    neighbours.append(other)

        if len(neighbours) >= 2:
            neighbour_lux = np.array([n.lux for n in neighbours], dtype=np.float64)
            local_median = float(np.median(neighbour_lux))
            local_mean = float(np.mean(neighbour_lux))
            local_std = float(np.std(neighbour_lux, ddof=1)) if len(neighbours) > 2 else 0.0

            if local_median > 0:
                rel_diff = abs(p.lux - local_median) / local_median
                diff_lux = p.lux - local_median

                # Check if exceeds relative threshold and absolute threshold (> 100 lx)
                if rel_diff >= relative_threshold and abs(diff_lux) >= 75.0:
                    p.is_possible_outlier = True
                    direction = tr("outlier_direction_higher") if diff_lux > 0 else tr("outlier_direction_lower")
                    p.outlier_reason = tr(
                        "outlier_relative", lux=f"{p.lux:.0f}", pct=f"{abs(rel_diff)*100:.0f}",
                        direction=direction, count=len(neighbours), median=f"{local_median:.0f}",
                    )
                    flagged.append(p)
                elif local_std > 0 and abs(p.lux - local_mean) > 2.8 * local_std and abs(diff_lux) >= 75.0:
                    p.is_possible_outlier = True
                    p.outlier_reason = tr(
                        "outlier_local", lux=f"{p.lux:.0f}", mean=f"{local_mean:.0f}", std=f"{local_std:.1f}",
                    )
                    flagged.append(p)
                else:
                    p.is_possible_outlier = False
                    p.outlier_reason = ""
            else:
                p.is_possible_outlier = False
                p.outlier_reason = ""
        else:
            p.is_possible_outlier = False
            p.outlier_reason = ""

    return flagged
