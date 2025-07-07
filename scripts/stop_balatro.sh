#!/bin/bash

# Stop Balatro if running

PID_FILE="$HOME/jimbot/balatro.pid"

if [ ! -f "$PID_FILE" ]; then
    echo "Balatro is not running (no PID file found)"
    exit 0
fi

PID=$(cat "$PID_FILE")

if ps -p "$PID" > /dev/null 2>&1; then
    echo "Stopping Balatro (PID: $PID)..."
    kill "$PID"
    
    # Wait for process to exit
    sleep 1
    
    if ps -p "$PID" > /dev/null 2>&1; then
        echo "Process didn't stop gracefully, force killing..."
        kill -9 "$PID"
    fi
    
    rm "$PID_FILE"
    echo "Balatro stopped"
else
    echo "Balatro process (PID: $PID) not found, cleaning up PID file"
    rm "$PID_FILE"
fi