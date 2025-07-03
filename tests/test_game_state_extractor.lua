-- Test suite for game_state_extractor.lua
-- Tests all game state identification and unknown state handling

local test_runner = {}
local tests_passed = 0
local tests_failed = 0
local failures = {}

-- Mock the G object and its states
local function setup_mock_g()
    _G.G = {
        STATES = {
            MENU = 0,
            DECK_SELECT = 1,
            STAKE_SELECT = 2,
            BLIND_SELECT = 3,
            SHOP = 4,
            PLAYING = 5,
            ROUND_EVAL = 6,
            GAME_OVER = 7,
            TAROT_PACK = 8,
            PLANET_PACK = 9,
            SPECTRAL_PACK = 10,
            STANDARD_PACK = 11,
            BUFFOON_PACK = 12,
            SMODS_BOOSTER_OPENED = 13,
        },
        STATE = nil,
        GAME = {
            pseudorandom_seed = "test_seed",
            round_resets = { ante = 1 },
            round = 1,
            current_round = {
                hands_played = 0,
                hands_left = 4,
                discards_left = 3,
            },
            chips = 0,
            mult = 0,
            dollars = 4,
            hand = { size = 8 },
            blind = {
                name = "Test Blind",
                chips = 300,
                mult = 1,
                defeated = false,
                boss = false,
            },
        },
        jokers = { cards = {} },
        hand = { cards = {}, highlighted = {} },
        deck = { cards = {} },
        consumeables = { cards = {} },
        playing_cards = {},
        FRAME = 0,
    }
end

-- Mock utils module
local function setup_mock_utils()
    package.loaded["mods.BalatroMCP.utils"] = {
        safe_check_path = function(obj, path)
            return true
        end,
        safe_primitive_value = function(obj, key, default)
            return obj and obj[key] or default
        end,
        safe_primitive_nested_value = function(obj, path, default)
            local current = obj
            for _, key in ipairs(path) do
                if not current or not current[key] then
                    return default
                end
                current = current[key]
            end
            return current
        end,
        get_card_edition_safe = function(card)
            return nil
        end,
        get_card_enhancement_safe = function(card)
            return nil
        end,
        get_card_seal_safe = function(card)
            return nil
        end,
    }
end

-- Helper function to run a test
local function run_test(name, test_func)
    local success, err = pcall(test_func)
    if success then
        tests_passed = tests_passed + 1
        print("[PASS] " .. name)
    else
        tests_failed = tests_failed + 1
        table.insert(failures, { name = name, error = err })
        print("[FAIL] " .. name .. " - " .. tostring(err))
    end
end

-- Helper function to assert equality
local function assert_equals(actual, expected, message)
    if actual ~= expected then
        error(
            string.format(
                "%s - Expected: %s, Got: %s",
                message or "Assertion failed",
                tostring(expected),
                tostring(actual)
            )
        )
    end
end

-- Test: All known game states are properly identified
function test_runner.test_all_known_states()
    setup_mock_g()
    setup_mock_utils()

    -- Reload the module to get fresh instance
    package.loaded["mods.BalatroMCP.game_state_extractor"] = nil
    local GameStateExtractor = require("mods.BalatroMCP.game_state_extractor")

    local state_mappings = {
        { state = G.STATES.MENU, expected = "MENU" },
        { state = G.STATES.DECK_SELECT, expected = "DECK_SELECT" },
        { state = G.STATES.STAKE_SELECT, expected = "STAKE_SELECT" },
        { state = G.STATES.BLIND_SELECT, expected = "BLIND_SELECT" },
        { state = G.STATES.SHOP, expected = "SHOP" },
        { state = G.STATES.PLAYING, expected = "PLAYING" },
        { state = G.STATES.ROUND_EVAL, expected = "ROUND_EVAL" },
        { state = G.STATES.GAME_OVER, expected = "GAME_OVER" },
        { state = G.STATES.TAROT_PACK, expected = "TAROT_PACK" },
        { state = G.STATES.PLANET_PACK, expected = "PLANET_PACK" },
        { state = G.STATES.SPECTRAL_PACK, expected = "SPECTRAL_PACK" },
        { state = G.STATES.STANDARD_PACK, expected = "STANDARD_PACK" },
        { state = G.STATES.BUFFOON_PACK, expected = "BUFFOON_PACK" },
        { state = G.STATES.SMODS_BOOSTER_OPENED, expected = "BOOSTER_PACK" },
    }

    for _, mapping in ipairs(state_mappings) do
        G.STATE = mapping.state
        local phase = GameStateExtractor:get_game_phase()
        assert_equals(
            phase,
            mapping.expected,
            string.format("State %d should be identified as %s", mapping.state, mapping.expected)
        )
    end
end

-- Test: Unknown states are properly reported with numeric value
function test_runner.test_unknown_states()
    setup_mock_g()
    setup_mock_utils()

    package.loaded["mods.BalatroMCP.game_state_extractor"] = nil
    local GameStateExtractor = require("mods.BalatroMCP.game_state_extractor")

    -- Test various unknown state values
    local unknown_states = { 14, 15, 20, 99, 100, 255 }

    for _, state_value in ipairs(unknown_states) do
        G.STATE = state_value
        local phase = GameStateExtractor:get_game_phase()
        local expected = "UNKNOWN_STATE_" .. tostring(state_value)
        assert_equals(
            phase,
            expected,
            string.format("Unknown state %d should be reported as %s", state_value, expected)
        )
    end
end

-- Test: Nil G or G.STATE returns UNKNOWN
function test_runner.test_nil_state_handling()
    setup_mock_utils()

    package.loaded["mods.BalatroMCP.game_state_extractor"] = nil
    local GameStateExtractor = require("mods.BalatroMCP.game_state_extractor")

    -- Test with nil G
    _G.G = nil
    local phase = GameStateExtractor:get_game_phase()
    assert_equals(phase, "UNKNOWN", "Nil G should return UNKNOWN")

    -- Test with G but nil STATE
    _G.G = { STATE = nil }
    phase = GameStateExtractor:get_game_phase()
    assert_equals(phase, "UNKNOWN", "Nil G.STATE should return UNKNOWN")
end

-- Test: Game state extraction includes correct phase
function test_runner.test_state_extraction_includes_phase()
    setup_mock_g()
    setup_mock_utils()

    package.loaded["mods.BalatroMCP.game_state_extractor"] = nil
    local GameStateExtractor = require("mods.BalatroMCP.game_state_extractor")

    -- Set a known state
    G.STATE = G.STATES.SHOP
    local state = GameStateExtractor:get_current_state()

    assert_equals(state.game_state, "SHOP", "Extracted state should include correct game phase")
    assert_equals(
        state.ui_state,
        tostring(G.STATES.SHOP),
        "UI state should be string representation of numeric state"
    )
end

-- Test: Available actions change based on game phase
function test_runner.test_available_actions_by_phase()
    setup_mock_g()
    setup_mock_utils()

    package.loaded["mods.BalatroMCP.game_state_extractor"] = nil
    local GameStateExtractor = require("mods.BalatroMCP.game_state_extractor")

    -- Test PLAYING state actions
    G.STATE = G.STATES.PLAYING
    local actions = GameStateExtractor:get_available_actions()
    local has_play_hand = false
    local has_sort_hand = false
    for _, action in ipairs(actions) do
        if action == "sort_hand" then
            has_sort_hand = true
        end
    end
    assert_equals(has_sort_hand, true, "PLAYING state should have sort_hand action")

    -- Test SHOP state actions
    G.STATE = G.STATES.SHOP
    actions = GameStateExtractor:get_available_actions()
    local has_buy_joker = false
    local has_skip_shop = false
    for _, action in ipairs(actions) do
        if action == "buy_joker" then
            has_buy_joker = true
        end
        if action == "skip_shop" then
            has_skip_shop = true
        end
    end
    assert_equals(has_buy_joker, true, "SHOP state should have buy_joker action")
    assert_equals(has_skip_shop, true, "SHOP state should have skip_shop action")

    -- Test BLIND_SELECT state actions
    G.STATE = G.STATES.BLIND_SELECT
    actions = GameStateExtractor:get_available_actions()
    local has_select_blind = false
    for _, action in ipairs(actions) do
        if action == "select_small_blind" then
            has_select_blind = true
        end
    end
    assert_equals(
        has_select_blind,
        true,
        "BLIND_SELECT state should have select_small_blind action"
    )
end

-- Test: Edge cases and error conditions
function test_runner.test_edge_cases()
    setup_mock_g()
    setup_mock_utils()

    package.loaded["mods.BalatroMCP.game_state_extractor"] = nil
    local GameStateExtractor = require("mods.BalatroMCP.game_state_extractor")

    -- Test with string state (should still work with tostring)
    G.STATE = "not_a_number"
    local phase = GameStateExtractor:get_game_phase()
    assert_equals(phase, "UNKNOWN_STATE_not_a_number", "String state should be handled gracefully")

    -- Test with negative state
    G.STATE = -1
    phase = GameStateExtractor:get_game_phase()
    assert_equals(phase, "UNKNOWN_STATE_-1", "Negative state should be handled")

    -- Test with float state
    G.STATE = 3.14
    phase = GameStateExtractor:get_game_phase()
    assert_equals(phase, "UNKNOWN_STATE_3.14", "Float state should be handled")
end

-- Main test runner
function test_runner.run_all_tests()
    print("\n=== Running Game State Extractor Tests ===\n")

    run_test("test_all_known_states", test_runner.test_all_known_states)
    run_test("test_unknown_states", test_runner.test_unknown_states)
    run_test("test_nil_state_handling", test_runner.test_nil_state_handling)
    run_test(
        "test_state_extraction_includes_phase",
        test_runner.test_state_extraction_includes_phase
    )
    run_test("test_available_actions_by_phase", test_runner.test_available_actions_by_phase)
    run_test("test_edge_cases", test_runner.test_edge_cases)

    print("\n=== Test Summary ===")
    print(string.format("Passed: %d", tests_passed))
    print(string.format("Failed: %d", tests_failed))

    if tests_failed > 0 then
        print("\n=== Failed Tests ===")
        for _, failure in ipairs(failures) do
            print(string.format("- %s: %s", failure.name, failure.error))
        end
    end

    print("\n" .. string.rep("=", 40) .. "\n")

    return tests_failed == 0
end

-- Run tests if executed directly
if arg and arg[0] and arg[0]:match("test_game_state_extractor%.lua$") then
    local success = test_runner.run_all_tests()
    os.exit(success and 0 or 1)
end

return test_runner
