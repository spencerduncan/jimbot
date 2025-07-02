#!/bin/bash

# Install or update BalatroMCP mod to Windows Balatro mod directory

# Configuration
WINDOWS_USER="${WINDOWS_USER:-$USER}"  # Can override with environment variable
MOD_SOURCE_DIR="$(pwd)/mods/BalatroMCP"
MOD_DEST_DIR="/mnt/c/Users/$WINDOWS_USER/AppData/Roaming/Balatro/mods/BalatroMCP"
BACKUP_DIR="$(pwd)/mod_backups/$(date +%Y%m%d_%H%M%S)"

echo "=== BalatroMCP Mod Installer for Windows ==="
echo ""

# Check if source mod exists
if [ ! -d "$MOD_SOURCE_DIR" ]; then
    echo "Error: Mod source directory not found at: $MOD_SOURCE_DIR"
    exit 1
fi

# Check if Windows user directory exists
if [ ! -d "/mnt/c/Users/$WINDOWS_USER" ]; then
    echo "Error: Windows user directory not found: /mnt/c/Users/$WINDOWS_USER"
    echo "Please set WINDOWS_USER environment variable to your Windows username"
    echo "Example: WINDOWS_USER=YourWindowsUsername ./install_mod_windows.sh"
    exit 1
fi

# Create mod parent directory if it doesn't exist
MOD_PARENT_DIR="$(dirname "$MOD_DEST_DIR")"
if [ ! -d "$MOD_PARENT_DIR" ]; then
    echo "Creating Balatro mods directory at: $MOD_PARENT_DIR"
    mkdir -p "$MOD_PARENT_DIR"
fi

# Backup existing mod if present
if [ -d "$MOD_DEST_DIR" ]; then
    echo "Found existing mod installation. Creating backup..."
    mkdir -p "$BACKUP_DIR"
    cp -r "$MOD_DEST_DIR" "$BACKUP_DIR/"
    echo "Backup created at: $BACKUP_DIR"
fi

# Install/update mod
echo "Installing BalatroMCP mod..."
rm -rf "$MOD_DEST_DIR"
mkdir -p "$MOD_DEST_DIR"
cp -r "$MOD_SOURCE_DIR"/* "$MOD_DEST_DIR/"

# Create config in a subdirectory to avoid SMODS confusion
CONFIG_DIR="$MOD_DEST_DIR/config"
mkdir -p "$CONFIG_DIR"
CONFIG_FILE="$CONFIG_DIR/config.json"

echo "Creating default configuration..."
cat > "$CONFIG_FILE" << EOF
{
  "event_bus_url": "http://localhost:8080/api/v1/events",
  "event_bus_timeout": 5000,
  "batch_window_ms": 100,
  "max_batch_size": 50,
  "heartbeat_interval_ms": 5000,
  "max_retries": 3,
  "retry_delay_ms": 1000,
  "exponential_backoff": true,
  "headless": false,
  "disable_sound": false,
  "game_speed_multiplier": 1,
  "auto_play": false,
  "debug": true,
  "log_file": "mods/BalatroMCP/balatro_mcp.log",
  "log_level": "INFO",
  "ai_decision_timeout_ms": 1000,
  "fallback_to_random": true,
  "cache_ai_decisions": true
}
EOF

echo ""
echo "Installation complete!"
echo "Mod installed at: $MOD_DEST_DIR"
echo ""
echo "To run Balatro with the mod:"
echo "  ./run_windows_balatro.sh"
echo ""
echo "Note: Make sure the Event Bus server is running before starting Balatro."