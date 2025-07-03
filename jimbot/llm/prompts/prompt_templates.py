"""
Optimized prompt templates for Claude AI integration.

These prompts are carefully engineered for:
- Minimal token usage
- Consistent JSON responses
- High-quality strategic advice
- Efficient meta-analysis
"""

# System prompt establishing Claude's role and response format
SYSTEM_PROMPT = """You are an expert Balatro strategy advisor integrated into an AI system.

Your role:
1. Analyze game states and provide optimal strategic decisions
2. Focus on synergies, risk assessment, and long-term value
3. Always respond in valid JSON format
4. Be concise but include reasoning

Key principles:
- Prioritize joker synergies and deck composition
- Consider economic efficiency (cost vs benefit)
- Account for ante progression and scaling
- Evaluate risk vs reward for each decision

Response format requirements:
- Valid JSON only
- Include confidence scores (0-1)
- Provide alternative actions when relevant
- Generate cache keys for similar situations"""

# Main strategy consultation prompt
STRATEGY_PROMPT = """Analyze this Balatro game state and recommend the optimal action.

Game State:
{context}

Consider:
1. Current joker synergies
2. Shop opportunities vs saving money
3. Hand optimization for current blind
4. Long-term deck building strategy

Respond with JSON:
{{
    "action": "buy_joker|sell_joker|buy_card|use_card|skip|play_hand",
    "target": "specific item/card name or null",
    "reasoning": "2-3 sentence explanation",
    "confidence": 0.0-1.0,
    "alternative": "next best action or null",
    "cache_key": "pattern identifier for similar situations"
}}"""

# Meta-analysis prompt for failed runs
META_ANALYSIS_PROMPT = """Analyze this failed Balatro run and identify improvement opportunities.

Run History (last 10 states):
{context}

Identify:
1. Critical decision points that led to failure
2. Missed synergy opportunities
3. Economic mismanagement
4. Strategic patterns to avoid

Respond with JSON:
{{
    "failure_reason": "primary cause of run failure",
    "critical_mistakes": [
        {{
            "ante": number,
            "mistake": "description",
            "better_action": "what should have been done"
        }}
    ],
    "patterns_to_avoid": ["pattern1", "pattern2"],
    "strategic_insights": ["insight1", "insight2"],
    "improvement_priority": "what to focus on next run"
}}"""

# Batch decision prompt for multiple similar decisions
BATCH_DECISION_PROMPT = """Analyze multiple similar Balatro decisions efficiently.

Decisions to evaluate:
{decisions}

For each decision, provide:
1. Recommended action
2. Brief reasoning
3. Confidence score

Respond with JSON:
{{
    "decisions": [
        {{
            "index": 0,
            "action": "recommended action",
            "reasoning": "brief explanation",
            "confidence": 0.0-1.0
        }}
    ],
    "general_pattern": "common strategy across decisions"
}}"""

# Joker synergy evaluation prompt
JOKER_SYNERGY_PROMPT = """Evaluate joker synergy potential for this combination.

Current Jokers:
{current_jokers}

Potential Addition:
{new_joker}

Deck Composition:
{deck_info}

Respond with JSON:
{{
    "synergy_score": 0.0-1.0,
    "synergy_type": "multiplicative|additive|transformative|none",
    "key_interactions": ["interaction1", "interaction2"],
    "recommendation": "strong_buy|buy|skip|sell_other",
    "sell_candidate": "joker to sell if needed or null"
}}"""

# Boss blind strategy prompt
BOSS_BLIND_PROMPT = """Recommend strategy for upcoming boss blind.

Boss Effect:
{boss_effect}

Current State:
{game_state}

Available Resources:
{resources}

Respond with JSON:
{{
    "strategy": "specific approach to counter boss",
    "hand_priority": "type of hand to focus on",
    "resource_usage": ["consumables to use"],
    "backup_plan": "if primary strategy fails",
    "success_probability": 0.0-1.0
}}"""

# Voucher evaluation prompt
VOUCHER_PROMPT = """Evaluate voucher purchase decision.

Voucher:
{voucher_info}

Current State:
{game_state}

Economic Situation:
Money: {money}
Upcoming Blinds: {blind_info}

Respond with JSON:
{{
    "recommendation": "buy|skip|buy_later",
    "value_score": 0.0-1.0,
    "reasoning": "cost-benefit analysis",
    "timing_factor": "why now or why wait",
    "synergies": ["current synergies with build"]
}}"""

# Run planning prompt (for early game)
RUN_PLANNING_PROMPT = """Create strategic plan for this Balatro run start.

Starting Conditions:
{start_state}

Available Strategies:
1. Flush/Straight builds
2. Pair/High card builds  
3. Economy focus
4. Joker synergy rush

Respond with JSON:
{{
    "primary_strategy": "chosen approach",
    "early_priorities": ["priority1", "priority2"],
    "joker_targets": ["ideal jokers for strategy"],
    "economy_plan": "spending vs saving approach",
    "pivot_conditions": ["when to change strategy"]
}}"""

# Performance optimization prompt
OPTIMIZATION_PROMPT = """Identify performance optimizations for current build.

Current Build:
{build_info}

Recent Performance:
{performance_metrics}

Respond with JSON:
{{
    "bottlenecks": ["current limiting factors"],
    "optimization_actions": [
        {{
            "action": "specific change",
            "impact": "expected improvement",
            "priority": "high|medium|low"
        }}
    ],
    "target_score": "realistic score target",
    "time_estimate": "antes needed for optimization"
}}"""

# Compact prompts for common decisions (token optimization)

QUICK_SHOP_PROMPT = """Shop: {shop}
Money: {money}
Jokers: {jokers}
Action? (buy_joker NAME|buy_card NAME|skip)"""

QUICK_HAND_PROMPT = """Hand: {hand}
Target: {target}
Best play? (flush|straight|three_of_kind|pair|high_card)"""

QUICK_SELL_PROMPT = """Jokers: {jokers}
Need space. Sell which? (JOKER_NAME)"""


# Prompt selection helper
def get_prompt_for_decision(decision_type: str) -> str:
    """Get the appropriate prompt template for a decision type."""
    prompt_map = {
        "strategy": STRATEGY_PROMPT,
        "meta_analysis": META_ANALYSIS_PROMPT,
        "batch": BATCH_DECISION_PROMPT,
        "joker_synergy": JOKER_SYNERGY_PROMPT,
        "boss_blind": BOSS_BLIND_PROMPT,
        "voucher": VOUCHER_PROMPT,
        "run_planning": RUN_PLANNING_PROMPT,
        "optimization": OPTIMIZATION_PROMPT,
        "quick_shop": QUICK_SHOP_PROMPT,
        "quick_hand": QUICK_HAND_PROMPT,
        "quick_sell": QUICK_SELL_PROMPT,
    }

    return prompt_map.get(decision_type, STRATEGY_PROMPT)


# Token counting helper (approximate)
def estimate_prompt_tokens(prompt: str, context: dict) -> int:
    """Estimate token count for a filled prompt."""
    filled = prompt.format(**context)
    # Rough estimate: 1 token per 4 characters
    return len(filled) // 4
