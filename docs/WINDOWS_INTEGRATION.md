# Windows Balatro Integration Guide

This guide explains how to run Windows Balatro with the BalatroMCP mod from WSL.

## Prerequisites

- Windows Balatro installed (Steam or standalone)
- WSL (Windows Subsystem for Linux) installed
- Access to Windows filesystem from WSL (`/mnt/c/`)

## Setup

1. **Install the mod to Windows Balatro:**
   ```bash
   # If your Windows username differs from WSL username:
   WINDOWS_USER=YourWindowsUsername ./install_mod_windows.sh
   
   # Otherwise just run:
   ./install_mod_windows.sh
   ```

2. **Start the Event Bus server** (in a separate terminal):
   ```bash
   python mods/BalatroMCP/test_server.py
   ```

3. **Launch Windows Balatro with the mod:**
   ```bash
   ./run_windows_balatro.sh
   ```

## File Locations

- **Windows Balatro executable:** 
  - Steam: `C:\Program Files (x86)\Steam\steamapps\common\Balatro\Balatro.exe`
  - Standalone: `C:\Users\<username>\AppData\Local\Balatro\Balatro.exe`

- **Mod installation directory:**
  - `C:\Users\<username>\AppData\Roaming\Balatro\mods\BalatroMCP\`

- **WSL paths:**
  - Windows C: drive: `/mnt/c/`
  - Mod source: `~/jimbot/mods/BalatroMCP/`

## Scripts

- `install_mod_windows.sh` - Installs/updates the mod to Windows Balatro
- `run_windows_balatro.sh` - Launches Windows Balatro with the mod
- `stop_windows_balatro.sh` - Attempts to stop Windows Balatro

## Configuration

The mod configuration file is located at:
- Windows: `%APPDATA%\Balatro\mods\BalatroMCP\config.json`
- WSL: `/mnt/c/Users/<username>/AppData/Roaming/Balatro/mods/BalatroMCP/config.json`

Key settings for Windows:
- `headless`: Set to `false` for Windows GUI
- `disable_sound`: Set to `false` to keep sound enabled
- `game_speed_multiplier`: Set to 1 for normal speed

## Troubleshooting

1. **Balatro not found:** Edit `run_windows_balatro.sh` and update the `BALATRO_EXE` path

2. **Permission denied:** Make sure scripts are executable:
   ```bash
   chmod +x *.sh
   ```

3. **Mod not loading:** Check the Balatro logs at:
   - `%APPDATA%\Balatro\mods\BalatroMCP\balatro_mcp.log`

4. **Can't connect to Event Bus:** Ensure the test server is running and accessible at `http://localhost:8080`

## Notes

- The game runs as a native Windows process, not through WSL
- Use Windows Task Manager to force-close if needed
- Mod files are automatically copied from WSL to Windows on each run
- Windows file paths use backslashes, but the mod handles both formats