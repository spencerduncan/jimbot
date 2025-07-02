# Analytics/Monitoring Subsystem - Claude Guidance

## Overview

The Analytics/Monitoring subsystem is responsible for collecting, storing, and analyzing performance metrics and game events from JimBot. This subsystem operates within a 6GB memory allocation and spans Weeks 5-10 of the development timeline.

## Memory Allocation (6GB Total)

- **QuestDB**: 3GB (time-series performance metrics)
- **EventStoreDB**: 2GB (game event history and replay)
- **Analytics Services**: 1GB (collectors, processors, dashboards)

## Core Components

### 1. QuestDB (Time-Series Database)
- **Purpose**: Store real-time performance metrics
- **Port**: 9000 (web console), 8812 (Postgres wire protocol)
- **Key Metrics**:
  - Decision latency (target: <100ms)
  - Learning rate convergence
  - Win rate over time
  - Resource utilization (CPU/GPU/Memory)
  - API call patterns (Claude, Memgraph)

### 2. EventStoreDB (Event Sourcing)
- **Purpose**: Complete game history for replay and analysis
- **Port**: 2113 (HTTP), 1113 (TCP)
- **Event Types**:
  - Game state changes
  - Decision points
  - Strategy selections
  - Outcome results

### 3. Metric Collection Patterns

```python
# Time-series data pattern for QuestDB
class MetricCollector:
    async def record_metric(self, metric_name: str, value: float, tags: dict):
        """
        Records metrics with microsecond precision
        Tags should include: component, game_id, strategy_type
        """
        timestamp = time.time_ns() // 1000  # microseconds
        await self.questdb_client.insert(
            table=metric_name,
            timestamp=timestamp,
            value=value,
            **tags
        )
```

### 4. Event Sourcing Patterns

```python
# Event sourcing pattern for EventStoreDB
class GameEvent:
    def __init__(self, event_type: str, game_id: str, data: dict):
        self.event_id = str(uuid.uuid4())
        self.event_type = event_type
        self.game_id = game_id
        self.timestamp = datetime.utcnow()
        self.data = data
        
    def to_eventstore_format(self):
        return {
            "eventId": self.event_id,
            "eventType": self.event_type,
            "data": json.dumps(self.data),
            "metadata": json.dumps({
                "timestamp": self.timestamp.isoformat(),
                "game_id": self.game_id
            })
        }
```

## Integration Points

### Event Bus Integration
- Subscribe to all game events from the Event Bus
- Transform events for storage in appropriate database
- Publish aggregated metrics back to Event Bus

### Performance Monitoring
```python
# Monitor all component interactions
MONITORED_OPERATIONS = [
    "mcp.event_received",
    "memgraph.query_executed", 
    "ray.decision_made",
    "claude.strategy_requested",
    "game.round_completed"
]
```

## Dashboard Requirements

### Real-Time Dashboards
1. **System Health**: CPU, Memory, GPU utilization
2. **Game Performance**: Win rate, average score, decision quality
3. **Learning Progress**: Loss curves, exploration vs exploitation
4. **Component Latency**: End-to-end decision time breakdown

### Historical Analysis
1. **Game Replay**: Step through any historical game
2. **Strategy Evolution**: How strategies change over time
3. **Performance Trends**: Long-term performance patterns
4. **Anomaly Detection**: Identify unusual game patterns

## Alert Configuration

### Critical Alerts
- Memory usage > 90% of allocation
- Decision latency > 500ms
- Component disconnection
- Error rate > 5%

### Warning Alerts
- Memory usage > 75%
- Decision latency > 200ms
- API rate limit approaching
- Learning rate stagnation

## Data Retention Policies

### QuestDB (Time-Series)
- Raw metrics: 7 days
- 1-minute aggregates: 30 days
- 1-hour aggregates: 1 year

### EventStoreDB (Events)
- Full game events: 30 days
- Summary events: Indefinite
- Failed games: 90 days (for analysis)

## Development Timeline

### Week 5: Foundation
- Set up QuestDB and EventStoreDB containers
- Implement basic metric collectors
- Create Event Bus subscriptions

### Week 6: Core Metrics
- Implement performance metric collection
- Create game event processors
- Basic health monitoring

### Week 7: Integration
- Full Event Bus integration
- Cross-component metric correlation
- Initial dashboards

### Week 8: Advanced Analytics
- Game replay functionality
- Strategy analysis tools
- Performance optimization metrics

### Week 9: Production Features
- Alert system implementation
- Data retention automation
- Advanced dashboards

### Week 10: Polish
- Performance tuning
- Documentation
- Deployment automation

## Testing Patterns

```python
# Test metric collection
async def test_metric_collection():
    collector = MetricCollector()
    await collector.record_metric(
        "decision_latency",
        value=45.2,
        tags={"component": "ray", "game_id": "test_123"}
    )
    
    # Verify in QuestDB
    result = await questdb_client.query(
        "SELECT * FROM decision_latency WHERE game_id = 'test_123'"
    )
    assert result[0].value == 45.2
```

## Performance Considerations

### Batch Processing
- Aggregate metrics in 1-second windows before writing
- Use QuestDB's bulk insert for efficiency
- Buffer events before writing to EventStoreDB

### Memory Management
- Monitor analytics service memory usage
- Implement circuit breakers at 90% allocation
- Use streaming for large result sets

### Query Optimization
- Pre-aggregate common queries
- Use QuestDB's time-based partitioning
- Index EventStoreDB streams by game_id

## Security Notes

- No sensitive data in metrics
- Sanitize all user inputs
- Use read-only connections where possible
- Implement rate limiting on dashboard APIs

## Quick Reference

### QuestDB Queries
```sql
-- Recent performance
SELECT timestamp, avg(value) as avg_latency
FROM decision_latency
WHERE timestamp > dateadd('h', -1, now())
SAMPLE BY 1m;

-- Win rate trend
SELECT timestamp, count(*) as games, 
       sum(CASE WHEN outcome = 'win' THEN 1 ELSE 0 END) as wins
FROM game_results
WHERE timestamp > dateadd('d', -7, now())
SAMPLE BY 1h;
```

### EventStore Projections
```javascript
// Game replay projection
fromStream('game-*')
  .when({
    $init: function() {
      return { moves: [], score: 0 };
    },
    GameMove: function(state, event) {
      state.moves.push(event.data);
      return state;
    },
    GameEnd: function(state, event) {
      state.finalScore = event.data.score;
      return state;
    }
  });
```