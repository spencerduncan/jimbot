"""Feature extraction from Memgraph for machine learning models."""

import numpy as np
from typing import List, Dict, Any, Optional, Tuple
import asyncio
from dataclasses import dataclass
import logging

from .client import MemgraphClient
from .query_builder import QueryBuilder, SynergyQueryBuilder

logger = logging.getLogger(__name__)


@dataclass
class GameState:
    """Current game state for feature extraction."""
    jokers: List[str]
    cards: List[Dict[str, str]]  # List of {suit, rank, enhancement}
    money: int
    ante: int
    hands_remaining: int
    discards_remaining: int
    hand_size: int
    deck_size: int
    shop_jokers: List[str] = None
    played_hands: List[str] = None


class GraphFeatureExtractor:
    """Extract graph-based features for RL models."""
    
    def __init__(self, client: MemgraphClient, embedding_dim: int = 128):
        self.client = client
        self.embedding_dim = embedding_dim
        self._joker_embeddings: Optional[Dict[str, np.ndarray]] = None
        self._synergy_matrix: Optional[np.ndarray] = None
        self._joker_index: Optional[Dict[str, int]] = None
    
    async def initialize(self):
        """Initialize embeddings and cached data."""
        await self._load_joker_embeddings()
        await self._load_synergy_matrix()
    
    async def _load_joker_embeddings(self):
        """Load or compute joker embeddings."""
        # Try to load pre-computed embeddings
        query = """
        MATCH (j:Joker)
        WHERE j.embedding IS NOT NULL
        RETURN j.name as name, j.embedding as embedding
        """
        
        results = await self.client.execute_query(query)
        
        if results:
            self._joker_embeddings = {
                r["name"]: np.array(r["embedding"])
                for r in results
            }
            logger.info(f"Loaded {len(self._joker_embeddings)} joker embeddings")
        else:
            # Compute embeddings if not available
            logger.info("Computing joker embeddings...")
            self._joker_embeddings = await self._compute_joker_embeddings()
    
    async def _compute_joker_embeddings(self) -> Dict[str, np.ndarray]:
        """Compute joker embeddings using graph structure."""
        # Get all jokers and their properties
        query = """
        MATCH (j:Joker)
        OPTIONAL MATCH (j)-[s:SYNERGIZES_WITH]-(other:Joker)
        OPTIONAL MATCH (j)-[:REQUIRES_CARD]->(c:PlayingCard)
        RETURN j.name as name,
               j.rarity as rarity,
               j.cost as cost,
               j.scaling_type as scaling_type,
               COLLECT(DISTINCT other.name) as synergies,
               COLLECT(DISTINCT c.suit + c.rank) as required_cards
        """
        
        results = await self.client.execute_query(query)
        
        # Build feature vectors
        embeddings = {}
        
        # Create categorical encodings
        rarities = ["common", "uncommon", "rare", "legendary"]
        scaling_types = ["none", "linear", "exponential", "conditional"]
        
        for joker in results:
            features = []
            
            # Rarity one-hot encoding
            rarity_vec = [1 if joker["rarity"] == r else 0 for r in rarities]
            features.extend(rarity_vec)
            
            # Cost normalized
            features.append(joker["cost"] / 20.0)  # Normalize by max cost
            
            # Scaling type one-hot
            scaling_vec = [1 if joker["scaling_type"] == s else 0 for s in scaling_types]
            features.extend(scaling_vec)
            
            # Synergy count normalized
            features.append(len(joker["synergies"]) / 10.0)
            
            # Required cards diversity
            suits = set(card[:1] for card in joker["required_cards"])
            features.append(len(suits) / 4.0)  # Normalized by number of suits
            
            # Pad to embedding dimension
            current_size = len(features)
            if current_size < self.embedding_dim:
                features.extend([0.0] * (self.embedding_dim - current_size))
            
            embeddings[joker["name"]] = np.array(features[:self.embedding_dim])
        
        return embeddings
    
    async def _load_synergy_matrix(self):
        """Load synergy relationships as a matrix."""
        # Get all jokers in consistent order
        joker_query = """
        MATCH (j:Joker)
        RETURN j.name as name
        ORDER BY j.name
        """
        
        joker_results = await self.client.execute_query(joker_query)
        joker_names = [r["name"] for r in joker_results]
        
        self._joker_index = {name: i for i, name in enumerate(joker_names)}
        n_jokers = len(joker_names)
        
        # Initialize matrix
        self._synergy_matrix = np.eye(n_jokers)  # Self-synergy = 1.0
        
        # Fill synergy values
        synergy_query = """
        MATCH (j1:Joker)-[s:SYNERGIZES_WITH]->(j2:Joker)
        RETURN j1.name as joker1, j2.name as joker2, s.strength as strength
        """
        
        synergy_results = await self.client.execute_query(synergy_query)
        
        for synergy in synergy_results:
            i = self._joker_index.get(synergy["joker1"])
            j = self._joker_index.get(synergy["joker2"])
            
            if i is not None and j is not None:
                self._synergy_matrix[i, j] = synergy["strength"]
                self._synergy_matrix[j, i] = synergy["strength"]  # Symmetric
    
    async def extract_features(self, game_state: GameState) -> np.ndarray:
        """Extract feature vector from current game state.
        
        Args:
            game_state: Current game state
            
        Returns:
            Feature vector for RL model
        """
        features = []
        
        # 1. Joker features
        joker_features = await self._extract_joker_features(game_state.jokers)
        features.extend(joker_features)
        
        # 2. Synergy features
        synergy_features = await self._extract_synergy_features(game_state.jokers)
        features.extend(synergy_features)
        
        # 3. Card composition features
        card_features = self._extract_card_features(game_state.cards)
        features.extend(card_features)
        
        # 4. Game state features
        state_features = self._extract_state_features(game_state)
        features.extend(state_features)
        
        # 5. Strategy alignment features
        strategy_features = await self._extract_strategy_features(game_state)
        features.extend(strategy_features)
        
        # 6. Victory path features
        path_features = await self._extract_victory_path_features(game_state)
        features.extend(path_features)
        
        return np.array(features, dtype=np.float32)
    
    async def _extract_joker_features(self, joker_names: List[str]) -> List[float]:
        """Extract features from current jokers."""
        if not self._joker_embeddings:
            await self._load_joker_embeddings()
        
        # Average embeddings of owned jokers
        if not joker_names:
            return [0.0] * self.embedding_dim
        
        embeddings = [
            self._joker_embeddings.get(name, np.zeros(self.embedding_dim))
            for name in joker_names
        ]
        
        avg_embedding = np.mean(embeddings, axis=0)
        return avg_embedding.tolist()
    
    async def _extract_synergy_features(self, joker_names: List[str]) -> List[float]:
        """Extract synergy-based features."""
        if not self._synergy_matrix is not None:
            await self._load_synergy_matrix()
        
        features = []
        
        if len(joker_names) < 2:
            # No synergies possible
            features.extend([0.0, 0.0, 0.0, 0.0])
        else:
            # Calculate pairwise synergies
            synergies = []
            for i, j1 in enumerate(joker_names):
                for j2 in joker_names[i+1:]:
                    idx1 = self._joker_index.get(j1)
                    idx2 = self._joker_index.get(j2)
                    
                    if idx1 is not None and idx2 is not None:
                        synergies.append(self._synergy_matrix[idx1, idx2])
            
            if synergies:
                features.append(np.mean(synergies))  # Average synergy
                features.append(np.max(synergies))   # Best synergy
                features.append(np.min(synergies))   # Worst synergy
                features.append(np.std(synergies))   # Synergy variance
            else:
                features.extend([0.0, 0.0, 0.0, 0.0])
        
        # Synergy graph density
        n_jokers = len(joker_names)
        max_edges = n_jokers * (n_jokers - 1) / 2
        actual_edges = sum(1 for s in synergies if s > 0.5) if 'synergies' in locals() else 0
        density = actual_edges / max_edges if max_edges > 0 else 0
        features.append(density)
        
        return features
    
    def _extract_card_features(self, cards: List[Dict[str, str]]) -> List[float]:
        """Extract features from card composition."""
        features = []
        
        # Suit distribution
        suit_counts = {"Hearts": 0, "Diamonds": 0, "Clubs": 0, "Spades": 0}
        rank_counts = {}
        enhancement_counts = {}
        
        for card in cards:
            suit_counts[card["suit"]] += 1
            rank = card["rank"]
            rank_counts[rank] = rank_counts.get(rank, 0) + 1
            enhancement = card.get("enhancement", "none")
            enhancement_counts[enhancement] = enhancement_counts.get(enhancement, 0) + 1
        
        total_cards = len(cards)
        
        # Suit distribution features
        for suit in ["Hearts", "Diamonds", "Clubs", "Spades"]:
            features.append(suit_counts[suit] / total_cards if total_cards > 0 else 0)
        
        # Suit concentration (Gini coefficient)
        suit_values = list(suit_counts.values())
        gini = self._calculate_gini(suit_values)
        features.append(gini)
        
        # Rank features
        face_cards = sum(1 for card in cards if card["rank"] in ["J", "Q", "K", "A"])
        features.append(face_cards / total_cards if total_cards > 0 else 0)
        
        # Most common rank frequency
        max_rank_count = max(rank_counts.values()) if rank_counts else 0
        features.append(max_rank_count / total_cards if total_cards > 0 else 0)
        
        # Enhancement features
        enhanced_cards = sum(1 for card in cards if card.get("enhancement", "none") != "none")
        features.append(enhanced_cards / total_cards if total_cards > 0 else 0)
        
        return features
    
    def _extract_state_features(self, game_state: GameState) -> List[float]:
        """Extract game state features."""
        features = []
        
        # Normalized game progress
        features.append(game_state.ante / 10.0)  # Normalize by typical max ante
        
        # Resource features
        features.append(game_state.money / 100.0)  # Normalize by typical money scale
        features.append(game_state.hands_remaining / 5.0)  # Normalize by typical max
        features.append(game_state.discards_remaining / 5.0)
        
        # Deck state
        features.append(game_state.deck_size / 52.0)  # Normalize by standard deck
        features.append(game_state.hand_size / 10.0)  # Normalize by max hand size
        
        # Pressure indicator (low hands + high ante)
        pressure = (game_state.ante / 10.0) * (1 - game_state.hands_remaining / 5.0)
        features.append(pressure)
        
        return features
    
    async def _extract_strategy_features(self, game_state: GameState) -> List[float]:
        """Extract features related to strategy alignment."""
        # Query for strategy alignment
        query = """
        MATCH (j:Joker)
        WHERE j.name IN $joker_names
        MATCH (j)-[e:ENABLES_STRATEGY]->(s:Strategy)
        WITH s, AVG(e.importance) as avg_importance
        RETURN s.name as strategy,
               s.win_rate as win_rate,
               avg_importance
        ORDER BY avg_importance DESC
        LIMIT 3
        """
        
        results = await self.client.execute_query(
            query,
            {"joker_names": game_state.jokers}
        )
        
        features = []
        
        if results:
            # Top strategy alignment
            top_strategy = results[0]
            features.append(top_strategy["avg_importance"])
            features.append(top_strategy["win_rate"])
            
            # Strategy diversity
            strategy_count = len(results)
            features.append(strategy_count / 5.0)  # Normalize by typical max
            
            # Average win rate of aligned strategies
            avg_win_rate = np.mean([r["win_rate"] for r in results])
            features.append(avg_win_rate)
        else:
            features.extend([0.0, 0.0, 0.0, 0.0])
        
        return features
    
    async def _extract_victory_path_features(self, game_state: GameState) -> List[float]:
        """Extract features about paths to victory."""
        if not game_state.jokers:
            return [0.0, 0.0, 0.0]
        
        # Find optimal additions within budget
        query, params = SynergyQueryBuilder.calculate_joker_combinations(
            game_state.jokers,
            game_state.money,
            min_synergy=0.5
        )
        
        results = await self.client.execute_query(query, params)
        
        features = []
        
        if results:
            # Best available synergy value
            features.append(results[0]["total_value"])
            
            # Number of good options
            good_options = sum(1 for r in results if r["total_value"] > 1.0)
            features.append(good_options / 5.0)  # Normalize
            
            # Affordability (can we buy the best option?)
            can_afford_best = 1.0 if results[0]["cost"] <= game_state.money else 0.0
            features.append(can_afford_best)
        else:
            features.extend([0.0, 0.0, 0.0])
        
        return features
    
    @staticmethod
    def _calculate_gini(values: List[float]) -> float:
        """Calculate Gini coefficient for concentration measure."""
        if not values or sum(values) == 0:
            return 0.0
        
        sorted_values = sorted(values)
        n = len(sorted_values)
        index = np.arange(1, n + 1)
        
        return (2 * np.sum(index * sorted_values)) / (n * np.sum(sorted_values)) - (n + 1) / n
    
    async def extract_action_features(
        self,
        game_state: GameState,
        action_type: str,
        action_target: Optional[str] = None
    ) -> np.ndarray:
        """Extract features for a specific action.
        
        Args:
            game_state: Current game state
            action_type: Type of action (buy_joker, play_hand, etc.)
            action_target: Target of action (joker name, hand type, etc.)
            
        Returns:
            Feature vector for action evaluation
        """
        base_features = await self.extract_features(game_state)
        
        action_features = []
        
        if action_type == "buy_joker" and action_target:
            # Get joker synergy with current setup
            synergy_query = """
            MATCH (new:Joker {name: $new_joker})
            OPTIONAL MATCH (owned:Joker)-[s:SYNERGIZES_WITH]-(new)
            WHERE owned.name IN $current_jokers
            RETURN AVG(s.strength) as avg_synergy,
                   COUNT(s) as synergy_count,
                   new.cost as cost
            """
            
            result = await self.client.execute_query(
                synergy_query,
                {
                    "new_joker": action_target,
                    "current_jokers": game_state.jokers
                }
            )
            
            if result:
                action_features.append(result[0]["avg_synergy"] or 0.0)
                action_features.append(result[0]["synergy_count"] / len(game_state.jokers) if game_state.jokers else 0.0)
                action_features.append(result[0]["cost"] / game_state.money if game_state.money > 0 else 1.0)
            else:
                action_features.extend([0.0, 0.0, 1.0])
        
        elif action_type == "play_hand":
            # Features about hand strength
            action_features.extend([0.5, 0.5, 0.5])  # Placeholder
        
        else:
            # Default action features
            action_features.extend([0.0, 0.0, 0.0])
        
        return np.concatenate([base_features, action_features])


# Example usage
async def example_usage():
    """Example of using the feature extractor."""
    client = MemgraphClient()
    await client.connect()
    
    try:
        extractor = GraphFeatureExtractor(client)
        await extractor.initialize()
        
        # Example game state
        game_state = GameState(
            jokers=["Blueprint", "Brainstorm"],
            cards=[
                {"suit": "Hearts", "rank": "A", "enhancement": "none"},
                {"suit": "Hearts", "rank": "K", "enhancement": "bonus"},
                {"suit": "Diamonds", "rank": "Q", "enhancement": "none"},
                # ... more cards
            ],
            money=25,
            ante=3,
            hands_remaining=3,
            discards_remaining=2,
            hand_size=8,
            deck_size=45
        )
        
        # Extract features
        features = await extractor.extract_features(game_state)
        print(f"Extracted {len(features)} features")
        print(f"Feature vector shape: {features.shape}")
        
        # Extract action-specific features
        action_features = await extractor.extract_action_features(
            game_state,
            "buy_joker",
            "DNA"
        )
        print(f"Action features shape: {action_features.shape}")
        
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(example_usage())