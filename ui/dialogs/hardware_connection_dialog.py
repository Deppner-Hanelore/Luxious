"""Meter connection and profile-status dialog (USB & Bluetooth).

Shows available serial ports and discovered Bluetooth devices. A physical value
can be captured only when a verified meter profile supports the selected source.
No such profile is currently configured in Luxious.
"""

from __future__ import annotations
from typing import Optional, List, Tuple
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtWidgets import (
    QDialog,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QTabWidget,
    QLabel,
    QPushButton,
    QComboBox,
    QListWidget,
    QListWidgetItem,
    QFrame,
    QGroupBox,
    QDialogButtonBox,
    QProgressBar,
)

from measurement_sources.usb_serial import USBSerialMeterSource
from measurement_sources.bluetooth_meter import BluetoothMeterSource
from measurement_sources.device_session import DeviceSession, MeasurementSample, DeviceSessionState
from i18n.translations import tr


class HardwareConnectionDialog(QDialog):
    """Dialog for scanning, connecting, and live-streaming from USB & Bluetooth lux meters."""

    reading_captured = Signal(object)  # Emitted with a validated MeasurementSample

    def __init__(
        self,
        usb_source: USBSerialMeterSource,
        bt_source: BluetoothMeterSource,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.usb_source = usb_source
        self.bt_source = bt_source
        self.device_session = DeviceSession()
        self._scan_failed = False

        self.setWindowTitle("Device connections")
        self.setMinimumWidth(520)

        # 1. Top Live Stream Monitor Banner
        self.monitor_frame = QFrame(self)
        self.monitor_frame.setObjectName("sensorMonitor")
        self.monitor_frame.setStyleSheet("""
            QFrame#sensorMonitor {
                background-color: #0f172a;
                border-radius: 6px;
                padding: 10px;
            }
        """)
        m_layout = QVBoxLayout(self.monitor_frame)
        live_row = QHBoxLayout()

        self.lbl_live_title = QLabel("LIVE SENSOR READOUT:", self.monitor_frame)
        self.lbl_live_title.setStyleSheet("background: transparent; color: #94a3b8; font-size: 11px; font-weight: bold;")

        self.lbl_live_value = QLabel("--.- lx", self.monitor_frame)
        self.lbl_live_value.setStyleSheet("background: transparent; color: #38bdf8; font-size: 24px; font-weight: bold; font-family: monospace;")
        self.lbl_device_state = QLabel("No verified meter profile selected. Capture is unavailable.", self.monitor_frame)
        self.lbl_device_state.setStyleSheet("background: transparent; color: #fbbf24; font-size: 11px; font-weight: 600;")
        self.lbl_device_state.setWordWrap(True)

        self.btn_capture = QPushButton("Capture Reading", self.monitor_frame)
        self.btn_capture.setStyleSheet("""
            QPushButton {
                background-color: #2563eb;
                color: #ffffff;
                font-weight: bold;
                font-size: 12px;
                padding: 6px 14px;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #1d4ed8; }
            QPushButton:disabled { background-color: #475569; color: #cbd5e1; }
        """)
        self.btn_capture.clicked.connect(self._capture_reading)
        self.btn_capture.setEnabled(False)
        self.btn_capture.setMinimumHeight(44)

        live_row.addWidget(self.lbl_live_title)
        live_row.addStretch()
        live_row.addWidget(self.lbl_live_value)
        live_row.addWidget(self.btn_capture)
        m_layout.addLayout(live_row)
        m_layout.addWidget(self.lbl_device_state)

        # 2. Connection Tabs: USB Serial vs Bluetooth
        self.tabs = QTabWidget(self)
        self.tabs.currentChanged.connect(self._on_source_tab_changed)

        # --- Tab 1: USB Serial ---
        self.tab_usb = QWidget(self)
        u_layout = QGridLayout(self.tab_usb)
        u_layout.setSpacing(8)

        self.combo_ports = QComboBox(self.tab_usb)
        self.btn_refresh_ports = QPushButton("Scan Ports", self.tab_usb)
        self.btn_refresh_ports.clicked.connect(self._refresh_ports)

        self.combo_baud = QComboBox(self.tab_usb)
        for b in [9600, 19200, 38400, 57600, 115200]:
            self.combo_baud.addItem(f"{b} bps", b)

        self.btn_connect_usb = QPushButton("Connect USB Meter", self.tab_usb)
        self.btn_connect_usb.setStyleSheet("font-weight: bold; padding: 5px 12px;")
        self.btn_connect_usb.clicked.connect(self._toggle_usb_connect)

        self.lbl_usb_status = QLabel("Status: Disconnected", self.tab_usb)
        self.lbl_usb_status.setStyleSheet("color: #64748b; font-size: 11px;")
        self.lbl_usb_status.setWordWrap(True)

        u_layout.addWidget(QLabel("Serial / COM Port:"), 0, 0)
        u_layout.addWidget(self.combo_ports, 0, 1)
        u_layout.addWidget(self.btn_refresh_ports, 0, 2)

        u_layout.addWidget(QLabel("Baud Rate:"), 1, 0)
        u_layout.addWidget(self.combo_baud, 1, 1)

        u_layout.addWidget(self.btn_connect_usb, 2, 0, 1, 3)
        u_layout.addWidget(self.lbl_usb_status, 3, 0, 1, 3)

        self.tabs.addTab(self.tab_usb, "USB Serial (COM)")

        # --- Tab 2: Bluetooth ---
        self.tab_bt = QWidget(self)
        b_layout = QVBoxLayout(self.tab_bt)
        b_layout.setSpacing(6)

        b_top = QHBoxLayout()
        self.btn_scan_bt = QPushButton("Scan Bluetooth Devices", self.tab_bt)
        self.btn_scan_bt.clicked.connect(self._scan_bluetooth)
        self.lbl_bt_scan_status = QLabel("", self.tab_bt)
        self.lbl_bt_scan_status.setStyleSheet("color: #64748b; font-size: 11px;")
        b_top.addWidget(self.btn_scan_bt)
        b_top.addWidget(self.lbl_bt_scan_status)
        b_top.addStretch()

        self.list_bt_devices = QListWidget(self.tab_bt)
        self.list_bt_devices.setStyleSheet("font-size: 12px; padding: 4px;")

        self.btn_connect_bt = QPushButton("Connect Selected Bluetooth Device", self.tab_bt)
        self.btn_connect_bt.setStyleSheet("font-weight: bold; padding: 5px 12px;")
        self.btn_connect_bt.setEnabled(self.bt_source.is_connected)
        self.btn_connect_bt.clicked.connect(self._toggle_bt_connect)
        self.list_bt_devices.currentItemChanged.connect(
            lambda current, previous: self.btn_connect_bt.setEnabled(self.bt_source.is_connected or current is not None)
        )

        self.lbl_bt_status = QLabel("Status: Disconnected", self.tab_bt)
        self.lbl_bt_status.setStyleSheet("color: #64748b; font-size: 11px;")
        self.lbl_bt_status.setWordWrap(True)

        b_layout.addLayout(b_top)
        b_layout.addWidget(self.list_bt_devices)
        b_layout.addWidget(self.btn_connect_bt)
        b_layout.addWidget(self.lbl_bt_status)

        self.tabs.addTab(self.tab_bt, "Bluetooth (BLE)")

        # 3. Close Button Box
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close, self)
        button_box.rejected.connect(self.accept)

        # Main Layout
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)
        main_layout.addWidget(self.monitor_frame)
        main_layout.addWidget(self.tabs)
        main_layout.addWidget(button_box)

        # Wire Driver Signals
        self.usb_source.live_reading_stream.connect(self._on_usb_stream_value)
        self.bt_source.live_reading_stream.connect(self._on_bt_stream_value)
        self.usb_source.connection_status_changed.connect(self._on_usb_status_changed)
        self.bt_source.connection_status_changed.connect(self._on_bt_status_changed)
        self.bt_source.device_discovered.connect(self._on_bt_device_discovered)
        self.bt_source.scan_finished.connect(self._on_bt_scan_finished)
        self.bt_source.scan_failed.connect(self._on_bt_scan_failed)

        self._freshness_timer = QTimer(self)
        self._freshness_timer.setInterval(250)
        self._freshness_timer.timeout.connect(self._refresh_capture_button)
        self._freshness_timer.start()

        # Initialize Ports
        self._refresh_ports()
        self._on_source_tab_changed(self.tabs.currentIndex())

    def _refresh_ports(self) -> None:
        """Scan and populate COM ports."""
        self.combo_ports.clear()
        ports = self.usb_source.list_available_ports()
        for p_id, p_name in ports:
            self.combo_ports.addItem(p_name, p_id)
        if not ports:
            self.lbl_usb_status.setText("No USB serial ports detected.")
        self.btn_connect_usb.setEnabled(bool(ports) or self.usb_source.is_connected)
        self.btn_connect_usb.setText("Disconnect USB Meter" if self.usb_source.is_connected else "Connect USB Meter")

    def _toggle_usb_connect(self) -> None:
        if self.usb_source.is_connected:
            self.usb_source.disconnect_port()
            self.btn_connect_usb.setText("Connect USB Meter")
            self.lbl_usb_status.setText("Status: Disconnected")
            self.lbl_live_value.setText("--.- lx")
            self.device_session.set_transport_connected(False)
            self._refresh_capture_button()
        else:
            port = self.combo_ports.currentData()
            baud = self.combo_baud.currentData()
            if port:
                ok, msg = self.usb_source.connect_port(port, baud=baud)
                if ok:
                    self.btn_connect_usb.setText("Disconnect USB Meter")
                    self.lbl_usb_status.setText(msg)
                else:
                    self.lbl_usb_status.setText(f"Error: {msg}")
                self._on_source_tab_changed(self.tabs.currentIndex())

    def _scan_bluetooth(self) -> None:
        self.list_bt_devices.clear()
        self._scan_failed = False
        self.lbl_bt_scan_status.setText("Scanning for Bluetooth meters...")
        self.btn_scan_bt.setEnabled(False)
        self.bt_source.scan_devices(timeout=3.0)

    def _on_bt_device_discovered(self, address: str, name: str, rssi: int) -> None:
        item = QListWidgetItem(f"{name} ({address}) [RSSI: {rssi} dBm]")
        item.setData(Qt.ItemDataRole.UserRole, (address, name))
        self.list_bt_devices.addItem(item)

    def _on_bt_scan_finished(self) -> None:
        if not self.list_bt_devices.count() and not self._scan_failed:
            self.lbl_bt_scan_status.setText("Scan complete. No devices found.")
        elif not self._scan_failed:
            self.lbl_bt_scan_status.setText("Scan complete.")
        self.btn_scan_bt.setEnabled(True)

    def _on_bt_scan_failed(self, message: str) -> None:
        self._scan_failed = True
        self.lbl_bt_scan_status.setText(message)

    def _toggle_bt_connect(self) -> None:
        if self.bt_source.is_connected:
            self.bt_source.disconnect_device()
            self.btn_connect_bt.setText("Connect Selected Bluetooth Device")
            self.lbl_bt_status.setText("Status: Disconnected")
            self.lbl_live_value.setText("--.- lx")
            self.device_session.set_transport_connected(False)
            self._refresh_capture_button()
        else:
            cur = self.list_bt_devices.currentItem()
            if cur:
                addr, name = cur.data(Qt.ItemDataRole.UserRole)
                connected = self.bt_source.connect_device(addr, name)
                if connected:
                    self.btn_connect_bt.setText("Disconnect Bluetooth Device")
                else:
                    self.lbl_bt_status.setText(
                        f"Unsupported: {name} has no verified Luxious profile. Enter readings manually."
                    )
                self._on_source_tab_changed(self.tabs.currentIndex())

    def _on_source_tab_changed(self, index: int) -> None:
        if index == 0:
            source_id = "usb"
            source = self.usb_source
        else:
            source_id = "bluetooth"
            source = self.bt_source
        self.device_session.select_source(
            source_id,
            profile_id=source.profile_id,
            supported=source.capture_supported,
            simulated=False,
            connected=source.is_connected,
            freshness_seconds=source.freshness_seconds,
        )
        self.lbl_live_value.setText("--.- lx")
        self._refresh_capture_button()

    def _on_usb_stream_value(self, lux: float) -> None:
        self._on_live_stream_value(lux, "usb")

    def _on_bt_stream_value(self, lux: float) -> None:
        self._on_live_stream_value(lux, "bluetooth")

    def _on_live_stream_value(self, lux: float, source_id: Optional[str] = None) -> None:
        """Show raw values while allowing capture only from a fresh supported profile."""
        if source_id is None:
            source_id = self.device_session.selected_source_id
        if source_id is None:
            return
        sample = self.device_session.update_sample(source_id, lux)
        if sample is None:
            return
        self.lbl_live_value.setText(f"{lux:.1f} lx")
        if self.device_session.state == DeviceSessionState.UNSUPPORTED:
            self.lbl_device_state.setText("Raw value received. No verified meter profile; capture is unavailable.")
        elif self.device_session.state == DeviceSessionState.PRACTICE:
            self.lbl_device_state.setText("Practice — simulated sample.")
        else:
            self.lbl_device_state.setText("Receiving a fresh sample from the selected meter profile.")
        self._refresh_capture_button()

    def _on_usb_status_changed(self, connected: bool, description: str) -> None:
        self.lbl_usb_status.setText(description)
        self.btn_connect_usb.setText("Disconnect USB Meter" if connected else "Connect USB Meter")
        self.btn_connect_usb.setEnabled(connected or bool(self.combo_ports.currentData()))
        if self.device_session.selected_source_id == "usb":
            self.device_session.set_transport_connected(connected)
            self._refresh_capture_button()

    def _on_bt_status_changed(self, connected: bool, description: str) -> None:
        self.lbl_bt_status.setText(description)
        self.btn_connect_bt.setText("Disconnect Bluetooth Device" if connected else "Connect Selected Bluetooth Device")
        self.btn_connect_bt.setEnabled(connected or self.list_bt_devices.currentItem() is not None)
        if self.device_session.selected_source_id == "bluetooth":
            self.device_session.set_transport_connected(connected)
            self._refresh_capture_button()

    def _refresh_capture_button(self) -> None:
        sample = self.device_session.capture_sample()
        self.btn_capture.setEnabled(sample is not None)
        if self.device_session.state == DeviceSessionState.STALE:
            self.lbl_device_state.setText("Last value is stale. Wait for a new meter sample.")
        elif self.device_session.state == DeviceSessionState.DISCONNECTED:
            self.lbl_device_state.setText("Meter disconnected. Enter readings manually.")
        elif self.device_session.state == DeviceSessionState.WAITING:
            self.lbl_device_state.setText("Connected — waiting for a fresh meter reading.")

    def _capture_reading(self) -> None:
        """Consume the current live update once, preventing repeat capture."""
        sample = self.device_session.capture_sample()
        if sample is None:
            return
        self.reading_captured.emit(sample)
        self.device_session.consume_sample(sample.sample_id)
        self._refresh_capture_button()
