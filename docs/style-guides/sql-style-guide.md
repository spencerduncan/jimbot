# SQL Style Guide for JimBot

This guide defines SQL conventions for the JimBot project, with specific focus
on QuestDB time-series patterns and game performance analytics.

## Table of Contents

1. [General Principles](#general-principles)
2. [Naming Conventions](#naming-conventions)
3. [QuestDB-Specific Extensions](#questdb-specific-extensions)
4. [Time-Series Query Patterns](#time-series-query-patterns)
5. [Index Design](#index-design)
6. [Partitioning Strategies](#partitioning-strategies)
7. [Game Analytics Schema](#game-analytics-schema)
8. [Performance Optimization](#performance-optimization)

## General Principles

Based on Simon Holywell's SQL Style Guide and QuestDB best practices:

- **Consistency**: Maintain consistent naming and formatting throughout all
  queries
- **Readability**: Use white space and indentation to enhance code clarity
- **Portability**: Prefer standard SQL functions over vendor-specific when
  possible
- **Efficiency**: Write concise queries without redundant clauses
- **Documentation**: Include comments for complex logic

### Formatting Rules

```sql
-- Good: Keywords uppercase, proper indentation
SELECT
    player_id,
    session_id,
    SUM(score) AS total_score,
    AVG(decision_time_ms) AS avg_decision_time
FROM
    game_events
WHERE
    timestamp BETWEEN '2024-01-01' AND '2024-01-31'
    AND event_type = 'hand_played'
GROUP BY
    player_id,
    session_id
ORDER BY
    total_score DESC;

-- Bad: Poor formatting
select player_id,session_id,sum(score) as total_score,avg(decision_time_ms) as avg_decision_time from game_events where timestamp between '2024-01-01' and '2024-01-31' and event_type='hand_played' group by player_id,session_id order by total_score desc;
```

## Naming Conventions

### Tables

- Use **singular** nouns for clarity (e.g., `game_session` not `game_sessions`)
- Maximum 30 characters
- Lowercase with underscores for word separation
- No prefixes like `tbl_` or Hungarian notation

```sql
-- Good table names
CREATE TABLE game_session (...);
CREATE TABLE player_action (...);
CREATE TABLE joker_synergy (...);
CREATE TABLE performance_metric (...);

-- Bad table names
CREATE TABLE tbl_GameSessions (...);  -- Avoid prefixes and mixed case
CREATE TABLE player-actions (...);     -- Use underscores, not hyphens
```

### Columns

- Use descriptive, self-documenting names
- Lowercase with underscores
- Standard suffixes for common patterns:
  - `_id` - Unique identifiers (primary/foreign keys)
  - `_at` - Timestamps (e.g., `created_at`, `played_at`)
  - `_ms` - Millisecond durations
  - `_count` - Counting metrics
  - `_rate` - Rate/percentage metrics
  - `_total` - Cumulative sums

```sql
-- Good column names
CREATE TABLE game_event (
    event_id LONG,                      -- Primary key
    session_id SYMBOL,                  -- Foreign key reference
    player_id SYMBOL,                   -- Foreign key reference
    timestamp TIMESTAMP,                -- Designated timestamp
    event_type SYMBOL,                  -- Categorical data
    decision_time_ms INT,               -- Duration in milliseconds
    score_gained INT,                   -- Points from this event
    chips_total INT,                    -- Current total chips
    win_rate DOUBLE,                    -- Percentage as decimal
    created_at TIMESTAMP                -- Event creation time
) TIMESTAMP(timestamp) PARTITION BY DAY;
```

### Indexes

Name indexes clearly to indicate their purpose:

```sql
-- Pattern: idx_<table>_<columns>
CREATE INDEX idx_game_event_player_session
ON game_event(player_id, session_id);

CREATE INDEX idx_performance_metric_session_type
ON performance_metric(session_id, metric_type);
```

## QuestDB-Specific Extensions

### SAMPLE BY for Time Aggregation

Use `SAMPLE BY` for efficient time-based grouping:

```sql
-- Calculate 5-minute performance metrics
SELECT
    timestamp,
    player_id,
    AVG(decision_time_ms) AS avg_decision_time,
    SUM(score_gained) AS total_score,
    COUNT() AS actions_count
FROM
    game_event
WHERE
    timestamp BETWEEN '2024-01-01' AND '2024-01-02'
    AND event_type = 'decision'
SAMPLE BY 5m
FILL(NULL);  -- Handle missing intervals

-- Daily player performance summary
SELECT
    timestamp,
    player_id,
    SUM(chips_gained) AS daily_chips,
    MAX(highest_mult) AS best_multiplier,
    COUNT(DISTINCT session_id) AS sessions_played
FROM
    player_action
WHERE
    timestamp > dateadd('d', -7, now())
SAMPLE BY 1d
ALIGN TO CALENDAR;  -- Align to day boundaries
```

### LATEST ON for Current State

Retrieve the most recent state efficiently:

```sql
-- Get latest player statistics
SELECT
    player_id,
    elo_rating,
    total_games,
    win_rate,
    timestamp
FROM
    player_stats
LATEST ON timestamp PARTITION BY player_id;

-- Find current session states
SELECT
    session_id,
    current_ante,
    current_blind,
    chips_total,
    active_jokers
FROM
    session_state
WHERE
    player_id = 'player_123'
LATEST ON timestamp PARTITION BY session_id;
```

### Timestamp Search Optimization

Use QuestDB's native timestamp notation:

```sql
-- Good: Native timestamp search
SELECT * FROM game_event
WHERE timestamp IN '2024-01-01;1d';  -- All events on Jan 1

SELECT * FROM performance_metric
WHERE timestamp IN '2024-01;1M';     -- All January events

-- Also good but less efficient
SELECT * FROM game_event
WHERE timestamp >= '2024-01-01'
  AND timestamp < '2024-01-02';
```

## Time-Series Query Patterns

### Real-Time Performance Monitoring

```sql
-- Monitor live game performance (last 5 minutes)
SELECT
    timestamp,
    COUNT() AS events_per_second,
    AVG(decision_time_ms) AS avg_response_time,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY decision_time_ms) AS p95_response
FROM
    game_event
WHERE
    timestamp > dateadd('m', -5, now())
SAMPLE BY 1s
FILL(0);

-- Track strategy effectiveness over time
WITH strategy_performance AS (
    SELECT
        timestamp,
        strategy_id,
        COUNT() AS uses,
        AVG(score_gained) AS avg_score,
        SUM(CASE WHEN won_hand = true THEN 1 ELSE 0 END) AS wins
    FROM
        strategy_event
    WHERE
        timestamp > dateadd('h', -24, now())
    GROUP BY
        timestamp,
        strategy_id
    SAMPLE BY 1h
)
SELECT
    timestamp,
    strategy_id,
    uses,
    avg_score,
    wins::DOUBLE / uses AS win_rate
FROM
    strategy_performance
WHERE
    uses > 10;  -- Filter out low-sample strategies
```

### Session Analysis

```sql
-- Analyze session patterns
WITH session_metrics AS (
    SELECT
        session_id,
        player_id,
        MIN(timestamp) AS session_start,
        MAX(timestamp) AS session_end,
        COUNT() AS total_actions,
        SUM(score_gained) AS total_score,
        MAX(highest_ante) AS max_ante_reached
    FROM
        game_event
    WHERE
        timestamp > dateadd('d', -7, now())
    GROUP BY
        session_id,
        player_id
)
SELECT
    player_id,
    COUNT(session_id) AS sessions_count,
    AVG(DATEDIFF('minute', session_start, session_end)) AS avg_session_length,
    AVG(total_actions) AS avg_actions_per_session,
    AVG(total_score) AS avg_score_per_session,
    MAX(max_ante_reached) AS best_ante
FROM
    session_metrics
GROUP BY
    player_id
ORDER BY
    sessions_count DESC;
```

## Index Design

### Primary Indexes

```sql
-- Time-series primary index (implicit on designated timestamp)
CREATE TABLE game_event (
    event_id LONG,
    timestamp TIMESTAMP,
    -- ... other columns
) TIMESTAMP(timestamp) PARTITION BY DAY;

-- Symbol columns for efficient filtering
CREATE TABLE player_action (
    action_id LONG,
    timestamp TIMESTAMP,
    player_id SYMBOL CAPACITY 10000,      -- Expected unique players
    session_id SYMBOL CAPACITY 100000,    -- Expected sessions
    action_type SYMBOL CAPACITY 50,       -- Limited action types
    -- ... other columns
) TIMESTAMP(timestamp) PARTITION BY DAY;
```

### Secondary Indexes for Analytics

```sql
-- Composite index for player session queries
CREATE INDEX idx_event_player_session_time
ON game_event(player_id, session_id, timestamp);

-- Index for strategy analysis
CREATE INDEX idx_strategy_type_outcome
ON strategy_event(strategy_type, outcome, timestamp);

-- Index for performance tracking
CREATE INDEX idx_metric_type_player
ON performance_metric(metric_type, player_id, timestamp);
```

## Partitioning Strategies

### Daily Partitioning for High-Volume Tables

```sql
-- Game events with daily partitions
CREATE TABLE game_event (
    event_id LONG,
    timestamp TIMESTAMP,
    player_id SYMBOL,
    event_data STRING
) TIMESTAMP(timestamp) PARTITION BY DAY;

-- Performance metrics with daily partitions
CREATE TABLE performance_metric (
    metric_id LONG,
    timestamp TIMESTAMP,
    metric_type SYMBOL,
    metric_value DOUBLE
) TIMESTAMP(timestamp) PARTITION BY DAY;
```

### Weekly/Monthly Partitioning for Summary Tables

```sql
-- Weekly summaries for medium-term analysis
CREATE TABLE weekly_player_summary (
    week_start TIMESTAMP,
    player_id SYMBOL,
    games_played INT,
    total_score LONG,
    avg_decision_time DOUBLE
) TIMESTAMP(week_start) PARTITION BY WEEK;

-- Monthly aggregates for long-term trends
CREATE TABLE monthly_strategy_stats (
    month_start TIMESTAMP,
    strategy_id SYMBOL,
    usage_count LONG,
    success_rate DOUBLE
) TIMESTAMP(month_start) PARTITION BY MONTH;
```

## Game Analytics Schema

### Core Event Tables

```sql
-- Main game event stream
CREATE TABLE game_event (
    event_id LONG,
    timestamp TIMESTAMP,
    session_id SYMBOL CAPACITY 100000,
    player_id SYMBOL CAPACITY 10000,
    ante_level INT,
    blind_level INT,
    event_type SYMBOL CAPACITY 50,
    event_data STRING,  -- JSON for flexibility
    score_gained INT,
    chips_gained INT,
    decision_time_ms INT,
    created_at TIMESTAMP
) TIMESTAMP(timestamp) PARTITION BY DAY;

-- Joker synergy events
CREATE TABLE joker_synergy_event (
    synergy_id LONG,
    timestamp TIMESTAMP,
    session_id SYMBOL,
    joker_combination STRING,  -- JSON array of joker IDs
    trigger_count INT,
    multiplier_achieved DOUBLE,
    chips_gained INT
) TIMESTAMP(timestamp) PARTITION BY DAY;

-- Strategy decision tracking
CREATE TABLE strategy_decision (
    decision_id LONG,
    timestamp TIMESTAMP,
    session_id SYMBOL,
    player_id SYMBOL,
    game_state_hash SYMBOL,  -- For deduplication
    strategy_chosen SYMBOL,
    alternative_strategies STRING,  -- JSON array
    expected_value DOUBLE,
    actual_outcome DOUBLE,
    decision_source SYMBOL  -- 'model', 'claude', 'random'
) TIMESTAMP(timestamp) PARTITION BY DAY;
```

### Performance Tracking Tables

```sql
-- Real-time performance metrics
CREATE TABLE performance_metric (
    metric_id LONG,
    timestamp TIMESTAMP,
    session_id SYMBOL,
    player_id SYMBOL,
    metric_type SYMBOL CAPACITY 100,
    metric_value DOUBLE,
    context STRING  -- JSON for additional context
) TIMESTAMP(timestamp) PARTITION BY DAY;

-- Model performance tracking
CREATE TABLE model_performance (
    eval_id LONG,
    timestamp TIMESTAMP,
    model_version SYMBOL,
    games_played INT,
    avg_score DOUBLE,
    avg_ante_reached DOUBLE,
    win_rate DOUBLE,
    decision_accuracy DOUBLE
) TIMESTAMP(timestamp) PARTITION BY DAY;
```

### Aggregate Tables

```sql
-- Hourly player statistics
CREATE TABLE hourly_player_stats (
    hour_timestamp TIMESTAMP,
    player_id SYMBOL,
    games_played INT,
    total_score LONG,
    highest_ante INT,
    avg_decision_time_ms DOUBLE,
    unique_strategies_used INT
) TIMESTAMP(hour_timestamp) PARTITION BY DAY;

-- Daily strategy effectiveness
CREATE TABLE daily_strategy_stats (
    day_timestamp TIMESTAMP,
    strategy_id SYMBOL,
    usage_count LONG,
    success_count LONG,
    avg_score_gain DOUBLE,
    avg_ante_when_used DOUBLE
) TIMESTAMP(day_timestamp) PARTITION BY MONTH;
```

## Performance Optimization

### Query Optimization Patterns

```sql
-- Filter early in subqueries
WITH filtered_events AS (
    -- Apply filters in the CTE
    SELECT
        session_id,
        timestamp,
        score_gained
    FROM
        game_event
    WHERE
        timestamp > dateadd('h', -1, now())
        AND player_id = 'player_123'
        AND event_type = 'hand_played'
)
SELECT
    session_id,
    COUNT() AS hands_played,
    SUM(score_gained) AS total_score
FROM
    filtered_events
GROUP BY
    session_id;

-- Use designated timestamp for partition pruning
SELECT
    COUNT() AS event_count
FROM
    game_event
WHERE
    timestamp IN '2024-01-15;1d'  -- Only scans one partition
    AND player_id = 'player_123';

-- Scope columns to reduce I/O
SELECT
    timestamp,
    decision_time_ms,  -- Only fetch needed columns
    score_gained
FROM
    game_event
WHERE
    timestamp > dateadd('m', -10, now())
SAMPLE BY 10s;
```

### Batch Processing Patterns

```sql
-- Efficient batch insert for event aggregation
INSERT INTO hourly_player_stats
SELECT
    date_trunc('hour', timestamp) AS hour_timestamp,
    player_id,
    COUNT(DISTINCT session_id) AS games_played,
    SUM(score_gained) AS total_score,
    MAX(ante_level) AS highest_ante,
    AVG(decision_time_ms) AS avg_decision_time_ms,
    COUNT(DISTINCT strategy_chosen) AS unique_strategies_used
FROM
    game_event
WHERE
    timestamp >= date_trunc('hour', dateadd('h', -1, now()))
    AND timestamp < date_trunc('hour', now())
GROUP BY
    date_trunc('hour', timestamp),
    player_id;

-- Periodic cleanup of old partitions
-- Run daily to maintain 30-day retention
ALTER TABLE game_event DROP PARTITION
WHERE timestamp < dateadd('d', -30, now());
```

### Monitoring Queries

```sql
-- System health check
SELECT
    table_name,
    partition_by,
    COUNT() AS partition_count,
    SUM(row_count) AS total_rows,
    MAX(max_timestamp) AS latest_data
FROM
    table_partitions
WHERE
    table_name IN ('game_event', 'performance_metric', 'strategy_decision')
GROUP BY
    table_name,
    partition_by;

-- Query performance tracking
WITH recent_queries AS (
    SELECT
        query_text,
        execution_time_ms,
        rows_processed,
        timestamp
    FROM
        query_log
    WHERE
        timestamp > dateadd('h', -1, now())
)
SELECT
    SUBSTRING(query_text, 1, 50) AS query_preview,
    COUNT() AS execution_count,
    AVG(execution_time_ms) AS avg_time_ms,
    MAX(execution_time_ms) AS max_time_ms,
    SUM(rows_processed) AS total_rows
FROM
    recent_queries
GROUP BY
    SUBSTRING(query_text, 1, 50)
ORDER BY
    avg_time_ms DESC
LIMIT 10;
```

## Best Practices Summary

1. **Always use designated timestamps** for time-series tables
2. **Partition by time** appropriate to your data volume (DAY for high-volume,
   WEEK/MONTH for summaries)
3. **Use SYMBOL type** for categorical data with known cardinality
4. **Apply filters early** and on designated timestamp when possible
5. **Leverage SAMPLE BY** for time-based aggregations
6. **Use LATEST ON** for current state queries
7. **Scope columns** to only what's needed
8. **Monitor partition growth** and implement retention policies
9. **Create indexes** on frequently filtered non-timestamp columns
10. **Batch aggregations** for summary tables during off-peak hours
