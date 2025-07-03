# Infrastructure CLAUDE.md

This file provides guidance to Claude Code when working with the shared
infrastructure components of JimBot.

## Infrastructure Overview

The infrastructure layer provides the foundation for all JimBot components to
communicate and share resources efficiently. It implements the Event Bus pattern
with Protocol Buffers for serialization and includes resource coordination for
GPU and API management.

## Core Components

### 1. Event Bus (Central Communication Hub)

- **Pattern**: Publish-Subscribe with topic-based routing
- **Implementation**: AsyncIO-based with gRPC for inter-process communication
- **Batch Processing**: 100ms aggregation windows for game events
- **Reliability**: At-least-once delivery with acknowledgments

### 2. Resource Coordinator (GPU/API Management)

- **GPU Allocation**: Manages Ray RLlib GPU access with semaphores
- **API Rate Limiting**: Controls Claude API requests (100/hour limit)
- **Redis Sharing**: Coordinates shared Redis access between Claude and
  Analytics
- **Priority Queuing**: Ensures critical operations get resources first

### 3. Protocol Buffer Schemas

- **Event Definitions**: All game events, state updates, and commands
- **Version Management**: Backward compatibility with schema evolution
- **Language Support**: Python, C++ (for MAGE modules), and potential future
  languages
- **Performance**: Binary serialization for minimal overhead

### 4. Configuration Management

- **Hierarchical Config**: Environment → Component → Feature levels
- **Hot Reload**: Dynamic configuration updates without restarts
- **Validation**: Schema-based validation for all configurations
- **Secrets**: Integration with environment variables and secret stores

## Event Bus Patterns

### Publishing Events

```python
# infrastructure/event_bus.py
async def publish_event(self, topic: str, event: Any):
    # Serialize with Protocol Buffers
    serialized = self.serializer.serialize(event)

    # Add to batch queue
    await self.batch_queue.put((topic, serialized))

    # Trigger batch processing if window elapsed
    if time.time() - self.last_batch > 0.1:  # 100ms
        await self.flush_batch()
```

### Subscribing to Events

```python
# Pattern for component subscription
async def subscribe(self, topic: str, handler: Callable):
    self.handlers[topic].append(handler)

    # For gRPC subscriptions
    async for event in self.grpc_stream(topic):
        deserialized = self.serializer.deserialize(event)
        await handler(deserialized)
```

### Event Aggregation

```python
# 100ms batch aggregation for MCP events
class EventAggregator:
    async def aggregate_batch(self, events: List[Event]):
        # Group by event type
        grouped = defaultdict(list)
        for event in events:
            grouped[event.type].append(event)

        # Apply aggregation rules
        aggregated = []
        for event_type, group in grouped.items():
            if event_type in self.aggregation_rules:
                aggregated.append(
                    self.aggregation_rules[event_type](group)
                )
            else:
                aggregated.extend(group)

        return aggregated
```

## Protocol Buffer Usage

### Schema Definition

```protobuf
// serialization/schemas/game_events.proto
syntax = "proto3";
package jimbot;

message GameStateUpdate {
    int64 timestamp = 1;
    string game_id = 2;

    oneof update {
        JokerPurchased joker_purchased = 3;
        HandPlayed hand_played = 4;
        RoundCompleted round_completed = 5;
    }
}

message JokerPurchased {
    string joker_name = 1;
    int32 cost = 2;
    repeated string synergies = 3;
}
```

### Python Integration

```python
# Generated from protobuf schemas
from jimbot.infrastructure.serialization import game_events_pb2

# Creating events
event = game_events_pb2.GameStateUpdate()
event.timestamp = int(time.time() * 1000)
event.game_id = "game_123"
event.joker_purchased.joker_name = "Jimbo"
```

## Resource Coordinator Patterns

### GPU Allocation

```python
# resource_coordinator.py
class GPUAllocator:
    def __init__(self):
        self.gpu_semaphore = asyncio.Semaphore(1)
        self.allocation_queue = asyncio.Queue()

    async def allocate_gpu(self, component_id: str, duration: float):
        async with self.gpu_semaphore:
            self.current_user = component_id
            try:
                yield  # GPU allocated to caller
            finally:
                self.current_user = None
```

### API Rate Limiting

```python
# Claude API rate limiter
class ClaudeRateLimiter:
    def __init__(self, hourly_limit=100):
        self.window = deque(maxlen=hourly_limit)
        self.lock = asyncio.Lock()

    async def acquire(self):
        async with self.lock:
            now = time.time()
            # Remove old timestamps
            while self.window and self.window[0] < now - 3600:
                self.window.popleft()

            if len(self.window) >= self.hourly_limit:
                wait_time = 3600 - (now - self.window[0])
                await asyncio.sleep(wait_time)
                return await self.acquire()

            self.window.append(now)
            return True
```

### Redis Sharing

```python
# Shared Redis pool for Claude and Analytics
class RedisCoordinator:
    def __init__(self):
        self.pool = aioredis.ConnectionPool(
            max_connections=20,
            decode_responses=True
        )
        self.namespaces = {
            'claude': 'claude:',
            'analytics': 'analytics:',
            'shared': 'shared:'
        }

    async def get_client(self, namespace: str):
        return aioredis.Redis(
            connection_pool=self.pool,
            key_prefix=self.namespaces.get(namespace, '')
        )
```

## Communication Patterns

### gRPC Services

```python
# For synchronous inter-component communication
class InfrastructureService(infrastructure_pb2_grpc.InfrastructureServicer):
    async def GetResourceStatus(self, request, context):
        status = ResourceStatus()
        status.gpu_available = not self.gpu_allocator.is_busy()
        status.claude_requests_remaining = self.claude_limiter.remaining()
        return status
```

### Async Queue Pattern (for Claude)

```python
# Claude uses async queues instead of direct gRPC
class ClaudeQueue:
    def __init__(self):
        self.request_queue = asyncio.Queue(maxsize=1000)
        self.response_queues = {}

    async def submit_request(self, request_id: str, prompt: str):
        response_queue = asyncio.Queue(maxsize=1)
        self.response_queues[request_id] = response_queue

        await self.request_queue.put({
            'id': request_id,
            'prompt': prompt,
            'timestamp': time.time()
        })

        return await response_queue.get()
```

## Monitoring Integration

### Metrics Collection

```python
# monitoring/metrics.py
class MetricsCollector:
    def __init__(self):
        self.event_counters = defaultdict(int)
        self.latency_histograms = defaultdict(list)

    async def record_event(self, event_type: str, latency: float):
        self.event_counters[event_type] += 1
        self.latency_histograms[event_type].append(latency)

        # Batch send to QuestDB every second
        if time.time() - self.last_flush > 1.0:
            await self.flush_to_questdb()
```

## Configuration Examples

### YAML Configuration

```yaml
# config/infrastructure.yaml
event_bus:
  batch_window_ms: 100
  max_batch_size: 1000
  grpc_port: 50051
  topics:
    - game_events
    - training_updates
    - strategy_requests

resource_coordinator:
  gpu:
    max_allocation_seconds: 300
    priority_components: ['training', 'inference']
  claude:
    hourly_limit: 100
    cache_ttl: 3600
  redis:
    max_connections: 20
    connection_timeout: 5

monitoring:
  metrics_flush_interval: 1.0
  questdb_url: 'http://localhost:9000'
  enable_profiling: false
```

## Error Handling

### Circuit Breaker Pattern

```python
class CircuitBreaker:
    def __init__(self, failure_threshold=5, recovery_timeout=60):
        self.failure_count = 0
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half-open

    async def call(self, func, *args, **kwargs):
        if self.state == "open":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "half-open"
            else:
                raise CircuitOpenError()

        try:
            result = await func(*args, **kwargs)
            if self.state == "half-open":
                self.state = "closed"
                self.failure_count = 0
            return result
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            if self.failure_count >= self.failure_threshold:
                self.state = "open"
            raise
```

## Testing Infrastructure

### Mock Event Bus

```python
# For component testing without full infrastructure
class MockEventBus:
    def __init__(self):
        self.published_events = []
        self.handlers = defaultdict(list)

    async def publish(self, topic: str, event: Any):
        self.published_events.append((topic, event))
        # Immediately deliver to handlers for testing
        for handler in self.handlers[topic]:
            await handler(event)
```

## Performance Considerations

1. **Event Batching**: Always batch events in 100ms windows
2. **Protocol Buffers**: Use for all serialization (10x faster than JSON)
3. **Connection Pooling**: Reuse gRPC channels and Redis connections
4. **Async Everything**: Use AsyncIO for all I/O operations
5. **Memory Management**: Implement backpressure for queues

## Security

1. **Authentication**: mTLS for gRPC connections
2. **Authorization**: Component-based access control
3. **Encryption**: TLS for all network communication
4. **Secrets**: Never hardcode, use environment variables

## Development Guidelines

1. **Always use Protocol Buffers** for event definitions
2. **Implement circuit breakers** for external dependencies
3. **Add metrics** for all critical operations
4. **Write integration tests** for all communication patterns
5. **Document rate limits** and resource constraints
6. **Use async/await** for all I/O operations
7. **Handle backpressure** in all queues and streams
