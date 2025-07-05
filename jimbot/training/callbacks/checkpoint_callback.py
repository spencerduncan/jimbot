"""
Custom callbacks for Balatro training

This module implements callbacks for monitoring training progress,
saving checkpoints, and integrating with external systems.
"""

import json
import os
import time
from typing import Any, Dict, Optional

from ray.rllib.agents.callbacks import DefaultCallbacks
from ray.rllib.env import BaseEnv
from ray.rllib.evaluation import Episode, RolloutWorker
from ray.rllib.policy import Policy
from ray.rllib.utils.typing import PolicyID


class BalatroCallbacks(DefaultCallbacks):
    """
    Custom callbacks for Balatro training

    Handles:
    - Performance monitoring
    - Custom checkpointing logic
    - Integration with monitoring systems
    - Game-specific metrics tracking
    """

    def __init__(self):
        super().__init__()
        self.episode_rewards = []
        self.episode_lengths = []
        self.games_won = 0
        self.games_total = 0
        self.start_time = time.time()
        self.best_reward = -float("inf")
        self.checkpoint_dir = None

    def on_episode_start(
        self,
        *,
        worker: RolloutWorker,
        base_env: BaseEnv,
        policies: Dict[PolicyID, Policy],
        episode: Episode,
        **kwargs,
    ):
        """Called at the start of each episode"""
        # Initialize episode metrics
        episode.user_data["cards_played"] = 0
        episode.user_data["jokers_activated"] = 0
        episode.user_data["rounds_completed"] = 0
        episode.user_data["max_score"] = 0
        episode.user_data["start_time"] = time.time()

    def on_episode_step(
        self,
        *,
        worker: RolloutWorker,
        base_env: BaseEnv,
        policies: Dict[PolicyID, Policy],
        episode: Episode,
        **kwargs,
    ):
        """Called at each step of the episode"""
        # Track game-specific metrics from info
        info = episode.last_info_for()
        if info:
            # Update max score
            current_score = info.get("game_score", 0)
            if current_score > episode.user_data["max_score"]:
                episode.user_data["max_score"] = current_score

            # Track actions
            if info.get("card_played", False):
                episode.user_data["cards_played"] += 1
            if info.get("joker_activated", False):
                episode.user_data["jokers_activated"] += 1
            if info.get("round_completed", False):
                episode.user_data["rounds_completed"] += 1

    def on_episode_end(
        self,
        *,
        worker: RolloutWorker,
        base_env: BaseEnv,
        policies: Dict[PolicyID, Policy],
        episode: Episode,
        **kwargs,
    ):
        """Called at the end of each episode"""
        # Calculate episode duration
        duration = time.time() - episode.user_data["start_time"]

        # Track overall metrics
        self.episode_rewards.append(episode.total_reward)
        self.episode_lengths.append(episode.length)
        self.games_total += 1

        # Check if won (assuming victory gives reward > 100)
        if episode.total_reward > 100:
            self.games_won += 1

        # Add custom metrics to episode
        episode.custom_metrics["cards_played"] = episode.user_data["cards_played"]
        episode.custom_metrics["jokers_activated"] = episode.user_data[
            "jokers_activated"
        ]
        episode.custom_metrics["rounds_completed"] = episode.user_data[
            "rounds_completed"
        ]
        episode.custom_metrics["max_score"] = episode.user_data["max_score"]
        episode.custom_metrics["episode_duration"] = duration
        episode.custom_metrics["win_rate"] = self.games_won / self.games_total
        episode.custom_metrics["games_per_hour"] = self._calculate_games_per_hour()

    def on_train_result(self, *, algorithm, result: dict, **kwargs) -> None:
        """Called after each training iteration"""
        # Calculate performance metrics
        iteration = result.get("training_iteration", 0)
        episode_reward_mean = result.get("episode_reward_mean", 0)
        episodes_total = result.get("episodes_total", 0)
        timesteps_total = result.get("timesteps_total", 0)

        # Save best model
        if episode_reward_mean > self.best_reward:
            self.best_reward = episode_reward_mean

            # Save checkpoint
            checkpoint_dir = algorithm.logdir
            best_checkpoint_path = os.path.join(checkpoint_dir, "best_model")
            algorithm.save(best_checkpoint_path)

            # Save metadata
            metadata = {
                "iteration": iteration,
                "reward": episode_reward_mean,
                "episodes": episodes_total,
                "timesteps": timesteps_total,
                "win_rate": self.games_won / max(self.games_total, 1),
                "timestamp": time.time(),
            }

            with open(f"{best_checkpoint_path}.json", "w") as f:
                json.dump(metadata, f, indent=2)

            print(f"New best model saved with reward: {episode_reward_mean:.2f}")

        # Log performance warning if below target
        games_per_hour = self._calculate_games_per_hour()
        if games_per_hour < 1000 and episodes_total > 100:
            print(f"WARNING: Games/hour ({games_per_hour:.2f}) below target (1000)")

        # Add custom metrics to result
        result["custom_metrics"]["games_won"] = self.games_won
        result["custom_metrics"]["games_total"] = self.games_total
        result["custom_metrics"]["win_rate"] = self.games_won / max(self.games_total, 1)
        result["custom_metrics"]["games_per_hour"] = games_per_hour
        result["custom_metrics"]["best_reward"] = self.best_reward

    def on_postprocess_trajectory(
        self,
        *,
        worker: RolloutWorker,
        episode: Episode,
        agent_id: str,
        policy_id: PolicyID,
        policies: Dict[PolicyID, Policy],
        postprocessed_batch: Dict[str, Any],
        original_batches: Dict[str, Any],
        **kwargs,
    ):
        """Called after trajectory postprocessing"""
        # Could add custom reward shaping here
        pass

    def on_sample_end(
        self, *, worker: RolloutWorker, samples: Dict[str, Any], **kwargs
    ):
        """Called after sampling is completed"""
        # Could log sampling statistics
        pass

    def on_learn_on_batch(
        self, *, policy: Policy, train_batch: Dict[str, Any], result: dict, **kwargs
    ) -> None:
        """Called before/after learning on a batch"""
        # Could add custom losses or metrics
        pass

    def _calculate_games_per_hour(self) -> float:
        """Calculate games per hour metric"""
        elapsed_hours = (time.time() - self.start_time) / 3600
        if elapsed_hours > 0:
            return self.games_total / elapsed_hours
        return 0.0


class MetricsCallback(DefaultCallbacks):
    """
    Simplified callback for just tracking key metrics
    """

    def __init__(self):
        super().__init__()
        self.metrics = {
            "episode_rewards": [],
            "episode_lengths": [],
            "win_count": 0,
            "total_games": 0,
        }

    def on_episode_end(self, *, episode: Episode, **kwargs):
        """Track basic metrics"""
        self.metrics["episode_rewards"].append(episode.total_reward)
        self.metrics["episode_lengths"].append(episode.length)
        self.metrics["total_games"] += 1

        if episode.total_reward > 100:  # Win threshold
            self.metrics["win_count"] += 1

    def get_metrics(self) -> Dict[str, Any]:
        """Return current metrics"""
        return self.metrics.copy()
