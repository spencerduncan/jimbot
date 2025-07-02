# Headless Balatro Mod Usage Guide

## Overview

The BalatroMCP mod enables Balatro to run in headless mode for AI integration. This guide explains how to install, configure, and use the mod with the JimBot system.

## Installation

1. **Copy the mod to Balatro**:
   ```bash
   # Copy the mods folder to your Balatro installation
   cp -r mods/ /path/to/balatro/
   ```

2. **Test with mock server**:
   ```bash
   # Start the test event bus server
   python3 mods/BalatroMCP/test_server.py
   
   # In another terminal, run Balatro
   ./run_balatro.sh
   ```

## Configuration

Edit `mods/BalatroMCP/config.json`:

```json
{
  "event_bus_url": "http://localhost:8080/api/v1/events",
  "headless": true,
  "auto_play": false,
  "game_speed_multiplier": 4,
  "debug": true
}
```

### For AI Integration

To enable AI control:
1. Set `"auto_play": true`
2. Ensure your AI decision service is running
3. The mod will execute actions received from the AI

## Testing the Mod

### 1. Verify Headless Mode

When running with `"headless": true`, you should see:
- No game window appears (or a black window)
- Console shows mod initialization messages
- CPU usage is lower than normal

### 2. Check Event Streaming

With the test server running:
```bash
# Terminal 1: Start test server
python3 mods/BalatroMCP/test_server.py

# Terminal 2: Run Balatro
./run_balatro.sh

# You should see events like:
# [2024-01-15 10:30:45] Received batch with 3 events
#   Event: HEARTBEAT from BalatroMCP
#   Event: GAME_STATE from BalatroMCP
#     Ante: 1, Round: 1
#     Money: $4, Chips: 300
```

### 3. Test Action Execution

Enable auto-play and send test actions:
```python
# Example: Send action to the mod
import requests

action = {
    "type": "ACTION_RESPONSE",
    "payload": {
        "action": "select_small_blind",
        "params": {}
    }
}

requests.post("http://localhost:8080/api/v1/actions", json=action)
```

## Integration with JimBot

### 1. Start Required Services

```bash
# Start Memgraph
docker run -p 7687:7687 memgraph/memgraph-platform

# Start Event Bus (when implemented)
python -m jimbot.event_bus.server

# Start Ray head node
ray start --head
```

### 2. Configure Mod for JimBot

Update `config.json`:
```json
{
  "event_bus_url": "http://localhost:8000/api/v1/events",
  "auto_play": true,
  "ai_decision_timeout_ms": 1000
}
```

### 3. Run Headless Balatro

```bash
# Run in headless mode with mod
./run_balatro.sh --headless
```

## Troubleshooting

### Mod Not Loading

1. Check Love2D console for errors
2. Verify mod files are in correct location
3. Check `balatro_mcp.log` for details

### Events Not Sending

1. Verify event bus URL is correct
2. Check network connectivity
3. Look for errors in mod log

### Headless Mode Issues

1. If window still appears, verify `headless` is `true` in config
2. Check if other mods are conflicting
3. Try disabling sound with `"disable_sound": true`

### Performance Problems

1. Reduce `game_speed_multiplier` to 2 or 1
2. Increase `batch_window_ms` to 200-500
3. Check CPU usage of event processing

## Development Tips

### Adding Custom Events

In `game_state_extractor.lua`:
```lua
function GameStateExtractor:extract_custom_data()
    return {
        -- Your custom data here
    }
end
```

### Adding New Actions

In `action_executor.lua`:
```lua
self.action_handlers["custom_action"] = function(params) 
    -- Your action implementation
end
```

### Debugging

Enable verbose logging:
```json
{
  "debug": true,
  "log_level": "DEBUG"
}
```

## Next Steps

1. Implement the Event Bus component in Python
2. Create the Ray RLlib integration
3. Connect Memgraph for knowledge queries
4. Build the full training pipeline

The headless mod is now ready for integration with the JimBot AI system!