"""2D Numerical Interpolation for Illuminance Distribution.

Performs scientific spatial reconstruction over a 2D room plane from physical measurement points.
Supports:
- Linear interpolation (Default)
- Cubic spline interpolation
- Thin-plate Radial Basis Functions (RBF)
- Nearest-neighbour interpolation

Includes robust edge case handling (collinear points, duplicate coordinates, sparse data)
and distinct fallback reporting.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Tuple, Sequence
import numpy as np

from models.measurement import MeasurementPoint
from models.room import Room


@dataclass
class InterpolationResult:
    """Encapsulates the result of a 2D spatial interpolation."""
    grid_x: np.ndarray
    grid_y: np.ndarray
    grid_z: np.ndarray  # 2D array of interpolated illuminance (lux) with NaNs outside convex hull
    method_requested: str
    method_used: str
    is_fallback: bool
    fallback_reason: Optional[str]
    num_points_used: int
    success: bool
    error_message: Optional[str] = None
    convex_hull_points: Optional[np.ndarray] = None

    @property
    def valid_mask(self) -> np.ndarray:
        """Boolean mask indicating regions with valid interpolated values (non-NaN)."""
        return ~np.isnan(self.grid_z)


def _check_collinearity(points_xy: np.ndarray, tol: float = 1e-4) -> bool:
    """Check if all points lie approximately on a straight line."""
    if len(points_xy) < 3:
        return True
    # Center points
    centered = points_xy - np.mean(points_xy, axis=0)
    # SVD
    _, s, _ = np.linalg.svd(centered)
    # If smaller singular value is very small relative to the larger, points are collinear
    if len(s) > 1 and s[1] < tol * max(s[0], 1.0):
        return True
    return False


def _merge_duplicate_points(points: Sequence[MeasurementPoint], tol: float = 0.005, allow_negative: bool = False) -> Tuple[np.ndarray, np.ndarray, List[str]]:
    """Merge duplicate coordinates by averaging their lux values.

    Returns:
        (xy_array, lux_array, point_ids)
    """
    merged_xy: List[Tuple[float, float]] = []
    merged_lux: List[float] = []
    merged_ids: List[str] = []

    for p in points:
        if not p.is_measured or p.lux is None or not np.isfinite(p.lux) or (p.lux < 0 and not allow_negative):
            continue

        # Check if already in merged
        found_idx = -1
        for i, (mx, my) in enumerate(merged_xy):
            if abs(p.x - mx) <= tol and abs(p.y - my) <= tol:
                found_idx = i
                break

        if found_idx >= 0:
            # Average duplicate
            old_val = merged_lux[found_idx]
            merged_lux[found_idx] = (old_val + p.lux) / 2.0
            merged_ids[found_idx] += f", {p.id}"
        else:
            merged_xy.append((p.x, p.y))
            merged_lux.append(p.lux)
            merged_ids.append(p.id)

    if not merged_xy:
        return np.empty((0, 2)), np.empty(0), []

    return np.array(merged_xy, dtype=np.float64), np.array(merged_lux, dtype=np.float64), merged_ids


def reconstruct_illuminance_field(
    points: Sequence[MeasurementPoint],
    room: Room,
    resolution: int = 150,
    method: str = "linear",
    extrapolate_to_walls: bool = False,
    allow_negative: bool = False,
) -> InterpolationResult:
    """Numerically reconstruct the continuous 2D illuminance distribution across the room.

    Args:
        points: Collection of measurement points.
        room: Physical room model defining boundaries.
        resolution: Number of grid sampling points along the longest room dimension.
        method: Requested method: "linear" (default), "cubic", "rbf", or "nearest".
        extrapolate_to_walls: If False, values outside the convex hull of measured points are NaN.
        allow_negative: Preserve signed values for difference maps only.

    Returns:
        InterpolationResult containing the meshgrid, interpolated lux values, and metadata.
    """
    from scipy.interpolate import griddata, RBFInterpolator
    from scipy.spatial import ConvexHull, Delaunay

    # 1. Prepare dense sampling grid over the room [0, length] x [0, width]
    res_x = max(20, min(200, resolution))
    aspect = room.width / max(0.01, room.length)
    res_y = max(20, min(200, int(round(resolution * aspect))))

    gx = np.linspace(0.0, room.length, res_x)
    gy = np.linspace(0.0, room.width, res_y)
    grid_x, grid_y = np.meshgrid(gx, gy)

    # 2. Extract and sanitize measured points
    xy, lux, _ = _merge_duplicate_points(points, allow_negative=allow_negative)
    n_pts = len(lux)

    if n_pts == 0:
        return InterpolationResult(
            grid_x=grid_x,
            grid_y=grid_y,
            grid_z=np.full_like(grid_x, np.nan),
            method_requested=method,
            method_used="none",
            is_fallback=False,
            fallback_reason="No measured points available.",
            num_points_used=0,
            success=False,
            error_message="No measured illuminance readings entered.",
        )

    # 3. Handle single point case
    if n_pts == 1:
        # Constant field or single point display
        grid_z = np.full_like(grid_x, np.nan)
        # Only valid at the exact point or small radius
        return InterpolationResult(
            grid_x=grid_x,
            grid_y=grid_y,
            grid_z=grid_z,
            method_requested=method,
            method_used="single_point",
            is_fallback=True,
            fallback_reason="Only 1 measurement point is recorded; minimum 3 non-collinear points required for 2D field.",
            num_points_used=1,
            success=True,
        )

    # 4. Handle two points case
    if n_pts == 2:
        return InterpolationResult(
            grid_x=grid_x,
            grid_y=grid_y,
            grid_z=np.full_like(grid_x, np.nan),
            method_requested=method,
            method_used="sparse_2pt",
            is_fallback=True,
            fallback_reason="Only 2 measurement points recorded; at least 3 non-collinear points needed for 2D contour reconstruction.",
            num_points_used=2,
            success=True,
        )

    # 5. Check collinearity or degenerate geometry
    is_collinear = _check_collinearity(xy)
    if is_collinear:
        # Do not fabricate an unphysical 2D gradient for collinear data
        grid_z = np.full_like(grid_x, np.nan)
        return InterpolationResult(
            grid_x=grid_x,
            grid_y=grid_y,
            grid_z=grid_z,
            method_requested=method,
            method_used="none",
            is_fallback=True,
            fallback_reason="A 2D illuminance field cannot be reconstructed from the current measurement geometry. Add measurements at non-collinear positions.",
            num_points_used=n_pts,
            success=False,
            error_message="A 2D illuminance field cannot be reconstructed from the current measurement geometry. Add measurements at non-collinear positions.",
        )

    # 6. Convex hull computation to prevent unphysical extrapolation
    hull_pts = None
    try:
        if n_pts >= 3:
            hull = ConvexHull(xy)
            hull_pts = xy[hull.vertices]
    except Exception:
        hull_pts = None

    # 7. Perform requested interpolation
    req_method = method.lower().strip()
    used_method = req_method
    is_fallback = False
    fallback_reason = None
    grid_z = np.full_like(grid_x, np.nan)

    # If cubic requested but < 4 points or Delaunay fails
    if req_method == "cubic":
        if n_pts < 4:
            used_method = "linear"
            is_fallback = True
            fallback_reason = "Cubic interpolation requires at least 4 points; fell back to Linear."
        else:
            try:
                grid_z = griddata(xy, lux, (grid_x, grid_y), method="cubic")
                # Cubic griddata can produce NaN near hull edges; fill internal NaNs with linear
                if not extrapolate_to_walls:
                    lin_z = griddata(xy, lux, (grid_x, grid_y), method="linear")
                    nan_mask = np.isnan(grid_z) & (~np.isnan(lin_z))
                    grid_z[nan_mask] = lin_z[nan_mask]
            except Exception as e:
                used_method = "linear"
                is_fallback = True
                fallback_reason = f"Cubic interpolation failed ({e}); fell back to Linear."

    if used_method == "rbf":
        try:
            # Thin-plate spline RBF
            rbf = RBFInterpolator(xy, lux, kernel="thin_plate_spline", smoothing=0.0)
            pts_eval = np.column_stack([grid_x.ravel(), grid_y.ravel()])
            z_eval = rbf(pts_eval).reshape(grid_x.shape)
            grid_z = z_eval if allow_negative else np.clip(z_eval, 0.0, None)

            # If not extrapolating to walls, mask outside convex hull
            if not extrapolate_to_walls and hull_pts is not None:
                delaunay = Delaunay(xy)
                in_hull = delaunay.find_simplex(pts_eval) >= 0
                grid_z[~in_hull.reshape(grid_x.shape)] = np.nan
        except Exception as e:
            used_method = "linear"
            is_fallback = True
            fallback_reason = f"RBF interpolation failed ({e}); fell back to Linear."

    if used_method == "linear":
        try:
            grid_z = griddata(xy, lux, (grid_x, grid_y), method="linear")
            if not allow_negative:
                grid_z = np.clip(grid_z, 0.0, None)
        except Exception as e:
            used_method = "nearest"
            is_fallback = True
            fallback_reason = f"Linear interpolation failed ({e}); fell back to Nearest."

    if used_method == "nearest":
        try:
            grid_z = griddata(xy, lux, (grid_x, grid_y), method="nearest")
            if not allow_negative:
                grid_z = np.clip(grid_z, 0.0, None)
        except Exception as e:
            return InterpolationResult(
                grid_x=grid_x,
                grid_y=grid_y,
                grid_z=np.full_like(grid_x, np.nan),
                method_requested=method,
                method_used="failed",
                is_fallback=True,
                fallback_reason=str(e),
                num_points_used=n_pts,
                success=False,
                error_message=f"Interpolation computation failed: {e}",
            )

    return InterpolationResult(
        grid_x=grid_x,
        grid_y=grid_y,
        grid_z=grid_z,
        method_requested=method,
        method_used=used_method,
        is_fallback=is_fallback,
        fallback_reason=fallback_reason,
        num_points_used=n_pts,
        success=True,
        convex_hull_points=hull_pts,
    )
