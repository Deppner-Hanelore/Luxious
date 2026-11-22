"""Chart Plotter for Illuminance Distribution and Target Compliance.

Generates auxiliary analytical plots for the dashboard and PDF reports:
- Illuminance frequency histogram and KDE distribution curve
- Target compliance breakdown bar chart
- Measured vs. Simulated scatter & deviation plot
"""

from __future__ import annotations
from typing import Optional, Sequence
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.figure import Figure

from models.measurement import MeasurementPoint
from analysis.statistics import calculate_statistics
from analysis.comparison import TargetComparisonResult, SimulatedComparisonResult
from i18n.translations import tr


def render_distribution_histogram(
    ax: Axes,
    points: Sequence[MeasurementPoint],
    target_lux: Optional[float] = None,
) -> None:
    """Render illuminance frequency distribution histogram with mean and target markers."""
    ax.clear()
    measured = [p for p in points if p.is_measured and p.lux is not None and p.lux >= 0]
    if not measured:
        ax.text(0.5, 0.5, tr("chart_no_data"), ha="center", va="center", color="#94a3b8")
        return

    lux_vals = np.array([p.lux for p in measured], dtype=np.float64)
    stats = calculate_statistics(measured)

    n_bins = max(5, min(15, int(len(lux_vals) / 2)))
    counts, bins, patches = ax.hist(
        lux_vals,
        bins=n_bins,
        color="#3b82f6",
        edgecolor="#1d4ed8",
        alpha=0.75,
        rwidth=0.85,
    )

    if stats:
        ax.axvline(
            stats.e_avg,
            color="#2563eb",
            linestyle="--",
            linewidth=2.0,
            label=tr("chart_avg", value=f"{stats.e_avg:.0f}"),
        )
        ax.axvline(
            stats.median,
            color="#0891b2",
            linestyle=":",
            linewidth=1.8,
            label=tr("chart_median", value=f"{stats.median:.0f}"),
        )

    if target_lux and target_lux > 0:
        ax.axvline(
            target_lux,
            color="#dc2626",
            linestyle="-",
            linewidth=2.0,
            label=tr("chart_target", value=f"{target_lux:.0f}"),
        )

    ax.set_xlabel(tr("chart_x_lux"), fontsize=9, fontweight="bold", color="#334155")
    ax.set_ylabel(tr("chart_y_count"), fontsize=9, fontweight="bold", color="#334155")
    ax.set_title(tr("chart_distribution"), fontsize=10, fontweight="bold", color="#0f172a")
    ax.legend(fontsize=8, loc="upper right")
    ax.grid(True, linestyle=":", alpha=0.5)


def render_target_compliance_bar(
    ax: Axes,
    comparison: TargetComparisonResult,
) -> None:
    """Render horizontal stacked bar chart showing points above vs below target."""
    ax.clear()
    pct_below = comparison.percentage_below_target
    pct_above = comparison.percentage_above_or_equal

    ax.barh(
        [0],
        [pct_below],
        color="#ef4444",
        edgecolor="#b91c1c",
        height=0.45,
        label=tr("chart_below", pct=f"{pct_below:.1f}"),
    )
    ax.barh(
        [0],
        [pct_above],
        left=[pct_below],
        color="#22c55e",
        edgecolor="#15803d",
        height=0.45,
        label=tr("chart_above", pct=f"{pct_above:.1f}"),
    )

    ax.set_xlim(0, 100)
    ax.set_yticks([])
    ax.set_xlabel(tr("chart_pct_points"), fontsize=9, color="#334155")
    ax.set_title(
        tr("chart_compliance", target=f"{comparison.target_lux:.0f}", above=comparison.points_above_or_equal_target, total=comparison.points_evaluated),
        fontsize=10,
        fontweight="bold",
        color="#0f172a",
    )
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, -0.45), ncol=2, fontsize=8)
    ax.grid(True, axis="x", linestyle=":", alpha=0.5)
