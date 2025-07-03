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

    -- Enable headless mode based on config
    self.headless = self.config.headless or false
    if self.headless then
        self.components.headless:enable()
        self.components.logger:info("Headless mode enabled")
    else
        self.components.logger:info("Headless mode disabled - graphics enabled")
    end

    -- Start heartbeat
    self:start_heartbeat()

    self.components.logger:info("BalatroMCP initialized successfully")
end

-- Start periodic heartbeat and state tracking
function BalatroMCP:start_heartbeat()
    self.last_heartbeat = 0
    self.last_state_check = 0
    self.previous_state = nil
    self.state_check_interval = 500 -- Check state every 500ms
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
                game_state = G.STATE and tostring(G.STATE) or "unknown",
            },
        })
        self.last_heartbeat = current_time
    end

    -- Process event queue
    self.components.aggregator:update(dt)

    -- Process pending actions
    if self.components.executor then
        self.components.executor:update(dt)
    end

    -- Check for commands periodically
    self:check_for_commands(dt)

    -- Check for state changes periodically
    self:check_state_changes(current_time)
end

-- Check for game state changes
function BalatroMCP:check_state_changes(current_time)
    -- Only check every state_check_interval ms
    if current_time - self.last_state_check < self.state_check_interval then
        return
    end

    self.last_state_check = current_time

    -- Get current state
    local current_state = self.components.extractor:get_current_state()
    if not current_state then
        return
    end

    -- If we have a previous state, compare them
    if self.previous_state then
        local changes = self:detect_state_changes(self.previous_state, current_state)

        -- Send events for any detected changes
        if #changes > 0 then
            for _, change in ipairs(changes) do
                self.components.aggregator:add_event(change)
            end

            -- Also send a comprehensive state update
            self.components.aggregator:add_event({
                type = "GAME_STATE",
                source = "BalatroMCP",
                payload = current_state,
                changes = changes,
            })
        end
    end

    -- Store current state for next comparison
    self.previous_state = current_state
end

-- Detect changes between two game states
function BalatroMCP:detect_state_changes(old_state, new_state)
    local changes = {}

    -- Check for money changes
    if old_state.money ~= new_state.money then
        table.insert(changes, {
            type = "MONEY_CHANGED",
            source = "BalatroMCP",
            payload = {
                old_value = old_state.money,
                new_value = new_state.money,
                difference = new_state.money - old_state.money,
            },
        })
    end

    -- Check for chip/mult changes (indicates scoring)
    if old_state.chips ~= new_state.chips or old_state.mult ~= new_state.mult then
        table.insert(changes, {
            type = "SCORE_CHANGED",
            source = "BalatroMCP",
            payload = {
                old_chips = old_state.chips,
                new_chips = new_state.chips,
                old_mult = old_state.mult,
                new_mult = new_state.mult,
            },
        })
    end

    -- Check for hand changes
    if old_state.hands_remaining ~= new_state.hands_remaining then
        table.insert(changes, {
            type = "HAND_PLAYED",
            source = "BalatroMCP",
            payload = {
                hands_remaining = new_state.hands_remaining,
                hand_number = new_state.hand_number,
            },
        })
    end

    -- Check for discard changes
    if old_state.discards_remaining ~= new_state.discards_remaining then
        table.insert(changes, {
            type = "CARDS_DISCARDED",
            source = "BalatroMCP",
            payload = {
                discards_remaining = new_state.discards_remaining,
            },
        })
    end

    -- Check for joker changes
    local old_joker_count = old_state.jokers and #old_state.jokers or 0
    local new_joker_count = new_state.jokers and #new_state.jokers or 0

    if old_joker_count ~= new_joker_count then
        table.insert(changes, {
            type = "JOKERS_CHANGED",
            source = "BalatroMCP",
            payload = {
                old_count = old_joker_count,
                new_count = new_joker_count,
                jokers = new_state.jokers,
            },
        })
    end

    -- Check for ante/round changes
    if old_state.ante ~= new_state.ante or old_state.round ~= new_state.round then
        table.insert(changes, {
            type = "ROUND_CHANGED",
            source = "BalatroMCP",
            payload = {
                ante = new_state.ante,
                round = new_state.round,
            },
        })
    end

    -- Check for game state changes
    if old_state.game_state ~= new_state.game_state then
        table.insert(changes, {
            type = "PHASE_CHANGED",
            source = "BalatroMCP",
            payload = {
                old_phase = old_state.game_state,
                new_phase = new_state.game_state,
            },
        })
    end

    return changes
end

-- Try to install game hooks
function BalatroMCP:try_install_hooks()
    -- Check if the functions we want to hook exist
    if not G or not G.FUNCS then
        return
    end

    local hooks_to_install = {
        {
            name = "play_cards_from_highlighted",
            exists = G.FUNCS.play_cards_from_highlighted ~= nil,
        },
        { name = "buy_from_shop", exists = G.FUNCS.buy_from_shop ~= nil },
        { name = "end_round", exists = G.FUNCS.end_round ~= nil },
    }

    -- Log what we find
    local all_exist = true
    for _, hook in ipairs(hooks_to_install) do
        if not hook.exists then
            all_exist = false
        end
    end

    -- If all hooks exist, install them
    if all_exist then
        self:hook_game_events()
        self.hooks_installed = true
        self.components.logger:info("All game hooks installed successfully")
    else
        -- Log which hooks are missing (only once every 5 seconds to avoid spam)
        self.hook_check_timer = (self.hook_check_timer or 0) + 1
        if self.hook_check_timer > 300 then -- Roughly 5 seconds at 60 FPS
            self.hook_check_timer = 0
            local missing = {}
            for _, hook in ipairs(hooks_to_install) do
                if not hook.exists then
                    table.insert(missing, hook.name)
                end
            end
            self.components.logger:debug(
                "Waiting for game functions",
                { missing = table.concat(missing, ", ") }
            )
        end
    end
end

-- Check for commands from the event bus
function BalatroMCP:check_for_commands(dt)
    self.command_check_timer = (self.command_check_timer or 0) + dt

    -- Check every 0.5 seconds
    if self.command_check_timer < 0.5 then
        return
    end

    self.command_check_timer = 0

    -- Poll for commands (in a real implementation, this would query an endpoint)
    -- For now, we'll enable auto-play by default for testing
    if not self.auto_play_set and self.components.executor then
        self.components.executor:set_auto_play(true)
        self.auto_play_set = true
    end
end

-- Hook into game state changes
function BalatroMCP:hook_game_events()
    self.components.logger:info("Installing game hooks...")

    -- Hook into card play
    if G.FUNCS.play_cards_from_highlighted then
        local original_play_cards = G.FUNCS.play_cards_from_highlighted
        G.FUNCS.play_cards_from_highlighted = function(e)
            self.components.logger:debug("play_cards_from_highlighted called")
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
        self.components.logger:info("Hooked play_cards_from_highlighted")
    else
        self.components.logger:error("Could not find play_cards_from_highlighted")
    end

    -- Hook into shop purchases
    if G.FUNCS.buy_from_shop then
        local original_buy = G.FUNCS.buy_from_shop
        G.FUNCS.buy_from_shop = function(e)
            self.components.logger:debug("buy_from_shop called")
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
        self.components.logger:info("Hooked buy_from_shop")
    else
        self.components.logger:error("Could not find buy_from_shop")
    end

    -- Hook into round completion
    if G.FUNCS.end_round then
        local original_end_round = G.FUNCS.end_round
        G.FUNCS.end_round = function(e)
            self.components.logger:debug("end_round called")
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
        self.components.logger:info("Hooked end_round")
    else
        self.components.logger:error("Could not find end_round")
    end
end

-- Defer initialization until game is ready
local function initialize_when_ready()
    if not BalatroMCP.initialized then
        -- Check if game is ready (G exists)
        if G then
            BalatroMCP:init()
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
    if not BalatroMCP.initialized and G then
        initialize_when_ready()
    end

    -- Run our update if initialized
    if BalatroMCP.initialized and BalatroMCP.update then
        BalatroMCP:update(dt)
    end
end

-- Don't return anything for SMODS compatibility
