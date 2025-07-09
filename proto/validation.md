# Protocol Buffer Schema Validation Rules

This document defines the validation rules for Balatro event messages to ensure data integrity and consistency.

## General Validation Rules

### Required Fields
- All events MUST have:
  - `event_id`: Non-empty, unique within session
  - `timestamp`: Valid timestamp
  - `event_type`: Non-empty string
  - `source`: Identifies the component that generated the event

### ID Format
- Event IDs: `evt_<timestamp>_<random>`
- Action IDs: `act_<timestamp>_<random>`
- Trigger IDs: `trig_<timestamp>_<sequence>`
- Card IDs: `c_<suit>_<rank>` or unique identifier
- Joker IDs: `j_<name>_<instance>` or unique identifier

## Game State Validation

### Card Validation
```python
VALID_SUITS = ["Hearts", "Diamonds", "Clubs", "Spades"]
VALID_RANKS = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]
VALID_ENHANCEMENTS = ["glass", "steel", "gold", "lucky", "mult", "bonus", "stone", "wild", ""]
VALID_SEALS = ["gold", "red", "blue", "purple", ""]
VALID_EDITIONS = ["foil", "holographic", "polychrome", "negative", ""]
```

### Hand Type Validation
```python
VALID_HAND_TYPES = [
    "high_card", "pair", "two_pair", "three_of_a_kind",
    "straight", "flush", "full_house", "four_of_a_kind",
    "straight_flush", "flush_house", "flush_five", "five_of_a_kind"
]
```

### Game Phase Validation
```python
VALID_PHASES = [
    "SELECT_BLIND", "PLAY_HAND", "SCORING", "SHOP",
    "BOOSTER_PACK", "ROUND_END", "GAME_OVER"
]
```

## Action Validation

### Play Hand Action
- Must have 1-5 card IDs
- All card IDs must exist in current hand
- Game phase must be PLAY_HAND
- Cards cannot be debuffed

### Discard Action
- Must have 1-5 card IDs
- All card IDs must exist in current hand
- Must have discards remaining
- Game phase must be PLAY_HAND

### Shop Action
- BUY: Item must exist in shop, have sufficient money
- SELL: Item must be owned (joker/consumable)
- REROLL: Must have rerolls remaining, sufficient money
- Game phase must be SHOP

### Use Consumable Action
- Consumable must exist in inventory
- Target cards must be valid for consumable type
- Some consumables require specific game phases

## Trigger Validation

### Trigger Types
```python
VALID_TRIGGER_TYPES = [
    "played", "scored", "held", "discarded",
    "bought", "sold", "reorder", "end_round",
    "retrigger", "copy", "destroy"
]
```

### Effect Types
```python
VALID_EFFECT_TYPES = [
    "add_mult", "x_mult", "add_chips", "x_chips",
    "add_money", "add_hand", "add_discard",
    "retrigger", "destroy_card", "enhance_card",
    "create_card", "copy_card", "transform"
]
```

### Trigger Context Rules
- `played_cards` and `scored_cards` must be subsets of cards in play
- `repetition` must be >= 0
- `hand_type` must be valid if cards were scored

## Numerical Constraints

### Score Values
- Chips: >= 0, <= 2^63-1
- Mult: >= 0.0, typically <= 1000000.0
- Money: >= 0, typically <= 999999

### Game Progression
- Ante: >= 1, <= 39 (or higher for endless mode)
- Round: >= 1
- Hands remaining: >= 0
- Discards remaining: >= 0

### Shop Constraints
- Item cost: >= 0
- Reroll cost: >= 0
- Rerolls remaining: >= 0

## State Consistency Rules

### Hand Management
- Sum of cards in (hand + played + discarded) <= deck size
- No duplicate card IDs in active play
- Card positions must be unique within hand

### Joker Management
- Maximum 5 jokers (unless voucher modifies)
- Joker positions must be unique
- Joker parameters must match expected values

### Resource Management
- Money cannot go negative
- Consumable slots respect limits
- Vouchers are unique (no duplicates)

## Cascade Validation

### Trigger Chains
- No circular dependencies in trigger chains
- Cascade depth typically <= 20
- Each trigger in chain must have valid cause

### Timing Constraints
- End time >= start time
- Execution time reasonable (< 5 seconds)

## Error Handling

### Required Error Information
```json
{
  "error_code": "INVALID_ACTION",
  "error_message": "Cannot play 6 cards (maximum 5)",
  "context": {
    "action_type": "play_hand",
    "card_count": 6,
    "max_allowed": 5
  }
}
```

### Common Error Codes
- `INVALID_CARD_ID`: Referenced card doesn't exist
- `INSUFFICIENT_FUNDS`: Not enough money for action
- `INVALID_PHASE`: Action not allowed in current phase
- `DEBUFFED_CARD`: Cannot use debuffed card
- `LIMIT_EXCEEDED`: Too many items of type

## Validation Implementation Example

```python
def validate_game_state_event(event):
    errors = []
    
    # Validate cards
    for card in event.hand:
        if card.suit not in VALID_SUITS:
            errors.append(f"Invalid suit: {card.suit}")
        if card.rank not in VALID_RANKS:
            errors.append(f"Invalid rank: {card.rank}")
        if card.enhancement and card.enhancement not in VALID_ENHANCEMENTS:
            errors.append(f"Invalid enhancement: {card.enhancement}")
    
    # Validate jokers
    if len(event.jokers) > 5 and "Joker Stencil" not in event.vouchers:
        errors.append(f"Too many jokers: {len(event.jokers)}")
    
    # Validate game progression
    if event.ante < 1:
        errors.append(f"Invalid ante: {event.ante}")
    
    return errors
```

## Performance Considerations

### Validation Performance
- Basic field validation: < 1ms
- Full state validation: < 10ms
- Batch validation: Process up to 1000 events/second

### Optimization Tips
- Cache validation results for immutable data
- Use bit flags for quick checks
- Validate only changed fields in updates