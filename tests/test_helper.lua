-- Test Helper for BalatroMCP tests
-- Provides test framework and mocking utilities

local TestHelper = {}

-- Test result tracking
TestHelper.tests = {}
TestHelper.passed = 0
TestHelper.failed = 0
TestHelper.current_test = nil

-- Mock storage
TestHelper.mocks = {}
TestHelper.mock_calls = {}

-- Assert functions
function TestHelper.assert_equal(actual, expected, message)
    if actual ~= expected then
        error(string.format("%s\nExpected: %s\nActual: %s", 
            message or "Values not equal", 
            tostring(expected), 
            tostring(actual)))
    end
end

function TestHelper.assert_true(value, message)
    if not value then
        error(message or "Expected true, got false")
    end
end

function TestHelper.assert_false(value, message)
    if value then
        error(message or "Expected false, got true")
    end
end

function TestHelper.assert_nil(value, message)
    if value ~= nil then
        error(string.format("%s\nExpected nil, got: %s", 
            message or "Expected nil", 
            tostring(value)))
    end
end

function TestHelper.assert_not_nil(value, message)
    if value == nil then
        error(message or "Expected non-nil value")
    end
end

function TestHelper.assert_called(mock_name, times)
    local calls = TestHelper.mock_calls[mock_name] or 0
    if times then
        TestHelper.assert_equal(calls, times, 
            string.format("Mock '%s' was called %d times, expected %d", 
                mock_name, calls, times))
    else
        TestHelper.assert_true(calls > 0, 
            string.format("Mock '%s' was not called", mock_name))
    end
end

function TestHelper.assert_not_called(mock_name)
    local calls = TestHelper.mock_calls[mock_name] or 0
    TestHelper.assert_equal(calls, 0, 
        string.format("Mock '%s' was called %d times, expected 0", 
            mock_name, calls))
end

-- Mock creation
function TestHelper.mock_function(name, return_value)
    TestHelper.mock_calls[name] = 0
    TestHelper.mocks[name] = function(...)
        -- Ensure mock_calls[name] exists before incrementing
        TestHelper.mock_calls[name] = (TestHelper.mock_calls[name] or 0) + 1
        if type(return_value) == "function" then
            return return_value(...)
        else
            return return_value
        end
    end
    return TestHelper.mocks[name]
end

-- Reset mocks between tests
function TestHelper.reset_mocks()
    TestHelper.mocks = {}
    TestHelper.mock_calls = {}
end

-- Test definition
function TestHelper.test(name, func)
    TestHelper.current_test = name
    TestHelper.reset_mocks()
    
    local success, error = pcall(func)
    
    if success then
        TestHelper.passed = TestHelper.passed + 1
        print(string.format("✓ %s", name))
    else
        TestHelper.failed = TestHelper.failed + 1
        print(string.format("✗ %s", name))
        print(string.format("  Error: %s", error))
    end
    
    table.insert(TestHelper.tests, {
        name = name,
        passed = success,
        error = error
    })
end

-- Test suite runner
function TestHelper.run_suite(suite_name)
    print(string.format("\nRunning test suite: %s", suite_name))
    print(string.rep("-", 50))
end

-- Summary reporter
function TestHelper.report()
    print(string.rep("-", 50))
    print(string.format("Tests run: %d", TestHelper.passed + TestHelper.failed))
    print(string.format("Passed: %d", TestHelper.passed))
    print(string.format("Failed: %d", TestHelper.failed))
    
    if TestHelper.failed > 0 then
        print("\nFailed tests:")
        for _, test in ipairs(TestHelper.tests) do
            if not test.passed then
                print(string.format("  - %s", test.name))
            end
        end
    end
    
    return TestHelper.failed == 0
end

-- Global state mocker
function TestHelper.create_mock_globals()
    -- Mock the global G table used by Balatro
    G = {
        STATE = nil,
        STATES = {
            MENU = "MENU",
            PLAYING = "PLAYING", 
            ROUND_EVAL = "ROUND_EVAL",
            SHOP = "SHOP",
            BLIND_SELECT = "BLIND_SELECT",
            DECK_SELECT = "DECK_SELECT",
            STAKE_SELECT = "STAKE_SELECT"
        },
        FUNCS = {},
        GAME = {
            dollars = 100,
            current_round = {
                discards_left = 3,
                reroll_cost = 5
            }
        },
        hand = nil,
        shop = nil,
        jokers = nil,
        blind_select_opts = nil
    }
    
    -- Mock Love2D timer
    love = {
        timer = {
            getTime = TestHelper.mock_function("love.timer.getTime", 0)
        }
    }
    
    -- Mock BalatroMCP
    BalatroMCP = {
        components = {
            logger = {
                info = TestHelper.mock_function("logger.info"),
                debug = TestHelper.mock_function("logger.debug"),
                warn = TestHelper.mock_function("logger.warn"),
                error = TestHelper.mock_function("logger.error")
            }
        },
        config = {
            auto_play = true
        }
    }
end

return TestHelper