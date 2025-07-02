# Bug: Game states reported as UNKNOWN_STATE_1, UNKNOWN_STATE_2

## Description
The game_state_extractor.lua module is reporting game states as "UNKNOWN_STATE_1", "UNKNOWN_STATE_2" etc instead of meaningful state names like "PLAYING", "HAND_EVAL", etc.

## Current Code Issue
In game_state_extractor.lua get_game_phase() function:
```lua
else
    -- Log the numeric state for debugging
    return "UNKNOWN_STATE_" .. tostring(G.STATE)
end
```

## Expected Behavior
All game states should be properly identified with meaningful names like:
- PLAYING
- HAND_EVAL  
- ROUND_EVAL
- SHOP
- BLIND_SELECT

## Actual Behavior
States are reported as UNKNOWN_STATE_1, UNKNOWN_STATE_2 which provides no useful information about what state the game is actually in.

## Suggested Fix
1. Add more state checks in get_game_phase()
2. Map numeric state values to their proper names
3. Log unknown states with more debugging info to identify them

## Priority
Medium - This makes debugging and understanding game flow difficult