# Ray RLlib Training Subsystem - Claude Guidance

## Overview

This directory contains the Ray RLlib training pipeline for JimBot's
reinforcement learning system. The subsystem is allocated 8GB RAM and must
achieve >1000 games/hour training throughput while managing GPU resources
efficiently.

## Directory Structure

```
training/
├── models/          # Custom neural network architectures
├── environments/    # Balatro game environment wrappers
├── policies/        # Custom policies and action distributions
├── callbacks/       # Training callbacks for monitoring and checkpointing
├── checkpoints/     # Model checkpoints and saved policies
├── configs/         # Training configurations and hyperparameters
├── run.py          # Main training entry point
└── __init__.py
```

## PPO Configuration

### Core Settings

```python
PPO_CONFIG = {
    "framework": "torch",
    "num_workers": 2,  # Limited by 8GB allocation
    "num_envs_per_worker": 4,  # 8 parallel environments total
    "rollout_fragment_length": 200,
    "train_batch_size": 4000,
    "sgd_minibatch_size": 128,
    "num_sgd_iter": 30,
    "lr": 5e-5,
    "lambda": 0.95,
    "gamma": 0.99,
    "entropy_coeff": 0.01,
    "clip_param": 0.2,
    "vf_clip_param": 10.0,
    "grad_clip": 0.5,
    "kl_target": 0.02,
}
```

### GPU Configuration

```python
GPU_CONFIG = {
    "num_gpus": 1,  # RTX 3090
    "num_gpus_per_worker": 0,  # GPU for training only
    "custom_resources_per_worker": {"gpu_memory": 0.1},  # 2.4GB per worker
    "_fake_gpus": False,
}
```

## Custom Model Architecture

### BalatroNet

```python
class BalatroNet(TorchModelV2):
    def __init__(self, obs_space, action_space, num_outputs, model_config, name):
        super().__init__(obs_space, action_space, num_outputs, model_config, name)

        # Memgraph embedding integration
        self.memgraph_embedding_dim = model_config["custom_model_config"]["memgraph_embedding_dim"]

        # Feature extraction layers
        self.card_encoder = nn.Sequential(
            nn.Linear(52 * 4, 256),  # 52 cards * 4 features
            nn.ReLU(),
            nn.Linear(256, 128)
        )

        self.joker_encoder = nn.Sequential(
            nn.Linear(150 * 8, 512),  # 150 jokers * 8 features
            nn.ReLU(),
            nn.Linear(512, 256)
        )

        # Combined processing
        self.shared_layers = nn.Sequential(
            nn.Linear(128 + 256 + self.memgraph_embedding_dim, 512),
            nn.ReLU(),
            nn.Linear(512, 512),
            nn.ReLU()
        )

        # Policy and value heads
        self.policy_head = nn.Linear(512, num_outputs)
        self.value_head = nn.Linear(512, 1)
```

## Memory Management Patterns

### Worker Memory Allocation

```python
def configure_ray_memory():
    """Configure Ray for 8GB training allocation"""
    ray.init(
        object_store_memory=2_000_000_000,  # 2GB object store
        _memory=8_000_000_000,  # 8GB total
        _system_config={
            "object_spilling_config": json.dumps({
                "type": "filesystem",
                "params": {
                    "directory_path": "/tmp/ray_spill",
                    "max_buffer_size": 1_000_000_000  # 1GB spill buffer
                }
            })
        }
    )
```

### Batch Processing Optimization

```python
class MemoryEfficientSampler:
    def __init__(self, buffer_size=100000):
        self.buffer = ReplayBuffer(buffer_size)
        self.batch_size = 4000

    def sample_efficient(self):
        """Sample with minimal memory allocation"""
        # Reuse tensors to avoid allocation
        if not hasattr(self, '_sample_buffer'):
            self._sample_buffer = torch.zeros((self.batch_size,), dtype=torch.float32)

        # In-place operations
        indices = torch.randint(0, len(self.buffer), (self.batch_size,))
        self._sample_buffer.index_copy_(0, indices, self.buffer.data)
        return self._sample_buffer
```

## Performance Optimization

### Achieving >1000 Games/Hour

1. **Vectorized Environments**: Run 8 environments in parallel
2. **Async Rollouts**: Overlap GPU training with CPU simulation
3. **Optimized Observations**: Compact game state representation
4. **Fast Action Sampling**: Cached probability distributions

### Profiling Code

```python
import torch.profiler

def profile_training_step():
    with torch.profiler.profile(
        activities=[
            torch.profiler.ProfilerActivity.CPU,
            torch.profiler.ProfilerActivity.CUDA,
        ],
        record_shapes=True,
        profile_memory=True,
        with_stack=True
    ) as prof:
        trainer.train()

    print(prof.key_averages().table(sort_by="cuda_time_total", row_limit=10))
```

## Environment Wrapper Requirements

### BalatroEnv Interface

```python
class BalatroEnv(gym.Env):
    """Balatro environment wrapper for Ray RLlib"""

    def __init__(self, config):
        self.mcp_client = config.get("mcp_client")
        self.memgraph_client = config.get("memgraph_client")
        self.action_space = spaces.Discrete(1000)  # All possible game actions
        self.observation_space = spaces.Dict({
            "cards": spaces.Box(low=0, high=1, shape=(52, 4)),
            "jokers": spaces.Box(low=0, high=1, shape=(150, 8)),
            "game_state": spaces.Box(low=-np.inf, high=np.inf, shape=(50,)),
            "memgraph_embedding": spaces.Box(low=-1, high=1, shape=(128,))
        })
```

## Checkpoint Management

### Checkpoint Strategy

```python
class BalatroCheckpointCallback(DefaultCallbacks):
    def on_train_result(self, *, algorithm, result, **kwargs):
        if result["episode_reward_mean"] > algorithm.best_reward:
            algorithm.best_reward = result["episode_reward_mean"]
            checkpoint = algorithm.save_checkpoint(self.checkpoint_dir)

            # Save additional metadata
            metadata = {
                "reward": result["episode_reward_mean"],
                "timesteps": result["timesteps_total"],
                "games_played": result["episodes_total"],
                "timestamp": time.time()
            }
            with open(f"{checkpoint}.meta", "w") as f:
                json.dump(metadata, f)
```

## Integration Points

### Week 2-3: Environment Development

- Implement BalatroEnv with MCP integration
- Create observation/action space mappings
- Test with random policy baseline

### Week 4-5: Neural Network Architecture

- Implement BalatroNet with Memgraph embeddings
- Optimize for GPU memory constraints
- Profile and benchmark performance

### Week 6-7: Training Pipeline

- Configure PPO for optimal performance
- Implement custom callbacks for monitoring
- Integrate with Claude for strategic decisions

### Week 8: Performance Optimization

- Achieve >1000 games/hour target
- Implement distributed training if needed
- Final checkpoint management system

## Common Pitfalls and Solutions

1. **Memory Leaks**: Use `ray.get()` carefully, clear object references
2. **GPU OOM**: Monitor GPU memory with `nvidia-smi`, adjust batch sizes
3. **Slow Rollouts**: Profile environment step times, optimize MCP calls
4. **Training Instability**: Adjust PPO clip parameters, use gradient clipping

## Testing Commands

```bash
# Test environment
python -m pytest tests/training/test_environment.py -v

# Benchmark throughput
python -m jimbot.training.benchmark --games 100

# Profile training
python -m jimbot.training.profile --steps 1000

# Memory monitoring
ray memory --help
```

## Performance Monitoring

```python
# Real-time metrics
wandb.log({
    "games_per_hour": games_played / hours_elapsed,
    "gpu_utilization": gpu_stats["utilization"],
    "memory_used": process.memory_info().rss / 1e9,
    "mean_reward": episode_rewards.mean(),
    "policy_loss": info["learner"]["policy_loss"],
    "value_loss": info["learner"]["vf_loss"]
})
```
