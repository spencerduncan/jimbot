# BalatroMCP - Headless Balatro Mod for AI Integration

## Overview

BalatroMCP is a Love2D mod for Balatro that enables headless operation and AI
integration. It extracts game state, sends events to an external event bus, and
can execute AI-generated actions automatically.

## Features

- **Headless Mode**: Disables rendering for faster execution and server
  deployment
- **Game State Extraction**: Captures complete game state including cards,
  jokers, shop, etc.
- **Event Streaming**: Sends game events via REST API with configurable batching
- **AI Control**: Executes actions received from AI decision-making systems
- **Configurable**: JSON-based configuration for all settings
- **Logging**: Comprehensive logging with multiple levels

## Installation

1. Place the `mods` folder in your Balatro game directory
2. The mod will auto-initialize when Balatro starts
3. Configure settings in `mods/BalatroMCP/config.json`

## Configuration

The mod creates a default `config.json` on first run:

```json
{
  "event_bus_url": "http://localhost:8080/api/v1/events",
  "batch_window_ms": 100,
  "headless": true,
  "auto_play": false,
  "debug": true,
  "game_speed_multiplier": 4
}
```

### Key Settings

- `event_bus_url`: URL of the event bus endpoint
- `batch_window_ms`: Time window for event batching (default: 100ms)
- `headless`: Enable headless mode (no rendering)
- `auto_play`: Enable AI control of the game
- `game_speed_multiplier`: Speed up gameplay (1-4x)

## Event Schema

Events follow the Protocol Buffers schema defined in the JimBot project:

### Game State Event

```json
{
  "type": "GAME_STATE",
  "source": "BalatroMCP",
  "payload": {
    "game_id": "seed_12345",
    "ante": 3,
    "round": 2,
    "chips": 300,
    "mult": 4,
    "money": 15,
    "jokers": [...],
    "hand": [...],
    "shop_items": {...}
  }
}
```

### Decision Request

```json
{
  "type": "LEARNING_DECISION",
  "subtype": "REQUEST",
  "payload": {
    "request_id": "REQ-123456",
    "game_state": {...},
    "available_actions": ["play_hand", "discard", "sort_hand"],
    "time_limit_ms": 1000
  }
}
```

## API Integration

The mod expects to communicate with an event bus that implements:

- `POST /api/v1/events` - Single event submission
- `POST /api/v1/events/batch` - Batch event submission

## Actions

The mod can execute these actions when `auto_play` is enabled:

### Playing Phase

- `play_hand` - Play highlighted cards
- `discard` - Discard highlighted cards
- `sort_hand` - Sort hand by rank/suit
- `select_card` - Toggle card selection

### Shop Phase

- `buy_joker` - Purchase joker by index
- `buy_booster` - Purchase booster pack
- `buy_voucher` - Purchase voucher
- `sell_joker` - Sell joker by position
- `reroll_shop` - Reroll shop items
- `skip_shop` - Exit shop

### Blind Selection

- `select_small_blind` - Choose small blind
- `select_big_blind` - Choose big blind
- `select_boss_blind` - Choose boss blind
- `skip_blind` - Skip current blind

## Development

### Module Structure

- `main.lua` - Entry point and initialization
- `config.lua` - Configuration management
- `logger.lua` - Logging utilities
- `headless_override.lua` - Rendering disablement
- `game_state_extractor.lua` - State extraction logic
- `event_bus_client.lua` - HTTP/REST communication
- `event_aggregator.lua` - Event batching
- `action_executor.lua` - AI action execution

### Adding New Features

1. Hook into Balatro's functions in `main.lua`
2. Extract relevant data in `game_state_extractor.lua`
3. Add new event types in `event_aggregator.lua`
4. Implement actions in `action_executor.lua`

## Performance

- Headless mode runs at 4x speed by default
- Event batching reduces network overhead
- Minimal CPU usage with rendering disabled
- Configurable game speed multiplier

## Troubleshooting

### Events not sending

- Check `event_bus_url` in config
- Verify event bus is running
- Check logs in `balatro_mcp.log`

### Actions not executing

- Ensure `auto_play` is enabled
- Check action parameters match expected format
- Verify game is in correct phase for action

### Performance issues

- Reduce `batch_window_ms` for faster updates
- Decrease `game_speed_multiplier`
- Check CPU usage of event processing

## Future Enhancements

- WebSocket support for real-time communication
- gRPC client for better performance
- Protocol Buffers serialization
- Advanced game state predictions
- Replay system for debugging
