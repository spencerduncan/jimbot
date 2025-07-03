"""
PPO configuration for Balatro training

This module contains the PPO algorithm configuration optimized for training
on Balatro with 8GB memory allocation and RTX 3090 GPU.
"""

from typing import Dict, Any


# Base PPO configuration
PPO_CONFIG: Dict[str, Any] = {
    # Algorithm
    "algorithm": "PPO",
    # Environment
    "env": "BalatroEnv",
    "env_config": {
        "game_config": {
            "stake": 0,  # Start with lowest difficulty
            "seed": None,  # Random seed
            "deck": "Red Deck",  # Default deck
            "challenge": None,
        }
    },
    # Framework
    "framework": "torch",
    "eager_tracing": False,
    # Resources
    "num_workers": 2,  # Limited by 8GB allocation
    "num_envs_per_worker": 4,  # 8 parallel environments total
    "num_cpus_per_worker": 1,
    "num_gpus": 1,  # RTX 3090
    "num_gpus_per_worker": 0,  # GPU for training only
    # Rollout settings
    "rollout_fragment_length": 200,
    "batch_mode": "truncate_episodes",
    # Training settings
    "train_batch_size": 4000,
    "sgd_minibatch_size": 128,
    "num_sgd_iter": 30,
    # Learning rate
    "lr": 5e-5,
    "lr_schedule": None,  # Could add decay schedule
    # PPO specific
    "use_critic": True,
    "use_gae": True,
    "lambda": 0.95,
    "kl_coeff": 0.2,
    "kl_target": 0.02,
    "vf_loss_coeff": 1.0,
    "entropy_coeff": 0.01,
    "entropy_coeff_schedule": None,
    "clip_param": 0.2,
    "vf_clip_param": 10.0,
    "grad_clip": 0.5,
    # Model
    "model": {
        "custom_model": "BalatroNet",
        "custom_model_config": {
            "memgraph_embedding_dim": 128,
            "hidden_size": 512,
        },
        "max_seq_len": 200,  # For LSTM variant
        "vf_share_layers": False,  # Separate value network
        "fcnet_hiddens": [512, 512],  # Fallback if custom model fails
        "fcnet_activation": "relu",
    },
    # Exploration
    "explore": True,
    "exploration_config": {
        "type": "StochasticSampling",
        "random_timesteps": 10000,  # Initial random exploration
    },
    # Memory settings
    "replay_buffer_config": {
        "type": "MultiAgentPrioritizedReplayBuffer",
        "capacity": 100000,  # ~2GB with our observation size
        "prioritized_replay": False,  # Save memory
        "storage_unit": "timesteps",
    },
    # Evaluation
    "evaluation_interval": 10,
    "evaluation_duration": 10,
    "evaluation_duration_unit": "episodes",
    "evaluation_parallel_to_training": False,  # Save resources
    "evaluation_config": {
        "explore": False,  # No exploration during eval
        "env_config": {
            "game_config": {
                "stake": 0,  # Consistent evaluation
            }
        },
    },
    # Callbacks
    "callbacks": "BalatroCallbacks",
    # Debugging
    "log_level": "INFO",
    "seed": 42,
    "monitor": False,  # Disable video recording
    # Checkpointing
    "checkpoint_freq": 10,
    "checkpoint_at_end": True,
    "export_native_model_files": True,
    # Multi-agent (future support)
    "multiagent": {
        "policies": {},
        "policy_mapping_fn": None,
    },
}


# GPU-specific configuration
GPU_CONFIG: Dict[str, Any] = {
    "num_gpus": 1,  # RTX 3090
    "num_gpus_per_worker": 0,  # GPU for training only
    "_fake_gpus": False,
    # Custom resource allocation
    "custom_resources_per_worker": {
        "gpu_memory": 0.1,  # Reserve 10% GPU memory per worker (~2.4GB)
    },
    # PyTorch specific
    "torch_gpu_id": 0,
    "torch_compile_config": {
        "backend": "inductor",
        "mode": "default",
    },
}


# Memory-optimized configuration for 8GB allocation
MEMORY_CONFIG: Dict[str, Any] = {
    # Object store settings
    "object_store_memory": 2_000_000_000,  # 2GB
    # Worker settings
    "memory_per_worker": 1_000_000_000,  # 1GB per worker
    # Spilling configuration
    "object_spilling_config": {
        "type": "filesystem",
        "params": {
            "directory_path": "/tmp/ray_spill",
            "max_buffer_size": 1_000_000_000,  # 1GB
        },
    },
    # Batch settings for memory efficiency
    "compress_observations": True,
    "shuffle_buffer_size": 1000,
    "prioritized_replay_eps": 1e-6,
}


# Performance optimization configuration
PERFORMANCE_CONFIG: Dict[str, Any] = {
    # Parallelism
    "remote_worker_envs": True,
    "remote_env_batch_wait_ms": 10,
    "sample_async": True,
    # Vectorization
    "batch_mode": "complete_episodes",
    "horizon": 1000,  # Max episode length
    # GPU optimization
    "num_multi_gpu_tower_stacks": 1,
    "simple_optimizer": True,
    "_disable_preprocessor_api": False,
    # Metrics
    "metrics_episode_collection_timeout_s": 60,
    "metrics_num_episodes_for_smoothing": 100,
    "min_time_s_per_iteration": 0,
    "min_sample_timesteps_per_iteration": 1000,
}


# Experimental configurations for different scenarios
EXPERIMENTAL_CONFIGS = {
    "fast_training": {
        **PPO_CONFIG,
        "num_workers": 4,
        "num_envs_per_worker": 2,
        "train_batch_size": 8000,
        "sgd_minibatch_size": 256,
        "lr": 1e-4,
        "entropy_coeff": 0.02,
    },
    "stable_training": {
        **PPO_CONFIG,
        "lr": 1e-5,
        "clip_param": 0.1,
        "num_sgd_iter": 50,
        "kl_target": 0.01,
    },
    "lstm_variant": {
        **PPO_CONFIG,
        "model": {
            **PPO_CONFIG["model"],
            "custom_model": "BalatroLSTMNet",
            "use_lstm": True,
            "lstm_cell_size": 256,
            "lstm_use_prev_action": True,
            "lstm_use_prev_reward": True,
        },
    },
}


def get_config(variant: str = "default") -> Dict[str, Any]:
    """
    Get configuration for a specific variant

    Args:
        variant: Configuration variant name

    Returns:
        Complete configuration dictionary
    """
    if variant == "default":
        config = PPO_CONFIG.copy()
    elif variant in EXPERIMENTAL_CONFIGS:
        config = EXPERIMENTAL_CONFIGS[variant].copy()
    else:
        raise ValueError(f"Unknown config variant: {variant}")

    # Merge GPU and memory settings
    config.update(GPU_CONFIG)

    # Add memory settings to config
    for key, value in MEMORY_CONFIG.items():
        if key not in config:
            config[key] = value

    return config


def tune_hyperparameters() -> Dict[str, Any]:
    """
    Get hyperparameter search space for Ray Tune

    Returns:
        Dictionary of hyperparameter distributions
    """
    from ray import tune

    return {
        "lr": tune.loguniform(1e-6, 1e-3),
        "train_batch_size": tune.choice([2000, 4000, 8000]),
        "sgd_minibatch_size": tune.choice([64, 128, 256]),
        "num_sgd_iter": tune.choice([10, 20, 30, 50]),
        "clip_param": tune.uniform(0.1, 0.3),
        "entropy_coeff": tune.loguniform(0.001, 0.1),
        "vf_loss_coeff": tune.uniform(0.5, 2.0),
        "model": {
            "custom_model_config": {
                "hidden_size": tune.choice([256, 512, 1024]),
            }
        },
    }


if __name__ == "__main__":
    # Print default configuration
    import json

    config = get_config()
    print(json.dumps(config, indent=2))
