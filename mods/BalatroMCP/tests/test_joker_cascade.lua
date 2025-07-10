-- Performance test for joker cascade event aggregation
local lu = require("luaunit")

-- Mock love.timer
love = love or {}
love.timer = love.timer or {}
local mock_time = 0
love.timer.getTime = function()
	return mock_time
end

-- Track HTTP requests
local http_requests = 0
local total_events_sent = 0

-- Mock BalatroMCP with request tracking
BalatroMCP = {
	components = {
		logger = {
			info = function(self, msg)
				if msg:match("Batch sent") then
					print("[INFO] " .. msg)
				end
			end,
			debug = function() end,
			error = function() end,
			warn = function() end,
		},
		event_bus = {
			send_event = function(self, event)
				http_requests = http_requests + 1
				total_events_sent = total_events_sent + 1
				return true
			end,
			send_batch = function(self, events)
				http_requests = http_requests + 1
				total_events_sent = total_events_sent + #events
				print("[BATCH] Sent " .. #events .. " events in 1 HTTP request")
				return true
			end,
		},
	},
	in_scoring_sequence = false,
}

-- Load the module
local EventAggregator = require("mods.BalatroMCP.event_aggregator")

-- Test Suite
TestJokerCascade = {}

function TestJokerCascade:setUp()
	-- Reset counters
	http_requests = 0
	total_events_sent = 0
	mock_time = 0

	-- Reset aggregator
	EventAggregator.event_queue = {}
	EventAggregator.stats = {
		events_queued = 0,
		batches_sent = 0,
		events_sent = 0,
		events_dropped = 0,
	}
	EventAggregator.last_flush_time = 0

	-- Initialize with 100ms window
	EventAggregator:init(100)
end

function TestJokerCascade:test_complex_joker_cascade()
	print("\n=== Complex Joker Cascade Test ===")

	-- Simulate scoring sequence start
	BalatroMCP.in_scoring_sequence = true
	local start_time = mock_time

	-- Simulate rapid joker triggers (100+ events)
	local num_triggers = 100
	print("Simulating " .. num_triggers .. " joker triggers...")

	for i = 1, num_triggers do
		EventAggregator:add_event({
			type = "JOKER_TRIGGER",
			source = "BalatroMCP",
			priority = "low",
			payload = {
				joker_name = "Joker_" .. (i % 10), -- Simulate 10 different jokers
				context_type = "scoring",
				trigger_index = i,
				timestamp = mock_time * 1000,
			},
		})

		-- Advance time slightly (0.5ms per trigger)
		mock_time = mock_time + 0.0005
	end

	local cascade_duration = (mock_time - start_time) * 1000
	print("Cascade duration: " .. cascade_duration .. "ms")

	-- Check events are queued
	lu.assertEquals(#EventAggregator.event_queue, num_triggers)
	lu.assertEquals(http_requests, 0) -- No requests yet

	-- Simulate end of scoring sequence - should flush
	BalatroMCP.in_scoring_sequence = false
	EventAggregator:flush()

	-- Check results
	print("\nResults:")
	print("Total events: " .. num_triggers)
	print("HTTP requests made: " .. http_requests)
	print("Events sent: " .. total_events_sent)
	print("Batches sent: " .. EventAggregator.stats.batches_sent)
	print("Average events per batch: " .. EventAggregator.stats.avg_events_per_batch)

	-- Verify performance improvement
	lu.assertEquals(total_events_sent, num_triggers)
	lu.assertTrue(http_requests <= 3, "Should batch into 3 or fewer requests")
	lu.assertTrue(http_requests < num_triggers / 10, "Should be significantly fewer requests than events")
end

function TestJokerCascade:test_mixed_priority_cascade()
	print("\n=== Mixed Priority Cascade Test ===")

	-- Start scoring
	BalatroMCP.in_scoring_sequence = true

	-- Add 50 low priority joker triggers
	for i = 1, 50 do
		EventAggregator:add_event({
			type = "JOKER_TRIGGER",
			priority = "low",
			payload = { joker_name = "Regular_" .. i },
		})
	end

	-- Add an error event (high priority)
	EventAggregator:add_event({
		type = "ERROR",
		priority = "high",
		payload = { error = "Joker calculation failed" },
	})

	-- Should have flushed due to high priority
	lu.assertTrue(EventAggregator.stats.batches_sent > 0)

	-- Add more events after error
	for i = 51, 100 do
		EventAggregator:add_event({
			type = "JOKER_TRIGGER",
			priority = "low",
			payload = { joker_name = "Regular_" .. i },
		})
	end

	-- End scoring - flush remaining
	BalatroMCP.in_scoring_sequence = false
	EventAggregator:flush()

	print("Total HTTP requests: " .. http_requests)
	print("Total events sent: " .. total_events_sent)

	-- Should have sent all events in just a few requests
	lu.assertEquals(total_events_sent, 101) -- 100 jokers + 1 error
	lu.assertTrue(http_requests <= 4, "Should batch efficiently even with high priority interruption")
end

function TestJokerCascade:test_real_world_scenario()
	print("\n=== Real World Scenario Test ===")

	-- Simulate a real game scenario with multiple scoring sequences
	local total_sequences = 5
	local total_events_generated = 0

	for sequence = 1, total_sequences do
		print("\nScoring sequence " .. sequence)

		-- Start scoring
		BalatroMCP.in_scoring_sequence = true

		-- Variable number of triggers per sequence
		local triggers_this_sequence = math.random(20, 150)
		print("Triggers this sequence: " .. triggers_this_sequence)

		for i = 1, triggers_this_sequence do
			EventAggregator:add_event({
				type = "JOKER_TRIGGER",
				priority = "low",
				payload = {
					joker_name = "Joker_" .. math.random(1, 15),
					sequence = sequence,
					trigger = i,
				},
			})

			-- Simulate time passing
			mock_time = mock_time + 0.001

			-- Occasionally update aggregator mid-sequence
			if i % 30 == 0 then
				EventAggregator:update(0.001)
			end
		end

		total_events_generated = total_events_generated + triggers_this_sequence

		-- End scoring - flush
		BalatroMCP.in_scoring_sequence = false
		EventAggregator:flush()

		-- Pause between sequences
		mock_time = mock_time + 1.0
	end

	print("\n=== Final Results ===")
	print("Total scoring sequences: " .. total_sequences)
	print("Total events generated: " .. total_events_generated)
	print("Total HTTP requests: " .. http_requests)
	print("Total events sent: " .. total_events_sent)
	print("Average events per request: " .. (total_events_sent / http_requests))

	-- Performance assertions
	lu.assertEquals(total_events_sent, total_events_generated)
	local expected_max_requests = math.ceil(total_sequences * 3) -- Max 3 requests per sequence
	lu.assertTrue(http_requests <= expected_max_requests, "Should batch efficiently across multiple sequences")

	-- Should achieve significant reduction
	local reduction_ratio = http_requests / total_events_generated
	print("Request reduction: " .. string.format("%.1f%%", (1 - reduction_ratio) * 100))
	lu.assertTrue(reduction_ratio < 0.1, "Should reduce requests by at least 90%")
end

-- Helper to set up realistic random seed
math.randomseed(os.time())

-- Run tests
os.exit(lu.LuaUnit.run())
