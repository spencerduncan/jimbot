-- BalatroMCP: Event Aggregator Module
-- Batches events within a time window for efficient transmission

local EventAggregator = {
    batch_window_ms = 100,
    max_batch_size = 50,
    event_queue = {},
    last_flush_time = 0,
    logger = nil,
    event_bus = nil,

    -- Statistics
    stats = {
        events_queued = 0,
        batches_sent = 0,
        events_sent = 0,
        events_dropped = 0,
    },
}

-- Initialize the aggregator
function EventAggregator:init(batch_window_ms)
    self.batch_window_ms = batch_window_ms or 100
    self.last_flush_time = love.timer.getTime() * 1000
    self.logger = BalatroMCP.components.logger
    -- event_bus will be set after initialization in main.lua

    self.logger:info("Event aggregator initialized", {
        batch_window_ms = self.batch_window_ms,
        max_batch_size = self.max_batch_size,
    })
end

-- Add event to the queue
function EventAggregator:add_event(event)
    -- Add timestamp if not present
    event.timestamp = event.timestamp or (love.timer.getTime() * 1000)

    -- Check queue size
    if #self.event_queue >= self.max_batch_size * 2 then
        self.logger:warn("Event queue full, dropping oldest events")
        -- Remove oldest events
        for i = 1, 10 do
            table.remove(self.event_queue, 1)
            self.stats.events_dropped = self.stats.events_dropped + 1
        end
    end

    -- Add to queue
    table.insert(self.event_queue, event)
    self.stats.events_queued = self.stats.events_queued + 1

    self.logger:debug("Event queued", {
        type = event.type,
        queue_size = #self.event_queue,
    })

    -- Check if we should flush immediately (high priority events)
    if event.priority == "high" or event.type == "ERROR" then
        self:flush()
    end
end

-- Update method called each frame
function EventAggregator:update(dt)
    local current_time = love.timer.getTime() * 1000

    -- Check if batch window has elapsed
    if current_time - self.last_flush_time >= self.batch_window_ms then
        self:flush()
    end

    -- Process any queued events from the event bus
    if self.event_bus then
        self.event_bus:process_queue()
    end
end

-- Flush the current batch
function EventAggregator:flush()
    if #self.event_queue == 0 then
        return
    end

    local current_time = love.timer.getTime() * 1000
    local batch_size = math.min(#self.event_queue, self.max_batch_size)

    -- Extract events for this batch
    local batch = {}
    for i = 1, batch_size do
        table.insert(batch, table.remove(self.event_queue, 1))
    end

    -- Aggregate similar events
    local aggregated = self:aggregate_events(batch)

    -- Send the batch
    if self.event_bus then
        local success = self.event_bus:send_batch(aggregated)

        if success then
            self.stats.batches_sent = self.stats.batches_sent + 1
            self.stats.events_sent = self.stats.events_sent + #aggregated

            self.logger:debug("Batch sent", {
                events = #aggregated,
                remaining = #self.event_queue,
            })
        else
            -- Re-queue events on failure
            for _, event in ipairs(aggregated) do
                table.insert(self.event_queue, 1, event)
            end

            self.logger:warn("Failed to send batch, re-queuing events")
        end
    end

    self.last_flush_time = current_time
end

-- Aggregate similar events to reduce redundancy
function EventAggregator:aggregate_events(events)
    local aggregated = {}
    local game_states = {}
    local other_events = {}

    -- Separate game state events from others
    for _, event in ipairs(events) do
        if event.type == "GAME_STATE" then
            table.insert(game_states, event)
        else
            table.insert(other_events, event)
        end
    end

    -- Keep only the latest game state per frame
    if #game_states > 1 then
        local latest_by_frame = {}
        for _, state in ipairs(game_states) do
            local frame = state.payload and state.payload.frame_count or 0
            if not latest_by_frame[frame] or state.timestamp > latest_by_frame[frame].timestamp then
                latest_by_frame[frame] = state
            end
        end

        -- Convert back to array
        game_states = {}
        for _, state in pairs(latest_by_frame) do
            table.insert(game_states, state)
        end

        self.logger:debug("Aggregated game states", {
            original = #events,
            aggregated = #game_states,
        })
    end

    -- Combine aggregated game states with other events
    for _, state in ipairs(game_states) do
        table.insert(aggregated, state)
    end

    for _, event in ipairs(other_events) do
        table.insert(aggregated, event)
    end

    -- Sort by timestamp
    table.sort(aggregated, function(a, b)
        return (a.timestamp or 0) < (b.timestamp or 0)
    end)

    return aggregated
end

-- Get statistics
function EventAggregator:get_stats()
    return {
        events_queued = self.stats.events_queued,
        batches_sent = self.stats.batches_sent,
        events_sent = self.stats.events_sent,
        events_dropped = self.stats.events_dropped,
        queue_size = #self.event_queue,
        avg_events_per_batch = self.stats.batches_sent > 0
                and (self.stats.events_sent / self.stats.batches_sent)
            or 0,
    }
end

-- Force flush all events (useful for shutdown)
function EventAggregator:flush_all()
    while #self.event_queue > 0 do
        self:flush()
    end
end

-- Create specialized event types
function EventAggregator:create_game_state_event(game_state)
    return {
        type = "GAME_STATE",
        source = "BalatroMCP",
        payload = game_state,
    }
end

function EventAggregator:create_decision_request(game_state, available_actions)
    return {
        type = "LEARNING_DECISION",
        subtype = "REQUEST",
        source = "BalatroMCP",
        priority = "high",
        payload = {
            request_id = self:generate_request_id(),
            game_state = game_state,
            available_actions = available_actions,
            time_limit_ms = 1000,
        },
    }
end

function EventAggregator:create_error_event(error_msg, context)
    return {
        type = "ERROR",
        source = "BalatroMCP",
        priority = "high",
        payload = {
            message = error_msg,
            context = context or {},
            stack_trace = debug.traceback(),
        },
    }
end

-- Generate request ID
function EventAggregator:generate_request_id()
    return string.format("%s-%d-%d", "REQ", os.time(), math.random(1000, 9999))
end

return EventAggregator
