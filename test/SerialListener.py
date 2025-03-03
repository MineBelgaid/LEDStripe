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
        self._command_queue = asyncio.Queue()  # Queue for commands
        self._lock = asyncio.Lock()  # Lock for thread safety

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

        # Start a separate processor for BLE commands
        self._ble_client = ble_client
        processor_task = asyncio.create_task(self._process_commands())

        try:
            while not self._stop_event.is_set():
                if self.serial.in_waiting > 0:
                    line = (
                        self.serial.readline().decode("utf-8", errors="replace").strip()
                    )
                    if line:
                        print(f"Arduino sent: {line}")
                        # Queue the command for processing
                        await self._command_queue.put(line)

                # Avoid tight loop
                await asyncio.sleep(0.1)

        except Exception as e:
            print(f"Error in Arduino listener: {e}")
        finally:
            self.is_listening = False
            # Cancel the processor task when we're done
            processor_task.cancel()
            try:
                await processor_task
            except asyncio.CancelledError:
                pass

        return True

    async def _process_commands(self):
        """Process commands from the queue"""
        while self.is_listening:
            try:
                # Get a command from the queue
                command = await self._command_queue.get()

                # Process standard LED protocol commands
                if command.startswith("COLOR:"):
                    try:
                        # Format: COLOR:R,G,B
                        rgb = command[6:].split(",")
                        if len(rgb) == 3:
                            r, g, b = map(int, rgb)
                            await self._ble_client.writeColor(r, g, b)
                            # Send acknowledgment back to Arduino
                            self.serial.write(f"ACK:COLOR:{r},{g},{b}\n".encode())
                    except Exception as e:
                        print(f"Error processing color command: {e}")

                elif command.startswith("MODE:"):
                    try:
                        # Format: MODE:index
                        mode_idx = int(command[5:])
                        await self._ble_client.writeMode(mode_idx)
                        # Send acknowledgment back to Arduino
                        self.serial.write(f"ACK:MODE:{mode_idx}\n".encode())
                    except Exception as e:
                        print(f"Error processing mode command: {e}")

                elif command == "POWER:ON":
                    await self._ble_client.writePower("On")
                    # Send acknowledgment back to Arduino
                    self.serial.write("ACK:POWER:ON\n".encode())

                elif command == "POWER:OFF":
                    await self._ble_client.writePower("Off")
                    # Send acknowledgment back to Arduino
                    self.serial.write("ACK:POWER:OFF\n".encode())

                # Alternative formats for flexibility
                elif command.startswith("LED:"):
                    # Process LED commands...
                    parts = command[4:].split(":")
                    if len(parts) >= 2:
                        cmd = parts[0].upper()
                        # Process various LED commands...
                        if cmd == "ON":
                            await self._ble_client.writePower("On")
                            self.serial.write("ACK:LED:ON\n".encode())
                        elif cmd == "OFF":
                            await self._ble_client.writePower("Off")
                            self.serial.write("ACK:LED:OFF\n".encode())
                        # Add other LED commands here

                # Simple on/off commands
                elif command.upper() == "ON":
                    await self._ble_client.writePower("On")
                    self.serial.write("ACK:ON\n".encode())

                elif command.upper() == "OFF":
                    await self._ble_client.writePower("Off")
                    self.serial.write("ACK:OFF\n".encode())

                # Mark the task as done
                self._command_queue.task_done()

            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Command processor error: {e}")

            # Small delay between commands
            await asyncio.sleep(0.01)

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

                        # Process commands in test mode
                        # [rest of your test mode code here]
                        # Standard LED protocol format:
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

                        # [rest of your test mode command processing]

                # Avoid tight loop
                await asyncio.sleep(0.1)

        except Exception as e:
            print(f"Error in Arduino test listener: {e}")
        finally:
            self.is_listening = False

        return True

    def stop_listening(self):
        """Stop the serial listener"""
        self._stop_event.set()
        self.is_listening = False
        print("Stopping Arduino serial listener")
