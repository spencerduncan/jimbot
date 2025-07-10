-- Test script for event aggregation performance
-- Simulates complex joker cascades

local test_aggregation = {}

-- Mock Love2D timer
local mock_time = 0
love = love or {}
love.timer = love.timer or {}
love.timer.getTime = function()
	return mock_time
end

-- Load modules
package.path = package.path .. ";./?.lua;./mods/BalatroMCP/?.lua"
local EventAggregator = require("event_aggregator")
local EventBusClient = require("event_bus_client")

-- Create test instances
local aggregator = EventAggregator
local event_bus = EventBusClient

-- Mock logger
local mock_logger = {
	info = function(self, msg, data)
		print("[INFO] " .. msg)
	end,
	debug = function(self, msg, data) end,
	warn = function(self, msg, data)
		print("[WARN] " .. msg)
	end,
	error = function(self, msg, data)
		print("[ERROR] " .. msg .. " - " .. tostring(data and data.error or ""))
	end,
}

-- Mock components
BalatroMCP = {
	components = {
		logger = mock_logger,
		event_bus = event_bus,
	},
}

-- Initialize components
event_bus:init({
	event_bus_url = "http://localhost:8080/api/v1/events",
	event_bus_timeout = 5000,
})
aggregator:init(100) -- 100ms batch window
aggregator.event_bus = event_bus

-- Test 1: Single event should wait for batch window
function test_aggregation.test_single_event_batching()
	print("\n=== Test 1: Single Event Batching ===")

	-- Add single event
	aggregator:add_event({
		type = "TEST_EVENT",
		source = "test",
		payload = { test = 1 },
	})

	-- Should not send immediately
	local stats = aggregator:get_stats()
	print("Events queued: " .. stats.events_queued)
	print("Batches sent: " .. stats.batches_sent)

	-- Advance time by 50ms - should not trigger
	mock_time = 0.05
	aggregator:update(0.05)
	stats = aggregator:get_stats()
	print("After 50ms - Batches sent: " .. stats.batches_sent)

	-- Advance time past batch window
	mock_time = 0.11
	aggregator:update(0.06)
	stats = aggregator:get_stats()
	print("After 110ms - Batches sent: " .. stats.batches_sent)
end

-- Test 2: Complex joker cascade simulation
function test_aggregation.test_joker_cascade()
	print("\n=== Test 2: Joker Cascade Simulation ===")

	-- Reset stats
	aggregator.stats = {
		events_queued = 0,
		batches_sent = 0,
		events_sent = 0,
		events_dropped = 0,
	}
	aggregator.event_queue = {}
	mock_time = 0

	-- Simulate 100 joker triggers in rapid succession
	print("Simulating 100 joker triggers...")
	local start_time = mock_time

	for i = 1, 100 do
		aggregator:add_event({
			type = "JOKER_TRIGGER",
			source = "BalatroMCP",
			priority = "low",
			payload = {
				joker_name = "Joker_" .. i,
				context_type = "scoring",
				trigger_index = i,
			},
		})

		-- Simulate slight time progression (1ms per trigger)
		mock_time = mock_time + 0.001
	end

	print("All events queued in " .. ((mock_time - start_time) * 1000) .. "ms")

	-- Update to trigger batch send
	mock_time = mock_time + 0.1
	aggregator:update(0.1)

	local stats = aggregator:get_stats()
	print("\nFinal Statistics:")
	print("Events queued: " .. stats.events_queued)
	print("Batches sent: " .. stats.batches_sent)
	print("Events sent: " .. stats.events_sent)
	print("Events dropped: " .. stats.events_dropped)
	print("Average events per batch: " .. stats.avg_events_per_batch)
end

-- Test 3: High priority events
function test_aggregation.test_high_priority()
	print("\n=== Test 3: High Priority Event ===")

	-- Reset
	aggregator.event_queue = {}
	aggregator.last_flush_time = love.timer.getTime() * 1000

	-- Add normal event
	aggregator:add_event({
		type = "NORMAL_EVENT",
		source = "test",
		payload = { data = "normal" },
	})

	local stats_before = aggregator:get_stats()

	-- Add high priority event - should trigger immediate flush
	aggregator:add_event({
		type = "ERROR",
		source = "test",
		priority = "high",
		payload = { error = "test error" },
	})

	local stats_after = aggregator:get_stats()
	print("Batches sent after high priority: " .. (stats_after.batches_sent - stats_before.batches_sent))
end

-- Test 4: Game state aggregation
function test_aggregation.test_game_state_aggregation()
	print("\n=== Test 4: Game State Aggregation ===")

	-- Reset
	aggregator.event_queue = {}
	mock_time = 0

	-- Add multiple game states for same frame
	for i = 1, 5 do
		aggregator:add_event({
			type = "GAME_STATE",
			source = "BalatroMCP",
			timestamp = mock_time * 1000,
			payload = {
				frame_count = 100,
				chips = 1000 + i * 100,
				mult = 10 + i,
			},
		})
	end

	-- Add game states for different frame
	for i = 1, 3 do
		aggregator:add_event({
			type = "GAME_STATE",
			source = "BalatroMCP",
			timestamp = (mock_time + 0.001) * 1000,
			payload = {
				frame_count = 101,
				chips = 2000 + i * 100,
				mult = 20 + i,
			},
		})
	end

	print("Queued 8 game state events (5 for frame 100, 3 for frame 101)")

	-- Trigger aggregation
	aggregator:flush()

	print("After aggregation: " .. #aggregator.event_queue .. " events remaining")
end

-- Run all tests
function test_aggregation.run_all()
	print("=== Event Aggregation Performance Tests ===")
	test_aggregation.test_single_event_batching()
	test_aggregation.test_joker_cascade()
	test_aggregation.test_high_priority()
	test_aggregation.test_game_state_aggregation()
	print("\n=== All tests completed ===")
end

-- If running directly
if arg and arg[0] and arg[0]:match("test_event_aggregation%.lua$") then
	test_aggregation.run_all()
end

return test_aggregation
