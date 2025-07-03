-- BalatroMCP: Headless Balatro Mod for AI Integration
-- Main entry point for the mod

local BalatroMCP = {
    version = "0.1.0",
    enabled = true,
    headless = true,
    debug = true,

    -- Component references
    components = {},

    -- Configuration
    config = {
        event_bus_url = "http://localhost:8080/api/v1/events",
        batch_window_ms = 100,
        heartbeat_interval_ms = 5000,
        max_retries = 3,
        retry_delay_ms = 1000,
    },
}

-- Global reference for other modules
_G.BalatroMCP = BalatroMCP

-- Initialize mod components
function BalatroMCP:init()
    if self.debug then
        print("[BalatroMCP] Initializing version " .. self.version)
    end

    -- Load components
    self.components.config = require("mods.BalatroMCP.config")
    self.components.logger = require("mods.BalatroMCP.logger")
    self.components.headless = require("mods.BalatroMCP.headless_override")
    self.components.extractor = require("mods.BalatroMCP.game_state_extractor")
    self.components.event_bus = require("mods.BalatroMCP.event_bus_client")
    self.components.aggregator = require("mods.BalatroMCP.event_aggregator")
    self.components.executor = require("mods.BalatroMCP.action_executor")

    -- Override configuration from file if exists
    local user_config = self.components.config:load()
    if user_config then
        for k, v in pairs(user_config) do
            self.config[k] = v
        end
    end

    -- Initialize components
    self.components.logger:init(self.debug)
    self.components.event_bus:init(self.config)
    self.components.aggregator:init(self.config.batch_window_ms)
    self.components.executor:init()

    -- Enable headless mode
    if self.headless then
        self.components.headless:enable()
        self.components.logger:info("Headless mode enabled")
    end

    -- Start heartbeat
    self:start_heartbeat()

    self.components.logger:info("BalatroMCP initialized successfully")
end

-- Start periodic heartbeat
function BalatroMCP:start_heartbeat()
    self.last_heartbeat = 0
end

-- Update function called from love.update
function BalatroMCP:update(dt)
    -- Send heartbeat periodically
    local current_time = love.timer.getTime() * 1000 -- Convert to ms
    if current_time - self.last_heartbeat > self.config.heartbeat_interval_ms then
        self.components.aggregator:add_event({
            type = "HEARTBEAT",
            source = "BalatroMCP",
            payload = {
                version = self.version,
                uptime = current_time,
                headless = self.headless,
            },
        })
        self.last_heartbeat = current_time
    end

    -- Process event queue
    self.components.aggregator:update(dt)
end

-- Hook into game state changes
function BalatroMCP:hook_game_events()
    -- Hook into card play
    local original_play_cards = G.FUNCS.play_cards_from_highlighted
    G.FUNCS.play_cards_from_highlighted = function(e)
        if original_play_cards then
            original_play_cards(e)
        end

        -- Extract and send game state
        local game_state = self.components.extractor:get_current_state()
        self.components.aggregator:add_event({
            type = "GAME_STATE",
            source = "BalatroMCP",
            payload = game_state,
        })
    end

    -- Hook into shop purchases
    local original_buy = G.FUNCS.buy_from_shop
    G.FUNCS.buy_from_shop = function(e)
        if original_buy then
            original_buy(e)
        end

        -- Extract and send updated state
        local game_state = self.components.extractor:get_current_state()
        self.components.aggregator:add_event({
            type = "GAME_STATE",
            source = "BalatroMCP",
            payload = game_state,
        })
    end

    -- Hook into round completion
    local original_end_round = G.FUNCS.end_round
    G.FUNCS.end_round = function(e)
        if original_end_round then
            original_end_round(e)
        end

        -- Send round complete event
        self.components.aggregator:add_event({
            type = "ROUND_COMPLETE",
            source = "BalatroMCP",
            payload = {
                ante = G.GAME.round_resets.ante,
                round = G.GAME.round,
                score = G.GAME.chips,
                money = G.GAME.dollars,
            },
        })
    end
end

-- Defer initialization until game is ready
local function initialize_when_ready()
    if not BalatroMCP.initialized then
        -- Check if game is ready (G exists and has necessary components)
        if G and G.FUNCS then
            BalatroMCP:init()
            BalatroMCP:hook_game_events()
            BalatroMCP.initialized = true
            print("[BalatroMCP] Initialized successfully")
        else
            -- Try again next frame
            love.timer.sleep(0.1)
            initialize_when_ready()
        end
    end
end

-- Hook into Love2D's update to initialize when ready
local original_update = love.update
love.update = function(dt)
    if original_update then
        original_update(dt)
    end

    -- Initialize once when game is ready
    if not BalatroMCP.initialized and G and G.FUNCS then
        initialize_when_ready()
    end

    -- Run our update if initialized
    if BalatroMCP.initialized and BalatroMCP.update then
        BalatroMCP:update(dt)
    end
end

return BalatroMCP
