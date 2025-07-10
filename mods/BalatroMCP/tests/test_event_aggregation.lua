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
				return true
			end,
			send_batch = function(self, events)
				return true
			end,
		},
	},
}

-- Load the module under test
local EventAggregator = require("mods.BalatroMCP.event_aggregator")

-- Test Suite
TestEventAggregator = {}

function TestEventAggregator:setUp()
	-- Reset mock time
	mock_time = 0

	-- Reset aggregator state
	EventAggregator.event_queue = {}
	EventAggregator.stats = {
		events_queued = 0,
		batches_sent = 0,
		events_sent = 0,
		events_dropped = 0,
	}
	EventAggregator.last_flush_time = 0

	-- Initialize aggregator
	EventAggregator:init(100) -- 100ms batch window
end

function TestEventAggregator:test_init()
	-- Test initialization
	lu.assertEquals(EventAggregator.batch_window_ms, 100)
	lu.assertEquals(EventAggregator.max_batch_size, 50)
	lu.assertNotNil(EventAggregator.logger)
	lu.assertNotNil(EventAggregator.event_bus)
end

function TestEventAggregator:test_add_event()
	-- Add a single event
	local event = {
		type = "TEST_EVENT",
		source = "test",
		payload = { value = 42 },
	}

	EventAggregator:add_event(event)

	-- Check event was queued
	lu.assertEquals(#EventAggregator.event_queue, 1)
	lu.assertEquals(EventAggregator.stats.events_queued, 1)

	-- Check timestamp was added
	lu.assertNotNil(EventAggregator.event_queue[1].timestamp)
end

function TestEventAggregator:test_batch_window()
	-- Add events
	EventAggregator:add_event({ type = "EVENT_1" })
	EventAggregator:add_event({ type = "EVENT_2" })

	-- Events should be queued
	lu.assertEquals(#EventAggregator.event_queue, 2)

	-- Update within batch window - should not flush
	mock_time = 0.05 -- 50ms
	EventAggregator:update(0.05)
	lu.assertEquals(#EventAggregator.event_queue, 2)
	lu.assertEquals(EventAggregator.stats.batches_sent, 0)

	-- Update past batch window - should flush
	mock_time = 0.11 -- 110ms
	EventAggregator:update(0.06)
	lu.assertEquals(#EventAggregator.event_queue, 0)
	lu.assertEquals(EventAggregator.stats.batches_sent, 1)
	lu.assertEquals(EventAggregator.stats.events_sent, 2)
end

function TestEventAggregator:test_high_priority_immediate_flush()
	-- Add normal event
	EventAggregator:add_event({ type = "NORMAL", priority = "normal" })
	lu.assertEquals(#EventAggregator.event_queue, 1)

	-- Add high priority event - should trigger immediate flush
	EventAggregator:add_event({ type = "ERROR", priority = "high" })

	-- Both events should be flushed
	lu.assertEquals(#EventAggregator.event_queue, 0)
	lu.assertEquals(EventAggregator.stats.batches_sent, 1)
	lu.assertEquals(EventAggregator.stats.events_sent, 2)
end

function TestEventAggregator:test_max_batch_size()
	-- Add more events than max batch size
	for i = 1, 60 do
		EventAggregator:add_event({ type = "EVENT_" .. i })
	end

	-- Should have all 60 events queued
	lu.assertEquals(#EventAggregator.event_queue, 60)

	-- Flush should send in batches
	EventAggregator:flush()

	-- Should have sent 50 events (max batch size)
	lu.assertEquals(EventAggregator.stats.events_sent, 50)
	lu.assertEquals(#EventAggregator.event_queue, 10) -- 10 remaining
end

function TestEventAggregator:test_queue_overflow_protection()
	-- Fill queue beyond limit (max_batch_size * 2 = 100)
	for i = 1, 110 do
		EventAggregator:add_event({ type = "EVENT_" .. i })
	end

	-- Should have dropped some events
	lu.assertTrue(EventAggregator.stats.events_dropped > 0)
	lu.assertEquals(#EventAggregator.event_queue, 100) -- Queue capped at 100
end

function TestEventAggregator:test_game_state_aggregation()
	-- Add multiple game states for same frame
	for i = 1, 5 do
		EventAggregator:add_event({
			type = "GAME_STATE",
			timestamp = 1000,
			payload = {
				frame_count = 100,
				chips = 1000 + i * 100,
			},
		})
	end

	-- Add game states for different frame
	for i = 1, 3 do
		EventAggregator:add_event({
			type = "GAME_STATE",
			timestamp = 2000 + i,
			payload = {
				frame_count = 101,
				chips = 2000 + i * 100,
			},
		})
	end

	-- Process aggregation
	local aggregated = EventAggregator:aggregate_events(EventAggregator.event_queue)

	-- Should have 2 game states (one per frame) + 0 other events
	local game_state_count = 0
	for _, event in ipairs(aggregated) do
		if event.type == "GAME_STATE" then
			game_state_count = game_state_count + 1
		end
	end

	lu.assertEquals(game_state_count, 2)

	-- Check we kept the latest for each frame
	local frame_100_found = false
	local frame_101_found = false

	for _, event in ipairs(aggregated) do
		if event.type == "GAME_STATE" then
			if event.payload.frame_count == 100 then
				frame_100_found = true
				-- Should have the last chips value for frame 100
				lu.assertEquals(event.payload.chips, 1500)
			elseif event.payload.frame_count == 101 then
				frame_101_found = true
				-- Should have the last chips value for frame 101
				lu.assertEquals(event.payload.chips, 2300)
			end
		end
	end

	lu.assertTrue(frame_100_found)
	lu.assertTrue(frame_101_found)
end

function TestEventAggregator:test_stats_tracking()
	-- Add and process some events
	for i = 1, 5 do
		EventAggregator:add_event({ type = "EVENT_" .. i })
	end

	-- Force flush
	EventAggregator:flush()

	-- Check stats
	local stats = EventAggregator:get_stats()
	lu.assertEquals(stats.events_queued, 5)
	lu.assertEquals(stats.batches_sent, 1)
	lu.assertEquals(stats.events_sent, 5)
	lu.assertEquals(stats.events_dropped, 0)
	lu.assertEquals(stats.avg_events_per_batch, 5)
end

function TestEventAggregator:test_event_sorting()
	-- Add events with different timestamps
	EventAggregator:add_event({ type = "EVENT_3", timestamp = 3000 })
	EventAggregator:add_event({ type = "EVENT_1", timestamp = 1000 })
	EventAggregator:add_event({ type = "EVENT_2", timestamp = 2000 })

	-- Process queue
	local sorted = EventAggregator:sort_events_by_timestamp(EventAggregator.event_queue)

	-- Check events are sorted by timestamp
	lu.assertEquals(sorted[1].type, "EVENT_1")
	lu.assertEquals(sorted[2].type, "EVENT_2")
	lu.assertEquals(sorted[3].type, "EVENT_3")
end

-- Run tests
os.exit(lu.LuaUnit.run())
