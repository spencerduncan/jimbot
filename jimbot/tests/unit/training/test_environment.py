"""
Unit tests for the Ray/RLlib training environment.

Tests the Balatro gym environment, reward calculations, and action spaces.
"""

import numpy as np
import pytest

from jimbot.training.environment import BalatroEnv, BalatroEnvConfig
from jimbot.training.rewards import RewardCalculator
from jimbot.training.spaces import ActionSpace, ObservationSpace


class TestBalatroEnvironment:
    """Test the Balatro gym environment."""

    @pytest.fixture
    def env_config(self):
        """Create environment configuration."""
        return BalatroEnvConfig(
            max_ante=8,
            starting_money=10,
            starting_hands=4,
            starting_discards=3,
            use_knowledge_graph=False,  # Unit test without external deps
        )

    @pytest.fixture
    def env(self, env_config):
        """Create a Balatro environment."""
        return BalatroEnv(env_config)

    def test_environment_initialization(self, env):
        """Test environment initializes correctly."""
        assert env.ante == 1
        assert env.money == 10
        assert env.hands_remaining == 4
        assert env.discards_remaining == 3
        assert len(env.jokers) == 0

    def test_reset_returns_valid_observation(self, env):
        """Test reset returns properly formatted observation."""
        obs = env.reset()

        assert isinstance(obs, np.ndarray)
        assert obs.shape == env.observation_space.shape
        assert np.all(obs >= env.observation_space.low)
        assert np.all(obs <= env.observation_space.high)

    def test_step_with_play_hand_action(self, env):
        """Test executing a play hand action."""
        env.reset()

        # Action: play hand (simplified for unit test)
        action = env.action_space.encode_action("play_hand", [0, 1, 2, 3, 4])

        obs, reward, done, info = env.step(action)

        assert isinstance(obs, np.ndarray)
        assert isinstance(reward, float)
        assert isinstance(done, bool)
        assert "chips_earned" in info

    def test_step_with_discard_action(self, env):
        """Test executing a discard action."""
        env.reset()

        # Action: discard cards
        action = env.action_space.encode_action("discard", [7, 6])

        obs, reward, done, info = env.step(action)

        assert env.discards_remaining == 2  # One discard used
        assert reward < 0  # Small negative reward for using resources

    def test_invalid_action_handling(self, env):
        """Test handling of invalid actions."""
        env.reset()
        env.hands_remaining = 0  # No hands left

        # Try to play hand when none remaining
        action = env.action_space.encode_action("play_hand", [0, 1, 2, 3, 4])

        obs, reward, done, info = env.step(action)

        assert reward < -10  # Large negative reward for invalid action
        assert info["invalid_action"] is True

    def test_episode_termination_conditions(self, env):
        """Test various episode termination conditions."""
        # Test losing all money
        env.reset()
        env.money = 0
        _, _, done, info = env.step(0)
        assert done
        assert info["termination_reason"] == "bankrupt"

        # Test completing max ante
        env.reset()
        env.ante = 8
        env.current_blind_defeated = True
        _, _, done, info = env.step(0)
        assert done
        assert info["termination_reason"] == "victory"

    def test_shop_action_processing(self, env):
        """Test shop purchase actions."""
        env.reset()
        env.money = 50
        env.shop_items = [
            {"type": "joker", "name": "Joker", "cost": 5},
            {"type": "voucher", "name": "Blank Voucher", "cost": 10},
        ]

        # Buy joker
        action = env.action_space.encode_action("buy", 0)
        obs, reward, done, info = env.step(action)

        assert env.money == 45
        assert len(env.jokers) == 1
        assert reward > 0  # Positive reward for strategic purchase

    def test_observation_encoding(self, env):
        """Test observation space encoding includes all features."""
        env.reset()
        env.ante = 5
        env.money = 75
        env.jokers = ["Joker", "Baseball Card"]

        obs = env._get_observation()

        # Check key features are encoded
        obs_dict = env.observation_space.decode(obs)
        assert obs_dict["ante"] == 5
        assert obs_dict["money"] == 75
        assert obs_dict["joker_count"] == 2


class TestRewardCalculator:
    """Test reward calculation logic."""

    @pytest.fixture
    def calculator(self):
        """Create a reward calculator."""
        return RewardCalculator()

    def test_calculates_hand_play_reward(self, calculator):
        """Test reward for playing a hand."""
        state = {
            "chips_earned": 500,
            "mult_earned": 10,
            "blind_requirement": 300,
            "hands_remaining": 2,
        }

        reward = calculator.calculate_hand_reward(state)

        assert reward > 0  # Beat the blind
        assert reward > 10  # Significant excess

    def test_calculates_ante_completion_bonus(self, calculator):
        """Test bonus reward for completing antes."""
        # Higher antes give bigger bonuses
        assert calculator.ante_completion_bonus(1) < calculator.ante_completion_bonus(5)
        assert calculator.ante_completion_bonus(8) > 100

    def test_calculates_resource_efficiency_bonus(self, calculator):
        """Test bonus for efficient resource use."""
        state = {
            "hands_remaining": 3,
            "discards_remaining": 2,
            "starting_hands": 4,
            "starting_discards": 3,
        }

        bonus = calculator.resource_efficiency_bonus(state)

        assert bonus > 0  # Used minimal resources

    def test_penalizes_invalid_actions(self, calculator):
        """Test penalties for invalid actions."""
        penalty = calculator.invalid_action_penalty("play_hand_no_hands")

        assert penalty < -10
        assert penalty > -100  # Not too harsh

    def test_calculates_strategic_value(self, calculator):
        """Test evaluation of strategic decisions."""
        # Good synergy purchase
        state = {
            "action": "buy_joker",
            "joker": "Baseball Card",
            "current_jokers": ["Joker", "Scary Face"],
            "synergy_score": 0.8,
        }

        value = calculator.evaluate_strategic_value(state)

        assert value > 0
        assert value < 20  # Reasonable bounds


class TestActionSpace:
    """Test action space encoding and validation."""

    @pytest.fixture
    def action_space(self):
        """Create action space."""
        return ActionSpace()

    def test_encodes_play_hand_action(self, action_space):
        """Test encoding hand selection."""
        cards = [0, 1, 2, 3, 4]  # First 5 cards
        action = action_space.encode_action("play_hand", cards)

        decoded = action_space.decode_action(action)
        assert decoded["type"] == "play_hand"
        assert decoded["cards"] == cards

    def test_encodes_discard_action(self, action_space):
        """Test encoding discard selection."""
        cards = [7, 5, 3]  # Discard 3 cards
        action = action_space.encode_action("discard", cards)

        decoded = action_space.decode_action(action)
        assert decoded["type"] == "discard"
        assert decoded["cards"] == cards

    def test_validates_action_legality(self, action_space):
        """Test action validation against game state."""
        state = {"hands_remaining": 0, "discards_remaining": 2, "hand_size": 8}

        # Can't play hand
        play_action = action_space.encode_action("play_hand", [0, 1, 2, 3, 4])
        assert not action_space.is_legal(play_action, state)

        # Can discard
        discard_action = action_space.encode_action("discard", [0, 1])
        assert action_space.is_legal(discard_action, state)

    def test_masks_illegal_actions(self, action_space):
        """Test generation of action masks."""
        state = {
            "phase": "blind",
            "hands_remaining": 1,
            "discards_remaining": 0,
            "money": 5,
            "shop_items": [{"cost": 10}, {"cost": 3}],  # Too expensive  # Affordable
        }

        mask = action_space.get_legal_action_mask(state)

        assert mask[action_space.PLAY_HAND_START] == 1  # Can play
        assert mask[action_space.DISCARD_START] == 0  # Can't discard
        assert mask[action_space.BUY_START] == 0  # Can't afford first item
        assert mask[action_space.BUY_START + 1] == 1  # Can afford second item


class TestObservationSpace:
    """Test observation space encoding."""

    @pytest.fixture
    def obs_space(self):
        """Create observation space."""
        return ObservationSpace()

    def test_encodes_game_state(self, obs_space, sample_game_state):
        """Test encoding full game state."""
        observation = obs_space.encode(sample_game_state)

        assert isinstance(observation, np.ndarray)
        assert observation.shape == obs_space.shape
        assert np.all(np.isfinite(observation))

    def test_normalizes_values(self, obs_space):
        """Test value normalization."""
        state = {
            "ante": 8,  # Max value
            "money": 1000,  # Very high
            "hands_remaining": 0,  # Min value
        }

        encoded = obs_space.encode(state)

        # Check normalization
        ante_idx = obs_space.get_feature_index("ante")
        money_idx = obs_space.get_feature_index("money")
        hands_idx = obs_space.get_feature_index("hands_remaining")

        assert encoded[ante_idx] == 1.0  # Normalized max
        assert encoded[hands_idx] == 0.0  # Normalized min
        assert 0 < encoded[money_idx] <= 1.0  # Money normalized

    def test_encodes_joker_features(self, obs_space):
        """Test joker encoding in observation."""
        state = {"jokers": ["Joker", "Baseball Card", "DNA"], "joker_slots": 5}

        encoded = obs_space.encode(state)
        joker_section = obs_space.get_joker_encoding(encoded)

        assert np.sum(joker_section) == 3  # Three jokers encoded

    def test_handles_missing_features(self, obs_space):
        """Test graceful handling of incomplete states."""
        minimal_state = {"ante": 1, "money": 10}

        encoded = obs_space.encode(minimal_state)

        assert encoded is not None
        assert not np.any(np.isnan(encoded))
