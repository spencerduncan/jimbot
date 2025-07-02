# Bug: "Score at least" message reappears after winning blind

## Description
When navigating from ROUND_EVAL state after winning a blind, attempting to go to the shop causes the "score at least" message to reappear, which is not normal game behavior.

## Steps to Reproduce
1. Win a blind (complete scoring requirement)
2. Enter ROUND_EVAL state
3. Send go_to_shop or navigate_menu commands
4. The "score at least" UI element reappears incorrectly

## Expected Behavior
After winning a blind and entering ROUND_EVAL, navigation commands should proceed to the shop without re-displaying scoring requirements.

## Actual Behavior
The scoring requirement UI ("score at least X chips") reappears, suggesting the mod is incorrectly triggering game state changes.

## Possible Cause
The action_executor.lua navigate_menu function may be calling incorrect game functions or the mod may be interfering with normal state transitions.

## Priority
High - This breaks normal game flow and prevents progression