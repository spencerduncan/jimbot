# BalatroMCP Test Suite

## Overview

This test suite provides comprehensive testing for the BalatroMCP mod, with a
specific focus on Issue #59 - the shop navigation bug where the "score at least"
message incorrectly reappears when navigating to the shop after winning a blind.

## Test Structure

```
tests/
├── test_helper.lua                              # Test framework and mocking utilities
├── run_tests.lua                               # Test runner script
├── unit/                                       # Unit tests
│   └── test_action_executor_shop_navigation.lua # Tests for shop navigation bug fix
└── integration/                                # Integration tests
    └── test_round_eval_to_shop_flow.lua       # Full flow tests for state transitions
```

## Running Tests

### Run All Tests

```bash
lua tests/run_tests.lua
```

### Run Individual Test Suite

```bash
# Run unit tests only
lua tests/unit/test_action_executor_shop_navigation.lua

# Run integration tests only
lua tests/integration/test_round_eval_to_shop_flow.lua
```

## Test Coverage for Issue #59

### Unit Tests (10 tests)

1. **navigate_menu does not call evaluate_round** - Verifies the main bug fix
2. **Shop function priority order** - Tests go_to_shop → to_shop → skip_to_shop
3. **Fallback mechanisms** - Tests graceful degradation when functions
   unavailable
4. **Continue button usage** - Tests non-shop navigation in ROUND_EVAL
5. **go_to_shop direct navigation** - Tests the primary shop navigation function
6. **navigate_menu fallback** - Tests when direct functions unavailable
7. **No evaluate_round in any scenario** - Comprehensive verification
8. **Non-ROUND_EVAL state handling** - Tests other game states
9. **Logging verification** - Ensures proper debug information
10. **Multiple navigation attempts** - Tests rapid clicking scenarios

### Integration Tests (8 tests)

1. **Complete win-to-shop flow** - Full game flow without UI bug
2. **Multiple navigation attempts** - Simulates user clicking multiple times
3. **Queued actions** - Tests asynchronous action processing
4. **Full UI state transitions** - Tests with complete UI state
5. **Error recovery** - Graceful handling of missing functions
6. **All navigation paths** - Tests every possible way to reach shop
7. **Auto-play mode** - Tests AI-controlled navigation
8. **Rapid state changes** - Stress test with quick state transitions

## Key Test Assertions

The tests verify that:

- `G.FUNCS.evaluate_round()` is NEVER called when navigating to shop from
  ROUND_EVAL
- The shop is reached successfully through various navigation paths
- UI elements behave correctly (no "score at least" message reappearing)
- The fix works in both manual and auto-play modes
- Error conditions are handled gracefully

## Mock Framework

The test helper provides:

- Function mocking with call tracking
- Global state mocking (G, love, BalatroMCP)
- Assertion helpers (assert_equal, assert_called, assert_not_called, etc.)
- Test isolation (mocks reset between tests)

## Adding New Tests

1. Create a new test file in the appropriate directory (unit/ or integration/)
2. Include the test helper: `local TestHelper = require("tests.test_helper")`
3. Use the test function: `test("description", function() ... end)`
4. Add the test file path to `test_suites` in run_tests.lua

Example:

```lua
local TestHelper = require("tests.test_helper")
local test = TestHelper.test

TestHelper.run_suite("My New Test Suite")

test("my new test", function()
    -- Arrange
    local ActionExecutor = load_action_executor()

    -- Act
    ActionExecutor:some_function()

    -- Assert
    TestHelper.assert_equal(result, expected)
end)

TestHelper.report()
```

## Continuous Integration

These tests should be run:

- Before committing changes to action_executor.lua
- As part of PR checks
- After merging PRs that affect game navigation
- As part of release validation

## Test Maintenance

When modifying action_executor.lua:

1. Run existing tests to ensure no regressions
2. Add new tests for new functionality
3. Update tests if behavior intentionally changes
4. Keep test names descriptive and documentation current
