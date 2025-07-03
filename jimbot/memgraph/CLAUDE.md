# Memgraph Subsystem - Claude Code Guidance

This document provides specific guidance for working with the Memgraph knowledge
graph subsystem in JimBot.

## Overview

The Memgraph subsystem is responsible for storing and querying game knowledge,
including:

- Card and joker relationships
- Synergy calculations
- Strategy patterns
- Historical game data analysis

## Performance Requirements

**Critical**: All queries must execute in <50ms to maintain real-time game
responsiveness.

## Directory Structure

```
memgraph/
├── schema/           # Cypher schema definitions
├── queries/          # Optimized Cypher queries
├── algorithms/       # Python-based graph algorithms
├── mage_modules/     # C++ MAGE modules for performance
├── migrations/       # Schema migration scripts
└── utils/           # Helper utilities
```

## Cypher Query Patterns

### 1. Synergy Detection Pattern

```cypher
// Find all jokers that synergize with current joker
MATCH (j1:Joker {name: $joker_name})-[s:SYNERGIZES_WITH]->(j2:Joker)
WHERE s.strength > 0.7
RETURN j2.name, s.strength, s.synergy_type
ORDER BY s.strength DESC
LIMIT 5
```

### 2. Card Requirement Pattern

```cypher
// Find cards required for joker activation
MATCH (j:Joker {name: $joker_name})-[:REQUIRES]->(c:Card)
RETURN c.suit, c.rank, c.enhancement
```

### 3. Strategy Path Pattern

```cypher
// Find optimal joker progression paths
MATCH path = (start:Joker)-[:LEADS_TO*1..3]->(end:Joker)
WHERE start.cost <= $current_money
AND all(r IN relationships(path) WHERE r.win_rate > 0.6)
RETURN path, reduce(s = 1.0, r IN relationships(path) | s * r.win_rate) as path_strength
ORDER BY path_strength DESC
LIMIT 3
```

## MAGE Module Development (C++)

MAGE modules provide high-performance graph algorithms. Follow these patterns:

### Module Structure

```cpp
// mage_modules/synergy_calculator.cpp
#include <mgp.hpp>
#include <vector>
#include <unordered_map>

extern "C" {
    // Register the module
    int mgp_init_module(mgp_module *module, mgp_memory *memory);

    // Module shutdown
    int mgp_shutdown_module();
}

// Algorithm implementation
void calculate_synergy_score(mgp_list *args, mgp_graph *graph,
                           mgp_result *result, mgp_memory *memory) {
    // Implementation here
}
```

### Performance Guidelines for MAGE

1. **Memory Management**: Use mgp_memory for all allocations
2. **Batch Processing**: Process multiple nodes in single traversal
3. **Early Termination**: Stop traversal when threshold met
4. **Caching**: Store frequently accessed values in memory

### Example: Fast Synergy Calculator

```cpp
// Calculate synergy scores for all joker combinations
void calculate_all_synergies(mgp_graph *graph, mgp_result *result,
                           mgp_memory *memory) {
    // Get all jokers
    auto jokers = get_all_nodes_with_label(graph, "Joker", memory);

    // Pre-calculate attribute maps for O(1) lookup
    std::unordered_map<mgp_vertex*, JokerAttributes> joker_attrs;
    for (auto j : jokers) {
        joker_attrs[j] = extract_joker_attributes(j, memory);
    }

    // Calculate pairwise synergies
    for (size_t i = 0; i < jokers.size(); ++i) {
        for (size_t j = i + 1; j < jokers.size(); ++j) {
            double synergy = calculate_synergy(
                joker_attrs[jokers[i]],
                joker_attrs[jokers[j]]
            );
            if (synergy > 0.5) {  // Only store significant synergies
                add_synergy_to_result(result, jokers[i], jokers[j],
                                    synergy, memory);
            }
        }
    }
}
```

## Query Optimization Techniques

### 1. Index Usage

```cypher
// Create indexes for frequently queried properties
CREATE INDEX ON :Joker(name);
CREATE INDEX ON :Joker(rarity);
CREATE INDEX ON :Card(suit, rank);
CREATE INDEX ON :Synergy(strength);
```

### 2. Query Planning

```cypher
// Use PROFILE to analyze query performance
PROFILE MATCH (j:Joker)-[:SYNERGIZES_WITH]->(other)
WHERE j.name = 'Blueprint'
RETURN other;

// Optimize with hints
MATCH (j:Joker)
USING INDEX j:Joker(name)
WHERE j.name = 'Blueprint'
RETURN j;
```

### 3. Batching

```python
# algorithms/batch_processor.py
async def batch_synergy_queries(joker_names: List[str]) -> Dict[str, List[Synergy]]:
    """Execute multiple synergy queries in single transaction"""
    query = """
    UNWIND $joker_names AS joker_name
    MATCH (j:Joker {name: joker_name})-[s:SYNERGIZES_WITH]->(other)
    RETURN joker_name, collect({
        target: other.name,
        strength: s.strength,
        type: s.synergy_type
    }) as synergies
    """
    results = await memgraph.execute(query, {"joker_names": joker_names})
    return {r["joker_name"]: r["synergies"] for r in results}
```

## Schema Design Principles

### 1. Node Labels

- Keep labels specific: `:Joker`, `:PlayingCard`, `:Enhancement`
- Avoid generic labels like `:Entity` or `:Node`

### 2. Relationship Types

- Use descriptive names: `:SYNERGIZES_WITH`, `:REQUIRES_CARD`, `:COUNTERS`
- Include properties for strength/weight: `{strength: 0.8, confidence: 0.95}`

### 3. Property Design

```cypher
// Good: Specific, indexed properties
CREATE (j:Joker {
    name: 'Fibonacci',
    rarity: 'uncommon',
    cost: 7,
    base_chips: 8,
    base_mult: 0,
    scaling_type: 'fibonacci'
});

// Bad: Generic properties that require parsing
CREATE (j:Joker {
    data: '{"name": "Fibonacci", "stats": {...}}'
});
```

## Migration Strategy

### 1. Schema Versioning

```cypher
// migrations/001_initial_schema.cypher
CREATE CONSTRAINT ON (j:Joker) ASSERT j.name IS UNIQUE;
CREATE CONSTRAINT ON (c:Card) ASSERT (c.suit, c.rank) IS UNIQUE;

// Track migration version
CREATE (m:Migration {version: 1, applied_at: datetime()});
```

### 2. Data Migration Pattern

```python
# migrations/002_add_win_rates.py
async def migrate():
    """Add win_rate property to all SYNERGIZES_WITH relationships"""
    await memgraph.execute("""
        MATCH ()-[s:SYNERGIZES_WITH]->()
        WHERE s.win_rate IS NULL
        SET s.win_rate = 0.5  // Default value
    """)
```

## Testing Patterns

### 1. Query Performance Tests

```python
# tests/test_query_performance.py
import pytest
import time

@pytest.mark.performance
async def test_synergy_query_under_50ms():
    start = time.time()
    result = await execute_synergy_query("Blueprint")
    duration = (time.time() - start) * 1000
    assert duration < 50, f"Query took {duration}ms, exceeds 50ms limit"
```

### 2. MAGE Module Testing

```cpp
// tests/test_synergy_calculator.cpp
TEST(SynergyCalculator, PerformanceTest) {
    auto graph = create_test_graph_with_jokers(100);
    auto start = std::chrono::high_resolution_clock::now();

    calculate_all_synergies(graph, result, memory);

    auto duration = std::chrono::duration_cast<std::chrono::milliseconds>(
        std::chrono::high_resolution_clock::now() - start
    ).count();

    EXPECT_LT(duration, 50);  // Must complete in 50ms
}
```

## Integration with Ray/RLlib

### 1. Feature Extraction

```python
# algorithms/feature_extractor.py
async def extract_graph_features(game_state: GameState) -> np.ndarray:
    """Extract graph-based features for RL model"""
    features = []

    # Current joker synergies
    synergies = await get_active_synergies(game_state.jokers)
    features.extend(encode_synergies(synergies))

    # Path to victory analysis
    victory_paths = await analyze_victory_paths(game_state)
    features.extend(encode_paths(victory_paths))

    return np.array(features)
```

### 2. Knowledge Embedding

```python
# algorithms/knowledge_embedder.py
class JokerEmbedder:
    """Create vector embeddings from graph structure"""

    async def create_embeddings(self, embedding_dim: int = 128):
        # Use Node2Vec or similar algorithm
        embeddings = await memgraph.execute("""
            CALL node2vec.embed({
                dimensions: $dim,
                walk_length: 10,
                num_walks: 20,
                p: 1.0,
                q: 0.5
            })
            YIELD node, embedding
            WHERE node:Joker
            RETURN node.name as joker, embedding
        """, {"dim": embedding_dim})

        return {e["joker"]: e["embedding"] for e in embeddings}
```

## Common Pitfalls to Avoid

1. **N+1 Queries**: Always batch related queries
2. **Missing Indexes**: Profile queries and add indexes for WHERE clauses
3. **Unbounded Traversals**: Always set relationship depth limits
4. **Large Property Storage**: Store large data in external systems, reference
   by ID
5. **Synchronous Blocking**: Use async patterns for all queries

## Development Workflow

1. **Design Schema** → Write in `schema/` directory
2. **Create Indexes** → Add to migration scripts
3. **Write Queries** → Test with PROFILE for <50ms
4. **Optimize if Needed** → Create MAGE module in C++
5. **Integration Test** → Verify with Ray/RLlib pipeline

## Debugging Tools

```bash
# Connect to Memgraph console
mgconsole --host localhost --port 7687

# Profile query
PROFILE MATCH (j:Joker)-[:SYNERGIZES_WITH*1..2]->(other) RETURN count(other);

# Check indexes
SHOW INDEX INFO;

# Monitor query log
SHOW CONFIG GET 'query_log_level';
```

## Resource Limits

- **Memory**: 12GB allocated (10GB working + 2GB buffer)
- **Query Timeout**: 100ms hard limit (target <50ms)
- **Connection Pool**: 20 connections max
- **Transaction Size**: 10,000 operations per transaction

Remember: Knowledge graph performance directly impacts game play speed. Every
millisecond counts!
