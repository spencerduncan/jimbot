-- Test suite for event_bus_client.lua
-- Tests non-blocking event sending, circuit breaker integration, and local buffering

local TestHelper = require("tests.test_helper")

-- Load the module under test
package.path = package.path .. ";../../mods/BalatroMCP/?.lua"

-- Set up environment
TestHelper.create_mock_globals()

-- Mock the retry manager
local mock_retry_manager = {
    can_attempt = TestHelper.mock_function("retry_manager.can_attempt", true),
    execute_with_retry = TestHelper.mock_function("retry_manager.execute_with_retry"),
    update = TestHelper.mock_function("retry_manager.update"),
    get_status = TestHelper.mock_function("retry_manager.get_status", {
        is_open = false,
        half_open = false,
        failure_count = 0,
        consecutive_failures = 0,
        active_retries = 0,
        can_attempt = true
    }),
    record_success = TestHelper.mock_function("retry_manager.record_success"),
    record_failure = TestHelper.mock_function("retry_manager.record_failure"),
    init = TestHelper.mock_function("retry_manager.init")
}

-- Override require to return our mock
local original_require = require
_G.require = function(module)
    if module == "mods.BalatroMCP.retry_manager" then
        return mock_retry_manager
    end
    return original_require(module)
end

-- Load the event bus client
local EventBusClient = require("mods.BalatroMCP.event_bus_client")

-- Test Suite
TestHelper.run_suite("EventBusClient")

-- Test initialization
TestHelper.test("EventBusClient:init - should initialize with correct configuration", function()
    local config = {
        event_bus_url = "http://localhost:8080/api/v1/events",
        event_bus_timeout = 3000,
        max_retries = 5,
        retry_delay_ms = 2000,
        max_buffer_size = 500
    }
    
    EventBusClient:init(config)
    
    TestHelper.assert_equal(EventBusClient.url, "http://localhost:8080/api/v1/events")
    TestHelper.assert_equal(EventBusClient.timeout, 3)
    TestHelper.assert_equal(EventBusClient.max_retries, 5)
    TestHelper.assert_equal(EventBusClient.retry_delay, 2)
    TestHelper.assert_equal(EventBusClient.max_buffer_size, 500)
    TestHelper.assert_not_nil(EventBusClient.retry_manager)
    TestHelper.assert_called("retry_manager.init", 1)
end)

-- Test non-blocking send_event
TestHelper.test("EventBusClient:send_event - should use retry manager for async sending", function()
    EventBusClient.connection_tested = true
    EventBusClient.retry_manager = mock_retry_manager
    
    -- Reset mock calls
    TestHelper.reset_mocks()
    mock_retry_manager.can_attempt = TestHelper.mock_function("retry_manager.can_attempt", true)
    mock_retry_manager.execute_with_retry = TestHelper.mock_function("retry_manager.execute_with_retry")
    
    local event = {
        type = "TEST_EVENT",
        data = { value = 42 }
    }
    
    local result = EventBusClient:send_event(event)
    
    TestHelper.assert_true(result)
    TestHelper.assert_called("retry_manager.can_attempt", 1)
    TestHelper.assert_called("retry_manager.execute_with_retry", 1)
    TestHelper.assert_not_nil(event.event_id)
    TestHelper.assert_not_nil(event.timestamp)
    TestHelper.assert_equal(event.source, "BalatroMCP")
end)

-- Test buffering when circuit breaker is open
TestHelper.test("EventBusClient:send_event - should buffer events when circuit breaker is open", function()
    EventBusClient.connection_tested = true
    EventBusClient.local_buffer = {}
    
    -- Mock circuit breaker as open
    TestHelper.reset_mocks()
    mock_retry_manager.can_attempt = TestHelper.mock_function("retry_manager.can_attempt", false)
    
    local event = {
        type = "TEST_EVENT",
        data = { value = 42 }
    }
    
    local result = EventBusClient:send_event(event)
    
    TestHelper.assert_false(result)
    TestHelper.assert_equal(#EventBusClient.local_buffer, 1)
    TestHelper.assert_equal(EventBusClient.local_buffer[1].type, "TEST_EVENT")
    TestHelper.assert_not_called("retry_manager.execute_with_retry")
end)

-- Test batch sending
TestHelper.test("EventBusClient:send_batch - should send events as batch", function()
    EventBusClient.connection_tested = true
    EventBusClient.retry_manager = mock_retry_manager
    
    TestHelper.reset_mocks()
    mock_retry_manager.can_attempt = TestHelper.mock_function("retry_manager.can_attempt", true)
    mock_retry_manager.execute_with_retry = TestHelper.mock_function("retry_manager.execute_with_retry")
    
    local events = {
        { type = "EVENT_1", data = { id = 1 } },
        { type = "EVENT_2", data = { id = 2 } },
        { type = "EVENT_3", data = { id = 3 } }
    }
    
    local result = EventBusClient:send_batch(events)
    
    TestHelper.assert_true(result)
    TestHelper.assert_called("retry_manager.execute_with_retry", 1)
    
    -- Check all events have metadata
    for _, event in ipairs(events) do
        TestHelper.assert_not_nil(event.event_id)
        TestHelper.assert_not_nil(event.timestamp)
        TestHelper.assert_equal(event.source, "BalatroMCP")
    end
end)

-- Test local buffer management
TestHelper.test("EventBusClient:buffer_event - should add events to local buffer", function()
    EventBusClient.local_buffer = {}
    EventBusClient.max_buffer_size = 3
    
    for i = 1, 3 do
        EventBusClient:buffer_event({ type = "EVENT_" .. i })
    end
    
    TestHelper.assert_equal(#EventBusClient.local_buffer, 3)
end)

TestHelper.test("EventBusClient:buffer_event - should drop oldest events when buffer is full", function()
    EventBusClient.local_buffer = {}
    EventBusClient.max_buffer_size = 3
    
    for i = 1, 5 do
        EventBusClient:buffer_event({ type = "EVENT_" .. i })
    end
    
    TestHelper.assert_equal(#EventBusClient.local_buffer, 3)
    TestHelper.assert_equal(EventBusClient.local_buffer[1].type, "EVENT_3")
    TestHelper.assert_equal(EventBusClient.local_buffer[3].type, "EVENT_5")
end)

-- Test buffer flushing
TestHelper.test("EventBusClient:flush_buffer - should send buffered events when circuit breaker allows", function()
    EventBusClient.local_buffer = {
        { type = "BUFFERED_1" },
        { type = "BUFFERED_2" },
        { type = "BUFFERED_3" }
    }
    
    TestHelper.reset_mocks()
    mock_retry_manager.can_attempt = TestHelper.mock_function("retry_manager.can_attempt", true)
    
    -- Mock send_batch to clear buffer
    EventBusClient.send_batch = TestHelper.mock_function("send_batch", function(self, events)
        -- Simulate successful send by removing from buffer
        for i = 1, #events do
            table.remove(self.local_buffer, 1)
        end
        return true
    end)
    
    EventBusClient:flush_buffer()
    
    TestHelper.assert_called("send_batch")
    TestHelper.assert_equal(#EventBusClient.local_buffer, 0)
end)

-- Test update method
TestHelper.test("EventBusClient:update - should update retry manager", function()
    EventBusClient.retry_manager = mock_retry_manager
    
    TestHelper.reset_mocks()
    mock_retry_manager.update = TestHelper.mock_function("retry_manager.update")
    
    EventBusClient:update(0.016)
    
    TestHelper.assert_called("retry_manager.update", 1)
end)

-- Test status reporting
TestHelper.test("EventBusClient:get_status - should return comprehensive status", function()
    EventBusClient.connected = true
    EventBusClient.event_queue = { {}, {} }
    EventBusClient.local_buffer = { {}, {}, {} }
    EventBusClient.url = "http://localhost:8080"
    EventBusClient.retry_manager = mock_retry_manager
    
    local status = EventBusClient:get_status()
    
    TestHelper.assert_equal(status.connected, true)
    TestHelper.assert_equal(status.event_queue_size, 2)
    TestHelper.assert_equal(status.local_buffer_size, 3)
    TestHelper.assert_equal(status.url, "http://localhost:8080")
    TestHelper.assert_not_nil(status.circuit_breaker)
end)

-- Test health check
TestHelper.test("EventBusClient:check_health - should perform health check", function()
    EventBusClient.retry_manager = mock_retry_manager
    
    TestHelper.reset_mocks()
    mock_retry_manager.can_attempt = TestHelper.mock_function("retry_manager.can_attempt", true)
    mock_retry_manager.record_success = TestHelper.mock_function("retry_manager.record_success")
    
    -- Mock successful HTTP POST
    EventBusClient.http_post = TestHelper.mock_function("http_post", function()
        return true, "OK"
    end)
    
    local healthy, message = EventBusClient:check_health()
    
    TestHelper.assert_true(healthy)
    TestHelper.assert_equal(message, "Healthy")
    TestHelper.assert_called("retry_manager.record_success", 1)
end)

TestHelper.test("EventBusClient:check_health - should handle circuit breaker open state", function()
    EventBusClient.retry_manager = mock_retry_manager
    
    TestHelper.reset_mocks()
    mock_retry_manager.can_attempt = TestHelper.mock_function("retry_manager.can_attempt", false)
    
    local healthy, message = EventBusClient:check_health()
    
    TestHelper.assert_false(healthy)
    TestHelper.assert_equal(message, "Circuit breaker is open")
end)

-- Test retry callback handling
TestHelper.test("EventBusClient retry callbacks - should handle success callback", function()
    EventBusClient.connection_tested = true
    EventBusClient.retry_manager = mock_retry_manager
    
    TestHelper.reset_mocks()
    local success_callback = nil
    mock_retry_manager.execute_with_retry = TestHelper.mock_function("retry_manager.execute_with_retry", 
        function(func, context, on_success, on_failure)
            success_callback = on_success
        end
    )
    
    local event = { type = "TEST" }
    EventBusClient:send_event(event)
    
    -- Simulate successful send by calling the success callback
    TestHelper.assert_not_nil(success_callback)
    success_callback("OK")
    
    TestHelper.assert_true(EventBusClient.connected)
end)

TestHelper.test("EventBusClient retry callbacks - should handle failure callback", function()
    EventBusClient.connection_tested = true
    EventBusClient.retry_manager = mock_retry_manager
    EventBusClient.local_buffer = {}
    
    TestHelper.reset_mocks()
    local failure_callback = nil
    mock_retry_manager.execute_with_retry = TestHelper.mock_function("retry_manager.execute_with_retry", 
        function(func, context, on_success, on_failure)
            failure_callback = on_failure
        end
    )
    
    local event = { type = "TEST", event_id = "123" }
    EventBusClient:send_event(event)
    
    -- Simulate failed send by calling the failure callback
    TestHelper.assert_not_nil(failure_callback)
    failure_callback("Connection refused")
    
    -- Event should be buffered
    TestHelper.assert_equal(#EventBusClient.local_buffer, 1)
    TestHelper.assert_equal(EventBusClient.local_buffer[1].type, "TEST")
end)

-- Clean up
_G.require = original_require

-- Report results
TestHelper.report()