# Testing Guidelines for JimBot

This document provides Claude Code with guidance for maintaining and extending
the JimBot test suite.

## Testing Philosophy

- **Test-Driven Development**: Write tests before implementation when possible
- **Sequential Thinking**: Test complex decision sequences, not just individual
  functions
- **Integration Focus**: Prioritize testing component interactions over isolated
  units
- **Performance Awareness**: Include benchmarks for critical paths

## Coverage Targets

### Overall Target: >80% Code Coverage

Component-specific targets:

- **MCP**: >85% (critical communication layer)
- **Memgraph**: >80% (complex graph operations)
- **Training**: >75% (allow for experimental code)
- **LLM**: >90% (expensive operations need validation)
- **Analytics**: >80% (data integrity critical)

## Test Categories

### Unit Tests (`/unit/`)

- Fast, isolated tests (<100ms per test)
- Mock external dependencies
- Focus on pure functions and single classes
- Run on every commit

### Integration Tests (`/integration/`)

- Test component interactions
- Use Docker containers for dependencies
- Test realistic data flows
- Run on PR creation/update

### Performance Tests (`/performance/`)

- Benchmark critical operations
- Track performance regressions
- Memory usage profiling
- Run nightly or on-demand

## Writing Tests

### Naming Conventions

```python
# Test file naming
test_<module_name>.py

# Test function naming
def test_<function>_<scenario>_<expected_result>():
    """Test that <function> <expected behavior> when <scenario>."""
    pass
```

### Test Structure

```python
# Arrange
game_state = create_test_game_state()
aggregator = EventAggregator(batch_window_ms=50)

# Act
result = aggregator.process_events(game_state.events)

# Assert
assert result.latency_ms < 100
assert len(result.aggregated_events) == expected_count
```

## Performance Benchmarks

### MCP Event Processing

- Event aggregation: <100ms for 1000 events
- WebSocket latency: <10ms round-trip
- Memory usage: <100MB for 10k events

### Memgraph Queries

- Simple lookups: <5ms
- Complex traversals: <50ms
- Bulk insertions: >1000 nodes/second

### Ray Training

- Step processing: >1000 steps/second
- Checkpoint save: <5 seconds
- Model inference: <10ms per decision

### Claude Integration

- Response time: <2 seconds (excluding API latency)
- Context building: <100ms
- Cache hit rate: >80%

## Test Data Management

### Fixtures (`/fixtures/`)

- Realistic game states
- Pre-computed graph data
- Trained model checkpoints
- Mock API responses

### Data Generation

```python
# fixtures/game_states.py
def create_ante_8_game_state():
    """Create a challenging late-game state."""
    return GameState(
        ante=8,
        money=25,
        jokers=[...],
        deck=[...],
        blinds_defeated=45
    )
```

## Continuous Integration

### Pre-commit Hooks

```yaml
- Run unit tests for changed modules
- Check code coverage hasn't decreased
- Validate performance benchmarks
```

### PR Checks

```yaml
- Full unit test suite
- Integration tests
- Coverage report with 80% threshold
- Performance regression detection
```

## Debugging Test Failures

### Common Issues

1. **Flaky Tests**: Use `pytest-retry` for network-dependent tests
2. **Memory Leaks**: Profile with `memory_profiler`
3. **Timing Issues**: Use proper async patterns, avoid `time.sleep()`
4. **Docker Issues**: Ensure containers are properly cleaned up

### Debugging Commands

```bash
# Run single test with verbose output
pytest tests/unit/mcp/test_aggregator.py::test_event_batching -vvs

# Run with coverage for specific module
pytest tests/unit/memgraph --cov=jimbot.memgraph --cov-report=html

# Profile memory usage
pytest tests/performance/test_memory.py --memprof
```

## Test Maintenance

### Weekly Tasks

- Review and update flaky test list
- Check coverage trends
- Update performance baselines

### Monthly Tasks

- Audit test data for staleness
- Review and consolidate duplicate tests
- Update integration test scenarios

## Best Practices

1. **Keep Tests Fast**: Aim for <10 second total unit test runtime
2. **Test Behaviors, Not Implementation**: Focus on outcomes
3. **Use Descriptive Names**: Test names should explain what and why
4. **Avoid Test Interdependencies**: Each test should be independent
5. **Mock Expensive Operations**: Claude API, GPU operations, etc.

## Component-Specific Guidelines

### MCP Tests

- Test event ordering guarantees
- Validate batch processing windows
- Check reconnection logic

### Memgraph Tests

- Use in-memory instances for unit tests
- Test schema migrations
- Validate query performance

### Training Tests

- Use small models for unit tests
- Test checkpoint recovery
- Validate reward calculations

### LLM Tests

- Mock API responses
- Test rate limiting
- Validate prompt construction

### Analytics Tests

- Test data aggregation accuracy
- Validate time-series queries
- Check metric calculations
