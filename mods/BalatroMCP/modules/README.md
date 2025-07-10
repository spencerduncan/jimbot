# BalatroMCP Modules

This directory contains specialized modules for the BalatroMCP mod that handle specific aspects of game integration.

## Scoring Module (`scoring.lua`)

The scoring module tracks score changes during hand evaluation and sends detailed updates through the event aggregation system.

### Features

- **Hand Evaluation Tracking**: Monitors the complete scoring sequence from start to finish
- **Score Delta Tracking**: Records incremental score changes during evaluation
- **Joker Trigger Tracking**: Captures individual joker activations and their contributions
- **Mult/Chip Tracking**: Separately tracks multiplier and chip changes
- **Statistics Collection**: Maintains statistics about hands played and scores achieved

### Event Types

The scoring module sends the following event types through the aggregator:

1. **SCORING/HAND_EVAL_START**: Sent when a hand evaluation begins
   - Includes starting score, ante, round, and hand number

2. **SCORING/SCORE_UPDATE**: Sent for each score change during evaluation
   - Includes previous score, new score, delta, and context

3. **SCORING/JOKER_TRIGGER**: Sent when a joker contributes to scoring
   - Includes joker details and score contribution

4. **SCORING/MULT_UPDATE**: Sent when multiplier changes
   - Includes before/after values and source

5. **SCORING/CHIPS_UPDATE**: Sent when chip value changes
   - Includes before/after values and source

6. **SCORING/HAND_EVAL_COMPLETE**: Sent when hand evaluation completes
   - Includes final score, total delta, and joker trigger count
   - Has high priority to ensure immediate flush

### Integration

The scoring module is integrated into the main BalatroMCP mod through:

1. Initialization in `main.lua` component loading
2. Hook into `play_cards_from_highlighted` for hand evaluation
3. Hook into `Card.calculate_joker` for joker tracking
4. Automatic score updates via state change detection

### Usage

The module is automatically initialized and used by the main BalatroMCP mod. No manual configuration is required.

### Statistics

The module tracks:
- Total hands tracked
- Total score delta across all hands
- Maximum single hand score
- Average hand score
- Current scoring state

These statistics can be retrieved using the `get_stats()` method.