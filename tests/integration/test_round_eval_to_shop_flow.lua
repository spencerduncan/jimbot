-- Integration tests for Round Evaluation to Shop state transitions
-- Tests the full flow to ensure Issue #59 doesn't reoccur

package.path = package.path .. ";../../?.lua"

local TestHelper = require("tests.test_helper")
local test = TestHelper.test
local assert_equal = TestHelper.assert_equal
local assert_true = TestHelper.assert_true
local assert_false = TestHelper.assert_false
local assert_called = TestHelper.assert_called
local assert_not_called = TestHelper.assert_not_called
local mock_function = TestHelper.mock_function

-- Load the module under test
local function load_action_executor()
    TestHelper.create_mock_globals()
    return dofile("mods/BalatroMCP/action_executor.lua")
end

TestHelper.run_suite("Round Evaluation to Shop Flow Integration Tests")

-- Test 1: Complete flow from winning blind to shop
test("complete flow from winning blind to shop without UI bug", function()
    local ActionExecutor = load_action_executor()
    ActionExecutor:init()
    
    -- Simulate game state after winning a blind
    G.STATE = G.STATES.ROUND_EVAL
    G.GAME.round_scores = {
        hand_chips = 1000,
        mult = 10,
        chips = 10000
    }
    
    -- Mock UI elements that would show "score at least" message
    local ui_elements = {
        score_at_least_shown = false,
        shop_shown = false
    }
    
    -- Mock evaluate_round to track if it causes UI bug
    G.FUNCS.evaluate_round = function()
        ui_elements.score_at_least_shown = true
        TestHelper.mock_calls["evaluate_round"] = (TestHelper.mock_calls["evaluate_round"] or 0) + 1
    end
    
    -- Mock shop navigation
    G.FUNCS.go_to_shop = function()
        G.STATE = G.STATES.SHOP
        ui_elements.shop_shown = true
        TestHelper.mock_calls["go_to_shop"] = (TestHelper.mock_calls["go_to_shop"] or 0) + 1
    end
    
    -- Execute the action to go to shop
    ActionExecutor:execute_action("go_to_shop")
    
    -- Verify correct behavior
    assert_false(ui_elements.score_at_least_shown, "Score at least UI should not be shown")
    assert_true(ui_elements.shop_shown, "Shop should be shown")
    assert_equal(G.STATE, G.STATES.SHOP, "Should transition to SHOP state")
    assert_not_called("evaluate_round")
end)

-- Test 2: Multiple navigation attempts should not trigger the bug
test("multiple shop navigation attempts remain bug-free", function()
    local ActionExecutor = load_action_executor()
    ActionExecutor:init()
    
    G.STATE = G.STATES.ROUND_EVAL
    
    local evaluate_round_calls = 0
    G.FUNCS.evaluate_round = function()
        evaluate_round_calls = evaluate_round_calls + 1
    end
    
    G.FUNCS.go_to_shop = mock_function("go_to_shop")
    
    -- Try multiple times (simulating user clicking multiple times)
    for i = 1, 5 do
        ActionExecutor:navigate_menu({action = "shop"})
    end
    
    -- evaluate_round should never be called
    assert_equal(evaluate_round_calls, 0, "evaluate_round should not be called at all")
    assert_called("go_to_shop", 5)
end)

-- Test 3: Queued actions should maintain correct flow
test("queued shop navigation actions process without triggering bug", function()
    local ActionExecutor = load_action_executor()
    ActionExecutor:init()
    
    G.STATE = G.STATES.ROUND_EVAL
    
    -- Track state transitions
    local state_history = {}
    local original_go_to_shop = nil
    
    G.FUNCS.evaluate_round = function()
        table.insert(state_history, "evaluate_round_called")
    end
    
    G.FUNCS.go_to_shop = function()
        table.insert(state_history, "go_to_shop_called")
        G.STATE = G.STATES.SHOP
    end
    
    -- Queue the action
    ActionExecutor:queue_action("go_to_shop", nil, 0.1)
    
    -- Simulate time passing
    love.timer.getTime = function() return 0.2 end
    
    -- Process queued actions
    ActionExecutor:update(0.1)
    
    -- Check state history
    assert_equal(#state_history, 1, "Only one function should be called")
    assert_equal(state_history[1], "go_to_shop_called", "Only go_to_shop should be called")
end)

-- Test 4: State transition with all UI elements
test("full UI state transition without score message reappearing", function()
    local ActionExecutor = load_action_executor()
    ActionExecutor:init()
    
    -- Simulate complete game UI state
    G.STATE = G.STATES.ROUND_EVAL
    G.UIBOX = {
        states = {},
        current_state = "ROUND_EVAL"
    }
    
    -- Track UI updates
    local ui_updates = {}
    
    G.FUNCS.evaluate_round = function()
        table.insert(ui_updates, {
            action = "evaluate_round",
            ui_element = "score_at_least",
            visible = true
        })
    end
    
    G.FUNCS.continue = function()
        G.STATE = G.STATES.SHOP
        G.UIBOX.current_state = "SHOP"
        table.insert(ui_updates, {
            action = "continue",
            ui_element = "shop_menu",
            visible = true
        })
    end
    
    -- Navigate using continue (common scenario)
    ActionExecutor:navigate_menu({})
    
    -- Verify UI updates
    assert_equal(#ui_updates, 1, "Only one UI update should occur")
    assert_equal(ui_updates[1].action, "continue", "Continue should be called")
    assert_equal(ui_updates[1].ui_element, "shop_menu", "Shop menu should be shown")
    
    -- Verify score_at_least was never shown
    local score_ui_shown = false
    for _, update in ipairs(ui_updates) do
        if update.ui_element == "score_at_least" then
            score_ui_shown = true
        end
    end
    assert_false(score_ui_shown, "Score at least UI should never be shown")
end)

-- Test 5: Error recovery - shop functions not available
test("graceful handling when shop functions are unavailable", function()
    local ActionExecutor = load_action_executor()
    ActionExecutor:init()
    
    G.STATE = G.STATES.ROUND_EVAL
    
    -- No functions available except evaluate_round (which we don't want called)
    G.FUNCS = {
        evaluate_round = mock_function("evaluate_round")
    }
    
    -- This should not crash and should not call evaluate_round
    local success, error = pcall(function()
        ActionExecutor:go_to_shop()
    end)
    
    assert_true(success, "Should not crash when functions unavailable")
    assert_not_called("evaluate_round")
end)

-- Test 6: Different action paths all avoid the bug
test("all navigation paths to shop avoid triggering score UI", function()
    local ActionExecutor = load_action_executor()
    ActionExecutor:init()
    
    local test_scenarios = {
        {
            name = "direct go_to_shop action",
            setup = function()
                G.FUNCS.go_to_shop = mock_function("go_to_shop")
            end,
            action = function(executor)
                executor:execute_action("go_to_shop")
            end
        },
        {
            name = "navigate_menu with shop action",
            setup = function()
                G.FUNCS.to_shop = mock_function("to_shop")
            end,
            action = function(executor)
                executor:execute_action("navigate_menu", {action = "shop"})
            end
        },
        {
            name = "skip_to_shop fallback",
            setup = function()
                G.FUNCS.skip_to_shop = mock_function("skip_to_shop")
            end,
            action = function(executor)
                executor:navigate_menu({action = "shop"})
            end
        }
    }
    
    for _, scenario in ipairs(test_scenarios) do
        -- Reset for each scenario
        TestHelper.reset_mocks()
        G.STATE = G.STATES.ROUND_EVAL
        G.FUNCS = {
            evaluate_round = mock_function("evaluate_round")
        }
        
        -- Setup scenario-specific mocks
        scenario.setup()
        
        -- Execute the action
        scenario.action(ActionExecutor)
        
        -- Verify evaluate_round was not called
        assert_not_called("evaluate_round")
    end
end)

-- Test 7: Auto-play mode respects the fix
test("auto-play mode navigation does not trigger bug", function()
    local ActionExecutor = load_action_executor()
    ActionExecutor:init()
    ActionExecutor:set_auto_play(true)
    
    G.STATE = G.STATES.ROUND_EVAL
    
    -- Mock AI decision to go to shop
    G.FUNCS = {
        evaluate_round = mock_function("evaluate_round"),
        go_to_shop = mock_function("go_to_shop")
    }
    
    -- Simulate AI decision
    ActionExecutor:execute_action("go_to_shop")
    
    assert_not_called("evaluate_round")
    assert_called("go_to_shop", 1)
end)

-- Test 8: Rapid state changes don't cause regression
test("rapid state changes maintain bug fix", function()
    local ActionExecutor = load_action_executor()
    ActionExecutor:init()
    
    -- Simulate rapid state changes
    local states = {G.STATES.PLAYING, G.STATES.ROUND_EVAL, G.STATES.SHOP}
    
    G.FUNCS = {
        evaluate_round = mock_function("evaluate_round"),
        go_to_shop = mock_function("go_to_shop"),
        continue = mock_function("continue")
    }
    
    -- Change states rapidly and try navigation
    for i = 1, 10 do
        G.STATE = states[(i % 3) + 1]
        
        if G.STATE == G.STATES.ROUND_EVAL then
            ActionExecutor:navigate_menu({action = "shop"})
        end
    end
    
    -- evaluate_round should never be called
    assert_not_called("evaluate_round")
end)

-- Report test results
TestHelper.report()