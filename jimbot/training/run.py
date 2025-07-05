"""
Main training script for JimBot Ray RLlib pipeline

This script handles the full training lifecycle including initialization,
training loop, checkpointing, and evaluation.
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional

import ray
from ray import tune
from ray.rllib.agents.ppo import PPOTrainer
from ray.rllib.models import ModelCatalog
from ray.tune.logger import pretty_print

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from jimbot.training.callbacks.checkpoint_callback import BalatroCallbacks
from jimbot.training.configs.ppo_config import get_config, tune_hyperparameters
from jimbot.training.environments.balatro_env import BalatroEnv
from jimbot.training.models.balatro_net import BalatroLSTMNet, BalatroNet


def setup_ray(memory_gb: int = 8):
    """
    Initialize Ray with memory constraints

    Args:
        memory_gb: Memory allocation in GB
    """
    if not ray.is_initialized():
        ray.init(
            num_cpus=4,
            num_gpus=1,
            object_store_memory=2_000_000_000,  # 2GB
            _memory=memory_gb * 1_000_000_000,
            _system_config={
                "object_spilling_config": json.dumps(
                    {
                        "type": "filesystem",
                        "params": {
                            "directory_path": "/tmp/ray_spill",
                            "max_buffer_size": 1_000_000_000,
                        },
                    }
                )
            },
        )
        print(f"Ray initialized with {memory_gb}GB memory allocation")


def register_models():
    """Register custom models with Ray"""
    ModelCatalog.register_custom_model("BalatroNet", BalatroNet)
    ModelCatalog.register_custom_model("BalatroLSTMNet", BalatroLSTMNet)
    print("Custom models registered")


def create_trainer(
    config: Dict[str, Any], checkpoint_path: Optional[str] = None
) -> PPOTrainer:
    """
    Create and optionally restore PPO trainer

    Args:
        config: Training configuration
        checkpoint_path: Path to checkpoint to restore from

    Returns:
        PPOTrainer instance
    """
    trainer = PPOTrainer(config=config, env=BalatroEnv)

    if checkpoint_path and os.path.exists(checkpoint_path):
        trainer.restore(checkpoint_path)
        print(f"Restored trainer from checkpoint: {checkpoint_path}")

    return trainer


def train_loop(
    trainer: PPOTrainer,
    num_iterations: int = 1000,
    checkpoint_freq: int = 10,
    target_reward: float = 500.0,
    log_file: Optional[str] = None,
):
    """
    Main training loop with monitoring and checkpointing

    Args:
        trainer: PPO trainer instance
        num_iterations: Maximum training iterations
        checkpoint_freq: Checkpoint frequency
        target_reward: Target reward to stop training
        log_file: Path to save training logs
    """
    best_reward = -float("inf")
    start_time = time.time()

    for i in range(num_iterations):
        # Train for one iteration
        result = trainer.train()

        # Extract key metrics
        episode_reward_mean = result.get("episode_reward_mean", 0)
        episode_len_mean = result.get("episode_len_mean", 0)
        timesteps_total = result.get("timesteps_total", 0)
        episodes_total = result.get("episodes_total", 0)

        # Calculate performance metrics
        elapsed_hours = (time.time() - start_time) / 3600
        games_per_hour = episodes_total / elapsed_hours if elapsed_hours > 0 else 0

        # Print progress
        print(f"\nIteration {i + 1}/{num_iterations}")
        print(f"Episode Reward Mean: {episode_reward_mean:.2f}")
        print(f"Episode Length Mean: {episode_len_mean:.2f}")
        print(f"Total Timesteps: {timesteps_total:,}")
        print(f"Total Episodes: {episodes_total:,}")
        print(f"Games/Hour: {games_per_hour:.2f}")
        print(f"Time Elapsed: {elapsed_hours:.2f} hours")

        # Log to file if specified
        if log_file:
            with open(log_file, "a") as f:
                f.write(
                    json.dumps(
                        {
                            "iteration": i + 1,
                            "episode_reward_mean": episode_reward_mean,
                            "episode_len_mean": episode_len_mean,
                            "timesteps_total": timesteps_total,
                            "episodes_total": episodes_total,
                            "games_per_hour": games_per_hour,
                            "time_elapsed": elapsed_hours,
                        }
                    )
                    + "\n"
                )

        # Save checkpoint if improved
        if episode_reward_mean > best_reward:
            best_reward = episode_reward_mean
            checkpoint = trainer.save()
            print(f"New best model saved: {checkpoint}")

            # Save best model separately
            best_checkpoint_path = os.path.join(
                os.path.dirname(checkpoint), "best_model"
            )
            trainer.save(best_checkpoint_path)

        # Regular checkpoint
        if (i + 1) % checkpoint_freq == 0:
            checkpoint = trainer.save()
            print(f"Checkpoint saved: {checkpoint}")

        # Check if target reached
        if episode_reward_mean >= target_reward:
            print(f"\nTarget reward {target_reward} reached!")
            final_checkpoint = trainer.save()
            print(f"Final model saved: {final_checkpoint}")
            break

        # Check performance target
        if games_per_hour < 1000 and elapsed_hours > 0.5:
            print(f"Warning: Games/hour ({games_per_hour:.2f}) below target (1000)")

    print(f"\nTraining completed. Best reward: {best_reward:.2f}")


def evaluate_model(trainer: PPOTrainer, num_episodes: int = 100):
    """
    Evaluate trained model

    Args:
        trainer: Trained PPO trainer
        num_episodes: Number of evaluation episodes
    """
    print(f"\nEvaluating model for {num_episodes} episodes...")

    rewards = []
    lengths = []
    wins = 0

    for i in range(num_episodes):
        episode_reward = 0
        episode_length = 0
        done = False

        obs = trainer.workers.local_worker().env.reset()

        while not done:
            action = trainer.compute_single_action(obs, explore=False)
            obs, reward, done, info = trainer.workers.local_worker().env.step(action)
            episode_reward += reward
            episode_length += 1

        rewards.append(episode_reward)
        lengths.append(episode_length)

        # Check if won (assuming victory gives large positive reward)
        if episode_reward > 100:
            wins += 1

        if (i + 1) % 10 == 0:
            print(f"Episodes completed: {i + 1}/{num_episodes}")

    # Print evaluation results
    print("\nEvaluation Results:")
    print(f"Average Reward: {sum(rewards) / len(rewards):.2f}")
    print(f"Average Length: {sum(lengths) / len(lengths):.2f}")
    print(f"Win Rate: {wins / num_episodes * 100:.2f}%")
    print(f"Max Reward: {max(rewards):.2f}")
    print(f"Min Reward: {min(rewards):.2f}")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Train JimBot with Ray RLlib")

    # Training arguments
    parser.add_argument(
        "--config", type=str, default="default", help="Configuration variant to use"
    )
    parser.add_argument(
        "--checkpoint", type=str, default=None, help="Checkpoint path to resume from"
    )
    parser.add_argument(
        "--iterations", type=int, default=1000, help="Number of training iterations"
    )
    parser.add_argument(
        "--checkpoint-freq", type=int, default=10, help="Checkpoint frequency"
    )
    parser.add_argument(
        "--target-reward",
        type=float,
        default=500.0,
        help="Target reward to stop training",
    )

    # Evaluation arguments
    parser.add_argument(
        "--evaluate", action="store_true", help="Evaluate model instead of training"
    )
    parser.add_argument(
        "--eval-episodes", type=int, default=100, help="Number of evaluation episodes"
    )

    # Other arguments
    parser.add_argument("--tune", action="store_true", help="Run hyperparameter tuning")
    parser.add_argument("--memory", type=int, default=8, help="Memory allocation in GB")
    parser.add_argument(
        "--log-file", type=str, default=None, help="Path to save training logs"
    )

    args = parser.parse_args()

    # Setup Ray
    setup_ray(args.memory)

    # Register models
    register_models()

    # Get configuration
    config = get_config(args.config)

    if args.tune:
        # Run hyperparameter tuning
        print("Starting hyperparameter tuning...")
        analysis = tune.run(
            PPOTrainer,
            config={**config, **tune_hyperparameters()},
            stop={"episode_reward_mean": args.target_reward},
            num_samples=10,
            checkpoint_at_end=True,
            checkpoint_freq=args.checkpoint_freq,
        )
        print("Best config:", analysis.best_config)
        print("Best checkpoint:", analysis.best_checkpoint)
    else:
        # Create trainer
        trainer = create_trainer(config, args.checkpoint)

        if args.evaluate:
            # Evaluate model
            evaluate_model(trainer, args.eval_episodes)
        else:
            # Run training
            train_loop(
                trainer,
                num_iterations=args.iterations,
                checkpoint_freq=args.checkpoint_freq,
                target_reward=args.target_reward,
                log_file=args.log_file,
            )

    # Cleanup
    ray.shutdown()


if __name__ == "__main__":
    main()
