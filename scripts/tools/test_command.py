#!/usr/bin/env python3
"""
Test sending a discard command to BalatroMCP
"""

import json
import time

# Create a command file that the mod can read
command = {
    "action": "discard",
    "params": {"indices": [1, 3, 5, 6, 7]},  # Card indices to discard
    "timestamp": time.time(),
}

# Write to a file the mod can check
with open(
    "/mnt/c/Users/whokn/AppData/Roaming/Balatro/mods/BalatroMCP/command.json", "w"
) as f:
    json.dump(command, f)

print("Command written. The mod should pick it up on next update cycle.")
