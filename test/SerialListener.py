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
                Utils.printLog(f"Arduino requested color change to RGB({r},{g},{b})")
                await client.writeColor(r, g, b)
            except (ValueError, IndexError):
                Utils.printLog(f"Invalid color command: {command}")

        # Log any unrecognized commands for debugging
        else:
            Utils.printLog(f"Received unrecognized command: {command}")

    except Exception as e:
        Utils.printLog(f"Error processing Arduino command: {e}")
