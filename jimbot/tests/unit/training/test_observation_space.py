"""Unit tests for dynamic observation space."""

import pytest
import numpy as np
from typing import List

from jimbot.training.spaces.observation_space import (
    DynamicObservationSpace, Card, Joker, 
    CardSuit, CardRank, CardEnhancement, CardSeal, CardEdition
)


class TestDynamicObservationSpace:
    """Test cases for DynamicObservationSpace."""
    
    @pytest.fixture
    def obs_space(self):
        """Create observation space instance."""
        return DynamicObservationSpace()
    
    @pytest.fixture
    def sample_cards(self) -> List[Card]:
        """Create sample cards for testing."""
        return [
            Card(CardSuit.HEARTS, CardRank.ACE, CardEnhancement.MULT, CardSeal.GOLD_SEAL, CardEdition.FOIL),
            Card(CardSuit.SPADES, CardRank.KING, CardEnhancement.BONUS),
            Card(CardSuit.DIAMONDS, CardRank.SEVEN),
            Card(CardSuit.CLUBS, CardRank.TWO, CardEnhancement.GLASS, CardSeal.RED_SEAL),
            Card(CardSuit.NONE, CardRank.NONE, CardEnhancement.STONE),  # Stone card
        ]
    
    @pytest.fixture
    def sample_jokers(self) -> List[Joker]:
        """Create sample jokers for testing."""
        return [
            Joker(joker_id=1, level=3, edition=CardEdition.HOLOGRAPHIC, sell_value=8, position=0),
            Joker(joker_id=15, level=1, sell_value=5, position=1, extra_data={'mult': 0.5, 'chips': 30}),
            Joker(joker_id=42, level=2, edition=CardEdition.POLYCHROME, sell_value=10, position=2),
        ]
    
    @pytest.fixture
    def basic_game_state(self, sample_cards, sample_jokers):
        """Create a basic game state for testing."""
        return {
            'hand': sample_cards[:3],
            'deck': sample_cards[3:],
            'discard': [sample_cards[0]],
            'jokers': sample_jokers,
            'money': 25,
            'ante': 3,
            'round': 2,
            'blind_type': 'Big',
            'chips_required': 1500,
            'hands_left': 3,
            'discards_left': 2,
            'score': 500,
            'mult': 10,
            'chips': 50,
            'selected_cards': [0, 2],
            'in_blind': True,
            'selecting_cards': True,
            'max_joker_slots': 5
        }
    
    def test_initialization(self, obs_space):
        """Test observation space initialization."""
        assert obs_space.card_feature_size == 8
        assert obs_space.joker_feature_size == 10
        assert obs_space.global_feature_size == 20
        assert obs_space.MAX_HAND_SIZE == 200
        assert obs_space.MAX_DECK_SIZE == 200
        assert obs_space.MAX_JOKERS == 30
    
    def test_basic_encoding(self, obs_space, basic_game_state):
        """Test basic encoding functionality."""
        encoded = obs_space.encode(basic_game_state)
        
        # Check all required keys are present
        expected_keys = [
            'hand_features', 'hand_mask', 'deck_features', 'deck_mask',
            'discard_features', 'discard_mask', 'joker_features', 'joker_mask',
            'global_features', 'sequence_lengths'
        ]
        for key in expected_keys:
            assert key in encoded
        
        # Check shapes
        assert encoded['hand_features'].shape == (200, 8)
        assert encoded['hand_mask'].shape == (200,)
        assert encoded['deck_features'].shape == (200, 8)
        assert encoded['deck_mask'].shape == (200,)
        assert encoded['discard_features'].shape == (200, 8)
        assert encoded['discard_mask'].shape == (200,)
        assert encoded['joker_features'].shape == (30, 10)
        assert encoded['joker_mask'].shape == (30,)
        assert encoded['global_features'].shape == (20,)
        
        # Check sequence lengths
        assert encoded['sequence_lengths']['hand'] == 3
        assert encoded['sequence_lengths']['deck'] == 2
        assert encoded['sequence_lengths']['discard'] == 1
        assert encoded['sequence_lengths']['jokers'] == 3
    
    def test_card_encoding(self, obs_space, sample_cards):
        """Test card encoding with various attributes."""
        features, mask = obs_space._encode_cards(sample_cards, 10, location='hand', selected_indices={0, 2})
        
        # Check first card (Ace of Hearts with enhancements)
        assert np.isclose(features[0, 0], 0.0)  # Hearts = 0/4
        assert np.isclose(features[0, 1], 1/13)  # Ace = 1/13
        assert np.isclose(features[0, 2], 2/8)   # Mult enhancement
        assert np.isclose(features[0, 3], 1/4)   # Gold seal
        assert np.isclose(features[0, 4], 1/4)   # Foil edition
        assert features[0, 5] == 1.0  # In hand
        assert features[0, 7] == 1.0  # Selected
        
        # Check stone card (index 4)
        assert np.isclose(features[4, 0], 4/4)  # No suit = 4/4
        assert np.isclose(features[4, 1], 0)    # No rank = 0/13
        assert np.isclose(features[4, 2], 6/8)  # Stone enhancement
        
        # Check mask
        assert np.sum(mask) == 5  # 5 real cards
        assert np.all(mask[:5] == 1.0)
        assert np.all(mask[5:] == 0.0)
    
    def test_joker_encoding(self, obs_space, sample_jokers):
        """Test joker encoding with extra data."""
        features, mask = obs_space._encode_jokers(sample_jokers)
        
        # Check first joker
        assert np.isclose(features[0, 0], 1/150)  # Joker ID normalized
        assert np.isclose(features[0, 1], 3/10)   # Level 3
        assert np.isclose(features[0, 2], 2/4)    # Holographic
        assert np.isclose(features[0, 3], 8/20)   # Sell value
        assert features[0, 4] == 0.0              # Position 0
        
        # Check joker with extra data (index 1)
        assert np.isclose(features[1, 5], 0.5)    # Extra mult
        assert np.isclose(features[1, 6], 1.0)    # Extra chips (capped at 1.0)
        
        # Check mask
        assert np.sum(mask) == 3
        assert np.all(mask[:3] == 1.0)
        assert np.all(mask[3:] == 0.0)
    
    def test_global_state_encoding(self, obs_space, basic_game_state):
        """Test global state feature encoding."""
        features = obs_space._encode_global_state(basic_game_state)
        
        assert np.isclose(features[0], 25/100)    # Money
        assert np.isclose(features[1], 3/20)      # Ante
        assert np.isclose(features[2], 2/3)       # Round
        assert features[4] == 1.0                 # Big blind
        assert np.isclose(features[6], 1500/10000)  # Chips required
        assert np.isclose(features[7], 3/10)      # Hands left
        assert features[13] == 1.0                # In blind
        assert features[14] == 1.0                # Selecting cards
    
    def test_empty_game_state(self, obs_space):
        """Test encoding with empty game state."""
        empty_state = {
            'hand': [],
            'deck': [],
            'discard': [],
            'jokers': [],
            'money': 0,
            'ante': 1,
            'round': 1
        }
        
        encoded = obs_space.encode(empty_state)
        
        # All masks should be zero
        assert np.sum(encoded['hand_mask']) == 0
        assert np.sum(encoded['deck_mask']) == 0
        assert np.sum(encoded['discard_mask']) == 0
        assert np.sum(encoded['joker_mask']) == 0
        
        # Sequence lengths should be zero
        assert encoded['sequence_lengths']['hand'] == 0
        assert encoded['sequence_lengths']['deck'] == 0
        assert encoded['sequence_lengths']['discard'] == 0
        assert encoded['sequence_lengths']['jokers'] == 0
    
    def test_extreme_game_state(self, obs_space):
        """Test encoding with extreme game state (100+ cards)."""
        # Create 150 cards
        huge_hand = [
            Card(CardSuit(i % 4), CardRank((i % 13) + 1)) 
            for i in range(150)
        ]
        
        # Create 25 jokers
        many_jokers = [
            Joker(joker_id=i, level=1, position=i) 
            for i in range(25)
        ]
        
        extreme_state = {
            'hand': huge_hand,
            'deck': huge_hand[:100],
            'discard': huge_hand[:75],
            'jokers': many_jokers,
            'money': 9999,
            'ante': 20,
            'chips_required': 1000000,
            'hands_left': 15,
            'score': 500000
        }
        
        encoded = obs_space.encode(extreme_state)
        
        # Check that encoding handles the extreme case
        assert np.sum(encoded['hand_mask']) == 150
        assert np.sum(encoded['deck_mask']) == 100
        assert np.sum(encoded['discard_mask']) == 75
        assert np.sum(encoded['joker_mask']) == 25
        
        # Check normalization handles large values
        global_features = encoded['global_features']
        assert global_features[0] <= 2.0  # Money capped
        assert global_features[6] <= 10.0  # Chips required capped
    
    def test_dict_conversion(self, obs_space):
        """Test dictionary to object conversion."""
        card_dict = {
            'suit': 1,  # Diamonds
            'rank': 12,  # Queen
            'enhancement': 3,  # Wild
            'seal': 2,  # Blue seal
            'edition': 3,  # Polychrome
            'id': 42
        }
        
        card = obs_space._dict_to_card(card_dict)
        assert card.suit == CardSuit.DIAMONDS
        assert card.rank == CardRank.QUEEN
        assert card.enhancement == CardEnhancement.WILD
        assert card.seal == CardSeal.BLUE_SEAL
        assert card.edition == CardEdition.POLYCHROME
        assert card.id == 42
        
        joker_dict = {
            'joker_id': 10,
            'level': 5,
            'edition': 2,  # Holographic
            'sell_value': 15,
            'position': 3,
            'extra_data': {'mult': 2.5, 'trigger_count': 10}
        }
        
        joker = obs_space._dict_to_joker(joker_dict)
        assert joker.joker_id == 10
        assert joker.level == 5
        assert joker.edition == CardEdition.HOLOGRAPHIC
        assert joker.sell_value == 15
        assert joker.position == 3
        assert joker.extra_data['mult'] == 2.5
    
    def test_mixed_card_dict_input(self, obs_space):
        """Test encoding with mixed Card objects and dictionaries."""
        mixed_hand = [
            Card(CardSuit.HEARTS, CardRank.ACE),
            {'suit': 2, 'rank': 10, 'enhancement': 1},  # Dict representation
            Card(CardSuit.SPADES, CardRank.KING),
        ]
        
        game_state = {
            'hand': mixed_hand,
            'deck': [],
            'jokers': [],
            'money': 10
        }
        
        encoded = obs_space.encode(game_state)
        
        # Should handle both formats correctly
        assert np.sum(encoded['hand_mask']) == 3
        assert encoded['hand_features'][1, 0] == 2/4  # Clubs from dict
        assert encoded['hand_features'][1, 1] == 10/13  # Ten from dict
        assert encoded['hand_features'][1, 2] == 1/8  # Bonus enhancement from dict
    
    def test_observation_shape(self, obs_space):
        """Test get_observation_shape method."""
        shapes = obs_space.get_observation_shape()
        
        assert shapes['hand_features'] == (200, 8)
        assert shapes['hand_mask'] == (200,)
        assert shapes['deck_features'] == (200, 8)
        assert shapes['deck_mask'] == (200,)
        assert shapes['discard_features'] == (200, 8)
        assert shapes['discard_mask'] == (200,)
        assert shapes['joker_features'] == (30, 10)
        assert shapes['joker_mask'] == (30,)
        assert shapes['global_features'] == (20,)
    
    def test_padding_overflow(self, obs_space):
        """Test that sequences longer than max are truncated properly."""
        # Create 250 cards (more than MAX_HAND_SIZE)
        overflow_hand = [
            Card(CardSuit.HEARTS, CardRank.ACE) 
            for _ in range(250)
        ]
        
        game_state = {
            'hand': overflow_hand,
            'deck': [],
            'jokers': []
        }
        
        encoded = obs_space.encode(game_state)
        
        # Should truncate to MAX_HAND_SIZE
        assert np.sum(encoded['hand_mask']) == 200
        assert encoded['sequence_lengths']['hand'] == 250  # Original length preserved
        
    def test_special_card_types(self, obs_space):
        """Test encoding of special card types."""
        special_cards = [
            Card(CardSuit.NONE, CardRank.NONE, CardEnhancement.STONE),  # Stone
            Card(CardSuit.HEARTS, CardRank.ACE, CardEnhancement.GLASS, edition=CardEdition.NEGATIVE),
            Card(CardSuit.DIAMONDS, CardRank.KING, CardEnhancement.LUCKY, seal=CardSeal.PURPLE_SEAL),
        ]
        
        features, mask = obs_space._encode_cards(special_cards, 5, location='hand')
        
        # Stone card should have max suit/rank encoding (no suit/rank)
        assert features[0, 0] == 1.0  # NONE suit = 4/4
        assert features[0, 1] == 0.0  # NONE rank = 0/13
        assert np.isclose(features[0, 2], 6/8)  # Stone enhancement
        
        # Negative edition
        assert np.isclose(features[1, 4], 4/4)  # Negative = max edition value
        
        # Purple seal
        assert np.isclose(features[2, 3], 4/4)  # Purple = max seal value