-- Test file for event aggregation functionality
local lu = require("luaunit")

-- Mock love.timer for testing
love = love or {}
love.timer = love.timer or {}
local mock_time = 0
love.timer.getTime = function()
    return mock_time
end

-- Mock BalatroMCP structure
BalatroMCP = {
    components = {
        logger = {
            info = function() end,
            debug = function() end,
            error = function() end,
        },
        event_bus = {
            send_event = function(self, event)
                -- Track sent events for testing
                self.sent_events = self.sent_events or {}
                table.insert(self.sent_events, event)
                return true
            end,
            sent_events = {},
        },
    },
}

-- Load the event aggregator
package.path = package.path .. ";../?.lua"
local EventAggregator = require("event_aggregator")

TestEventAggregator = {}

function TestEventAggregator:setUp()
    -- Reset mock time
    mock_time = 0
    -- Clear sent events
    BalatroMCP.components.event_bus.sent_events = {}
    -- Create fresh aggregator instance
    self.aggregator = EventAggregator:new()
    self.aggregator:init(100) -- 100ms batch window
    self.aggregator.event_bus = BalatroMCP.components.event_bus
end

function TestEventAggregator:test_basic_batching()
    -- Add multiple events within batch window
    self.aggregator:add_event({ type = "TEST_EVENT_1", payload = { id = 1 } })
    self.aggregator:add_event({ type = "TEST_EVENT_2", payload = { id = 2 } })
    self.aggregator:add_event({ type = "TEST_EVENT_3", payload = { id = 3 } })

    -- Events should be queued, not sent yet
    lu.assertEquals(#BalatroMCP.components.event_bus.sent_events, 0)
    lu.assertEquals(self.aggregator.queue_size, 3)

    -- Advance time past batch window
    mock_time = 0.15 -- 150ms
    self.aggregator:add_event({ type = "TEST_EVENT_4", payload = { id = 4 } })

    -- Should have sent one batch with 3 events
    lu.assertEquals(#BalatroMCP.components.event_bus.sent_events, 1)
    local batch = BalatroMCP.components.event_bus.sent_events[1]
    lu.assertEquals(batch.type, "EVENT_BATCH")
    lu.assertEquals(#batch.payload.events, 3)

    -- New event should be in queue
    lu.assertEquals(self.aggregator.queue_size, 1)
end

function TestEventAggregator:test_high_priority_bypass()
    -- Add normal event
    self.aggregator:add_event({ type = "NORMAL_EVENT", payload = { id = 1 } })
    lu.assertEquals(#BalatroMCP.components.event_bus.sent_events, 0)

    -- Add high priority event
    self.aggregator:add_event({
        type = "HIGH_PRIORITY_EVENT",
        priority = "high",
        payload = { id = 2 },
    })

    -- High priority should be sent immediately
    lu.assertEquals(#BalatroMCP.components.event_bus.sent_events, 1)
    lu.assertEquals(BalatroMCP.components.event_bus.sent_events[1].type, "HIGH_PRIORITY_EVENT")

    -- Normal event should still be queued
    lu.assertEquals(self.aggregator.queue_size, 1)
end

function TestEventAggregator:test_max_batch_size()
    -- Add events exceeding max batch size
    for i = 1, 55 do
        self.aggregator:add_event({ type = "TEST_EVENT", payload = { id = i } })
    end

    -- Should have sent one batch with max size (50)
    lu.assertEquals(#BalatroMCP.components.event_bus.sent_events, 1)
    local batch = BalatroMCP.components.event_bus.sent_events[1]
    lu.assertEquals(#batch.payload.events, 50)

    -- Remaining events should be queued
    lu.assertEquals(self.aggregator.queue_size, 5)
end

function TestEventAggregator:test_force_flush()
    -- Add events
    self.aggregator:add_event({ type = "TEST_EVENT_1", payload = { id = 1 } })
    self.aggregator:add_event({ type = "TEST_EVENT_2", payload = { id = 2 } })

    -- Force flush
    self.aggregator:flush()

    -- Should have sent batch immediately
    lu.assertEquals(#BalatroMCP.components.event_bus.sent_events, 1)
    local batch = BalatroMCP.components.event_bus.sent_events[1]
    lu.assertEquals(#batch.payload.events, 2)
    lu.assertEquals(self.aggregator.queue_size, 0)
end

function TestEventAggregator:test_empty_flush()
    -- Flush with no events
    self.aggregator:flush()

    -- Should not send anything
    lu.assertEquals(#BalatroMCP.components.event_bus.sent_events, 0)
end

function TestEventAggregator:test_joker_cascade_batching()
    -- Simulate joker cascade during scoring
    BalatroMCP.in_scoring_sequence = true

    -- Add multiple joker trigger events rapidly
    for i = 1, 10 do
        self.aggregator:add_event({
            type = "JOKER_TRIGGER",
            priority = "low",
            payload = {
                joker_name = "Joker_" .. i,
                timestamp = mock_time * 1000,
            },
        })
        mock_time = mock_time + 0.001 -- 1ms apart
    end

    -- Events should be batched
    lu.assertEquals(#BalatroMCP.components.event_bus.sent_events, 0)
    lu.assertEquals(self.aggregator.queue_size, 10)

    -- Flush at end of scoring
    self.aggregator:flush()

    -- Should send all joker events as one batch
    lu.assertEquals(#BalatroMCP.components.event_bus.sent_events, 1)
    local batch = BalatroMCP.components.event_bus.sent_events[1]
    lu.assertEquals(#batch.payload.events, 10)
end

-- Run tests if executed directly
if arg and arg[0]:match("test_event_aggregation.lua$") then
    os.exit(lu.LuaUnit.run())
end

return TestEventAggregator
