# Protocol Buffers Style Guide for JimBot

This guide provides comprehensive Protocol Buffers (protobuf) best practices and style guidelines for the JimBot project, focusing on event streaming, game state management, and service interfaces.

## Table of Contents
1. [File Organization](#file-organization)
2. [Naming Conventions](#naming-conventions)
3. [Message Design Patterns](#message-design-patterns)
4. [Event Streaming Patterns](#event-streaming-patterns)
5. [Game State Messages](#game-state-messages)
6. [Versioning and Compatibility](#versioning-and-compatibility)
7. [Performance Optimization](#performance-optimization)
8. [gRPC Service Definitions](#grpc-service-definitions)

## File Organization

### Directory Structure
```
jimbot/
├── proto/
│   ├── common/           # Shared message definitions
│   │   ├── timestamp.proto
│   │   ├── metadata.proto
│   │   └── enums.proto
│   ├── events/          # Event messages
│   │   ├── game_events.proto
│   │   ├── system_events.proto
│   │   └── analytics_events.proto
│   ├── state/           # State messages
│   │   ├── game_state.proto
│   │   ├── player_state.proto
│   │   └── joker_state.proto
│   └── services/        # Service definitions
│       ├── mcp_service.proto
│       ├── memgraph_service.proto
│       └── ray_service.proto
```

### File Naming Rules
- Use `snake_case.proto` for file names
- Group related messages in the same file
- Service definitions and their request/response messages should be in the same file
- Create an obvious entry file (e.g., `jimbot.proto`) that imports key definitions

### Package Structure
```protobuf
syntax = "proto3";

package jimbot.events.v1;

option java_package = "com.jimbot.proto.events.v1";
option java_multiple_files = true;
option java_outer_classname = "GameEventsProto";
option go_package = "github.com/jimbot/proto/events/v1;eventsv1";
```

## Naming Conventions

### Messages
```protobuf
// Use PascalCase for message names
message GameStateUpdate {
  // Use snake_case for field names
  string game_id = 1;
  int32 current_ante = 2;
  repeated JokerState active_jokers = 3;
}
```

### Enums
```protobuf
// Enum names in PascalCase
enum GamePhase {
  // Suffix with _UNSPECIFIED for zero value
  GAME_PHASE_UNSPECIFIED = 0;
  // Prefix with enum name in UPPER_SNAKE_CASE
  GAME_PHASE_BLIND_SELECT = 1;
  GAME_PHASE_SHOP = 2;
  GAME_PHASE_PLAYING_HAND = 3;
  GAME_PHASE_SCORING = 4;
}
```

### Services
```protobuf
// Service names in PascalCase
service GameEventService {
  // RPC method names in PascalCase
  rpc StreamGameEvents(StreamGameEventsRequest) returns (stream GameEvent);
  rpc SendPlayerAction(PlayerActionRequest) returns (PlayerActionResponse);
}
```

## Message Design Patterns

### Event Message Pattern
```protobuf
// Base event structure with metadata
message GameEvent {
  // Common event metadata
  EventMetadata metadata = 1;
  
  // Event-specific payload using oneof
  oneof event {
    CardPlayed card_played = 10;
    JokerPurchased joker_purchased = 11;
    HandScored hand_scored = 12;
    BlindDefeated blind_defeated = 13;
    GameOver game_over = 14;
  }
}

message EventMetadata {
  string event_id = 1;
  google.protobuf.Timestamp timestamp = 2;
  string game_id = 3;
  int32 sequence_number = 4;
  string player_id = 5;
}
```

### State Snapshot Pattern
```protobuf
message GameStateSnapshot {
  // Metadata about the snapshot
  SnapshotMetadata metadata = 1;
  
  // Current game phase
  GamePhase phase = 2;
  
  // Player state
  PlayerState player = 3;
  
  // Game board state
  BoardState board = 4;
  
  // Active effects and modifiers
  repeated ActiveEffect active_effects = 5;
}

message SnapshotMetadata {
  string snapshot_id = 1;
  google.protobuf.Timestamp created_at = 2;
  int64 event_sequence = 3;  // Event that triggered snapshot
  string checksum = 4;        // For validation
}
```

### Command Pattern
```protobuf
message PlayerCommand {
  CommandMetadata metadata = 1;
  
  oneof command {
    PlayCardsCommand play_cards = 10;
    DiscardCardsCommand discard_cards = 11;
    PurchaseItemCommand purchase_item = 12;
    UseConsumableCommand use_consumable = 13;
    SkipBlindCommand skip_blind = 14;
  }
}

message CommandMetadata {
  string command_id = 1;
  string player_id = 2;
  google.protobuf.Timestamp issued_at = 3;
  int32 retry_count = 4;
}
```

## Event Streaming Patterns

### Event Aggregation Pattern
```protobuf
// For batching multiple events efficiently
message EventBatch {
  repeated GameEvent events = 1 [packed=true];
  BatchMetadata metadata = 2;
}

message BatchMetadata {
  google.protobuf.Timestamp batch_start = 1;
  google.protobuf.Timestamp batch_end = 2;
  int32 event_count = 3;
  int32 compressed_size = 4;
}
```

### Stream Control Messages
```protobuf
message StreamControl {
  oneof control {
    StreamStart start = 1;
    StreamHeartbeat heartbeat = 2;
    StreamCheckpoint checkpoint = 3;
    StreamEnd end = 4;
  }
}

message StreamCheckpoint {
  int64 last_processed_sequence = 1;
  google.protobuf.Timestamp checkpoint_time = 2;
  map<string, int64> component_offsets = 3;
}
```

## Game State Messages

### Joker State Management
```protobuf
message JokerState {
  string joker_id = 1;
  JokerType type = 2;
  
  // Dynamic properties
  map<string, int32> counters = 3;     // e.g., "hands_played": 5
  map<string, string> properties = 4;   // e.g., "copied_joker": "j_123"
  
  // Position and status
  int32 position = 5;
  bool is_active = 6;
  bool is_eternal = 7;
  bool is_perishable = 8;
  int32 remaining_uses = 9;
  
  // Calculated values
  float current_multiplier = 10;
  int32 current_chips = 11;
}
```

### Card Representation
```protobuf
message Card {
  // Core identity
  Suit suit = 1;
  Rank rank = 2;
  
  // Enhancements and modifiers
  Enhancement enhancement = 3;
  Seal seal = 4;
  Edition edition = 5;
  
  // Dynamic state
  bool is_debuffed = 6;
  bool is_face_down = 7;
  int32 temp_mult_bonus = 8;
  int32 temp_chip_bonus = 9;
}

enum Suit {
  SUIT_UNSPECIFIED = 0;
  SUIT_SPADES = 1;
  SUIT_HEARTS = 2;
  SUIT_CLUBS = 3;
  SUIT_DIAMONDS = 4;
}
```

### Score Calculation Messages
```protobuf
message ScoreCalculation {
  // Initial values
  BaseScore base = 1;
  
  // Step-by-step modifications
  repeated ScoreModification modifications = 2;
  
  // Final result
  FinalScore final = 3;
  
  // For replay and debugging
  repeated string calculation_log = 4;
}

message ScoreModification {
  string source_id = 1;           // Joker or card ID
  ModificationType type = 2;
  int32 chips_added = 3;
  float mult_added = 4;
  float mult_multiplied = 5;
  string description = 6;
}
```

## Versioning and Compatibility

### Field Management Rules
```protobuf
message EvolvingMessage {
  // Original fields (never change numbers)
  string id = 1;
  string name = 2;
  
  // Deprecated field (reserved to prevent reuse)
  reserved 3;
  reserved "old_field_name";
  
  // New fields (use higher numbers)
  string new_field = 10;
  
  // Optional fields for gradual rollout
  optional string experimental_feature = 20;
}
```

### API Versioning
```protobuf
// v1/game_service.proto
package jimbot.api.v1;

service GameService {
  rpc GetGameState(GetGameStateRequest) returns (GameState);
}

// v2/game_service.proto (backward compatible)
package jimbot.api.v2;

import "jimbot/api/v1/game_service.proto";

service GameService {
  // Include all v1 methods
  rpc GetGameState(GetGameStateRequest) returns (GameState);
  
  // Add new v2 methods
  rpc GetGameStateStream(GetGameStateRequest) returns (stream GameState);
}
```

## Performance Optimization

### Field Number Optimization
```protobuf
message OptimizedMessage {
  // Use numbers 1-15 for frequently used fields (1 byte encoding)
  string id = 1;
  int32 score = 2;
  float multiplier = 3;
  
  // Less frequent fields use higher numbers (2 byte encoding)
  string description = 16;
  repeated string tags = 17;
}
```

### Packed Repeated Fields
```protobuf
message PerformanceData {
  // Pack numeric repeated fields for efficiency
  repeated int32 frame_times = 1 [packed=true];
  repeated float cpu_usage = 2 [packed=true];
  repeated int64 timestamps = 3 [packed=true];
  
  // Strings cannot be packed
  repeated string event_names = 4;
}
```

### Size-Optimized Types
```protobuf
message EfficientData {
  // Use appropriate integer types
  int32 small_counter = 1;      // For values < 2^31
  sint32 signed_delta = 2;      // For negative values (zig-zag encoding)
  fixed32 hash_value = 3;       // For values often > 2^28
  
  // Use bytes for binary data
  bytes compressed_data = 4;
  
  // Avoid large messages - split if needed
  DataPart part1 = 5;
  DataPart part2 = 6;
}
```

## gRPC Service Definitions

### Unary RPC Pattern
```protobuf
service MemgraphService {
  // Simple request-response
  rpc QueryJokerSynergies(JokerSynergyRequest) returns (JokerSynergyResponse) {
    option (google.api.http) = {
      post: "/v1/jokers/synergies"
      body: "*"
    };
  }
}

message JokerSynergyRequest {
  repeated string joker_ids = 1;
  int32 max_results = 2;
}

message JokerSynergyResponse {
  repeated JokerSynergy synergies = 1;
  ResponseMetadata metadata = 2;
}
```

### Server Streaming Pattern
```protobuf
service EventStreamService {
  // Server sends stream of events
  rpc SubscribeToEvents(EventSubscription) returns (stream GameEvent) {
    option (google.api.http) = {
      get: "/v1/events/stream"
    };
  }
}

message EventSubscription {
  repeated EventType event_types = 1;
  string start_from = 2;  // Event ID or "latest"
  EventFilter filter = 3;
}
```

### Client Streaming Pattern
```protobuf
service AnalyticsService {
  // Client sends stream of metrics
  rpc RecordMetrics(stream MetricData) returns (MetricSummary);
}

message MetricData {
  string metric_name = 1;
  double value = 2;
  google.protobuf.Timestamp timestamp = 3;
  map<string, string> labels = 4;
}
```

### Bidirectional Streaming Pattern
```protobuf
service GameSessionService {
  // Full duplex communication
  rpc PlayGame(stream PlayerAction) returns (stream GameUpdate) {
    option (google.api.http) = {
      post: "/v1/game/play"
      body: "*"
    };
  }
}

// Client sends actions
message PlayerAction {
  oneof action {
    JoinGame join = 1;
    PlayCards play = 2;
    PurchaseItem purchase = 3;
    EndTurn end_turn = 4;
  }
}

// Server sends updates
message GameUpdate {
  oneof update {
    GameStateChange state_change = 1;
    ScoreUpdate score = 2;
    ShopRefresh shop = 3;
    GameResult result = 4;
  }
}
```

### Error Handling
```protobuf
message ErrorDetail {
  string code = 1;
  string message = 2;
  map<string, string> metadata = 3;
}

message APIResponse {
  oneof result {
    GameState success = 1;
    ErrorDetail error = 2;
  }
  ResponseMetadata metadata = 3;
}

message ResponseMetadata {
  string request_id = 1;
  google.protobuf.Duration processing_time = 2;
  string server_version = 3;
}
```

## Best Practices Summary

1. **Design for Evolution**: Always leave room for future fields and changes
2. **Use Semantic Versioning**: Version your APIs and maintain backward compatibility
3. **Optimize for Common Cases**: Put frequently used fields in positions 1-15
4. **Document Everything**: Add comments explaining field purposes and valid values
5. **Validate Early**: Use protoc-gen-validate or similar for field validation
6. **Monitor Performance**: Track message sizes and serialization times
7. **Test Compatibility**: Always test with older clients when making changes
8. **Use Standard Types**: Prefer google.protobuf.Timestamp over custom time representations

## Example: Complete Event Definition

```protobuf
syntax = "proto3";

package jimbot.events.v1;

import "google/protobuf/timestamp.proto";
import "google/protobuf/duration.proto";

option go_package = "github.com/jimbot/proto/events/v1;eventsv1";

// GameEvent represents any event that occurs during gameplay
message GameEvent {
  // Event metadata (fields 1-5 for efficiency)
  string event_id = 1;
  google.protobuf.Timestamp timestamp = 2;
  string game_id = 3;
  int64 sequence_number = 4;
  string player_id = 5;
  
  // Event-specific data
  oneof payload {
    // Game flow events (10-19)
    GameStarted game_started = 10;
    RoundStarted round_started = 11;
    RoundEnded round_ended = 12;
    GameEnded game_ended = 13;
    
    // Player action events (20-29)
    CardsPlayed cards_played = 20;
    CardsDiscarded cards_discarded = 21;
    ItemPurchased item_purchased = 22;
    ItemSold item_sold = 23;
    ConsumableUsed consumable_used = 24;
    
    // Game state events (30-39)
    HandScored hand_scored = 30;
    BlindRevealed blind_revealed = 31;
    BlindDefeated blind_defeated = 32;
    ShopEntered shop_entered = 33;
    ShopExited shop_exited = 34;
    
    // Joker events (40-49)
    JokerTriggered joker_triggered = 40;
    JokerEvolved joker_evolved = 41;
    JokerDestroyed joker_destroyed = 42;
  }
  
  // Performance tracking
  google.protobuf.Duration processing_time = 100;
  map<string, string> context = 101;
}

// Example of a specific event payload
message HandScored {
  // The cards that were played
  repeated Card played_cards = 1;
  
  // The poker hand type detected
  PokerHand hand_type = 2;
  
  // Base score before modifiers
  int32 base_chips = 3;
  float base_mult = 4;
  
  // All score modifications applied
  repeated ScoreModification modifications = 5;
  
  // Final score after all calculations
  int64 final_score = 6;
  
  // Whether this defeated the current blind
  bool defeated_blind = 7;
}

// Enums for the event
enum PokerHand {
  POKER_HAND_UNSPECIFIED = 0;
  POKER_HAND_HIGH_CARD = 1;
  POKER_HAND_PAIR = 2;
  POKER_HAND_TWO_PAIR = 3;
  POKER_HAND_THREE_OF_A_KIND = 4;
  POKER_HAND_STRAIGHT = 5;
  POKER_HAND_FLUSH = 6;
  POKER_HAND_FULL_HOUSE = 7;
  POKER_HAND_FOUR_OF_A_KIND = 8;
  POKER_HAND_STRAIGHT_FLUSH = 9;
  POKER_HAND_ROYAL_FLUSH = 10;
  POKER_HAND_FIVE_OF_A_KIND = 11;  // With jokers
  POKER_HAND_FLUSH_HOUSE = 12;      // Special hands
  POKER_HAND_FLUSH_FIVE = 13;
}
```

This style guide provides a comprehensive foundation for implementing Protocol Buffers in the JimBot project, ensuring consistency, performance, and maintainability across all components.