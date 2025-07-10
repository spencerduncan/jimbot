-- Test file for the scoring module
-- Run this to verify scoring tracking functionality

-- Mock the required globals
_G.BalatroMCP = {
    components = {
        logger = {
            info = function(self, msg, data)
                print("[INFO] " .. msg .. (data and ": " .. vim.inspect(data) or ""))
            end,
            debug = function(self, msg, data)
                print("[DEBUG] " .. msg .. (data and ": " .. vim.inspect(data) or ""))
            end,
            warn = function(self, msg, data)
                print("[WARN] " .. msg .. (data and ": " .. vim.inspect(data) or ""))
            end,
        },
        aggregator = {
            add_event = function(self, event)
                print("[EVENT] " .. event.type .. "/" .. (event.subtype or ""))
                if event.payload then
                    print("  Payload: " .. vim.inspect(event.payload))
                end
            end,
            flush = function(self)
                print("[AGGREGATOR] Flushing events")
            end,
        },
    },
}

_G.G = {
    GAME = {
        chips = 1000,
        round_resets = { ante = 1 },
        round = 1,
        current_round = { hands_played = 1 },
    },
}

_G.love = {
    timer = {
        getTime = function()
            return os.time()
        end,
    },
}

-- Helper to pretty print tables
local function inspect(t)
    if type(t) ~= "table" then
        return tostring(t)
    end
    local result = "{"
    for k, v in pairs(t) do
        result = result .. k .. "=" .. tostring(v) .. ", "
    end
    return result .. "}"
end

-- Override vim.inspect if not available
if not vim then
    _G.vim = { inspect = inspect }
end

-- Load the scoring module
local ScoringTracker = require("mods.BalatroMCP.modules.scoring")

print("=== Testing Scoring Module ===")

-- Test initialization
print("\n1. Testing initialization...")
ScoringTracker:init()
print("  ✓ Initialized successfully")

-- Test starting hand evaluation
print("\n2. Testing hand evaluation start...")
ScoringTracker:start_hand_evaluation()
print("  ✓ Hand evaluation started")

-- Test score tracking
print("\n3. Testing score changes...")
G.GAME.chips = 1500
ScoringTracker:track_score_change(1500, "base_hand")
print("  ✓ Score change tracked (1000 -> 1500)")

-- Test joker triggers
print("\n4. Testing joker triggers...")
ScoringTracker:track_joker_trigger({
    name = "Joker",
    id = "j_joker",
    position = 0,
}, 50)
print("  ✓ Joker trigger tracked")

ScoringTracker:track_joker_trigger({
    name = "Crazy Joker",
    id = "j_crazy",
    position = 1,
}, 100)
print("  ✓ Second joker trigger tracked")

-- Test mult/chip tracking
print("\n5. Testing mult/chip changes...")
ScoringTracker:track_mult_change(1, 3, "joker_effect")
ScoringTracker:track_chips_change(100, 150, "card_bonus")
print("  ✓ Mult and chip changes tracked")

-- Test completing hand evaluation
print("\n6. Testing hand evaluation completion...")
G.GAME.chips = 2500
ScoringTracker:complete_hand_evaluation()
print("  ✓ Hand evaluation completed")

-- Test statistics
print("\n7. Testing statistics...")
local stats = ScoringTracker:get_stats()
print("  Statistics:")
print("    Hands tracked: " .. stats.hands_tracked)
print("    Total score delta: " .. stats.total_score_delta)
print("    Max hand score: " .. stats.max_hand_score)
print("    Average hand score: " .. stats.avg_hand_score)

-- Test another hand
print("\n8. Testing second hand...")
G.GAME.chips = 2500
ScoringTracker:start_hand_evaluation()
G.GAME.chips = 3000
ScoringTracker:track_score_change(3000, "another_hand")
G.GAME.chips = 3500
ScoringTracker:complete_hand_evaluation()
print("  ✓ Second hand tracked")

-- Final statistics
print("\n9. Final statistics...")
stats = ScoringTracker:get_stats()
print("  Statistics after 2 hands:")
print("    Hands tracked: " .. stats.hands_tracked)
print("    Total score delta: " .. stats.total_score_delta)
print("    Max hand score: " .. stats.max_hand_score)
print("    Average hand score: " .. stats.avg_hand_score)

print("\n=== All tests passed! ===")

