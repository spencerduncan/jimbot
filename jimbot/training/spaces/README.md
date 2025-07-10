# Dynamic Observation Space for Balatro RL

This module provides a flexible observation space for Balatro reinforcement learning that can handle variable-sized game states.

## Features

- **Variable-length sequences**: Supports hands, decks, and joker collections of any size
- **Attention masking**: Provides masks for sequence processing in neural networks
- **Extreme game states**: Handles 100+ card hands common in endless mode
- **Efficient encoding**: Minimal overhead with optimized numpy operations
- **Comprehensive card features**: Encodes suit, rank, enhancement, seal, and edition
- **Rich joker encoding**: Supports joker-specific data and positioning

## Usage

```python
from jimbot.training.spaces.observation_space import (
    DynamicObservationSpace, Card, Joker,
    CardSuit, CardRank, CardEnhancement, CardSeal, CardEdition
)

# Create observation space
obs_space = DynamicObservationSpace()

# Create game state
game_state = {
    'hand': [
        Card(CardSuit.HEARTS, CardRank.ACE, CardEnhancement.MULT),
        Card(CardSuit.SPADES, CardRank.KING),
    ],
    'deck': [Card(CardSuit.DIAMONDS, CardRank.SEVEN) for _ in range(52)],
    'discard': [],
    'jokers': [
        Joker(joker_id=1, level=2, edition=CardEdition.FOIL),
        Joker(joker_id=15, level=1, extra_data={'mult': 1.5}),
    ],
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
    'selected_cards': [0],  # First card selected
    'in_blind': True,
    'selecting_cards': True,
}

# Encode the game state
encoded = obs_space.encode(game_state)

# Access encoded tensors
hand_features = encoded['hand_features']  # (200, 8) tensor
hand_mask = encoded['hand_mask']         # (200,) attention mask
global_features = encoded['global_features']  # (20,) tensor
```

## Encoding Details

### Card Features (8 dimensions)
1. **Suit** (0-1): Normalized suit value (Hearts=0, Diamonds=0.25, Clubs=0.5, Spades=0.75, None=1)
2. **Rank** (0-1): Normalized rank value (Ace=1/13, ..., King=13/13, None=0)
3. **Enhancement** (0-1): Normalized enhancement type
4. **Seal** (0-1): Normalized seal type
5. **Edition** (0-1): Normalized edition type
6. **Location** (0-1): One-hot encoding for hand/deck/discard
7. **Selected** (0/1): Whether card is selected (hand only)
8. **Playable** (0/1): Reserved for future use

### Joker Features (10 dimensions)
1. **ID** (0-1): Normalized joker type ID
2. **Level** (0-1): Normalized level (capped at 10)
3. **Edition** (0-1): Normalized edition type
4. **Sell Value** (0-1): Normalized sell value
5. **Position** (0-1): Normalized position in joker list
6-10. **Extra Data**: Joker-specific features (e.g., accumulated mult)

### Global Features (20 dimensions)
1. **Money** (0-2): Normalized money (capped at 200)
2. **Ante** (0-1): Normalized ante level
3. **Round** (0-1): Normalized round within ante
4-6. **Blind Type**: One-hot encoding (Small, Big, Boss)
7. **Chips Required** (0-10): Normalized chip requirement
8. **Hands Left** (0-1): Normalized hands remaining
9. **Discards Left** (0-1): Normalized discards remaining
10. **Score** (0-10): Normalized current score
11. **Mult** (0-5): Normalized current multiplier
12. **Chips** (0-5): Normalized current chips
13. **In Shop** (0/1): Whether in shop phase
14. **In Blind** (0/1): Whether playing blind
15. **Selecting Cards** (0/1): Whether selecting cards
16. **Deck Size** (0-1): Normalized deck size
17. **Hand Size** (0-1): Normalized hand size
18. **Discard Size** (0-1): Normalized discard pile size
19. **Joker Count** (0-1): Normalized active joker count
20. **Max Joker Slots** (0-1): Normalized maximum joker slots

## Maximum Sequence Lengths

- **Hand**: 200 cards (supports extreme endless mode scenarios)
- **Deck**: 200 cards
- **Discard**: 200 cards
- **Jokers**: 30 jokers

## Integration with Ray RLlib

The `BalatroEnv` class uses this observation space to provide dynamic encoding:

```python
from jimbot.training.environments.balatro_env import BalatroEnv

env = BalatroEnv(config)
obs = env.reset()

# obs contains:
# - hand_features, hand_mask
# - deck_features, deck_mask
# - discard_features, discard_mask
# - joker_features, joker_mask
# - global_features
# - memgraph_embedding
# - action_mask
```

## Performance Considerations

- Encoding is optimized with numpy operations
- Attention masks enable efficient batch processing
- Padding overhead is minimal due to sparse masking
- Supports GPU tensor conversion for neural networks

## Testing

Run unit tests:
```bash
python -m pytest jimbot/tests/unit/training/test_observation_space.py -v
```

## Future Enhancements

- [ ] Add consumable card encoding
- [ ] Support voucher state encoding
- [ ] Add planet card effects to global state
- [ ] Encode spectral card availability
- [ ] Add boss blind special conditions