-- BalatroMCP: Configuration Module
-- Handles loading and saving mod configuration

local Config = {
    config_file = "mods/BalatroMCP/config/config.json",
    -- Windows compatibility: check if running on Windows
    is_windows = package.config:sub(1, 1) == "\\",
    defaults = {
        -- Connection settings
        event_bus_url = "http://localhost:8080/api/v1/events",
        event_bus_timeout = 5000,

        -- Performance settings
        batch_window_ms = 100,
        max_batch_size = 50,
        heartbeat_interval_ms = 5000,

        -- Retry settings
        max_retries = 3,
        retry_delay_ms = 1000,
        exponential_backoff = true,

        -- Game settings
        headless = true,
        disable_sound = true,
        game_speed_multiplier = 4,
        auto_play = false,

        -- Logging
        debug = true,
        log_file = "mods/BalatroMCP/balatro_mcp.log",
        log_level = "INFO",

        -- AI Integration
        ai_decision_timeout_ms = 1000,
        fallback_to_random = true,
        cache_ai_decisions = true,
    },
}

-- Simple JSON encoder (basic implementation)
function Config:encode_json(data)
    local json = "{\n"
    local first = true

    for k, v in pairs(data) do
        if not first then
            json = json .. ",\n"
        end
        first = false

        json = json .. '  "' .. k .. '": '

        local vtype = type(v)
        if vtype == "string" then
            json = json .. '"' .. v .. '"'
        elseif vtype == "number" or vtype == "boolean" then
            json = json .. tostring(v)
        elseif vtype == "table" then
            -- Simple array handling
            json = json .. "["
            local array_first = true
            for _, item in ipairs(v) do
                if not array_first then
                    json = json .. ", "
                end
                array_first = false
                json = json .. '"' .. tostring(item) .. '"'
            end
            json = json .. "]"
        else
            json = json .. "null"
        end
    end

    json = json .. "\n}"
    return json
end

-- Simple JSON decoder (basic implementation)
function Config:decode_json(json_str)
    local config = {}

    -- Remove whitespace and newlines
    json_str = json_str:gsub("[\n\r]", "")

    -- Extract key-value pairs
    for key, value in json_str:gmatch('"([^"]+)"%s*:%s*([^,}]+)') do
        -- Clean up the value
        value = value:gsub("^%s+", ""):gsub("%s+$", "")

        -- Parse value type
        if value:match('^".-"$') then
            -- String value
            config[key] = value:sub(2, -2)
        elseif value == "true" then
            config[key] = true
        elseif value == "false" then
            config[key] = false
        elseif value == "null" then
            config[key] = nil
        elseif value:match("^%[.*%]$") then
            -- Simple array
            config[key] = {}
            for item in value:gmatch('"([^"]+)"') do
                table.insert(config[key], item)
            end
        else
            -- Try to parse as number
            local num = tonumber(value)
            if num then
                config[key] = num
            else
                config[key] = value
            end
        end
    end

    return config
end

-- Load configuration from file
function Config:load()
    local file = io.open(self.config_file, "r")
    if not file then
        -- Create default config file
        self:save(self.defaults)
        return self.defaults
    end

    local content = file:read("*all")
    file:close()

    if not content or content == "" then
        return self.defaults
    end

    -- Parse JSON
    local success, config = pcall(self.decode_json, self, content)
    if not success then
        print("[BalatroMCP] Error parsing config file: " .. tostring(config))
        return self.defaults
    end

    -- Merge with defaults
    local merged = {}
    for k, v in pairs(self.defaults) do
        merged[k] = config[k] or v
    end

    return merged
end

-- Save configuration to file
function Config:save(config)
    local file = io.open(self.config_file, "w")
    if not file then
        print("[BalatroMCP] Error: Could not save config file")
        return false
    end

    local json = self:encode_json(config)
    file:write(json)
    file:close()

    return true
end

-- Get a specific config value
function Config:get(key)
    local config = self:load()
    return config[key]
end

-- Set a specific config value
function Config:set(key, value)
    local config = self:load()
    config[key] = value
    return self:save(config)
end

return Config
