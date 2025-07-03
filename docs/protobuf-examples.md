# Protocol Buffers Examples for JimBot

This document provides concrete examples of well-designed Protocol Buffer
messages for the JimBot project, focusing on game state management and event
streaming patterns.

## Complete MCP Event Schema

```protobuf
syntax = "proto3";

package jimbot.mcp.v1;

import "google/protobuf/timestamp.proto";
import "google/protobuf/duration.proto";
import "google/protobuf/any.proto";

option go_package = "github.com/jimbot/proto/mcp/v1;mcpv1";
option java_package = "com.jimbot.proto.mcp.v1";
option java_multiple_files = true;

// MCPEvent is the root event type for all MCP communications
message MCPEvent {
  // Event identification (1-15 for frequent access)
  string event_id = 1;
  google.protobuf.Timestamp timestamp = 2;
  string source_component = 3;
  int64 sequence_number = 4;

  // Event routing information
  EventRouting routing = 5;

  // The actual event payload
  oneof payload {
    // Game state events (10-29)
    GameStateUpdate game_state_update = 10;
    PlayerActionRequest player_action = 11;
    ScoreCalculationEvent score_calculation = 12;

    // System events (30-49)
    ComponentHealthCheck health_check = 30;
    PerformanceMetrics performance = 31;
    ErrorEvent error = 32;

    // Control events (50-69)
    StreamControlEvent stream_control = 50;
    ConfigurationUpdate config_update = 51;
  }

  // Extended metadata (100+ for less frequent fields)
  map<string, string> metadata = 100;
  google.protobuf.Duration processing_duration = 101;
}

message EventRouting {
  repeated string target_components = 1;
  int32 priority = 2;  // 0 = normal, 1 = high, 2 = critical
  bool requires_ack = 3;
  google.protobuf.Timestamp expires_at = 4;
}
```

## Optimized Game State Representation

```protobuf
// Efficient game state snapshot with delta compression support
message GameStateSnapshot {
  // Snapshot identification
  SnapshotHeader header = 1;

  // Current game phase and round info
  GamePhase phase = 2;
  int32 ante = 3;
  int32 round = 4;

  // Player state (optimized for frequent access)
  PlayerState player = 5;

  // Board state
  BoardState board = 6;

  // Shop state (only populated during shop phase)
  ShopState shop = 7;

  // Active effects (sorted by priority)
  repeated ActiveEffect effects = 8 [packed=true];

  // Delta compression support
  DeltaInfo delta = 100;
}

message SnapshotHeader {
  string snapshot_id = 1;
  string game_id = 2;
  google.protobuf.Timestamp created_at = 3;
  int64 based_on_event = 4;  // Event sequence that triggered this snapshot
  bytes checksum = 5;        // SHA256 of snapshot content
}

message DeltaInfo {
  bool is_delta = 1;
  string base_snapshot_id = 2;
  repeated FieldChange changes = 3;
}

message FieldChange {
  string field_path = 1;  // e.g., "player.money"
  google.protobuf.Any old_value = 2;
  google.protobuf.Any new_value = 3;
}

// Compact player state representation
message PlayerState {
  // Resources (1-10 for frequent access)
  int32 money = 1;
  int32 hand_size = 2;
  int32 hands_remaining = 3;
  int32 discards_remaining = 4;

  // Score tracking
  int64 current_score = 5;
  int64 blind_requirement = 6;

  // Inventory (11-20)
  repeated JokerState jokers = 11;
  repeated ConsumableState consumables = 12;
  repeated VoucherState vouchers = 13;

  // Deck state (21-30)
  DeckState deck = 21;
  repeated Card hand = 22;

  // Stats tracking (100+)
  PlayerStats stats = 100;
}
```

## Event Aggregation Pattern

```protobuf
// Efficient event batching for 100ms aggregation window
message EventBatch {
  BatchHeader header = 1;

  // Events grouped by type for better compression
  repeated GameStateUpdate state_updates = 2;
  repeated PlayerActionRequest player_actions = 3;
  repeated ScoreCalculationEvent score_events = 4;
  repeated PerformanceMetrics metrics = 5;

  // Compression info
  CompressionInfo compression = 100;
}

message BatchHeader {
  string batch_id = 1;
  google.protobuf.Timestamp start_time = 2;
  google.protobuf.Timestamp end_time = 3;
  int32 total_events = 4;
  int32 dropped_events = 5;  // If buffer overflow
}

message CompressionInfo {
  string algorithm = 1;  // "none", "gzip", "snappy"
  int32 uncompressed_size = 2;
  int32 compressed_size = 3;
  float compression_ratio = 4;
}
```

## Joker Synergy Knowledge Graph

```protobuf
// Efficient representation for Memgraph queries
message JokerSynergyGraph {
  // All jokers in the graph
  repeated JokerNode jokers = 1;

  // All synergy edges
  repeated SynergyEdge synergies = 2;

  // Precomputed synergy clusters
  repeated SynergyCluster clusters = 3;
}

message JokerNode {
  string joker_id = 1;
  string name = 2;
  JokerRarity rarity = 3;

  // Compact property storage
  repeated JokerProperty properties = 4;

  // Graph metrics
  float centrality_score = 10;
  int32 synergy_count = 11;
}

message JokerProperty {
  PropertyType type = 1;
  oneof value {
    int32 int_value = 2;
    float float_value = 3;
    string string_value = 4;
    bool bool_value = 5;
  }
}

message SynergyEdge {
  string source_joker_id = 1;
  string target_joker_id = 2;
  float synergy_strength = 3;
  SynergyType type = 4;
  repeated string required_conditions = 5;
}

enum SynergyType {
  SYNERGY_TYPE_UNSPECIFIED = 0;
  SYNERGY_TYPE_MULTIPLICATIVE = 1;
  SYNERGY_TYPE_ADDITIVE = 2;
  SYNERGY_TYPE_CONDITIONAL = 3;
  SYNERGY_TYPE_TRANSFORMATIVE = 4;
}
```

## Ray RLlib Training Messages

```protobuf
// Efficient state representation for RL training
message TrainingObservation {
  // Compressed state representation (1-15)
  bytes encoded_state = 1;        // Numpy array as bytes
  float reward = 2;
  bool is_terminal = 3;

  // Action mask for valid actions
  repeated bool action_mask = 4 [packed=true];

  // Additional features
  repeated float custom_features = 5 [packed=true];

  // Metadata for debugging (100+)
  ObservationMetadata metadata = 100;
}

message TrainingAction {
  int32 action_id = 1;
  repeated float action_parameters = 2 [packed=true];
  float predicted_value = 3;
  float action_probability = 4;
}

message TrainingBatch {
  // Efficient batch representation
  repeated TrainingObservation observations = 1;
  repeated TrainingAction actions = 2;
  repeated float rewards = 3 [packed=true];
  repeated float advantages = 4 [packed=true];

  // Batch metadata
  string batch_id = 10;
  int32 batch_size = 11;
  int32 trajectory_length = 12;
  google.protobuf.Timestamp collected_at = 13;
}
```

## Claude LLM Integration Messages

```protobuf
// Async queue messages for Claude integration
message StrategyConsultationRequest {
  // Request identification
  string request_id = 1;
  google.protobuf.Timestamp requested_at = 2;
  int32 priority = 3;

  // Game context (compressed)
  GameContext context = 4;

  // Specific question or decision point
  DecisionPoint decision = 5;

  // Rate limiting info
  RateLimitInfo rate_limit = 6;
}

message GameContext {
  // Compressed representation for LLM
  string game_phase = 1;
  int32 ante = 2;
  repeated string active_jokers = 3;
  repeated string available_actions = 4;

  // Recent history (last N events)
  repeated GameEvent recent_events = 5;

  // Performance metrics
  float win_rate = 10;
  float average_score = 11;
}

message StrategyConsultationResponse {
  string request_id = 1;

  // LLM recommendation
  StrategyRecommendation recommendation = 2;

  // Processing info
  google.protobuf.Duration processing_time = 3;
  int32 tokens_used = 4;

  // Cache info
  bool from_cache = 5;
  google.protobuf.Timestamp cache_expires_at = 6;
}

message StrategyRecommendation {
  string recommended_action = 1;
  float confidence = 2;
  string reasoning = 3;
  repeated AlternativeAction alternatives = 4;
}
```

## Performance Monitoring Messages

```protobuf
// QuestDB time-series data
message PerformanceMetrics {
  // Timestamp is the primary key
  google.protobuf.Timestamp timestamp = 1;

  // Component identification
  string component_id = 2;
  string component_type = 3;

  // Core metrics (packed for efficiency)
  repeated MetricPoint cpu_usage = 4;
  repeated MetricPoint memory_usage = 5;
  repeated MetricPoint latency_ms = 6;
  repeated MetricPoint throughput = 7;

  // Custom metrics
  map<string, MetricSeries> custom_metrics = 10;
}

message MetricPoint {
  float value = 1;
  int64 timestamp_micros = 2;  // Microseconds since epoch
}

message MetricSeries {
  repeated MetricPoint points = 1 [packed=true];
  string unit = 2;
  AggregationType aggregation = 3;
}

enum AggregationType {
  AGGREGATION_TYPE_UNSPECIFIED = 0;
  AGGREGATION_TYPE_GAUGE = 1;
  AGGREGATION_TYPE_COUNTER = 2;
  AGGREGATION_TYPE_HISTOGRAM = 3;
}
```

## gRPC Service Example

```protobuf
// Complete service definition with all patterns
service JimBotGameService {
  // Unary RPC - Simple request/response
  rpc GetGameState(GetGameStateRequest) returns (GameStateSnapshot) {
    option (google.api.http) = {
      get: "/v1/game/{game_id}/state"
    };
  }

  // Server streaming - Real-time events
  rpc StreamGameEvents(StreamEventsRequest) returns (stream MCPEvent) {
    option (google.api.http) = {
      get: "/v1/game/{game_id}/events/stream"
    };
  }

  // Client streaming - Batch metrics upload
  rpc UploadMetrics(stream PerformanceMetrics) returns (MetricsUploadResponse) {
    option (google.api.http) = {
      post: "/v1/metrics/upload"
      body: "*"
    };
  }

  // Bidirectional streaming - Interactive gameplay
  rpc PlayInteractive(stream PlayerCommand) returns (stream GameUpdate) {
    option (google.api.http) = {
      post: "/v1/game/play/interactive"
      body: "*"
    };
  }
}

// Request/Response messages
message GetGameStateRequest {
  string game_id = 1;
  bool include_history = 2;
  int32 history_limit = 3;
}

message StreamEventsRequest {
  string game_id = 1;
  repeated EventType event_types = 2;

  oneof start_point {
    int64 from_sequence = 3;
    google.protobuf.Timestamp from_timestamp = 4;
    string from_snapshot = 5;
  }

  StreamOptions options = 10;
}

message StreamOptions {
  bool include_heartbeats = 1;
  int32 heartbeat_interval_seconds = 2;
  bool auto_reconnect = 3;
  int32 buffer_size = 4;
}
```

## Error Handling Pattern

```protobuf
// Comprehensive error representation
message ErrorInfo {
  // Standard fields
  string error_id = 1;
  ErrorCode code = 2;
  string message = 3;
  google.protobuf.Timestamp occurred_at = 4;

  // Context
  string component = 5;
  string operation = 6;

  // Debugging info
  repeated StackFrame stack_trace = 10;
  map<string, string> context = 11;

  // Recovery info
  bool is_retryable = 20;
  google.protobuf.Duration retry_after = 21;
  repeated string suggested_actions = 22;
}

enum ErrorCode {
  ERROR_CODE_UNSPECIFIED = 0;
  ERROR_CODE_INVALID_INPUT = 1;
  ERROR_CODE_NOT_FOUND = 2;
  ERROR_CODE_ALREADY_EXISTS = 3;
  ERROR_CODE_PERMISSION_DENIED = 4;
  ERROR_CODE_RESOURCE_EXHAUSTED = 5;
  ERROR_CODE_FAILED_PRECONDITION = 6;
  ERROR_CODE_ABORTED = 7;
  ERROR_CODE_OUT_OF_RANGE = 8;
  ERROR_CODE_UNIMPLEMENTED = 9;
  ERROR_CODE_INTERNAL = 10;
  ERROR_CODE_UNAVAILABLE = 11;
  ERROR_CODE_DATA_LOSS = 12;
}

message StackFrame {
  string function = 1;
  string file = 2;
  int32 line = 3;
  string module = 4;
}
```

## Best Practices Demonstrated

1. **Field Number Optimization**: Fields 1-15 used for frequently accessed data
2. **Packed Encoding**: Used for all repeated numeric fields
3. **Oneof Usage**: For mutually exclusive fields and polymorphic messages
4. **Clear Naming**: PascalCase for messages, snake_case for fields
5. **Enum Design**: Zero values with \_UNSPECIFIED suffix
6. **Versioning**: Package includes version (v1)
7. **Documentation**: Comments explain field purposes
8. **Performance**: Appropriate types chosen for each use case
9. **Streaming Patterns**: All four gRPC patterns demonstrated
10. **Error Handling**: Comprehensive error information with recovery hints

These examples provide templates for implementing efficient, well-designed
Protocol Buffer messages throughout the JimBot system.
