"""Selected meter state and freshness rules for one capture session."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import time
import uuid
import math
from typing import Optional


class DeviceSessionState(str, Enum):
    DISCONNECTED = "disconnected"
    WAITING = "waiting"
    RECEIVING = "receiving"
    STALE = "stale"
    UNSUPPORTED = "unsupported"
    PRACTICE = "practice"


@dataclass(frozen=True)
class MeasurementSample:
    """One incoming value with a unique event identity and monotonic age."""

    sample_id: str
    source_id: str
    lux: float
    unit: str
    received_at: float
    simulated: bool
    profile_id: Optional[str] = None


class DeviceSession:
    """Keep transport, profile support, selected source, and sample age distinct."""

    def __init__(self, freshness_seconds: Optional[float] = None) -> None:
        if freshness_seconds is not None and freshness_seconds <= 0:
            raise ValueError("Sample freshness interval must be positive.")
        self.freshness_seconds = freshness_seconds
        self.selected_source_id: Optional[str] = None
        self.profile_id: Optional[str] = None
        self.connected = False
        self.profile_supported = False
        self.simulated = False
        self.latest_sample: Optional[MeasurementSample] = None

    @property
    def state(self) -> DeviceSessionState:
        if not self.connected:
            return DeviceSessionState.DISCONNECTED
        if not self.profile_supported or not self.profile_id:
            if not self.simulated:
                return DeviceSessionState.UNSUPPORTED
        if self.latest_sample is None:
            return DeviceSessionState.WAITING
        if not self.is_fresh():
            return DeviceSessionState.STALE
        if self.simulated:
            return DeviceSessionState.PRACTICE
        return DeviceSessionState.RECEIVING

    def select_source(
        self,
        source_id: Optional[str],
        *,
        profile_id: Optional[str] = None,
        supported: bool = False,
        simulated: bool = False,
        connected: bool = False,
        freshness_seconds: Optional[float] = None,
    ) -> None:
        """Select one source and clear data carried over from the previous source."""
        self.selected_source_id = source_id
        self.profile_id = profile_id
        self.profile_supported = supported
        self.simulated = simulated
        self.connected = connected
        self.freshness_seconds = freshness_seconds
        self.latest_sample = None

    def set_transport_connected(self, connected: bool) -> None:
        self.connected = connected
        if not connected:
            self.latest_sample = None

    def update_sample(
        self,
        source_id: str,
        lux: float,
        *,
        unit: str = "lx",
        received_at: Optional[float] = None,
    ) -> Optional[MeasurementSample]:
        """Accept a valid nonnegative sample from the currently selected source."""
        if source_id != self.selected_source_id or not self.connected:
            return None
        if unit != "lx" or not math.isfinite(lux) or lux < 0:
            return None
        sample = MeasurementSample(
            sample_id=str(uuid.uuid4()),
            source_id=source_id,
            lux=float(lux),
            unit=unit,
            received_at=time.monotonic() if received_at is None else received_at,
            simulated=self.simulated,
            profile_id=self.profile_id,
        )
        self.latest_sample = sample
        return sample

    def is_fresh(self, now: Optional[float] = None) -> bool:
        if self.latest_sample is None:
            return False
        current = time.monotonic() if now is None else now
        age = current - self.latest_sample.received_at
        return (
            self.freshness_seconds is not None
            and 0.0 <= age <= self.freshness_seconds
        )

    def capture_sample(self, now: Optional[float] = None) -> Optional[MeasurementSample]:
        """Return the latest selected, fresh, supported sample if capture is safe."""
        sample = self.latest_sample
        if (
            sample is None
            or not self.connected
            or sample.source_id != self.selected_source_id
            or sample.simulated != self.simulated
            or not self.is_fresh(now)
            or not (self.profile_supported or self.simulated)
        ):
            return None
        return sample

    def consume_sample(self, sample_id: str) -> bool:
        """Consume one sample once after the user activates capture."""
        if self.latest_sample is None or self.latest_sample.sample_id != sample_id:
            return False
        self.latest_sample = None
        return True
