# JimBot Protocol Buffer Schemas

This directory contains the Protocol Buffer schemas for JimBot's event system, specifically designed for Balatro game event handling and action issuing.

## Directory Structure

```
proto/
└── jimbot/
    └── events/
        └── v1/
            ├── base.proto           # Base event types and common messages
            ├── balatro_events.proto # Balatro-specific game events
            └── balatro_actions.proto # Action commands for game control
```

## Schema Overview

### base.proto
Defines the foundational event types that all other events extend:
- `Event`: Base event message with metadata
- `GameStateEvent`: Generic game state information
- `BlindInfo`: Information about game blinds

### balatro_events.proto
Extends base events with Balatro-specific information:
- `BalatroGameStateEvent`: Complete game state including jokers, cards, score
- `BalatroTriggerEvent`: Joker/card trigger effects with cascade support
- `RoundSummaryEvent`: Summary of completed rounds
- `GameSummaryEvent`: Full game session summary

### balatro_actions.proto
Defines action commands for controlling the game:
- `BalatroActionCommand`: Base command with action-specific payloads
- Action types: PlayHand, Discard, Shop, Reorder, UseConsumable, etc.
- `BalatroActionResult`: Response after executing actions
- `ActionValidationRules`: Rules for validating actions

## Key Features

### Event Design
- Timestamps on all events for precise timing analysis
- Correlation IDs for tracking related events
- Extensible metadata maps for additional context
- Support for event cascades and trigger chains

### Balatro-Specific Extensions
- Complete joker parameters and effects tracking
- Card enhancements, seals, and editions
- Trigger context with hand types and scoring details
- Shop state and consumable management
- Round and game summary analytics

### Action Commands
- Type-safe action definitions
- Validation rules to prevent invalid actions
- Batch action support for complex sequences
- Execution results with timing information

## Usage Examples

### Generating Code
```bash
# Generate Python code
protoc --python_out=../jimbot/proto/ jimbot/events/v1/*.proto

# Generate Rust code (if using prost)
protoc --prost_out=../services/event-bus-rust/src/proto/ jimbot/events/v1/*.proto

# Using buf for multi-language generation
buf generate
```

### Example Event Creation (Python)
```python
from jimbot.proto.jimbot.events.v1 import balatro_events_pb2
from google.protobuf import timestamp_pb2

# Create a game state event
state = balatro_events_pb2.BalatroGameStateEvent()
state.base.phase = "PLAY_HAND"
state.base.score = 1500
state.base.money = 25
state.round = 3
state.ante = 1

# Add a joker
joker = state.jokers.add()
joker.id = "j_mult"
joker.name = "Mult Joker"
joker.params["mult"] = 4.0
joker.position = 0

# Add cards to hand
card = state.hand.add()
card.id = "c_h_a"
card.suit = "Hearts"
card.rank = "A"
card.enhancement = "gold"
```

### Example Action Command (Python)
```python
from jimbot.proto.jimbot.events.v1 import balatro_actions_pb2

# Create a play hand action
action = balatro_actions_pb2.BalatroActionCommand()
action.action_id = "act_001"
action.action_type = "play_hand"

play = action.play_hand
play.card_ids.extend(["c_h_a", "c_h_k", "c_h_q", "c_h_j", "c_h_10"])
play.expected_hand_type = "flush"
```

## Validation Rules

### Event Validation
- All events must have unique event_id
- Timestamps must be valid
- Card suits must be one of: Hearts, Diamonds, Clubs, Spades
- Card ranks must be valid: A, 2-10, J, Q, K
- Enhancements must be recognized types

### Action Validation
- Action IDs must be unique within a session
- Card IDs in actions must exist in current game state
- Shop actions must have sufficient money
- Actions must be valid for current game phase

## Best Practices

1. **Use Correlation IDs**: Link related events and actions
2. **Include Metadata**: Add relevant context in metadata maps
3. **Validate Early**: Check action validity before sending
4. **Track Timing**: Use timestamps for performance analysis
5. **Handle Cascades**: Process trigger chains correctly

## Integration Points

- **MCP Server**: Receives events from BalatroMCP mod
- **Event Bus**: Distributes events to subscribers
- **Ray RLlib**: Consumes state events for training
- **Analytics**: Processes summary events for metrics

## Version Management

The `v1` directory indicates schema version 1. Future breaking changes will create new version directories (v2, v3, etc.) to maintain backward compatibility.