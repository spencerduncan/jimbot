# Knowledge Graph Development Plan

## Executive Summary

This plan details the implementation of a Memgraph-based knowledge graph for the Balatro Sequential Learning System, to be developed during Weeks 1-8 of the project timeline. Working within a 10GB memory allocation (reduced from 12GB to accommodate Event Bus infrastructure), the system will consume game state events from the Event Bus, expose a GraphQL query interface, and provide strategic knowledge to the learning system via efficient graph queries.

## 1. Memgraph Configuration for Balatro

### Memory-Optimized Configuration

```bash
# memgraph.conf - Optimized for 10GB allocation
--memory-limit=9728  # 9.5GB (leaving 0.5GB buffer)
--storage-mode=IN_MEMORY_TRANSACTIONAL
--storage-snapshot-interval-sec=1800  # Every 30 minutes
--storage-snapshot-retention-count=3  # Keep only recent snapshots
--query-execution-timeout-sec=60  # Shorter timeout for Balatro queries
--storage-property-store-compression-level=high  # Maximize compression
--storage-gc-cycle-sec=60  # More frequent garbage collection
--log-level=WARNING  # Reduce logging overhead
```

### Docker Deployment

```bash
docker run -p 7687:7687 -p 3000:3000 \
  --memory=10g --memory-swap=10g \
  --name balatro-memgraph \
  memgraph/memgraph-platform:latest \
  --memory-limit=9728 \
  --storage-property-store-compression-level=high \
  --query-plan-cache-ttl=3600
```

### MAGE Modules for Balatro

Essential algorithms for strategy discovery:
- **Community Detection**: Identify joker synergy clusters
- **PageRank**: Determine influential jokers in winning runs
- **Path Analysis**: Find optimal play sequences
- **Temporal Analysis**: Detect winning patterns across game phases

## 2. Technical Architecture

### Event Bus Integration

The Knowledge Graph consumes game state events and knowledge updates from the Event Bus:

```python
from jimbot.proto.events_pb2 import Event, GameStateEvent, KnowledgeUpdate
from jimbot.clients import EventBusClient
from gqlalchemy import Memgraph

class MemgraphEventConsumer:
    def __init__(self):
        self.event_bus = EventBusClient()
        self.memgraph = Memgraph()
        
    async def start(self):
        await self.event_bus.subscribe(
            topics=['game.state', 'knowledge.update'],
            handler=self.process_event
        )
        
    async def process_event(self, event: Event):
        if event.type == EventType.GAME_STATE:
            await self.update_game_state(event)
        elif event.type == EventType.KNOWLEDGE_UPDATE:
            await self.update_knowledge(event)
```

### GraphQL Service Interface

Expose a GraphQL API for querying the knowledge graph:

```python
from strawberry import Schema
from strawberry.fastapi import GraphQLRouter

@strawberry.type
class JokerSynergy:
    joker1: str
    joker2: str
    strength: float
    win_rate: float

@strawberry.type
class Query:
    @strawberry.field
    async def joker_synergies(self, joker_names: List[str]) -> List[JokerSynergy]:
        query = """
        MATCH (j1:Joker)-[s:SYNERGIZES_WITH]->(j2:Joker)
        WHERE j1.name IN $names AND j2.name IN $names
        RETURN j1.name as joker1, j2.name as joker2, 
               s.synergy_strength as strength, s.win_rate as win_rate
        """
        results = await self.memgraph.execute(query, names=joker_names)
        return [JokerSynergy(**r) for r in results]

schema = Schema(query=Query)
graphql_app = GraphQLRouter(schema)
```

### gRPC Mutation Service

High-performance updates via gRPC:

```python
class KnowledgeGraphService(KnowledgeServicer):
    def UpdateKnowledge(self, request: KnowledgeUpdate, context):
        # Fast path for game state updates
        if request.update_type == "game_state":
            self._batch_update_game_state(request.game_states)
        return UpdateResponse(success=True)
```

## 3. Balatro-Specific Graph Schema

### Core Node Types

```cypher
// Joker definitions with Balatro-specific properties
(:Joker {
  id: "baron",
  name: "Baron",
  rarity: "Rare",
  cost: 10,
  effect_type: "mult_conditional",
  effect_description: "Kings held in hand give X1.5 Mult each",
  trigger_condition: "in_hand",
  affected_cards: ["King"],
  base_mult_modifier: 1.5,
  discovered: true,
  win_rate: 0.0,  // Updated from gameplay
  usage_count: 0
})

// Playing card representations
(:Card {
  id: "KH",
  rank: "King",
  suit: "Hearts",
  base_chips: 10,
  scoring_value: 10
})

// Hand types with scoring rules
(:HandType {
  name: "Royal Flush",
  base_chips: 100,
  base_mult: 8,
  level: 1,
  cards_required: 5,
  contains: ["Straight Flush", "Flush", "Straight"]
})

// Strategic archetypes discovered through play
(:Strategy {
  id: "baron_mime_kings",
  name: "Baron-Mime King Hold",
  core_jokers: ["baron", "mime"],
  target_cards: ["King"],
  complexity: 4,
  discovered_date: datetime(),
  success_rate: 0.0
})
```

### Game State Tracking

```cypher
// Balatro-specific game state
(:GameState {
  id: "gs_001_a3_b2",
  run_id: "run_001",
  ante: 3,
  blind_type: "Big",
  blind_name: "The Hook",
  blind_chips: 750,
  money: 45,
  hands_remaining: 3,
  discards_remaining: 2,
  timestamp: datetime(),
  jokers_active: ["baron", "mime", "blueprint"],
  hand_cards: ["KH", "KS", "QD", "JC", "10H"]
})

// Decision nodes for strategy learning
(:Decision {
  id: "dec_001_23",
  run_id: "run_001",
  state_id: "gs_001_a3_b2",
  decision_type: "play_hand",
  cards_played: ["KH", "KS"],
  hand_type: "Pair",
  calculated_score: 12500,
  joker_order: ["baron", "mime", "blueprint"],
  reasoning: "Hold remaining Kings for Baron multiplier"
})
```

### Relationship Types

```cypher
// Joker synergies with strength metrics
(:Joker)-[:SYNERGIZES_WITH {
  synergy_strength: 9.5,
  combo_name: "Baron-Mime",
  discovered_runs: 45,
  avg_score_multiplier: 12.5
}]->(:Joker)

// Strategic relationships
(:Strategy)-[:REQUIRES_JOKER {priority: 1}]->(:Joker)
(:Strategy)-[:TARGETS_CARD {importance: "critical"}]->(:Card)

// Temporal game flow
(:GameState)-[:LEADS_TO {
  action: "play_hand",
  score_gained: 12500,
  chips_remaining: 0
}]->(:GameState)

// Learning relationships
(:Decision)-[:RESULTED_IN {
  outcome: "blind_cleared",
  score_efficiency: 0.92
}]->(:Outcome)
```

## 3. Memory-Efficient Data Model

### Pruning Strategy

```cypher
// Remove low-value game states older than 7 days
CALL apoc.periodic.iterate(
  "MATCH (gs:GameState) 
   WHERE gs.timestamp < datetime() - duration('P7D')
   AND NOT EXISTS((gs)<-[:CRITICAL_DECISION]-())
   RETURN gs",
  "DETACH DELETE gs",
  {batchSize: 500, parallel: false}
);

// Aggregate old decisions into summary nodes
MATCH (d:Decision)
WHERE d.timestamp < datetime() - duration('P14D')
WITH d.run_id as run, d.decision_type as type, 
     collect(d) as decisions, avg(d.calculated_score) as avg_score
CREATE (s:DecisionSummary {
  run_id: run,
  decision_type: type,
  count: size(decisions),
  avg_score: avg_score,
  created: datetime()
})
FOREACH (dec IN decisions | DETACH DELETE dec);
```

### Selective Index Strategy

```cypher
-- Only essential indices to minimize memory overhead
CREATE INDEX ON :Joker(id);
CREATE INDEX ON :GameState(run_id, ante);
CREATE INDEX ON :Decision(run_id, timestamp);
CREATE INDEX ON :Strategy(success_rate);
```

## 4. Balatro-Specific Algorithms

### Joker Synergy Detection

```python
@mgp.read_proc
def detect_joker_synergies(
    ctx: mgp.ProcCtx,
    min_occurrences: int = 20,
    min_win_rate: float = 0.6
) -> mgp.Record(synergies=mgp.List[mgp.Map]):
    
    query = """
    MATCH (r:Run)-[:USED_JOKER]->(j1:Joker)
    MATCH (r)-[:USED_JOKER]->(j2:Joker)
    WHERE j1.id < j2.id AND r.outcome = 'win'
    WITH j1, j2, count(r) as wins
    MATCH (r2:Run)-[:USED_JOKER]->(j1)
    MATCH (r2)-[:USED_JOKER]->(j2)
    WITH j1, j2, wins, count(r2) as total
    WHERE total >= $min_occurrences
    RETURN j1.name as joker1, j2.name as joker2, 
           wins * 1.0 / total as win_rate, total as games
    ORDER BY win_rate DESC
    """
    
    results = []
    for record in ctx.execute(query, {'min_occurrences': min_occurrences}):
        if record['win_rate'] >= min_win_rate:
            results.append({
                'joker1': record['joker1'],
                'joker2': record['joker2'],
                'win_rate': record['win_rate'],
                'sample_size': record['games']
            })
    
    return mgp.Record(synergies=results)
```

### Optimal Joker Ordering

```python
@mgp.write_proc
def optimize_joker_order(
    ctx: mgp.ProcCtx,
    joker_ids: mgp.List[str]
) -> mgp.Record(optimal_order=mgp.List[str], expected_mult=float):
    
    # Retrieve joker effects
    jokers = []
    for jid in joker_ids:
        result = ctx.execute(
            "MATCH (j:Joker {id: $id}) RETURN j",
            {'id': jid}
        ).fetchone()
        if result:
            jokers.append(result['j'])
    
    # Sort by Balatro rules: additive before multiplicative
    def sort_key(joker):
        effect = joker.properties.get('effect_type', '')
        if 'add' in effect or 'chips' in effect:
            return 0  # Additive effects first
        elif 'mult_base' in effect:
            return 1  # Base multipliers
        elif 'mult_conditional' in effect:
            return 2  # Conditional multipliers
        elif 'xmult' in effect:
            return 3  # X multipliers last
        return 4
    
    sorted_jokers = sorted(jokers, key=sort_key)
    optimal_order = [j.properties['id'] for j in sorted_jokers]
    
    # Calculate expected multiplier
    base_mult = 1.0
    for joker in sorted_jokers:
        if 'mult_modifier' in joker.properties:
            base_mult *= joker.properties['mult_modifier']
    
    return mgp.Record(
        optimal_order=optimal_order,
        expected_mult=base_mult
    )
```

### Play Sequence Pattern Mining

```cypher
// Find winning play patterns for specific blind types
MATCH path = (start:GameState)-[:LEADS_TO*1..5]->(end:GameState)
WHERE start.blind_type = $blind_type
  AND end.outcome = 'blind_cleared'
  AND end.hands_remaining >= 1
WITH path, 
     [n IN nodes(path) WHERE n:Decision | n] as decisions,
     end.hands_remaining as efficiency
RETURN 
  [d IN decisions | {
    cards: d.cards_played,
    hand_type: d.hand_type,
    score: d.calculated_score
  }] as play_sequence,
  count(*) as frequency,
  avg(efficiency) as avg_hands_saved
ORDER BY frequency DESC, avg_hands_saved DESC
LIMIT 10
```

## 5. Development Timeline (Weeks 1-8)

### Week 1: Foundation and Event Bus Integration

**Objective**: Set up Memgraph and connect to Event Bus

- Deploy Memgraph with 10GB memory configuration
- Implement Event Bus consumer for game state events
- Create base schema (Joker, Card, HandType nodes)
- Set up GraphQL endpoint infrastructure
- Basic health check and monitoring
- Deliverables: Working Memgraph consuming events

### Week 2: Schema Implementation

**Objective**: Complete Balatro-specific graph schema

- Implement full node types (Strategy, GameState, Decision)
- Create relationship types with properties
- Load static game data (jokers, cards, hand types)
- Implement memory-efficient indices
- Create data pruning jobs
- Deliverables: Complete schema with test data

### Week 3: Core Query Interface

**Objective**: Implement GraphQL query API

- Create GraphQL schema for all query types
- Implement joker synergy queries
- Add strategy retrieval endpoints
- Create subscription mechanism for updates
- Performance optimization for <50ms queries
- Deliverables: Functional GraphQL API

### Week 4: Analytics Implementation

**Objective**: Develop Balatro-specific algorithms

- Implement joker synergy detection in MAGE
- Create optimal joker ordering algorithm
- Develop play sequence pattern mining
- Add community detection for strategy groups
- Integrate PageRank for influential patterns
- Deliverables: Core analytics operational
- Performance benchmarking

**Key Implementation:**
```python
class BalatroAnalyzer:
    def __init__(self, memgraph):
        self.db = memgraph
        
    def analyze_ante_progression(self, run_id):
        """Analyze score progression through antes"""
        query = """
        MATCH (gs:GameState {run_id: $run_id})
        WITH gs.ante as ante, max(gs.calculated_score) as max_score
        ORDER BY ante
        RETURN collect({ante: ante, score: max_score}) as progression
        """
        return self.db.execute_and_fetch(query, {'run_id': run_id})
```

### Week 5: Ray RLlib Integration

**Objective**: Enable bidirectional communication with learning system

- Implement gRPC mutation service for fast updates
- Create strategy persistence from Ray discoveries
- Add real-time decision scoring queries
- Optimize query patterns for Ray's needs
- WebSocket subscriptions for strategy updates
- Deliverables: Full Ray integration operational

### Week 6: Advanced Analytics

**Objective**: Implement sophisticated pattern detection

- Temporal pattern analysis for ante progression
- Blind-specific strategy mining
- Meta-strategy detection across runs
- Joker tier list generation
- Statistical validation of patterns
- Deliverables: Advanced analytics suite

### Week 7: Performance Optimization

**Objective**: Achieve production performance targets

- Query optimization for <50ms response
- Implement query result caching
- Optimize memory usage patterns
- Add connection pooling
- Stress testing with 1000+ concurrent queries
- Deliverables: System meeting all performance targets

### Week 8: Production Readiness

**Objective**: Complete integration and hardening

- End-to-end testing with all components
- Implement comprehensive monitoring
- Create operational dashboards
- Documentation and runbooks
- Performance validation under load
- Deliverables: Production-ready knowledge graph

## 6. Performance Targets

### Query Performance Requirements
- Simple lookups (joker by ID): <1ms
- Synergy detection: <50ms
- Play sequence mining: <100ms
- Strategy recommendation: <200ms
- Full ante analysis: <500ms

### Memory Targets
- Base graph structure: ~4GB
- Active game states (last 7 days): ~3GB
- Historical summaries: ~2GB
- Indices and caches: ~2GB
- Buffer/overhead: ~1GB

## 7. Testing Strategy

### Unit Tests
```python
def test_joker_synergy_detection():
    # Create test data
    mg.execute("""
        CREATE (r1:Run {id: 'test1', outcome: 'win'})
        CREATE (r2:Run {id: 'test2', outcome: 'win'})
        CREATE (r3:Run {id: 'test3', outcome: 'loss'})
        CREATE (baron:Joker {id: 'baron'})
        CREATE (mime:Joker {id: 'mime'})
        CREATE (r1)-[:USED_JOKER]->(baron)
        CREATE (r1)-[:USED_JOKER]->(mime)
        CREATE (r2)-[:USED_JOKER]->(baron)
        CREATE (r2)-[:USED_JOKER]->(mime)
        CREATE (r3)-[:USED_JOKER]->(baron)
    """)
    
    # Test synergy detection
    result = detect_joker_synergies(min_occurrences=2)
    assert len(result) == 1
    assert result[0]['win_rate'] == 1.0
```

### Performance Benchmarks
```python
class BalatroPerformanceTest:
    def benchmark_pattern_mining(self):
        """Test pattern mining performance with realistic data"""
        start = time.time()
        
        result = self.db.execute_and_fetch("""
            MATCH path = (s:GameState {ante: 8})-[:LEADS_TO*1..5]->(:GameState)
            WITH path LIMIT 1000
            RETURN count(path)
        """)
        
        duration = time.time() - start
        assert duration < 0.1  # Must complete in 100ms
```

## 8. Integration Points

### MCP Server Integration
```python
class MCPToMemgraphBridge:
    def process_game_state(self, mcp_state):
        """Convert MCP game state to graph nodes"""
        query = """
        MERGE (gs:GameState {id: $id})
        SET gs += $properties
        WITH gs
        UNWIND $jokers as joker_id
        MATCH (j:Joker {id: joker_id})
        MERGE (gs)-[:HAS_JOKER]->(j)
        """
        
        self.db.execute(query, {
            'id': f"{mcp_state['session_id']}_{mcp_state['sequence_id']}",
            'properties': {
                'ante': mcp_state['ante'],
                'money': mcp_state['money'],
                'timestamp': datetime.now()
            },
            'jokers': [j['name'] for j in mcp_state.get('jokers', [])]
        })
```

### Ray RLlib Interface
```python
def get_strategy_features(game_state):
    """Extract features for RL model"""
    query = """
    MATCH (gs:GameState {id: $id})
    OPTIONAL MATCH (gs)-[:HAS_JOKER]->(j:Joker)
    OPTIONAL MATCH (j)-[s:SYNERGIZES_WITH]-(j2:Joker)<-[:HAS_JOKER]-(gs)
    RETURN 
        gs.ante as ante,
        gs.money as money,
        collect(DISTINCT j.id) as jokers,
        sum(s.synergy_strength) as total_synergy
    """
    
    result = memgraph.execute_and_fetch(query, {'id': game_state['id']})
    return vectorize_features(result)
```

## 9. Monitoring and Maintenance

### Health Checks
```python
@mgp.read_proc
def health_check(ctx: mgp.ProcCtx) -> mgp.Record(status=str, details=mgp.Map):
    checks = {
        'node_count': "MATCH (n) RETURN count(n) as count",
        'memory_usage': "CALL mg.memory() YIELD used_memory, total_memory",
        'largest_paths': "MATCH p=(:GameState)-[:LEADS_TO*]->(:GameState) RETURN length(p) ORDER BY length(p) DESC LIMIT 1"
    }
    
    results = {}
    all_healthy = True
    
    for check_name, query in checks.items():
        try:
            result = ctx.execute(query).fetchone()
            results[check_name] = "OK"
        except Exception as e:
            results[check_name] = f"ERROR: {str(e)}"
            all_healthy = False
    
    return mgp.Record(
        status="HEALTHY" if all_healthy else "UNHEALTHY",
        details=results
    )
```

### Automated Cleanup
```bash
# Cron job for nightly cleanup
0 3 * * * docker exec balatro-memgraph cypher-shell -u "" -p "" "CALL prune_old_data()"
```

## 10. Risk Mitigation

### Memory Exhaustion Prevention
- Aggressive pruning of old game states
- Summary nodes for historical data
- Configurable retention policies
- Real-time memory monitoring with alerts at 80% usage

### Query Performance Degradation
- Limited path traversal depth (max 5 hops)
- Query timeouts at 60 seconds
- Materialized views for complex aggregations
- Regular index maintenance

### Data Quality Issues
- Validation on ingestion
- Consistency checks between game states
- Anomaly detection for impossible scores
- Regular data quality reports

## 11. Integration Patterns

### Event Processing Pipeline

```python
class GameStateProcessor:
    async def process_game_state_event(self, event: GameStateEvent):
        # Convert Protocol Buffer to Cypher
        cypher = """
        MERGE (gs:GameState {id: $id})
        SET gs += $properties
        WITH gs
        MATCH (prev:GameState {id: $prev_id})
        CREATE (prev)-[:LEADS_TO {
            action: $action,
            score_gained: $score
        }]->(gs)
        """
        await self.memgraph.execute(cypher, event.to_dict())
```

### Resource Coordination

```python
async def execute_heavy_query(self, query: str):
    # Request resources before heavy operations
    grant = await self.resource_coordinator.request({
        'component': 'memgraph',
        'type': ResourceType.MEMORY_MB,
        'amount': 500  # 500MB for complex query
    })
    
    if grant.approved:
        with grant:
            return await self.memgraph.execute(query)
    else:
        # Fallback to cached results
        return self.get_cached_result(query)
```

## 12. Success Criteria

- **Performance**: All queries complete within specified SLAs (<50ms for synergies)
- **Memory**: Stable operation within 10GB allocation
- **Integration**: Seamless Event Bus consumption and GraphQL serving
- **Reliability**: 99.9% uptime with automatic recovery
- **Analytics**: Accurate pattern detection validated against known strategies

## 13. Resource Requirements

### Development Approach
This component is designed for implementation by a single developer or small team with graph database expertise.

### Technical Skills Required
- **Cypher Query Language**: Advanced proficiency
- **Python**: For MAGE modules and integrations
- **GraphQL**: API design and implementation
- **Event-Driven Architecture**: Understanding of Event Bus patterns

### Memory Allocation
- **Total**: 10GB RAM (reduced from 12GB)
- **Graph Storage**: ~8GB
- **Query Processing**: ~1.5GB
- **Buffer**: ~0.5GB

This implementation plan provides a comprehensive approach to building a sophisticated knowledge graph within the JimBot architecture, optimized for Balatro's specific requirements while maintaining strict memory constraints and clean integration patterns.