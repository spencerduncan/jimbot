-- BalatroMCP: Retry Manager Module
-- Handles non-blocking retry logic with circuit breaker pattern

local RetryManager = {
    -- Circuit breaker state
    failure_count = 0,
    consecutive_failures = 0,
    is_open = false,
    half_open = false,
    last_failure_time = 0,
    reset_timeout = 60, -- seconds
    failure_threshold = 3,
    
    -- Retry configuration
    max_retries = 3,
    retry_delays = {1, 2, 5}, -- seconds for each retry attempt
    
    -- Coroutines tracking
    active_coroutines = {},
    
    -- Components
    logger = nil,
}

-- Initialize retry manager
function RetryManager:init(config)
    self.max_retries = config.max_retries or 3
    self.reset_timeout = config.reset_timeout or 60
    self.failure_threshold = config.failure_threshold or 3
    self.logger = BalatroMCP.components.logger
    
    -- Calculate retry delays with exponential backoff
    self.retry_delays = {}
    local base_delay = (config.retry_delay_ms or 1000) / 1000
    for i = 1, self.max_retries do
        self.retry_delays[i] = base_delay * (2 ^ (i - 1))
    end
    
    self.logger:info("Retry manager initialized", {
        max_retries = self.max_retries,
        retry_delays = self.retry_delays,
        failure_threshold = self.failure_threshold,
        reset_timeout = self.reset_timeout
    })
end

-- Check if circuit breaker allows requests
function RetryManager:can_attempt()
    if not self.is_open then
        return true
    end
    
    -- Check if enough time has passed to try half-open
    local current_time = love.timer.getTime()
    if current_time - self.last_failure_time >= self.reset_timeout then
        self.half_open = true
        self.logger:info("Circuit breaker entering half-open state")
        return true
    end
    
    return false
end

-- Record successful attempt
function RetryManager:record_success()
    if self.half_open then
        -- Reset circuit breaker
        self.is_open = false
        self.half_open = false
        self.consecutive_failures = 0
        self.failure_count = 0
        self.logger:info("Circuit breaker closed - service recovered")
    end
    
    self.consecutive_failures = 0
end

-- Record failed attempt
function RetryManager:record_failure()
    self.failure_count = self.failure_count + 1
    self.consecutive_failures = self.consecutive_failures + 1
    self.last_failure_time = love.timer.getTime()
    
    if self.half_open then
        -- Failed in half-open state, go back to open
        self.is_open = true
        self.half_open = false
        self.logger:warn("Circuit breaker reopened - service still failing")
    elseif self.consecutive_failures >= self.failure_threshold then
        -- Open the circuit breaker
        self.is_open = true
        self.logger:error("Circuit breaker opened after " .. self.consecutive_failures .. " failures")
    end
end

-- Execute function with retry logic (non-blocking)
function RetryManager:execute_with_retry(func, context, on_success, on_failure)
    -- Check circuit breaker
    if not self:can_attempt() then
        self.logger:warn("Circuit breaker is open, skipping attempt", context)
        if on_failure then
            on_failure("Circuit breaker is open")
        end
        return
    end
    
    -- Create coroutine for non-blocking execution
    local co = coroutine.create(function()
        local attempt = 0
        local last_error = nil
        
        while attempt < self.max_retries do
            attempt = attempt + 1
            
            -- Log attempt
            self.logger:debug("Retry attempt " .. attempt .. "/" .. self.max_retries, context)
            
            -- Try to execute the function
            local success, result = pcall(func)
            
            if success and result then
                -- Success!
                self:record_success()
                self.logger:debug("Operation succeeded on attempt " .. attempt, context)
                
                if on_success then
                    on_success(result)
                end
                return true
            else
                -- Failure
                last_error = result or "Unknown error"
                self.logger:warn("Operation failed on attempt " .. attempt, {
                    error = last_error,
                    context = context
                })
                
                -- If not the last attempt, wait before retrying
                if attempt < self.max_retries then
                    local delay = self.retry_delays[attempt] or 5
                    self.logger:debug("Waiting " .. delay .. " seconds before retry", context)
                    
                    -- Non-blocking wait using coroutine yield
                    local start_time = love.timer.getTime()
                    while love.timer.getTime() - start_time < delay do
                        coroutine.yield()
                    end
                end
            end
        end
        
        -- All retries exhausted
        self:record_failure()
        self.logger:error("All retry attempts failed", {
            attempts = attempt,
            last_error = last_error,
            context = context
        })
        
        if on_failure then
            on_failure(last_error)
        end
        
        return false
    end)
    
    -- Store coroutine reference
    table.insert(self.active_coroutines, {
        coroutine = co,
        context = context,
        started = love.timer.getTime()
    })
    
    -- Start the coroutine
    coroutine.resume(co)
end

-- Update active coroutines (called from game loop)
function RetryManager:update(dt)
    local completed = {}
    
    -- Resume all active coroutines
    for i, co_data in ipairs(self.active_coroutines) do
        if coroutine.status(co_data.coroutine) ~= "dead" then
            local success, err = coroutine.resume(co_data.coroutine)
            if not success then
                self.logger:error("Coroutine error", {
                    error = err,
                    context = co_data.context
                })
                table.insert(completed, i)
            end
        else
            table.insert(completed, i)
        end
    end
    
    -- Remove completed coroutines
    for i = #completed, 1, -1 do
        table.remove(self.active_coroutines, completed[i])
    end
end

-- Get circuit breaker status
function RetryManager:get_status()
    return {
        is_open = self.is_open,
        half_open = self.half_open,
        failure_count = self.failure_count,
        consecutive_failures = self.consecutive_failures,
        active_retries = #self.active_coroutines,
        can_attempt = self:can_attempt()
    }
end

-- Force reset circuit breaker (for testing/manual intervention)
function RetryManager:reset()
    self.is_open = false
    self.half_open = false
    self.consecutive_failures = 0
    self.failure_count = 0
    self.logger:info("Circuit breaker manually reset")
end

return RetryManager