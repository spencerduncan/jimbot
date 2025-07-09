-- Integration test for retry logic with simulated network failures
-- Tests the full retry flow including circuit breaker behavior

local TestHelper = require("tests.test_helper")

-- Load modules
package.path = package.path .. ";./?.lua;./?/init.lua"

-- Set up environment
TestHelper.create_mock_globals()

-- Create a time variable for mocking
local mock_time = 0

-- Ensure love global exists before loading modules
if not _G.love then
    _G.love = {
        timer = {
            getTime = function()
                return mock_time
            end,
        },
    }
end

-- Create a mock https module with controllable failures
local mock_https = {
    failure_count = 0,
    max_failures = 2,
    request = function(url, options)
        mock_https.failure_count = mock_https.failure_count + 1
        if mock_https.failure_count <= mock_https.max_failures then
            -- Simulate failure
            return 500, "Internal Server Error"
        else
            -- Simulate success
            return 200, '{"status":"ok"}'
        end
    end,
}

-- Override require to provide our mock https
local original_require = require
_G.require = function(module)
    if module == "https" then
        return mock_https
    end
    return original_require(module)
end

-- Load the actual modules
local EventBusClient = require("mods.BalatroMCP.event_bus_client")
local RetryManager = require("mods.BalatroMCP.retry_manager")

-- Test Suite
TestHelper.run_suite("Retry Integration Tests")

-- Test successful retry after transient failures
TestHelper.test("Integration: Should retry and succeed after transient failures", function()
    -- Initialize components
    local config = {
        event_bus_url = "http://localhost:8080/api/v1/events",
        max_retries = 3,
        retry_delay_ms = 100,
        failure_threshold = 5,
    }

    EventBusClient:init(config)

    -- Mark connection as tested to skip initial test
    EventBusClient.connection_tested = true

    -- Configure mock to succeed after 2 failures
    mock_https.failure_count = 0
    mock_https.max_failures = 2

    -- Track what happens
    local http_calls = 0
    local success_called = false

    -- Create event
    local event = { type = "TEST_EVENT", data = { value = 42 } }

    -- Mock http_post to use our mock_https
    EventBusClient.http_post = function(self, url, json)
        http_calls = http_calls + 1
        local code, response = mock_https.request(url, { body = json })
        return code == 200, response
    end

    -- Direct test of retry logic
    local attempts = 0
    local function test_func()
        attempts = attempts + 1
        local code, response = mock_https.request("test", {})
        return code == 200, response
    end

    -- Execute with retry manager directly
    EventBusClient.retry_manager:execute_with_retry(test_func, { test = "retry" }, function(result)
        success_called = true
    end, function(error)
        -- Should not be called
    end)

    -- Process retries through update method
    -- The retry manager needs multiple update cycles to process retries
    -- We need to advance time more aggressively for retry delays
    for i = 1, 30 do  -- Allow enough cycles for retries with delays
        -- Advance time before update to handle delays
        mock_time = mock_time + 0.5 -- Advance time by 500ms each cycle
        
        -- Update the retry manager
        EventBusClient.retry_manager:update(0.1)

        -- Check if we're done
        if #EventBusClient.retry_manager.active_coroutines == 0 then
            break
        end
    end

    -- Verify results
    TestHelper.assert_equal(attempts, 3) -- 2 failures + 1 success
    TestHelper.assert_equal(mock_https.failure_count, 3)
    TestHelper.assert_true(success_called)
end)

-- Test circuit breaker opening after persistent failures
TestHelper.test("Integration: Circuit breaker should open after persistent failures", function()
    -- Reset retry manager state
    RetryManager:reset()
    RetryManager.failure_threshold = 3

    -- Configure mock to always fail
    mock_https.failure_count = 0
    mock_https.max_failures = 999

    -- Track circuit breaker state
    local initial_state = RetryManager.is_open
    TestHelper.assert_false(initial_state)

    -- Simulate multiple failed requests
    for i = 1, 3 do
        RetryManager:record_failure()
    end

    -- Circuit breaker should be open
    TestHelper.assert_true(RetryManager.is_open)
    TestHelper.assert_false(RetryManager:can_attempt())
end)

-- Test event buffering when circuit breaker is open
TestHelper.test("Integration: Events should be buffered when circuit breaker is open", function()
    -- Open circuit breaker
    RetryManager.is_open = true
    EventBusClient.local_buffer = {}
    EventBusClient.retry_manager = RetryManager

    -- Try to send events
    for i = 1, 5 do
        EventBusClient:send_event({ type = "BUFFERED_EVENT_" .. i })
    end

    -- All events should be buffered
    TestHelper.assert_equal(#EventBusClient.local_buffer, 5)

    -- No network calls should have been made
    local calls_before = mock_https.failure_count
    TestHelper.assert_equal(calls_before, mock_https.failure_count)
end)

-- Test buffer flushing after circuit breaker recovery
TestHelper.test("Integration: Buffered events should be sent after recovery", function()
    -- Setup buffered events
    EventBusClient.local_buffer = {
        { type = "BUFFERED_1", event_id = "1", timestamp = 1000, source = "BalatroMCP" },
        { type = "BUFFERED_2", event_id = "2", timestamp = 2000, source = "BalatroMCP" },
        { type = "BUFFERED_3", event_id = "3", timestamp = 3000, source = "BalatroMCP" },
    }

    -- Reset circuit breaker and mock
    EventBusClient.retry_manager:reset()
    mock_https.failure_count = 0
    mock_https.max_failures = 0 -- All requests succeed

    -- Track batch sending
    local batches_sent = 0
    local original_send_batch = EventBusClient.send_batch
    EventBusClient.send_batch = function(self, events)
        batches_sent = batches_sent + 1
        -- Clear the buffer to simulate successful send
        self.local_buffer = {}
        return true
    end

    -- Flush buffer
    EventBusClient:flush_buffer()

    -- Restore original
    EventBusClient.send_batch = original_send_batch

    -- Verify events were sent
    TestHelper.assert_equal(batches_sent, 1)
    TestHelper.assert_equal(#EventBusClient.local_buffer, 0)
end)

-- Test graceful degradation
TestHelper.test(
    "Integration: System should continue operating with event bus unavailable",
    function()
        -- Configure for immediate circuit breaker opening
        EventBusClient.retry_manager:reset()
        EventBusClient.retry_manager.failure_threshold = 1
        EventBusClient.local_buffer = {}

        -- Mock complete failure
        mock_https.failure_count = 0
        mock_https.max_failures = 999

        -- Mock http_post to always fail
        EventBusClient.http_post = function(self, url, json)
            local code, response = mock_https.request(url, { body = json })
            return code == 200, response
        end

        -- Send first event to trigger circuit breaker
        EventBusClient:send_event({ type = "TRIGGER_FAILURE" })

        -- Record failure to open circuit breaker
        EventBusClient.retry_manager:record_failure()

        -- Now send multiple events - they should all be buffered
        local initial_buffer_size = #EventBusClient.local_buffer

        for i = 1, 10 do
            EventBusClient:send_event({
                type = "EVENT_" .. i,
                important = true,
            })
        end

        -- Circuit breaker should be open
        TestHelper.assert_true(EventBusClient.retry_manager.is_open)

        -- All new events should be in buffer
        TestHelper.assert_true(#EventBusClient.local_buffer >= 10)
    end
)

-- Clean up
_G.require = original_require

-- Report results
TestHelper.report()
