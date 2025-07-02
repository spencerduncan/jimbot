#!/bin/bash

# Run Windows Balatro from WSL with BalatroMCP mod
# This script handles launching Windows Balatro with proper mod directory setup

# Windows paths (adjust these based on your installation)
WINDOWS_USER="${WINDOWS_USER:-whokn}"  # Use environment variable or default to whokn
BALATRO_EXE="/mnt/c/Program Files (x86)/Steam/steamapps/common/Balatro/Balatro.exe"
BALATRO_ALT="/mnt/c/Users/$WINDOWS_USER/AppData/Local/Balatro/Balatro.exe"
MOD_SOURCE_DIR="$(pwd)/mods/BalatroMCP"
MOD_DEST_DIR="/mnt/c/Users/$WINDOWS_USER/AppData/Roaming/Balatro/mods/BalatroMCP"

# PID file location
PID_FILE="$HOME/jimbot/windows_balatro.pid"

# Check if already running
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    if ps -p "$OLD_PID" > /dev/null 2>&1; then
        echo "Windows Balatro is already running (PID: $OLD_PID)"
        echo "Use ./stop_windows_balatro.sh to stop it"
        exit 1
    else
        rm "$PID_FILE"
    fi
fi

# Find Balatro executable
if [ -f "$BALATRO_EXE" ]; then
    BALATRO_PATH="$BALATRO_EXE"
elif [ -f "$BALATRO_ALT" ]; then
    BALATRO_PATH="$BALATRO_ALT"
else
    echo "Error: Balatro.exe not found!"
    echo "Please check the following paths:"
    echo "  - $BALATRO_EXE"
    echo "  - $BALATRO_ALT"
    echo ""
    echo "If Balatro is installed elsewhere, please edit this script."
    exit 1
fi

echo "Found Balatro at: $BALATRO_PATH"

# Create mod directory if it doesn't exist
echo "Setting up BalatroMCP mod..."
mkdir -p "$(dirname "$MOD_DEST_DIR")"

# Copy mod files to Windows mod directory
echo "Copying mod files to: $MOD_DEST_DIR"
rm -rf "$MOD_DEST_DIR"
mkdir -p "$MOD_DEST_DIR"
cp -r "$MOD_SOURCE_DIR"/* "$MOD_DEST_DIR/"

# Convert paths to Windows format for the executable
WINDOWS_PATH=$(echo "$BALATRO_PATH" | sed 's|/mnt/c/|C:/|' | sed 's|/|\\|g')

# Launch Balatro through Windows
echo "Launching Windows Balatro..."
cmd.exe /c start "" "$WINDOWS_PATH" &
PID=$!

# Save PID
echo $PID > "$PID_FILE"

echo "Windows Balatro launched (WSL PID: $PID)"
echo "Mod installed at: $MOD_DEST_DIR"
echo "To stop: ./stop_windows_balatro.sh"
echo ""
echo "Note: The game runs as a Windows process. Use Task Manager to close if needed."