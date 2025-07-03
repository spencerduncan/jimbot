# JimBot Analytics & Monitoring Subsystem

## Overview

The Analytics & Monitoring subsystem provides comprehensive observability for
JimBot's learning process and game performance. It captures real-time metrics,
stores complete game histories, and provides dashboards for analysis and
debugging.

## Architecture

```
┌─────────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Event Bus         │────>│ Metric Collector │────>│    QuestDB      │
│                     │     └──────────────────┘     │  (Time-Series)  │
│ (All Components)    │                              └─────────────────┘
│                     │     ┌──────────────────┐     ┌─────────────────┐
│                     │────>│ Event Processor  │────>│  EventStoreDB   │
└─────────────────────┘     └──────────────────┘     │ (Event Sourcing)│
                                                      └─────────────────┘
                                    │
                            ┌───────┴────────┐
                            │   Dashboards   │
                            │  & Exporters   │
                            └────────────────┘
```

## Key Metrics

### Performance Metrics (QuestDB)

#### System Metrics

- **CPU Usage**: Per-component CPU utilization
- **Memory Usage**: Heap and RSS memory per service
- **GPU Utilization**: Training and inference GPU usage
- **Network I/O**: Inter-component communication volume

#### Game Performance

- **Win Rate**: Rolling average over last N games
- **Average Score**: Score distribution and trends
- **Decision Latency**: Time from game state to action
- **Strategy Distribution**: Which strategies are being used

#### Learning Metrics

- **Loss Curves**: PPO loss, value loss, entropy
- **Exploration Rate**: Epsilon or entropy-based exploration
- **Reward Trends**: Episode rewards over time
- **Q-Value Estimates**: Action value predictions

#### Integration Metrics

- **API Call Rates**: Claude, Memgraph query rates
- **Cache Hit Rates**: Strategy and embedding caches
- **Error Rates**: Component failures and retries
- **Queue Depths**: Event Bus and processing backlogs

### Event Types (EventStoreDB)

#### Game Events

- `GameStarted`: Initial game configuration
- `RoundStarted`: Round number, blind, available actions
- `DecisionMade`: State, action taken, reasoning
- `JokerPurchased`: Joker details, cost, strategy
- `HandPlayed`: Cards played, score achieved
- `RoundCompleted`: Round score, money earned
- `GameEnded`: Final score, rounds survived, win/loss

#### System Events

- `ModelCheckpoint`: Model version, performance metrics
- `StrategyChanged`: Old strategy, new strategy, reason
- `ComponentError`: Error details, recovery action
- `ConfigurationUpdate`: Setting changes

## Dashboard Setup

### Prerequisites

```bash
# Install Grafana (for dashboards)
docker run -d -p 3000:3000 --name grafana grafana/grafana

# Install QuestDB
docker run -d -p 9000:9000 -p 8812:8812 \
  -v questdb_data:/var/lib/questdb \
  --name questdb questdb/questdb

# Install EventStoreDB
docker run -d -p 2113:2113 -p 1113:1113 \
  --name eventstore eventstore/eventstore:latest --insecure
```

### Dashboard Configuration

1. **System Health Dashboard**
   - Resource utilization graphs
   - Component status indicators
   - Alert summary panel

2. **Game Performance Dashboard**
   - Win rate over time
   - Score distribution histograms
   - Strategy effectiveness comparison

3. **Learning Progress Dashboard**
   - Loss curves
   - Reward trends
   - Exploration vs exploitation balance

4. **Game Replay Dashboard**
   - Interactive game state viewer
   - Decision timeline
   - Score progression

## Usage Examples

### Recording Metrics

```python
from jimbot.analytics.metrics import MetricCollector

collector = MetricCollector()

# Record a simple metric
await collector.record_metric(
    name="decision_latency",
    value=42.5,
    tags={"component": "ray", "game_id": "game_123"}
)

# Record with timestamp
await collector.record_metric_at(
    name="gpu_utilization",
    value=0.85,
    timestamp=datetime.utcnow(),
    tags={"device": "cuda:0"}
)
```

### Processing Events

```python
from jimbot.analytics.eventstore import EventProcessor

processor = EventProcessor()

# Store a game event
await processor.store_event(
    stream="game-123",
    event_type="JokerPurchased",
    data={
        "joker_name": "Fibonacci",
        "cost": 6,
        "current_money": 4,
        "round": 3
    }
)

# Read game history
events = await processor.read_stream("game-123")
```

### Querying Metrics

```python
from jimbot.analytics.questdb import QuestDBClient

client = QuestDBClient()

# Get recent performance
results = await client.query("""
    SELECT timestamp, avg(value) as avg_latency
    FROM decision_latency
    WHERE timestamp > dateadd('h', -1, now())
    SAMPLE BY 1m
""")

# Get win rate trend
win_rate = await client.query("""
    SELECT timestamp,
           count(*) as total_games,
           sum(CASE WHEN outcome = 'win' THEN 1 ELSE 0 END) as wins,
           avg(final_score) as avg_score
    FROM game_results
    WHERE timestamp > dateadd('d', -7, now())
    SAMPLE BY 1h
""")
```

## Metric Definitions

### Latency Metrics

- **Decision Latency**: Time from receiving game state to returning action
  - Target: <100ms
  - Critical: >500ms
- **Query Latency**: Time for Memgraph queries
  - Target: <50ms
  - Critical: >200ms

- **API Latency**: Time for Claude API calls
  - Target: <2s
  - Critical: >5s

### Rate Metrics

- **Games Per Hour**: Number of complete games
  - Target: >1000
  - Minimum: >500

- **Decisions Per Second**: Action selection rate
  - Target: >20
  - Minimum: >10

### Quality Metrics

- **Win Rate**: Percentage of games reaching ante 8+
  - Target: >10%
  - Baseline: >5%

- **Average Score**: Mean final score across games
  - Tracks improvement over time
  - Compared to baseline strategies

## Alert Configuration

### Critical Alerts

```yaml
alerts:
  - name: HighMemoryUsage
    condition: memory_usage > 5.5GB # 90% of 6GB allocation
    severity: critical
    action: notify_and_scale_down

  - name: ComponentDisconnected
    condition: component_heartbeat_missing > 30s
    severity: critical
    action: notify_and_restart

  - name: HighErrorRate
    condition: error_rate > 0.05 # 5% errors
    severity: critical
    action: notify_and_investigate
```

### Warning Alerts

```yaml
alerts:
  - name: ElevatedLatency
    condition: p95_latency > 200ms
    severity: warning
    action: notify

  - name: LowCacheHitRate
    condition: cache_hit_rate < 0.7 # 70% hits
    severity: warning
    action: notify_and_analyze
```

## Data Retention

### QuestDB Retention Policy

```sql
-- Automated cleanup (run daily)
ALTER TABLE decision_latency DROP PARTITION
WHERE timestamp < dateadd('d', -7, now());

-- Aggregate old data before deletion
INSERT INTO decision_latency_daily
SELECT date_trunc('day', timestamp) as day,
       component,
       avg(value) as avg_latency,
       min(value) as min_latency,
       max(value) as max_latency,
       count(*) as sample_count
FROM decision_latency
WHERE timestamp < dateadd('d', -7, now())
GROUP BY day, component;
```

### EventStoreDB Retention

```javascript
// Scavenge old events (configure in EventStore)
{
  "scavengeHistoryMaxAge": 30,  // days
  "scavengeInterval": 86400,     // daily
  "streams": {
    "game-*": {
      "maxAge": "30d",
      "maxCount": 10000
    },
    "system-*": {
      "maxAge": "90d"
    }
  }
}
```

## Development Guide

### Adding New Metrics

1. Define metric in `metrics/definitions.py`
2. Add collector in appropriate component
3. Create dashboard panel in Grafana
4. Set up alerts if needed

### Adding New Events

1. Define event schema in `eventstore/schemas.py`
2. Add event handler in `event_processor.py`
3. Update replay logic if needed
4. Document in this README

### Creating New Dashboards

1. Design in Grafana UI
2. Export as JSON
3. Save in `dashboards/` directory
4. Add setup instructions here

## Testing

```bash
# Run analytics tests
pytest tests/analytics/

# Test metric collection
pytest tests/analytics/test_metrics.py -v

# Test event processing
pytest tests/analytics/test_events.py -v

# Test dashboards
pytest tests/analytics/test_dashboards.py -v
```

## Performance Tuning

### QuestDB Optimization

- Use proper timestamp indexing
- Batch inserts (1000+ rows)
- Partition by day for large tables
- Use SAMPLE BY for aggregations

### EventStoreDB Optimization

- Use projections for complex queries
- Category streams for related events
- Proper stream naming conventions
- Regular scavenging

### Service Optimization

- Batch metric writes (1-second windows)
- Async processing where possible
- Connection pooling
- Circuit breakers for failures

## Troubleshooting

### Common Issues

1. **High Memory Usage**
   - Check batch sizes
   - Verify retention policies
   - Look for memory leaks

2. **Slow Queries**
   - Check indexes
   - Use EXPLAIN for QuestDB
   - Review projection efficiency

3. **Missing Metrics**
   - Verify Event Bus connection
   - Check collector logs
   - Confirm metric definitions

4. **Dashboard Loading Issues**
   - Check Grafana datasources
   - Verify database connectivity
   - Review query complexity
