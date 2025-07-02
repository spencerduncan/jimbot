#!/bin/bash

# Stop Windows Balatro launched from WSL

PID_FILE="$HOME/jimbot/windows_balatro.pid"

if [ ! -f "$PID_FILE" ]; then
    echo "No Windows Balatro PID file found."
    echo "The game might not be running or was started differently."
    exit 1
fi

# Try to kill via taskkill (Windows command)
echo "Attempting to stop Windows Balatro..."
taskkill.exe /F /IM "Balatro.exe" 2>/dev/null

if [ $? -eq 0 ]; then
    echo "Windows Balatro stopped successfully"
    rm "$PID_FILE"
else
    echo "Could not stop Balatro via taskkill."
    echo "Please close the game manually through Windows."
    rm "$PID_FILE"
fi