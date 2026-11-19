"""Bluetooth device discovery without a qualified Luxious meter profile.

Discovery identifies nearby devices only. It does not establish a data protocol
or prove that a device sends illuminance readings.
"""

from __future__ import annotations
import asyncio
import threading
from typing import List, Optional, Tuple, Dict
from PySide6.QtCore import QObject, Signal

from measurement_sources.base import MeasurementSource

try:
    import bleak
    BLE_AVAILABLE = True
except ImportError:
    BLE_AVAILABLE = False


class BluetoothMeterSource(MeasurementSource):
    """Discover BLE devices and reject unverified lux meter connections."""

    live_reading_stream = Signal(float)
    connection_status_changed = Signal(bool, str)
    device_discovered = Signal(str, str, int)
    scan_finished = Signal()
    scan_failed = Signal(str)

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent=parent)
        self.device_address: Optional[str] = None
        self.device_name: Optional[str] = None
        self.client = None
        self.is_running: bool = False
        self._thread: Optional[threading.Thread] = None
        self.latest_lux: Optional[float] = None
        self.profile_id: Optional[str] = None
        self.capture_supported = False
        self.freshness_seconds: Optional[float] = None
        self._is_connected = False

    def get_source_name(self) -> str:
        return "Bluetooth (unverified profile)"

    def connect_source(self) -> bool:
        if self.device_address:
            return self.connect_device(self.device_address, self.device_name or "Bluetooth Meter")
        return False

    def disconnect_source(self) -> None:
        self.disconnect_device()

    def scan_devices(self, timeout: float = 4.0) -> None:
        """Scan for nearby Bluetooth lux meters in a background thread."""
        thread = threading.Thread(target=self._scan_worker, args=(timeout,), daemon=True)
        thread.start()

    def _scan_worker(self, timeout: float) -> None:
        if not BLE_AVAILABLE:
            self.scan_failed.emit("Bluetooth scanning is unavailable because bleak is not installed.")
            self.scan_finished.emit()
            return

        async def run_scan():
            try:
                scanner = bleak.BleakScanner()
                devices = await scanner.discover(timeout=timeout)
                for d in devices:
                    name = d.name or "Unknown Bluetooth Device"
                    rssi = d.rssi if hasattr(d, "rssi") else -70
                    self.device_discovered.emit(d.address, name, rssi)
            except Exception as exc:
                self.scan_failed.emit(f"Bluetooth scan failed: {exc}")
            finally:
                self.scan_finished.emit()

        try:
            asyncio.run(run_scan())
        except Exception as exc:
            self.scan_failed.emit(f"Bluetooth scan failed: {exc}")
            self.scan_finished.emit()

    def connect_device(self, address: str, name: str = "Bluetooth Lux Meter") -> bool:
        """Decline an unverified meter profile instead of fabricating a connection."""
        self.disconnect_device()
        self.device_address = address
        self.device_name = name
        message = f"{name} was discovered, but no verified lux profile is configured. Capture is unavailable."
        self.connection_status_changed.emit(False, message)
        return False

    def disconnect_device(self) -> None:
        """Disconnect Bluetooth device."""
        self.is_running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=0.8)
        self._thread = None
        self._is_connected = False
        self.latest_lux = None
        self.connection_status_changed.emit(False, "Disconnected")
