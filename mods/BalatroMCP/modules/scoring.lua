-- BalatroMCP: Scoring Module
-- Tracks score changes during hand evaluation and sends updates through aggregator

local ScoringTracker = {
    -- Track scoring state
    current_score = 0,
    previous_score = 0,
    hand_score_start = 0,
    scoring_sequence_active = false,

    -- Components
    logger = nil,
    aggregator = nil,

    -- Statistics
    stats = {
        hands_tracked = 0,
        total_score_delta = 0,
        max_hand_score = 0,
        joker_triggers = 0,
    },
}

-- Initialize the scoring tracker
function ScoringTracker:init()
    self.logger = BalatroMCP.components.logger
    self.aggregator = BalatroMCP.components.aggregator

    self.logger:info("Scoring tracker initialized")

    -- Reset tracking state
    self:reset()
end

-- Reset tracking state
function ScoringTracker:reset()
    self.current_score = 0
    self.previous_score = 0
    self.hand_score_start = 0
    self.scoring_sequence_active = false
end

-- Start tracking a new hand evaluation
function ScoringTracker:start_hand_evaluation()
    if not G or not G.GAME then
        return
    end

    self.hand_score_start = G.GAME.chips or 0
    self.previous_score = self.hand_score_start
    self.scoring_sequence_active = true

    self.logger:debug("Started hand evaluation tracking", {
        starting_score = self.hand_score_start,
    })

    -- Send hand evaluation started event
    self.aggregator:add_event({
        type = "SCORING",
        subtype = "HAND_EVAL_START",
        source = "BalatroMCP",
        payload = {
            starting_score = self.hand_score_start,
            ante = G.GAME.round_resets and G.GAME.round_resets.ante or 0,
            round = G.GAME.round or 0,
            hand_number = G.GAME.current_round and G.GAME.current_round.hands_played or 0,
        },
    })
end

-- Track score change during evaluation
function ScoringTracker:track_score_change(new_score, context)
    if not self.scoring_sequence_active then
        return
    end

    local score_delta = new_score - self.previous_score

    if score_delta > 0 then
        self.logger:debug("Score increased", {
            previous = self.previous_score,
            new = new_score,
            delta = score_delta,
            context = context,
        })

        -- Send score update event
        self.aggregator:add_event({
            type = "SCORING",
            subtype = "SCORE_UPDATE",
            source = "BalatroMCP",
            payload = {
                previous_score = self.previous_score,
                new_score = new_score,
                delta = score_delta,
                total_hand_delta = new_score - self.hand_score_start,
                context = context or "unknown",
                timestamp = love.timer.getTime() * 1000,
            },
        })
    end

    self.previous_score = new_score
    self.current_score = new_score
end

-- Track individual joker trigger
function ScoringTracker:track_joker_trigger(joker_data, score_contribution)
    if not self.scoring_sequence_active then
        return
    end

    self.stats.joker_triggers = self.stats.joker_triggers + 1

    self.logger:debug("Joker triggered", {
        joker = joker_data.name or "Unknown",
        contribution = score_contribution,
    })

    -- Send joker trigger event
    self.aggregator:add_event({
        type = "SCORING",
        subtype = "JOKER_TRIGGER",
        source = "BalatroMCP",
        payload = {
            joker = {
                name = joker_data.name or "Unknown",
                id = joker_data.id,
                position = joker_data.position,
            },
            score_contribution = score_contribution,
            current_total = self.current_score,
            timestamp = love.timer.getTime() * 1000,
        },
    })
end

-- Complete hand evaluation tracking
function ScoringTracker:complete_hand_evaluation()
    if not self.scoring_sequence_active then
        return
    end

    local final_score = G.GAME and G.GAME.chips or self.current_score
    local total_hand_score = final_score - self.hand_score_start

    -- Update statistics
    self.stats.hands_tracked = self.stats.hands_tracked + 1
    self.stats.total_score_delta = self.stats.total_score_delta + total_hand_score
    if total_hand_score > self.stats.max_hand_score then
        self.stats.max_hand_score = total_hand_score
    end

    self.logger:info("Hand evaluation complete", {
        starting_score = self.hand_score_start,
        final_score = final_score,
        total_delta = total_hand_score,
        joker_triggers = self.stats.joker_triggers,
    })

    -- Send hand evaluation complete event
    self.aggregator:add_event({
        type = "SCORING",
        subtype = "HAND_EVAL_COMPLETE",
        source = "BalatroMCP",
        priority = "high", -- High priority to flush immediately
        payload = {
            starting_score = self.hand_score_start,
            final_score = final_score,
            total_delta = total_hand_score,
            joker_triggers = self.stats.joker_triggers,
            ante = G.GAME.round_resets and G.GAME.round_resets.ante or 0,
            round = G.GAME.round or 0,
            hand_number = G.GAME.current_round and G.GAME.current_round.hands_played or 0,
        },
    })

    -- Force flush to ensure scoring sequence is sent
    self.aggregator:flush()

    -- Reset for next hand
    self.scoring_sequence_active = false
    self.stats.joker_triggers = 0
end

-- Update the current score (called from game hooks)
function ScoringTracker:update_score(new_score)
    if not new_score or new_score == self.current_score then
        return
    end

    -- Only track if we're in an active scoring sequence
    if self.scoring_sequence_active then
        self:track_score_change(new_score, "score_update")
    else
        -- Just update our tracking
        self.current_score = new_score
        self.previous_score = new_score
    end
end

-- Get current statistics
function ScoringTracker:get_stats()
    return {
        hands_tracked = self.stats.hands_tracked,
        total_score_delta = self.stats.total_score_delta,
        max_hand_score = self.stats.max_hand_score,
        avg_hand_score = self.stats.hands_tracked > 0
                and (self.stats.total_score_delta / self.stats.hands_tracked)
            or 0,
        current_score = self.current_score,
        scoring_active = self.scoring_sequence_active,
    }
end

-- Track mult changes specifically
function ScoringTracker:track_mult_change(mult_before, mult_after, source)
    if not self.scoring_sequence_active then
        return
    end

    local mult_delta = mult_after - mult_before

    if mult_delta ~= 0 then
        self.logger:debug("Mult changed", {
            before = mult_before,
            after = mult_after,
            delta = mult_delta,
            source = source,
        })

        self.aggregator:add_event({
            type = "SCORING",
            subtype = "MULT_UPDATE",
            source = "BalatroMCP",
            payload = {
                mult_before = mult_before,
                mult_after = mult_after,
                delta = mult_delta,
                source = source or "unknown",
                timestamp = love.timer.getTime() * 1000,
            },
        })
    end
end

-- Track chip changes specifically
function ScoringTracker:track_chips_change(chips_before, chips_after, source)
    if not self.scoring_sequence_active then
        return
    end

    local chips_delta = chips_after - chips_before

    if chips_delta ~= 0 then
        self.logger:debug("Chips changed", {
            before = chips_before,
            after = chips_after,
            delta = chips_delta,
            source = source,
        })

        self.aggregator:add_event({
            type = "SCORING",
            subtype = "CHIPS_UPDATE",
            source = "BalatroMCP",
            payload = {
                chips_before = chips_before,
                chips_after = chips_after,
                delta = chips_delta,
                source = source or "unknown",
                timestamp = love.timer.getTime() * 1000,
            },
        })
    end
end

return ScoringTracker
