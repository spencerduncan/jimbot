"""Dynamic observation space for Balatro RL training.

This module provides a flexible observation space that can handle variable-sized
hands, decks, and joker collections with attention masking for sequence processing.
"""

from dataclasses import dataclass
from enum import IntEnum
from typing import Any, Optional

import numpy as np


class CardSuit(IntEnum):
    """Card suit encoding."""

    HEARTS = 0
    DIAMONDS = 1
    CLUBS = 2
    SPADES = 3
    NONE = 4  # For stone cards or no suit


class CardRank(IntEnum):
    """Card rank encoding."""

    ACE = 1
    TWO = 2
    THREE = 3
    FOUR = 4
    FIVE = 5
    SIX = 6
    SEVEN = 7
    EIGHT = 8
    NINE = 9
    TEN = 10
    JACK = 11
    QUEEN = 12
    KING = 13
    NONE = 0  # For stone cards or no rank


class CardEnhancement(IntEnum):
    """Card enhancement encoding."""

    NONE = 0
    BONUS = 1
    MULT = 2
    WILD = 3
    GLASS = 4
    STEEL = 5
    STONE = 6
    GOLD = 7
    LUCKY = 8


class CardSeal(IntEnum):
    """Card seal encoding."""

    NONE = 0
    GOLD_SEAL = 1
    RED_SEAL = 2
    BLUE_SEAL = 3
    PURPLE_SEAL = 4


class CardEdition(IntEnum):
    """Card edition encoding."""

    NONE = 0
    FOIL = 1
    HOLOGRAPHIC = 2
    POLYCHROME = 3
    NEGATIVE = 4


@dataclass
class Card:
    """Card representation with all attributes."""

    suit: CardSuit
    rank: CardRank
    enhancement: CardEnhancement = CardEnhancement.NONE
    seal: CardSeal = CardSeal.NONE
    edition: CardEdition = CardEdition.NONE
    id: Optional[int] = None  # Unique card ID for tracking


@dataclass
class Joker:
    """Joker representation."""

    joker_id: int  # Joker type ID
    level: int = 1
    edition: CardEdition = CardEdition.NONE
    sell_value: int = 0
    position: int = 0  # Position in joker list (left to right)
    extra_data: dict[str, float] = None  # Joker-specific data (e.g., mult accumulation)


class DynamicObservationSpace:
    """Dynamic observation space for Balatro with variable-length sequences.

    This class handles encoding of game states with variable numbers of cards
    and jokers, providing attention masks for sequence processing and supporting
    extreme game states (100+ card hands).
    """

    # Maximum sequence lengths for padding
    MAX_HAND_SIZE = 200  # Support extreme cases
    MAX_DECK_SIZE = 200
    MAX_JOKERS = 30
    MAX_DISCARD_SIZE = 200

    # Feature dimensions
    CARD_FEATURES = (
        8  # suit, rank, enhancement, seal, edition, location, selected, playable
    )
    JOKER_FEATURES = (
        10  # id, level, edition, sell_value, position, + 5 extra data slots
    )
    GLOBAL_FEATURES = (
        20  # money, ante, round, blind_type, chips_required, hands_left, etc.
    )

    def __init__(self):
        """Initialize the dynamic observation space."""
        self.card_feature_size = self.CARD_FEATURES
        self.joker_feature_size = self.JOKER_FEATURES
        self.global_feature_size = self.GLOBAL_FEATURES

    def encode(self, game_state: dict[str, Any]) -> dict[str, np.ndarray]:
        """Encode game state into observation tensors with attention masks.

        Args:
            game_state: Dictionary containing:
                - hand: List of cards in hand
                - deck: List of cards in deck
                - discard: List of cards in discard pile
                - jokers: List of active jokers
                - money: Current money
                - ante: Current ante
                - round: Current round in ante
                - blind_type: Type of blind (Small, Big, Boss)
                - chips_required: Chips needed to beat blind
                - hands_left: Hands remaining
                - discards_left: Discards remaining
                - score: Current score
                - mult: Current mult
                - chips: Current chips
                - selected_cards: List of selected card indices

        Returns:
            Dictionary with:
                - hand_features: (MAX_HAND_SIZE, CARD_FEATURES) tensor
                - hand_mask: (MAX_HAND_SIZE,) attention mask
                - deck_features: (MAX_DECK_SIZE, CARD_FEATURES) tensor
                - deck_mask: (MAX_DECK_SIZE,) attention mask
                - discard_features: (MAX_DISCARD_SIZE, CARD_FEATURES) tensor
                - discard_mask: (MAX_DISCARD_SIZE,) attention mask
                - joker_features: (MAX_JOKERS, JOKER_FEATURES) tensor
                - joker_mask: (MAX_JOKERS,) attention mask
                - global_features: (GLOBAL_FEATURES,) tensor
                - sequence_lengths: Dict with actual lengths for each sequence
        """
        # Extract components
        hand = game_state.get("hand", [])
        deck = game_state.get("deck", [])
        discard = game_state.get("discard", [])
        jokers = game_state.get("jokers", [])
        selected_indices = set(game_state.get("selected_cards", []))

        # Encode card sequences
        hand_features, hand_mask = self._encode_cards(
            hand, self.MAX_HAND_SIZE, location="hand", selected_indices=selected_indices
        )
        deck_features, deck_mask = self._encode_cards(
            deck, self.MAX_DECK_SIZE, location="deck"
        )
        discard_features, discard_mask = self._encode_cards(
            discard, self.MAX_DISCARD_SIZE, location="discard"
        )

        # Encode jokers
        joker_features, joker_mask = self._encode_jokers(jokers)

        # Encode global features
        global_features = self._encode_global_state(game_state)

        # Track actual sequence lengths
        sequence_lengths = {
            "hand": len(hand),
            "deck": len(deck),
            "discard": len(discard),
            "jokers": len(jokers),
        }

        return {
            "hand_features": hand_features,
            "hand_mask": hand_mask,
            "deck_features": deck_features,
            "deck_mask": deck_mask,
            "discard_features": discard_features,
            "discard_mask": discard_mask,
            "joker_features": joker_features,
            "joker_mask": joker_mask,
            "global_features": global_features,
            "sequence_lengths": sequence_lengths,
        }

    def _encode_cards(
        self,
        cards: list[Card],
        max_length: int,
        location: str = "unknown",
        selected_indices: Optional[set] = None,
    ) -> tuple[np.ndarray, np.ndarray]:
        """Encode a list of cards with padding and attention mask.

        Args:
            cards: List of Card objects
            max_length: Maximum sequence length for padding
            location: Card location ('hand', 'deck', 'discard')
            selected_indices: Set of selected card indices (for hand only)

        Returns:
            features: (max_length, CARD_FEATURES) tensor
            mask: (max_length,) attention mask (1 for real cards, 0 for padding)
        """
        features = np.zeros((max_length, self.CARD_FEATURES), dtype=np.float32)
        mask = np.zeros(max_length, dtype=np.float32)

        if selected_indices is None:
            selected_indices = set()

        # Encode each card
        for i, card in enumerate(cards[:max_length]):
            if isinstance(card, dict):
                # Convert dict to Card object if needed
                card = self._dict_to_card(card)

            # Basic features
            features[i, 0] = card.suit.value / 4.0  # Normalize to [0, 1]
            features[i, 1] = card.rank.value / 13.0  # Normalize to [0, 1]
            features[i, 2] = card.enhancement.value / 8.0
            features[i, 3] = card.seal.value / 4.0
            features[i, 4] = card.edition.value / 4.0

            # Location encoding (one-hot)
            if location == "hand":
                features[i, 5] = 1.0
            elif location == "deck":
                features[i, 6] = 0.5
            elif location == "discard":
                features[i, 6] = 1.0

            # Selected flag (for cards in hand)
            if location == "hand" and i in selected_indices:
                features[i, 7] = 1.0

            # Mark as valid card
            mask[i] = 1.0

        return features, mask

    def _encode_jokers(self, jokers: list[Joker]) -> tuple[np.ndarray, np.ndarray]:
        """Encode jokers with padding and attention mask.

        Args:
            jokers: List of Joker objects

        Returns:
            features: (MAX_JOKERS, JOKER_FEATURES) tensor
            mask: (MAX_JOKERS,) attention mask
        """
        features = np.zeros((self.MAX_JOKERS, self.JOKER_FEATURES), dtype=np.float32)
        mask = np.zeros(self.MAX_JOKERS, dtype=np.float32)

        for i, joker in enumerate(jokers[: self.MAX_JOKERS]):
            if isinstance(joker, dict):
                # Convert dict to Joker object if needed
                joker = self._dict_to_joker(joker)

            # Basic features
            features[i, 0] = (
                joker.joker_id / 150.0
            )  # Normalize assuming ~150 joker types
            features[i, 1] = min(joker.level / 10.0, 1.0)  # Cap at level 10
            features[i, 2] = joker.edition.value / 4.0
            features[i, 3] = joker.sell_value / 20.0  # Normalize sell value
            features[i, 4] = (
                joker.position / (self.MAX_JOKERS - 1) if self.MAX_JOKERS > 1 else 0
            )

            # Extra data (joker-specific features)
            if joker.extra_data:
                extra_values = list(joker.extra_data.values())[:5]
                for j, val in enumerate(extra_values):
                    features[i, 5 + j] = min(max(val, -1.0), 1.0)  # Clamp to [-1, 1]

            mask[i] = 1.0

        return features, mask

    def _encode_global_state(self, game_state: dict[str, Any]) -> np.ndarray:
        """Encode global game state features.

        Args:
            game_state: Game state dictionary

        Returns:
            features: (GLOBAL_FEATURES,) tensor
        """
        features = np.zeros(self.GLOBAL_FEATURES, dtype=np.float32)

        # Economic features
        features[0] = min(game_state.get("money", 0) / 100.0, 2.0)  # Cap at 200

        # Progression features
        features[1] = game_state.get("ante", 1) / 20.0  # Normalize to ~20 antes
        features[2] = game_state.get("round", 1) / 3.0  # 3 rounds per ante

        # Blind type (one-hot)
        blind_type = game_state.get("blind_type", "Small")
        if blind_type == "Small":
            features[3] = 1.0
        elif blind_type == "Big":
            features[4] = 1.0
        elif blind_type == "Boss":
            features[5] = 1.0

        # Requirements and resources
        features[6] = min(game_state.get("chips_required", 0) / 10000.0, 10.0)
        features[7] = game_state.get("hands_left", 0) / 10.0
        features[8] = game_state.get("discards_left", 0) / 10.0

        # Current scoring state
        features[9] = min(game_state.get("score", 0) / 10000.0, 10.0)
        features[10] = min(game_state.get("mult", 0) / 100.0, 5.0)
        features[11] = min(game_state.get("chips", 0) / 1000.0, 5.0)

        # Game phase indicators
        features[12] = 1.0 if game_state.get("in_shop", False) else 0.0
        features[13] = 1.0 if game_state.get("in_blind", False) else 0.0
        features[14] = 1.0 if game_state.get("selecting_cards", False) else 0.0

        # Deck statistics
        features[15] = len(game_state.get("deck", [])) / self.MAX_DECK_SIZE
        features[16] = len(game_state.get("hand", [])) / self.MAX_HAND_SIZE
        features[17] = len(game_state.get("discard", [])) / self.MAX_DISCARD_SIZE

        # Joker slots
        features[18] = len(game_state.get("jokers", [])) / self.MAX_JOKERS
        features[19] = game_state.get("max_joker_slots", 5) / 10.0

        return features

    def _dict_to_card(self, card_dict: dict[str, Any]) -> Card:
        """Convert dictionary representation to Card object."""
        return Card(
            suit=CardSuit(card_dict.get("suit", CardSuit.NONE)),
            rank=CardRank(card_dict.get("rank", CardRank.NONE)),
            enhancement=CardEnhancement(
                card_dict.get("enhancement", CardEnhancement.NONE)
            ),
            seal=CardSeal(card_dict.get("seal", CardSeal.NONE)),
            edition=CardEdition(card_dict.get("edition", CardEdition.NONE)),
            id=card_dict.get("id"),
        )

    def _dict_to_joker(self, joker_dict: dict[str, Any]) -> Joker:
        """Convert dictionary representation to Joker object."""
        return Joker(
            joker_id=joker_dict.get("joker_id", 0),
            level=joker_dict.get("level", 1),
            edition=CardEdition(joker_dict.get("edition", CardEdition.NONE)),
            sell_value=joker_dict.get("sell_value", 0),
            position=joker_dict.get("position", 0),
            extra_data=joker_dict.get("extra_data", {}),
        )

    def get_observation_shape(self) -> dict[str, tuple[int, ...]]:
        """Get the shape of each observation component.

        Returns:
            Dictionary mapping component names to their shapes
        """
        return {
            "hand_features": (self.MAX_HAND_SIZE, self.CARD_FEATURES),
            "hand_mask": (self.MAX_HAND_SIZE,),
            "deck_features": (self.MAX_DECK_SIZE, self.CARD_FEATURES),
            "deck_mask": (self.MAX_DECK_SIZE,),
            "discard_features": (self.MAX_DISCARD_SIZE, self.CARD_FEATURES),
            "discard_mask": (self.MAX_DISCARD_SIZE,),
            "joker_features": (self.MAX_JOKERS, self.JOKER_FEATURES),
            "joker_mask": (self.MAX_JOKERS,),
            "global_features": (self.GLOBAL_FEATURES,),
        }
