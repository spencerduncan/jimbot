"""
BalatroNet: Custom neural network architecture for Balatro RL

This module implements a custom neural network that processes card game state,
joker configurations, and knowledge graph embeddings to produce action distributions
and value estimates for PPO training.
"""

import numpy as np
import torch
import torch.nn as nn
from typing import Dict, List, Optional, Tuple

from ray.rllib.models.torch.torch_modelv2 import TorchModelV2
from ray.rllib.models.torch.misc import SlimFC, normc_initializer
from ray.rllib.utils.annotations import override
from ray.rllib.utils.typing import ModelConfigDict, TensorType


class BalatroNet(TorchModelV2, nn.Module):
    """
    Custom neural network for Balatro game
    
    Architecture:
    - Card encoder: Processes 52 cards with 4 features each
    - Joker encoder: Processes up to 150 jokers with 8 features each
    - Shared layers: Combines encodings with Memgraph embeddings
    - Separate policy and value heads
    """
    
    def __init__(
        self,
        obs_space,
        action_space,
        num_outputs: int,
        model_config: ModelConfigDict,
        name: str
    ):
        """
        Initialize BalatroNet
        
        Args:
            obs_space: Observation space (Dict)
            action_space: Action space (Discrete)
            num_outputs: Number of output logits
            model_config: Model configuration from RLlib
            name: Model name
        """
        TorchModelV2.__init__(
            self, obs_space, action_space, num_outputs, model_config, name
        )
        nn.Module.__init__(self)
        
        # Get custom config
        custom_config = model_config.get("custom_model_config", {})
        self.memgraph_embedding_dim = custom_config.get("memgraph_embedding_dim", 128)
        hidden_size = custom_config.get("hidden_size", 512)
        
        # Card encoder: 52 cards * 4 features = 208 inputs
        self.card_encoder = nn.Sequential(
            SlimFC(52 * 4, 256, activation_fn=nn.ReLU),
            SlimFC(256, 128, activation_fn=nn.ReLU)
        )
        
        # Joker encoder: 150 jokers * 8 features = 1200 inputs
        self.joker_encoder = nn.Sequential(
            SlimFC(150 * 8, 512, activation_fn=nn.ReLU),
            SlimFC(512, 256, activation_fn=nn.ReLU)
        )
        
        # Game state encoder: 50 features
        self.state_encoder = nn.Sequential(
            SlimFC(50, 128, activation_fn=nn.ReLU),
            SlimFC(128, 64, activation_fn=nn.ReLU)
        )
        
        # Combined feature size
        combined_size = 128 + 256 + 64 + self.memgraph_embedding_dim  # 576
        
        # Shared layers
        self.shared_layers = nn.Sequential(
            SlimFC(combined_size, hidden_size, activation_fn=nn.ReLU),
            SlimFC(hidden_size, hidden_size, activation_fn=nn.ReLU)
        )
        
        # Policy head with action masking support
        self.policy_head = SlimFC(
            hidden_size,
            num_outputs,
            initializer=normc_initializer(0.01)
        )
        
        # Value head
        self.value_head = SlimFC(
            hidden_size,
            1,
            initializer=normc_initializer(1.0)
        )
        
        # Placeholder for last output
        self._features = None
        self._value = None
        
    @override(TorchModelV2)
    def forward(
        self,
        input_dict: Dict[str, TensorType],
        state: List[TensorType],
        seq_lens: TensorType
    ) -> Tuple[TensorType, List[TensorType]]:
        """
        Forward pass through the network
        
        Args:
            input_dict: Dictionary containing observations
            state: RNN state (not used)
            seq_lens: Sequence lengths (not used)
            
        Returns:
            Action logits and updated state
        """
        obs = input_dict["obs"]
        
        # Extract components from observation
        cards = obs["cards"]
        jokers = obs["jokers"]
        game_state = obs["game_state"]
        memgraph_embedding = obs["memgraph_embedding"]
        action_mask = obs.get("action_mask", None)
        
        # Flatten cards and jokers for encoding
        batch_size = cards.shape[0]
        cards_flat = cards.view(batch_size, -1)
        jokers_flat = jokers.view(batch_size, -1)
        
        # Encode each component
        card_features = self.card_encoder(cards_flat)
        joker_features = self.joker_encoder(jokers_flat)
        state_features = self.state_encoder(game_state)
        
        # Concatenate all features
        combined_features = torch.cat([
            card_features,
            joker_features,
            state_features,
            memgraph_embedding
        ], dim=1)
        
        # Process through shared layers
        self._features = self.shared_layers(combined_features)
        
        # Get policy logits
        logits = self.policy_head(self._features)
        
        # Apply action masking if provided
        if action_mask is not None:
            # Convert mask to logit mask (0 -> -inf, 1 -> 0)
            inf_mask = torch.clamp(torch.log(action_mask), min=-1e10)
            logits = logits + inf_mask
        
        # Compute value for value_function()
        self._value = self.value_head(self._features)
        
        return logits, state
    
    @override(TorchModelV2)
    def value_function(self) -> TensorType:
        """
        Return the value estimate
        
        Returns:
            Value tensor
        """
        assert self._value is not None, "Must call forward() first"
        return self._value.squeeze(1)
    
    def get_initial_state(self) -> List[TensorType]:
        """
        Get initial RNN state (not used for feedforward network)
        
        Returns:
            Empty list
        """
        return []
    
    def custom_loss(
        self,
        policy_loss: TensorType,
        loss_inputs: Dict[str, TensorType]
    ) -> TensorType:
        """
        Add custom losses if needed
        
        Args:
            policy_loss: Base policy loss
            loss_inputs: Dictionary of loss inputs
            
        Returns:
            Modified loss
        """
        # Could add auxiliary losses here (e.g., predict next card)
        return policy_loss
    
    def metrics(self) -> Dict[str, TensorType]:
        """
        Return custom metrics for logging
        
        Returns:
            Dictionary of metrics
        """
        return {
            "feature_norm": torch.mean(torch.norm(self._features, dim=1))
            if self._features is not None else 0.0
        }


class BalatroLSTMNet(BalatroNet):
    """
    LSTM variant of BalatroNet for handling sequential decisions
    
    Adds LSTM layers after feature encoding to capture temporal dependencies
    in card play sequences.
    """
    
    def __init__(
        self,
        obs_space,
        action_space,
        num_outputs: int,
        model_config: ModelConfigDict,
        name: str
    ):
        """Initialize LSTM variant"""
        super().__init__(obs_space, action_space, num_outputs, model_config, name)
        
        # Replace shared layers with LSTM
        hidden_size = model_config.get("custom_model_config", {}).get("hidden_size", 512)
        self.lstm = nn.LSTM(
            input_size=128 + 256 + 64 + self.memgraph_embedding_dim,
            hidden_size=hidden_size,
            num_layers=2,
            batch_first=True
        )
        
        # Update policy and value heads to work with LSTM output
        self.policy_head = SlimFC(hidden_size, num_outputs)
        self.value_head = SlimFC(hidden_size, 1)
        
        # LSTM state size
        self.state_size = [hidden_size, hidden_size]  # (h, c) for each layer
    
    @override(BalatroNet)
    def get_initial_state(self) -> List[TensorType]:
        """Get initial LSTM state"""
        return [
            torch.zeros(2, self.state_size[0]),  # Hidden state
            torch.zeros(2, self.state_size[1])   # Cell state
        ]
    
    # Override forward() to use LSTM instead of feedforward layers