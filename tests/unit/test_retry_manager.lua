-- Test suite for retry_manager.lua
-- Tests non-blocking retry logic, circuit breaker pattern, and coroutine handling

local TestHelper = require("tests.test_helper")

-- Load the module under test
package.path = package.path .. ";./?.lua;./?/init.lua"

-- Create a time variable for mocking
local mock_time = 0

-- Set up environment
TestHelper.create_mock_globals()

-- Override the love.timer.getTime to use our mock_time
_G.love.timer.getTime = function() return mock_time end

-- Load the retry manager
local RetryManager = require("mods.BalatroMCP.retry_manager")

-- Test Suite
TestHelper.run_suite("RetryManager")

-- Test initialization
TestHelper.test("RetryManager:init - should initialize with correct defaults", function()
    local config = {
        max_retries = 5,
        retry_delay_ms = 2000,
        reset_timeout = 120,
        failure_threshold = 5,
    }

    RetryManager:init(config)

    TestHelper.assert_equal(RetryManager.max_retries, 5)
    TestHelper.assert_equal(RetryManager.reset_timeout, 120)
    TestHelper.assert_equal(RetryManager.failure_threshold, 5)
    TestHelper.assert_equal(#RetryManager.retry_delays, 5)
    TestHelper.assert_equal(RetryManager.retry_delays[1], 2) -- 2000ms / 1000
    TestHelper.assert_equal(RetryManager.retry_delays[2], 4) -- Exponential backoff
    TestHelper.assert_equal(RetryManager.retry_delays[3], 8)
end)

-- Test circuit breaker states
TestHelper.test(
    "RetryManager:can_attempt - should allow attempts when circuit breaker is closed",
    function()
        RetryManager.is_open = false
        RetryManager.half_open = false

        TestHelper.assert_true(RetryManager:can_attempt())
    end
)

TestHelper.test(
    "RetryManager:can_attempt - should block attempts when circuit breaker is open",
    function()
        RetryManager.is_open = true
        RetryManager.half_open = false
        RetryManager.last_failure_time = love.timer.getTime()
        RetryManager.reset_timeout = 60

        TestHelper.assert_false(RetryManager:can_attempt())
    end
)

TestHelper.test("RetryManager:can_attempt - should allow attempt after reset timeout", function()
    RetryManager.is_open = true
    RetryManager.half_open = false
    RetryManager.reset_timeout = 1

    -- Set initial failure time
    mock_time = 0
    RetryManager.last_failure_time = mock_time
    
    -- Mock time to be past reset timeout
    mock_time = 2 -- 2 seconds later

    TestHelper.assert_true(RetryManager:can_attempt())
    TestHelper.assert_true(RetryManager.half_open)
end)

-- Test success recording
TestHelper.test(
    "RetryManager:record_success - should reset circuit breaker on success in half-open state",
    function()
        RetryManager.is_open = true
        RetryManager.half_open = true
        RetryManager.consecutive_failures = 3
        RetryManager.failure_count = 10

        RetryManager:record_success()

        TestHelper.assert_false(RetryManager.is_open)
        TestHelper.assert_false(RetryManager.half_open)
        TestHelper.assert_equal(RetryManager.consecutive_failures, 0)
        TestHelper.assert_equal(RetryManager.failure_count, 0)
    end
)

-- Test failure recording
TestHelper.test(
    "RetryManager:record_failure - should open circuit breaker after threshold failures",
    function()
        RetryManager.is_open = false
        RetryManager.consecutive_failures = 2
        RetryManager.failure_threshold = 3

        RetryManager:record_failure()

        TestHelper.assert_equal(RetryManager.consecutive_failures, 3)
        TestHelper.assert_true(RetryManager.is_open)
    end
)

TestHelper.test(
    "RetryManager:record_failure - should reopen circuit breaker if failure in half-open state",
    function()
        RetryManager.is_open = false
        RetryManager.half_open = true

        RetryManager:record_failure()

        TestHelper.assert_true(RetryManager.is_open)
        TestHelper.assert_false(RetryManager.half_open)
    end
)

-- Test retry execution
TestHelper.test("RetryManager:execute_with_retry - should succeed on first attempt", function()
    RetryManager.is_open = false
    local success_called = false
    local failure_called = false

    RetryManager:execute_with_retry(function()
        return true
    end, { test = "context" }, function(result)
        success_called = true
    end, function(error)
        failure_called = true
    end)

    -- Resume the coroutine
    local co_data = RetryManager.active_coroutines[1]
    TestHelper.assert_not_nil(co_data)
    coroutine.resume(co_data.coroutine)

    TestHelper.assert_true(success_called)
    TestHelper.assert_false(failure_called)
end)

TestHelper.test("RetryManager:execute_with_retry - should retry on failure", function()
    RetryManager.is_open = false
    RetryManager.max_retries = 3
    RetryManager.retry_delays = { 0.1, 0.2, 0.4 }

    local attempt_count = 0
    local success_called = false
    local failure_called = false

    -- Reset mock time for this test
    mock_time = 0

    RetryManager:execute_with_retry(function()
        attempt_count = attempt_count + 1
        if attempt_count < 3 then
            error("Simulated failure")
        end
        return true
    end, { test = "retry_context" }, function(result)
        success_called = true
    end, function(error)
        failure_called = true
    end)

    -- Simulate multiple update cycles to process retries
    local co_data = RetryManager.active_coroutines[1]

    -- Helper to advance time and resume coroutine
    local function advance_and_resume(time_delta)
        local start_time = mock_time
        local end_time = start_time + time_delta
        
        -- Simulate multiple small time steps
        while mock_time < end_time and coroutine.status(co_data.coroutine) ~= "dead" do
            mock_time = mock_time + 0.01
            coroutine.resume(co_data.coroutine)
        end
    end

    -- First attempt should happen immediately
    coroutine.resume(co_data.coroutine)
    TestHelper.assert_equal(attempt_count, 1)

    -- Wait for first retry delay (0.1s) and process
    advance_and_resume(0.15)
    TestHelper.assert_equal(attempt_count, 2)

    -- Wait for second retry delay (0.2s) and process
    advance_and_resume(0.25)
    TestHelper.assert_equal(attempt_count, 3)
    
    -- Final resume to complete
    coroutine.resume(co_data.coroutine)

    TestHelper.assert_true(success_called)
    TestHelper.assert_false(failure_called)
end)

TestHelper.test("RetryManager:execute_with_retry - should fail after max retries", function()
    RetryManager.is_open = false
    RetryManager.max_retries = 2
    RetryManager.retry_delays = { 0.1, 0.2 }

    local attempt_count = 0
    local failure_called = false
    local failure_error = nil

    -- Reset mock time for this test
    mock_time = 0

    RetryManager:execute_with_retry(
        function()
            attempt_count = attempt_count + 1
            error("Always fails")
        end,
        { test = "failure_context" },
        nil,
        function(error)
            failure_called = true
            failure_error = error
        end
    )

    -- Process all retry attempts
    local co_data = RetryManager.active_coroutines[1]
    
    -- Helper to advance time and resume coroutine
    local function advance_and_resume(time_delta)
        local start_time = mock_time
        local end_time = start_time + time_delta
        
        -- Simulate multiple small time steps
        while mock_time < end_time and coroutine.status(co_data.coroutine) ~= "dead" do
            mock_time = mock_time + 0.01
            coroutine.resume(co_data.coroutine)
        end
    end
    
    -- First attempt
    coroutine.resume(co_data.coroutine)
    TestHelper.assert_equal(attempt_count, 1)
    
    -- Wait for retry delay and process second attempt
    advance_and_resume(0.15)
    TestHelper.assert_equal(attempt_count, 2)
    
    -- Complete any remaining processing
    while coroutine.status(co_data.coroutine) ~= "dead" do
        coroutine.resume(co_data.coroutine)
    end

    TestHelper.assert_true(failure_called)
    TestHelper.assert_not_nil(failure_error)
end)

-- Test update method
TestHelper.test("RetryManager:update - should resume active coroutines", function()
    RetryManager.active_coroutines = {}

    local resumed = false
    local co = coroutine.create(function()
        resumed = true
        coroutine.yield()
    end)

    table.insert(RetryManager.active_coroutines, {
        coroutine = co,
        context = { test = true },
        started = 0,
    })

    RetryManager:update(0.016) -- ~60 FPS

    TestHelper.assert_true(resumed)
end)

TestHelper.test("RetryManager:update - should remove dead coroutines", function()
    RetryManager.active_coroutines = {}

    local co = coroutine.create(function()
        -- Immediately return, making coroutine dead
    end)

    table.insert(RetryManager.active_coroutines, {
        coroutine = co,
        context = { test = true },
        started = 0,
    })

    -- Resume once to make it dead
    coroutine.resume(co)

    TestHelper.assert_equal(#RetryManager.active_coroutines, 1)
    RetryManager:update(0.016)
    TestHelper.assert_equal(#RetryManager.active_coroutines, 0)
end)

-- Test status reporting
TestHelper.test("RetryManager:get_status - should return comprehensive status", function()
    RetryManager.is_open = true
    RetryManager.half_open = false
    RetryManager.failure_count = 5
    RetryManager.consecutive_failures = 3
    RetryManager.active_coroutines = { {}, {} }

    local status = RetryManager:get_status()

    TestHelper.assert_equal(status.is_open, true)
    TestHelper.assert_equal(status.half_open, false)
    TestHelper.assert_equal(status.failure_count, 5)
    TestHelper.assert_equal(status.consecutive_failures, 3)
    TestHelper.assert_equal(status.active_retries, 2)
    TestHelper.assert_false(status.can_attempt)
end)

-- Test manual reset
TestHelper.test("RetryManager:reset - should reset all circuit breaker state", function()
    RetryManager.is_open = true
    RetryManager.half_open = true
    RetryManager.consecutive_failures = 10
    RetryManager.failure_count = 20

    RetryManager:reset()

    TestHelper.assert_false(RetryManager.is_open)
    TestHelper.assert_false(RetryManager.half_open)
    TestHelper.assert_equal(RetryManager.consecutive_failures, 0)
    TestHelper.assert_equal(RetryManager.failure_count, 0)
end)

-- Report results
TestHelper.report()

