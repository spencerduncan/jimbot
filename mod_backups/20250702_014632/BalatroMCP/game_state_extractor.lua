-- BalatroMCP: Game State Extractor Module
-- Extracts current game state from Balatro's global objects

local Utils = require("mods.BalatroMCP.utils")
local GameStateExtractor = {}

-- Extract current game state
function GameStateExtractor:get_current_state()
    if not G or not G.GAME then
        return {
            in_game = false,
            timestamp = os.time(),
            phase = "MENU"
        }
    end
    
    local state = {
        in_game = true,
        game_id = G.GAME.pseudorandom_seed or "unknown",
        ante = G.GAME.round_resets and G.GAME.round_resets.ante or 0,
        round = G.GAME.round or 0,
        hand_number = G.GAME.current_round and G.GAME.current_round.hands_played or 0,
        
        -- Resources
        chips = G.GAME.chips or 0,
        mult = G.GAME.mult or 0,
        money = G.GAME.dollars or 0,
        hand_size = G.GAME.hand and G.GAME.hand.size or 8,
        hands_remaining = G.GAME.current_round and G.GAME.current_round.hands_left or 0,
        discards_remaining = G.GAME.current_round and G.GAME.current_round.discards_left or 0,
        
        -- Score info
        score_history = {},
        
        -- Collections
        jokers = self:extract_jokers(),
        hand = self:extract_hand(),
        deck = self:extract_deck(),
        consumables = self:extract_consumables(),
        shop_items = self:extract_shop(),
        
        -- Current state
        game_state = self:get_game_phase(),
        ui_state = G.STATE and tostring(G.STATE) or "unknown",
        blind = self:extract_blind_info(),
        
        -- Additional metadata
        timestamp = os.time(),
        frame_count = G.FRAME or 0
    }
    
    -- Add score history if available
    if G.GAME.round_scores then
        for ante, rounds in pairs(G.GAME.round_scores) do
            state.score_history[tostring(ante)] = rounds
        end
    end
    
    return state
end

-- Extract joker information with CIRCULAR REFERENCE SAFE access
function GameStateExtractor:extract_jokers()
    local jokers = {}
    
    if not Utils.safe_check_path(G, {"jokers", "cards"}) then
        return jokers
    end
    
    for i, joker in ipairs(G.jokers.cards) do
        if joker then
            local safe_joker = {
                id = Utils.safe_primitive_value(joker, "unique_val", "joker_" .. i),
                name = Utils.safe_primitive_nested_value(joker, {"ability", "name"}, "Unknown"),
                position = i - 1, -- 0-based indexing
                properties = {
                    mult = Utils.safe_primitive_nested_value(joker, {"ability", "mult"}, 0),
                    chips = Utils.safe_primitive_nested_value(joker, {"ability", "t_chips"}, 0),
                    cost = Utils.safe_primitive_value(joker, "cost", 0),
                    sell_value = Utils.safe_primitive_value(joker, "sell_cost", 0),
                    edition = Utils.get_card_edition_safe(joker),
                    -- Avoid extracting complex 'extra' object to prevent circular references
                }
            }
            table.insert(jokers, safe_joker)
        end
    end
    
    return jokers
end

-- Extract hand cards with CIRCULAR REFERENCE SAFE access
function GameStateExtractor:extract_hand()
    local hand = {}
    
    if not Utils.safe_check_path(G, {"hand", "cards"}) then
        return hand
    end
    
    for i, card in ipairs(G.hand.cards) do
        if card then
            local safe_card = {
                id = Utils.safe_primitive_value(card, "unique_val", "card_" .. i),
                rank = Utils.safe_primitive_nested_value(card, {"base", "value"}, "A"),
                suit = Utils.safe_primitive_nested_value(card, {"base", "suit"}, "Spades"),
                enhancement = Utils.get_card_enhancement_safe(card),
                edition = Utils.get_card_edition_safe(card),
                seal = Utils.get_card_seal_safe(card),
                position = i - 1 -- 0-based indexing
            }
            table.insert(hand, safe_card)
        end
    end
    
    return hand
end

-- Extract deck information
function GameStateExtractor:extract_deck()
    local deck_info = {
        remaining_count = 0,
        cards_remaining = {},
        full_deck = {}
    }
    
    -- Get remaining cards in draw pile
    if Utils.safe_check_path(G, {"deck", "cards"}) then
        deck_info.remaining_count = #G.deck.cards
        -- Only show top few cards to avoid large payloads
        local max_preview = math.min(5, #G.deck.cards)
        for i = 1, max_preview do
            local card = G.deck.cards[i]
            if card then
                table.insert(deck_info.cards_remaining, self:extract_card_info(card))
            end
        end
    end
    
    -- Get full deck composition from G.playing_cards
    if Utils.safe_check_path(G, {"playing_cards"}) then
        for i, card in ipairs(G.playing_cards) do
            if card then
                table.insert(deck_info.full_deck, self:extract_card_info(card))
            end
        end
    end
    
    return deck_info
end

-- Extract individual card information with CIRCULAR REFERENCE SAFE access
function GameStateExtractor:extract_card_info(card)
    if not card then return nil end
    
    return {
        id = Utils.safe_primitive_value(card, "unique_val", nil),
        rank = Utils.safe_primitive_nested_value(card, {"base", "value"}, "unknown"),
        suit = Utils.safe_primitive_nested_value(card, {"base", "suit"}, "unknown"),
        enhancement = Utils.get_card_enhancement_safe(card),
        edition = Utils.get_card_edition_safe(card),
        seal = Utils.get_card_seal_safe(card)
    }
end

-- Extract shop information
function GameStateExtractor:extract_shop()
    local shop = {}
    
    if G.shop and G.shop.jokers and G.shop.jokers.cards then
        for i, item in ipairs(G.shop.jokers.cards) do
            shop["joker_" .. i] = {
                name = item.ability and item.ability.name or "unknown",
                cost = item.cost or 0,
                rarity = item.config and item.config.center and item.config.center.rarity or "common"
            }
        end
    end
    
    if G.shop and G.shop.booster and G.shop.booster.cards then
        for i, item in ipairs(G.shop.booster.cards) do
            shop["booster_" .. i] = {
                name = item.ability and item.ability.name or "unknown",
                cost = item.cost or 0
            }
        end
    end
    
    if G.shop and G.shop.vouchers and G.shop.vouchers.cards then
        for i, item in ipairs(G.shop.vouchers.cards) do
            shop["voucher_" .. i] = {
                name = item.ability and item.ability.name or "unknown",
                cost = item.cost or 0
            }
        end
    end
    
    return shop
end

-- Get current game phase
function GameStateExtractor:get_game_phase()
    if G.STATE == G.STATES.BLIND_SELECT then
        return "BLIND_SELECT"
    elseif G.STATE == G.STATES.SHOP then
        return "SHOP"
    elseif G.STATE == G.STATES.PLAYING then
        return "PLAYING"
    elseif G.STATE == G.STATES.GAME_OVER then
        return "GAME_OVER"
    elseif G.STATE == G.STATES.MENU then
        return "MENU"
    else
        return "UNKNOWN"
    end
end

-- Extract blind information
function GameStateExtractor:extract_blind_info()
    if not G.GAME or not G.GAME.blind then
        return nil
    end
    
    local blind = G.GAME.blind
    return {
        name = blind.name or "unknown",
        chips = blind.chips or 0,
        chip_text = blind.chip_text or "",
        mult = blind.mult or 1,
        defeated = blind.defeated or false,
        boss = blind.boss or false
    }
end

-- Get available actions in current state
function GameStateExtractor:get_available_actions()
    local actions = {}
    local phase = self:get_game_phase()
    
    if phase == "PLAYING" then
        -- Card play actions
        if G.hand and G.hand.highlighted and #G.hand.highlighted > 0 then
            table.insert(actions, "play_hand")
        end
        
        -- Discard actions
        if G.GAME.current_round and G.GAME.current_round.discards_left > 0 then
            table.insert(actions, "discard")
        end
        
        -- Sort hand
        table.insert(actions, "sort_hand")
        
    elseif phase == "SHOP" then
        -- Shop actions
        table.insert(actions, "buy_joker")
        table.insert(actions, "buy_booster")
        table.insert(actions, "buy_voucher")
        table.insert(actions, "sell_joker")
        table.insert(actions, "reroll_shop")
        table.insert(actions, "skip_shop")
        
    elseif phase == "BLIND_SELECT" then
        -- Blind selection
        table.insert(actions, "select_small_blind")
        table.insert(actions, "select_big_blind")
        table.insert(actions, "select_boss_blind")
        table.insert(actions, "skip_blind")
    end
    
    return actions
end

-- Extract consumables (tarot, planet, spectral cards) with CIRCULAR REFERENCE SAFE access
function GameStateExtractor:extract_consumables()
    local consumables = {}
    
    if not Utils.safe_check_path(G, {"consumeables", "cards"}) then
        return consumables
    end
    
    for i, consumable in ipairs(G.consumeables.cards) do
        if consumable then
            local safe_consumable = {
                id = Utils.safe_primitive_value(consumable, "unique_val", "consumable_" .. i),
                name = Utils.safe_primitive_nested_value(consumable, {"ability", "name"}, "Unknown"),
                card_type = Utils.safe_primitive_nested_value(consumable, {"ability", "set"}, "Tarot"),
                position = i - 1, -- 0-based indexing
                properties = {
                    cost = Utils.safe_primitive_value(consumable, "cost", 0),
                    edition = Utils.get_card_edition_safe(consumable)
                }
            }
            table.insert(consumables, safe_consumable)
        end
    end
    
    return consumables
end

-- Get highlighted cards
function GameStateExtractor:get_highlighted_cards()
    local highlighted = {}
    
    if G.hand and G.hand.highlighted then
        for i, card in ipairs(G.hand.highlighted) do
            if card then
                table.insert(highlighted, self:extract_card_info(card))
            end
        end
    end
    
    return highlighted
end

return GameStateExtractor