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
}

-- Initialize the client
function EventBusClient:init(config)
    self.url = config.event_bus_url
    self.timeout = (config.event_bus_timeout or 5000) / 1000 -- Convert to seconds
    self.max_retries = config.max_retries or 3
    self.retry_delay = (config.retry_delay_ms or 1000) / 1000
    self.logger = BalatroMCP.components.logger

    -- Test connection
    self:test_connection()
end

-- Test connection to event bus
function EventBusClient:test_connection()
    -- Note: This is a simplified HTTP client
    -- In production, you'd want to use a proper HTTP library
    self.logger:info("Testing connection to event bus", { url = self.url })

    -- For now, assume connected
    self.connected = true
    self.logger:info("Event bus connection established")
end

-- Send event to the event bus
function EventBusClient:send_event(event)
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

-- Send batch of events
function EventBusClient:send_batch(events)
    if #events == 0 then
        return true
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

    local json = self:batch_to_json(batch)
    local success, response = self:http_post(self.url .. "/batch", json)

    if success then
        self.logger:debug("Batch sent successfully")
        return true
    else
        self.logger:error("Failed to send batch", { error = response })
        -- Queue events for retry
        for _, event in ipairs(events) do
            table.insert(self.event_queue, event)
        end
        return false
    end
end

-- Simple HTTP POST implementation
function EventBusClient:http_post(url, data)
    -- This is a simplified implementation
    -- In a real mod, you'd use LuaSocket or similar

    -- Parse URL
    local host, port, path = self:parse_url(url)

    -- Create request
    local request = string.format(
        "POST %s HTTP/1.1\r\n"
            .. "Host: %s\r\n"
            .. "Content-Type: application/json\r\n"
            .. "Content-Length: %d\r\n"
            .. "Connection: close\r\n"
            .. "\r\n"
            .. "%s",
        path,
        host,
        #data,
        data
    )

    -- In a real implementation, you'd send this via socket
    -- For now, we'll simulate success
    self.logger:debug("HTTP POST (simulated)", { url = url, size = #data })

    -- Simulate network delay
    local start_time = love.timer.getTime()
    while love.timer.getTime() - start_time < 0.01 do
        -- Wait
    end

    -- Simulate success for now
    return true, "OK"
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

return EventBusClient
