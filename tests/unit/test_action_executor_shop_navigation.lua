-- Unit tests for ActionExecutor shop navigation bug (Issue #59)
-- Tests that "score at least" message doesn't reappear when navigating to shop

package.path = package.path .. ";../../?.lua"

local TestHelper = require("tests.test_helper")
local test = TestHelper.test
local assert_equal = TestHelper.assert_equal
local assert_called = TestHelper.assert_called
local assert_not_called = TestHelper.assert_not_called
local mock_function = TestHelper.mock_function

-- Load the module under test
local function load_action_executor()
    TestHelper.create_mock_globals()
    return dofile("mods/BalatroMCP/action_executor.lua")
end

TestHelper.run_suite("ActionExecutor Shop Navigation Bug Tests")

-- Test 1: navigate_menu should NOT call evaluate_round when navigating to shop from ROUND_EVAL
test(
    "navigate_menu does not call evaluate_round when action is shop in ROUND_EVAL state",
    function()
        local ActionExecutor = load_action_executor()
        ActionExecutor:init()

        -- Set up state
        G.STATE = G.STATES.ROUND_EVAL

        -- Mock the functions
        G.FUNCS.evaluate_round = mock_function("evaluate_round")
        G.FUNCS.go_to_shop = mock_function("go_to_shop")

        -- Call navigate_menu with shop action
        ActionExecutor:navigate_menu({ action = "shop" })

        -- Assert evaluate_round was NOT called (this is the bug fix)
        assert_not_called("evaluate_round")

        -- Assert go_to_shop was called
        assert_called("go_to_shop", 1)
    end
)

-- Test 2: navigate_menu should try shop functions in correct order
test("navigate_menu tries shop functions in priority order", function()
    local ActionExecutor = load_action_executor()
    ActionExecutor:init()

    G.STATE = G.STATES.ROUND_EVAL

    -- Test priority 1: go_to_shop
    G.FUNCS = {
        go_to_shop = mock_function("go_to_shop"),
        to_shop = mock_function("to_shop"),
        skip_to_shop = mock_function("skip_to_shop"),
    }

    ActionExecutor:navigate_menu({ action = "shop" })

    assert_called("go_to_shop", 1)
    assert_not_called("to_shop")
    assert_not_called("skip_to_shop")
end)

-- Test 3: navigate_menu falls back to to_shop if go_to_shop not available
test("navigate_menu falls back to to_shop when go_to_shop not available", function()
    local ActionExecutor = load_action_executor()
    ActionExecutor:init()

    G.STATE = G.STATES.ROUND_EVAL

    -- Only to_shop available
    G.FUNCS = {
        to_shop = mock_function("to_shop"),
        skip_to_shop = mock_function("skip_to_shop"),
    }

    ActionExecutor:navigate_menu({ action = "shop" })

    assert_called("to_shop", 1)
    assert_not_called("skip_to_shop")
end)

-- Test 4: navigate_menu falls back to skip_to_shop as last resort
test("navigate_menu falls back to skip_to_shop when others not available", function()
    local ActionExecutor = load_action_executor()
    ActionExecutor:init()

    G.STATE = G.STATES.ROUND_EVAL

    -- Only skip_to_shop available
    G.FUNCS = {
        skip_to_shop = mock_function("skip_to_shop"),
    }

    ActionExecutor:navigate_menu({ action = "shop" })

    assert_called("skip_to_shop", 1)
end)

-- Test 5: navigate_menu uses continue for non-shop actions in ROUND_EVAL
test("navigate_menu uses continue button for general navigation in ROUND_EVAL", function()
    local ActionExecutor = load_action_executor()
    ActionExecutor:init()

    G.STATE = G.STATES.ROUND_EVAL

    G.FUNCS = {
        continue = mock_function("continue"),
        evaluate_round = mock_function("evaluate_round"),
    }

    -- Call without shop action
    ActionExecutor:navigate_menu({})

    assert_called("continue", 1)
    assert_not_called("evaluate_round")
end)

-- Test 6: go_to_shop function prioritizes direct shop navigation
test("go_to_shop tries direct shop functions before falling back to navigate_menu", function()
    local ActionExecutor = load_action_executor()
    ActionExecutor:init()

    G.STATE = G.STATES.ROUND_EVAL

    -- Mock navigate_menu to track if it's called
    local original_navigate = ActionExecutor.navigate_menu
    ActionExecutor.navigate_menu = mock_function("navigate_menu")

    -- Test with go_to_shop available
    G.FUNCS = {
        go_to_shop = mock_function("go_to_shop"),
    }

    ActionExecutor:go_to_shop()

    assert_called("go_to_shop", 1)
    assert_not_called("navigate_menu")
end)

-- Test 7: go_to_shop falls back to navigate_menu when no direct functions available
test("go_to_shop falls back to navigate_menu when no shop functions available", function()
    local ActionExecutor = load_action_executor()
    ActionExecutor:init()

    G.STATE = G.STATES.ROUND_EVAL

    -- Track navigate_menu calls
    local navigate_calls = 0
    local navigate_params = nil
    ActionExecutor.navigate_menu = function(self, params)
        navigate_calls = navigate_calls + 1
        navigate_params = params
    end

    -- No shop functions available
    G.FUNCS = {}

    ActionExecutor:go_to_shop()

    assert_equal(navigate_calls, 1, "navigate_menu should be called once")
    assert_equal(navigate_params.action, "shop", "navigate_menu should be called with shop action")
end)

-- Test 8: Verify evaluate_round is never called in any shop navigation scenario
test("evaluate_round is never called in any shop navigation path", function()
    local ActionExecutor = load_action_executor()
    ActionExecutor:init()

    G.STATE = G.STATES.ROUND_EVAL

    -- Mock all possible functions including evaluate_round
    G.FUNCS = {
        evaluate_round = mock_function("evaluate_round"),
        continue = mock_function("continue"),
    }

    -- Test various navigation scenarios
    local scenarios = {
        { action = "shop" },
        { action = "continue" },
        {}, -- no action
        { direction = "select" },
    }

    for _, params in ipairs(scenarios) do
        TestHelper.reset_mocks()
        G.FUNCS.evaluate_round = mock_function("evaluate_round")

        ActionExecutor:navigate_menu(params)

        assert_not_called("evaluate_round")
    end
end)

-- Test 9: Shop navigation works correctly in non-ROUND_EVAL states
test("shop navigation handles non-ROUND_EVAL states appropriately", function()
    local ActionExecutor = load_action_executor()
    ActionExecutor:init()

    -- Test in PLAYING state
    G.STATE = G.STATES.PLAYING

    G.FUNCS = {
        go_to_shop = mock_function("go_to_shop"),
        evaluate_round = mock_function("evaluate_round"),
    }

    ActionExecutor:navigate_menu({ action = "shop" })

    -- Should still call go_to_shop if available
    assert_called("go_to_shop", 1)
    assert_not_called("evaluate_round")
end)

-- Test 10: Logging is correct for shop navigation
test("shop navigation logs appropriate messages", function()
    local ActionExecutor = load_action_executor()
    ActionExecutor:init()

    G.STATE = G.STATES.ROUND_EVAL

    -- Reset logger mocks
    TestHelper.reset_mocks()
    BalatroMCP.components.logger.info = mock_function("logger.info")

    G.FUNCS = {
        go_to_shop = mock_function("go_to_shop"),
    }

    ActionExecutor:navigate_menu({ action = "shop" })

    -- Should log the navigation attempt
    assert_called("logger.info")
end)

-- Report test results
TestHelper.report()
