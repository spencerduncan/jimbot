-- BalatroMCP: Action Executor Module
-- Executes AI decisions in the game

local ActionExecutor = {
    logger = nil,
    pending_actions = {},
    action_handlers = {},
    auto_play_enabled = false
}

-- Initialize the executor
function ActionExecutor:init()
    self.logger = BalatroMCP.components.logger
    
    -- Register action handlers
    self:register_handlers()
    
    -- Check if auto-play is enabled
    self.auto_play_enabled = BalatroMCP.config.auto_play or false
    
    self.logger:info("Action executor initialized", {
        auto_play = self.auto_play_enabled
    })
end

-- Register all action handlers
function ActionExecutor:register_handlers()
    -- Menu/game start actions
    self.action_handlers["start_new_run"] = function(params) self:start_new_run(params) end
    self.action_handlers["select_deck"] = function(params) self:select_deck(params) end
    self.action_handlers["select_stake"] = function(params) self:select_stake(params) end
    self.action_handlers["navigate_menu"] = function(params) self:navigate_menu(params) end
    
    -- Playing phase actions
    self.action_handlers["play_hand"] = function() self:play_hand() end
    self.action_handlers["discard"] = function() self:discard_hand() end
    self.action_handlers["sort_hand"] = function() self:sort_hand() end
    self.action_handlers["select_card"] = function(params) self:select_card(params) end
    
    -- Shop phase actions
    self.action_handlers["buy_joker"] = function(params) self:buy_joker(params) end
    self.action_handlers["buy_booster"] = function(params) self:buy_booster(params) end
    self.action_handlers["buy_voucher"] = function(params) self:buy_voucher(params) end
    self.action_handlers["sell_joker"] = function(params) self:sell_joker(params) end
    self.action_handlers["reroll_shop"] = function() self:reroll_shop() end
    self.action_handlers["skip_shop"] = function() self:skip_shop() end
    
    -- Blind selection actions
    self.action_handlers["select_small_blind"] = function() self:select_blind("Small") end
    self.action_handlers["select_big_blind"] = function() self:select_blind("Big") end
    self.action_handlers["select_boss_blind"] = function() self:select_blind("Boss") end
    self.action_handlers["skip_blind"] = function() self:skip_blind() end
    
    -- Round evaluation actions
    self.action_handlers["go_to_shop"] = function() self:go_to_shop() end
end

-- Execute an action
function ActionExecutor:execute_action(action, params)
    if not self.auto_play_enabled then
        self.logger:debug("Auto-play disabled, ignoring action", {action = action})
        return false
    end
    
    local handler = self.action_handlers[action]
    if not handler then
        self.logger:warn("Unknown action", {action = action})
        return false
    end
    
    self.logger:info("Executing action", {action = action, params = params})
    
    -- Execute in protected call
    local success, error = pcall(handler, params)
    
    if not success then
        self.logger:error("Action execution failed", {
            action = action,
            error = error
        })
        return false
    end
    
    return true
end

-- Add action to queue
function ActionExecutor:queue_action(action, params, delay)
    table.insert(self.pending_actions, {
        action = action,
        params = params,
        delay = delay or 0.1,
        queued_at = love.timer.getTime()
    })
end

-- Process pending actions
function ActionExecutor:update(dt)
    if #self.pending_actions == 0 then return end
    
    local current_time = love.timer.getTime()
    local action_data = self.pending_actions[1]
    
    -- Check if enough time has passed
    if current_time - action_data.queued_at >= action_data.delay then
        table.remove(self.pending_actions, 1)
        self:execute_action(action_data.action, action_data.params)
    end
end

-- Playing phase actions
function ActionExecutor:play_hand()
    if not G.FUNCS or not G.FUNCS.play_cards_from_highlighted then
        self.logger:warn("Play function not available")
        return
    end
    
    -- Check if cards are highlighted
    if not G.hand or not G.hand.highlighted or #G.hand.highlighted == 0 then
        self.logger:warn("No cards highlighted to play")
        return
    end
    
    -- Play the highlighted cards
    G.FUNCS.play_cards_from_highlighted()
    self.logger:info("Played hand", {cards = #G.hand.highlighted})
end

function ActionExecutor:discard_hand()
    if not G.FUNCS or not G.FUNCS.discard_cards_from_highlighted then
        self.logger:warn("Discard function not available")
        return
    end
    
    -- Check if discards are available
    if G.GAME.current_round and G.GAME.current_round.discards_left <= 0 then
        self.logger:warn("No discards remaining")
        return
    end
    
    -- Discard highlighted cards
    G.FUNCS.discard_cards_from_highlighted()
    self.logger:info("Discarded cards")
end

function ActionExecutor:sort_hand()
    if G.FUNCS and G.FUNCS.sort_hand then
        G.FUNCS.sort_hand()
        self.logger:info("Sorted hand")
    end
end

function ActionExecutor:select_card(params)
    if not params or not params.card_index then 
        self.logger:warn("No card_index provided")
        return 
    end
    
    if G.hand and G.hand.cards and G.hand.cards[params.card_index] then
        local card = G.hand.cards[params.card_index]
        
        -- Add to highlighted using Balatro's method
        if G.hand.add_to_highlighted then
            G.hand:add_to_highlighted(card)
            self.logger:info("Selected card", {index = params.card_index})
        else
            self.logger:error("G.hand:add_to_highlighted not available")
        end
    else
        self.logger:warn("Card not found", {
            index = params.card_index,
            hand_size = G.hand and G.hand.cards and #G.hand.cards or 0
        })
    end
end

-- Shop phase actions
function ActionExecutor:buy_joker(params)
    if not G.shop or not G.shop.jokers then
        self.logger:warn("Shop not available")
        return
    end
    
    local index = params and params.index or 1
    local card = G.shop.jokers.cards[index]
    
    if not card then
        self.logger:warn("Joker not found in shop", {index = index})
        return
    end
    
    -- Check if we can afford it
    if G.GAME.dollars < card.cost then
        self.logger:warn("Not enough money", {
            cost = card.cost,
            money = G.GAME.dollars
        })
        return
    end
    
    -- Buy the joker
    if G.FUNCS and G.FUNCS.buy_from_shop then
        G.FUNCS.buy_from_shop({config = {ref_table = card}})
        self.logger:info("Bought joker", {
            name = card.ability and card.ability.name or "unknown",
            cost = card.cost
        })
    end
end

function ActionExecutor:buy_booster(params)
    if not G.shop or not G.shop.booster then
        self.logger:warn("No boosters in shop")
        return
    end
    
    local index = params and params.index or 1
    local card = G.shop.booster.cards[index]
    
    if card and G.GAME.dollars >= card.cost then
        if G.FUNCS and G.FUNCS.buy_from_shop then
            G.FUNCS.buy_from_shop({config = {ref_table = card}})
            self.logger:info("Bought booster", {cost = card.cost})
        end
    end
end

function ActionExecutor:buy_voucher(params)
    if not G.shop or not G.shop.vouchers then
        self.logger:warn("No vouchers in shop")
        return
    end
    
    local index = params and params.index or 1
    local card = G.shop.vouchers.cards[index]
    
    if card and G.GAME.dollars >= card.cost then
        if G.FUNCS and G.FUNCS.buy_from_shop then
            G.FUNCS.buy_from_shop({config = {ref_table = card}})
            self.logger:info("Bought voucher", {cost = card.cost})
        end
    end
end

function ActionExecutor:sell_joker(params)
    if not G.jokers or not params or not params.index then
        return
    end
    
    local card = G.jokers.cards[params.index]
    if card and G.FUNCS and G.FUNCS.sell_card then
        G.FUNCS.sell_card({config = {ref_table = card}})
        self.logger:info("Sold joker", {
            name = card.ability and card.ability.name or "unknown"
        })
    end
end

function ActionExecutor:reroll_shop()
    if G.FUNCS and G.FUNCS.reroll_shop then
        if G.GAME.dollars >= G.GAME.current_round.reroll_cost then
            G.FUNCS.reroll_shop()
            self.logger:info("Rerolled shop")
        else
            self.logger:warn("Not enough money to reroll")
        end
    end
end

function ActionExecutor:skip_shop()
    if G.FUNCS and G.FUNCS.skip_shop then
        G.FUNCS.skip_shop()
        self.logger:info("Skipped shop")
    elseif G.FUNCS and G.FUNCS.skip_booster then
        G.FUNCS.skip_booster()
        self.logger:info("Skipped booster")
    end
end

function ActionExecutor:go_to_shop()
    -- Handle navigation to shop from round evaluation
    if G.STATE == G.STATES.ROUND_EVAL then
        self.logger:info("Attempting to go to shop from round evaluation")
        
        -- Try shop-specific navigation functions directly
        if G.FUNCS then
            -- First priority: direct shop navigation functions
            if G.FUNCS.go_to_shop then
                G.FUNCS.go_to_shop()
                self.logger:info("Called G.FUNCS.go_to_shop directly")
                return
            elseif G.FUNCS.to_shop then
                G.FUNCS.to_shop()
                self.logger:info("Called G.FUNCS.to_shop directly")
                return
            elseif G.FUNCS.skip_to_shop then
                G.FUNCS.skip_to_shop()
                self.logger:info("Called G.FUNCS.skip_to_shop directly")
                return
            end
            
            -- Fallback: continue button (usually goes to shop after round eval)
            if G.FUNCS.continue then
                G.FUNCS.continue()
                self.logger:info("Called G.FUNCS.continue as fallback")
                return
            end
        end
        
        -- If no direct functions available, use navigate_menu as last resort
        self:navigate_menu({action = "shop"})
    else
        self.logger:warn("Not in round evaluation state", {current_state = tostring(G.STATE)})
    end
end

-- Blind selection actions
function ActionExecutor:select_blind(blind_type)
    if not G.FUNCS or not G.FUNCS.select_blind then 
        self.logger:error("Blind selection function not available")
        return 
    end
    
    -- Check if blind selection UI is available
    if not G.blind_select_opts then
        self.logger:error("Blind selection UI not initialized")
        return
    end
    
    -- Convert blind type to lowercase key
    local blind_key = blind_type:lower()
    local blind_option = G.blind_select_opts[blind_key]
    
    if not blind_option then
        -- Log available options
        local available = {}
        for key, _ in pairs(G.blind_select_opts) do
            table.insert(available, key)
        end
        self.logger:error("Blind option not found", {
            requested = blind_key,
            available = table.concat(available, ", ")
        })
        return
    end
    
    -- Get the select button UI element
    if not blind_option.get_UIE_by_ID then
        self.logger:error("Blind option missing get_UIE_by_ID method")
        return
    end
    
    local select_button = blind_option:get_UIE_by_ID("select_blind_button")
    if not select_button then
        self.logger:error("Select blind button not found in UI")
        return
    end
    
    -- Call the select blind function with the button element
    self.logger:info("Selecting blind", {type = blind_type})
    local success, error = pcall(function()
        G.FUNCS.select_blind(select_button)
    end)
    
    if success then
        self.logger:info("Blind selected successfully", {type = blind_type})
    else
        self.logger:error("Failed to select blind", {error = tostring(error)})
    end
end

function ActionExecutor:skip_blind()
    if G.FUNCS and G.FUNCS.skip_blind then
        G.FUNCS.skip_blind()
        self.logger:info("Skipped blind")
    end
end

-- Menu navigation actions
function ActionExecutor:start_new_run(params)
    -- Try different ways to start a new run
    if G.FUNCS and G.FUNCS.start_run then
        G.FUNCS.start_run()
        self.logger:info("Started new run")
        return
    end
    
    -- Try to click play button if on main menu
    if G.STATE == G.STATES.MENU then
        if G.FUNCS and G.FUNCS.play then
            G.FUNCS.play()
            self.logger:info("Clicked play button")
        end
    elseif G.STATE == G.STATES.DECK_SELECT then
        -- We're already in deck selection
        self.logger:info("Already in deck selection")
    end
end

function ActionExecutor:select_deck(params)
    local deck_name = params and params.deck or "Red Deck"
    
    -- Check if we're in deck selection state
    if G.STATE ~= G.STATES.DECK_SELECT then
        self.logger:warn("Not in deck selection state")
        return
    end
    
    -- Try to select the specified deck
    if G.FUNCS and G.FUNCS.select_deck then
        -- Find deck by name
        for k, v in pairs(G.P_CENTER_POOLS.Back or {}) do
            if v.name == deck_name and v.unlocked ~= false then
                G.FUNCS.select_deck({config = {ref_table = v}})
                self.logger:info("Selected deck", {deck = deck_name})
                return
            end
        end
    end
    
    self.logger:warn("Deck not found or locked", {deck = deck_name})
end

function ActionExecutor:select_stake(params)
    local stake_level = params and params.stake or 1
    
    -- Check if we're in stake selection
    if G.STATE ~= G.STATES.STAKE_SELECT then
        self.logger:warn("Not in stake selection state")
        return
    end
    
    -- Try to select stake
    if G.FUNCS and G.FUNCS.select_stake then
        G.FUNCS.select_stake({stake = stake_level})
        self.logger:info("Selected stake", {level = stake_level})
    end
end

function ActionExecutor:navigate_menu(params)
    local action = params and params.action
    local direction = params and params.direction
    
    -- If we're in ROUND_EVAL state, handle shop/cash out
    if G.STATE == G.STATES.ROUND_EVAL then
        -- Debug: Log available functions
        if G.FUNCS then
            local available_funcs = {}
            for k, v in pairs(G.FUNCS) do
                if type(v) == "function" and (string.find(k, "shop") or string.find(k, "continue") or string.find(k, "cash")) then
                    table.insert(available_funcs, k)
                end
            end
            self.logger:debug("Available shop/continue functions", {funcs = table.concat(available_funcs, ", ")})
        end
        
        -- When action is "shop", specifically look for shop navigation
        if action == "shop" then
            -- Try shop-specific functions first
            if G.FUNCS and G.FUNCS.go_to_shop then
                G.FUNCS.go_to_shop()
                self.logger:info("Going to shop from round evaluation")
                return
            elseif G.FUNCS and G.FUNCS.to_shop then
                G.FUNCS.to_shop()
                self.logger:info("Going to shop from round evaluation")
                return
            elseif G.FUNCS and G.FUNCS.skip_to_shop then
                G.FUNCS.skip_to_shop()
                self.logger:info("Skipping to shop from round evaluation")
                return
            end
        end
        
        -- For general navigation or continue action, use continue button
        if G.FUNCS and G.FUNCS.continue then
            G.FUNCS.continue()
            self.logger:info("Clicked continue from round evaluation")
            return
        end
        
        -- REMOVED: evaluate_round call that was causing the bug
        -- Do NOT call evaluate_round as it re-triggers the blind UI
    end
    
    -- Handle specific actions
    if action then
        if action == "continue" and G.FUNCS and G.FUNCS.continue then
            G.FUNCS.continue()
            self.logger:info("Clicked continue")
        elseif action == "play" and G.FUNCS and G.FUNCS.play then
            G.FUNCS.play()
            self.logger:info("Clicked play")
        elseif action == "new_run" and G.FUNCS and G.FUNCS.new_run then
            G.FUNCS.new_run()
            self.logger:info("Started new run")
        elseif action == "options" and G.FUNCS and G.FUNCS.options then
            G.FUNCS.options()
            self.logger:info("Opened options")
        elseif action == "shop" and G.FUNCS and G.FUNCS.go_to_shop then
            G.FUNCS.go_to_shop()
            self.logger:info("Going to shop")
        elseif action == "cash_out" and G.FUNCS and G.FUNCS.cash_out then
            G.FUNCS.cash_out()
            self.logger:info("Cashing out")
        end
    end
    
    -- Handle direction-based selection
    if direction == "select" then
        -- Try common select/confirm functions
        if G.FUNCS and G.FUNCS.select then
            G.FUNCS.select()
            self.logger:info("Selected current option")
        elseif G.FUNCS and G.FUNCS.confirm then
            G.FUNCS.confirm()
            self.logger:info("Confirmed selection")
        end
    end
end

-- Enable/disable auto-play
function ActionExecutor:set_auto_play(enabled)
    self.auto_play_enabled = enabled
    self.logger:info("Auto-play " .. (enabled and "enabled" or "disabled"))
end

-- Get current auto-play status
function ActionExecutor:is_auto_play_enabled()
    return self.auto_play_enabled
end

return ActionExecutor