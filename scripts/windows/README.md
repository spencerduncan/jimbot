# Windows Scripts

This directory contains scripts for running Balatro on Windows systems.

## Scripts

- `install_mod_windows.sh` - Install the BalatroMCP mod on Windows
- `run_windows_balatro.sh` - Start Balatro with the mod enabled
- `stop_windows_balatro.sh` - Stop the running Balatro instance

## Usage

These scripts are designed to be run from Git Bash or WSL on Windows:

```bash
# Install the mod
./install_mod_windows.sh

# Start Balatro
./run_windows_balatro.sh

# Stop Balatro
./stop_windows_balatro.sh
```

Note: These scripts manage the Balatro process and create PID files for
tracking.
