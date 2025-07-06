#!/bin/bash

# Run Balatro on Linux with Love2D in background
# This script handles the Windows mod directory mounting

# Set the mod directory from Windows
export BALATRO_MOD_DIR="/mnt/c/Users/whokn/AppData/Roaming/Balatro/mods"

# Set the save directory (you can modify this to sync with Windows saves if needed)
export BALATRO_SAVE_DIR="$HOME/.local/share/Balatro"

# Create save directory if it doesn't exist
mkdir -p "$BALATRO_SAVE_DIR"

# PID file location
PID_FILE="$HOME/jimbot/balatro.pid"

# Check if already running
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    if ps -p "$OLD_PID" > /dev/null 2>&1; then
        echo "Balatro is already running (PID: $OLD_PID)"
        echo "Use ./stop_balatro.sh to stop it"
        exit 1
    else
        # Clean up stale PID file
        rm "$PID_FILE"
    fi
fi

# Run Balatro with Love2D in background
cd "$(dirname "$0")"
nohup love Balatro.love "$@" > balatro.log 2>&1 &
PID=$!

# Save PID
echo $PID > "$PID_FILE"

echo "Balatro started in background (PID: $PID)"
echo "Logs available at: $(pwd)/balatro.log"
echo "To stop: ./stop_balatro.sh"