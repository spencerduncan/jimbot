# JimBot LLM Integration

This module provides Claude AI integration for strategic consultation in Balatro
gameplay, with a focus on cost optimization and intelligent decision-making.

## Overview

The LLM subsystem serves two primary functions:

1. **Strategic Consultation**: Provides expert advice for complex game decisions
2. **Meta-Analysis**: Analyzes failed runs to improve future performance

## Key Features

- **Rate Limited**: 100 requests/hour hard limit
- **Cost Optimized**: <5% of decisions require LLM consultation
- **Non-Blocking**: Async queue pattern prevents game delays
- **Intelligent Caching**: Three-tier cache system for response reuse
- **Fallback Strategies**: Heuristic-based decisions when rate limited

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Game Engine                          │
│                  (via Event Bus)                        │
└────────────────────┬────────────────────────────────────┘
                     │ Game State
                     ▼
┌─────────────────────────────────────────────────────────┐
│                 Strategy Request                         │
│                    Processor                            │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────┐ │
│  │   Cache     │  │ Rate Limiter │  │  Confidence   │ │
│  │   Check     │  │   (100/hr)   │  │   Scorer      │ │
│  └─────────────┘  └──────────────┘  └───────────────┘ │
└─────────────────────┬────────────────────────────────────┘
                     │ If needed
                     ▼
┌─────────────────────────────────────────────────────────┐
│                  Claude AI                               │
│                (via LangChain)                          │
└─────────────────────────────────────────────────────────┘
```

## Quick Start

```python
from jimbot.llm import ClaudeAdvisor

# Initialize with rate limiting
advisor = ClaudeAdvisor(
    api_key=os.getenv("ANTHROPIC_API_KEY"),
    requests_per_hour=100,
    cache_size=10000
)

# Get strategic advice
game_state = GameState(...)
strategy = await advisor.get_strategy(game_state)

# Perform meta-analysis
failed_run = GameHistory(...)
insights = await advisor.analyze_failure(failed_run)
```

## Cost Optimization Strategies

### 1. Intelligent Request Filtering

Only consult Claude for high-value decisions:

- Complex joker synergies (3+ jokers)
- Unknown boss blind effects
- Critical voucher decisions
- Spectral card usage

### 2. Advanced Caching System

Three-tier cache hierarchy:

1. **Exact Match**: Direct game state mapping
2. **Similarity**: Cosine similarity > 0.85
3. **Pattern**: Abstract strategy patterns

### 3. Confidence-Based Consultation

Dynamic thresholds based on game stage:

- Early Game (Antes 1-3): 30% confidence required
- Mid Game (Antes 4-6): 50% confidence required
- Late Game (Antes 7-8): 70% confidence required

### 4. Request Batching

Batch similar decisions within 100ms windows to reduce API calls.

## Fallback Strategies

When rate limited or experiencing errors:

1. **Cached Strategies**: Use previously successful strategies
2. **Heuristic Rules**: Apply rule-based decision making
3. **Conservative Play**: Default to safe, proven strategies
4. **Learn Offline**: Queue decisions for later analysis

## Module Structure

```
llm/
├── __init__.py           # Package initialization
├── CLAUDE.md            # Detailed Claude-specific guidance
├── README.md            # This file
├── strategies/          # Strategy implementations
│   ├── __init__.py
│   └── ...
├── prompts/            # Prompt templates and engineering
│   ├── __init__.py
│   └── prompt_templates.py
├── cache/              # Caching implementations
│   ├── __init__.py
│   └── strategy_cache.py
├── rate_limiting/      # Rate limiting logic
│   ├── __init__.py
│   └── rate_limiter.py
├── interfaces/         # External interfaces
│   ├── __init__.py
│   └── ...
└── claude_advisor.py   # Main advisor implementation
```

## Configuration

Environment variables:

```bash
ANTHROPIC_API_KEY=your_api_key_here
CLAUDE_MODEL=claude-3-opus-20240229
LLM_REQUESTS_PER_HOUR=100
LLM_CACHE_SIZE=10000
LLM_CONFIDENCE_THRESHOLD=0.5
```

## Monitoring

Key metrics tracked:

- Requests per hour
- Cache hit rate (target: >95%)
- Decision consultation rate (target: <5%)
- Cost per run
- Strategy success rate

## Development Timeline

- **Week 4**: Basic integration with rate limiting
- **Week 5**: Advanced caching and optimization
- **Week 6**: Meta-analysis implementation
- **Week 7**: Full integration with game system

## Testing

```bash
# Run unit tests
pytest tests/unit/llm/

# Run integration tests
pytest tests/integration/llm/

# Run cost analysis
python -m jimbot.llm.analyze_costs
```

## Best Practices

1. **Always Check Cache First**: Reduce unnecessary API calls
2. **Use Confidence Scores**: Only consult when uncertain
3. **Batch When Possible**: Group similar decisions
4. **Monitor Costs**: Track spending and optimize
5. **Fail Gracefully**: Never block gameplay on LLM errors

## Troubleshooting

### High API Costs

- Check consultation rate (should be <5%)
- Verify cache is working properly
- Review confidence thresholds
- Analyze decision patterns

### Rate Limit Errors

- Check hourly request count
- Verify rate limiter configuration
- Ensure proper request distribution
- Consider increasing cache size

### Slow Response Times

- Check network latency
- Verify async implementation
- Review prompt size
- Consider request batching

## Contributing

When adding new features:

1. Maintain <5% consultation target
2. Add comprehensive caching
3. Include fallback strategies
4. Document cost implications
5. Add monitoring metrics
