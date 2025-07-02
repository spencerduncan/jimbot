# Lua Style Guide for Balatro Mod Development

This guide defines Lua coding conventions specifically for Balatro mod development, incorporating best practices from the Lua community and patterns from successful Balatro mods.

## Table of Contents
1. [General Principles](#general-principles)
2. [File Organization](#file-organization)
3. [Naming Conventions](#naming-conventions)
4. [Variables and Scope](#variables-and-scope)
5. [Tables and Metatables](#tables-and-metatables)
6. [Functions](#functions)
7. [Error Handling](#error-handling)
8. [Balatro-Specific Patterns](#balatro-specific-patterns)
9. [Common Interactions](#common-interactions)
10. [Performance Guidelines](#performance-guidelines)
11. [Debugging and Testing](#debugging-and-testing)

## General Principles

### Core Rules
- **Always use `local`** - Never pollute the global namespace
- **Consistent indentation** - 2 or 4 spaces (never tabs)
- **Descriptive names** - Code is read more than written
- **Fail gracefully** - Always check for nil values
- **Hook responsibly** - Preserve original functionality

### Code Style
```lua
-- Good: Clear, local scope, proper spacing
local function calculate_joker_mult(card, context)
    if not card or not context then
        return 0
    end
    
    local base_mult = card.ability.extra.mult or 1
    local bonus = context.scoring_hand and 2 or 1
    
    return base_mult * bonus
end

-- Bad: Global function, no validation, unclear
function calcMult(c,ctx)
    return c.ability.extra.mult*2
end
```

## File Organization

### Mod Structure
```
YourMod/
├── mod.json              -- Mod metadata
├── main.lua              -- Entry point
├── localization/
│   ├── default.lua       -- Fallback language
│   └── en-us.lua         -- English strings
├── assets/
│   ├── 1x/               -- Standard resolution
│   │   └── jokers.png    
│   └── 2x/               -- High resolution
│       └── jokers.png
├── jokers/               -- Joker definitions
│   ├── multiplier_jokers.lua
│   └── chip_jokers.lua
├── consumables/          -- Tarot/Planet/Spectral cards
│   └── custom_tarots.lua
├── utils/                -- Utility functions
│   └── helpers.lua
└── config.lua            -- Configuration values
```

### Main File Structure
```lua
-- main.lua
--- @module YourModName
--- @description Brief description of your mod
--- @author YourName

-- Mod metadata
local MOD_ID = "your_mod_id"
local MOD_NAME = "Your Mod Name"
local MOD_VERSION = "1.0.0"
local MOD_PREFIX = "YM"  -- Short prefix for your mod

-- Local references to frequently used globals
local G = G
local SMODS = SMODS

-- Load configuration
local config = require("config")

-- Load utilities
local utils = require("utils.helpers")

-- Initialize mod
local function init()
    -- Load jokers
    require("jokers.multiplier_jokers")
    require("jokers.chip_jokers")
    
    -- Load consumables
    require("consumables.custom_tarots")
    
    -- Set up hooks
    setup_hooks()
end

-- Hook setup
local function setup_hooks()
    -- Hook implementations
end

-- Start initialization
init()
```

## Naming Conventions

### General Rules
| Type | Convention | Example |
|------|------------|---------|
| Local variables | `snake_case` | `local card_count = 5` |
| Global variables | Avoid! Use mod namespace | `MOD.my_value` |
| Constants | `UPPER_SNAKE_CASE` | `local MAX_MULT = 100` |
| Functions | `snake_case` | `function calculate_score()` |
| Modules | `snake_case` | `require("utils.helpers")` |
| Classes/Constructors | `PascalCase` | `function JokerCard()` |
| Private/Internal | `_leading_underscore` | `local _internal_state` |
| Ignored variables | `_` | `for _, card in ipairs(cards)` |

### Balatro-Specific Naming
```lua
-- Joker keys follow pattern: j_prefix_name
SMODS.Joker({
    key = 'golden_ratio',              -- Becomes j_ym_golden_ratio
    loc_key = 'ym_golden_ratio',       -- Localization key
    config = { extra = { mult = 8 } },  -- Always use 'extra' for custom data
})

-- Atlas keys: prefix_type_name
SMODS.Atlas({
    key = 'ym_jokers',                  -- Your mod's joker atlas
    path = 'jokers.png',
    px = 71,
    py = 95
})

-- Sound keys: prefix_sound_name
SMODS.Sound({
    key = 'ym_level_up',
    path = 'level_up.ogg'
})
```

## Variables and Scope

### Always Use Local
```lua
-- Good: Local by default
local function process_hand(cards)
    local total_chips = 0
    local total_mult = 1
    
    for _, card in ipairs(cards) do
        total_chips = total_chips + card.base.nominal
    end
    
    return total_chips, total_mult
end

-- Bad: Global pollution
function processHand(cards)  -- Global function
    totalChips = 0           -- Global variable!
    totalMult = 1            -- Global variable!
    -- ...
end
```

### Caching Global Access
```lua
-- Cache frequently accessed globals at file scope
local G = G
local SMODS = SMODS
local pairs = pairs
local ipairs = ipairs
local math_floor = math.floor
local table_insert = table.insert

-- Use cached references
local function optimized_function()
    local value = math_floor(G.GAME.chips * 1.5)
    table_insert(G.hand.cards, new_card)
end
```

### Module-Level State
```lua
-- Use module table for shared state
local M = {}
M.active_effects = {}
M.config = {
    max_triggers = 5,
    base_mult = 2
}

-- Access module state
function M.add_effect(effect)
    table.insert(M.active_effects, effect)
end

return M
```

## Tables and Metatables

### Table Initialization
```lua
-- Good: Initialize with known structure
local joker_data = {
    name = "Lucky Seven",
    mult = 7,
    chips = 0,
    triggers = {},
    config = {
        suit = "Hearts",
        rank = "7"
    }
}

-- Good: Array initialization
local card_pool = {}
for i = 1, 52 do
    card_pool[i] = create_card(i)  -- Array part
end

-- Avoid: Mixed array/hash in loops
local bad_pool = {}
for i = 1, 52 do
    bad_pool[i] = create_card(i)
    bad_pool["card_" .. i] = true  -- Converts to hash
end
```

### Metatables for Joker Behavior
```lua
-- Joker class with metamethods
local JokerBase = {}
JokerBase.__index = JokerBase

function JokerBase:new(config)
    local obj = setmetatable({}, self)
    obj.mult = config.mult or 1
    obj.chips = config.chips or 0
    obj.triggers = 0
    return obj
end

function JokerBase:calculate(context)
    if context.joker_main then
        return {
            mult_mod = self.mult,
            chip_mod = self.chips,
            message = localize('k_upgrade_ex')
        }
    end
end

-- Extend for specific joker
local LuckyJoker = setmetatable({}, {__index = JokerBase})
LuckyJoker.__index = LuckyJoker

function LuckyJoker:calculate(context)
    -- Call parent
    local result = JokerBase.calculate(self, context)
    
    -- Add lucky logic
    if context.scoring_name == "Lucky 7s" then
        result.mult_mod = result.mult_mod * 2
    end
    
    return result
end
```

## Functions

### Function Definition
```lua
-- Good: Clear parameters, local scope
local function calculate_hand_score(cards, mult, chips)
    if not cards or #cards == 0 then
        return 0, 0
    end
    
    local total_chips = chips or 0
    local total_mult = mult or 1
    
    for _, card in ipairs(cards) do
        total_chips = total_chips + (card.base.nominal or 0)
    end
    
    return total_chips, total_mult
end

-- Good: Document complex functions
--- Calculate joker synergy bonus
--- @param joker1 table First joker card
--- @param joker2 table Second joker card
--- @param context table Current game context
--- @return number Synergy multiplier
local function calculate_synergy(joker1, joker2, context)
    -- Implementation
end
```

### Callback Patterns
```lua
-- Balatro callback pattern
SMODS.Joker({
    key = 'multiplier_master',
    calculate = function(self, card, context)
        -- Early returns for invalid contexts
        if not context.joker_main then return end
        if not context.scoring_hand then return end
        
        -- Calculate effect
        local mult = card.ability.extra.mult or 4
        local hand_size = #context.scoring_hand
        
        -- Return effect table
        return {
            mult_mod = mult * hand_size,
            message = localize{
                type = 'variable',
                key = 'a_mult',
                vars = {mult * hand_size}
            },
            card = card
        }
    end
})
```

### Hook Pattern
```lua
-- Safe hook pattern
local function hook_function(original_func)
    return function(...)
        -- Pre-hook validation
        local args = {...}
        if not validate_args(args) then
            return original_func(...)
        end
        
        -- Pre-hook logic
        modify_args(args)
        
        -- Call original with modified args
        local results = {original_func(table.unpack(args))}
        
        -- Post-hook logic
        modify_results(results)
        
        return table.unpack(results)
    end
end

-- Apply hook
local original_play = G.FUNCS.play_cards_from_highlighted
G.FUNCS.play_cards_from_highlighted = hook_function(original_play)
```

## Error Handling

### Defensive Programming
```lua
-- Always validate inputs
local function apply_joker_effect(card, context)
    -- Validate card
    if not card then
        return nil, "No card provided"
    end
    
    if not card.ability then
        return nil, "Card has no ability"
    end
    
    -- Validate context
    if not context or type(context) ~= "table" then
        return nil, "Invalid context"
    end
    
    -- Safe property access
    local mult = (card.ability.extra and card.ability.extra.mult) or 1
    local triggers = card.ability.extra and card.ability.extra.triggers
    
    -- Process effect
    if triggers and triggers > 0 then
        return mult * triggers, nil
    end
    
    return mult, nil
end
```

### Protected Calls
```lua
-- Use pcall for risky operations
local function load_mod_config(path)
    local success, result = pcall(function()
        return require(path)
    end)
    
    if not success then
        -- Log error, return defaults
        print("[ERROR] Failed to load config: " .. tostring(result))
        return get_default_config()
    end
    
    return result
end

-- xpcall with traceback for debugging
local function debug_call(func, ...)
    local function error_handler(err)
        print("[ERROR] " .. err)
        print(debug.traceback())
    end
    
    local success, result = xpcall(func, error_handler, ...)
    return success, result
end
```

## Balatro-Specific Patterns

### Creating Custom Jokers
```lua
-- Complete joker implementation
SMODS.Joker({
    key = 'fibonacci_sequence',
    loc_txt = {
        name = 'Fibonacci Sequence',
        text = {
            "Each played {C:attention}Ace{}, {C:attention}2{}, {C:attention}3{}, {C:attention}5{}, or {C:attention}8{}",
            "gives {C:mult}+#1#{} Mult when scored",
            "{C:inactive}(Currently {C:mult}+#2#{C:inactive} Mult)"
        }
    },
    config = { 
        extra = { 
            mult_per_trigger = 2,
            current_mult = 0,
            fib_ranks = {1, 2, 3, 5, 8}  -- Store as array for performance
        } 
    },
    rarity = 2,
    cost = 6,
    atlas = 'ym_jokers',
    pos = { x = 0, y = 0 },
    
    -- Localization variables
    loc_vars = function(self, info_queue, card)
        return {
            vars = {
                card.ability.extra.mult_per_trigger,
                card.ability.extra.current_mult
            }
        }
    end,
    
    -- Main calculation
    calculate = function(self, card, context)
        -- Fibonacci number detection
        if context.individual and context.cardarea == G.play then
            local rank = context.other_card:get_id()
            for _, fib_rank in ipairs(card.ability.extra.fib_ranks) do
                if rank == fib_rank then
                    card.ability.extra.current_mult = card.ability.extra.current_mult + 
                        card.ability.extra.mult_per_trigger
                    
                    -- Visual feedback
                    card:juice_up(0.5, 0.5)
                    
                    return {
                        extra = {
                            focus = card,
                            message = localize('k_upgrade_ex')
                        }
                    }
                end
            end
        end
        
        -- Apply accumulated mult
        if context.joker_main and card.ability.extra.current_mult > 0 then
            return {
                mult_mod = card.ability.extra.current_mult,
                message = localize{
                    type = 'variable',
                    key = 'a_mult',
                    vars = {card.ability.extra.current_mult}
                }
            }
        end
    end,
    
    -- Reset on round end
    on_round_end = function(self, card)
        card.ability.extra.current_mult = 0
    end
})
```

### UI Element Creation
```lua
-- Create custom UI box
local function create_joker_info_box()
    return {
        n = G.UIT.ROOT,
        config = {
            align = "cm",
            colour = G.C.CLEAR,
            minh = 4,
            minw = 6
        },
        nodes = {
            {
                n = G.UIT.C,
                config = {
                    align = "cm",
                    padding = 0.1
                },
                nodes = {
                    {
                        n = G.UIT.R,
                        config = { align = "cm" },
                        nodes = {
                            {
                                n = G.UIT.T,
                                config = {
                                    text = "Custom Joker Info",
                                    scale = 0.4,
                                    colour = G.C.WHITE
                                }
                            }
                        }
                    },
                    {
                        n = G.UIT.R,
                        config = { align = "cm", padding = 0.1 },
                        nodes = {
                            UIBox_button({
                                button = "view_details",
                                label = {"View Details"},
                                colour = G.C.BLUE,
                                minw = 3,
                                minh = 0.7,
                                scale = 0.5
                            })
                        }
                    }
                }
            }
        }
    }
end

-- Register button callback
G.FUNCS.view_details = function()
    -- Handle button click
    play_sound('button')
    -- Show details logic
end
```

### Card Manipulation
```lua
-- Add enhancement to cards in hand
local function enhance_hand_cards(enhancement_type)
    if not G.hand or not G.hand.cards then return end
    
    for _, card in ipairs(G.hand.cards) do
        -- Check if card can be enhanced
        if card.config.center ~= G.P_CENTERS.c_base then
            -- Skip already enhanced cards
            goto continue
        end
        
        -- Apply enhancement
        card:set_edition({
            [enhancement_type] = true
        })
        
        -- Visual feedback
        card:juice_up(0.3, 0.5)
        play_sound('gold_seal')
        
        ::continue::
    end
end

-- Create and add card to deck
local function spawn_random_joker()
    -- Create joker with random or specific key
    local card = create_card('Joker', G.jokers, nil, nil, nil, nil, nil)
    
    -- Add to joker area
    card:add_to_deck()
    G.jokers:emplace(card)
    
    -- Animation
    card:start_materialize()
    
    -- Play sound
    play_sound('card1')
    
    return card
end
```

### Save Data Management
```lua
-- Initialize mod save data
local function init_save_data()
    -- Ensure save structure exists
    G.GAME.ym_mod_data = G.GAME.ym_mod_data or {}
    
    -- Set defaults if missing
    local data = G.GAME.ym_mod_data
    data.version = data.version or MOD_VERSION
    data.unlocks = data.unlocks or {}
    data.statistics = data.statistics or {
        jokers_created = 0,
        hands_played = 0,
        best_mult = 0
    }
    
    -- Migrate old save data if needed
    if data.version ~= MOD_VERSION then
        migrate_save_data(data)
    end
end

-- Update statistics
local function track_statistic(stat_name, value)
    if not G.GAME.ym_mod_data then
        init_save_data()
    end
    
    local stats = G.GAME.ym_mod_data.statistics
    if stat_name == "best_mult" then
        stats[stat_name] = math.max(stats[stat_name] or 0, value)
    else
        stats[stat_name] = (stats[stat_name] or 0) + (value or 1)
    end
end
```

## Common Interactions

### Scoring Modification
```lua
-- Modify hand chips/mult during scoring
local function modify_hand_scoring()
    local old_evaluate = G.FUNCS.evaluate_play
    
    G.FUNCS.evaluate_play = function(e)
        -- Let original function run first
        local ret = old_evaluate(e)
        
        -- Modify the scoring
        if G.GAME.current_round.hands_played == 0 then
            -- First hand bonus
            hand_chips = hand_chips * 2
            mult = mult * 2
            
            -- Add floating text
            card_eval_status_text(
                G.hand.cards[1], 
                'extra', 
                nil, 
                nil, 
                {
                    message = "First Hand!",
                    colour = G.C.GOLD
                }
            )
        end
        
        return ret
    end
end
```

### Shop Manipulation
```lua
-- Modify shop on creation
local function modify_shop()
    local old_shop = G.FUNCS.shop_generation
    
    G.FUNCS.shop_generation = function()
        -- Generate normal shop
        local ret = old_shop()
        
        -- Add custom joker to shop
        if G.GAME.round % 3 == 0 then  -- Every 3rd round
            local card = create_card('Joker', G.shop_jokers, nil, nil, nil, nil, 'j_ym_special')
            card.cost = math.floor(card.cost * 0.5)  -- Half price
            card:set_edition({negative = true})  -- Make it negative
            G.shop_jokers:emplace(card)
        end
        
        return ret
    end
end
```

### Deck Manipulation
```lua
-- Add cards to deck
local function add_special_cards_to_deck(count)
    count = count or 5
    
    G.E_MANAGER:add_event(Event({
        func = function()
            for i = 1, count do
                -- Create enhanced playing card
                local card = create_card(
                    'Enhanced',           -- type
                    G.deck,              -- area
                    nil,                 -- legendary
                    nil,                 -- rarity
                    nil,                 -- skip_materialize
                    nil,                 -- soulable
                    'm_gold'            -- key for Gold Card
                )
                
                -- Set specific rank/suit if needed
                card:set_base(G.P_CARDS["S_A"])  -- Ace of Spades
                
                -- Add to deck
                G.deck:emplace(card)
                
                -- Small delay between cards
                if i < count then
                    G.E_MANAGER:add_event(Event({
                        func = function()
                            return true
                        end,
                        delay = 0.1
                    }))
                end
            end
            
            -- Update deck display
            G.deck:shuffle()
            
            return true
        end
    }))
end
```

### Consumable Effects
```lua
-- Create custom tarot card
SMODS.Tarot({
    key = 'transformation',
    loc_txt = {
        name = 'Transformation',
        text = {
            "Convert all cards in hand",
            "to {C:attention}Aces{}"
        }
    },
    config = {},
    pos = { x = 0, y = 1 },
    atlas = 'ym_tarots',
    
    use = function(self, card, area, copier)
        -- Transform all cards in hand to Aces
        G.E_MANAGER:add_event(Event({
            trigger = 'after',
            delay = 0.4,
            func = function()
                local cards = {}
                for _, hand_card in ipairs(G.hand.cards) do
                    table.insert(cards, hand_card)
                end
                
                -- Transform each card
                for i, hand_card in ipairs(cards) do
                    G.E_MANAGER:add_event(Event({
                        trigger = 'after',
                        delay = 0.1 * i,
                        func = function()
                            -- Keep suit, change to Ace
                            local suit = hand_card.base.suit
                            local ace_key = suit .. "_A"
                            
                            hand_card:set_base(G.P_CARDS[ace_key])
                            hand_card:juice_up(0.3, 0.5)
                            play_sound('tarot1')
                            
                            return true
                        end
                    }))
                end
                
                return true
            end
        }))
    end
})
```

### Round Events
```lua
-- Hook into round transitions
local function setup_round_hooks()
    -- Before round starts
    local old_round_start = G.FUNCS.start_round
    G.FUNCS.start_round = function()
        -- Pre-round setup
        if G.GAME.round == 1 then
            -- First round bonus
            G.GAME.dollars = G.GAME.dollars + 10
            attention_text({
                text = "+$10 First Round Bonus!",
                scale = 1.3,
                hold = 2,
                backdrop_colour = G.C.MONEY,
                align = 'cm',
                major = G.play
            })
        end
        
        return old_round_start()
    end
    
    -- After hand played
    local old_play_hand = G.FUNCS.play_cards_from_highlighted
    G.FUNCS.play_cards_from_highlighted = function(e)
        local ret = old_play_hand(e)
        
        -- Check for special conditions
        if #G.play.cards == 5 then
            local all_same_suit = true
            local suit = G.play.cards[1].base.suit
            
            for _, card in ipairs(G.play.cards) do
                if card.base.suit ~= suit then
                    all_same_suit = false
                    break
                end
            end
            
            if all_same_suit then
                -- Bonus for flush
                ease_dollars(5)
                card_eval_status_text(
                    G.play.cards[1],
                    'extra',
                    nil,
                    nil,
                    {
                        message = "+$5",
                        colour = G.C.MONEY,
                        delay = 0.45
                    }
                )
            end
        end
        
        return ret
    end
end
```

## Performance Guidelines

### Table Optimization
```lua
-- Pre-allocate tables when size is known
local function create_card_pool(size)
    local pool = {}
    -- Pre-allocate
    for i = 1, size do
        pool[i] = false
    end
    
    -- Fill pool
    for i = 1, size do
        pool[i] = create_card(i)
    end
    
    return pool
end

-- Reuse tables instead of creating new ones
local temp_hand = {}  -- Module-level temporary table

local function evaluate_hand(cards)
    -- Clear and reuse
    for k in pairs(temp_hand) do
        temp_hand[k] = nil
    end
    
    -- Use temporary table
    for _, card in ipairs(cards) do
        local rank = card:get_id()
        temp_hand[rank] = (temp_hand[rank] or 0) + 1
    end
    
    return calculate_hand_type(temp_hand)
end
```

### String Optimization
```lua
-- Cache string concatenations
local MULT_PREFIX = "Mult x"
local CHIP_PREFIX = "Chips +"

local function format_bonus(mult, chips)
    -- Avoid repeated concatenation
    if mult > 1 and chips > 0 then
        return MULT_PREFIX .. mult .. ", " .. CHIP_PREFIX .. chips
    elseif mult > 1 then
        return MULT_PREFIX .. mult
    elseif chips > 0 then
        return CHIP_PREFIX .. chips
    end
    return ""
end

-- Use table.concat for multiple strings
local function build_description(parts)
    return table.concat(parts, "\n")
end
```

### Loop Optimization
```lua
-- Cache table lengths
local function process_large_array(array)
    local len = #array  -- Cache length
    
    for i = 1, len do
        -- Process array[i]
    end
end

-- Use pairs vs ipairs appropriately
local function count_suits(cards)
    local suits = {}
    
    -- ipairs for arrays
    for _, card in ipairs(cards) do
        local suit = card.base.suit
        suits[suit] = (suits[suit] or 0) + 1
    end
    
    -- pairs for hash tables
    local count = 0
    for suit, amount in pairs(suits) do
        if amount >= 3 then
            count = count + 1
        end
    end
    
    return count
end
```

## Debugging and Testing

### Debug Helpers
```lua
-- Conditional debug logging
local DEBUG = false  -- Set to true during development

local function debug_log(message, data)
    if not DEBUG then return end
    
    print("[YM_DEBUG] " .. message)
    if data then
        print("  Data: " .. inspect(data))
    end
end

-- Performance timing
local function timed_function(name, func, ...)
    local start = os.clock()
    local results = {func(...)}
    local elapsed = os.clock() - start
    
    if elapsed > 0.016 then  -- Log if > 1 frame at 60fps
        print(string.format("[PERF] %s took %.3f seconds", name, elapsed))
    end
    
    return table.unpack(results)
end
```

### Testing Patterns
```lua
-- Test helper functions
local function test_joker_effect()
    -- Create test context
    local test_card = {
        ability = {
            extra = {
                mult = 5,
                triggers = 3
            }
        }
    }
    
    local test_context = {
        joker_main = true,
        scoring_hand = true,
        full_hand = {}
    }
    
    -- Run calculation
    local result = calculate_joker_mult(test_card, test_context)
    
    -- Verify
    assert(result == 15, "Expected 15, got " .. tostring(result))
    debug_log("Joker effect test passed")
end

-- Console command registration
G.FUNCS.test_my_mod = function()
    test_joker_effect()
    print("All tests passed!")
end
```

### Common Debugging Issues
```lua
-- Issue: Card doesn't appear in shop
-- Solution: Check atlas loading
local function debug_atlas()
    if not G.ASSET_ATLAS["ym_jokers"] then
        print("[ERROR] Atlas 'ym_jokers' not loaded!")
        print("  Check: Path exists? Resolution folders?")
    end
end

-- Issue: Joker effect not triggering
-- Solution: Add debug output to calculate
calculate = function(self, card, context)
    debug_log("Calculate called", {
        context_type = context.joker_main and "joker_main" or "other",
        card_area = context.cardarea and context.cardarea.config.type
    })
    
    -- Effect logic...
end

-- Issue: Nil reference errors
-- Solution: Defensive checking
local function safe_get_joker_mult(card)
    if not card then
        debug_log("WARNING: Nil card passed")
        return 1
    end
    
    if not card.ability then
        debug_log("WARNING: Card missing ability")
        return 1
    end
    
    return card.ability.extra and card.ability.extra.mult or 1
end
```

## Best Practices Summary

1. **Always use `local`** - Global namespace pollution breaks other mods
2. **Validate inputs** - Never assume game state is valid
3. **Hook responsibly** - Always call original functions
4. **Cache globals** - Improves performance significantly
5. **Use proper naming** - Follow key patterns (j_prefix_name)
6. **Handle errors gracefully** - Use pcall for risky operations
7. **Optimize loops** - Pre-allocate tables, cache lengths
8. **Test thoroughly** - Include debug helpers and test functions
9. **Document your mod** - Clear comments and localization
10. **Respect the player** - Don't break game balance unfairly