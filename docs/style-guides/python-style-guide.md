# Python Style Guide for JimBot

This style guide defines the Python coding conventions for the JimBot project, a sequential learning system for mastering Balatro using ML and AI integration.

## Table of Contents
1. [Foundation Standards](#foundation-standards)
2. [Code Formatting](#code-formatting)
3. [Naming Conventions](#naming-conventions)
4. [Type Hints](#type-hints)
5. [Documentation](#documentation)
6. [Project Structure](#project-structure)
7. [Async Patterns](#async-patterns)
8. [Testing Conventions](#testing-conventions)
9. [Ray RLlib Patterns](#ray-rllib-patterns)
10. [Error Handling](#error-handling)

## Foundation Standards

### Core Principles
- **PEP 8** as the base standard with practical adaptations
- **Black** formatter for consistent code style
- **Type hints** for all public APIs and complex functions
- **Async-first** for I/O operations

### Tools Configuration
```toml
# pyproject.toml
[tool.black]
line-length = 88
target-version = ['py39']

[tool.mypy]
python_version = "3.9"
strict = true
warn_return_any = true
warn_unused_configs = true

[tool.pytest]
minversion = "6.0"
addopts = "-ra -q --strict-markers"
testpaths = ["tests"]
```

## Code Formatting

### Black Formatter
- Use Black with default settings (88-character line length)
- Run before every commit: `black .`
- No manual formatting debates

### Import Organization
```python
# Standard library imports
import asyncio
import json
from typing import Dict, List, Optional

# Third-party imports
import numpy as np
import ray
from langchain import LLMChain

# Local imports
from jimbot.core.types import GameState, JokerID
from jimbot.mcp.aggregator import EventAggregator
```

## Naming Conventions

### General Rules
- **Classes**: `UpperCamelCase`
- **Functions/Variables**: `snake_case`
- **Constants**: `UPPER_SNAKE_CASE`
- **Private**: Leading underscore `_private_method`
- **Type Aliases**: `UpperCamelCase`

### Domain-Specific Names
```python
# Type aliases for domain concepts
JokerID = str
CardValue = int
Multiplier = float
GameStateID = str

# Domain entities
class Joker:
    """Represents a Balatro joker with its properties."""
    
class SynergyGraph:
    """Knowledge graph for joker synergies."""
    
# Event types
class MCPGameEvent:
    """MCP protocol game event."""
```

## Type Hints

### Basic Usage
```python
from typing import Dict, List, Optional, Union, TypedDict, Protocol

def calculate_synergy(
    joker1: JokerID,
    joker2: JokerID,
    game_state: GameState
) -> Optional[float]:
    """Calculate synergy multiplier between two jokers."""
    ...

# For complex return types
def get_strategy_recommendation(
    state: GameState,
) -> tuple[str, float, Dict[str, Any]]:
    """Returns (action, confidence, metadata)."""
    ...
```

### ML-Specific Types
```python
from typing import TypeVar, Generic
import numpy as np
import torch
from numpy.typing import NDArray

# Type variables for tensors
TensorType = TypeVar("TensorType", np.ndarray, torch.Tensor)

class ModelOutput(TypedDict):
    """Typed dictionary for model outputs."""
    action: int
    value: float
    policy_logits: NDArray[np.float32]
    
def preprocess_state(
    raw_state: Dict[str, Any]
) -> NDArray[np.float32]:
    """Convert game state to model input tensor."""
    ...
```

## Documentation

### Google-Style Docstrings
```python
def aggregate_events(
    events: List[MCPGameEvent],
    window_ms: int = 100
) -> AggregatedGameState:
    """Aggregate multiple game events within a time window.
    
    Combines multiple MCP events into a single state update
    for efficient processing by the RL model.
    
    Args:
        events: List of game events from MCP
        window_ms: Aggregation window in milliseconds
        
    Returns:
        Aggregated game state ready for model input
        
    Raises:
        ValueError: If events list is empty
        AggregationError: If events cannot be combined
    """
    ...
```

### Class Documentation
```python
class EventAggregator:
    """Aggregates MCP events for batch processing.
    
    Implements a sliding window aggregator that batches
    game events to reduce model inference overhead while
    maintaining real-time responsiveness.
    
    Attributes:
        window_ms: Aggregation window in milliseconds
        event_queue: Async queue for incoming events
        
    Example:
        >>> aggregator = EventAggregator(window_ms=100)
        >>> await aggregator.start()
        >>> state = await aggregator.get_next_batch()
    """
```

## Project Structure

```
jimbot/
├── __init__.py
├── core/              # Core game logic and types
│   ├── __init__.py
│   ├── types.py       # Type definitions
│   ├── game_state.py  # Game state management
│   └── constants.py   # Game constants
├── mcp/               # MCP communication layer
│   ├── __init__.py
│   ├── server.py      # MCP server implementation
│   ├── aggregator.py  # Event aggregation
│   └── protocol.py    # Protocol definitions
├── memgraph/          # Knowledge graph integration
│   ├── __init__.py
│   ├── client.py      # Memgraph client
│   ├── queries.py     # Cypher queries
│   └── schemas.py     # Graph schemas
├── training/          # Ray RLlib training
│   ├── __init__.py
│   ├── config.py      # Training configuration
│   ├── models.py      # Neural network models
│   └── callbacks.py   # Training callbacks
├── llm/               # LangChain/Claude integration
│   ├── __init__.py
│   ├── claude_strategy.py
│   └── rate_limiter.py
└── utils/             # Shared utilities
    ├── __init__.py
    ├── logging.py
    └── metrics.py

tests/
├── unit/              # Unit tests
├── integration/       # Integration tests
└── performance/       # Performance benchmarks
```

## Async Patterns

### Basic Async/Await
```python
async def fetch_game_state(game_id: str) -> GameState:
    """Fetch current game state asynchronously."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"/api/games/{game_id}") as resp:
                data = await resp.json()
                return GameState.from_dict(data)
    except aiohttp.ClientError as e:
        logger.error(f"Failed to fetch game state: {e}")
        raise
```

### Event Aggregation Pattern
```python
class EventAggregator:
    def __init__(self, batch_window_ms: int = 100):
        self.batch_window = batch_window_ms / 1000.0
        self.event_queue: asyncio.Queue[MCPGameEvent] = asyncio.Queue()
        
    async def process_batch(self) -> List[MCPGameEvent]:
        """Process a batch of events within the time window."""
        events = []
        deadline = asyncio.get_event_loop().time() + self.batch_window
        
        while True:
            try:
                timeout = deadline - asyncio.get_event_loop().time()
                if timeout <= 0:
                    break
                    
                event = await asyncio.wait_for(
                    self.event_queue.get(),
                    timeout=timeout
                )
                events.append(event)
            except asyncio.TimeoutError:
                break
                
        return events
```

### Concurrent Operations
```python
async def parallel_strategy_check(
    jokers: List[JokerID],
    game_state: GameState
) -> List[StrategyResult]:
    """Check multiple strategies in parallel."""
    tasks = [
        check_strategy(joker, game_state)
        for joker in jokers
    ]
    return await asyncio.gather(*tasks)
```

## Testing Conventions

### Test Organization
```python
# tests/unit/test_event_aggregator.py
import pytest
from jimbot.mcp.aggregator import EventAggregator

class TestEventAggregator:
    """Test suite for EventAggregator."""
    
    @pytest.fixture
    def aggregator(self):
        """Create aggregator instance for testing."""
        return EventAggregator(batch_window_ms=50)
        
    @pytest.mark.asyncio
    async def test_batch_processing(self, aggregator):
        """Test that events are batched within window."""
        # Arrange
        events = [create_test_event(i) for i in range(5)]
        
        # Act
        for event in events:
            await aggregator.event_queue.put(event)
        batch = await aggregator.process_batch()
        
        # Assert
        assert len(batch) == 5
        assert all(e in events for e in batch)
```

### Fixtures and Mocking
```python
@pytest.fixture
async def mock_memgraph_client():
    """Mock Memgraph client for testing."""
    with patch("jimbot.memgraph.client.MemgraphClient") as mock:
        mock.query.return_value = {"synergy": 2.5}
        yield mock
        
@pytest.fixture
def game_state_factory():
    """Factory for creating test game states."""
    def _create_state(**kwargs):
        defaults = {
            "money": 100,
            "ante": 1,
            "hands_remaining": 4,
            "jokers": []
        }
        defaults.update(kwargs)
        return GameState(**defaults)
    return _create_state
```

## Ray RLlib Patterns

### Model Configuration
```python
from ray.rllib.models.torch.torch_modelv2 import TorchModelV2

class BalatroNet(TorchModelV2):
    """Custom neural network for Balatro RL agent."""
    
    def __init__(self, obs_space, action_space, num_outputs, 
                 model_config, name):
        super().__init__(obs_space, action_space, num_outputs,
                        model_config, name)
        
        # Extract custom config
        hidden_size = model_config["custom_model_config"]["hidden_size"]
        memgraph_dim = model_config["custom_model_config"]["memgraph_embedding_dim"]
        
        # Build layers
        self.encoder = nn.Sequential(
            nn.Linear(obs_space.shape[0], hidden_size),
            nn.ReLU(),
            nn.Linear(hidden_size, hidden_size),
            nn.ReLU()
        )
        
    def forward(self, input_dict, state, seq_lens):
        """Forward pass with knowledge graph embeddings."""
        obs = input_dict["obs"]
        features = self.encoder(obs)
        return self.policy_head(features), state
```

### Training Configuration
```python
PPO_CONFIG = {
    "framework": "torch",
    "num_workers": 2,
    "num_gpus": 1,
    "rollout_fragment_length": 200,
    "train_batch_size": 4000,
    "sgd_minibatch_size": 128,
    "num_sgd_iter": 30,
    "model": {
        "custom_model": "BalatroNet",
        "custom_model_config": {
            "hidden_size": 512,
            "memgraph_embedding_dim": 128,
        }
    },
    "callbacks": "BalatroCallbacks",
    "env_config": {
        "memgraph_client": memgraph_client,
        "event_aggregator": aggregator,
    }
}
```

### Custom Callbacks
```python
from ray.rllib.algorithms.callbacks import DefaultCallbacks

class BalatroCallbacks(DefaultCallbacks):
    """Custom callbacks for training metrics."""
    
    def on_episode_end(self, *, episode, **kwargs):
        """Log episode metrics."""
        episode.custom_metrics["final_ante"] = episode.last_info_for()["ante"]
        episode.custom_metrics["total_money"] = episode.last_info_for()["money"]
        episode.custom_metrics["joker_synergy"] = episode.last_info_for()["synergy_score"]
```

## Error Handling

### Custom Exceptions
```python
class JimBotError(Exception):
    """Base exception for JimBot errors."""
    
class AggregationError(JimBotError):
    """Raised when event aggregation fails."""
    
class MemgraphQueryError(JimBotError):
    """Raised when Memgraph query fails."""
    
class RateLimitError(JimBotError):
    """Raised when API rate limit is exceeded."""
```

### Error Handling Pattern
```python
async def safe_claude_query(
    prompt: str,
    rate_limiter: RateLimiter
) -> Optional[str]:
    """Query Claude with rate limiting and fallback."""
    try:
        if not rate_limiter.can_request():
            logger.warning("Rate limit reached, using cached response")
            return get_cached_response(prompt)
            
        response = await claude_client.query(prompt)
        rate_limiter.record_request()
        return response
        
    except RateLimitError:
        logger.error("Claude rate limit exceeded")
        return get_cached_response(prompt)
        
    except Exception as e:
        logger.error(f"Unexpected error querying Claude: {e}")
        return None
```

### Context Managers
```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def memgraph_transaction():
    """Context manager for Memgraph transactions."""
    tx = await memgraph_client.begin_transaction()
    try:
        yield tx
        await tx.commit()
    except Exception:
        await tx.rollback()
        raise
```

## Performance Considerations

### Memory Management
```python
# Use generators for large datasets
def process_game_history(history_file: Path) -> Iterator[GameState]:
    """Process game history without loading all into memory."""
    with open(history_file) as f:
        for line in f:
            yield GameState.from_json(line)
            
# Pre-allocate arrays for known sizes
def create_observation_tensor(state: GameState) -> np.ndarray:
    """Create observation tensor with pre-allocation."""
    obs = np.zeros(OBSERVATION_SIZE, dtype=np.float32)
    obs[:4] = [state.money, state.ante, state.hands, state.discards]
    return obs
```

### Caching Patterns
```python
from functools import lru_cache

@lru_cache(maxsize=1000)
def get_joker_synergy(joker1: JokerID, joker2: JokerID) -> float:
    """Cache joker synergy calculations."""
    return calculate_synergy(joker1, joker2)
    
# Time-based cache for Claude responses
class TimedCache:
    def __init__(self, ttl_seconds: int = 300):
        self.cache: Dict[str, tuple[float, Any]] = {}
        self.ttl = ttl_seconds
        
    def get(self, key: str) -> Optional[Any]:
        """Get cached value if not expired."""
        if key in self.cache:
            timestamp, value = self.cache[key]
            if time.time() - timestamp < self.ttl:
                return value
        return None
```

## Code Review Checklist

- [ ] Code is formatted with Black
- [ ] Type hints for all public functions
- [ ] Google-style docstrings for modules, classes, and functions
- [ ] No bare `except:` clauses
- [ ] Async functions properly handle exceptions
- [ ] Tests cover happy path and edge cases
- [ ] Performance-critical sections are optimized
- [ ] No hardcoded values (use constants or config)
- [ ] Logging at appropriate levels
- [ ] No secrets or credentials in code