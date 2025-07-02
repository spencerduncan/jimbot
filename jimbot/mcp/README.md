# MCP (Model-Context-Protocol) Subsystem

The MCP subsystem provides real-time communication between the BalatroMCP mod and the JimBot learning system, enabling efficient game state capture and event processing.

## Overview

MCP serves as the critical bridge between the game client and the AI learning infrastructure:

- **WebSocket Server**: Receives real-time events from BalatroMCP mod
- **Event Aggregator**: Batches events in 100ms windows for efficient processing
- **Protocol Translation**: Converts game events to Protocol Buffer format
- **Integration Layer**: Delivers processed events to Ray RLlib and Memgraph

## Architecture

```
┌─────────────────┐     WebSocket      ┌─────────────────┐
│  BalatroMCP Mod │ ──────────────────→│   MCP Server    │
└─────────────────┘                     └────────┬────────┘
                                                 │
                                        ┌────────▼────────┐
                                        │ Event Aggregator│
                                        └────────┬────────┘
                                                 │
                                   ┌─────────────┴─────────────┐
                                   │                           │
                              ┌────▼────┐               ┌──────▼──────┐
                              │   Ray   │               │  Memgraph   │
                              └─────────┘               └─────────────┘
```

## Quick Start

### 1. Install Dependencies

```bash
# From the jimbot root directory
pip install -r requirements.txt

# MCP-specific dependencies
pip install websockets==12.0
pip install protobuf==4.25.1
pip install asyncio
```

### 2. Compile Protocol Buffers

```bash
# Compile protocol definitions
cd /home/spduncan/jimbot-ws/jimbot-main
python -m jimbot.scripts.compile_protos
```

### 3. Start MCP Server

```bash
# Default configuration (port 8765)
python -m jimbot.mcp.server

# Custom configuration
python -m jimbot.mcp.server --port 9000 --host 0.0.0.0
```

### 4. Verify Connection

```bash
# Run test client
python -m jimbot.mcp.client --test-connection

# Send mock events
python -m jimbot.mcp.client --mock-events --rate 100
```

## API Documentation

### WebSocket API

The MCP server exposes a WebSocket endpoint for event streaming:

**Endpoint**: `ws://localhost:8765/events`

**Message Format**:
```json
{
  "type": "hand_played",
  "timestamp": 1704067200.123,
  "game_id": "abc123",
  "data": {
    "hand_type": "flush",
    "cards": ["AH", "KH", "QH", "JH", "10H"],
    "score": 35,
    "multiplier": 4
  }
}
```

### Event Types

| Event Type | Description | Required Fields |
|------------|-------------|-----------------|
| `game_start` | New game session started | `game_id`, `seed`, `stake`, `deck` |
| `hand_played` | Player played a hand | `hand_type`, `cards`, `score` |
| `joker_triggered` | Joker effect activated | `joker_id`, `trigger_type`, `effect` |
| `blind_defeated` | Blind successfully beaten | `blind_type`, `score`, `required_score` |
| `shop_entered` | Player entered shop | `round`, `money`, `available_items` |
| `card_purchased` | Card bought from shop | `card_type`, `card_id`, `cost` |
| `game_over` | Game ended | `final_score`, `round_reached`, `reason` |

### Python Client API

```python
from jimbot.mcp.client import MCPClient

# Initialize client
client = MCPClient("ws://localhost:8765/events")

# Connect and send events
async with client:
    await client.send_event({
        "type": "hand_played",
        "timestamp": time.time(),
        "game_id": "test123",
        "data": {
            "hand_type": "flush",
            "cards": ["AH", "KH", "QH", "JH", "10H"],
            "score": 35
        }
    })
```

### Event Aggregator API

```python
from jimbot.mcp.aggregator import EventAggregator

# Create aggregator with 100ms window
aggregator = EventAggregator(batch_window_ms=100)

# Set batch handler
async def handle_batch(events):
    print(f"Processing {len(events)} events")
    # Process events...

aggregator.set_batch_handler(handle_batch)

# Start aggregator
await aggregator.start()

# Add events
await aggregator.add_event(event_data)
```

## Configuration

### Server Configuration

Create `mcp_config.json`:

```json
{
  "server": {
    "host": "0.0.0.0",
    "port": 8765,
    "max_connections": 100,
    "heartbeat_interval": 30
  },
  "aggregator": {
    "batch_window_ms": 100,
    "max_queue_size": 10000,
    "max_batch_size": 1000
  },
  "performance": {
    "enable_profiling": false,
    "metrics_port": 9090
  }
}
```

### Environment Variables

```bash
# Server settings
export MCP_HOST=0.0.0.0
export MCP_PORT=8765

# Performance tuning
export MCP_BATCH_WINDOW_MS=100
export MCP_MAX_QUEUE_SIZE=10000

# Debugging
export MCP_LOG_LEVEL=INFO
export MCP_ENABLE_PROFILING=false
```

## Performance Tuning

### Achieving <100ms Latency

1. **Optimize Batch Window**
   ```python
   # Adjust based on event rate
   aggregator = EventAggregator(batch_window_ms=50)  # For high-rate events
   ```

2. **Configure Queue Size**
   ```python
   # Prevent memory overflow
   event_queue = asyncio.Queue(maxsize=5000)  # Adjust based on memory
   ```

3. **Enable Performance Monitoring**
   ```bash
   python -m jimbot.mcp.server --enable-metrics --metrics-port 9090
   ```

### Monitoring Metrics

Access metrics at `http://localhost:9090/metrics`:

- `mcp_batch_latency_ms`: Histogram of batch processing times
- `mcp_events_per_batch`: Distribution of batch sizes
- `mcp_queue_size`: Current queue depth
- `mcp_websocket_connections`: Active connections
- `mcp_events_processed_total`: Cumulative event count

## Development

### Running Tests

```bash
# All MCP tests
pytest tests/unit/mcp/ -v
pytest tests/integration/mcp/ -v

# Specific components
pytest tests/unit/mcp/test_aggregator.py -v
pytest tests/unit/mcp/test_server.py -v

# Performance benchmarks
pytest tests/performance/mcp/ -v --benchmark
```

### Mock Testing

```bash
# Start server with mock data generator
python -m jimbot.mcp.server --mock-mode

# Generate specific event patterns
python -m jimbot.mcp.utils.mock_generator --pattern game_sequence --rate 100
```

### Debugging

Enable detailed logging:

```python
import logging

# Set MCP logging to DEBUG
logging.getLogger('jimbot.mcp').setLevel(logging.DEBUG)

# Enable event tracing
from jimbot.mcp.utils import enable_tracing
enable_tracing()
```

## Troubleshooting

### Common Issues

1. **Connection Refused**
   - Check if server is running: `ps aux | grep mcp.server`
   - Verify port availability: `netstat -an | grep 8765`
   - Check firewall settings

2. **High Latency**
   - Monitor queue size: May need to increase `max_queue_size`
   - Check CPU usage: Consider reducing batch window
   - Profile code: `python -m cProfile -o profile.stats jimbot.mcp.server`

3. **Event Loss**
   - Enable persistent queue: `aggregator.enable_persistence()`
   - Increase queue size limits
   - Implement backpressure handling

### Health Check

```bash
# Check server health
curl http://localhost:8765/health

# Expected response
{
  "status": "healthy",
  "uptime": 3600,
  "connections": 2,
  "events_processed": 150000,
  "avg_latency_ms": 45
}
```

## Integration Examples

### Ray Integration

```python
import ray
from jimbot.mcp.integrations import RayEventDelivery

# Initialize Ray
ray.init()

# Create delivery actor
delivery_actor = RayEventDelivery.remote()

# Configure aggregator to use Ray
aggregator.set_delivery_handler(
    lambda events: ray.get(delivery_actor.deliver.remote(events))
)
```

### Memgraph Integration

```python
from jimbot.mcp.integrations import MemgraphEventHandler

# Create Memgraph handler
memgraph_handler = MemgraphEventHandler(
    host="localhost",
    port=7687
)

# Add to aggregator pipeline
aggregator.add_handler(memgraph_handler)
```

## Best Practices

1. **Always validate events** before processing
2. **Implement circuit breakers** for external integrations
3. **Use backpressure** to prevent memory overflow
4. **Monitor performance metrics** continuously
5. **Test with realistic load** before production

## Contributing

See [CONTRIBUTING.md](../../CONTRIBUTING.md) for development guidelines.

## License

Part of the JimBot project. See [LICENSE](../../LICENSE) for details.