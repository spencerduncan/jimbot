# MCP (Model-Context-Protocol) Development Guide

This guide provides MCP-specific development instructions for the JimBot system, focusing on achieving <100ms event aggregation latency and efficient WebSocket communication.

## MCP Overview

The MCP subsystem serves as the communication framework between the BalatroMCP mod and the JimBot learning system. It handles:
- Real-time game event collection via WebSocket
- Event aggregation and batching (100ms window)
- Protocol translation between game and learning system
- Integration with Ray RLlib training pipeline

## Architecture

```
BalatroMCP Mod → WebSocket → MCP Server → Event Aggregator → Ray/Memgraph
                                  ↓
                            Event Handlers
                                  ↓
                           Protocol Buffers
```

## Week 1-3 Deliverables

### Week 1: Foundation
- [x] Directory structure and initial setup
- [ ] WebSocket server implementation
- [ ] Basic event handler framework
- [ ] Protocol Buffer definitions

### Week 2: Event Aggregation
- [ ] Event aggregator with 100ms batch window
- [ ] Event queue management
- [ ] Basic event types (game_start, action, hand_played, etc.)
- [ ] Performance monitoring

### Week 3: Ray Integration
- [ ] Ray actor interface for event delivery
- [ ] Shared memory optimization
- [ ] Integration tests
- [ ] Performance benchmarks

## Event Aggregation Pattern

The aggregator MUST achieve <100ms latency for event processing:

```python
class EventAggregator:
    """
    Critical performance requirements:
    - 100ms batch window
    - Non-blocking event collection
    - Efficient batch processing
    - Zero-copy where possible
    """
    
    def __init__(self, batch_window_ms=100):
        self.batch_window = batch_window_ms / 1000.0
        self.event_queue = asyncio.Queue(maxsize=10000)
        self.batch_processor = None
        
    async def start(self):
        """Start the batch processing loop"""
        self.batch_processor = asyncio.create_task(self._process_batches())
        
    async def _process_batches(self):
        """
        Process events in 100ms windows
        CRITICAL: Must maintain <100ms latency
        """
        while True:
            batch_start = time.time()
            events = []
            
            # Collect events for batch_window duration
            while (time.time() - batch_start) < self.batch_window:
                try:
                    remaining = self.batch_window - (time.time() - batch_start)
                    if remaining > 0:
                        event = await asyncio.wait_for(
                            self.event_queue.get(),
                            timeout=remaining
                        )
                        events.append(event)
                except asyncio.TimeoutError:
                    break
                    
            if events:
                # Process batch without blocking next window
                asyncio.create_task(self._process_batch(events))
```

## WebSocket Handling

WebSocket server must handle:
1. Multiple concurrent connections
2. Automatic reconnection
3. Message validation
4. Backpressure management

```python
class MCPWebSocketServer:
    """
    WebSocket server for BalatroMCP communication
    """
    
    async def handle_connection(self, websocket, path):
        """
        Handle individual WebSocket connection
        - Validate client authentication
        - Setup heartbeat monitoring
        - Process incoming events
        """
        client_id = await self._authenticate(websocket)
        
        try:
            async for message in websocket:
                event = self._parse_event(message)
                await self.aggregator.add_event(event)
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Client {client_id} disconnected")
```

## Performance Optimization

### 1. Event Batching
- Use `asyncio.Queue` with appropriate size limits
- Implement backpressure to prevent memory overflow
- Consider using `collections.deque` for batch collection

### 2. Zero-Copy Strategies
- Use `memoryview` for large payloads
- Implement shared memory for Ray integration
- Minimize serialization/deserialization

### 3. Monitoring
```python
# Track key metrics
metrics = {
    'batch_latency_ms': Histogram('mcp_batch_latency_ms'),
    'events_per_batch': Histogram('mcp_events_per_batch'),
    'queue_size': Gauge('mcp_queue_size'),
    'websocket_connections': Gauge('mcp_websocket_connections')
}
```

## Protocol Buffer Usage

All events use Protocol Buffers for efficient serialization:

```python
# Import compiled protocol buffers
from jimbot.proto import balatro_events_pb2

# Example event creation
def create_hand_played_event(hand_data):
    event = balatro_events_pb2.HandPlayedEvent()
    event.timestamp = time.time()
    event.hand_type = hand_data['type']
    event.score = hand_data['score']
    # ... populate other fields
    return event.SerializeToString()
```

## Ray Integration Interface

The MCP must integrate with Ray for training pipeline:

```python
@ray.remote
class MCPEventDelivery:
    """
    Ray actor for receiving aggregated events
    """
    
    def __init__(self):
        self.event_buffer = []
        
    def deliver_batch(self, events):
        """
        Receive event batch from MCP aggregator
        Returns immediately to not block MCP
        """
        self.event_buffer.extend(events)
        return len(events)
```

## Testing Strategy

### Unit Tests
```bash
# Test individual components
pytest tests/unit/mcp/test_aggregator.py -v
pytest tests/unit/mcp/test_websocket.py -v
pytest tests/unit/mcp/test_protocols.py -v
```

### Integration Tests
```bash
# Test full MCP pipeline
pytest tests/integration/test_mcp_pipeline.py -v
```

### Performance Tests
```bash
# Verify <100ms latency requirement
pytest tests/performance/test_mcp_latency.py -v --benchmark
```

## Common Patterns

### 1. Event Validation
```python
def validate_event(event_data):
    """Validate incoming event structure"""
    required_fields = ['type', 'timestamp', 'game_id']
    for field in required_fields:
        if field not in event_data:
            raise ValueError(f"Missing required field: {field}")
    return True
```

### 2. Error Recovery
```python
async def with_retry(coro, max_retries=3, backoff=1.0):
    """Retry pattern for network operations"""
    for i in range(max_retries):
        try:
            return await coro
        except Exception as e:
            if i == max_retries - 1:
                raise
            await asyncio.sleep(backoff * (2 ** i))
```

### 3. Circuit Breaker
```python
class CircuitBreaker:
    """Prevent cascading failures"""
    def __init__(self, failure_threshold=5, recovery_timeout=60):
        self.failure_count = 0
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.last_failure_time = None
        self.state = 'closed'  # closed, open, half_open
```

## Development Workflow

1. **Start MCP Server**
   ```bash
   python -m jimbot.mcp.server --port 8765
   ```

2. **Monitor Performance**
   ```bash
   # Watch real-time metrics
   python -m jimbot.mcp.utils.monitor
   ```

3. **Test with Mock Client**
   ```bash
   python -m jimbot.mcp.client --mock-events
   ```

## Debugging Tips

1. **Enable Debug Logging**
   ```python
   import logging
   logging.getLogger('jimbot.mcp').setLevel(logging.DEBUG)
   ```

2. **Event Tracing**
   ```python
   # Add tracing to events
   event['trace_id'] = str(uuid.uuid4())
   event['span_id'] = str(uuid.uuid4())
   ```

3. **Performance Profiling**
   ```python
   import cProfile
   profiler = cProfile.Profile()
   profiler.enable()
   # ... code to profile ...
   profiler.disable()
   profiler.dump_stats('mcp_profile.stats')
   ```

## Critical Success Factors

1. **Latency**: MUST maintain <100ms event aggregation
2. **Reliability**: Zero event loss during normal operation
3. **Scalability**: Handle 10,000+ events/second
4. **Integration**: Seamless Ray/Memgraph delivery

## Next Steps

After Week 3:
- Week 4-5: Advanced event types and game state reconstruction
- Week 6-7: Optimization and performance tuning
- Week 8-10: Production hardening and monitoring