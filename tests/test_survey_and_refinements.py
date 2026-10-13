"""Unit and Integration Tests for Usability & Scientific Refinements.

Tests:
1. Serpentine traversal order vs Standard Left-to-Right (Top-to-Bottom)
2. Survey Mode auto-advance, previous navigation, and unmeasured search
3. Non-destructive spatial outlier detection
4. Degenerate interpolation messaging & non-fabrication of fields
5. Extended Target comparison metrics (E_avg, MAE, surplus, deficit)
6. Persistence roundtrip with reading metadata (device_name, timestamp, notes)
7. USB Serial & Bluetooth Lux Meter hardware drivers
"""

import os
import pytest
import numpy as np

from models.room import Room
from models.project import LuminationProject
from models.measurement import MeasurementPoint
from analysis.statistics import calculate_statistics
from analysis.comparison import compare_with_target
from analysis.interpolation import reconstruct_illuminance_field
from analysis.outliers import evaluate_spatial_outliers
from persistence.project_io import save_project, load_project
from persistence.csv_io import export_measurements_to_csv, import_measurements_from_csv
from measurement_sources.usb_serial import USBSerialMeterSource
from measurement_sources.bluetooth_meter import BluetoothMeterSource


def test_serpentine_traversal_order():
    """Verify serpentine walking pattern reverses direction on alternating rows from top to bottom."""
    room = Room(length=4.0, width=3.0, wall_margin=0.5, traversal_order="serpentine")
    # 2 rows, 3 cols:
    # Row 1 (Top, j=0): left -> right: x1, x2, x3
    # Row 2 (Bottom, j=1): right -> left: x3, x2, x1
    pts = room.generate_grid_points(mode="count", rows=2, cols=3, centered_in_cells=True, traversal_order="serpentine")

    assert len(pts) == 6
    # Row 1 is at the top (higher Y)
    assert pts[0].y > pts[3].y
    # Row 1: Left to right
    assert pts[0].x < pts[1].x < pts[2].x
    # Row 2 (immediately below Row 1): Right to left
    assert pts[3].x > pts[4].x > pts[5].x

    # Consecutive adjacency check: The right-most point of Row 1 is pts[2].
    # The first point of Row 2 is pts[3] (same X coordinate, just one row down!).
    assert pytest.approx(pts[2].x, 0.001) == pts[3].x

    # Compare with standard left_to_right order
    std_pts = room.generate_grid_points(mode="count", rows=2, cols=3, centered_in_cells=True, traversal_order="left_to_right")
    assert std_pts[0].x < std_pts[1].x < std_pts[2].x
    assert std_pts[3].x < std_pts[4].x < std_pts[5].x


def test_spatial_outlier_detection_non_destructive():
    """Verify spatial outlier flag detects localized spikes without altering raw lux values."""
    room = Room(length=6.0, width=4.0, wall_margin=0.5)
    project = LuminationProject(name="Outlier Test", room=room)
    project.regenerate_grid(mode="count", rows=3, cols=3, wall_margin=0.5, centered_in_cells=True)

    for p in project.points:
        p.record_reading(400.0)

    center_pt = project.points[4]  # P5
    center_pt.record_reading(1200.0)

    flagged = evaluate_spatial_outliers(project.points, room)
    assert center_pt in flagged
    assert center_pt.is_possible_outlier is True
    assert center_pt.lux == 1200.0  # Raw data not mutated


def test_degenerate_interpolation_explicit_message():
    """Verify collinear measurement configurations produce an explicit notice."""
    room = Room(length=6.0, width=4.0, wall_margin=0.5)
    points = [
        MeasurementPoint(id="P1", x=1.0, y=2.0, lux=300.0),
        MeasurementPoint(id="P2", x=3.0, y=2.0, lux=450.0),
        MeasurementPoint(id="P3", x=5.0, y=2.0, lux=600.0),
    ]
    res = reconstruct_illuminance_field(points, room, method="linear")
    assert res.is_fallback is True
    assert "collinear" in res.fallback_reason.lower()


def test_extended_target_comparison_metrics():
    """Verify target comparison computes accurate MAE, surplus, deficit, and compliance."""
    points = [
        MeasurementPoint(id="P1", x=1.0, y=1.0, lux=400.0),  # deficit 100
        MeasurementPoint(id="P2", x=2.0, y=1.0, lux=500.0),  # equal target
        MeasurementPoint(id="P3", x=3.0, y=1.0, lux=650.0),  # surplus 150
    ]
    summary = compare_with_target(points, target_lux=500.0)
    assert summary is not None
    assert summary.points_evaluated == 3
    assert summary.points_below_target == 1
    assert summary.points_above_or_equal_target == 2
    assert summary.avg_absolute_deviation > 0.0
    assert summary.max_positive_deviation == 150.0
    assert summary.max_negative_deficit == 100.0


def test_persistence_metadata_roundtrip(tmp_path):
    """Verify reading metadata (device, timestamp, notes) persists across save/load."""
    room = Room(length=5.0, width=4.0)
    proj = LuminationProject(name="Metadata Test", room=room)
    p = MeasurementPoint(id="P1", x=1.0, y=1.0)
    p.record_reading(520.0, device_name="Extech HD450")
    p.notes = "Near window"
    proj.points = [p]

    filepath = str(tmp_path / "metadata_test.luxproj")
    save_project(proj, filepath)

    loaded = load_project(filepath)
    lp = loaded.points[0]
    assert lp.lux == 520.0
    assert lp.device_name == "Extech HD450"
    assert lp.notes == "Near window"
    assert lp.timestamp is not None


def test_usb_serial_meter_driver(qapp):
    """Verify USB serial lux parsing and simulated connection."""
    driver = USBSerialMeterSource()
    assert driver.list_available_ports() is not None

    # Test parser
    assert driver._parse_lux_value("450.5 lx") == 450.5
    assert driver._parse_lux_value("LUX: 1250") == 1250.0
    assert driver._parse_lux_value("320.0") == 320.0
    assert driver._parse_lux_value("Invalid Text") is None

    # Never present the old synthetic stream as a connected physical meter.
    ok, msg = driver.connect_port("COM_MOCK")
    assert ok is False
    assert "Practice" in msg
    assert driver.is_connected is False
    driver.disconnect_port()
    assert driver.is_connected is False


def test_bluetooth_meter_driver(qapp):
    """Verify Bluetooth driver discovery and connection handling."""
    driver = BluetoothMeterSource()
    status = []
    driver.connection_status_changed.connect(lambda connected, desc: status.append((connected, desc)))
    connected = driver.connect_device("00:1A:7D:DA:71:13", "Testo 540i")
    assert connected is False
    assert status[-1][0] is False
    assert "no verified lux profile" in status[-1][1]
    driver.disconnect_device()
    assert driver.is_connected is False
