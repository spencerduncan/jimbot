# Game State Extractor Fix - Issue #60

## Problem
The game_state_extractor.lua module was reporting game states as "UNKNOWN_STATE_1", "UNKNOWN_STATE_2" etc instead of meaningful state names like "DECK_SELECT", "STAKE_SELECT", etc.

## Root Cause
The `get_game_phase()` function was missing mappings for two game states:
- `DECK_SELECT` (state value 1)
- `STAKE_SELECT` (state value 2)

These states exist in the game but were not included in the state checking logic.

## Solution
Updated the `get_game_phase()` function to include all 14 known game states:
1. MENU (0)
2. DECK_SELECT (1) - **Added**
3. STAKE_SELECT (2) - **Added**
4. BLIND_SELECT (3)
5. SHOP (4)
6. PLAYING (5)
7. ROUND_EVAL (6)
8. GAME_OVER (7)
9. TAROT_PACK (8)
10. PLANET_PACK (9)
11. SPECTRAL_PACK (10)
12. STANDARD_PACK (11)
13. BUFFOON_PACK (12)
14. SMODS_BOOSTER_OPENED (13) → BOOSTER_PACK

Additionally, improved the unknown state handling to log warnings when unrecognized states are encountered.

## Testing Approach

### Unit Tests (test_game_state_extractor.lua)
- **test_all_known_states**: Verifies all 14 states are correctly identified
- **test_unknown_states**: Ensures unknown states are reported with numeric values
- **test_nil_state_handling**: Tests graceful handling of nil G or G.STATE
- **test_state_extraction_includes_phase**: Verifies phase is included in extracted state
- **test_available_actions_by_phase**: Tests that available actions match the game phase
- **test_edge_cases**: Tests handling of invalid state values (strings, negatives, floats)

### Integration Tests (test_game_state_integration.lua)
- **test_playing_state_full_extraction**: Full state extraction during gameplay
- **test_shop_state_extraction**: Shop state with items available
- **test_menu_state_extraction**: Menu state when not in game
- **test_state_transitions**: All state transitions report correctly
- **test_available_actions_comprehensive**: Actions for all game states
- **test_highlighted_cards_extraction**: Card selection tracking
- **test_unknown_state_logging**: Warning messages for unknown states

## Test Results
All tests pass successfully:
- Unit Tests: 6/6 passed
- Integration Tests: 7/7 passed

## Files Changed
- `/mods/BalatroMCP/game_state_extractor.lua` - Added missing state mappings and improved logging

## Files Created
- `/tests/test_game_state_extractor.lua` - Unit test suite
- `/tests/test_game_state_integration.lua` - Integration test suite
- `/tests/run_all_tests.lua` - Master test runner
- `/tests/README_game_state_fix.md` - This documentation

## How to Run Tests
```bash
# Run unit tests only
lua tests/test_game_state_extractor.lua

# Run integration tests only
lua tests/test_game_state_integration.lua

# Run all tests
lua tests/run_all_tests.lua
```

## Verification
The fix ensures that:
1. All known game states are properly identified with meaningful names
2. Unknown states are still reported but with clear numeric identifiers
3. Warning messages are logged for debugging unknown states
4. The system remains robust and doesn't crash on unexpected states