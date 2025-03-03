import asyncio
import serial
import Utils


class ArduinoSerialListener:
    def __init__(self, serial_port="COM3", baud_rate=9600):
        self.serial_port = serial_port
        self.baud_rate = baud_rate
        self.ser = None
        self.is_listening = False

    def connect(self):
        try:
            self.ser = serial.Serial(self.serial_port, self.baud_rate, timeout=0.1)
            Utils.printLog(f"Connected to Arduino on {self.serial_port}")
            return True
        except Exception as e:
            Utils.printLog(f"Failed to connect to Arduino: {e}")
            return False

    def disconnect(self):
        if self.ser and self.ser.is_open:
            self.ser.close()
            Utils.printLog("Disconnected from Arduino")

    async def start_listening(self, client):
        """Start listening for Arduino commands"""
        self.is_listening = True
        Utils.printLog("Starting Arduino serial listener...")

        while self.is_listening:
            if self.ser and self.ser.is_open:
                try:
                    if self.ser.in_waiting > 0:
                        message = self.ser.readline().decode("utf-8").strip()
                        if message:
                            Utils.printLog(f"Arduino sent: {message}")
                            await self.process_command(message, client)
                except Exception as e:
                    Utils.printLog(f"Error reading from serial port: {e}")
            await asyncio.sleep(0.1)

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
