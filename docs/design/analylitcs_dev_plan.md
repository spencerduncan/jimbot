# Analytics and Persistence Development Plan

## Executive Overview

The Analytics and Persistence component establishes the data foundation for the
Balatro Sequential Learning System, to be developed during Weeks 5-10 of the
project timeline. The system consumes events from the Event Bus, storing
time-series metrics in QuestDB and complete game histories in EventStoreDB,
while providing real-time insights through Grafana dashboards. Operating within
a 5GB memory allocation, the system captures game events at microsecond
granularity and enables sophisticated strategy analysis.

## Technical Architecture

### Event Bus Integration

The Analytics system operates as a consumer of multiple event streams:

```python
from jimbot.proto.events_pb2 import Event, GameStateEvent, Metric
from jimbot.clients import EventBusClient
import questdb.ingress as qi
from esdbclient import EventStoreDBClient

class AnalyticsEventConsumer:
    def __init__(self):
        self.event_bus = EventBusClient()
        self.questdb = qi.Sender('localhost', 9009)
        self.eventstore = EventStoreDBClient("esdb://localhost:2113")

    async def start(self):
        await self.event_bus.subscribe(
            topics=['game.state', 'metrics.*', 'learning.decision'],
            handler=self.process_event
        )

    async def process_event(self, event: Event):
        # Route to appropriate storage
        if event.type in [EventType.METRIC, EventType.GAME_STATE]:
            await self.store_timeseries(event)

        # All events go to EventStore for complete history
        await self.store_event(event)
```

### Core Components and Memory Allocation

Operating within a 5GB total allocation:

- **QuestDB**: 3GB for time-series metrics and real-time analytics
- **EventStoreDB**: 2GB for complete event history and projections
- **Redis Cache**: Shared with Claude integration (no additional allocation)

### Data Flow Architecture

```
Event Bus → Analytics Consumer → [QuestDB | EventStoreDB]
                ↓                        ↓
         SQL Interface            Event Projections
                ↓                        ↓
         Grafana Dashboards      MLflow Experiments
```

## Development Timeline (Weeks 5-10)

### Week 5: Foundation and Event Bus Integration

**Objective**: Set up persistence infrastructure and connect to Event Bus

- Deploy QuestDB with 3GB memory configuration
- Deploy EventStoreDB with 2GB allocation
- Implement Event Bus consumer for analytics topics
- Create base schemas for time-series data
- Set up event routing logic
- Basic health monitoring
- Deliverables: Working consumers storing events

### Week 6: Schema Implementation and Optimization

**Objective**: Implement Balatro-specific data schemas

Core QuestDB tables:

- `game_metrics`: Per-hand performance with microsecond timestamps
- `decision_points`: All player choices with context and outcomes
- `joker_synergies`: Joker combination effectiveness tracking
- `economic_flow`: Money generation and spending patterns

EventStore streams:

- `game-{id}`: Complete game event sequences
- `strategy-{id}`: Strategy discovery events
- `learning-metrics`: Model performance tracking

Implementation example:

```sql
CREATE TABLE game_metrics (
  timestamp TIMESTAMP,
  session_id SYMBOL,
  ante INT,
  blind_type SYMBOL,
  hand_score LONG,
  mult INT,
  chips INT,
  jokers_active INT,
  money_earned INT,
  cards_played INT
) timestamp(timestamp) PARTITION BY DAY;
```

### Week 7: Query Optimization and MLflow Integration

**Objective**: Optimize query performance and set up experiment tracking

- Create indexes for common query patterns:
  - (session_id, timestamp) for game replay
  - (ante, blind_type, outcome) for strategy analysis
  - (joker_combination, win_rate) for synergy detection
- Implement MLflow experiment tracking:
  - Strategy performance metrics
  - Learning rate progression
  - Hyperparameter configurations
- Create materialized views for real-time dashboards
- Optimize ingestion for 10,000+ events/second
- Deliverables: Sub-10ms query performance, MLflow operational

### Week 8: Grafana Dashboards and Visualization

**Objective**: Create comprehensive monitoring and analytics dashboards

Real-time dashboards:

- System health and performance metrics
- Active game monitoring
- Strategy diversity tracking
- Learning progress visualization

Analytics dashboards:

- Joker synergy heatmaps
- Win rate progression curves
- Economic efficiency analysis
- Decision quality metrics

Implementation using QuestDB SQL:

```sql
-- Real-time win rate calculation
SELECT
  ante,
  COUNT(*) FILTER (WHERE outcome = 'win') * 100.0 / COUNT(*) as win_rate,
  AVG(final_score) as avg_score
FROM game_metrics
WHERE timestamp > dateadd('h', -24, now())
SAMPLE BY 1h
```

### Week 9: Advanced Analytics and Projections

**Objective**: Implement sophisticated analysis capabilities

EventStore projections for strategy analysis:

```javascript
fromStream('game-*').when({
  $init: function () {
    return {
      jokerCombos: {},
      winningStrategies: [],
    };
  },
  HandPlayed: function (state, event) {
    if (event.data.finalScore > 10000) {
      var combo = event.data.jokerEffects
        .map((j) => j.name)
        .sort()
        .join('+');
      state.jokerCombos[combo] = (state.jokerCombos[combo] || 0) + 1;
    }
  },
  GameCompleted: function (state, event) {
    if (event.data.outcome === 'win') {
      state.winningStrategies.push({
        jokers: event.data.finalJokers,
        score: event.data.finalScore,
      });
    }
  },
});
```

Advanced QuestDB analytics:

- Joker synergy correlation matrices
- Ante progression analysis
- Economic efficiency metrics
- Decision quality scoring

### Week 10: Production Readiness and Integration

**Objective**: Complete system hardening and full integration

- Implement data retention policies:
  - QuestDB: 30-day hot data, archive to Parquet
  - EventStore: 90-day complete history
- Performance optimization for concurrent queries
- Alerting for anomalies and learning milestones
- Complete documentation and runbooks
- End-to-end testing with all components
- Deliverables: Production-ready analytics platform

## Integration Patterns

### Event Processing Pipeline

```python
class EventProcessor:
    async def process_event(self, event: Event):
        # Convert Protocol Buffer to storage format
        if event.type == EventType.GAME_STATE:
            await self.process_game_state(event)
        elif event.type == EventType.METRIC:
            await self.process_metric(event)

    async def process_game_state(self, event: Event):
        # Extract to QuestDB line protocol
        game_state = GameStateEvent()
        event.payload.Unpack(game_state)

        line = f"game_metrics,session_id={game_state.game_id}"
        line += f",ante={game_state.ante}"
        line += f" hand_score={game_state.chips}i"
        line += f",mult={game_state.mult}i"
        line += f",money={game_state.money}i"
        line += f" {event.timestamp.ToNanoseconds()}"

        await self.questdb.send(line)
```

### Query Interface for Other Components

````python
class AnalyticsQueryService:
    async def get_joker_synergies(self, min_games: int = 100):
        query = """
        SELECT
            joker_combo,
            AVG(final_score) as avg_score,
            COUNT(*) as games,
            AVG(CASE WHEN outcome = 'win' THEN 1.0 ELSE 0.0 END) as win_rate
        FROM game_metrics
        WHERE timestamp > dateadd('d', -7, now())
        GROUP BY joker_combo
        HAVING games > $1
        ORDER BY win_rate DESC
        """
        return await self.questdb.query(query, min_games)

## Data Schemas

### QuestDB Schema Details

```sql
CREATE TABLE game_metrics (
  timestamp TIMESTAMP,
  session_id SYMBOL,
  sequence_id INT,
  ante INT,
  blind_type SYMBOL,
  blind_name STRING,
  hand_number INT,
  hand_type SYMBOL,
  cards_played STRING,
  base_chips INT,
  base_mult INT,
  final_chips INT,
  final_mult INT,
  final_score LONG,
  money_before INT,
  money_after INT,
  jokers_active INT,
  consumables_used STRING,
  time_to_decision INT,
  outcome SYMBOL
) timestamp(timestamp) PARTITION BY DAY;

CREATE TABLE decision_points (
  timestamp TIMESTAMP,
  session_id SYMBOL,
  decision_type SYMBOL,
  phase SYMBOL,
  options_available STRING,
  option_selected STRING,
  confidence_score DOUBLE,
  used_llm BOOLEAN,
  context_hash SYMBOL
) timestamp(timestamp) PARTITION BY DAY;

CREATE TABLE joker_synergies (
  timestamp TIMESTAMP,
  session_id SYMBOL,
  joker_combination STRING,
  hands_played_with INT,
  total_score_contribution LONG,
  average_multiplier DOUBLE
) timestamp(timestamp) PARTITION BY DAY;
````

### EventStoreDB Event Types

```typescript
interface BalatroEvent {
  eventId: string;
  eventType: string;
  timestamp: string;
  sessionId: string;
  sequenceId: number;
  data: Record<string, any>;
}

type GameStarted = BalatroEvent & {
  eventType: 'GameStarted';
  data: {
    seed: string;
    stakes: string;
    deck: string;
    startingMoney: number;
  };
};

type HandPlayed = BalatroEvent & {
  eventType: 'HandPlayed';
  data: {
    hand: string[];
    handType: string;
    scoring: {
      baseChips: number;
      baseMult: number;
      jokerEffects: Array<{ name: string; effect: string; value: number }>;
      finalScore: number;
    };
  };
};

type ShopEntered = BalatroEvent & {
  eventType: 'ShopEntered';
  data: {
    money: number;
    shopItems: Array<{
      slot: number;
      type: string;
      name: string;
      cost: number;
    }>;
    rerollCost: number;
  };
};
```

## Performance Requirements

The system must maintain these Balatro-specific performance targets:

- Ingestion: <1ms P99 latency for game events
- Query Performance: <50ms for strategy analysis queries
- Dashboard Refresh: <2 seconds for real-time metrics
- Event Replay: <5 seconds to reconstruct any game state
- Storage Efficiency: <100KB per complete game session

## Testing Strategy

### Unit Testing

- Schema validation for all event types
- Query performance benchmarks
- Data rotation and archival processes

### Integration Testing

- End-to-end data flow from MCP to dashboards
- Concurrent game simulation (100+ simultaneous games)
- Failure recovery scenarios

### Performance Testing

- Sustained ingestion at 50,000 events/second
- Complex analytical queries under load
- Memory usage within 6GB allocation

## Risk Mitigation

### Technical Risks

**Memory Exhaustion**: Automatic data rotation policies move older games to
compressed storage. QuestDB's age-based partitioning ensures only recent data
remains in memory.

**Ingestion Bottlenecks**: Batching and connection pooling prevent overwhelming
the database. Circuit breakers provide graceful degradation under extreme load.

**Query Performance Degradation**: Materialized views and strategic indexing
maintain query speed. Regular VACUUM operations prevent index bloat.

### Operational Risks

**Data Loss**: EventStoreDB's append-only model prevents data corruption.
Automated backups capture both databases hourly.

**Integration Delays**: Stub interfaces allow independent development. Weekly
integration tests catch issues early.

## Dependencies

### External Libraries

- **QuestDB Java Client** (1.0.0): High-performance ingestion
- **EventStore-Client-NodeJS** (5.0.1): Event sourcing
- **@questdb/grafana-questdb-datasource** (1.0.0): Direct Grafana integration
- **mlflow** (2.9.2): Experiment tracking
- **node-redis** (4.6.12): Caching layer

### Internal Dependencies

- MCP Communication Framework (Week 3)
- Learning Orchestration event format (Week 2)
- Knowledge Graph strategy identifiers (Week 4)

## Deliverables

### Week 5 Completion

1. **Fully Operational Data Platform**
   - QuestDB capturing all game metrics
   - EventStoreDB maintaining complete game histories
   - Redis caching layer for analytics

2. **Comprehensive Analytics Suite**
   - 15+ Grafana dashboards for game insights
   - MLflow experiment tracking integrated
   - Custom Balatro visualizations

3. **Developer Tools**
   - Event replay framework
   - Performance profiling utilities
   - Debugging query library

4. **Documentation Package**
   - API specifications for data access
   - Query cookbook for common analyses
   - Operational runbooks

## Resource Requirements

### Development Approach

This component is designed for implementation by a single developer or small
team with experience in time-series databases and event sourcing.

### Technical Skills

- **TypeScript/Node.js**: Event processing and routing
- **SQL**: Complex analytical queries
- **Event Sourcing**: EventStoreDB projections
- **Data Visualization**: Grafana dashboard creation

### Memory Allocation

- **Total**: 5GB RAM
- **QuestDB**: 3GB (time-series data)
- **EventStoreDB**: 2GB (event history)
- **Redis**: Shared with Claude integration

## Success Criteria

1. **Performance**: Ingestion <1ms latency, queries <50ms
2. **Reliability**: Zero event loss with at-least-once delivery
3. **Scalability**: Handle 50,000 events/second sustained
4. **Analytics**: Real-time dashboards with <2s refresh
5. **Integration**: Seamless Event Bus consumption

## Key Deliverables

By Week 10:

- Event Bus consumer for analytics events
- QuestDB with optimized schemas and indexes
- EventStoreDB with game replay capability
- 15+ Grafana dashboards for insights
- MLflow experiment tracking
- SQL query interface for other components
- Complete documentation and runbooks

This plan provides a comprehensive analytics foundation for the Balatro
Sequential Learning System, enabling deep insights into strategy evolution and
system performance.
