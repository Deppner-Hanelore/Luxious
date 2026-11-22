"""Scientific 2D Illuminance Map & Contour Plotter.

Renders ultra-clean, full-viewport 2D room plans:
- Ultra-tiny, very dark blue point markers (#0a192f)
- Clean false-colour heatmaps and isolux contours
- Edge-to-edge drawing with zero emojis
"""

from __future__ import annotations
import copy
import math
from typing import Optional, List, Tuple, Dict, Any
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle, Polygon
from matplotlib.ticker import FixedLocator, FuncFormatter, MultipleLocator
from matplotlib.figure import Figure
from matplotlib.axes import Axes
from matplotlib.colors import Normalize

from models.project import LuminationProject, VisualizationSettings
from models.measurement import MeasurementPoint
from analysis.interpolation import InterpolationResult, reconstruct_illuminance_field
from analysis.contours import generate_isolux_levels
from analysis.statistics import calculate_statistics
from i18n.translations import tr


def _metre_ticks(size: float) -> List[float]:
    """0, 1, 2, ... metres up to the room size, plus the room size itself when it is not whole."""
    ticks = [float(value) for value in range(0, int(math.floor(size + 1e-9)) + 1)]
    if size - ticks[-1] > 0.05:
        ticks.append(round(float(size), 2))
    return ticks


def _metre_label(value: float, _position=None) -> str:
    if value < -1e-9:
        return ""
    return f"{value:g}"


def render_room_map(
    ax: Axes,
    project: LuminationProject,
    interp_result: Optional[InterpolationResult] = None,
    selected_point_id: Optional[str] = None,
    highlight_min_max: bool = False,
    override_settings: Optional[VisualizationSettings] = None,
    colorbar_ax: Optional[Axes] = None,
    placement_mode: bool = False,
    preview_pos: Optional[Tuple[float, float]] = None,
    snapped_pos: Optional[Tuple[float, float]] = None,
    snap_guides: Optional[List[Tuple[Tuple[float, float], Tuple[float, float]]]] = None,
    snap_label: Optional[str] = None,
) -> Dict[str, Any]:
    """Render full 2D room plan, heatmap, contours, and subtle point markers onto Matplotlib Axes."""
    settings = override_settings or project.visualization_settings
    room = project.room
    points = project.points

    ax.clear()

    display_mode = settings.display_mode
    stats = calculate_statistics(points)

    # 1. Setup physical axes limits and aspect ratio (1m X = 1m Y)
    margin_offset = max(0.20, min(room.length, room.width) * 0.04)
    ax.set_xlim(-margin_offset, room.length + margin_offset)
    ax.set_ylim(-margin_offset, room.width + margin_offset)
    ax.set_aspect("equal", adjustable="box")

    # 2. Draw Room Walls & Floor
    floor_rect = Rectangle(
        (0, 0),
        room.length,
        room.width,
        facecolor="#ffffff",
        edgecolor="#0f172a",
        linewidth=2.0,
        zorder=1,
    )
    ax.add_patch(floor_rect)

    # 3. Compute or use Interpolation
    mesh_handle = None
    contour_handle = None
    clabels_handle = None

    valid_points: List[MeasurementPoint] = []
    if display_mode == "expected":
        valid_points = [
            MeasurementPoint(id=p.id, x=p.x, y=p.y, lux=p.expected_lux, locked_coordinates=p.locked_coordinates)
            for p in points if p.expected_lux is not None
        ]
    elif display_mode == "difference":
        for point in points:
            if point.delta_lux is not None:
                display_point = copy.copy(point)
                display_point.lux = point.delta_lux  # Only the display field may be signed.
                valid_points.append(display_point)
    else:
        valid_points = [p for p in points if p.is_measured and p.lux is not None]

    if not placement_mode and (settings.show_heatmap or settings.show_contours):
        if interp_result is None and len(valid_points) >= 3:
            interp_result = reconstruct_illuminance_field(
                valid_points,
                room,
                resolution=100,
                method=settings.interpolation_method,
                extrapolate_to_walls=True,
                allow_negative=display_mode == "difference",
            )

        if interp_result is not None and interp_result.success and not np.all(np.isnan(interp_result.grid_z)):
            grid_x = interp_result.grid_x
            grid_y = interp_result.grid_y
            grid_z = interp_result.grid_z

            valid_z = grid_z[~np.isnan(grid_z)]
            if len(valid_z) > 0:
                # Colour scale from the real readings only, never from estimated cells.
                measured_values = [float(p.lux) for p in valid_points if p.lux is not None]
                vmin = float(min(measured_values)) if measured_values else float(np.min(valid_z))
                vmax = float(max(measured_values)) if measured_values else float(np.max(valid_z))
                if abs(vmax - vmin) < 1.0:
                    vmax = vmin + 10.0
                norm = Normalize(vmin=vmin, vmax=vmax)

                # Heatmap layer
                if settings.show_heatmap:
                    mesh_handle = ax.pcolormesh(
                        grid_x,
                        grid_y,
                        grid_z,
                        cmap=settings.colormap,
                        norm=norm,
                        shading="auto",
                        alpha=0.88,
                        zorder=3,
                    )

                # Contour layer
                if settings.show_contours:
                    interval = settings.contour_interval
                    levels = generate_isolux_levels(vmin, vmax, interval=interval)
                    if len(levels) > 1:
                        contour_handle = ax.contour(
                            grid_x,
                            grid_y,
                            grid_z,
                            levels=levels,
                            colors="#0f172a",
                            linewidths=0.9,
                            alpha=0.85,
                            zorder=4,
                        )
                        clabels_handle = ax.clabel(
                            contour_handle,
                            inline=True,
                            fontsize=7.5,
                            fmt="%1.0f lx",
                            inline_spacing=6,
                        )

                # Colorbar
                if settings.show_colorbar and mesh_handle is not None and colorbar_ax is not None:
                    colorbar_ax.clear()
                    cb = colorbar_ax.figure.colorbar(mesh_handle, cax=colorbar_ax, orientation="vertical")
                    cb_label = tr("canvas_colorbar_lux") if display_mode != "difference" else tr("canvas_colorbar_delta")
                    cb.set_label(cb_label, fontsize=8, fontweight="bold", color="#334155")
                    cb.ax.tick_params(labelsize=7.5)

    # 4. Dimension rulers & guides in Placement Mode
    if placement_mode:
        if snap_guides:
            for line_start, line_end in snap_guides:
                ax.plot(
                    [line_start[0], line_end[0]],
                    [line_start[1], line_end[1]],
                    color="#2563eb",
                    linestyle="--",
                    linewidth=1.1,
                    alpha=0.85,
                    zorder=15,
                )

        active_pos = snapped_pos or preview_pos
        if active_pos and room.is_inside(active_pos[0], active_pos[1]):
            px, py = active_pos
            ax.plot([0, px], [py, py], color="#3b82f6", linestyle=":", linewidth=0.9, alpha=0.7, zorder=16)
            ax.plot([px, room.length], [py, py], color="#3b82f6", linestyle=":", linewidth=0.9, alpha=0.7, zorder=16)
            ax.plot([px, px], [0, py], color="#3b82f6", linestyle=":", linewidth=0.9, alpha=0.7, zorder=16)
            ax.plot([px, px], [py, room.width], color="#3b82f6", linestyle=":", linewidth=0.9, alpha=0.7, zorder=16)

            preview_circle = Circle(
                (px, py),
                radius=max(0.04, min(room.length, room.width) * 0.008),
                facecolor="#93c5fd",
                edgecolor="#0a192f",
                linewidth=1.5,
                alpha=0.85,
                zorder=20,
            )
            ax.add_patch(preview_circle)

            badge_text = snap_label or f"X: {px:.2f} m, Y: {py:.2f} m"
            ax.annotate(
                badge_text,
                xy=(px, py),
                xytext=(8, 8),
                textcoords="offset points",
                fontsize=8.0,
                fontweight="bold",
                color="#0f172a",
                bbox=dict(boxstyle="round,pad=0.2", fc="#dbeafe", ec="#2563eb", lw=0.9),
                zorder=25,
            )

    # 5. Draw Measurement Points (Even smaller & very dark blue: #0a192f)
    marker_radius = max(0.022, min(room.length, room.width) * 0.0055)

    if settings.show_points or placement_mode:
        for p in points:
            is_selected = (p.id == selected_point_id)

            if p.is_measured and p.lux is not None:
                # Solid ultra-tiny very dark blue dot
                circ = Circle(
                    (p.x, p.y),
                    radius=marker_radius,
                    facecolor="#0a192f" if not is_selected else "#2563eb",
                    edgecolor="#020617",
                    linewidth=0.8,
                    zorder=10,
                )
                ax.add_patch(circ)
            else:
                # Open subtle very dark blue ring
                circ = Circle(
                    (p.x, p.y),
                    radius=marker_radius,
                    facecolor="#ffffff",
                    edgecolor="#0a192f" if not is_selected else "#2563eb",
                    linewidth=0.9,
                    linestyle="--",
                    zorder=10,
                )
                ax.add_patch(circ)

            # Selected point focus ring
            if is_selected:
                glow = Circle(
                    (p.x, p.y),
                    radius=marker_radius * 2.2,
                    facecolor="none",
                    edgecolor="#2563eb",
                    linewidth=1.5,
                    zorder=15,
                )
                ax.add_patch(glow)

    # 5b. Permanent lux labels next to each point (Layers > "Permanent Lux Labels")
    if settings.show_values and not placement_mode:
        for p in valid_points:
            if p.lux is None:
                continue
            label = f"{p.lux:+.0f}" if display_mode == "difference" else f"{p.lux:.0f}"
            ax.annotate(
                label,
                xy=(p.x, p.y),
                xytext=(0, 7),
                textcoords="offset points",
                ha="center",
                va="bottom",
                fontsize=7.5,
                fontweight="bold",
                color="#0f172a",
                bbox=dict(boxstyle="round,pad=0.15", fc="#ffffff", ec="none", alpha=0.75),
                zorder=18,
            )

    # 6. Metric grid: one line per metre, starting at the walls (0), drawn above the floor and the
    # colour map so it stays visible, and only inside the room. Fully hidden when switched off.
    ax.grid(False)
    x_ticks = _metre_ticks(room.length)
    y_ticks = _metre_ticks(room.width)
    if settings.show_grid and not placement_mode:
        for x_value in x_ticks[1:-1]:
            ax.plot([x_value, x_value], [0, room.width], color="#475569", linewidth=0.7, alpha=0.55, zorder=6)
        for y_value in y_ticks[1:-1]:
            ax.plot([0, room.length], [y_value, y_value], color="#475569", linewidth=0.7, alpha=0.55, zorder=6)

    ax.set_xlabel(tr("canvas_x_axis"), fontsize=8.5, fontweight="bold", color="#475569")
    ax.set_ylabel(tr("canvas_y_axis"), fontsize=8.5, fontweight="bold", color="#475569")
    # Axis numbers start at the wall (0) and end at the room size; nothing negative is labelled.
    ax.xaxis.set_major_locator(FixedLocator(x_ticks))
    ax.yaxis.set_major_locator(FixedLocator(y_ticks))
    ax.xaxis.set_major_formatter(FuncFormatter(_metre_label))
    ax.yaxis.set_major_formatter(FuncFormatter(_metre_label))
    ax.xaxis.set_minor_locator(FixedLocator([]))
    ax.yaxis.set_minor_locator(FixedLocator([]))
    ax.tick_params(axis="both", which="major", labelsize=8, colors="#475569")

    # Fallback notice if collinear
    if interp_result is not None and interp_result.is_fallback and interp_result.fallback_reason:
        ax.text(
            0.02,
            0.02,
            tr("canvas_notice", reason=interp_result.fallback_reason),
            transform=ax.transAxes,
            fontsize=7.5,
            color="#475569",
            bbox=dict(boxstyle="round,pad=0.25", fc="#f8fafc", ec="#cbd5e1", lw=0.8, alpha=0.9),
            zorder=30,
        )

    return {
        "mesh": mesh_handle,
        "contours": contour_handle,
        "clabels": clabels_handle,
        "interp_result": interp_result,
    }
