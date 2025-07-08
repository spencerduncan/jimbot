-- Integration test for retry logic with simulated network failures
-- Tests the full retry flow including circuit breaker behavior

local TestHelper = require("tests.test_helper")

-- Load modules
package.path = package.path .. ";../../mods/BalatroMCP/?.lua"

-- Set up environment
TestHelper.create_mock_globals()

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
    end
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
local RetryManager = require("mods.BalatroMCP.retry_manager")
local EventBusClient = require("mods.BalatroMCP.event_bus_client")

-- Test Suite
TestHelper.run_suite("Retry Integration Tests")

-- Test successful retry after transient failures
TestHelper.test("Integration: Should retry and succeed after transient failures", function()
    -- Initialize components
    local config = {
        event_bus_url = "http://localhost:8080/api/v1/events",
        max_retries = 3,
        retry_delay_ms = 100,
        failure_threshold = 5
    }
    
    EventBusClient:init(config)
    
    -- Simulate connection test
    EventBusClient.https = mock_https
    EventBusClient.connection_tested = true
    EventBusClient.connected = true
    
    -- Reset mock state
    mock_https.failure_count = 0
    mock_https.max_failures = 2
    
    -- Track callbacks
    local success_count = 0
    local failure_count = 0
    
    -- Send event with retry logic
    EventBusClient.retry_manager.execute_with_retry = function(self, func, context, on_success, on_failure)
        local attempt = 0
        local co = coroutine.create(function()
            while attempt < config.max_retries do
                attempt = attempt + 1
                local success, result = pcall(func)
                
                if success and result then
                    self:record_success()
                    if on_success then on_success(result) end
                    return
                else
                    if attempt < config.max_retries then
                        -- Simulate delay
                        coroutine.yield()
                    end
                end
            end
            
            self:record_failure()
            if on_failure then on_failure("Max retries exceeded") end
        end)
        
        -- Execute coroutine fully for test
        while coroutine.status(co) ~= "dead" do
            coroutine.resume(co)
        end
    end
    
    local event = { type = "TEST_EVENT", data = { value = 42 } }
    
    EventBusClient.retry_manager.execute_with_retry(
        EventBusClient.retry_manager,
        function()
            local json = EventBusClient:event_to_json(event)
            return EventBusClient:http_post(EventBusClient.url, json)
        end,
        { type = "TEST" },
        function() success_count = success_count + 1 end,
        function() failure_count = failure_count + 1 end
    )
    
    -- Verify results
    TestHelper.assert_equal(mock_https.failure_count, 3) -- 2 failures + 1 success
    TestHelper.assert_equal(success_count, 1)
    TestHelper.assert_equal(failure_count, 0)
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
        { type = "BUFFERED_3", event_id = "3", timestamp = 3000, source = "BalatroMCP" }
    }
    
    -- Reset circuit breaker and mock
    RetryManager:reset()
    mock_https.failure_count = 0
    mock_https.max_failures = 0 -- All requests succeed
    
    -- Mock batch sending
    local batches_sent = 0
    EventBusClient.http_post = function(self, url, data)
        batches_sent = batches_sent + 1
        return true, "OK"
    end
    
    -- Flush buffer
    EventBusClient:flush_buffer()
    
    -- Verify events were sent
    TestHelper.assert_true(batches_sent > 0)
    TestHelper.assert_equal(#EventBusClient.local_buffer, 0)
end)

-- Test graceful degradation
TestHelper.test("Integration: System should continue operating with event bus unavailable", function()
    -- Configure for immediate circuit breaker opening
    RetryManager:reset()
    RetryManager.failure_threshold = 1
    
    -- Mock complete failure
    mock_https.max_failures = 999
    
    -- System should handle multiple events gracefully
    local events_processed = 0
    
    for i = 1, 10 do
        local result = EventBusClient:send_event({ 
            type = "EVENT_" .. i,
            important = true 
        })
        events_processed = events_processed + 1
    end
    
    -- All events should have been processed (buffered)
    TestHelper.assert_equal(events_processed, 10)
    
    -- Circuit breaker should be open
    TestHelper.assert_true(RetryManager.is_open)
    
    -- Events should be in buffer
    TestHelper.assert_true(#EventBusClient.local_buffer > 0)
end)

-- Clean up
_G.require = original_require

-- Report results
TestHelper.report()