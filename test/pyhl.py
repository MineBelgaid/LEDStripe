from bleak import BleakScanner, BleakClient
import asyncio
import sys

sys.coinit_flags = 0  # 0 means MTA
import qasync
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
import BLEClass
import Utils
import os
from SerialListener import ArduinoSerialListener

try:
    from ctypes import windll
except ImportError:
    print("ctypes not imported due to different OS (Non Windows)")


class MainWindow(QMainWindow):
    def closeEvent(self, event):
        # Clean up Arduino listener when closing
        if hasattr(self, "serial_listener"):
            self.serial_listener.stop_listening()
            self.serial_listener.disconnect()
            if hasattr(self, "arduino_task") and self.arduino_task:
                self.arduino_task.cancel()

        # Clean up BLE connection
        if Utils.client is not None:
            loop = asyncio.get_event_loop()
            loop.create_task(Utils.client.stop())

    def __init__(self):
        super().__init__()
        self.setFixedSize(400, 300)  # Reduced height for simpler UI
        self.setWindowTitle("LED Arduino Control")

        # Basic UI layout - scanning and connection
        self.scan_button = QPushButton("Scan", self)
        self.scan_button.setGeometry(QRect(10, 10, 75, 23))
        self.scan_button.clicked.connect(self.handle_scan)

        self.devices_combobox = QComboBox(self)
        self.devices_combobox.setGeometry(QRect(90, 10, 200, 22))

        self.connect_button = QPushButton("Connect", self)
        self.connect_button.setGeometry(QRect(10, 40, 75, 23))
        self.connect_button.clicked.connect(self.handle_connect)

        self.device_address = QLineEdit(self)
        self.device_address.setGeometry(QRect(160, 40, 130, 22))

        self.connection_status = QLabel("Disconnected", self)
        self.connection_status.setGeometry(QRect(90, 40, 71, 20))
        self.connection_status.setStyleSheet("QLabel {color: red; }")

        # Progress indicator for scanning
        self.scan_progress = QLabel(self)
        self.scan_progress.setGeometry(QRect(300, 10, 20, 20))
        self.scan_progress.setScaledContents(True)
        self.movie = QMovie(os.path.join(os.path.abspath("."), "Flower.gif"))
        self.scan_progress.setMovie(self.movie)
        self.scan_progress.hide()

        # Power buttons
        self.power_group = QGroupBox("LED Control", self)
        self.power_group.setGeometry(QRect(10, 80, 380, 80))

        self.powerOn_button = QPushButton("Power On", self.power_group)
        self.powerOn_button.setGeometry(QRect(20, 30, 150, 30))
        self.powerOn_button.clicked.connect(self.handle_powerOn)

        self.powerOff_button = QPushButton("Power Off", self.power_group)
        self.powerOff_button.setGeometry(QRect(210, 30, 150, 30))
        self.powerOff_button.clicked.connect(self.handle_powerOff)

        # Arduino control section
        self.arduino_group = QGroupBox("Arduino Serial Control", self)
        self.arduino_group.setGeometry(QRect(10, 170, 380, 120))

        self.arduino_enabled = QCheckBox("Enable Arduino Control", self.arduino_group)
        self.arduino_enabled.setGeometry(QRect(20, 30, 160, 20))
        self.arduino_enabled.stateChanged.connect(self.toggle_arduino_listener)

        # Port selection
        self.arduino_port_label = QLabel("Port:", self.arduino_group)
        self.arduino_port_label.setGeometry(QRect(20, 60, 40, 20))

        self.arduino_port_combo = QComboBox(self.arduino_group)
        self.arduino_port_combo.setGeometry(QRect(60, 60, 230, 22))

        # Refresh button
        self.arduino_refresh_button = QPushButton("⟳", self.arduino_group)
        self.arduino_refresh_button.setGeometry(QRect(300, 60, 30, 22))
        self.arduino_refresh_button.setToolTip("Refresh port list")
        self.arduino_refresh_button.clicked.connect(self.populate_arduino_ports)

        # Status indicator
        self.arduino_status = QLabel("Status: Disconnected", self.arduino_group)
        self.arduino_status.setGeometry(QRect(20, 90, 340, 20))
        self.arduino_status.setStyleSheet("QLabel {color: red;}")

        # Create serial listener and populate ports
        self.serial_listener = ArduinoSerialListener()
        self.populate_arduino_ports()

        # Initial state
        self.devices = []
        self.setControlsEnabled(False)

    def setControlsEnabled(self, enabled):
        """Enable or disable LED control buttons"""
        self.powerOn_button.setEnabled(enabled)
        self.powerOff_button.setEnabled(enabled)

    @property
    def current_client(self):
        return Utils.client

    @qasync.asyncSlot()
    async def handle_scan(self):
        """Scan for BLE devices"""
        self.devices.clear()
        self.devices_combobox.clear()

        # Show scanning animation
        self.scan_progress.show()
        self.movie.start()

        # Perform scan
        devices = await BLEClass.BleakScanner.discover(timeout=8.0)
        self.devices = devices

        # Populate dropdown
        for i, device in enumerate(self.devices):
            if str(device.name).startswith("QHM"):
                print(f"Found Device {device.name}")
                self.devices_combobox.insertItem(i, device.name, device)

        # Hide animation when done
        self.movie.stop()
        self.scan_progress.hide()

    @qasync.asyncSlot()
    async def handle_connect(self):
        """Connect to the selected BLE device"""
        # Get device from address field or dropdown
        if self.device_address.text() != "":
            device = await BLEClass.BleakScanner.find_device_by_address(
                self.device_address.text()
            )
        else:
            device = self.devices_combobox.currentData()

        # Connect if we have a valid device
        if isinstance(device, BLEClass.BLEDevice):
            if Utils.client is not None:
                await Utils.client.stop()

            Utils.client = BLEClass.QBleakClient(device)
            await Utils.client.start()

            # Update UI
            self.connection_status.setText("Connected")
            self.connection_status.setStyleSheet("QLabel {color: green;}")
            self.setControlsEnabled(True)
            self.connect_button.setText("Disconnect")
            self.connect_button.clicked.disconnect()
            self.connect_button.clicked.connect(self.handle_disconnect)

    @qasync.asyncSlot()
    async def handle_disconnect(self):
        """Disconnect from the BLE device"""
        if Utils.client is not None:
            await Utils.client.stop()
            Utils.client = None

            # Update UI
            self.connection_status.setText("Disconnected")
            self.connection_status.setStyleSheet("QLabel {color: red;}")
            self.setControlsEnabled(False)
            self.connect_button.setText("Connect")
            self.connect_button.clicked.disconnect()
            self.connect_button.clicked.connect(self.handle_connect)

    @qasync.asyncSlot()
    async def handle_powerOn(self):
        """Turn LED power on"""
        if self.current_client:
            await self.current_client.writePower("On")
            print("LED power turned ON")

    @qasync.asyncSlot()
    async def handle_powerOff(self):
        """Turn LED power off"""
        if self.current_client:
            await self.current_client.writePower("Off")
            print("LED power turned OFF")

    def populate_arduino_ports(self):
        """Get available serial ports and populate the combo box"""
        self.arduino_port_combo.clear()
        import serial.tools.list_ports

        ports = serial.tools.list_ports.comports()
        for i, port in enumerate(ports):
            self.arduino_port_combo.addItem(
                f"{port.device} - {port.description}", port.device
            )

        # Select current port if exists
        if hasattr(self.serial_listener, "port") and self.serial_listener.port:
            for i in range(self.arduino_port_combo.count()):
                if self.arduino_port_combo.itemData(i) == self.serial_listener.port:
                    self.arduino_port_combo.setCurrentIndex(i)
                    break

    def update_arduino_status(self, connected):
        """Update the Arduino connection status display"""
        if connected:
            self.arduino_status.setText(
                f"Status: Connected ({self.serial_listener.port}) - Ready to receive on/off commands"
            )
            self.arduino_status.setStyleSheet("QLabel {color: green;}")
        else:
            self.arduino_status.setText("Status: Disconnected")
            self.arduino_status.setStyleSheet("QLabel {color: red;}")

    @qasync.asyncSlot()
    async def toggle_arduino_listener(self):
        """Toggle Arduino serial connection on/off"""
        if self.arduino_enabled.isChecked():
            # Get selected port
            if self.arduino_port_combo.currentIndex() >= 0:
                port = self.arduino_port_combo.itemData(
                    self.arduino_port_combo.currentIndex()
                )
                self.serial_listener.port = port

            # Try to connect
            if self.serial_listener.connect():
                self.update_arduino_status(True)

                # Start listening in test mode or with BLE client
                if self.current_client:
                    print("Starting Arduino listener with BLE connection")
                    self.arduino_task = asyncio.create_task(
                        self.serial_listener.start_listening(self.current_client)
                    )
                else:
                    print("Starting Arduino listener in test mode")
                    self.arduino_task = asyncio.create_task(
                        self.serial_listener.start_listening_test_mode()
                    )

                # Add error handler
                self.arduino_task.add_done_callback(self.handle_arduino_task_result)
            else:
                self.arduino_enabled.setChecked(False)
                print(
                    f"Failed to connect to Arduino on port {self.serial_listener.port}"
                )
        else:
            # Stop listening and disconnect
            self.serial_listener.stop_listening()
            await asyncio.sleep(0.1)
            self.serial_listener.disconnect()
            self.update_arduino_status(False)

            # Cancel task if it exists
            if hasattr(self, "arduino_task") and self.arduino_task:
                self.arduino_task.cancel()

    def handle_arduino_task_result(self, task):
        """Handle the result of the Arduino listener task"""
        try:
            task.result()  # This will raise any exception that occurred
        except asyncio.CancelledError:
            print("Arduino task was cancelled")
        except Exception as e:
            print(f"Arduino task failed with error: {e}")
            # Update UI to show disconnected state
            self.arduino_enabled.setChecked(False)
            self.update_arduino_status(False)


def main():
    try:
        user32 = windll.user32
        user32.SetProcessDPIAware()
    except:
        pass

    Utils.app = QApplication(sys.argv)
    loop = qasync.QEventLoop(Utils.app)
    asyncio.set_event_loop(loop)

    w = MainWindow()
    w.show()

    with loop:
        loop.run_forever()


if __name__ == "__main__":
    main()
