"""USB serial transport reader for inspecting unverified numeric lines.

No meter model is currently qualified for physical capture. Raw parsed values
remain diagnostic until a model-specific profile is implemented and validated.
"""

from __future__ import annotations
import re
import time
import threading
from typing import List, Optional, Tuple, Dict
from PySide6.QtCore import QObject, Signal

from measurement_sources.base import MeasurementSource

try:
    import serial
    import serial.tools.list_ports
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False


class USBSerialMeterSource(MeasurementSource):
    """Open serial transport and expose raw values without claiming meter support."""

    live_reading_stream = Signal(float)
    connection_status_changed = Signal(bool, str)

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent=parent)
        self.port_name: Optional[str] = None
        self.baud_rate: int = 9600
        self.serial_inst = None
        self.is_running: bool = False
        self._thread: Optional[threading.Thread] = None
        self.latest_lux: Optional[float] = None
        self.profile_id: Optional[str] = None
        self.capture_supported = False
        self.freshness_seconds: Optional[float] = None
        self._is_connected = False

    def get_source_name(self) -> str:
        return "USB Serial (unverified profile)"

    def connect_source(self) -> bool:
        if self.port_name:
            ok, _ = self.connect_port(self.port_name, self.baud_rate)
            return ok
        return False

    def disconnect_source(self) -> None:
        self.disconnect_port()

    def is_available(self) -> bool:
        return SERIAL_AVAILABLE

    @classmethod
    def list_available_ports(cls) -> List[Tuple[str, str]]:
        """List available physical/virtual USB COM ports with descriptions."""
        if not SERIAL_AVAILABLE:
            return []

        ports = []
        for p in serial.tools.list_ports.comports():
            ports.append((p.device, f"{p.device} - {p.description}"))

        return ports

    def connect_port(self, port: str, baud: int = 9600, timeout: float = 1.0) -> Tuple[bool, str]:
        """Open USB serial connection to lux meter."""
        self.disconnect_port()
        self.port_name = port
        self.baud_rate = baud

        if not SERIAL_AVAILABLE:
            message = "USB serial support is unavailable because pyserial is not installed."
            self.connection_status_changed.emit(False, message)
            return False, message
        if port == "COM_MOCK":
            message = "Simulated ports are not physical meter connections. Choose Practice instead."
            self.connection_status_changed.emit(False, message)
            return False, message

        try:
            self.serial_inst = serial.Serial(port=port, baudrate=baud, timeout=timeout)
            self._is_connected = True
            self.is_running = True
            self._thread = threading.Thread(target=self._read_stream_loop, daemon=True)
            self._thread.start()
            message = (
                f"Serial transport open on {port} @ {baud} bps. "
                "No qualified meter profile is configured; readings cannot be captured."
            )
            self.connection_status_changed.emit(True, message)
            return True, message
        except Exception as e:
            self._is_connected = False
            self.connection_status_changed.emit(False, f"Connection Failed: {e}")
            return False, str(e)

    def disconnect_port(self) -> None:
        """Close connection."""
        self.is_running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=0.8)
        self._thread = None

        if self.serial_inst and self.serial_inst.is_open:
            try:
                self.serial_inst.close()
            except Exception:
                pass
        self.serial_inst = None
        self._is_connected = False
        self.latest_lux = None
        self.connection_status_changed.emit(False, "Disconnected")

    def _read_stream_loop(self) -> None:
        """Background thread reading lines and parsing lux numeric values."""
        while self.is_running and self.serial_inst and self.serial_inst.is_open:
            try:
                line = self.serial_inst.readline().decode("utf-8", errors="ignore").strip()
                if line:
                    lux = self._parse_lux_value(line)
                    if lux is not None:
                        self.latest_lux = lux
                        self.live_reading_stream.emit(lux)
            except Exception:
                time.sleep(0.1)

    @staticmethod
    def _parse_lux_value(raw_text: str) -> Optional[float]:
        """Parse raw text from lux meter into float value."""
        clean = raw_text.replace("lx", "").replace("LX", "").replace("Lux", "").replace("LUX", "")
        match = re.search(r"[-+]?\d*\.?\d+", clean)
        if match:
            try:
                val = float(match.group(0))
                if 0.0 <= val <= 200000.0:
                    return round(val, 1)
            except ValueError:
                pass
        return None
