# Protocol Buffer Schemas

This directory contains all Protocol Buffer schema definitions for the Jimbot event system.

## Overview

The Protocol Buffer schemas define a comprehensive event system that maintains backward compatibility with the existing BalatroMCP JSON format while providing:

- **Type Safety**: Strongly typed event definitions
- **Performance**: Efficient binary serialization
- **Language Support**: Code generation for Python, Rust, and TypeScript
- **Versioning**: Built-in version management and migration support
- **JSON Compatibility**: Seamless conversion between JSON and protobuf formats

## Schema Files

### Core Event Schemas

- **`balatro_events.proto`**: Main event definitions including:
  - Base `Event` wrapper with metadata
  - All game event types (GameState, HandPlayed, JokerTriggered, etc.)
  - Learning and strategy request/response events
  - Knowledge updates and metrics
  - Support for custom events via `google.protobuf.Any`

- **`resource_coordinator.proto`**: Resource coordination protocol for distributed processing

### Compatibility and Support

- **`json_compatibility.proto`**: JSON-Protobuf conversion schema
  - Bidirectional conversion service
  - Field mapping configuration
  - Legacy format support

- **`version.proto`**: Version management and migration
  - Schema versioning
  - Migration definitions
  - Version negotiation protocol

## Event Types

### Game Flow Events
- `GameStateEvent`: Complete game state snapshot
- `GameStartEvent`: Game initialization
- `GameOverEvent`: Game completion
- `RoundChangedEvent`: Round transitions
- `PhaseChangedEvent`: Game phase transitions

### Action Events
- `HandPlayedEvent`: Card hand played
- `CardsDiscardedEvent`: Cards discarded
- `CardPurchasedEvent`: Shop purchase
- `CardSoldEvent`: Item sold
- `CardEnhancedEvent`: Card enhancement applied

### Resource Events
- `MoneyChangedEvent`: Currency changes
- `ScoreChangedEvent`: Score updates
- `JokersChangedEvent`: Joker collection changes

### AI/Learning Events
- `LearningDecisionRequest`: Request for AI decision
- `LearningDecisionResponse`: AI decision response
- `StrategyRequest`: Strategy recommendation request
- `StrategyResponse`: Recommended strategy
- `KnowledgeUpdate`: Knowledge graph updates

### System Events
- `HeartbeatEvent`: Connection heartbeat
- `ConnectionTestEvent`: Connection testing
- `ErrorEvent`: Error reporting
- `MetricEvent`: Performance metrics

## Usage

### Generating Code

Run the generation script to create language-specific code:

```bash
cd jimbot/proto
./generate_code.sh
```

This will generate:
- Python code in `jimbot/proto/`
- Rust code in `generated/rust/src/proto/`
- TypeScript code in `generated/typescript/src/proto/`

### Python Example

```python
from jimbot.proto import balatro_events_pb2
from jimbot.infrastructure.serialization import ProtobufSerializer

# Create an event
event = balatro_events_pb2.Event()
event.event_id = "123e4567-e89b-12d3-a456-426614174000"
event.type = balatro_events_pb2.EVENT_TYPE_GAME_STATE
event.source = "BalatroMCP"
event.timestamp = int(time.time() * 1000)

# Add game state
event.game_state.in_game = True
event.game_state.ante = 1
event.game_state.money = 4

# Serialize
serializer = ProtobufSerializer()
data = serializer.serialize(event)

# JSON compatibility
json_event = serializer.serialize(event, format=SerializationFormat.JSON)
```

### JSON Compatibility

The system maintains full compatibility with the existing JSON format:

```python
from jimbot.infrastructure.serialization import JsonCompatibilityLayer

compat = JsonCompatibilityLayer()

# Convert JSON to Protobuf
json_event = {
    "type": "GAME_STATE",
    "source": "BalatroMCP",
    "payload": {
        "in_game": True,
        "ante": 1,
        "money": 4
    }
}

proto_event = compat.json_to_proto(json_event)

# Convert Protobuf to JSON
json_event = compat.proto_to_json(proto_event)
```

## Version Management

The schema includes version information in each event:

```protobuf
message Event {
  string event_id = 1;
  int64 timestamp = 2;
  EventType type = 3;
  string source = 4;
  int32 version = 5;  // Schema version
  // ...
}
```

Version compatibility is handled through:
- Forward compatibility: New fields with higher numbers
- Backward compatibility: Optional fields, reserved numbers
- Migration support: Version negotiation and transformation

## Development Guidelines

1. **Adding New Events**:
   - Add event type to `EventType` enum
   - Define event message
   - Add to `Event.payload` oneof
   - Update JSON compatibility mappings

2. **Field Evolution**:
   - Never change field numbers
   - Never change field types
   - Use reserved for deprecated fields
   - Add new fields with higher numbers

3. **Testing**:
   - Always test JSON compatibility
   - Verify code generation works
   - Test with multiple language implementations

## Dependencies

- Protocol Buffers 3.x
- Python: `protobuf>=4.25.0`
- Rust: `prost`, `tonic` (optional)
- TypeScript: `@bufbuild/protobuf`

## Buf Integration

The project uses [Buf](https://buf.build) for schema management:

- `buf.yaml`: Lint and breaking change configuration
- `buf.gen.*.yaml`: Language-specific generation configs
- Run `buf lint` to check schema quality
- Run `buf breaking` to detect breaking changes