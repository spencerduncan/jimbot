# Development Tools

This directory contains utility scripts for development and debugging.

## Scripts

- `monitor_events.py` - Simple HTTP server to monitor events from BalatroMCP
- `parse_state.py` - Parse and analyze Balatro game state data
- `play_game.py` - Automated game playing script for testing
- `send_command.py` - Send commands to the Balatro game
- `test_command.py` - Test command execution
- `test_event_bus.sh` - Test the event bus connectivity
- `events.html` - Web-based event monitoring interface

## Usage

Most Python scripts can be run directly:

```bash
python monitor_events.py
python send_command.py <command>
```

The shell script can be executed:

```bash
./test_event_bus.sh
```
