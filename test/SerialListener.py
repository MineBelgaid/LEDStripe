import serial as pyserial  # Rename the import to avoid namespace conflicts
import asyncio
import threading
import time
import Utils

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

            # Use pyserial instead of serial to avoid namespace conflict
            self.serial = pyserial.Serial(self.port, self.baudrate, timeout=1)
            self.is_connected = True
            print(f"Connected to Arduino on {self.port}")

            # Update status (for example, printing the connection status)
            print("Status: Connected")

            return True
        except Exception as e:
            print(f"Failed to connect to Arduino: {e}")
            self.is_connected = False
            # Update status to disconnected in case of an error
            print("Status: Disconnected")
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
                    line = self.serial.readline().decode("utf-8").strip()
                    if line:
                        print(f"Arduino sent: {line}")
                        # Process commands from Arduino
                        if line.startswith("COLOR:"):
                            try:
                                # Format: COLOR:R,G,B
                                rgb = line[6:].split(",")
                                if len(rgb) == 3:
                                    r, g, b = map(int, rgb)
                                    await ble_client.writeColor(r, g, b)
                            except Exception as e:
                                print(f"Error processing color command: {e}")
                        elif line.startswith("MODE:"):
                            try:
                                # Format: MODE:index
                                mode_idx = int(line[5:])
                                await ble_client.writeMode(mode_idx)
                            except Exception as e:
                                print(f"Error processing mode command: {e}")
                        elif line == "POWER:ON":
                            await ble_client.writePower("On")
                        elif line == "POWER:OFF":
                            await ble_client.writePower("Off")

                # Avoid tight loop
                await asyncio.sleep(0.1)

        except Exception as e:
            print(f"Error in Arduino listener: {e}")
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
                        # Just log commands without forwarding
                        if line.startswith("COLOR:"):
                            try:
                                # Format: COLOR:R,G,B
                                rgb = line[6:].split(",")
                                if len(rgb) == 3:
                                    r, g, b = map(int, rgb)
                                    print(f"Would send COLOR: R={r}, G={g}, B={b}")
                                    # Send acknowledgment back to Arduino
                                    self.serial.write(
                                        f"ACK:COLOR:{r},{g},{b}\n".encode()
                                    )
                            except Exception as e:
                                print(f"Error processing color command: {e}")
                        elif line.startswith("MODE:"):
                            try:
                                # Format: MODE:index
                                mode_idx = int(line[5:])
                                print(f"Would send MODE: {mode_idx}")
                                # Send acknowledgment back to Arduino
                                self.serial.write(f"ACK:MODE:{mode_idx}\n".encode())
                            except Exception as e:
                                print(f"Error processing mode command: {e}")
                        elif line == "POWER:ON":
                            print("Would send POWER ON")
                            # Send acknowledgment back to Arduino
                            self.serial.write("ACK:POWER:ON\n".encode())
                        elif line == "POWER:OFF":
                            print("Would send POWER OFF")
                            # Send acknowledgment back to Arduino
                            self.serial.write("ACK:POWER:OFF\n".encode())

                # Avoid tight loop
                await asyncio.sleep(0.1)

        except Exception as e:
            print(f"Error in Arduino test listener: {e}")
            self.is_listening = False

        return True

    def stop_listening(self):
        """Stop the serial listener"""
        self.is_listening = False
        Utils.printLog("Stopping Arduino serial listener")

    async def process_command(self, command, client):
        """Process commands received from Arduino"""
        try:
            if command == "POWER_ON" or command == "TURN_ON":
                Utils.printLog("Arduino requested Power ON")
                await client.writePower("On")

            elif command == "POWER_OFF" or command == "TURN_OFF":
                Utils.printLog("Arduino requested Power OFF")
                await client.writePower("Off")

            elif command.startswith("MODE_"):
                try:
                    mode_idx = int(command.split("_")[1])
                    Utils.printLog(f"Arduino requested mode change to {mode_idx}")
                    await client.writeMode(mode_idx)
                except (ValueError, IndexError):
                    Utils.printLog(f"Invalid mode command: {command}")

            elif command.startswith("COLOR_"):
                try:
                    rgb = command.split("_")[1].split(",")
                    r = int(rgb[0])
                    g = int(rgb[1])
                    b = int(rgb[2])
                    Utils.printLog(
                        f"Arduino requested color change to RGB({r},{g},{b})"
                    )
                    await client.writeColor(r, g, b)
                except (ValueError, IndexError):
                    Utils.printLog(f"Invalid color command: {command}")

            # Log any unrecognized commands for debugging
            else:
                Utils.printLog(f"Received unrecognized command: {command}")

        except Exception as e:
            Utils.printLog(f"Error processing Arduino command: {e}")
