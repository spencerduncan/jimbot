# JimBot Test Suite

This directory contains all tests for the JimBot system, organized by test type
and component.

## Directory Structure

```
tests/
├── unit/              # Fast, isolated unit tests
│   ├── mcp/          # MCP communication tests
│   ├── memgraph/     # Graph database tests
│   ├── training/     # Ray/RLlib training tests
│   ├── llm/          # Claude integration tests
│   └── analytics/    # Metrics and monitoring tests
├── integration/       # Cross-component integration tests
├── performance/       # Performance benchmarks and profiling
├── fixtures/          # Shared test data and utilities
├── conftest.py        # Shared pytest configuration
├── CLAUDE.md          # Guidelines for Claude Code
└── README.md          # This file
```

## Quick Start

### Running All Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=jimbot --cov-report=html

# Run in parallel (faster)
pytest -n auto
```

### Running Specific Test Categories

```bash
# Unit tests only
pytest tests/unit/ -v

# Integration tests
pytest tests/integration/ -v

# Performance benchmarks
pytest tests/performance/ -v --benchmark-only

# Specific component
pytest tests/unit/mcp/ -v
```

### Common Test Commands

```bash
# Run tests matching a pattern
pytest -k "event_aggregation"

# Run a specific test file
pytest tests/unit/mcp/test_aggregator.py

# Run with debugging output
pytest -vvs tests/unit/mcp/test_server.py

# Run failed tests from last run
pytest --lf

# Run tests that cover a specific file
pytest --cov=jimbot.mcp.aggregator --cov-report=term-missing
```

## Test Organization

### Unit Tests

Each component has its own subdirectory with tests organized by module:

```
unit/mcp/
├── test_server.py
├── test_aggregator.py
├── test_protocol.py
└── test_websocket.py
```

### Integration Tests

Tests that span multiple components:

```
integration/
├── test_mcp_to_ray.py
├── test_memgraph_queries.py
├── test_end_to_end_training.py
└── test_claude_integration.py
```

### Performance Tests

Benchmarks and profiling tests:

```
performance/
├── test_event_throughput.py
├── test_graph_query_performance.py
├── test_training_speed.py
└── test_memory_usage.py
```

## Writing Tests

### Basic Test Structure

```python
import pytest
from jimbot.mcp import EventAggregator

class TestEventAggregator:
    """Test the MCP event aggregator."""

    @pytest.fixture
    def aggregator(self):
        """Create an aggregator instance for testing."""
        return EventAggregator(batch_window_ms=50)

    def test_aggregates_events_within_window(self, aggregator):
        """Test that events are properly batched within time window."""
        # Test implementation
        pass
```

### Using Fixtures

Common fixtures are defined in `conftest.py` and component-specific fixture
files:

```python
# Use provided fixtures
def test_game_state_processing(sample_game_state, memgraph_client):
    """Test processing a complete game state."""
    result = memgraph_client.store_game_state(sample_game_state)
    assert result.success
```

## CI Integration

### GitHub Actions Workflow

Tests run automatically on:

- Every push to a PR
- Merges to main
- Nightly for performance tests

### Local Pre-commit Hooks

Install pre-commit hooks:

```bash
pre-commit install
```

This runs:

- Unit tests for changed files
- Code formatting checks
- Basic linting

## Test Coverage

### Current Coverage Requirements

- Overall: >80%
- Critical components (MCP, LLM): >85%
- New code: >90%

### Viewing Coverage Reports

```bash
# Generate HTML coverage report
pytest --cov=jimbot --cov-report=html

# Open in browser
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

### Excluding Code from Coverage

```python
# Mark code as not needing coverage
if TYPE_CHECKING:  # pragma: no cover
    from typing import SomeType
```

## Performance Testing

### Running Benchmarks

```bash
# Run all benchmarks
pytest tests/performance/ --benchmark-only

# Compare with saved results
pytest tests/performance/ --benchmark-compare

# Save results for comparison
pytest tests/performance/ --benchmark-save=baseline
```

### Memory Profiling

```bash
# Profile memory usage
pytest tests/performance/test_memory.py --memprof

# Generate memory report
python -m memory_profiler tests/performance/profile_training.py
```

## Debugging Failed Tests

### Verbose Output

```bash
# Maximum verbosity
pytest -vvvs tests/unit/mcp/test_aggregator.py

# Show local variables on failure
pytest -l tests/unit/mcp/test_aggregator.py
```

### Using Debugger

```python
# Add breakpoint in test
def test_complex_scenario():
    # ... setup ...
    import pdb; pdb.set_trace()  # Debugger will stop here
    # ... test ...
```

### Docker-based Tests

```bash
# Ensure containers are running
docker-compose -f tests/docker-compose.test.yml up -d

# Run integration tests
pytest tests/integration/

# Clean up
docker-compose -f tests/docker-compose.test.yml down
```

## Best Practices

1. **Keep Tests Fast**: Unit tests should run in <100ms
2. **Test One Thing**: Each test should verify a single behavior
3. **Use Descriptive Names**: Test names should explain what and why
4. **Avoid External Dependencies**: Mock external services in unit tests
5. **Clean Up Resources**: Ensure tests don't leave artifacts

## Troubleshooting

### Common Issues

**Import Errors**

```bash
# Ensure jimbot is in PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:/home/spduncan/jimbot-ws/jimbot-main"
```

**Docker Connection Issues**

```bash
# Reset test containers
docker-compose -f tests/docker-compose.test.yml down -v
docker-compose -f tests/docker-compose.test.yml up -d
```

**Flaky Tests**

```bash
# Re-run flaky tests automatically
pytest --reruns 3 --reruns-delay 1
```

## Maintenance

### Adding New Tests

1. Create test file following naming convention
2. Add fixtures to conftest.py if reusable
3. Update component-specific README if needed
4. Ensure coverage doesn't decrease

### Updating Fixtures

1. Keep fixtures minimal and focused
2. Version large fixture files
3. Document fixture purpose and structure
4. Clean up outdated fixtures quarterly
