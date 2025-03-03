import serial as pyserial
import asyncio
import threading
import time


class ArduinoSerialListener:
    def __init__(self):
        self.port = None
        self.baudrate = 9600
        self.serial = None
        self.is_connected = False
        self.is_listening = False
        self._stop_event = threading.Event()

    def connect(self, port=None):
        """Connect to the Arduino via serial port"""
        if port:
            self.port = port

        if not self.port:
            # Try to auto-detect a port if none specified
            import serial.tools.list_ports

            ports = list(serial.tools.list_ports.comports())
            if ports:
                self.port = ports[0].device
            else:
                print("No serial ports found")
                return False

        try:
            # Close previous connection if exists
            if self.serial and hasattr(self.serial, "is_open") and self.serial.is_open:
                self.serial.close()

            # Open new connection
            self.serial = pyserial.Serial(self.port, self.baudrate, timeout=1)
            self.is_connected = True
            print(f"Connected to Arduino on {self.port}")
            return True
        except Exception as e:
            print(f"Failed to connect to Arduino: {e}")
            self.is_connected = False
            return False

    def disconnect(self):
        """Disconnect from the Arduino"""
        try:
            if hasattr(self, "serial") and self.serial and self.serial.is_open:
                self.serial.close()
            self.is_connected = False
            print("Disconnected from Arduino")
            return True
        except Exception as e:
            print(f"Error disconnecting from Arduino: {e}")
            return False

    async def start_listening(self, ble_client):
        """Start listening for Arduino commands and forward them to BLE"""
        if not self.is_connected or not self.serial:
            print("Cannot start listening: Not connected to Arduino")
            return False

        self.is_listening = True
        self._stop_event.clear()
        print("Started listening for Arduino commands")

        try:
            while not self._stop_event.is_set():
                if self.serial.in_waiting > 0:
                    line = (
                        self.serial.readline().decode("utf-8", errors="replace").strip()
                    )
                    if line:
                        print(f"Arduino sent: {line}")

                        # Simple on/off commands - handle multiple formats
                        if (
                            line.upper() == "ON"
                            or line == "POWER:ON"
                            or line == "LED:ON"
                        ):
                            await ble_client.writePower("On")
                            self.serial.write("ACK:ON\n".encode())
                            print("Turned LED ON via Arduino command")

                        elif (
                            line.upper() == "OFF"
                            or line == "POWER:OFF"
                            or line == "LED:OFF"
                        ):
                            await ble_client.writePower("Off")
                            self.serial.write("ACK:OFF\n".encode())
                            print("Turned LED OFF via Arduino command")

                # Small delay to avoid tight loop
                await asyncio.sleep(0.1)

        except Exception as e:
            print(f"Error in Arduino listener: {e}")
        finally:
            self.is_listening = False

        return True

    async def start_listening_test_mode(self):
        """Test mode - just log commands without forwarding to BLE"""
        if not self.is_connected or not hasattr(self, "serial") or not self.serial:
            print("Cannot start listening: Not connected to Arduino")
            return False

        self.is_listening = True
        self._stop_event.clear()
        print(
            "Started listening for Arduino commands in TEST MODE (commands will be logged only)"
        )

        try:
            while not self._stop_event.is_set():
                if self.serial.in_waiting > 0:
                    line = (
                        self.serial.readline().decode("utf-8", errors="replace").strip()
                    )
                    if line:
                        print(f"Arduino sent (TEST MODE): {line}")

                        # Simple on/off commands - just acknowledge in test mode
                        if (
                            line.upper() == "ON"
                            or line == "POWER:ON"
                            or line == "LED:ON"
                        ):
                            self.serial.write("ACK:ON\n".encode())
                            print("Would turn LED ON (test mode)")

                        elif (
                            line.upper() == "OFF"
                            or line == "POWER:OFF"
                            or line == "LED:OFF"
                        ):
                            self.serial.write("ACK:OFF\n".encode())
                            print("Would turn LED OFF (test mode)")

                # Small delay to avoid tight loop
                await asyncio.sleep(0.1)

        except Exception as e:
            print(f"Error in Arduino test listener: {e}")
        finally:
            self.is_listening = False

        return True

    def stop_listening(self):
        """Stop listening for Arduino commands"""
        self._stop_event.set()
        self.is_listening = False
        print("Stopped listening for Arduino commands")
