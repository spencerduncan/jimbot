"""
Shared pytest configuration and fixtures for JimBot tests.

This file is automatically loaded by pytest and provides common fixtures
and configuration used across all test modules.
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import AsyncMock, Mock

import pytest
from faker import Faker

# Add project root to Python path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Initialize Faker for test data generation
fake = Faker()


# ===== Pytest Configuration =====


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line(
        "markers", "performance: marks tests as performance benchmarks"
    )
    config.addinivalue_line(
        "markers", "requires_docker: marks tests that require Docker"
    )
    config.addinivalue_line("markers", "requires_gpu: marks tests that require GPU")


# ===== Event Loop Configuration =====


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ===== Game State Fixtures =====


@pytest.fixture
def sample_joker():
    """Create a sample joker for testing."""
    return {
        "id": fake.uuid4(),
        "name": "Joker",
        "rarity": "Common",
        "cost": 5,
        "effect": "+4 Mult",
        "description": "Adds 4 to multiplier",
    }


@pytest.fixture
def sample_card():
    """Create a sample playing card."""
    return {
        "suit": fake.random_element(["Hearts", "Diamonds", "Clubs", "Spades"]),
        "rank": fake.random_element(
            ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]
        ),
        "enhancement": None,
        "edition": None,
        "seal": None,
    }


@pytest.fixture
def sample_game_state():
    """Create a complete game state for testing."""
    return {
        "ante": fake.random_int(1, 8),
        "round": fake.random_int(1, 3),
        "money": fake.random_int(0, 100),
        "hands_remaining": fake.random_int(0, 4),
        "discards_remaining": fake.random_int(0, 3),
        "jokers": [sample_joker() for _ in range(fake.random_int(0, 5))],
        "hand": [sample_card() for _ in range(8)],
        "deck_size": fake.random_int(30, 52),
        "current_blind": {
            "name": fake.random_element(["Small Blind", "Big Blind", "Boss"]),
            "chips_required": fake.random_int(100, 10000),
            "mult_requirement": fake.random_int(1, 50),
        },
        "shop": {"cards": [], "vouchers": [], "packs": []},
    }


@pytest.fixture
def sample_mcp_event():
    """Create a sample MCP event."""
    return {
        "type": fake.random_element(["game_state", "action", "result"]),
        "timestamp": fake.unix_time(),
        "data": {"event_id": fake.uuid4(), "game_id": fake.uuid4(), "payload": {}},
    }


# ===== Mock Service Fixtures =====


@pytest.fixture
def mock_memgraph_client():
    """Create a mock Memgraph client."""
    client = Mock()
    client.execute_query = Mock(return_value=[])
    client.get_joker_synergies = Mock(return_value=[])
    client.store_game_state = Mock(return_value={"success": True})
    return client


@pytest.fixture
def mock_ray_trainer():
    """Create a mock Ray trainer."""
    trainer = Mock()
    trainer.train = Mock(return_value={"episode_reward_mean": 100})
    trainer.compute_single_action = Mock(return_value=0)
    trainer.save = Mock(return_value="/tmp/checkpoint")
    return trainer


@pytest.fixture
def mock_claude_client():
    """Create a mock Claude/LangChain client."""
    client = AsyncMock()
    client.get_strategic_advice = AsyncMock(
        return_value="Focus on flush builds with current joker setup"
    )
    client.analyze_failure = AsyncMock(
        return_value="Consider more defensive play in early antes"
    )
    return client


@pytest.fixture
def mock_event_bus():
    """Create a mock event bus for testing."""
    bus = AsyncMock()
    bus.publish = AsyncMock()
    bus.subscribe = AsyncMock()
    bus.unsubscribe = AsyncMock()
    return bus


# ===== WebSocket Fixtures =====


@pytest.fixture
def mock_websocket():
    """Create a mock WebSocket connection."""
    ws = AsyncMock()
    ws.send = AsyncMock()
    ws.recv = AsyncMock(return_value=json.dumps({"type": "ping"}))
    ws.close = AsyncMock()
    return ws


# ===== File System Fixtures =====


@pytest.fixture
def temp_checkpoint_dir(tmp_path):
    """Create a temporary directory for checkpoints."""
    checkpoint_dir = tmp_path / "checkpoints"
    checkpoint_dir.mkdir()
    return checkpoint_dir


@pytest.fixture
def temp_config_file(tmp_path):
    """Create a temporary config file."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        """
    mcp:
      host: localhost
      port: 8765
      batch_window_ms: 100
    
    memgraph:
      host: localhost
      port: 7687
    
    ray:
      num_workers: 2
      batch_size: 32
    
    claude:
      api_key: test_key
      model: claude-3-opus
      hourly_limit: 100
    """
    )
    return config_file


# ===== Database Fixtures =====


@pytest.fixture
def memgraph_test_data():
    """Provide test data for Memgraph."""
    return {
        "jokers": [
            {"name": "Joker", "rarity": "Common", "cost": 5},
            {"name": "Wrathful Joker", "rarity": "Rare", "cost": 8},
            {"name": "Baseball Card", "rarity": "Uncommon", "cost": 6},
        ],
        "synergies": [
            {"joker1": "Joker", "joker2": "Baseball Card", "strength": 0.8},
            {"joker1": "Wrathful Joker", "joker2": "Joker", "strength": 0.6},
        ],
    }


# ===== Performance Testing Fixtures =====


@pytest.fixture
def performance_timer():
    """Simple timer for performance tests."""
    import time

    class Timer:
        def __init__(self):
            self.start_time = None
            self.elapsed = None

        def __enter__(self):
            self.start_time = time.perf_counter()
            return self

        def __exit__(self, *args):
            self.elapsed = time.perf_counter() - self.start_time

    return Timer


# ===== Async Utilities =====


@pytest.fixture
def async_timeout():
    """Provide configurable timeout for async tests."""
    return 5.0  # seconds


# ===== Environment Fixtures =====


@pytest.fixture(autouse=True)
def reset_environment(monkeypatch):
    """Reset environment variables for each test."""
    # Clear any existing JimBot environment variables
    for key in list(os.environ.keys()):
        if key.startswith("JIMBOT_"):
            monkeypatch.delenv(key, raising=False)

    # Set test environment
    monkeypatch.setenv("JIMBOT_ENV", "test")
    monkeypatch.setenv("JIMBOT_LOG_LEVEL", "DEBUG")


# ===== Docker Fixtures =====


@pytest.fixture(scope="session")
def docker_services():
    """Ensure Docker services are available for integration tests."""
    # This would be extended with actual Docker management
    # For now, it's a placeholder that can be expanded
    return {
        "memgraph": "localhost:7687",
        "questdb": "localhost:9000",
        "eventstore": "localhost:2113",
    }


# ===== Logging Fixtures =====


@pytest.fixture
def capture_logs(caplog):
    """Capture and provide access to log messages."""
    import logging

    caplog.set_level(logging.DEBUG)
    return caplog


# ===== Test Data Generators =====


@pytest.fixture
def generate_game_history():
    """Generate a sequence of game states for testing."""

    def _generate(num_states: int = 10) -> List[Dict[str, Any]]:
        states = []
        for i in range(num_states):
            state = sample_game_state()
            state["sequence_number"] = i
            state["timestamp"] = fake.unix_time() + i * 60
            states.append(state)
        return states

    return _generate


@pytest.fixture
def generate_training_batch():
    """Generate a batch of training data."""

    def _generate(batch_size: int = 32) -> Dict[str, Any]:
        return {
            "observations": [
                [fake.random.random() for _ in range(128)] for _ in range(batch_size)
            ],
            "actions": [fake.random_int(0, 10) for _ in range(batch_size)],
            "rewards": [fake.random.random() * 100 for _ in range(batch_size)],
            "dones": [fake.boolean() for _ in range(batch_size)],
        }

    return _generate
