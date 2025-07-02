# Balatro Modding API Reference

## Overview

This document provides a comprehensive reference for the Balatro modding API, focusing on the most commonly used functions and patterns that mod developers need to understand. It covers SMODS (Steamodded) framework, core game objects, and practical examples.

## Table of Contents

1. [Core Game Objects](#core-game-objects)
2. [SMODS (Steamodded) API](#smods-steamodded-api)
3. [Card Object Structure](#card-object-structure)
4. [Joker System](#joker-system)
5. [UI Element Creation](#ui-element-creation)
6. [Localization System](#localization-system)
7. [Game State Management](#game-state-management)
8. [Animation and Juice Functions](#animation-and-juice-functions)
9. [Sound System](#sound-system)
10. [Achievement and Unlock System](#achievement-and-unlock-system)
11. [Challenge and Seed Modifications](#challenge-and-seed-modifications)
12. [Common Patterns and Examples](#common-patterns-and-examples)

## Core Game Objects

### G (Global Game Object)

The global `G` object is the root of all game state and functionality in Balatro.

#### Key Components:

```lua
G = {
    -- Card Collections
    jokers = {},        -- Active joker cards
    hand = {},          -- Cards in hand
    deck = {},          -- Draw pile
    consumeables = {},  -- Tarot, Planet, Spectral cards
    playing_cards = {}, -- All cards in the game
    
    -- Game State
    GAME = {},          -- Current game state and stats
    STATE = nil,        -- Current game phase enum
    STATES = {},        -- All possible game states
    
    -- UI and Functions
    FUNCS = {},         -- All UI callback functions
    UIT = {},           -- UI node type definitions
    E_MANAGER = {},     -- Event and animation manager
    
    -- Shop and Economy
    shop = {},          -- Shop inventory
    
    -- Other
    FRAME = 0,          -- Current frame number
    localization = {},  -- Text and translations
}
```

### G.jokers

Collection of active joker cards affecting gameplay.

```lua
G.jokers = {
    cards = {},  -- Array of joker card objects
    
    -- Methods
    add_to_deck = function(self, card) end,
    remove_card = function(self, card) end,
    
    -- Properties
    config = {
        card_limit = 5,  -- Default joker limit
    }
}
```

### G.hand

Current hand of playing cards.

```lua
G.hand = {
    cards = {},        -- Array of card objects in hand
    highlighted = {},  -- Currently selected cards
    
    -- Methods
    add_to_highlighted = function(self, card) end,
    remove_from_highlighted = function(self, card) end,
    draw = function(self, amount) end,
}
```

### G.deck

Draw pile management.

```lua
G.deck = {
    cards = {},  -- Remaining cards in draw pile
    
    -- Methods
    shuffle = function(self) end,
    draw_card = function(self) end,
}
```

### G.consumeables

Consumable cards (Tarot, Planet, Spectral).

```lua
G.consumeables = {
    cards = {},  -- Array of consumable card objects
    config = {
        card_limit = 2,  -- Default consumable limit
    }
}
```

## SMODS (Steamodded) API

SMODS is the primary modding framework for Balatro, providing extensive APIs for content creation.

### Mod Structure

```lua
-- mod.json
{
    "id": "my_mod",
    "name": "My Mod",
    "version": "1.0.0",
    "author": "Author Name",
    "description": "Mod description"
}

-- main.lua
SMODS.current_mod = SMODS.current_mod or {}

-- Mod initialization
function SMODS.current_mod.init()
    -- Initialize mod
end
```

### Creating Custom Jokers

```lua
SMODS.Joker {
    key = 'my_joker',
    loc_txt = {
        name = 'My Joker',
        text = {
            "Gain {C:mult}+#1#{} Mult",
            "when played hand contains",
            "a {C:attention}Pair{}"
        }
    },
    config = {extra = {mult = 10}},
    rarity = 2,  -- 1=common, 2=uncommon, 3=rare, 4=legendary
    cost = 5,
    atlas = 'my_joker_atlas',
    pos = {x = 0, y = 0},
    
    -- Calculate function - core joker logic
    calculate = function(self, card, context)
        if context.joker_main and context.cardarea == G.jokers then
            if context.poker_hands and next(context.poker_hands['Pair']) then
                return {
                    mult_mod = card.ability.extra.mult,
                    message = localize{type='variable', key='a_mult', vars={card.ability.extra.mult}}
                }
            end
        end
    end
}
```

### Creating Custom Consumables

```lua
SMODS.Consumable {
    key = 'my_tarot',
    set = 'Tarot',
    loc_txt = {
        name = 'My Tarot',
        text = {
            "Enhance {C:attention}#1#{}",
            "selected cards to",
            "{C:attention}Gold Cards{}"
        }
    },
    config = {max_highlighted = 3},
    
    can_use = function(self, card)
        return #G.hand.highlighted <= self.config.max_highlighted
    end,
    
    use = function(self, card, area, copier)
        for i = 1, #G.hand.highlighted do
            local highlighted = G.hand.highlighted[i]
            highlighted:set_ability(G.P_CENTERS.m_gold, nil, true)
        end
    end
}
```

### Hooks and Callbacks

```lua
-- Hook into existing game functions
local ref_func = G.FUNCS.play_cards_from_highlighted
G.FUNCS.play_cards_from_highlighted = function(e)
    -- Custom logic before
    print("Playing cards!")
    
    -- Call original function
    ref_func(e)
    
    -- Custom logic after
    print("Cards played!")
end
```

## Card Object Structure

### Base Card Object

```lua
Card = {
    -- Identity
    unique_val = "card_123",  -- Unique identifier
    sort_id = 1,              -- Sorting order
    
    -- Visual Properties
    base = {
        value = "A",          -- Rank (A, 2-10, J, Q, K)
        suit = "Spades",      -- Suit
        id = 14,              -- Numeric ID
    },
    
    -- Abilities and Modifiers
    ability = {
        name = "ability_name",
        extra = {},           -- Extra parameters
        mult = 0,             -- Multiplier bonus
        t_chips = 0,          -- Chip bonus
    },
    
    -- State
    cost = 5,                 -- Purchase cost
    sell_cost = 2,            -- Sell value
    highlighted = false,      -- Selection state
    debuffed = false,         -- Debuff state
    
    -- Edition/Enhancement
    edition = nil,            -- Foil, Holo, Polychrome
    seal = nil,               -- Gold, Red, Blue, Purple
    
    -- Methods
    set_ability = function(self, center, initial, delay) end,
    juice_up = function(self, scale, rot) end,
    start_dissolve = function(self) end,
}
```

### Card Methods

```lua
-- Set card enhancement
card:set_ability(G.P_CENTERS.m_gold, nil, true)

-- Add visual effect
card:juice_up(0.3, 0.5)

-- Check if can be played
card:can_play()

-- Get chip/mult contribution
card:get_chip_bonus()
card:get_chip_mult()
```

## Joker System

### Joker Trigger Conditions

Jokers can trigger at various points during gameplay:

```lua
-- Context types for joker calculations
context = {
    -- Before hand is played
    before = true,
    
    -- Main hand evaluation
    joker_main = true,
    
    -- Individual card scoring
    individual = true,
    cardarea = G.play,
    other_card = scoring_card,
    
    -- After hand is played
    after = true,
    
    -- End of round
    end_of_round = true,
    
    -- Card destruction
    destroying_card = true,
    
    -- Shop actions
    buying_card = true,
    selling_card = true,
    reroll_shop = true,
    
    -- Game events
    skip_blind = true,
    setting_blind = true,
    discard = true,
}
```

### Calculate Function Pattern

```lua
calculate = function(self, card, context)
    -- Check trigger condition
    if context.joker_main then
        -- Return effect
        return {
            mult_mod = 10,      -- Add to mult
            chip_mod = 50,      -- Add to chips
            Xmult_mod = 1.5,    -- Multiply total mult
            
            -- Visual feedback
            message = localize{type='variable', key='a_mult', vars={10}},
            
            -- Additional effects
            card_eval_status_text(card, 'extra', nil, nil, nil, {message = "Triggered!"})
        }
    end
end
```

## UI Element Creation

### UI Node Types (G.UIT)

```lua
G.UIT = {
    ROOT = "ROOT",    -- Root container
    C = "C",          -- Column layout
    R = "R",          -- Row layout
    T = "T",          -- Text element
    O = "O",          -- Object container
    B = "B",          -- Box/border
    SLIDER = "SLIDER" -- Slider control
}
```

### Creating a UIBox

```lua
-- Create a simple menu
local my_menu = UIBox({
    definition = create_menu_definition(),
    config = {
        align = "cm",
        offset = {x = 0, y = 10},
        major = G.hand,
        bond = 'Weak'
    }
})

-- Menu definition function
function create_menu_definition()
    return {
        n = G.UIT.ROOT,
        config = {align = "cm", colour = G.C.CLEAR},
        nodes = {
            {n = G.UIT.R, config = {align = "cm"}, nodes = {
                {n = G.UIT.T, config = {text = "Menu Title", scale = 0.5, colour = G.C.WHITE}},
            }},
            {n = G.UIT.R, config = {align = "cm", padding = 0.1}, nodes = {
                create_button("Option 1", "option1_callback"),
                create_button("Option 2", "option2_callback"),
            }}
        }
    }
end
```

### Button Creation

```lua
function create_button(label, func_name)
    return {
        n = G.UIT.C,
        config = {
            align = "cm",
            button = func_name,
            colour = G.C.BLUE,
            minw = 3,
            minh = 0.7,
            r = 0.1,
            hover = true,
            shadow = true
        },
        nodes = {
            {n = G.UIT.T, config = {text = label, scale = 0.3, colour = G.C.WHITE}}
        }
    }
end

-- Button callback
G.FUNCS.option1_callback = function(e)
    -- Handle button press
    print("Option 1 selected!")
end
```

### Dynamic UI Updates

```lua
-- Update UIBox content
G.FUNCS.update_my_menu = function(e)
    local menu_box = e.config.ref_table.menu_box
    local parent = menu_box.parent
    
    -- Remove old content
    parent.config.object:remove()
    
    -- Create new content
    parent.config.object = UIBox({
        definition = create_updated_menu(),
        config = {parent = parent, type = "cm"}
    })
end
```

## Localization System

### Basic Localization

```lua
-- Define localization strings
G.localization.descriptions.Joker.j_my_joker = {
    name = "My Joker",
    text = {
        "Gain {C:mult}+#1#{} Mult",
        "for each {C:attention}Ace{}",
        "in your full deck",
        "{C:inactive}(Currently {C:mult}+#2#{C:inactive} Mult)"
    }
}

-- Localize with variables
localize{type = 'variable', key = 'a_mult', vars = {10}}
localize{type = 'name_text', key = 'j_my_joker'}
```

### Color Codes

```lua
-- Text color codes
{C:mult}        -- Red (multiplier)
{C:chips}       -- Blue (chips)
{C:money}       -- Gold (money)
{C:attention}   -- Yellow (important)
{C:green}       -- Green
{C:inactive}    -- Gray (inactive text)
{C:purple}      -- Purple
{C:black}       -- Black
{C:white}       -- White
{C:red}         -- Red
{C:blue}        -- Blue
```

### Dynamic Text

```lua
-- Mod localization with variables
SMODS.current_mod.loc_vars = function(self, info_queue, card)
    return {
        vars = {
            card.ability.extra.mult,
            card.ability.extra.mult * #G.playing_cards
        }
    }
end
```

## Game State Management

### G.STATE Values

```lua
G.STATES = {
    MENU = 0,
    DECK_SELECT = 1,
    STAKE_SELECT = 2,
    BLIND_SELECT = 3,
    SHOP = 4,
    PLAYING = 5,
    ROUND_EVAL = 6,
    GAME_OVER = 7,
    TAROT_PACK = 8,
    PLANET_PACK = 9,
    SPECTRAL_PACK = 10,
    STANDARD_PACK = 11,
    BUFFOON_PACK = 12,
    SMODS_BOOSTER_OPENED = 13
}
```

### G.GAME Structure

```lua
G.GAME = {
    -- Round information
    round = 1,
    ante = 1,
    round_resets = {
        ante = 1,
        hands = 4,
        discards = 3,
        reroll_cost = 5,
    },
    
    -- Current round state
    current_round = {
        hands_left = 4,
        discards_left = 3,
        hands_played = 0,
        discards_used = 0,
        reroll_cost = 5,
    },
    
    -- Resources
    dollars = 4,
    chips = 0,
    mult = 0,
    
    -- Score tracking
    chips_scored = 0,
    hand_type = "",
    
    -- Blind information
    blind = {
        name = "Small Blind",
        chips = 300,
        mult = 1,
        boss = false,
    },
    
    -- Other
    pseudorandom_seed = "seed_value",
    win_condition = {
        ante = 8,
    },
}
```

### State Transitions

```lua
-- Check current state
if G.STATE == G.STATES.PLAYING then
    -- In playing phase
elseif G.STATE == G.STATES.SHOP then
    -- In shop phase
end

-- State change hooks
local old_set_state = set_state
function set_state(new_state)
    print("State changing from", G.STATE, "to", new_state)
    old_set_state(new_state)
end
```

## Animation and Juice Functions

### juice_up Function

Creates visual feedback effects on cards and UI elements.

```lua
-- Basic juice effect
card:juice_up(scale, rotation)
-- scale: 0.1 to 1.0 (size pulse)
-- rotation: rotation amount in radians

-- Examples
card:juice_up(0.3, 0.5)    -- Moderate effect
card:juice_up(0.8, 0.2)    -- Large scale, small rotation
card:juice_up(0.15, 0.05)  -- Subtle effect
```

### Event Manager (G.E_MANAGER)

```lua
-- Add delayed event
G.E_MANAGER:add_event(Event({
    trigger = 'after',
    delay = 0.4,
    func = function()
        -- Code to execute after delay
        card:juice_up(0.3, 0.5)
        play_sound('card1')
        return true
    end
}))

-- Chain multiple events
G.E_MANAGER:add_event(Event({
    trigger = 'after',
    delay = 0.2,
    func = function()
        -- First action
        return true
    end
}))
```

### Card Animation Functions

```lua
-- Flip card
card:flip()

-- Start dissolve effect
card:start_dissolve({
    G.C.RED,     -- Color
    G.C.BLACK,   -- Shadow color
    nil,         -- Dissolve texture
    'flipped'    -- Flip state
})

-- Highlight effect
card:highlight(true)

-- Set rotation
card:set_rotation(0.1)

-- Shatter effect (destroy card)
card:shatter()
```

### Attention Effects

```lua
-- Draw attention to card
attention_text({
    text = "Triggered!",
    scale = 1.3,
    hold = 0.7,
    align = 'cm',
    offset = {x = 0, y = -0.5},
    major = card
})

-- Card evaluation status
card_eval_status_text(
    card,           -- Card object
    'extra',        -- Text type
    nil,            -- Extra chips
    nil,            -- Percentage
    nil,            -- Total chips
    {
        message = "Custom Message",
        colour = G.C.RED,
        delay = 0.5
    }
)
```

## Sound System

### Playing Sounds

```lua
-- Play built-in sounds
play_sound('card1')          -- Card sound 1
play_sound('chips1')         -- Chip sound
play_sound('button')         -- Button click
play_sound('cancel')         -- Cancel sound
play_sound('highlight1')     -- Highlight sound
play_sound('gold_seal')      -- Gold seal sound
play_sound('tarot1')         -- Tarot sound
play_sound('timpani')        -- Timpani hit
play_sound('negative')       -- Negative/error sound

-- Play with parameters
play_sound('card1', 1, 0.4)  -- sound, pitch, volume
```

### Common Sound Effects

```lua
-- Card actions
'card1', 'card2', 'card3'    -- Card movements
'cardSlide1', 'cardSlide2'   -- Card sliding
'cardFan1', 'cardFan2'       -- Card fanning

-- UI sounds
'button', 'cancel', 'back'   -- UI interactions
'highlight1', 'highlight2'    -- Selection sounds
'hover1', 'hover2', 'hover3'  -- Hover effects

-- Game events
'chips1', 'chips2'           -- Scoring sounds
'coin1', 'coin2', 'coin3'    -- Money sounds
'bell'                       -- Achievement/unlock
```

## Achievement and Unlock System

### Checking Unlocks

```lua
-- Check if content is unlocked
if G.PROFILES[G.SETTINGS.profile].unlocked_jokers.j_joker_name then
    -- Joker is unlocked
end

-- Unlock new content
G.PROFILES[G.SETTINGS.profile].unlocked_jokers.j_my_joker = true
```

### Achievement Triggers

```lua
-- Check for achievement conditions
if G.GAME.dollars >= 100 then
    check_for_unlock({type = 'money_threshold'})
end

-- Custom achievement
check_for_unlock({
    type = 'custom_achievement',
    key = 'a_my_achievement'
})
```

## Challenge and Seed Modifications

### Creating Custom Challenges

```lua
SMODS.Challenge {
    key = 'my_challenge',
    loc_txt = {
        name = "My Challenge",
        text = {
            "Start with {C:attention}10 Jokers{}",
            "but {C:red}no money{}"
        }
    },
    
    -- Challenge rules
    rules = {
        custom = {
            {id = 'no_shop_money', value = true},
            {id = 'starting_jokers', value = 10}
        }
    },
    
    -- Starting deck
    deck = {
        type = 'Challenge Deck',
        cards = {{s='H',r='A'},{s='H',r='A'}}, -- Two Ace of Hearts
    },
    
    -- Starting items
    jokers = {
        {id = 'j_joker'},
        {id = 'j_greedy_joker'},
    },
    
    -- Win condition
    restrictions = {
        banned_cards = {
            {id = 'j_blueprint'},
            {id = 'j_brainstorm'}
        }
    }
}
```

### Seed Modifications

```lua
-- Apply seed effects
if G.GAME.seeded then
    -- Modify RNG behavior
    G.GAME.pseudorandom_seed = G.GAME.seeded
end

-- Custom seed effects
if G.GAME.seed_flags and G.GAME.seed_flags.no_faces then
    -- Remove face cards from deck
end
```

## Common Patterns and Examples

### Creating a Simple Mult Joker

```lua
SMODS.Joker {
    key = 'mult_joker',
    loc_txt = {
        name = 'Mult Master',
        text = {
            "{C:mult}+#1#{} Mult"
        }
    },
    config = {extra = {mult = 15}},
    rarity = 1,
    cost = 4,
    
    loc_vars = function(self, info_queue, card)
        return {vars = {card.ability.extra.mult}}
    end,
    
    calculate = function(self, card, context)
        if context.joker_main then
            return {
                mult_mod = card.ability.extra.mult,
                message = localize{type='variable', key='a_mult', vars={card.ability.extra.mult}}
            }
        end
    end
}
```

### Conditional Trigger Joker

```lua
SMODS.Joker {
    key = 'flush_bonus',
    loc_txt = {
        name = 'Flush Master',
        text = {
            "{X:mult,C:white} X#1# {} Mult if played",
            "hand contains a {C:attention}Flush{}"
        }
    },
    config = {extra = {Xmult = 3}},
    rarity = 2,
    cost = 6,
    
    loc_vars = function(self, info_queue, card)
        return {vars = {card.ability.extra.Xmult}}
    end,
    
    calculate = function(self, card, context)
        if context.joker_main and context.cardarea == G.jokers then
            if context.poker_hands and next(context.poker_hands['Flush']) then
                return {
                    Xmult_mod = card.ability.extra.Xmult,
                    message = localize{type='variable', key='a_xmult', vars={card.ability.extra.Xmult}}
                }
            end
        end
    end
}
```

### Shop Manipulation Joker

```lua
SMODS.Joker {
    key = 'discount_joker',
    loc_txt = {
        name = 'Bargain Hunter',
        text = {
            "All {C:attention}Shop{} items",
            "cost {C:money}$#1#{} less"
        }
    },
    config = {extra = {discount = 2}},
    rarity = 2,
    cost = 6,
    
    loc_vars = function(self, info_queue, card)
        return {vars = {card.ability.extra.discount}}
    end,
    
    -- Hook into shop generation
    add_to_deck = function(self, card, from_debuff)
        -- Modify shop prices when joker is acquired
        if G.shop then
            for k, v in pairs(G.shop.jokers.cards) do
                v.cost = math.max(0, v.cost - card.ability.extra.discount)
            end
        end
    end
}
```

### Custom Tarot Card

```lua
SMODS.Consumable {
    key = 'mult_tarot',
    set = 'Tarot',
    loc_txt = {
        name = 'The Multiplier',
        text = {
            "Enhances up to",
            "{C:attention}#1#{} selected cards",
            "to {C:red}Mult Cards{}"
        }
    },
    config = {max_highlighted = 2},
    
    loc_vars = function(self, info_queue, card)
        return {vars = {self.config.max_highlighted}}
    end,
    
    can_use = function(self, card)
        return #G.hand.highlighted > 0 and #G.hand.highlighted <= self.config.max_highlighted
    end,
    
    use = function(self, card, area, copier)
        for i = 1, #G.hand.highlighted do
            local target = G.hand.highlighted[i]
            G.E_MANAGER:add_event(Event({
                trigger = 'after',
                delay = 0.1 * i,
                func = function()
                    target:juice_up(0.3, 0.5)
                    target:set_ability(G.P_CENTERS.m_mult, nil, true)
                    play_sound('tarot1')
                    return true
                end
            }))
        end
    end
}
```

### Event-Based Joker

```lua
SMODS.Joker {
    key = 'evolving_joker',
    loc_txt = {
        name = 'Evolution',
        text = {
            "Gains {C:mult}+#2#{} Mult",
            "every {C:attention}#3#{} rounds",
            "{C:inactive}(Currently {C:mult}+#1#{C:inactive} Mult)"
        }
    },
    config = {extra = {mult = 5, mult_gain = 3, rounds = 3, rounds_remaining = 3}},
    rarity = 2,
    cost = 5,
    
    loc_vars = function(self, info_queue, card)
        return {vars = {
            card.ability.extra.mult,
            card.ability.extra.mult_gain,
            card.ability.extra.rounds
        }}
    end,
    
    calculate = function(self, card, context)
        -- Provide mult bonus
        if context.joker_main then
            return {
                mult_mod = card.ability.extra.mult,
                message = localize{type='variable', key='a_mult', vars={card.ability.extra.mult}}
            }
        end
        
        -- Track rounds
        if context.end_of_round and not context.blueprint then
            card.ability.extra.rounds_remaining = card.ability.extra.rounds_remaining - 1
            if card.ability.extra.rounds_remaining <= 0 then
                card.ability.extra.rounds_remaining = card.ability.extra.rounds
                card.ability.extra.mult = card.ability.extra.mult + card.ability.extra.mult_gain
                return {
                    message = localize('k_upgrade_ex'),
                    card = card
                }
            end
        end
    end
}
```

## Best Practices

1. **Always use localization** - Never hardcode text strings
2. **Test with different game states** - Ensure your mod works in all phases
3. **Use proper event delays** - Chain animations with G.E_MANAGER
4. **Handle edge cases** - Check for nil values and empty collections
5. **Follow naming conventions** - Use lowercase with underscores for keys
6. **Provide visual feedback** - Use juice_up and card_eval_status_text
7. **Balance carefully** - Test your content at different antes
8. **Document your mod** - Include clear descriptions and examples

## Debugging Tips

```lua
-- Enable debug mode in conf.lua
G.DEBUG = true

-- Log to console
print("Debug:", inspect(card))

-- Check game state
print("Current state:", G.STATE, "Ante:", G.GAME.ante)

-- Inspect objects
local inspect = require('inspect')
print(inspect(G.jokers))

-- Add debug UI
G.FUNCS.debug_info = function()
    return {
        n = G.UIT.ROOT,
        config = {align = "cm"},
        nodes = {
            {n = G.UIT.T, config = {text = "Debug: " .. tostring(G.GAME.dollars), scale = 0.5}}
        }
    }
end
```

## Resources

- **Official Steamodded GitHub**: https://github.com/Steamodded/smods
- **Steamodded Wiki**: GitHub Wiki with guides and documentation
- **Modded Balatro Wiki**: https://balatromods.miraheze.org/
- **Balatro Discord**: Community support and mod sharing
- **Example Mods**: Learn from existing SMODS implementations

This reference covers the essential APIs and patterns for Balatro modding. For more specific implementations, refer to the Steamodded documentation and example mods.