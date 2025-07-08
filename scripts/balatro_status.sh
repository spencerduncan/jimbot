#!/bin/bash

# Check Balatro status

PID_FILE="$HOME/jimbot/balatro.pid"

if [ ! -f "$PID_FILE" ]; then
    echo "Balatro is not running"
    exit 0
fi

PID=$(cat "$PID_FILE")

if ps -p "$PID" > /dev/null 2>&1; then
    echo "Balatro is running (PID: $PID)"
    echo "To view logs: tail -f $(dirname "$0")/balatro.log"
    echo "To stop: ./stop_balatro.sh"
else
    echo "Balatro is not running (stale PID file)"
    rm "$PID_FILE"
fi