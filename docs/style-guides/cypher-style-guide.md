# Cypher Query Language Style Guide for JimBot

This comprehensive style guide establishes best practices for writing Cypher
queries in the JimBot project, focusing on Memgraph-specific optimizations,
real-time performance, and knowledge graph patterns for the Balatro learning
system.

## Table of Contents

1. [Naming Conventions](#naming-conventions)
2. [Query Formatting](#query-formatting)
3. [Performance Patterns](#performance-patterns)
4. [Anti-Patterns to Avoid](#anti-patterns-to-avoid)
5. [Transaction Patterns](#transaction-patterns)
6. [Memgraph-Specific Optimizations](#memgraph-specific-optimizations)
7. [Knowledge Graph Patterns](#knowledge-graph-patterns)
8. [Real-Time Query Examples](#real-time-query-examples)

## Naming Conventions

### Node Labels

Use **UpperCamelCase** (PascalCase) for all node labels:

```cypher
// Good
(:Joker), (:Card), (:GameState), (:Strategy), (:SynergyPattern)

// Bad
(:joker), (:game_state), (:STRATEGY)
```

### Relationship Types

Use **ALL_UPPERCASE** with underscores for word separation:

```cypher
// Good
-[:SYNERGIZES_WITH]->
-[:REQUIRES_CARD]->
-[:LEADS_TO_STATE]->
-[:COUNTERS_STRATEGY]->

// Bad
-[:synergizesWith]->
-[:requires-card]->
-[:LeadsTo]->
```

### Properties

Use **camelCase** for property names (JSON-style):

```cypher
// Good
{name: "Baron", rarity: "common", cost: 4}
{winRate: 0.85, lastPlayed: timestamp()}

// Bad
{Name: "Baron", card_cost: 4}
{win_rate: 0.85, LastPlayed: timestamp()}
```

### Variables and Parameters

Use **camelCase** for variables and parameters:

```cypher
// Good
MATCH (j:Joker {name: $jokerName})
WITH j, count(s) AS synergyCount

// Bad
MATCH (J:Joker {name: $JokerName})
WITH J, count(s) AS SynergyCount
```

## Query Formatting

### Keyword Capitalization

Always use **UPPERCASE** for Cypher keywords:

```cypher
// Good
MATCH (j:Joker)
WHERE j.rarity = 'legendary'
RETURN j.name
ORDER BY j.cost DESC
LIMIT 10

// Bad
match (j:Joker)
where j.rarity = 'legendary'
return j.name
```

### Clause Structure

Start each clause on a new line with consistent indentation:

```cypher
// Good
MATCH (j:Joker)-[:SYNERGIZES_WITH]->(other:Joker)
WHERE j.name = 'Baron'
  AND other.rarity IN ['common', 'uncommon']
WITH j, collect(other) AS synergies
RETURN j.name, size(synergies) AS synergyCount

// Bad - all on one line
MATCH (j:Joker)-[:SYNERGIZES_WITH]->(other:Joker) WHERE j.name = 'Baron' AND other.rarity IN ['common', 'uncommon'] WITH j, collect(other) AS synergies RETURN j.name, size(synergies) AS synergyCount
```

### String Literals

Use single quotes for string literals:

```cypher
// Good
WHERE j.name = 'Baron'

// Bad
WHERE j.name = "Baron"
```

### Boolean and Null Values

Use lowercase for boolean and null values:

```cypher
// Good
WHERE j.isActive = true
  AND j.deprecated IS NOT null

// Bad
WHERE j.isActive = TRUE
  AND j.deprecated IS NOT NULL
```

## Performance Patterns

### 1. Index Usage

Create indexes on frequently queried properties:

```cypher
// Create indexes for optimal performance
CREATE INDEX ON :Joker(name);
CREATE INDEX ON :Card(suit, rank);
CREATE INDEX ON :GameState(timestamp);
CREATE INDEX ON :Strategy(winRate);

// Use indexed properties in WHERE clauses
MATCH (j:Joker)
WHERE j.name = 'Baron'  // Uses index
RETURN j
```

### 2. Early Filtering

Filter as early as possible in the query:

```cypher
// Good - filter in MATCH clause
MATCH (j:Joker {rarity: 'legendary'})
WHERE j.cost <= 5
RETURN j

// Better - all filters in MATCH when possible
MATCH (j:Joker {rarity: 'legendary', cost: 5})
RETURN j

// Bad - late filtering
MATCH (j:Joker)
WITH j
WHERE j.rarity = 'legendary' AND j.cost <= 5
RETURN j
```

### 3. Limit Variable-Length Paths

Always set upper bounds on variable-length patterns:

```cypher
// Good - bounded traversal
MATCH (j1:Joker)-[:SYNERGIZES_WITH*1..3]->(j2:Joker)
WHERE j1.name = 'Baron'
RETURN j2

// Bad - unbounded traversal (performance killer)
MATCH (j1:Joker)-[:SYNERGIZES_WITH*]->(j2:Joker)
WHERE j1.name = 'Baron'
RETURN j2
```

### 4. Use Parameters

Parameterize queries for better plan caching:

```cypher
// Good - parameterized
MATCH (j:Joker {name: $jokerName})
WHERE j.cost <= $maxCost
RETURN j

// Bad - hardcoded values
MATCH (j:Joker {name: 'Baron'})
WHERE j.cost <= 5
RETURN j
```

### 5. Project Only Needed Data

Return only required properties:

```cypher
// Good - specific properties
MATCH (j:Joker)-[:SYNERGIZES_WITH]->(other:Joker)
RETURN j.name, j.cost, collect(other.name) AS synergies

// Bad - returning entire nodes
MATCH (j:Joker)-[:SYNERGIZES_WITH]->(other:Joker)
RETURN j, collect(other) AS synergies
```

## Anti-Patterns to Avoid

### 1. Cartesian Products

```cypher
// BAD - Creates cartesian product
MATCH (j:Joker), (c:Card)
WHERE j.cost = 5
RETURN j, c

// GOOD - Explicit relationship
MATCH (j:Joker)-[:REQUIRES]->(c:Card)
WHERE j.cost = 5
RETURN j, c
```

### 2. Missing Labels

```cypher
// BAD - No label filter
MATCH (n)
WHERE n.name = 'Baron'
RETURN n

// GOOD - Use labels
MATCH (j:Joker)
WHERE j.name = 'Baron'
RETURN j
```

### 3. Dense Node Traversal

```cypher
// BAD - Traversing through hub nodes
MATCH (j:Joker)-[:PLAYED_IN]->(g:Game)-[:PLAYED_IN]-(other:Joker)
RETURN j, other

// GOOD - Direct relationships or limited traversal
MATCH (j:Joker)-[:SYNERGIZES_WITH]->(other:Joker)
RETURN j, other
```

### 4. Excessive OPTIONAL MATCH

```cypher
// BAD - Multiple optional matches
MATCH (j:Joker)
OPTIONAL MATCH (j)-[:SYNERGIZES_WITH]->(s1:Joker)
OPTIONAL MATCH (j)-[:COUNTERS]->(s2:Joker)
OPTIONAL MATCH (j)-[:REQUIRES]->(c:Card)
RETURN j, s1, s2, c

// GOOD - Pattern comprehension or subqueries
MATCH (j:Joker)
RETURN j,
  [(j)-[:SYNERGIZES_WITH]->(s:Joker) | s.name] AS synergies,
  [(j)-[:COUNTERS]->(c:Joker) | c.name] AS counters,
  [(j)-[:REQUIRES]->(card:Card) | card] AS requiredCards
```

### 5. Query Part Splitting

```cypher
// BAD - Multiple MATCH clauses split query
MATCH (j:Joker {name: 'Baron'})
WITH j
MATCH (j)-[:SYNERGIZES_WITH]->(other)
RETURN j, other

// GOOD - Single MATCH pattern
MATCH (j:Joker {name: 'Baron'})-[:SYNERGIZES_WITH]->(other)
RETURN j, other
```

## Transaction Patterns

### Batch Operations

Use transactions for bulk updates:

```cypher
// Good - Batch insert with UNWIND
UNWIND $jokerData AS data
CREATE (j:Joker {
  name: data.name,
  rarity: data.rarity,
  cost: data.cost,
  effect: data.effect
})

// For large batches, use CALL IN TRANSACTIONS
CALL {
  MATCH (j:Joker)
  WHERE j.lastAnalyzed < datetime() - duration('P7D')
  SET j.needsAnalysis = true
} IN TRANSACTIONS OF 1000 ROWS
```

### Read-Write Separation

Keep read and write operations separate:

```cypher
// Good - Separate read query
MATCH (j:Joker)-[:SYNERGIZES_WITH]->(other:Joker)
WHERE j.name = 'Baron'
RETURN other.name, other.rarity

// Good - Separate write query
MATCH (j:Joker {name: 'Baron'})
SET j.lastPlayed = timestamp()
```

### Idempotent Updates

Use MERGE for idempotent operations:

```cypher
// Good - MERGE ensures no duplicates
MERGE (j:Joker {name: 'Baron'})
ON CREATE SET
  j.created = timestamp(),
  j.playCount = 0
ON MATCH SET
  j.lastSeen = timestamp(),
  j.playCount = j.playCount + 1
```

## Memgraph-Specific Optimizations

### 1. Query Plan Caching

Structure queries to maximize plan reuse:

```cypher
// Good - Consistent structure enables caching
MATCH (j:Joker {name: $jokerName})
OPTIONAL MATCH (j)-[:SYNERGIZES_WITH]->(synergy:Joker)
RETURN j, collect(synergy) AS synergies

// Avoid schema changes that invalidate cache
// Run index creation during maintenance windows
```

### 2. Memory Limits for Deep Traversals

Set memory limits before expensive queries:

```cypher
// Set query memory limit (80% of available)
:query memory-limit 6GB

// Then run deep traversal
MATCH path = (j:Joker {name: 'Baron'})-[:SYNERGIZES_WITH*1..5]->(target:Joker)
WHERE all(node IN nodes(path) WHERE node.rarity <> 'legendary')
RETURN path
LIMIT 100
```

### 3. In-Memory Analytics Mode

For bulk analysis without ACID guarantees:

```cypher
// Use for read-heavy analytical queries
MATCH (j:Joker)
WITH j.rarity AS rarity, avg(j.cost) AS avgCost, count(j) AS count
RETURN rarity, avgCost, count
ORDER BY avgCost DESC
```

### 4. Built-in Algorithm Usage

Leverage Memgraph's C++ algorithms:

```cypher
// Use built-in shortest path
MATCH (j1:Joker {name: 'Baron'}), (j2:Joker {name: 'Mime'})
CALL algo.shortestPath(j1, j2) YIELD path
RETURN path

// Use built-in BFS for traversal
MATCH (start:Joker {name: 'Baron'})
CALL algo.bfs(start, 'SYNERGIZES_WITH', 3) YIELD node
RETURN node
```

## Knowledge Graph Patterns

### 1. Hierarchical Relationships

```cypher
// Define strategy hierarchies
CREATE (root:Strategy {name: 'High Card'})
CREATE (flush:Strategy {name: 'Flush Build'})-[:SPECIALIZES]->(root)
CREATE (straight:Strategy {name: 'Straight Build'})-[:SPECIALIZES]->(root)

// Query with hierarchy
MATCH (s:Strategy)-[:SPECIALIZES*0..3]->(root:Strategy {name: 'High Card'})
RETURN s.name, size((s)-[:SPECIALIZES*]->()) AS depth
ORDER BY depth
```

### 2. Temporal Patterns

```cypher
// Track game state evolution
CREATE (gs1:GameState {ante: 1, score: 0, timestamp: timestamp()})
CREATE (gs2:GameState {ante: 1, score: 150, timestamp: timestamp() + 30000})
CREATE (gs1)-[:TRANSITIONS_TO {action: 'playHand', duration: 30000}]->(gs2)

// Query temporal sequences
MATCH path = (start:GameState)-[:TRANSITIONS_TO*]->(end:GameState)
WHERE start.ante = 1 AND end.ante = 8
RETURN path, reduce(time = 0, r IN relationships(path) | time + r.duration) AS totalTime
ORDER BY totalTime
LIMIT 5
```

### 3. Synergy Networks

```cypher
// Create synergy network
MATCH (j1:Joker), (j2:Joker)
WHERE j1.name < j2.name  // Avoid duplicates
  AND exists((j1)-[:WORKS_WELL_WITH]->(j2))
MERGE (j1)-[s:SYNERGIZES_WITH]->(j2)
SET s.strength =
  CASE
    WHEN j1.rarity = 'legendary' AND j2.rarity = 'legendary' THEN 1.0
    WHEN j1.rarity = 'legendary' OR j2.rarity = 'legendary' THEN 0.8
    ELSE 0.6
  END

// Find synergy clusters
MATCH (j:Joker)
WITH j, size((j)-[:SYNERGIZES_WITH]-()) AS degree
WHERE degree >= 3
MATCH (j)-[:SYNERGIZES_WITH]-(connected)
WITH j, collect(DISTINCT connected) AS cluster
RETURN j.name, [c IN cluster | c.name] AS clusterMembers
ORDER BY size(cluster) DESC
```

### 4. Decision Trees

```cypher
// Model decision paths
CREATE (root:Decision {state: 'ante_4_low_money'})
CREATE (buy:Decision {state: 'buy_joker'})-[:IF {condition: 'money >= 25'}]->(root)
CREATE (skip:Decision {state: 'skip_shop'})-[:IF {condition: 'money < 25'}]->(root)

// Query optimal paths
MATCH path = (d:Decision)-[:IF*]->(outcome:Decision)
WHERE d.state = 'ante_4_low_money'
  AND outcome.state CONTAINS 'win'
RETURN path,
  reduce(prob = 1.0, r IN relationships(path) | prob * r.probability) AS pathProbability
ORDER BY pathProbability DESC
```

## Real-Time Query Examples

### 1. Fast Joker Recommendation (Target: <50ms)

```cypher
// Optimized for speed with precomputed scores
MATCH (current:GameState {isCurrent: true})
MATCH (j:Joker)
WHERE NOT exists((current)-[:HAS_JOKER]->(j))
  AND j.cost <= current.money
WITH j, j.baseScore +
  CASE
    WHEN current.ante >= 4 THEN j.lateGameBonus
    ELSE 0
  END AS score
RETURN j.name, j.cost, score
ORDER BY score DESC
LIMIT 5
```

### 2. Real-Time Synergy Check (Target: <30ms)

```cypher
// Use indexed lookups and limited traversal
MATCH (current:GameState {isCurrent: true})-[:HAS_JOKER]->(owned:Joker)
WITH collect(owned) AS ownedJokers
MATCH (candidate:Joker {name: $candidateName})
WHERE NOT candidate IN ownedJokers
OPTIONAL MATCH (candidate)-[s:SYNERGIZES_WITH]->(owned)
WHERE owned IN ownedJokers
RETURN candidate.name,
  count(s) AS synergyCount,
  sum(s.strength) AS totalStrength
```

### 3. Pattern Recognition (Target: <100ms)

```cypher
// Detect winning patterns from current state
MATCH (current:GameState {isCurrent: true})
MATCH (pattern:WinningPattern)
WHERE all(req IN pattern.requirements WHERE
  CASE req.type
    WHEN 'joker' THEN exists((current)-[:HAS_JOKER]->(:Joker {name: req.value}))
    WHEN 'money' THEN current.money >= toInteger(req.value)
    WHEN 'ante' THEN current.ante >= toInteger(req.value)
    ELSE false
  END
)
WITH pattern, pattern.historicWinRate * pattern.difficultyMultiplier AS score
RETURN pattern.name, pattern.description, score
ORDER BY score DESC
LIMIT 3
```

### 4. Performance Monitoring Query

```cypher
// Track query performance metrics
CREATE (qm:QueryMetric {
  queryType: $queryType,
  timestamp: timestamp(),
  executionTime: $executionTime,
  resultCount: $resultCount
})

// Analyze performance trends
MATCH (qm:QueryMetric)
WHERE qm.timestamp > timestamp() - 3600000  // Last hour
WITH qm.queryType AS type,
  avg(qm.executionTime) AS avgTime,
  max(qm.executionTime) AS maxTime,
  count(qm) AS queryCount
WHERE avgTime > 50  // Flag slow queries
RETURN type, round(avgTime) AS avgMs, round(maxTime) AS maxMs, queryCount
ORDER BY avgMs DESC
```

## Summary

This style guide provides a comprehensive foundation for writing efficient,
maintainable Cypher queries in the JimBot project. Key takeaways:

1. **Consistency is King**: Follow naming conventions religiously
2. **Performance First**: Always consider query performance implications
3. **Memgraph Advantages**: Leverage platform-specific features for speed
4. **Real-Time Focus**: Design queries with <100ms response time targets
5. **Avoid Anti-Patterns**: Learn from common mistakes to write better queries

Remember that JimBot's success depends on fast, accurate queries that can keep
pace with real-time game decisions. Every millisecond counts when making
strategic choices in Balatro.
