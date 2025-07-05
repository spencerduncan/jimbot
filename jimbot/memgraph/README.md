# Memgraph Knowledge Graph Subsystem

The Memgraph subsystem provides a high-performance graph database for storing
and querying Balatro game knowledge, including card relationships, joker
synergies, and strategy patterns.

## Overview

Memgraph serves as JimBot's long-term memory and strategic knowledge base,
enabling:

- Real-time synergy calculations during gameplay
- Historical pattern analysis across thousands of games
- Strategy path optimization based on win rates
- Dynamic feature extraction for the RL model

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    JimBot System                        │
├─────────────────┬───────────────┬────────────────────────┤
│   Ray/RLlib     │   Event Bus   │    Claude/LangChain   │
│                 │               │                        │
└────────┬────────┴───────┬───────┴────────┬──────────────┘
         │                │                │
         ▼                ▼                ▼
┌─────────────────────────────────────────────────────────┐
│                 Memgraph (Port 7687)                    │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────┐ │
│  │   Schema    │  │ MAGE Modules │  │ Query Engine  │ │
│  │  - Jokers   │  │  - Synergy   │  │  - Cypher    │ │
│  │  - Cards    │  │  - Victory   │  │  - Indexes   │ │
│  │  - Synergy  │  │  - Features  │  │  - Cache     │ │
│  └─────────────┘  └──────────────┘  └───────────────┘ │
└─────────────────────────────────────────────────────────┘
```

## Schema Documentation

### Core Node Types

#### Joker

Represents a joker card with its properties and effects.

```cypher
(:Joker {
    name: STRING,           // Unique identifier (e.g., "Blueprint")
    rarity: STRING,         // common, uncommon, rare, legendary
    cost: INTEGER,          // Shop cost
    base_chips: INTEGER,    // Base chip contribution
    base_mult: INTEGER,     // Base multiplier
    description: STRING,    // Effect description
    scaling_type: STRING    // none, linear, exponential, conditional
})
```

#### PlayingCard

Represents standard playing cards with enhancements.

```cypher
(:PlayingCard {
    suit: STRING,           // Hearts, Diamonds, Clubs, Spades
    rank: STRING,           // A, 2-10, J, Q, K
    enhancement: STRING,    // none, bonus, mult, wild, glass, steel, stone, gold
    seal: STRING           // none, gold, red, blue, purple
})
```

#### HandType

Represents poker hand types.

```cypher
(:HandType {
    name: STRING,           // "Flush", "Full House", etc.
    base_chips: INTEGER,
    base_mult: INTEGER,
    level: INTEGER,         // Current upgrade level
    plays: INTEGER          // Number of times played
})
```

#### Strategy

High-level strategy patterns discovered through gameplay.

```cypher
(:Strategy {
    name: STRING,           // "Fibonacci Rush", "Blueprint Engine"
    win_rate: FLOAT,        // Historical win rate (0.0-1.0)
    avg_score: INTEGER,     // Average final score
    games_played: INTEGER,  // Sample size
    ante_reached: FLOAT     // Average ante reached
})
```

### Core Relationship Types

#### SYNERGIZES_WITH

Connects jokers that work well together.

```cypher
(:Joker)-[:SYNERGIZES_WITH {
    strength: FLOAT,        // Synergy strength (0.0-1.0)
    synergy_type: STRING,   // multiplicative, additive, conditional
    win_rate: FLOAT,        // Win rate when paired
    confidence: FLOAT       // Statistical confidence
}]->(:Joker)
```

#### REQUIRES_CARD

Links jokers to specific card requirements.

```cypher
(:Joker)-[:REQUIRES_CARD {
    condition: STRING,      // "in_hand", "scored", "discarded"
    quantity: INTEGER       // Number required
}]->(:PlayingCard)
```

#### COUNTERS

Indicates jokers that counter each other.

```cypher
(:Joker)-[:COUNTERS {
    severity: FLOAT        // How badly it counters (0.0-1.0)
}]->(:Joker)
```

#### ENABLES_STRATEGY

Links jokers to strategies they enable.

```cypher
(:Joker)-[:ENABLES_STRATEGY {
    importance: FLOAT      // How critical for strategy (0.0-1.0)
}]->(:Strategy)
```

## Query Examples

### 1. Find Best Synergies for Current Jokers

```cypher
// Given current jokers, find the best additions
WITH ['Blueprint', 'Brainstorm'] AS current_jokers
MATCH (j:Joker)
WHERE j.name IN current_jokers
MATCH (j)-[s:SYNERGIZES_WITH]->(other:Joker)
WHERE NOT other.name IN current_jokers
AND s.strength > 0.7
RETURN other.name,
       AVG(s.strength) as avg_synergy,
       AVG(s.win_rate) as avg_win_rate
ORDER BY avg_synergy DESC
LIMIT 5
```

### 2. Analyze Victory Paths

```cypher
// Find successful joker progression paths
MATCH path = (start:Joker {rarity: 'common'})-[:LEADS_TO*1..4]->(end:Joker)
WHERE ALL(r IN relationships(path) WHERE r.win_rate > 0.6)
WITH path,
     REDUCE(s = 1.0, r IN relationships(path) | s * r.win_rate) as path_success,
     REDUCE(c = 0, n IN nodes(path) | c + n.cost) as total_cost
WHERE total_cost <= 30  // Early game budget
RETURN path, path_success, total_cost
ORDER BY path_success DESC
LIMIT 10
```

### 3. Card Requirement Analysis

```cypher
// Find jokers compatible with current deck composition
WITH {hearts: 15, spades: 10, diamonds: 8, clubs: 7} AS deck_comp
MATCH (j:Joker)-[r:REQUIRES_CARD]->(c:PlayingCard)
WITH j, c.suit as required_suit, SUM(r.quantity) as total_required
WHERE deck_comp[required_suit] >= total_required
RETURN j.name, COLLECT({suit: required_suit, needed: total_required}) as requirements
ORDER BY j.cost ASC
```

### 4. Counter-Strategy Detection

```cypher
// Detect if opponent jokers counter our strategy
WITH ['DNA', 'Blueprint'] AS our_jokers
MATCH (ours:Joker)-[:ENABLES_STRATEGY]->(s:Strategy)<-[:COUNTERS]-(counter:Joker)
WHERE ours.name IN our_jokers
RETURN DISTINCT counter.name, s.name as countered_strategy, AVG(counter.severity) as threat_level
ORDER BY threat_level DESC
```

### 5. Meta-Analysis Queries

```cypher
// Find emerging meta strategies
MATCH (s:Strategy)
WHERE s.games_played > 100
WITH s, s.win_rate * s.games_played as confidence_score
ORDER BY confidence_score DESC
LIMIT 20
MATCH (j:Joker)-[:ENABLES_STRATEGY]->(s)
RETURN s.name, s.win_rate, s.avg_score, COLLECT(j.name) as key_jokers
```

## Performance Optimization

### Indexes

```cypher
// Core indexes for sub-50ms query performance
CREATE INDEX ON :Joker(name);
CREATE INDEX ON :Joker(rarity);
CREATE INDEX ON :Joker(cost);
CREATE INDEX ON :PlayingCard(suit, rank);
CREATE INDEX ON :HandType(name);
CREATE INDEX ON :Strategy(win_rate);
CREATE CONSTRAINT ON (j:Joker) ASSERT j.name IS UNIQUE;
CREATE CONSTRAINT ON (h:HandType) ASSERT h.name IS UNIQUE;
```

### Query Optimization Tips

1. Always use parameters instead of string concatenation
2. Limit traversal depth with explicit bounds
3. Use `WITH` clauses to pipeline results
4. Profile queries with `PROFILE` prefix
5. Batch similar queries together

## Integration Examples

### Python Integration

```python
from typing import List, Dict
import asyncio
from neo4j import AsyncGraphDatabase

class MemgraphClient:
    def __init__(self, uri="bolt://localhost:7687"):
        self.driver = AsyncGraphDatabase.driver(uri)

    async def get_synergies(self, joker_names: List[str]) -> Dict[str, List[Dict]]:
        query = """
        UNWIND $joker_names AS joker_name
        MATCH (j:Joker {name: joker_name})-[s:SYNERGIZES_WITH]->(other:Joker)
        WHERE s.strength > $min_strength
        RETURN joker_name, COLLECT({
            target: other.name,
            strength: s.strength,
            type: s.synergy_type,
            win_rate: s.win_rate
        }) as synergies
        """

        async with self.driver.session() as session:
            result = await session.run(
                query,
                joker_names=joker_names,
                min_strength=0.5
            )
            return {r["joker_name"]: r["synergies"] async for r in result}
```

### MAGE Module Usage

```cypher
// Call Rust MAGE module for fast synergy calculation
CALL synergy.calculate_all() YIELD joker1, joker2, score
WHERE score > 0.8
RETURN joker1, joker2, score
ORDER BY score DESC
LIMIT 20;

// Victory path analysis with Rust MAGE module
CALL victory.find_optimal_paths({
    starting_money: 10,
    target_ante: 8,
    max_depth: 5
}) YIELD path, success_rate, total_cost
RETURN path, success_rate, total_cost;

// Fallback to pure Cypher if MAGE modules not available
MATCH path = (start:Joker {rarity: 'common'})-[:LEADS_TO*1..5]->(end:Joker)
WHERE ALL(r IN relationships(path) WHERE r.win_rate > 0.6)
WITH path, 
     REDUCE(s = 1.0, r IN relationships(path) | s * r.win_rate) as success_rate,
     REDUCE(c = start.cost, n IN nodes(path)[1..] | c + n.cost) as total_cost
WHERE total_cost <= 30
RETURN path, success_rate, total_cost
ORDER BY success_rate DESC;
```

## Development Setup

### Docker Compose

```yaml
# docker-compose.memgraph.yml
version: '3.8'
services:
  memgraph:
    image: memgraph/memgraph-platform:latest
    ports:
      - '7687:7687' # Bolt protocol
      - '3000:3000' # Memgraph Lab (web UI)
    volumes:
      - memgraph_data:/var/lib/memgraph
      - ./mage_modules/target/release:/usr/lib/memgraph/query_modules
    environment:
      - MEMGRAPH_LOG_LEVEL=INFO
      - MEMGRAPH_QUERY_TIMEOUT=100
    command: ['--memory-limit=12288', '--query-parallelism=4']

volumes:
  memgraph_data:
```

### Initial Schema Setup

```bash
# Load initial schema
mgconsole < schema/init_schema.cypher

# Load sample data for testing
mgconsole < tests/fixtures/sample_jokers.cypher

# Verify indexes
mgconsole -e "SHOW INDEX INFO;"
```

## Monitoring and Maintenance

### Key Metrics to Track

- Query execution time (target: <50ms)
- Memory usage (limit: 12GB)
- Active connections (limit: 20)
- Cache hit rate (target: >80%)

### Maintenance Tasks

```cypher
// Weekly: Update strategy statistics
MATCH (s:Strategy)
WITH s
MATCH ()-[r:PLAYED_STRATEGY {strategy: s.name}]->()
WHERE r.timestamp > datetime() - duration('P7D')
WITH s, COUNT(r) as recent_games, AVG(r.final_score) as recent_avg
SET s.games_played = s.games_played + recent_games,
    s.avg_score = (s.avg_score * s.games_played + recent_avg * recent_games) / (s.games_played + recent_games)

// Daily: Recalculate synergy strengths
CALL synergy.recalculate_all() YIELD updated_count
RETURN updated_count;

// Hourly: Clean up orphaned nodes
MATCH (n)
WHERE NOT (n)--()
DELETE n;
```

## Troubleshooting

### Common Issues

1. **Slow Queries**
   - Check for missing indexes: `PROFILE` your query
   - Reduce traversal depth
   - Use Rust MAGE modules for complex calculations

2. **Memory Issues**
   - Monitor with: `SHOW STORAGE INFO;`
   - Implement pagination for large result sets
   - Use projection to limit returned properties

3. **Connection Errors**
   - Check connection pool settings
   - Verify Memgraph is running: `docker ps`
   - Check logs: `docker logs memgraph`

## Future Enhancements

- [ ] Graph neural network embeddings
- [ ] Real-time synergy updates during gameplay
- [ ] Distributed graph processing for large-scale analysis
- [ ] Integration with streaming analytics
- [ ] Advanced visualization dashboard
