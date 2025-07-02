# Protocol Buffers Style Guide for JimBot

This guide defines Protocol Buffers (protobuf) conventions for the JimBot project's event schemas and service interfaces.

## Table of Contents
1. [General Principles](#general-principles)
2. [File Organization](#file-organization)
3. [Naming Conventions](#naming-conventions)
4. [Message Design Patterns](#message-design-patterns)
5. [Field Guidelines](#field-guidelines)
6. [Versioning and Compatibility](#versioning-and-compatibility)
7. [Performance Optimization](#performance-optimization)
8. [gRPC Service Definitions](#grpc-service-definitions)
9. [JimBot-Specific Schemas](#jimbot-specific-schemas)

## General Principles

### Core Rules
- **Always use proto3** syntax for new development
- **Design for forward/backward compatibility** from day one
- **Keep messages focused** - one concept per message
- **Use well-known types** when available (google.protobuf.*)
- **Document everything** with clear comments

### File Structure
```protobuf
syntax = "proto3";

package jimbot.mcp.v1;

import "google/protobuf/timestamp.proto";
import "google/protobuf/duration.proto";

// Language-specific options
option java_multiple_files = true;
option java_package = "com.jimbot.mcp.v1";
option go_package = "github.com/jimbot/proto/mcp/v1;mcpv1";

// Message definitions follow...
```

## File Organization

### Naming Convention
- Files use `snake_case.proto`
- One primary message type per file
- Related messages can be in the same file

### Directory Structure
```
proto/
├── jimbot/
│   ├── common/
│   │   ├── v1/
│   │   │   ├── types.proto      # Common types
│   │   │   └── metadata.proto   # Metadata messages
│   ├── mcp/
│   │   ├── v1/
│   │   │   ├── events.proto     # MCP events
│   │   │   ├── game_state.proto # Game state messages
│   │   │   └── aggregation.proto # Aggregation messages
│   ├── memgraph/
│   │   ├── v1/
│   │   │   └── knowledge.proto  # Knowledge graph types
│   └── training/
│       ├── v1/
│       │   ├── model.proto      # Model messages
│       │   └── metrics.proto    # Training metrics
```

## Naming Conventions

### Messages
- **PascalCase** for message names
- Descriptive, noun-based names
- Avoid abbreviations

```protobuf
message GameState {
  // Good: Clear, descriptive name
}

message MCPEvent {
  // Good: Well-known abbreviation in context
}

message GS {  // Bad: Too abbreviated
}
```

### Fields
- **snake_case** for field names
- Use meaningful, descriptive names
- Standard suffixes:
  - `_id` for identifiers
  - `_at` for timestamps
  - `_ms` for millisecond durations
  - `_count` for quantities

```protobuf
message PlayerAction {
  string player_id = 1;
  google.protobuf.Timestamp performed_at = 2;
  int32 decision_time_ms = 3;
  int32 cards_played_count = 4;
}
```

### Enums
- **PascalCase** for enum names
- **UPPER_SNAKE_CASE** for values
- First value must be `_UNSPECIFIED` with number 0

```protobuf
enum JokerRarity {
  JOKER_RARITY_UNSPECIFIED = 0;
  JOKER_RARITY_COMMON = 1;
  JOKER_RARITY_UNCOMMON = 2;
  JOKER_RARITY_RARE = 3;
  JOKER_RARITY_LEGENDARY = 4;
}
```

## Message Design Patterns

### Event Pattern
```protobuf
message MCPEvent {
  // Event metadata
  EventMetadata metadata = 1;
  
  // Event-specific payload
  oneof payload {
    GameStarted game_started = 2;
    CardPlayed card_played = 3;
    JokerActivated joker_activated = 4;
    RoundCompleted round_completed = 5;
    GameEnded game_ended = 6;
  }
}

message EventMetadata {
  string event_id = 1;
  string session_id = 2;
  google.protobuf.Timestamp timestamp = 3;
  int32 sequence_number = 4;
}
```

### State Snapshot Pattern
```protobuf
message GameStateSnapshot {
  // Immutable game info
  string game_id = 1;
  string player_id = 2;
  
  // Current state
  int32 ante = 3;
  int32 round = 4;
  int64 money = 5;
  int32 hands_remaining = 6;
  int32 discards_remaining = 7;
  
  // Collections
  repeated Joker active_jokers = 8;
  repeated Card hand_cards = 9;
  repeated Card deck_cards = 10;
  
  // Computed values
  ScoreInfo current_score = 11;
  google.protobuf.Timestamp snapshot_at = 12;
}
```

### Command Pattern
```protobuf
message PlayerCommand {
  CommandMetadata metadata = 1;
  
  oneof command {
    PlayCards play_cards = 2;
    DiscardCards discard_cards = 3;
    BuyJoker buy_joker = 4;
    SellJoker sell_joker = 5;
    RerollShop reroll_shop = 6;
  }
}

message CommandMetadata {
  string command_id = 1;
  string player_id = 2;
  google.protobuf.Timestamp issued_at = 3;
  int32 timeout_ms = 4;
}
```

### Aggregation Pattern
```protobuf
message AggregatedEvents {
  AggregationInfo info = 1;
  repeated MCPEvent events = 2;
  GameStateDelta computed_delta = 3;
}

message AggregationInfo {
  google.protobuf.Timestamp window_start = 1;
  google.protobuf.Timestamp window_end = 2;
  int32 event_count = 3;
  int32 dropped_count = 4;
  CompressionInfo compression = 5;
}
```

## Field Guidelines

### Field Numbers
- **1-15**: Most frequently accessed fields (1 byte encoding)
- **16-2047**: Regular fields (2 byte encoding)
- **2048+**: Rarely used fields
- **19000-19999**: Reserved for protobuf implementation

```protobuf
message OptimizedGameState {
  // Hot fields (1-15)
  int32 ante = 1;
  int64 money = 2;
  int32 hands = 3;
  int32 discards = 4;
  repeated string joker_ids = 5;
  
  // Regular fields (16+)
  string game_id = 16;
  string player_id = 17;
  GameConfig config = 18;
}
```

### Field Types
```protobuf
message FieldTypeExamples {
  // Use specific types for clarity
  int32 count = 1;           // For counts/quantities
  sint32 delta = 2;          // For values that can be negative
  fixed32 hash = 3;          // For fixed-size values
  
  // Strings
  string joker_id = 4;       // IDs as strings for flexibility
  
  // Repeated fields
  repeated string tags = 5 [packed = true];  // Pack numeric arrays
  
  // Maps for lookups
  map<string, float> synergy_scores = 6;
  
  // Well-known types
  google.protobuf.Timestamp created_at = 7;
  google.protobuf.Duration processing_time = 8;
  google.protobuf.Any extension_data = 9;
}
```

### Reserved Fields
```protobuf
message EvolvingMessage {
  reserved 2, 4, 6 to 10;  // Reserved field numbers
  reserved "old_field", "deprecated_name";  // Reserved names
  
  string active_field = 1;
  int32 new_field = 3;
}
```

## Versioning and Compatibility

### Package Versioning
```protobuf
// Always include version in package name
package jimbot.mcp.v1;

// When breaking changes needed, create v2
package jimbot.mcp.v2;
```

### Field Evolution Rules
1. **Never change field numbers** once deployed
2. **Never change field types**
3. **Add new fields** with higher numbers
4. **Mark old fields** as reserved
5. **Use optional semantics** (proto3 default)

```protobuf
// Version 1
message UserStats {
  int32 games_played = 1;
  int32 games_won = 2;
}

// Version 2 (backward compatible)
message UserStats {
  int32 games_played = 1;
  int32 games_won = 2;
  float win_rate = 3;        // New field
  int64 total_score = 4;     // New field
  reserved 5;                // Reserve for future
}
```

### Deprecation Pattern
```protobuf
message GameConfig {
  // Active fields
  int32 starting_money = 1;
  int32 hands_per_round = 2;
  
  // Deprecated but reserved
  reserved 3, 4;
  reserved "old_difficulty", "legacy_mode";
  
  // Replacement field
  DifficultySettings difficulty = 5;
}
```

## Performance Optimization

### Packed Repeated Fields
```protobuf
message PerformanceMetrics {
  // Pack numeric repeated fields
  repeated int32 frame_times = 1 [packed = true];
  repeated float cpu_usage = 2 [packed = true];
  repeated int64 memory_bytes = 3 [packed = true];
  
  // Strings cannot be packed
  repeated string event_types = 4;
}
```

### Size Optimization
```protobuf
message OptimizedEvent {
  // Use appropriate numeric types
  int32 small_value = 1;     // If always < 2^31
  uint32 positive_only = 2;  // If never negative
  sint32 signed_value = 3;   // If often negative
  fixed32 fixed_size = 4;    // If always 4 bytes
  
  // Avoid repeated message fields when possible
  repeated string joker_ids = 5;  // Better than repeated Joker
  
  // Use bytes for binary data
  bytes compressed_data = 6;
}
```

### Streaming Patterns
```protobuf
message StreamHeader {
  string stream_id = 1;
  StreamType type = 2;
  google.protobuf.Timestamp started_at = 3;
}

message StreamChunk {
  int32 sequence = 1;
  bytes data = 2;
  bool is_final = 3;
}

message StreamControl {
  oneof control {
    StreamHeader start = 1;
    HeartBeat heartbeat = 2;
    Checkpoint checkpoint = 3;
    StreamEnd end = 4;
  }
}
```

## gRPC Service Definitions

### Service Design
```protobuf
service BalatroGameService {
  // Unary RPC - Simple request/response
  rpc GetGameState(GetGameStateRequest) returns (GameStateSnapshot);
  
  // Server streaming - Real-time updates
  rpc WatchGameEvents(WatchRequest) returns (stream MCPEvent);
  
  // Client streaming - Batch operations
  rpc SendCommands(stream PlayerCommand) returns (CommandResults);
  
  // Bidirectional streaming - Interactive session
  rpc PlaySession(stream SessionMessage) returns (stream SessionUpdate);
}
```

### Request/Response Pattern
```protobuf
message GetGameStateRequest {
  string game_id = 1;
  bool include_history = 2;
  SnapshotOptions options = 3;
}

message WatchRequest {
  string game_id = 1;
  repeated EventType event_types = 2;  // Filter events
  google.protobuf.Timestamp start_from = 3;
}
```

### Error Handling
```protobuf
message ErrorInfo {
  string code = 1;
  string message = 2;
  map<string, string> details = 3;
  google.protobuf.Timestamp occurred_at = 4;
  RetryInfo retry_info = 5;
}

message RetryInfo {
  bool can_retry = 1;
  google.protobuf.Duration retry_after = 2;
  int32 attempts_remaining = 3;
}
```

## JimBot-Specific Schemas

### MCP Event Schema
```protobuf
// mcp/v1/events.proto
syntax = "proto3";
package jimbot.mcp.v1;

import "google/protobuf/timestamp.proto";
import "jimbot/common/v1/types.proto";

message MCPEvent {
  EventMetadata metadata = 1;
  
  oneof payload {
    // Game flow events
    GameStarted game_started = 2;
    RoundStarted round_started = 3;
    HandDealt hand_dealt = 4;
    
    // Player actions
    CardsPlayed cards_played = 10;
    CardsDiscarded cards_discarded = 11;
    JokerPurchased joker_purchased = 12;
    
    // Game state changes
    ScoreCalculated score_calculated = 20;
    MoneyChanged money_changed = 21;
    AnteProgressed ante_progressed = 22;
  }
}

message EventMetadata {
  string event_id = 1;
  string game_id = 2;
  string session_id = 3;
  google.protobuf.Timestamp timestamp = 4;
  int32 sequence_number = 5;
  string source = 6;  // "game", "ai", "user"
}
```

### Knowledge Graph Integration
```protobuf
// memgraph/v1/knowledge.proto
message JokerNode {
  string joker_id = 1;
  string name = 2;
  JokerRarity rarity = 3;
  int32 cost = 4;
  repeated string tags = 5;
  map<string, float> attributes = 6;
}

message SynergyEdge {
  string source_joker_id = 1;
  string target_joker_id = 2;
  float synergy_score = 3;
  string synergy_type = 4;
  repeated Condition conditions = 5;
}

message KnowledgeQuery {
  oneof query {
    FindSynergies find_synergies = 1;
    GetJokerInfo get_joker_info = 2;
    RecommendJokers recommend_jokers = 3;
  }
}
```

### Training Messages
```protobuf
// training/v1/model.proto
message TrainingBatch {
  string batch_id = 1;
  repeated StateTransition transitions = 2;
  ModelMetadata model_metadata = 3;
  google.protobuf.Timestamp created_at = 4;
}

message StateTransition {
  GameStateSnapshot state = 1;
  PlayerCommand action = 2;
  float reward = 3;
  GameStateSnapshot next_state = 4;
  bool is_terminal = 5;
  map<string, float> info = 6;
}

message ModelCheckpoint {
  string checkpoint_id = 1;
  int64 training_steps = 2;
  map<string, float> metrics = 3;
  bytes model_weights = 4;  // Or reference to storage
  google.protobuf.Timestamp saved_at = 5;
}
```

### Performance Monitoring
```protobuf
// monitoring/v1/metrics.proto
message PerformanceEvent {
  string component = 1;  // "mcp", "memgraph", "ray", "claude"
  
  oneof metric {
    LatencyMetric latency = 2;
    ThroughputMetric throughput = 3;
    ResourceMetric resource = 4;
  }
  
  google.protobuf.Timestamp recorded_at = 5;
}

message LatencyMetric {
  string operation = 1;
  double value_ms = 2;
  map<string, double> percentiles = 3;  // p50, p95, p99
}
```

## Best Practices Summary

1. **Always use proto3** syntax
2. **Version packages** from the start (v1, v2, etc.)
3. **Design for evolution** - never remove or renumber fields
4. **Optimize field numbers** - hot fields get 1-15
5. **Pack repeated numeric fields** for efficiency
6. **Use well-known types** for timestamps, durations, etc.
7. **Document everything** with clear comments
8. **Test compatibility** when making changes
9. **Keep messages focused** - one concept per message
10. **Use oneof** for polymorphic data