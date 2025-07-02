# Docker Minimal Setup Guide

This guide explains the minimal Docker Compose setup that provides only the external services needed for JimBot development, solving the chicken-and-egg problem where the full setup requires Event Bus and Resource Coordinator images that don't exist yet.

## Overview

The minimal setup includes:
- **Memgraph**: Knowledge graph database (12GB allocation)
- **QuestDB**: Time-series metrics database (3GB allocation)
- **EventStoreDB**: Event sourcing database (3GB allocation)
- **Redis**: Shared cache for components (2GB allocation)
- **Test Event Receiver**: Temporary Python server to receive BalatroMCP events

## Quick Start

1. **Copy the environment file**:
   ```bash
   cp .env.example .env
   ```

2. **Start the minimal services**:
   ```bash
   docker-compose -f docker-compose.minimal.yml up -d
   ```

3. **Verify all services are healthy**:
   ```bash
   docker-compose -f docker-compose.minimal.yml ps
   ```

4. **View service logs**:
   ```bash
   docker-compose -f docker-compose.minimal.yml logs -f
   ```

## Service Details

### Memgraph (Knowledge Graph)
- **Ports**: 7687 (Bolt), 3000 (Lab UI)
- **Web UI**: http://localhost:3000
- **Memory**: 10GB limit (12GB allocation with safety margin)
- **Volumes**: Persistent data and logs

### QuestDB (Time-Series Metrics)
- **Ports**: 9000 (HTTP), 8812 (PostgreSQL), 9009 (InfluxDB Line Protocol)
- **Web UI**: http://localhost:9000
- **Memory**: 3GB limit
- **Volumes**: Persistent data

### EventStoreDB (Event Sourcing)
- **Ports**: 1113 (TCP), 2113 (HTTP)
- **Web UI**: http://localhost:2113
- **Memory**: 3GB limit
- **Volumes**: Persistent data and logs
- **Note**: Running in insecure mode for development

### Redis (Shared Cache)
- **Port**: 6379
- **Memory**: 2GB limit with LRU eviction
- **Volumes**: Persistent data with AOF

### Test Event Receiver
- **Port**: 8080
- **Endpoints**:
  - `GET /health` - Health check
  - `POST /events` - Receive single event
  - `POST /events/batch` - Receive event batch
  - `GET /stats` - View statistics
  - `GET /events/recent` - View recent events
- **Memory**: 512MB limit

## Adding Local Services

To add your local services (Event Bus, Resource Coordinator, etc.), create a `docker-compose.override.yml` file:

```bash
cp docker-compose.override.yml.example docker-compose.override.yml
```

Then edit it to include your services. Docker Compose will automatically merge it with the minimal configuration.

Example override for Event Bus:
```yaml
services:
  event-bus:
    build:
      context: ./event-bus
      dockerfile: Dockerfile.dev
    ports:
      - "8081:8081"
    environment:
      - REDIS_URL=redis://redis:6379
    networks:
      - jimbot-network
```

## Testing the Setup

### Test Event Receiver
Send a test event to verify the setup:

```bash
curl -X POST http://localhost:8080/events \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "game_started",
    "timestamp": 1234567890.123,
    "game_state": {
      "round": 1,
      "chips": 100,
      "mult": 4
    }
  }'
```

View event statistics:
```bash
curl http://localhost:8080/stats
```

### Test Memgraph
Connect via the Lab UI at http://localhost:3000 or use the Bolt protocol:
```cypher
CREATE (:TestNode {name: 'Hello JimBot'});
MATCH (n) RETURN n;
```

### Test QuestDB
Access the web console at http://localhost:9000 and run:
```sql
CREATE TABLE test (ts TIMESTAMP, value INT) TIMESTAMP(ts);
INSERT INTO test VALUES (now(), 42);
SELECT * FROM test;
```

### Test EventStoreDB
Access the web UI at http://localhost:2113 (no authentication in dev mode).

## Troubleshooting

### Memory Issues
If services fail due to memory constraints, adjust the limits in `.env` and restart:
```bash
docker-compose -f docker-compose.minimal.yml down
docker-compose -f docker-compose.minimal.yml up -d
```

### Port Conflicts
If ports are already in use, modify them in `.env` before starting.

### Service Dependencies
The test event receiver depends on Redis being healthy. If it fails to start, ensure Redis is running first.

## Next Steps

1. **Develop Event Bus**: Replace the test event receiver with the full Event Bus implementation
2. **Add Resource Coordinator**: Implement GPU and API rate limit management
3. **Integrate Components**: Use the override file to progressively add services
4. **Production Setup**: Create a production Docker Compose with proper security settings

## Cleanup

To stop and remove all services:
```bash
docker-compose -f docker-compose.minimal.yml down
```

To also remove volumes (WARNING: deletes all data):
```bash
docker-compose -f docker-compose.minimal.yml down -v
```