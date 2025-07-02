# JimBot Infrastructure

The infrastructure layer provides the foundation for all JimBot components to communicate and share resources. It implements an event-driven architecture with Protocol Buffer serialization and intelligent resource management.

## Overview

The infrastructure consists of six core modules that work together to provide reliable, high-performance communication and resource management:

```
infrastructure/
├── event_bus/          # Central communication hub
├── resource_coordinator/   # GPU and API resource management
├── serialization/      # Protocol Buffer schemas and handlers
├── config/            # Configuration management
├── logging/           # Structured logging
└── monitoring/        # Metrics and observability
```

## Component Communication Patterns

### 1. Event Bus Architecture

The Event Bus is the central nervous system of JimBot, enabling decoupled communication between components:

```python
# Publishing events
await event_bus.publish("game.state.update", {
    "game_id": "abc123",
    "event": "joker_purchased",
    "data": {"joker": "Jimbo", "cost": 6}
})

# Subscribing to events
@event_bus.subscribe("game.state.*")
async def handle_game_event(event):
    # Process game state updates
    pass
```

**Key Features:**
- Topic-based routing with wildcard support
- 100ms batch aggregation for efficiency
- At-least-once delivery guarantees
- Automatic retries with exponential backoff

### 2. Communication Protocols

Different components use different communication patterns optimized for their needs:

#### gRPC (High-Performance RPC)
Used for: Memgraph ↔ Ray, MCP ↔ Event Bus
```python
# Synchronous request-response
response = await memgraph_client.query_synergies(
    joker_names=["Jimbo", "Ceremonial Dagger"]
)
```

#### REST API (Simple Integration)
Used for: External monitoring, health checks
```python
# RESTful endpoints for status
GET /api/v1/health
GET /api/v1/metrics
POST /api/v1/events
```

#### Async Queues (Decoupled Processing)
Used for: Claude AI integration
```python
# Submit request to Claude queue
request_id = await claude_queue.submit(
    prompt="Analyze this game state",
    context=game_state
)
# Get response when ready
response = await claude_queue.get_response(request_id)
```

### 3. Resource Coordination

The Resource Coordinator ensures efficient use of limited resources:

```python
# GPU allocation for training
async with resource_coordinator.allocate_gpu("training_job_1"):
    # GPU is exclusively allocated for this block
    model.train(data)

# API rate limiting for Claude
if await resource_coordinator.can_call_claude():
    response = await claude_client.query(prompt)
else:
    # Use cached response or fallback strategy
    response = await get_fallback_response()
```

## Configuration Management

### Hierarchical Configuration

Configuration follows a three-level hierarchy:

1. **Environment Level**: Base settings for dev/staging/prod
2. **Component Level**: Component-specific overrides
3. **Feature Level**: Feature flags and toggles

```yaml
# config/environments/production.yaml
infrastructure:
  event_bus:
    grpc_port: 50051
    max_batch_size: 1000
  
  resource_coordinator:
    claude_hourly_limit: 100
    gpu_timeout_seconds: 300

# config/components/memgraph.yaml
memgraph:
  query_timeout_ms: 50
  connection_pool_size: 10
```

### Dynamic Configuration

Configuration can be updated without restarting:

```python
# Watch for configuration changes
@config_manager.watch("infrastructure.event_bus.batch_window_ms")
async def on_batch_window_change(new_value):
    event_bus.update_batch_window(new_value)
```

## Protocol Buffer Schemas

All inter-component communication uses Protocol Buffers for efficiency and type safety:

```protobuf
// Common event wrapper
message Event {
    string id = 1;
    int64 timestamp = 2;
    string source = 3;
    string type = 4;
    google.protobuf.Any payload = 5;
}

// Game-specific events
message GameStateUpdate {
    string game_id = 1;
    int32 round = 2;
    int32 ante = 3;
    repeated Joker jokers = 4;
    Hand current_hand = 5;
}
```

## Monitoring and Observability

### Metrics Collection

All components automatically report metrics:

```python
# Automatic instrumentation
@event_bus.instrument("game.decision")
async def make_decision(state):
    # Metrics recorded: latency, success/failure, event count
    return await decide(state)
```

### Available Metrics

- **Event Bus**: Messages/sec, latency percentiles, queue depths
- **Resource Coordinator**: GPU utilization, API rate limit usage
- **Component Health**: Uptime, error rates, resource usage

### Logging

Structured logging with correlation IDs:

```python
logger.info("Processing game event", 
    event_id="evt_123",
    game_id="game_456",
    component="memgraph",
    latency_ms=23
)
```

## Getting Started

### Installation

```bash
# Install infrastructure dependencies
pip install -r infrastructure/requirements.txt

# Generate Protocol Buffer code
./infrastructure/scripts/generate_protos.sh
```

### Basic Usage

```python
from jimbot.infrastructure import EventBus, ResourceCoordinator

# Initialize infrastructure
event_bus = EventBus()
resource_coordinator = ResourceCoordinator()

# Start event bus
await event_bus.start()

# Publish events
await event_bus.publish("game.started", {"game_id": "123"})

# Subscribe to events
@event_bus.subscribe("game.*")
async def handle_game_events(event):
    print(f"Received: {event}")
```

### Testing

```python
# Use mock infrastructure for testing
from jimbot.infrastructure.testing import MockEventBus, MockResourceCoordinator

mock_bus = MockEventBus()
mock_coordinator = MockResourceCoordinator()

# Test with mocked infrastructure
await mock_bus.publish("test.event", {"data": "test"})
assert len(mock_bus.published_events) == 1
```

## Architecture Decisions

### Why Event Bus?
- **Decoupling**: Components don't need to know about each other
- **Scalability**: Easy to add new components
- **Flexibility**: Can replay events for debugging/recovery
- **Observability**: Central point for monitoring all communication

### Why Protocol Buffers?
- **Performance**: 10x faster than JSON serialization
- **Type Safety**: Compile-time validation of message formats
- **Evolution**: Backward compatibility with schema changes
- **Language Support**: Works with Python, C++, and more

### Why Resource Coordinator?
- **Fairness**: Prevents any component from monopolizing resources
- **Efficiency**: Maximizes utilization of GPU and API limits
- **Reliability**: Graceful degradation when resources are constrained

## Best Practices

1. **Always use the Event Bus** for component communication
2. **Define events in Protocol Buffers** before implementing
3. **Handle resource allocation failures** gracefully
4. **Include correlation IDs** in all log messages
5. **Monitor queue depths** to detect bottlenecks
6. **Test with mock infrastructure** for unit tests
7. **Use circuit breakers** for external dependencies

## Troubleshooting

### Common Issues

**Event Bus not receiving messages:**
- Check topic subscriptions match publishing topics
- Verify event serialization is correct
- Look for errors in component logs

**Resource allocation timeouts:**
- Check resource coordinator logs for contention
- Verify GPU is not locked by crashed process
- Review allocation priorities

**High latency:**
- Check batch window settings
- Monitor queue depths
- Review event aggregation rules

### Debug Tools

```bash
# Monitor event bus traffic
python -m jimbot.infrastructure.tools.event_monitor

# Check resource allocation
python -m jimbot.infrastructure.tools.resource_status

# Validate configuration
python -m jimbot.infrastructure.tools.config_validator
```

## Performance Tuning

### Event Bus Optimization
- Adjust batch windows based on latency requirements
- Use event aggregation for high-frequency updates
- Implement topic sharding for high throughput

### Resource Coordinator Tuning
- Set appropriate timeouts for GPU allocation
- Configure Claude API rate limits with buffer
- Use priority queues for critical operations

### Monitoring Optimization
- Adjust metric collection intervals
- Use sampling for high-frequency events
- Implement metric aggregation before storage