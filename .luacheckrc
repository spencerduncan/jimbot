-- Luacheck configuration for Balatro mods

-- Globals
globals = {
    -- Balatro/LOVE2D globals
    "G",
    "SMODS",
    "love",
    "create_card",
    "Card",
    "localize",
    "play_sound",
    "ease_dollars",
    "attention_text",
    "card_eval_status_text",
    "UIBox_button",
    "Event",
    "inspect",
    
    -- Common Balatro objects
    "Joker",
    "Tarot",
    "Planet",
    "Spectral",
    "Voucher",
    "Back",
    "Blind",
    "Tag",
    "Booster",
    "Edition",
    "Shader",
    "Consumable",
    "Stake",
    
    -- Debugging globals (development only)
    "debug",
    "print",
}

-- Read-only globals
read_globals = {
    "string",
    "table",
    "math",
    "io",
    "os",
    "pairs",
    "ipairs",
    "next",
    "type",
    "tostring",
    "tonumber",
    "setmetatable",
    "getmetatable",
    "rawget",
    "rawset",
    "pcall",
    "xpcall",
    "require",
    "assert",
    "error",
    "select",
    "unpack",
    "coroutine",
    "_VERSION",
    "_G",
}

-- Module-level variables
files["**/*.lua"] = {
    max_line_length = 120,
    max_code_line_length = 100,
    max_string_line_length = 120,
    max_comment_line_length = 120,
}

-- Test files
files["**/tests/**/*.lua"] = {
    std = "+busted",
    globals = {"describe", "it", "before_each", "after_each", "setup", "teardown", "pending"},
    ignore = {"121"}, -- Allow setting read-only fields in tests for mocking
}

-- Main mod files
files["**/main.lua"] = {
    ignore = {"121"}, -- Allow setting global mod variables
}

-- Ignore certain warnings
ignore = {
    "212", -- Unused argument
    "213", -- Unused loop variable
    "211", -- Unused variable
    "311", -- Value assigned to variable is never used
    "431", -- Shadowing upvalue
    "542", -- Empty if branch
    "611", -- Line contains only whitespace
    "612", -- Line contains trailing whitespace
    "614", -- Trailing whitespace in comment
    "621", -- Inconsistent whitespace
    "631", -- Line is too long
    "121", -- Setting read-only field (common in Lua modules and tests)
    "122", -- Setting read-only field of global _G (common in Lua modules and tests)
    "131", -- Setting non-standard global variable
    "112", -- Mutating non-standard global variable
    "113", -- Accessing undefined variable
}

-- Allow specific unused arguments
unused_args = false
unused_secondaries = false
allow_defined = true
allow_defined_top = true

-- Exclude certain directories
exclude_files = {
    ".luacheckrc",
    "vendor/**/*.lua",
    "libs/**/*.lua",
    ".vscode/**/*.lua",
}

-- Standard library version
std = "lua51+love"

-- Custom standard library additions for LOVE2D
stds.love = {
    read_globals = {
        love = {
            fields = {
                "graphics", "audio", "keyboard", "mouse", "filesystem",
                "timer", "event", "system", "window", "thread", "sound",
                "font", "image", "math", "physics", "touch", "video",
            }
        }
    }
}

-- Balatro-specific standard
stds.balatro = {
    read_globals = {
        G = {
            fields = {
                "GAME", "STATE", "STATES", "FUNCS", "UIDEF",
                "jokers", "hand", "deck", "consumeables", "play",
                "shop_jokers", "shop_vouchers", "shop_booster",
                "P_CARDS", "P_CENTERS", "C", "UIT", "E_MANAGER",
                "CONTROLLER", "SETTINGS", "PROFILES", "SPEEDFACTOR",
                "canvas", "ROOM", "LOBBY", "OVERLAY", "SCENE",
            }
        },
        SMODS = {
            fields = {
                "Joker", "Consumable", "Back", "Voucher", "Blind",
                "Booster", "Atlas", "Sound", "Shader", "Tag",
                "current_mod", "end_load",
            }
        }
    }
}

std = "lua51+love+balatro"