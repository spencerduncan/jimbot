# Claude LLM Integration Guide

This document provides specific guidance for Claude/LangChain integration within the JimBot LLM subsystem.

## Overview

The LLM subsystem provides strategic consultation for exploratory decisions and meta-analysis of unsuccessful runs. It operates under strict rate limits (100 requests/hour) and must achieve <5% consultation rate for cost optimization.

## Architecture Principles

### 1. Rate Limiting Strategy
- **Hard Limit**: 100 requests per hour
- **Soft Target**: <5% of all decisions require LLM consultation
- **Implementation**: Token bucket algorithm with hourly refresh
- **Fallback**: Use cached strategies when rate limited

### 2. Caching Architecture
```python
# Three-tier caching strategy
1. Exact Match Cache: Direct game state → strategy mapping
2. Similarity Cache: Find similar game states (cosine similarity > 0.85)
3. Pattern Cache: Abstract patterns (e.g., "flush build", "pair strategy")
```

### 3. Async Queue Pattern
```python
# Non-blocking integration pattern
async def get_strategy(self, game_state):
    # Check cache first
    if cached := await self.cache.get(game_state):
        return cached
    
    # Queue request if rate limit allows
    if self.rate_limiter.can_request():
        return await self.strategy_queue.put(game_state)
    
    # Fallback to heuristic
    return self.fallback_strategy(game_state)
```

## Prompt Engineering Guidelines

### 1. System Prompt Structure
```
You are a Balatro strategy advisor analyzing game states.
Focus on: synergies, risk assessment, and long-term value.
Provide: specific action, reasoning, confidence level.
Format: JSON response for parsing.
```

### 2. Context Optimization
- Include only relevant game state (current jokers, hand, shop)
- Compress historical data to key patterns
- Limit context to 2000 tokens max
- Use structured format for consistency

### 3. Response Format
```json
{
    "action": "buy_joker",
    "target": "Fibonacci",
    "reasoning": "Strong synergy with current Ace-heavy deck",
    "confidence": 0.85,
    "alternative": "skip_shop",
    "cache_key": "ace_deck_fibonacci_ante3"
}
```

## Strategic Consultation Patterns

### 1. High-Value Decisions (Request LLM)
- Boss blind selection with unknown effects
- Joker synergy evaluation with 3+ jokers
- Voucher purchases affecting core strategy
- Spectral card usage decisions

### 2. Low-Value Decisions (Use Cache/Heuristics)
- Standard card selection in hand
- Common joker purchases (e.g., +Mult jokers)
- Early ante decisions (antes 1-2)
- Obvious plays (e.g., play flush when held)

### 3. Meta-Analysis Triggers
- Run ends before ante 8
- Score below expectation by >50%
- Failed boss blind 3+ times
- Negative ROI on recent decisions

## Cost Optimization Strategies

### 1. Request Batching
```python
# Batch similar decisions within 100ms window
async def batch_decisions(self, decisions: List[GameState]):
    prompt = self.create_batch_prompt(decisions)
    response = await self.query_claude(prompt)
    return self.parse_batch_response(response)
```

### 2. Progressive Refinement
- Start with cached/heuristic strategies
- Only consult LLM on failure or uncertainty
- Update cache with successful strategies
- Decay old cache entries based on meta performance

### 3. Confidence Thresholds
```python
# Only request LLM if confidence below threshold
CONFIDENCE_THRESHOLDS = {
    "ante_1-3": 0.3,  # High threshold, rarely ask
    "ante_4-6": 0.5,  # Medium threshold
    "ante_7-8": 0.7,  # Low threshold, ask more often
    "endless": 0.6    # Balanced for long runs
}
```

## Implementation Checklist

### Week 4: Foundation
- [ ] Implement rate limiter with token bucket
- [ ] Create basic prompt templates
- [ ] Set up LangChain with Claude integration
- [ ] Implement exact match cache

### Week 5: Optimization
- [ ] Add similarity-based caching
- [ ] Implement request batching
- [ ] Create fallback strategy system
- [ ] Add confidence scoring

### Week 6: Intelligence
- [ ] Implement meta-analysis system
- [ ] Add pattern recognition cache
- [ ] Create strategy evolution tracking
- [ ] Optimize prompt engineering

### Week 7: Integration
- [ ] Connect with Ray for game states
- [ ] Integrate with Memgraph for context
- [ ] Add monitoring and metrics
- [ ] Performance optimization

## Monitoring Metrics

### Rate Limiting
- Requests per hour (target: <100)
- Request denial rate
- Cache hit rate (target: >95%)
- Fallback usage rate

### Decision Quality
- Win rate improvement with LLM
- Cost per decision
- Response latency (target: <500ms)
- Confidence accuracy correlation

### Cost Analysis
- $ per run
- $ per win
- ROI on LLM consultation
- Cost trend over time

## Error Handling

### Rate Limit Exceeded
1. Log warning with current usage
2. Return cached strategy
3. Queue for next hour if critical
4. Alert if pattern continues

### LLM Timeout/Error
1. Retry with exponential backoff (max 2 retries)
2. Fall back to heuristic strategy
3. Log error for analysis
4. Continue game without blocking

### Invalid Response
1. Validate JSON structure
2. Check action validity
3. Use default if invalid
4. Log for prompt improvement

## Security Considerations

- Never expose API keys in code
- Use environment variables for configuration
- Implement request signing if needed
- Monitor for unusual usage patterns
- Sanitize game state before sending

## Testing Strategy

### Unit Tests
- Rate limiter accuracy
- Cache operations
- Prompt generation
- Response parsing

### Integration Tests
- End-to-end decision flow
- Fallback mechanisms
- Queue processing
- Error recovery

### Performance Tests
- Latency under load
- Cache efficiency
- Memory usage
- Throughput limits