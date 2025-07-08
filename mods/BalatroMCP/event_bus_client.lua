-- BalatroMCP: Event Bus Client Module
-- Handles REST communication with the event bus

local EventBusClient = {
    url = nil,
    timeout = 5,
    retry_count = 0,
    max_retries = 3,
    retry_delay = 1,
    logger = nil,
    connected = false,
    event_queue = {},
    sending = false,
    retry_manager = nil,
    local_buffer = {}, -- Buffer for events when event bus is unavailable
    max_buffer_size = 1000,
}

-- Initialize the client
function EventBusClient:init(config)
    self.url = config.event_bus_url
    self.timeout = (config.event_bus_timeout or 5000) / 1000 -- Convert to seconds
    self.max_retries = config.max_retries or 3
    self.retry_delay = (config.retry_delay_ms or 1000) / 1000
    self.logger = BalatroMCP.components.logger
    self.max_buffer_size = config.max_buffer_size or 1000

    -- Initialize retry manager
    self.retry_manager = require("mods.BalatroMCP.retry_manager")
    self.retry_manager:init(config)

    -- Don't test connection immediately - wait until SMODS is fully loaded
    self.connection_tested = false
    self.connected = false
end

-- Test connection to event bus
function EventBusClient:test_connection()
    self.connection_tested = true
    self.logger:info("Testing connection to event bus", { url = self.url })

    -- Try to load https module directly (as SMODS does)
    local success, https = pcall(require, "https")
    if not success then
        self.logger:error("Failed to require 'https' module: " .. tostring(https))
        self.connected = false
        return
    end

    if not https or not https.request then
        self.logger:error("https module loaded but request function not found")
        self.connected = false
        return
    end

    -- Store the https module for later use
    self.https = https

    -- Send a test event to verify connection
    local test_event = {
        type = "connection_test",
        timestamp = os.time() * 1000,
        source = "BalatroMCP",
        data = {
            message = "Testing event bus connection",
        },
    }

    local json = self:event_to_json(test_event)
    local post_success, response = self:http_post(self.url, json)

    if post_success then
        self.connected = true
        self.logger:info("Event bus connection established", { response = response })
    else
        self.connected = false
        self.logger:error("Failed to connect to event bus", { error = response })
    end
end

-- Send event to the event bus (now non-blocking)
function EventBusClient:send_event(event)
    -- For backward compatibility, redirect to aggregator if available
    if BalatroMCP and BalatroMCP.components and BalatroMCP.components.aggregator then
        self.logger:debug("Redirecting event to aggregator for batching")
        BalatroMCP.components.aggregator:add_event(event)
        return true
    end
    
    -- Test connection on first use if not already tested
    if not self.connection_tested then
        self:test_connection()
    end

    -- Add to local buffer if event bus is unavailable
    if not self.retry_manager:can_attempt() then
        self:buffer_event(event)
        return false
    end

    -- Add metadata
    event.event_id = self:generate_uuid()
    event.timestamp = os.time() * 1000 -- milliseconds
    event.source = event.source or "BalatroMCP"
    event.version = 1

    -- Use non-blocking retry mechanism
    self.retry_manager:execute_with_retry(function()
        -- This function will be called with retry logic
        local json = self:event_to_json(event)
        return self:http_post(self.url, json)
    end, { type = event.type, event_id = event.event_id }, function(result)
        -- Success callback
        self.connected = true
        self.logger:debug("Event sent successfully", {
            type = event.type,
            event_id = event.event_id,
        })
    end, function(error)
        -- Failure callback
        self.logger:error("Failed to send event after retries", {
            type = event.type,
            event_id = event.event_id,
            error = error,
        })
        self:buffer_event(event)
    end)

    return true -- Return immediately, actual send happens asynchronously
end

-- Send event synchronously (for backward compatibility)
function EventBusClient:send_event_sync(event)
    -- Test connection on first use if not already tested
    if not self.connection_tested then
        self:test_connection()
    end

    if not self.connected then
        self.logger:warn("Event bus not connected, queueing event")
        table.insert(self.event_queue, event)
        return false
    end

    -- Add metadata
    event.event_id = self:generate_uuid()
    event.timestamp = os.time() * 1000 -- milliseconds
    event.source = event.source or "BalatroMCP"
    event.version = 1

    -- Convert to JSON
    local json = self:event_to_json(event)

    -- Send via HTTP POST
    local success, response = self:http_post(self.url, json)

    if success then
        self.retry_count = 0
        return true
    else
        self.logger:error("Failed to send event", { error = response })
        return self:handle_send_failure(event)
    end
end

-- Send batch of events (now non-blocking)
function EventBusClient:send_batch(events)
    if #events == 0 then
        return true
    end

    -- Test connection on first use if not already tested
    if not self.connection_tested then
        self:test_connection()
    end

    -- Add to local buffer if circuit breaker is open
    if not self.retry_manager:can_attempt() then
        self.logger:warn("Circuit breaker open, buffering batch")
        for _, event in ipairs(events) do
            self:buffer_event(event)
        end
        return false
    end

    self.logger:debug("Sending event batch", { count = #events })

    local batch = {
        batch_id = self:generate_uuid(),
        events = events,
        source = "BalatroMCP",
        timestamp = os.time() * 1000,
    }

    -- Add metadata to each event
    for _, event in ipairs(events) do
        event.event_id = event.event_id or self:generate_uuid()
        event.timestamp = event.timestamp or (os.time() * 1000)
        event.source = event.source or "BalatroMCP"
        event.version = event.version or 1
    end

    -- Use non-blocking retry mechanism
    self.retry_manager:execute_with_retry(function()
        local json = self:batch_to_json(batch)
        return self:http_post(self.url .. "/batch", json)
    end, { type = "batch", batch_id = batch.batch_id, count = #events }, function(result)
        -- Success callback
        self.connected = true
        self.logger:debug("Batch sent successfully", {
            batch_id = batch.batch_id,
            count = #events,
        })
        -- Try to flush buffered events
        self:flush_buffer()
    end, function(error)
        -- Failure callback
        self.logger:error("Failed to send batch after retries", {
            batch_id = batch.batch_id,
            count = #events,
            error = error,
        })
        -- Buffer events for later
        for _, event in ipairs(events) do
            self:buffer_event(event)
        end
    end)

    return true -- Return immediately, actual send happens asynchronously
end

-- HTTP POST implementation using https module
function EventBusClient:http_post(url, data)
    -- Use the https module we loaded earlier
    if not self.https then
        self.logger:error("https module not available", {
            url = url,
            context = "HTTP POST attempt without loaded https module",
        })
        return false, "https module not available"
    end

    self.logger:debug("HTTP POST via https module", {
        url = url,
        size = #data,
        first_100_chars = string.sub(data, 1, 100),
    })

    -- The https module in SMODS uses data instead of body
    local options = {
        method = "POST",
        headers = {
            ["Content-Type"] = "application/json",
            ["User-Agent"] = "BalatroMCP/1.0",
        },
        data = data, -- Changed from body to data
    }

    -- Send the request using the https module
    -- Returns: status, body, headers
    local start_time = love.timer.getTime()
    local success, status_or_error, response_body = pcall(function()
        return self.https.request(url, options)
    end)
    local duration = (love.timer.getTime() - start_time) * 1000 -- Convert to ms

    if not success then
        self.logger:error("HTTP request failed", {
            error = tostring(status_or_error),
            url = url,
            duration_ms = duration,
            context = "Network request exception",
        })
        return false, tostring(status_or_error)
    end

    -- The https module returns status code and response body
    local status = status_or_error
    local body = response_body

    -- Check response status
    if status and status >= 200 and status < 300 then
        self.logger:debug("HTTP POST successful", {
            status = status,
            duration_ms = duration,
            response_size = body and #body or 0,
        })
        return true, body or "OK"
    else
        local error_msg = string.format("HTTP %d: %s", status or 0, body or "no response body")
        self.logger:error("HTTP POST failed", {
            error = error_msg,
            status = status,
            url = url,
            duration_ms = duration,
            response_body = body and string.sub(body, 1, 200) or "none",
        })
        return false, error_msg
    end
end

-- Parse URL into components
function EventBusClient:parse_url(url)
    -- Remove protocol
    local without_protocol = url:gsub("^https?://", "")

    -- Extract host and path
    local host, path = without_protocol:match("^([^/]+)(.*)$")
    path = path or "/"

    -- Extract port if present
    local host_part, port = host:match("^([^:]+):(%d+)$")
    if host_part then
        host = host_part
        port = tonumber(port)
    else
        port = 80
    end

    return host, port, path
end

-- Handle send failure
function EventBusClient:handle_send_failure(event)
    self.retry_count = self.retry_count + 1

    if self.retry_count <= self.max_retries then
        -- Queue for retry
        table.insert(self.event_queue, event)
        self.logger:warn("Queueing event for retry", { attempt = self.retry_count })
        return false
    else
        self.logger:error("Max retries exceeded, dropping event")
        self.retry_count = 0
        return false
    end
end

-- Process queued events
function EventBusClient:process_queue()
    if #self.event_queue == 0 or self.sending then
        return
    end

    self.sending = true
    local events_to_send = {}

    -- Take up to 10 events from queue
    for i = 1, math.min(10, #self.event_queue) do
        table.insert(events_to_send, table.remove(self.event_queue, 1))
    end

    -- Try to send as batch
    if not self:send_batch(events_to_send) then
        self.logger:warn("Failed to send queued events")
    end

    self.sending = false
end

-- Buffer event locally when event bus is unavailable
function EventBusClient:buffer_event(event)
    -- Check buffer size
    if #self.local_buffer >= self.max_buffer_size then
        self.logger:warn("Local buffer full, dropping oldest event")
        table.remove(self.local_buffer, 1)
    end

    -- Add to buffer
    table.insert(self.local_buffer, event)
    self.logger:debug("Event buffered locally", {
        type = event.type,
        buffer_size = #self.local_buffer,
    })
end

-- Attempt to flush buffered events
function EventBusClient:flush_buffer()
    if #self.local_buffer == 0 then
        return
    end

    -- Check if we can attempt to send
    if not self.retry_manager:can_attempt() then
        return
    end

    self.logger:info("Flushing local buffer", { count = #self.local_buffer })

    -- Take events from buffer in batches
    while #self.local_buffer > 0 do
        local batch_size = math.min(10, #self.local_buffer)
        local batch = {}

        for i = 1, batch_size do
            table.insert(batch, table.remove(self.local_buffer, 1))
        end

        -- Send batch (non-blocking)
        self:send_batch(batch)
    end
end

-- Update method to be called from main game loop
function EventBusClient:update(dt)
    -- Update retry manager coroutines
    if self.retry_manager then
        self.retry_manager:update(dt)
    end

    -- Try to flush buffer periodically
    if #self.local_buffer > 0 and self.retry_manager:can_attempt() then
        self:flush_buffer()
    end
end

-- Convert event to JSON
function EventBusClient:event_to_json(event)
    return self:table_to_json(event)
end

-- Convert batch to JSON
function EventBusClient:batch_to_json(batch)
    return self:table_to_json(batch)
end

-- Simple JSON encoder
function EventBusClient:table_to_json(t)
    local json = "{"
    local first = true

    for k, v in pairs(t) do
        if not first then
            json = json .. ","
        end
        first = false

        json = json .. '"' .. k .. '":'

        local vtype = type(v)
        if vtype == "string" then
            json = json .. '"' .. self:escape_json_string(v) .. '"'
        elseif vtype == "number" then
            json = json .. tostring(v)
        elseif vtype == "boolean" then
            json = json .. (v and "true" or "false")
        elseif vtype == "table" then
            if #v > 0 then
                -- Array
                json = json .. "["
                for i, item in ipairs(v) do
                    if i > 1 then
                        json = json .. ","
                    end
                    if type(item) == "table" then
                        json = json .. self:table_to_json(item)
                    else
                        json = json .. '"' .. tostring(item) .. '"'
                    end
                end
                json = json .. "]"
            else
                -- Object
                json = json .. self:table_to_json(v)
            end
        else
            json = json .. "null"
        end
    end

    json = json .. "}"
    return json
end

-- Escape special characters in JSON strings
function EventBusClient:escape_json_string(str)
    str = str:gsub("\\", "\\\\")
    str = str:gsub('"', '\\"')
    str = str:gsub("\n", "\\n")
    str = str:gsub("\r", "\\r")
    str = str:gsub("\t", "\\t")
    return str
end

-- Generate a simple UUID
function EventBusClient:generate_uuid()
    local template = "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx"
    return string.gsub(template, "[xy]", function(c)
        local v = (c == "x") and math.random(0, 0xf) or math.random(8, 0xb)
        return string.format("%x", v)
    end)
end

-- Get client status
function EventBusClient:get_status()
    local retry_status = self.retry_manager and self.retry_manager:get_status() or {}

    return {
        connected = self.connected,
        event_queue_size = #self.event_queue,
        local_buffer_size = #self.local_buffer,
        circuit_breaker = retry_status,
        url = self.url,
    }
end

-- Health check endpoint integration
function EventBusClient:check_health()
    if not self.retry_manager:can_attempt() then
        return false, "Circuit breaker is open"
    end

    -- Try a simple health check request
    local success, response = self:http_post(self.url .. "/health", "{}")

    if success then
        self.retry_manager:record_success()
        return true, "Healthy"
    else
        self.retry_manager:record_failure()
        return false, response
    end
end

return EventBusClient
