# JimBot Interface Specification

## Overview

This document defines the comprehensive interface strategy for all JimBot components, resolving integration conflicts and establishing clear contracts between services.

## Architecture Pattern: Event-Driven Service Mesh

### Core Principles
1. **Event Bus Architecture**: All components communicate through a central event bus
2. **Language Agnostic**: Protocol Buffers for serialization, gRPC/REST for transport
3. **Fault Tolerance**: Circuit breakers, retries, and dead letter queues
4. **Observable**: Built-in metrics, tracing, and logging

### Component Registry

| Component | Language | Primary Interface | Secondary Interface | Status |
|-----------|----------|------------------|-------------------|---------|
| BalatroMCP | **Lua** | REST Event Producer | File I/O for Actions | **Implemented** |
| Event Bus | **Rust** | REST API (for BalatroMCP) | gRPC Streaming | Planned |
| Memgraph | Python/Cypher | GraphQL Query | gRPC Mutations | Planned |
| Ray RLlib | Python | gRPC Model Serving | REST Job Management | Planned |
| Claude/LangChain | Python | Async Queue | REST Cache Management | Planned |
| Analytics | **Rust** | Event Consumer | SQL Query Interface | Planned |
| Resource Coordinator | **Rust** | gRPC Service | Prometheus Metrics | Planned |
| MAGE Modules | **Rust** | Cypher Procedures | N/A | Planned |

## Canonical Event Schema

### Current BalatroMCP JSON Format
The existing BalatroMCP implementation sends events in JSON format:
```json
{
  "type": "GAME_STATE",
  "source": "BalatroMCP",
  "event_id": "uuid-here",
  "timestamp": 1234567890000,
  "version": 1,
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

The Event Bus will accept this JSON format and internally convert to Protocol Buffers.

### Base Event Structure (Protocol Buffers v3)

```protobuf
syntax = "proto3";
package jimbot.events.v1;

import "google/protobuf/timestamp.proto";
import "google/protobuf/any.proto";

message Event {
  string event_id = 1;  // UUID v4
  string correlation_id = 2;  // For tracing related events
  EventType type = 3;
  string source = 4;  // Component name
  google.protobuf.Timestamp timestamp = 5;
  int32 version = 6;  // Schema version
  map<string, string> metadata = 7;
  google.protobuf.Any payload = 8;  // Type-specific payload
}

enum EventType {
  GAME_STATE = 0;
  LEARNING_DECISION = 1;
  STRATEGY_REQUEST = 2;
  STRATEGY_RESPONSE = 3;
  KNOWLEDGE_QUERY = 4;
  KNOWLEDGE_UPDATE = 5;
  METRIC = 6;
  ERROR = 7;
  HEARTBEAT = 8;
}
```

### Game State Events

```protobuf
message GameStateEvent {
  string game_id = 1;
  int32 ante = 2;
  int32 round = 3;
  int32 hand_number = 4;
  
  message Joker {
    string name = 1;
    string rarity = 2;
    int32 position = 3;
    map<string, string> properties = 4;
  }
  
  message Card {
    string suit = 1;
    string rank = 2;
    string enhancement = 3;
    string seal = 4;
    string edition = 5;
  }
  
  repeated Joker jokers = 5;
  repeated Card hand = 6;
  repeated Card deck = 7;
  
  int32 chips = 8;
  int32 mult = 9;
  int32 money = 10;
  int32 hand_size = 11;
  int32 hands_remaining = 12;
  int32 discards_remaining = 13;
  
  map<string, int32> shop_items = 14;
  map<string, float> score_history = 15;
}
```

### Learning Events

```protobuf
message LearningDecisionRequest {
  string request_id = 1;
  GameStateEvent game_state = 2;
  repeated string available_actions = 3;
  float time_limit_ms = 4;
  DecisionContext context = 5;
}

message LearningDecisionResponse {
  string request_id = 1;
  string selected_action = 2;
  float confidence = 3;
  map<string, float> action_values = 4;
  bool used_llm = 5;
  string strategy_name = 6;
}

message DecisionContext {
  repeated string recent_actions = 1;
  float current_score = 2;
  float target_score = 3;
  string strategy_hint = 4;
}
```

## Service Interfaces

### 1. Event Bus Interface

```yaml
service: EventBus
protocol: gRPC streaming + REST
endpoints:
  - name: PublishEvent
    type: gRPC unary
    request: Event
    response: PublishResponse
    
  - name: SubscribeEvents  
    type: gRPC streaming
    request: SubscribeRequest
    response: stream Event
    
  - name: GetEventHistory
    type: REST GET
    path: /api/v1/events
    query: ?from={timestamp}&to={timestamp}&type={type}
    
configuration:
  max_message_size: 10MB
  retention_period: 7d
  partitions: 8
  replication_factor: 1  # Single node deployment
```

### 2. Knowledge Graph Interface

```yaml
service: KnowledgeGraph
protocol: GraphQL + gRPC
endpoints:
  - name: Query
    type: GraphQL
    endpoint: /graphql
    example: |
      query JokerSynergies($jokerName: String!) {
        joker(name: $jokerName) {
          synergies {
            target { name }
            strength
            conditions
          }
        }
      }
      
  - name: UpdateKnowledge
    type: gRPC unary
    request: KnowledgeUpdate
    response: UpdateResponse
    
  - name: SubscribeToChanges
    type: WebSocket
    path: /ws/knowledge
    
performance:
  query_timeout: 50ms
  mutation_timeout: 200ms
  max_concurrent_queries: 100
```

### 3. Learning Orchestration Interface

```yaml
service: RayRLlib
protocol: gRPC + REST
endpoints:
  - name: GetDecision
    type: gRPC unary
    request: LearningDecisionRequest
    response: LearningDecisionResponse
    sla: 95% < 100ms
    
  - name: SubmitTrainingJob
    type: REST POST
    path: /api/v1/training/jobs
    body: TrainingJobSpec
    
  - name: GetModelMetrics
    type: REST GET
    path: /api/v1/models/{model_id}/metrics
    
  - name: StreamDecisions
    type: gRPC streaming
    request: stream LearningDecisionRequest
    response: stream LearningDecisionResponse
    
resource_limits:
  max_concurrent_decisions: 1000
  max_memory_per_job: 6GB
  gpu_time_slice: 100ms
```

### 4. LLM Integration Interface

```yaml
service: ClaudeAdvisor
protocol: Async Queue + REST
endpoints:
  - name: RequestStrategy
    type: Async Message Queue
    queue: strategy_requests
    request: StrategyRequest
    response: StrategyResponse
    timeout: 5s
    
  - name: GetCachedStrategies
    type: REST GET
    path: /api/v1/strategies/cache
    
  - name: UpdateRateLimits
    type: REST PUT
    path: /api/v1/config/rate_limits
    
rate_limiting:
  strategy: token_bucket
  capacity: 100
  refill_rate: 100/hour
  burst_capacity: 10
```

### 5. Analytics Interface

```yaml
service: Analytics
protocol: Event Consumer + SQL
endpoints:
  - name: IngestEvents
    type: Event Bus Subscription
    topics: ["metrics.*", "game.state", "learning.decision"]
    
  - name: QueryMetrics
    type: REST POST
    path: /api/v1/query
    body: SQL query
    
  - name: StreamMetrics
    type: WebSocket
    path: /ws/metrics
    
storage:
  questdb:
    retention: 30d
    partition_by: day
  eventstore:
    retention: 90d
    snapshots: hourly
```

## Resource Coordination Service

### Purpose
Manages shared resources (GPU, memory, API quotas) across all components.

### Interface

```protobuf
service ResourceCoordinator {
  rpc RequestResource(ResourceRequest) returns (ResourceGrant);
  rpc ReleaseResource(ResourceRelease) returns (ReleaseResponse);
  rpc GetResourceStatus(Empty) returns (ResourceStatus);
  rpc SubscribeToResourceEvents(Empty) returns (stream ResourceEvent);
}

message ResourceRequest {
  string component = 1;
  ResourceType type = 2;
  int64 amount = 3;
  int64 duration_ms = 4;
  Priority priority = 5;
}

enum ResourceType {
  GPU_COMPUTE = 0;
  MEMORY_MB = 1;
  CLAUDE_API_TOKENS = 2;
}
```

## Error Handling Strategy

### Error Propagation

```protobuf
message ErrorEvent {
  string error_id = 1;
  string source_component = 2;
  ErrorSeverity severity = 3;
  string message = 4;
  string stack_trace = 5;
  map<string, string> context = 6;
  repeated string affected_components = 7;
  RecoveryAction suggested_action = 8;
}

enum ErrorSeverity {
  INFO = 0;
  WARNING = 1;
  ERROR = 2;
  CRITICAL = 3;
}

enum RecoveryAction {
  RETRY = 0;
  CIRCUIT_BREAK = 1;
  FALLBACK = 2;
  ESCALATE = 3;
}
```

### Circuit Breaker Configuration

```yaml
circuit_breaker:
  failure_threshold: 5
  timeout: 30s
  half_open_requests: 3
  
per_component:
  claude_advisor:
    failure_threshold: 3  # More sensitive due to cost
    timeout: 60s
  memgraph:
    failure_threshold: 10
    timeout: 15s
```

## Monitoring and Observability

### Metrics (Prometheus Format)

```yaml
common_metrics:
  - name: jimbot_event_bus_messages_total
    type: counter
    labels: [source, destination, event_type]
    
  - name: jimbot_request_duration_seconds
    type: histogram
    labels: [service, method, status]
    
  - name: jimbot_resource_usage_ratio
    type: gauge
    labels: [resource_type, component]
    
  - name: jimbot_error_rate
    type: counter
    labels: [component, severity, error_type]
```

### Distributed Tracing

All services must propagate OpenTelemetry trace context:
- `traceparent` header for HTTP
- Metadata for gRPC
- Message properties for async queues

### Logging

Structured JSON logs with required fields:
```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "level": "INFO",
  "component": "mcp_server",
  "trace_id": "abc123",
  "span_id": "def456",
  "message": "Event published",
  "event_type": "game.state",
  "duration_ms": 15
}
```

## Integration Timeline

### Week 0-1: Foundation
- Define all Protocol Buffer schemas
- Set up Event Bus infrastructure
- Implement Resource Coordinator

### Week 2: Core Services
- MCP publishes to Event Bus
- Knowledge Graph GraphQL endpoint
- Basic monitoring infrastructure

### Week 3: Integration Checkpoint
- End-to-end event flow test
- Resource coordination validation
- Performance baseline

### Weeks 4-10: Progressive Integration
- Add components following dependency order
- Continuous integration testing
- Performance optimization

## Memory Allocation (Revised)

Total: 32GB

### Infrastructure (5GB)
- Event Bus: 2GB
- Resource Coordinator: 1GB
- Redis Cache: 2GB

### Components (26GB)
- Memgraph: 10GB (reduced from 12GB)
- Ray RLlib: 8GB
- Analytics (QuestDB + EventStore): 5GB
- MCP + Headless: 2GB
- Claude/LangChain: 1GB

### Buffer (1GB)
- OS and burst capacity

## Configuration Management

All components use environment variables with defaults:

```bash
# Event Bus
EVENT_BUS_URL=grpc://localhost:50051
EVENT_BUS_TOPIC_PREFIX=jimbot

# Resource Coordinator  
RESOURCE_COORDINATOR_URL=grpc://localhost:50052
RESOURCE_REQUEST_TIMEOUT=5s

# Component Registration
COMPONENT_NAME=mcp_server
COMPONENT_VERSION=1.0.0

# Monitoring
METRICS_PORT=9090
TRACE_ENDPOINT=http://localhost:4317
LOG_LEVEL=INFO
```

## Security Considerations

1. **Internal Only**: All services bind to localhost only
2. **No Authentication**: Single-user workstation deployment
3. **API Keys**: Stored in environment variables
4. **Data Privacy**: No external data transmission except Claude API

## Testing Strategy

### Interface Contract Tests
Each component must provide:
- OpenAPI/gRPC service definitions
- Example requests/responses
- Performance benchmarks

### Integration Test Scenarios
1. End-to-end game play with all components
2. Failover testing (component failures)
3. Resource contention scenarios
4. Performance under load

## Success Criteria

1. **Latency**: 95% of cross-component calls < 100ms
2. **Throughput**: Support 1000+ games/hour
3. **Reliability**: 99.9% uptime for 8-hour training sessions
4. **Resource Usage**: Stay within allocated memory limits
5. **Integration**: All components communicate successfully

This specification provides the foundation for consistent, reliable integration across all JimBot components.