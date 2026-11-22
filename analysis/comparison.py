"""Comparison Analysis Module.

Handles:
1. Comparison with selected target illuminance (user reference value, e.g. 500 lx).
2. Comparison with expected/simulated illuminance (e.g., DIALux simulated model vs real measurements).
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Tuple, Sequence, Dict, Any
import numpy as np

from models.measurement import MeasurementPoint
from i18n.translations import tr


@dataclass
class TargetComparisonResult:
    """Results of comparing measured illuminance against a selected target reference value."""
    target_lux: float
    e_avg: float
    points_evaluated: int
    points_below_target: int
    percentage_below_target: float
    points_above_or_equal_target: int
    percentage_above_or_equal: float
    avg_deviation: float  # Mean of (E_measured - E_target)
    avg_absolute_deviation: float  # Mean of |E_measured - E_target|
    max_positive_deviation: float  # Largest positive surplus
    max_negative_deficit: float  # Largest negative deficit
    max_deficit_point_id: Optional[str]
    max_deficit_point_coords: Optional[Tuple[float, float]]
    summary_text: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target_lux": round(self.target_lux, 2),
            "e_avg": round(self.e_avg, 2),
            "points_evaluated": self.points_evaluated,
            "points_below_target": self.points_below_target,
            "percentage_below_target": round(self.percentage_below_target, 1),
            "points_above_or_equal_target": self.points_above_or_equal_target,
            "percentage_above_or_equal": round(self.percentage_above_or_equal, 1),
            "avg_deviation": round(self.avg_deviation, 2),
            "avg_absolute_deviation": round(self.avg_absolute_deviation, 2),
            "max_positive_deviation": round(self.max_positive_deviation, 2),
            "max_negative_deficit": round(self.max_negative_deficit, 2),
            "max_deficit_point_id": self.max_deficit_point_id,
            "max_deficit_point_coords": self.max_deficit_point_coords,
            "summary_text": self.summary_text,
        }


@dataclass
class PointDelta:
    """Per-point delta between measured and expected illuminance."""
    point_id: str
    x: float
    y: float
    measured_lux: float
    expected_lux: float
    delta_lux: float  # measured - expected
    percentage_diff: float  # (|measured - expected| / expected) * 100


@dataclass
class SimulatedComparisonResult:
    """Results of comparing measured physical points with expected/simulated values."""
    points_evaluated: int
    avg_measured: float
    avg_expected: float
    mean_delta: float  # Mean of (E_meas - E_exp)
    mean_absolute_error: float  # MAE
    root_mean_squared_error: float  # RMSE
    mean_percentage_diff: float  # MAPE
    max_absolute_delta: float
    point_deltas: List[PointDelta]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "points_evaluated": self.points_evaluated,
            "avg_measured": round(self.avg_measured, 2),
            "avg_expected": round(self.avg_expected, 2),
            "mean_delta": round(self.mean_delta, 2),
            "mean_absolute_error": round(self.mean_absolute_error, 2),
            "root_mean_squared_error": round(self.root_mean_squared_error, 2),
            "mean_percentage_diff": round(self.mean_percentage_diff, 2),
            "max_absolute_delta": round(self.max_absolute_delta, 2),
            "point_deltas": [
                {
                    "point_id": pd.point_id,
                    "x": pd.x,
                    "y": pd.y,
                    "measured_lux": pd.measured_lux,
                    "expected_lux": pd.expected_lux,
                    "delta_lux": round(pd.delta_lux, 2),
                    "percentage_diff": round(pd.percentage_diff, 2),
                }
                for pd in self.point_deltas
            ],
        }


def compare_with_target(
    points: Sequence[MeasurementPoint],
    target_lux: float,
) -> Optional[TargetComparisonResult]:
    """Analyze measured points against a user-specified target illuminance.

    Args:
        points: Collection of measurement points.
        target_lux: Target illuminance in lux (> 0).

    Returns:
        TargetComparisonResult or None if no measured points exist.
    """
    if target_lux <= 0:
        return None

    measured = [p for p in points if p.is_measured and p.lux is not None and p.lux >= 0]
    if not measured:
        return None

    n = len(measured)
    lux_values = np.array([p.lux for p in measured], dtype=np.float64)
    deviations = lux_values - target_lux
    abs_deviations = np.abs(deviations)

    below = np.sum(deviations < 0)
    above_eq = n - below

    pct_below = (below / n) * 100.0
    pct_above = (above_eq / n) * 100.0
    e_avg = float(np.mean(lux_values))
    avg_dev = float(np.mean(deviations))
    avg_abs_dev = float(np.mean(abs_deviations))

    max_pos = float(np.max(deviations))
    min_dev = float(np.min(deviations))  # Most negative deficit

    # Find point with worst deficit
    worst_idx = int(np.argmin(deviations))
    worst_pt = measured[worst_idx]

    summary = tr("target_summary", target=f"{target_lux:.0f}", below=below, total=n, pct=f"{pct_below:.1f}")

    return TargetComparisonResult(
        target_lux=target_lux,
        e_avg=e_avg,
        points_evaluated=n,
        points_below_target=int(below),
        percentage_below_target=pct_below,
        points_above_or_equal_target=int(above_eq),
        percentage_above_or_equal=pct_above,
        avg_deviation=avg_dev,
        avg_absolute_deviation=avg_abs_dev,
        max_positive_deviation=max_pos,
        max_negative_deficit=abs(min_dev) if min_dev < 0 else 0.0,
        max_deficit_point_id=worst_pt.id if min_dev < 0 else None,
        max_deficit_point_coords=(worst_pt.x, worst_pt.y) if min_dev < 0 else None,
        summary_text=summary,
    )


def compare_measured_with_simulated(
    points: Sequence[MeasurementPoint],
) -> Optional[SimulatedComparisonResult]:
    """Compare measured physical points against expected/simulated illuminance values.

    Calculates:
    - Delta E = E_measured - E_expected
    - Relative percentage error: (|E_m - E_e| / E_e) * 100
    - MAE and RMSE metrics
    """
    valid_pairs: List[MeasurementPoint] = [
        p for p in points
        if p.is_measured and p.lux is not None and p.expected_lux is not None and p.expected_lux > 0
    ]

    if not valid_pairs:
        return None

    n = len(valid_pairs)
    meas = np.array([p.lux for p in valid_pairs], dtype=np.float64)
    exp = np.array([p.expected_lux for p in valid_pairs], dtype=np.float64)

    deltas = meas - exp
    abs_deltas = np.abs(deltas)
    pct_diffs = (abs_deltas / exp) * 100.0

    point_deltas: List[PointDelta] = []
    for i, p in enumerate(valid_pairs):
        point_deltas.append(
            PointDelta(
                point_id=p.id,
                x=p.x,
                y=p.y,
                measured_lux=float(meas[i]),
                expected_lux=float(exp[i]),
                delta_lux=float(deltas[i]),
                percentage_diff=float(pct_diffs[i]),
            )
        )

    mae = float(np.mean(abs_deltas))
    rmse = float(np.sqrt(np.mean(deltas ** 2)))
    mape = float(np.mean(pct_diffs))
    mean_delta = float(np.mean(deltas))
    max_abs_delta = float(np.max(abs_deltas))

    return SimulatedComparisonResult(
        points_evaluated=n,
        avg_measured=float(np.mean(meas)),
        avg_expected=float(np.mean(exp)),
        mean_delta=mean_delta,
        mean_absolute_error=mae,
        root_mean_squared_error=rmse,
        mean_percentage_diff=mape,
        max_absolute_delta=max_abs_delta,
        point_deltas=point_deltas,
    )


@dataclass
class FileComparisonResult:
    """Your survey compared point by point with another survey or table of the same grid."""

    points_compared: int
    compared_avg: float
    current_avg: float
    difference_lux: float        # current - compared (average)
    difference_pct: float        # difference relative to the compared file
    depreciation_pct: float      # (compared - current) / compared * 100; 0 when the light did not drop
    has_depreciation: bool       # False when the survey is equal to or brighter than the compared file


def compare_with_file(points: Sequence[MeasurementPoint]) -> Optional[FileComparisonResult]:
    """Compare readings with the compared-file values stored on the same points.

    Only points with a reading in both are used; nothing is estimated.
    """
    pairs = [
        (float(p.lux), float(p.expected_lux))
        for p in points
        if p.is_measured and p.lux is not None and p.expected_lux is not None
    ]
    if not pairs:
        return None
    current_avg = float(np.mean([current for current, _ in pairs]))
    compared_avg = float(np.mean([compared for _, compared in pairs]))
    difference = current_avg - compared_avg
    if compared_avg <= 0:
        return None
    difference_pct = difference / compared_avg * 100.0
    has_depreciation = difference < 0
    return FileComparisonResult(
        points_compared=len(pairs),
        compared_avg=compared_avg,
        current_avg=current_avg,
        difference_lux=difference,
        difference_pct=difference_pct,
        depreciation_pct=-difference_pct if has_depreciation else 0.0,
        has_depreciation=has_depreciation,
    )
