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
    sending = false
}

-- Initialize the client
function EventBusClient:init(config)
    self.url = config.event_bus_url
    self.timeout = (config.event_bus_timeout or 5000) / 1000 -- Convert to seconds
    self.max_retries = config.max_retries or 3
    self.retry_delay = (config.retry_delay_ms or 1000) / 1000
    self.logger = BalatroMCP.components.logger
    
    -- Don't test connection immediately - wait until SMODS is fully loaded
    self.connection_tested = false
    self.connected = false
end

-- Test connection to event bus
function EventBusClient:test_connection()
    self.connection_tested = true
    self.logger:info("Testing connection to event bus", {url = self.url})
    
    -- Check if SMODS.https is available
    if not SMODS then
        self.logger:error("SMODS not available yet")
        self.connected = false
        return
    end
    
    if not SMODS.https then
        -- Debug what's in SMODS
        local smods_keys = {}
        for k, v in pairs(SMODS) do
            table.insert(smods_keys, k .. " (" .. type(v) .. ")")
        end
        self.logger:error("SMODS.https not found. Available SMODS keys: " .. table.concat(smods_keys, ", "))
        self.connected = false
        return
    end
    
    -- Send a test event to verify connection
    local test_event = {
        type = "connection_test",
        timestamp = os.time() * 1000,
        source = "BalatroMCP",
        data = {
            message = "Testing event bus connection"
        }
    }
    
    local json = self:event_to_json(test_event)
    local success, response = self:http_post(self.url, json)
    
    if success then
        self.connected = true
        self.logger:info("Event bus connection established", {response = response})
    else
        self.connected = false
        self.logger:error("Failed to connect to event bus", {error = response})
    end
end

-- Send event to the event bus
function EventBusClient:send_event(event)
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
        self.logger:error("Failed to send event", {error = response})
        return self:handle_send_failure(event)
    end
end

-- Send batch of events
function EventBusClient:send_batch(events)
    if #events == 0 then return true end
    
    -- Test connection on first use if not already tested
    if not self.connection_tested then
        self:test_connection()
    end
    
    if not self.connected then
        self.logger:warn("Event bus not connected, cannot send batch")
        -- Queue events for retry
        for _, event in ipairs(events) do
            table.insert(self.event_queue, event)
        end
        return false
    end
    
    self.logger:debug("Sending event batch", {count = #events})
    
    local batch = {
        batch_id = self:generate_uuid(),
        events = events,
        source = "BalatroMCP",
        timestamp = os.time() * 1000
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
        self.logger:error("Failed to send batch", {error = response})
        -- Queue events for retry
        for _, event in ipairs(events) do
            table.insert(self.event_queue, event)
        end
        return false
    end
end

-- HTTP POST implementation using SMODS.https
function EventBusClient:http_post(url, data)
    -- Check for SMODS.https at runtime
    if not SMODS or not SMODS.https then
        self.logger:error("SMODS.https not available")
        return false, "SMODS.https not available"
    end
    
    self.logger:debug("HTTP POST via SMODS.https", {url = url, size = #data})
    
    -- Create the request
    local request = {
        url = url,
        method = "POST",
        headers = {
            ["Content-Type"] = "application/json",
            ["User-Agent"] = "BalatroMCP/1.0"
        },
        body = data
    }
    
    -- Send the request directly with SMODS.https
    local success, response = pcall(function()
        return SMODS.https(request)
    end)
    
    if not success then
        self.logger:error("HTTP request failed", {error = tostring(response)})
        return false, tostring(response)
    end
    
    -- Check response
    if response and response.status and response.status >= 200 and response.status < 300 then
        self.logger:debug("HTTP POST successful", {status = response.status})
        return true, response.body or "OK"
    else
        local error_msg = "HTTP error"
        if response then
            error_msg = string.format("HTTP %s: %s", 
                tostring(response.status or "unknown"), 
                tostring(response.body or "no body"))
        end
        self.logger:error("HTTP POST failed", {error = error_msg})
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
        self.logger:warn("Queueing event for retry", {attempt = self.retry_count})
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
                    if i > 1 then json = json .. "," end
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
    local template = 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'
    return string.gsub(template, '[xy]', function (c)
        local v = (c == 'x') and math.random(0, 0xf) or math.random(8, 0xb)
        return string.format('%x', v)
    end)
end

return EventBusClient