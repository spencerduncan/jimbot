-- Integration tests for game_state_extractor.lua
-- Tests the game state extraction in realistic scenarios

local test_runner = {}
local tests_passed = 0
local tests_failed = 0
local failures = {}

-- Mock full game environment
local function setup_full_game_mock(state_value)
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
            SMODS_BOOSTER_OPENED = 13
        },
        STATE = state_value,
        GAME = {
            pseudorandom_seed = "integration_test_" .. tostring(state_value),
            round_resets = {ante = 3},
            round = 5,
            current_round = {
                hands_played = 2,
                hands_left = 2,
                discards_left = 1
            },
            chips = 1500,
            mult = 15,
            dollars = 25,
            hand = {size = 8},
            blind = {
                name = "Big Blind",
                chips = 2400,
                chip_text = "2400",
                mult = 1,
                defeated = false,
                boss = false
            },
            round_scores = {
                ["1"] = {100, 200, 300},
                ["2"] = {400, 500, 600}
            }
        },
        jokers = {
            cards = {
                {
                    unique_val = "joker_001",
                    ability = {name = "Joker", mult = 4},
                    cost = 3,
                    sell_cost = 1
                },
                {
                    unique_val = "joker_002",
                    ability = {name = "Greedy Joker", mult = 0, t_chips = 25},
                    cost = 5,
                    sell_cost = 2
                }
            }
        },
        hand = {
            cards = {
                {
                    unique_val = "card_001",
                    base = {value = "A", suit = "Spades"}
                },
                {
                    unique_val = "card_002",
                    base = {value = "K", suit = "Hearts"}
                }
            },
            highlighted = {}
        },
        deck = {
            cards = {}
        },
        consumeables = {
            cards = {
                {
                    unique_val = "tarot_001",
                    ability = {name = "The Fool", set = "Tarot"},
                    cost = 3
                }
            }
        },
        playing_cards = {},
        shop = state_value == 4 and {
            jokers = {
                cards = {
                    {
                        ability = {name = "Test Joker"},
                        cost = 8,
                        config = {center = {rarity = 2}}
                    }
                }
            },
            booster = {cards = {}},
            vouchers = {cards = {}}
        } or nil,
        FRAME = 12345
    }
end

-- Mock utils
local function setup_mock_utils()
    package.loaded["mods.BalatroMCP.utils"] = {
        safe_check_path = function(obj, path)
            local current = obj
            for _, key in ipairs(path) do
                if not current or not current[key] then
                    return false
                end
                current = current[key]
            end
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
        end
    }
end

-- Helper functions
local function run_test(name, test_func)
    local success, err = pcall(test_func)
    if success then
        tests_passed = tests_passed + 1
        print("[PASS] " .. name)
    else
        tests_failed = tests_failed + 1
        table.insert(failures, {name = name, error = err})
        print("[FAIL] " .. name .. " - " .. tostring(err))
    end
end

local function assert_equals(actual, expected, message)
    if actual ~= expected then
        error(string.format("%s - Expected: %s, Got: %s", 
            message or "Assertion failed", tostring(expected), tostring(actual)))
    end
end

local function assert_not_nil(value, message)
    if value == nil then
        error(message or "Value should not be nil")
    end
end

local function assert_table_contains(table, value, message)
    for _, v in ipairs(table) do
        if v == value then
            return
        end
    end
    error(message or string.format("Table does not contain value: %s", tostring(value)))
end

-- Test: Full state extraction in PLAYING state
function test_runner.test_playing_state_full_extraction()
    setup_full_game_mock(5) -- PLAYING state
    setup_mock_utils()
    
    package.loaded["mods.BalatroMCP.game_state_extractor"] = nil
    local GameStateExtractor = require("mods.BalatroMCP.game_state_extractor")
    
    local state = GameStateExtractor:get_current_state()
    
    -- Verify basic state info
    assert_equals(state.in_game, true, "Should be in game")
    assert_equals(state.game_state, "PLAYING", "Should be in PLAYING state")
    assert_equals(state.ante, 3, "Ante should be 3")
    assert_equals(state.round, 5, "Round should be 5")
    assert_equals(state.hand_number, 2, "Hand number should be 2")
    
    -- Verify resources
    assert_equals(state.chips, 1500, "Chips should be 1500")
    assert_equals(state.mult, 15, "Mult should be 15")
    assert_equals(state.money, 25, "Money should be 25")
    assert_equals(state.hands_remaining, 2, "Hands remaining should be 2")
    assert_equals(state.discards_remaining, 1, "Discards remaining should be 1")
    
    -- Verify collections
    assert_not_nil(state.jokers, "Jokers should not be nil")
    assert_equals(#state.jokers, 2, "Should have 2 jokers")
    assert_equals(state.jokers[1].name, "Joker", "First joker should be 'Joker'")
    
    assert_not_nil(state.hand, "Hand should not be nil")
    assert_equals(#state.hand, 2, "Should have 2 cards in hand")
    
    assert_not_nil(state.consumables, "Consumables should not be nil")
    assert_equals(#state.consumables, 1, "Should have 1 consumable")
    
    -- Verify blind info
    assert_not_nil(state.blind, "Blind info should not be nil")
    assert_equals(state.blind.name, "Big Blind", "Blind name should be 'Big Blind'")
    assert_equals(state.blind.chips, 2400, "Blind chips should be 2400")
end

-- Test: Shop state with items
function test_runner.test_shop_state_extraction()
    setup_full_game_mock(4) -- SHOP state
    setup_mock_utils()
    
    package.loaded["mods.BalatroMCP.game_state_extractor"] = nil
    local GameStateExtractor = require("mods.BalatroMCP.game_state_extractor")
    
    local state = GameStateExtractor:get_current_state()
    
    assert_equals(state.game_state, "SHOP", "Should be in SHOP state")
    assert_not_nil(state.shop_items, "Shop items should not be nil")
    assert_not_nil(state.shop_items["joker_1"], "Should have joker in shop")
    assert_equals(state.shop_items["joker_1"].name, "Test Joker", "Shop joker name should match")
    assert_equals(state.shop_items["joker_1"].cost, 8, "Shop joker cost should be 8")
end

-- Test: Menu state (not in game)
function test_runner.test_menu_state_extraction()
    setup_mock_utils()
    
    -- Setup minimal G for menu state
    _G.G = {
        STATES = {MENU = 0},
        STATE = 0,
        GAME = nil
    }
    
    package.loaded["mods.BalatroMCP.game_state_extractor"] = nil
    local GameStateExtractor = require("mods.BalatroMCP.game_state_extractor")
    
    local state = GameStateExtractor:get_current_state()
    
    assert_equals(state.in_game, false, "Should not be in game")
    assert_equals(state.phase, "MENU", "Phase should be MENU")
end

-- Test: State transitions are reported correctly
function test_runner.test_state_transitions()
    setup_mock_utils()
    
    package.loaded["mods.BalatroMCP.game_state_extractor"] = nil
    local GameStateExtractor = require("mods.BalatroMCP.game_state_extractor")
    
    local states_to_test = {
        {value = 1, name = "DECK_SELECT"},
        {value = 2, name = "STAKE_SELECT"},
        {value = 3, name = "BLIND_SELECT"},
        {value = 5, name = "PLAYING"},
        {value = 6, name = "ROUND_EVAL"},
        {value = 4, name = "SHOP"}
    }
    
    for _, state_info in ipairs(states_to_test) do
        setup_full_game_mock(state_info.value)
        local state = GameStateExtractor:get_current_state()
        assert_equals(state.game_state, state_info.name, 
            string.format("State %d should be reported as %s", state_info.value, state_info.name))
    end
end

-- Test: Available actions match game state
function test_runner.test_available_actions_comprehensive()
    setup_mock_utils()
    
    package.loaded["mods.BalatroMCP.game_state_extractor"] = nil
    local GameStateExtractor = require("mods.BalatroMCP.game_state_extractor")
    
    -- Test DECK_SELECT state (should have no specific actions)
    setup_full_game_mock(1)
    local actions = GameStateExtractor:get_available_actions()
    assert_not_nil(actions, "Actions should not be nil for DECK_SELECT")
    
    -- Test STAKE_SELECT state (should have no specific actions)
    setup_full_game_mock(2)
    actions = GameStateExtractor:get_available_actions()
    assert_not_nil(actions, "Actions should not be nil for STAKE_SELECT")
    
    -- Test pack opening states
    local pack_states = {8, 9, 10, 11, 12}
    for _, state_value in ipairs(pack_states) do
        setup_full_game_mock(state_value)
        actions = GameStateExtractor:get_available_actions()
        assert_not_nil(actions, string.format("Actions should not be nil for state %d", state_value))
    end
end

-- Test: Highlighted cards tracking
function test_runner.test_highlighted_cards_extraction()
    setup_full_game_mock(5) -- PLAYING state
    setup_mock_utils()
    
    -- Add highlighted cards
    G.hand.highlighted = {G.hand.cards[1]}
    
    package.loaded["mods.BalatroMCP.game_state_extractor"] = nil
    local GameStateExtractor = require("mods.BalatroMCP.game_state_extractor")
    
    local highlighted = GameStateExtractor:get_highlighted_cards()
    
    assert_not_nil(highlighted, "Highlighted cards should not be nil")
    assert_equals(#highlighted, 1, "Should have 1 highlighted card")
    assert_equals(highlighted[1].rank, "A", "Highlighted card should be Ace")
    assert_equals(highlighted[1].suit, "Spades", "Highlighted card should be Spades")
end

-- Test: Unknown state logging
function test_runner.test_unknown_state_logging()
    setup_full_game_mock(999) -- Unknown state
    setup_mock_utils()
    
    package.loaded["mods.BalatroMCP.game_state_extractor"] = nil
    local GameStateExtractor = require("mods.BalatroMCP.game_state_extractor")
    
    -- Capture print output
    local original_print = print
    local printed_messages = {}
    print = function(msg)
        table.insert(printed_messages, msg)
    end
    
    local state = GameStateExtractor:get_current_state()
    
    -- Restore original print
    print = original_print
    
    assert_equals(state.game_state, "UNKNOWN_STATE_999", "Unknown state should be reported correctly")
    assert_equals(#printed_messages, 3, "Should have printed warning message") -- 3 because of hand extraction debug messages
    
    local found_warning = false
    for _, msg in ipairs(printed_messages) do
        if msg:match("WARNING: Unknown game state detected: UNKNOWN_STATE_999") then
            found_warning = true
            break
        end
    end
    assert_equals(found_warning, true, "Should have printed unknown state warning")
end

-- Main test runner
function test_runner.run_all_tests()
    print("\n=== Running Game State Integration Tests ===\n")
    
    run_test("test_playing_state_full_extraction", test_runner.test_playing_state_full_extraction)
    run_test("test_shop_state_extraction", test_runner.test_shop_state_extraction)
    run_test("test_menu_state_extraction", test_runner.test_menu_state_extraction)
    run_test("test_state_transitions", test_runner.test_state_transitions)
    run_test("test_available_actions_comprehensive", test_runner.test_available_actions_comprehensive)
    run_test("test_highlighted_cards_extraction", test_runner.test_highlighted_cards_extraction)
    run_test("test_unknown_state_logging", test_runner.test_unknown_state_logging)
    
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
if arg and arg[0] and arg[0]:match("test_game_state_integration%.lua$") then
    local success = test_runner.run_all_tests()
    os.exit(success and 0 or 1)
end

return test_runner