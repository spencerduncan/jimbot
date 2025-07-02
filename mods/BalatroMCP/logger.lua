-- BalatroMCP: Logger Module
-- Provides structured logging with different levels

local Logger = {
    enabled = true,
    debug_mode = false,
    log_file = nil,
    log_levels = {
        DEBUG = 1,
        INFO = 2,
        WARN = 3,
        ERROR = 4
    },
    current_level = 2, -- Default to INFO
    colors = {
        DEBUG = "\27[36m", -- Cyan
        INFO = "\27[32m",  -- Green
        WARN = "\27[33m",  -- Yellow
        ERROR = "\27[31m", -- Red
        RESET = "\27[0m"
    }
}

function Logger:init(debug_mode, log_file_path)
    self.debug_mode = debug_mode
    if debug_mode then
        self.current_level = self.log_levels.DEBUG
    end
    
    -- Open log file if path provided
    if log_file_path then
        self.log_file = io.open(log_file_path, "a")
        if self.log_file then
            self.log_file:write("\n--- BalatroMCP Started: " .. os.date() .. " ---\n")
        end
    end
end

function Logger:log(level, message, data)
    local level_value = self.log_levels[level] or self.log_levels.INFO
    
    -- Check if we should log this level
    if level_value < self.current_level then
        return
    end
    
    -- Format timestamp
    local timestamp = os.date("%Y-%m-%d %H:%M:%S")
    
    -- Format message
    local formatted_message = string.format("[%s] [%s] %s", timestamp, level, message)
    
    -- Add data if provided
    if data then
        formatted_message = formatted_message .. " | " .. self:serialize_data(data)
    end
    
    -- Console output with colors (if supported)
    if self.enabled then
        local color = self.colors[level] or ""
        local reset = self.colors.RESET
        print(color .. formatted_message .. reset)
    end
    
    -- File output
    if self.log_file then
        self.log_file:write(formatted_message .. "\n")
        self.log_file:flush()
    end
end

function Logger:serialize_data(data)
    local data_type = type(data)
    
    if data_type == "nil" then
        return "nil"
    elseif data_type == "boolean" then
        return tostring(data)
    elseif data_type == "number" or data_type == "string" then
        return tostring(data)
    elseif data_type == "table" then
        return self:table_to_string(data)
    else
        return tostring(data)
    end
end

function Logger:table_to_string(t, indent)
    indent = indent or 0
    local indent_str = string.rep("  ", indent)
    local result = "{\n"
    
    for k, v in pairs(t) do
        result = result .. indent_str .. "  "
        
        -- Key
        if type(k) == "string" then
            result = result .. k .. " = "
        else
            result = result .. "[" .. tostring(k) .. "] = "
        end
        
        -- Value
        if type(v) == "table" and indent < 3 then -- Limit nesting depth
            result = result .. self:table_to_string(v, indent + 1)
        else
            result = result .. self:serialize_data(v)
        end
        
        result = result .. ",\n"
    end
    
    result = result .. indent_str .. "}"
    return result
end

-- Convenience methods
function Logger:debug(message, data)
    self:log("DEBUG", message, data)
end

function Logger:info(message, data)
    self:log("INFO", message, data)
end

function Logger:warn(message, data)
    self:log("WARN", message, data)
end

function Logger:error(message, data)
    self:log("ERROR", message, data)
end

-- Set log level
function Logger:set_level(level)
    if type(level) == "string" then
        self.current_level = self.log_levels[level:upper()] or self.log_levels.INFO
    elseif type(level) == "number" then
        self.current_level = level
    end
end

-- Clean up
function Logger:close()
    if self.log_file then
        self.log_file:close()
        self.log_file = nil
    end
end

return Logger