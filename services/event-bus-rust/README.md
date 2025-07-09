# Rust Event Bus

Production-ready Event Bus implementation in Rust for JimBot, serving as the central message router for all components. This service provides the core communication infrastructure for the entire system.

## Features

- **REST API Compatibility**: Maintains backward compatibility with BalatroMCP endpoints
- **High Performance**: Designed to handle 10,000+ events/second
- **Protocol Buffers**: Efficient binary serialization for internal communication
- **Topic-Based Routing**: Flexible publish-subscribe with wildcard support
- **gRPC Support**: For high-performance inter-service communication
- **Docker Ready**: Containerized deployment with health checks

## API Endpoints

### REST API

- `POST /api/v1/events` - Submit a single event
- `POST /api/v1/events/batch` - Submit multiple events
- `GET /health` - Health check endpoint
- `GET /metrics` - Prometheus-compatible metrics

### Event Format (JSON)

```json
{
  "type": "GAME_STATE",
  "source": "BalatroMCP",
  "timestamp": 1704067200000,
  "version": 1,
  "payload": {
    "ante": 1,
    "round": 1,
    "money": 4,
    "chips": 100
  }
}
```

### Batch Format

```json
{
  "events": [
    {
      "type": "HEARTBEAT",
      "source": "BalatroMCP",
      "payload": {
        "version": "1.0.0",
        "uptime": 12345
      }
    }
  ]
}
```

## Building

### Local Development

```bash
# Install Rust
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# Build the project
cargo build

# Run tests
cargo test

# Run the server
RUST_LOG=debug cargo run
```

### Docker

```bash
# Build the image
docker-compose build

# Run the service
docker-compose up
```

## Configuration

Environment variables:

- `RUST_LOG` - Log level (default: `event_bus_rust=info`)
- `REST_PORT` - REST API port (default: 8080)
- `GRPC_PORT` - gRPC port (default: 50051)

## Performance

The Event Bus is optimized for high throughput:

- Async I/O with Tokio
- Zero-copy message routing where possible
- Efficient Protocol Buffer serialization
- Connection pooling for downstream services

## Testing

The Event Bus uses a two-tier testing strategy:

### Merge CI (Unit Tests Only)

Fast unit tests that run on every PR:

```bash
# Run unit tests
cargo test --bins
```

### Scheduled Integration Tests

Comprehensive integration tests run every 4 hours:
- Full API endpoint testing
- Edge case validation
- Security tests (appropriate for LAN deployment)
- Performance validation

To run integration tests locally:

```bash
# Option 1: Use the test runner script
./run-integration-tests.sh

# Option 2: Manual testing
cargo run &
cargo test --tests
# Don't forget to stop the service

# Option 3: Test individual endpoints
cargo run

# Test with curl
curl -X POST http://localhost:8080/api/v1/events \
  -H "Content-Type: application/json" \
  -d '{"type": "HEARTBEAT", "source": "test", "payload": {}}'
```

## Topic Routing

Events are routed based on their type to specific topics:

| Event Type | Topic |
|------------|-------|
| GAME_STATE | game.state.update |
| HEARTBEAT | system.heartbeat |
| MONEY_CHANGED | game.money.changed |
| SCORE_CHANGED | game.score.changed |
| HAND_PLAYED | game.hand.played |
| CARDS_DISCARDED | game.cards.discarded |
| JOKERS_CHANGED | game.jokers.changed |
| ROUND_CHANGED | game.round.changed |
| PHASE_CHANGED | game.phase.changed |
| ROUND_COMPLETE | game.round.complete |
| CONNECTION_TEST | system.connection.test |

Subscribers can use wildcards:
- `game.*.*` - All game events
- `game.state.*` - All state-related events
- `*.*.*` - All events

## Integration

### With BalatroMCP

The Event Bus maintains full compatibility with the existing BalatroMCP mod:

```lua
-- BalatroMCP sends events to the Event Bus
local event = {
    type = "GAME_STATE",
    source = "BalatroMCP",
    payload = game_state
}
http_post("http://event-bus:8080/api/v1/events", event)
```

### With Other Services

Services can consume events via gRPC for better performance:

```rust
// Example gRPC client
let mut client = EventBusClient::connect("http://event-bus:50051").await?;
let stream = client.subscribe(SubscribeRequest {
    topic_pattern: "game.*.*".to_string(),
    subscriber_id: "analytics-service".to_string(),
}).await?;
```

## Monitoring

The Event Bus exposes Prometheus metrics at `/metrics`:

- `events_received_total` - Total events received
- `events_processed_total` - Total events successfully processed
- `events_failed_total` - Total events that failed processing
- `event_processing_duration_seconds` - Event processing latency

## Health Checks

The service provides health endpoints:

- `/health` - Basic health check
- Returns 200 OK when service is healthy
- Includes version and uptime information

## Development

### Adding New Event Types

1. Update the Protocol Buffer definition in `jimbot/proto/balatro_events.proto`
2. Add the mapping in `src/proto/converter.rs`
3. Update the topic routing in `src/routing/mod.rs`

### Testing

```bash
# Unit tests
cargo test

# Integration tests
cargo test --test '*' -- --test-threads=1

# Load testing
./scripts/load_test.sh
```