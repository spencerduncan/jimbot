"""Example usage of DynamicObservationSpace for Balatro RL training."""

from jimbot.training.spaces.observation_space import (
    Card,
    CardEdition,
    CardEnhancement,
    CardRank,
    CardSeal,
    CardSuit,
    DynamicObservationSpace,
    Joker,
)


def example_basic_usage():
    """Basic usage example."""
    # Create observation space
    obs_space = DynamicObservationSpace()

    # Create sample game state
    game_state = {
        "hand": [
            Card(CardSuit.HEARTS, CardRank.ACE, CardEnhancement.MULT),
            Card(CardSuit.SPADES, CardRank.KING),
            Card(CardSuit.DIAMONDS, CardRank.SEVEN, CardEnhancement.BONUS),
            Card(CardSuit.CLUBS, CardRank.TWO),
            Card(CardSuit.HEARTS, CardRank.QUEEN, seal=CardSeal.GOLD_SEAL),
        ],
        "deck": [Card(CardSuit.HEARTS, CardRank(i)) for i in range(1, 14)]
        * 2,  # 26 cards
        "discard": [
            Card(CardSuit.SPADES, CardRank.THREE),
            Card(CardSuit.DIAMONDS, CardRank.JACK),
        ],
        "jokers": [
            Joker(joker_id=1, level=2, edition=CardEdition.FOIL, sell_value=8),
            Joker(joker_id=15, level=1, sell_value=5, extra_data={"mult": 1.5}),
            Joker(joker_id=42, level=3, edition=CardEdition.NEGATIVE, sell_value=12),
        ],
        "money": 45,
        "ante": 4,
        "round": 2,
        "blind_type": "Boss",
        "chips_required": 3000,
        "hands_left": 2,
        "discards_left": 1,
        "score": 1200,
        "mult": 15,
        "chips": 80,
        "selected_cards": [0, 2],  # Ace and Seven selected
        "in_blind": True,
        "selecting_cards": True,
        "max_joker_slots": 5,
    }

    # Encode the game state
    encoded = obs_space.encode(game_state)

    # Print information about the encoding
    print("Encoded observation keys:", list(encoded.keys()))
    print("\nSequence lengths:")
    for key, length in encoded["sequence_lengths"].items():
        print(f"  {key}: {length}")

    print("\nShapes:")
    for key, value in encoded.items():
        if key != "sequence_lengths" and hasattr(value, "shape"):
            print(f"  {key}: {value.shape}")

    # Check attention masks
    print(f"\nHand mask sum: {encoded['hand_mask'].sum()} (should be 5)")
    print(f"Deck mask sum: {encoded['deck_mask'].sum()} (should be 26)")
    print(f"Joker mask sum: {encoded['joker_mask'].sum()} (should be 3)")

    # Check selected cards encoding
    print("\nSelected cards (indices 0 and 2):")
    print(f"  Card 0 selected flag: {encoded['hand_features'][0, 7]}")
    print(f"  Card 2 selected flag: {encoded['hand_features'][2, 7]}")

    return encoded


def example_extreme_case():
    """Example with extreme game state (100+ cards)."""
    obs_space = DynamicObservationSpace()

    # Create a massive hand (150 cards - common in endless mode)
    massive_hand = []
    for suit in [CardSuit.HEARTS, CardSuit.DIAMONDS, CardSuit.CLUBS, CardSuit.SPADES]:
        for rank in range(1, 14):
            for _ in range(3):  # Multiple copies
                massive_hand.append(Card(suit, CardRank(rank)))

    # Add some special cards
    for _ in range(10):
        massive_hand.append(Card(CardSuit.NONE, CardRank.NONE, CardEnhancement.STONE))

    # Create 20 jokers
    many_jokers = [
        Joker(joker_id=i, level=(i % 5) + 1, sell_value=i * 2, position=i)
        for i in range(20)
    ]

    extreme_state = {
        "hand": massive_hand[:150],  # Cap at 150 for this example
        "deck": massive_hand[50:150],  # 100 cards in deck
        "discard": massive_hand[:50],  # 50 in discard
        "jokers": many_jokers,
        "money": 9999,
        "ante": 15,
        "round": 3,
        "blind_type": "Boss",
        "chips_required": 1000000,
        "hands_left": 10,
        "discards_left": 5,
        "score": 500000,
        "mult": 250,
        "chips": 2000,
        "in_blind": True,
    }

    encoded = obs_space.encode(extreme_state)

    print("\nExtreme case encoding:")
    print(f"Hand size: {encoded['sequence_lengths']['hand']} cards")
    print(f"Deck size: {encoded['sequence_lengths']['deck']} cards")
    print(f"Joker count: {encoded['sequence_lengths']['jokers']}")
    print(f"Hand mask sum: {encoded['hand_mask'].sum()}")
    print(f"Global features - Money: {encoded['global_features'][0]}")
    print(f"Global features - Chips required: {encoded['global_features'][6]}")

    return encoded


def example_shop_state():
    """Example of shop phase encoding."""
    obs_space = DynamicObservationSpace()

    shop_state = {
        "hand": [],  # No cards in hand during shop
        "deck": [Card(CardSuit(i % 4), CardRank((i % 13) + 1)) for i in range(52)],
        "discard": [],
        "jokers": [
            Joker(joker_id=5, level=1, sell_value=5),
            Joker(joker_id=8, level=2, sell_value=8, edition=CardEdition.HOLOGRAPHIC),
        ],
        "money": 15,
        "ante": 2,
        "round": 1,  # Between rounds
        "in_shop": True,
        "in_blind": False,
        "selecting_cards": False,
        "max_joker_slots": 5,
    }

    encoded = obs_space.encode(shop_state)

    print("\nShop phase encoding:")
    print(f"In shop flag: {encoded['global_features'][12]}")
    print(f"In blind flag: {encoded['global_features'][13]}")
    print(f"Hand is empty: {encoded['hand_mask'].sum() == 0}")

    return encoded


if __name__ == "__main__":
    print("=== Basic Usage Example ===")
    example_basic_usage()

    print("\n=== Extreme Case Example ===")
    example_extreme_case()

    print("\n=== Shop State Example ===")
    example_shop_state()
