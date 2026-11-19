"""Measurement Point Data Model with Metadata and Non-Destructive Outlier Flagging.

Represents an individual physical measurement location in real-world meter coordinates.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any


@dataclass
class MeasurementPoint:
    """Represents a single illuminance measurement point inside a room.

    Attributes:
        id: Unique identifier for the point (e.g. "P1", "P2").
        x: X-coordinate in real meters (measured from room origin, 0 <= x <= room.length).
        y: Y-coordinate in real meters (measured from room origin, 0 <= y <= room.width).
        lux: Measured illuminance in lux (physical reading). None if unmeasured.
        expected_lux: Optional expected/simulated illuminance (e.g. from DIALux).
        locked_coordinates: True if coordinates are fixed (default for grid points).
        notes: Optional text notes for this location.
        timestamp: ISO timestamp of when the measurement was recorded.
        device_name: Optional name of the physical lux meter instrument.
        is_possible_outlier: Flag set when reading differs significantly from spatial neighbours.
        outlier_reason: Descriptive explanation of why the reading was flagged.
    """
    id: str
    x: float
    y: float
    lux: Optional[float] = None
    expected_lux: Optional[float] = None
    locked_coordinates: bool = True
    notes: str = ""
    timestamp: Optional[str] = None
    device_name: Optional[str] = None
    source_sample_id: Optional[str] = None
    source_profile_id: Optional[str] = None
    is_possible_outlier: bool = False
    outlier_reason: str = ""

    def __post_init__(self) -> None:
        self.x = float(self.x)
        self.y = float(self.y)
        if self.lux is not None:
            self.lux = float(self.lux)
            if self.lux < 0:
                raise ValueError(f"Illuminance cannot be negative: {self.lux} lx")
        if self.expected_lux is not None:
            self.expected_lux = float(self.expected_lux)
            if self.expected_lux < 0:
                raise ValueError(f"Expected illuminance cannot be negative: {self.expected_lux} lx")

    @property
    def is_measured(self) -> bool:
        """Return True if a valid physical lux reading has been recorded."""
        return self.lux is not None

    @property
    def delta_lux(self) -> Optional[float]:
        """Calculate difference between measured and expected illuminance: E_measured - E_expected."""
        if self.lux is not None and self.expected_lux is not None:
            return self.lux - self.expected_lux
        return None

    @property
    def percentage_diff(self) -> Optional[float]:
        """Calculate relative percentage difference from expected value (|E_m - E_e| / E_e) * 100."""
        if self.lux is not None and self.expected_lux is not None and self.expected_lux > 0:
            return (abs(self.lux - self.expected_lux) / self.expected_lux) * 100.0
        return None

    def record_reading(
        self,
        lux_value: float,
        timestamp: Optional[str] = None,
        device_name: Optional[str] = None,
        source_sample_id: Optional[str] = None,
        source_profile_id: Optional[str] = None,
    ) -> None:
        """Record a physical lux meter reading with optional metadata."""
        if lux_value < 0:
            raise ValueError("Measured lux cannot be negative.")
        self.lux = float(lux_value)
        self.timestamp = timestamp or datetime.now().isoformat()
        if device_name:
            self.device_name = device_name
        self.source_sample_id = source_sample_id
        self.source_profile_id = source_profile_id

    def clear_reading(self) -> None:
        """Clear the recorded reading and associated metadata."""
        self.lux = None
        self.timestamp = None
        self.device_name = None
        self.source_sample_id = None
        self.source_profile_id = None
        self.is_possible_outlier = False
        self.outlier_reason = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize point to a JSON-serializable dictionary."""
        return {
            "id": self.id,
            "x": round(self.x, 4),
            "y": round(self.y, 4),
            "lux": self.lux,
            "expected_lux": self.expected_lux,
            "locked_coordinates": self.locked_coordinates,
            "notes": self.notes,
            "timestamp": self.timestamp,
            "device_name": self.device_name,
            "source_sample_id": self.source_sample_id,
            "source_profile_id": self.source_profile_id,
            "is_possible_outlier": self.is_possible_outlier,
            "outlier_reason": self.outlier_reason,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> MeasurementPoint:
        """Create a MeasurementPoint from a dictionary."""
        return cls(
            id=str(data["id"]),
            x=float(data["x"]),
            y=float(data["y"]),
            lux=float(data["lux"]) if data.get("lux") is not None else None,
            expected_lux=float(data["expected_lux"]) if data.get("expected_lux") is not None else None,
            locked_coordinates=bool(data.get("locked_coordinates", True)),
            notes=str(data.get("notes", "")),
            timestamp=data.get("timestamp"),
            device_name=data.get("device_name"),
            source_sample_id=data.get("source_sample_id"),
            source_profile_id=data.get("source_profile_id"),
            is_possible_outlier=bool(data.get("is_possible_outlier", False)),
            outlier_reason=str(data.get("outlier_reason", "")),
        )
