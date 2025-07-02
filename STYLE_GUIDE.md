# JimBot Python Style Guide

This comprehensive style guide establishes coding standards for the JimBot project, incorporating best practices from PEP 8, Google Python Style Guide, Black formatter, and machine learning conventions. This guide is tailored for a Ray RLlib-based reinforcement learning system with asyncio integration.

## Table of Contents

1. [General Principles](#general-principles)
2. [Code Formatting](#code-formatting)
3. [Naming Conventions](#naming-conventions)
4. [Type Hints](#type-hints)
5. [Docstrings](#docstrings)
6. [Project Structure](#project-structure)
7. [Testing Conventions](#testing-conventions)
8. [Async/Await Patterns](#asyncawait-patterns)
9. [Machine Learning Specific Conventions](#machine-learning-specific-conventions)
10. [Ray RLlib Patterns](#ray-rllib-patterns)

## General Principles

### Philosophy
- **Readability counts**: Code is read more often than written
- **Consistency matters**: Follow conventions throughout the codebase
- **Explicit is better than implicit**: Clear code beats clever code
- **Think sequentially**: Use sequential thinking for complex problems

### Core Guidelines
- Follow PEP 8 as the foundation
- Use Black formatter with default settings (88 character line length)
- Maintain at least 80% test coverage
- Document all public APIs

## Code Formatting

### Black Configuration

Configure Black in `pyproject.toml`:

```toml
[tool.black]
line-length = 88
target-version = ['py39']
include = '\.pyi?$'
extend-exclude = '''
/(
  # directories
  \.eggs
  | \.git
  | \.hg
  | \.mypy_cache
  | \.tox
  | \.venv
  | build
  | dist
)/
'''
```

### Import Organization

```python
# Standard library imports
import asyncio
import json
from typing import Dict, List, Optional

# Third-party imports
import numpy as np
import ray
from ray import rllib
from langchain import LLMChain

# Local imports
from jimbot.core import BaseAgent
from jimbot.utils import timer
```

### Line Length and Wrapping
- Maximum line length: 88 characters (Black default)
- Use parentheses for line continuation, not backslashes
- Break before binary operators

```python
# Good
total_reward = (
    base_reward
    + exploration_bonus
    + synergy_multiplier
    - penalty
)

# Bad
total_reward = base_reward + exploration_bonus + \
               synergy_multiplier - penalty
```

## Naming Conventions

### General Rules

| Type | Convention | Example |
|------|------------|---------|
| Variables | snake_case | `card_value`, `joker_synergy` |
| Functions | snake_case | `calculate_score()`, `get_valid_actions()` |
| Classes | PascalCase | `BalatroAgent`, `MemgraphConnector` |
| Constants | UPPER_SNAKE_CASE | `MAX_JOKERS`, `DEFAULT_BATCH_SIZE` |
| Module names | snake_case | `event_aggregator.py`, `ray_trainer.py` |
| Type variables | PascalCase with suffix | `StateT`, `ActionT` |

### Specific Conventions

```python
# Constants at module level
MAX_HAND_SIZE = 8
DEFAULT_LEARNING_RATE = 0.0003
MEMGRAPH_TIMEOUT_MS = 50

# Private functions/methods start with underscore
def _validate_game_state(state: GameState) -> bool:
    """Internal validation logic."""
    pass

# Async functions should be clearly named
async def fetch_strategy_advice(game_state: GameState) -> Strategy:
    """Asynchronously fetches strategy from Claude."""
    pass
```

## Type Hints

### Basic Type Annotations

```python
from typing import Dict, List, Optional, Union, Tuple, TypeVar, Protocol
from typing import cast, overload
import numpy as np
from ray.rllib.utils.typing import TensorType

# Type aliases for clarity
JokerID = str
CardID = str
Score = float
GameState = Dict[str, Union[List[CardID], List[JokerID], int]]

# Generic types
T = TypeVar('T')
StateT = TypeVar('StateT', bound='BaseState')

# Function signatures
def select_action(
    state: GameState,
    valid_actions: List[int],
    exploration_rate: float = 0.1
) -> Tuple[int, float]:
    """Select action with exploration."""
    pass

# Optional parameters
def create_agent(
    config: Dict[str, Any],
    checkpoint_path: Optional[str] = None
) -> 'BalatroAgent':
    """Create agent with optional checkpoint loading."""
    pass
```

### Advanced Patterns

```python
# Protocol for duck typing
class Scoreable(Protocol):
    def calculate_score(self) -> float: ...

# Union types for flexible APIs
ActionSpace = Union[int, List[int], np.ndarray]

# TypedDict for structured data
from typing import TypedDict

class JokerInfo(TypedDict):
    name: str
    rarity: str
    cost: int
    synergies: List[str]

# Numpy/Tensor type hints
def preprocess_observation(
    obs: np.ndarray,
    normalize: bool = True
) -> TensorType:
    """Preprocess observation for neural network."""
    pass
```

## Docstrings

### Google Style (Recommended)

```python
def train_agent(
    env_config: Dict[str, Any],
    num_iterations: int = 1000,
    checkpoint_freq: int = 100
) -> Tuple[BalatroAgent, Dict[str, List[float]]]:
    """Train a Balatro agent using PPO algorithm.
    
    This function initializes a Ray RLlib PPO trainer and runs training
    iterations on the Balatro environment. It handles checkpointing and
    metric collection throughout the training process.
    
    Args:
        env_config: Configuration dict for the Balatro environment.
            Should contain 'seed', 'stake', and 'deck' keys.
        num_iterations: Number of training iterations to run.
        checkpoint_freq: Save checkpoint every N iterations.
    
    Returns:
        A tuple containing:
            - The trained BalatroAgent instance
            - A dict of training metrics with keys:
                'episode_reward_mean': List of mean rewards per iteration
                'episode_len_mean': List of mean episode lengths
                'learning_rate': Learning rate schedule over time
    
    Raises:
        ValueError: If env_config is missing required keys.
        RuntimeError: If Ray cluster is not initialized.
    
    Example:
        >>> config = {'seed': 42, 'stake': 1, 'deck': 'red'}
        >>> agent, metrics = train_agent(config, num_iterations=500)
        >>> print(f"Final reward: {metrics['episode_reward_mean'][-1]}")
    """
    pass
```

### Class Docstrings

```python
class EventAggregator:
    """Aggregates game events for efficient batch processing.
    
    This class collects Balatro game events from the MCP connection and
    batches them for processing by the RL agent. It implements a sliding
    window approach to maintain low latency while reducing overhead.
    
    Attributes:
        batch_window_ms: Time window for collecting events (default: 100ms).
        event_queue: Async queue for incoming events.
        metrics_collector: QuestDB client for performance metrics.
    
    Note:
        This class is designed for single-producer, single-consumer use.
        For multi-threaded scenarios, use EventAggregatorMT instead.
    """
    
    def __init__(self, batch_window_ms: int = 100):
        """Initialize the event aggregator.
        
        Args:
            batch_window_ms: Milliseconds to wait before processing batch.
        """
        self.batch_window_ms = batch_window_ms
        self.event_queue: asyncio.Queue = asyncio.Queue()
```

## Project Structure

### Recommended Layout

```
jimbot/
├── __init__.py
├── core/               # Core game logic and interfaces
│   ├── __init__.py
│   ├── agent.py       # Base agent classes
│   ├── environment.py # Balatro environment wrapper
│   └── types.py       # Type definitions and protocols
├── mcp/               # MCP communication layer
│   ├── __init__.py
│   ├── server.py      # WebSocket server
│   ├── aggregator.py  # Event aggregation
│   └── protocol.py    # Protocol definitions
├── memgraph/          # Knowledge graph integration
│   ├── __init__.py
│   ├── connector.py   # Memgraph client wrapper
│   ├── queries.py     # Cypher query templates
│   └── schemas.py     # Graph schema definitions
├── training/          # Ray RLlib training
│   ├── __init__.py
│   ├── config.py      # Training configurations
│   ├── models.py      # Neural network architectures
│   └── trainer.py     # Training orchestration
├── llm/               # LLM integration
│   ├── __init__.py
│   ├── claude.py      # Claude API wrapper
│   ├── strategies.py  # Strategy extraction
│   └── prompts.py     # Prompt templates
├── utils/             # Shared utilities
│   ├── __init__.py
│   ├── logging.py     # Logging configuration
│   ├── metrics.py     # Metrics collection
│   └── timers.py      # Performance timing
└── tests/             # Test suite
    ├── conftest.py    # Pytest fixtures
    ├── unit/          # Unit tests
    ├── integration/   # Integration tests
    └── performance/   # Performance benchmarks
```

### Module Organization Principles

1. **Single Responsibility**: Each module should have one clear purpose
2. **Minimal Dependencies**: Reduce coupling between modules
3. **Clear Interfaces**: Define protocols/ABCs for module boundaries
4. **Testability**: Design modules to be easily testable in isolation

## Testing Conventions

### Pytest Configuration

```toml
# pyproject.toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py", "*_test.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = [
    "--strict-markers",
    "--verbose",
    "--cov=jimbot",
    "--cov-report=term-missing",
    "--cov-fail-under=80",
]
markers = [
    "slow: marks tests as slow (deselect with '-m \"not slow\"')",
    "integration: marks tests as integration tests",
    "requires_gpu: marks tests that require GPU",
]
```

### Test Structure

```python
import pytest
from unittest.mock import Mock, patch
import numpy as np

from jimbot.core.agent import BalatroAgent
from jimbot.core.types import GameState


class TestBalatroAgent:
    """Test suite for BalatroAgent class."""
    
    @pytest.fixture
    def mock_game_state(self) -> GameState:
        """Create a mock game state for testing."""
        return {
            "hand": ["Ah", "Kh", "Qh", "Jh", "10h"],
            "jokers": ["blueprint", "brainstorm"],
            "money": 25,
            "round": 3,
        }
    
    @pytest.fixture
    def agent(self) -> BalatroAgent:
        """Create agent instance with test configuration."""
        config = {"learning_rate": 0.001, "gamma": 0.99}
        return BalatroAgent(config)
    
    def test_action_selection_deterministic(
        self, agent: BalatroAgent, mock_game_state: GameState
    ):
        """Test that action selection is deterministic with no exploration."""
        agent.set_exploration(0.0)
        
        actions = [agent.select_action(mock_game_state) for _ in range(10)]
        
        # All actions should be identical
        assert all(a == actions[0] for a in actions)
    
    @pytest.mark.slow
    @pytest.mark.parametrize("num_episodes", [10, 100, 1000])
    def test_training_convergence(self, agent: BalatroAgent, num_episodes: int):
        """Test that agent improves over training episodes."""
        initial_performance = agent.evaluate()
        
        agent.train(num_episodes=num_episodes)
        
        final_performance = agent.evaluate()
        assert final_performance > initial_performance
```

### Testing Best Practices

1. **Arrange-Act-Assert**: Structure tests clearly
2. **One assertion per test**: Keep tests focused
3. **Use fixtures**: Share setup code efficiently
4. **Mock external dependencies**: Isolate units under test
5. **Parametrize tests**: Cover edge cases systematically

## Async/Await Patterns

### Basic Async Patterns

```python
import asyncio
from typing import List, Optional
import aiohttp

class MCPClient:
    """Async client for MCP communication."""
    
    def __init__(self, url: str, timeout: float = 5.0):
        self.url = url
        self.timeout = timeout
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout))
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    async def send_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Send event to MCP server."""
        if not self.session:
            raise RuntimeError("Client not initialized. Use async with.")
        
        async with self.session.post(f"{self.url}/event", json=event) as resp:
            return await resp.json()
    
    async def batch_send_events(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Send multiple events concurrently."""
        tasks = [self.send_event(event) for event in events]
        return await asyncio.gather(*tasks, return_exceptions=True)
```

### Event Aggregation Pattern

```python
class EventAggregator:
    """Aggregates events with time-based batching."""
    
    def __init__(self, batch_window_ms: int = 100, max_batch_size: int = 1000):
        self.batch_window_ms = batch_window_ms
        self.max_batch_size = max_batch_size
        self.event_queue: asyncio.Queue = asyncio.Queue()
        self._running = False
    
    async def add_event(self, event: Dict[str, Any]) -> None:
        """Add event to queue for processing."""
        await self.event_queue.put(event)
    
    async def process_batch(self) -> List[Dict[str, Any]]:
        """Collect and process a batch of events."""
        events = []
        deadline = asyncio.get_event_loop().time() + (self.batch_window_ms / 1000)
        
        while len(events) < self.max_batch_size:
            timeout = deadline - asyncio.get_event_loop().time()
            if timeout <= 0:
                break
                
            try:
                event = await asyncio.wait_for(
                    self.event_queue.get(), 
                    timeout=timeout
                )
                events.append(event)
            except asyncio.TimeoutError:
                break
        
        return self._aggregate_events(events)
    
    def _aggregate_events(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Aggregate events by type and timestamp."""
        # Implementation details...
        pass
```

## Machine Learning Specific Conventions

### Data Pipeline Patterns

```python
import numpy as np
from typing import Iterator, Tuple
from ray.data import Dataset

class BalatroDataPipeline:
    """Data pipeline for preprocessing game states."""
    
    @staticmethod
    def preprocess_observation(obs: np.ndarray) -> np.ndarray:
        """Normalize and augment observation.
        
        Args:
            obs: Raw observation array of shape (N, 52 + num_jokers).
        
        Returns:
            Processed observation of shape (N, feature_dim).
        """
        # Normalize card values to [0, 1]
        obs = obs.astype(np.float32)
        obs[:, :52] /= 13.0  # Card ranks
        
        # One-hot encode suits
        # Add positional embeddings
        # etc...
        
        return obs
    
    @staticmethod
    def create_training_dataset(
        replay_buffer: List[Tuple[GameState, int, float, GameState]],
        batch_size: int = 32
    ) -> Iterator[Dict[str, np.ndarray]]:
        """Create batched dataset from replay buffer.
        
        Yields:
            Batches with keys: 'obs', 'actions', 'rewards', 'next_obs'.
        """
        # Implementation...
        pass
```

### Model Architecture Patterns

```python
import torch
import torch.nn as nn
from ray.rllib.models.torch.torch_modelv2 import TorchModelV2

class BalatroNet(TorchModelV2, nn.Module):
    """Neural network for Balatro agent."""
    
    def __init__(self, obs_space, action_space, num_outputs, model_config, name):
        TorchModelV2.__init__(self, obs_space, action_space, num_outputs, model_config, name)
        nn.Module.__init__(self)
        
        # Configuration
        hidden_dim = model_config.get("hidden_dim", 512)
        num_layers = model_config.get("num_layers", 3)
        
        # Build encoder
        self.encoder = self._build_encoder(obs_space.shape[0], hidden_dim)
        
        # Build policy head
        self.policy_head = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, num_outputs)
        )
        
        # Build value head
        self.value_head = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, 1)
        )
        
        self._features = None
    
    def forward(self, input_dict, state, seq_lens):
        """Forward pass through the network."""
        obs = input_dict["obs"].float()
        self._features = self.encoder(obs)
        logits = self.policy_head(self._features)
        self._value = self.value_head(self._features).squeeze(1)
        return logits, state
    
    def value_function(self):
        """Return value function output."""
        return self._value
```

## Ray RLlib Patterns

### Configuration Best Practices

```python
from ray.rllib.algorithms.ppo import PPOConfig

def create_ppo_config(
    num_workers: int = 2,
    num_gpus: int = 1,
    framework: str = "torch"
) -> PPOConfig:
    """Create PPO configuration for Balatro training.
    
    Args:
        num_workers: Number of parallel workers for sampling.
        num_gpus: Number of GPUs to use for training.
        framework: Deep learning framework ('torch' or 'tf2').
    
    Returns:
        Configured PPOConfig instance.
    """
    config = (
        PPOConfig()
        .environment(
            env="BalatroEnv-v0",
            env_config={
                "stake": 1,
                "seed": None,  # Random seed
                "enable_cheats": False,
            }
        )
        .framework(framework)
        .resources(
            num_gpus=num_gpus,
            num_cpus_for_driver=1,
        )
        .rollouts(
            num_rollout_workers=num_workers,
            rollout_fragment_length=200,
            batch_mode="truncate_episodes",
        )
        .training(
            lr=3e-4,
            train_batch_size=4000,
            sgd_minibatch_size=128,
            num_sgd_iter=30,
            model={
                "custom_model": "BalatroNet",
                "custom_model_config": {
                    "hidden_dim": 512,
                    "num_layers": 3,
                },
            },
        )
        .evaluation(
            evaluation_interval=10,
            evaluation_duration=10,
            evaluation_config={
                "explore": False,
                "env_config": {"enable_cheats": False},
            },
        )
    )
    
    return config
```

### Custom Callbacks

```python
from ray.rllib.algorithms.callbacks import DefaultCallbacks
from ray.rllib.env.episode_v2 import EpisodeV2
from typing import Dict, Optional

class BalatroCallbacks(DefaultCallbacks):
    """Custom callbacks for Balatro training."""
    
    def on_episode_start(
        self,
        *,
        worker: "RolloutWorker",
        base_env: "BaseEnv",
        episode: EpisodeV2,
        env_index: Optional[int] = None,
        **kwargs
    ) -> None:
        """Initialize episode-specific metrics."""
        episode.user_data["jokers_collected"] = []
        episode.user_data["hands_played"] = 0
        episode.user_data["highest_score"] = 0
    
    def on_episode_step(
        self,
        *,
        worker: "RolloutWorker",
        base_env: "BaseEnv",
        episode: EpisodeV2,
        env_index: Optional[int] = None,
        **kwargs
    ) -> None:
        """Track step-level metrics."""
        info = episode.last_info_for()
        
        if "hand_score" in info:
            episode.user_data["hands_played"] += 1
            episode.user_data["highest_score"] = max(
                episode.user_data["highest_score"],
                info["hand_score"]
            )
    
    def on_episode_end(
        self,
        *,
        worker: "RolloutWorker",
        base_env: "BaseEnv",
        episode: EpisodeV2,
        env_index: Optional[int] = None,
        **kwargs
    ) -> None:
        """Aggregate episode metrics."""
        episode.custom_metrics["hands_played"] = episode.user_data["hands_played"]
        episode.custom_metrics["highest_score"] = episode.user_data["highest_score"]
        episode.custom_metrics["jokers_collected"] = len(episode.user_data["jokers_collected"])
```

## Conclusion

This style guide provides a foundation for consistent, maintainable code in the JimBot project. Key takeaways:

1. **Use Black**: Automate formatting to avoid debates
2. **Type everything**: Use type hints for clarity and tooling support
3. **Document thoroughly**: Write comprehensive docstrings
4. **Test rigorously**: Maintain high test coverage
5. **Structure thoughtfully**: Organize code for clarity and reusability
6. **Embrace async**: Use async/await for concurrent operations
7. **Follow conventions**: Consistency beats personal preferences

Remember: these are guidelines, not rigid rules. Use judgment when exceptions make sense, but document why you're deviating from the standard.