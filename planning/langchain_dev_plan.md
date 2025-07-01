# Claude Integration Development Plan

## Executive Summary

This plan outlines the development of the Claude integration layer for the Balatro Sequential Learning System, to be implemented during Weeks 4-7 of the project timeline. The integration will consume strategy requests from the Event Bus using an async queue pattern, provide strategic advice to the learning system, and implement aggressive cost optimization to operate within a 100 requests/hour rate limit while maintaining high-quality decision support.

The system will integrate with the central Resource Coordinator for API quota management and use the Event Bus for all communications, ensuring clean separation of concerns and scalability.

## Technical Architecture

### Event Bus Integration

The Claude integration operates as an async consumer of strategy requests:

```python
from jimbot.proto.events_pb2 import StrategyRequest, StrategyResponse
from jimbot.clients import EventBusClient, ResourceCoordinator
from langchain_anthropic import ChatAnthropic

class ClaudeStrategyAdvisor:
    def __init__(self):
        self.event_bus = EventBusClient()
        self.resource_coordinator = ResourceCoordinator()
        self.claude = ChatAnthropic(model="claude-3-7-sonnet")
        self.rate_limiter = TokenBucket(capacity=100, refill_rate=100/3600)
        
    async def start(self):
        # Subscribe to strategy request queue
        await self.event_bus.subscribe(
            topics=['strategy.request'],
            handler=self.handle_strategy_request,
            queue_mode=True  # Async queue processing
        )
        
    async def handle_strategy_request(self, event: Event):
        request = StrategyRequest()
        event.payload.Unpack(request)
        
        # Check rate limit via Resource Coordinator
        if await self.can_process_request():
            response = await self.get_strategic_advice(request)
        else:
            response = await self.get_cached_strategy(request)
            
        await self.publish_response(response)
```

### Cost Optimization Architecture

The system implements three-tier optimization to maximize value within the 100 requests/hour limit:

1. **Semantic Caching**: Redis-backed cache with vector similarity search (85-95% hit rate target)
2. **Request Prioritization**: Only consult Claude for low-confidence decisions (<70% confidence)
3. **Batch Analysis**: Aggregate post-game analysis into single requests

### Resource Coordination

```python
async def can_process_request(self) -> bool:
    grant = await self.resource_coordinator.request({
        'component': 'claude_advisor',
        'type': ResourceType.CLAUDE_API_TOKENS,
        'amount': 1,
        'priority': Priority.MEDIUM
    })
    return grant.approved
```

## Development Timeline (Weeks 4-7)

### Week 4: Foundation and Event Bus Integration

**Objective**: Establish core Claude integration with Event Bus

- Set up Python environment with LangChain 0.2.x and dependencies
- Implement Event Bus consumer for strategy requests
- Configure Claude client with proper timeout handling
- Create basic prompt templates for Balatro context
- Set up Redis for semantic caching (shared with Analytics)
- Integrate with Resource Coordinator for rate limiting
- Deliverables: Working async consumer processing strategy requests

### Week 5: Semantic Caching and Optimization

**Objective**: Implement cost optimization strategies

- Implement semantic caching with Redis vector search
- Configure embedding generation for cache keys
- Create cache warming strategies for common scenarios
- Implement request prioritization logic
- Add fallback strategies for rate limit scenarios
- Develop prompt compression techniques
- Deliverables: 85%+ cache hit rate, <100 API calls/hour

### Week 6: Advanced Strategy Analysis

**Objective**: Develop sophisticated game analysis capabilities

- Implement extended thinking mode for complex decisions
- Create structured reasoning templates
- Add post-game batch analysis
- Develop strategy extraction from game histories
- Implement confidence scoring for recommendations
- Create meta-strategy detection patterns
- Deliverables: High-quality strategic advice system

### Week 7: Production Hardening

**Objective**: Prepare for production deployment

- Implement comprehensive error handling
- Add circuit breakers for API failures
- Create monitoring and alerting
- Optimize response times (<5s target)
- Integration testing with all components
- Documentation and runbooks
- Deliverables: Production-ready Claude integration

## Implementation Details

### Semantic Caching Strategy

```python
class SemanticCache:
    def __init__(self, redis_client, embedding_model):
        self.redis = redis_client
        self.embedder = embedding_model
        self.similarity_threshold = 0.85
        
    async def get_or_compute(self, game_state: GameState) -> StrategyResponse:
        # Generate embedding for current state
        embedding = await self.embedder.embed(game_state.serialize())
        
        # Search for similar cached responses
        similar = await self.redis.vector_search(
            embedding, 
            threshold=self.similarity_threshold
        )
        
        if similar and similar.score > 0.95:
            # Direct cache hit
            return similar.response
        elif similar and similar.score > self.similarity_threshold:
            # Adapt similar response
            return await self.adapt_response(similar.response, game_state)
        else:
            # Cache miss - compute new response
            response = await self.compute_strategy(game_state)
            await self.cache_response(embedding, response)
            return response
```

### Prompt Engineering for Balatro

```python
STRATEGY_PROMPT = """You are an expert Balatro player analyzing a game state.

Current State:
- Ante: {ante}, Blind: {blind_type} ({chips_required} chips)
- Money: ${money}
- Jokers: {jokers}
- Hand: {hand_cards}
- Shop: {shop_items}

Previous Actions: {recent_decisions}

Provide strategic advice considering:
1. Immediate scoring needs vs long-term synergy building
2. Risk/reward of current joker combinations
3. Economic efficiency of shop purchases

Format your response as:
RECOMMENDED_ACTION: [specific action]
CONFIDENCE: [0.0-1.0]
REASONING: [brief explanation]
ALTERNATIVE: [fallback option if primary fails]
"""
```

### Rate Limiting and Fallbacks

```python
class RateLimitedAdvisor:
    def __init__(self, hourly_limit=100):
        self.token_bucket = TokenBucket(hourly_limit, refill_rate=hourly_limit/3600)
        self.fallback_strategies = self.load_cached_strategies()
        
    async def get_advice(self, request: StrategyRequest) -> StrategyResponse:
        if self.token_bucket.try_consume(1):
            # Use Claude API
            return await self.claude_strategy(request)
        else:
            # Use fallback
            return await self.fallback_strategy(request)
            
    async def fallback_strategy(self, request: StrategyRequest) -> StrategyResponse:
        # Try cache first
        cached = await self.semantic_cache.get(request)
        if cached:
            return cached
            
        # Use rule-based fallback
        return self.rule_based_strategy(request)
```

## Integration Patterns

### Knowledge Graph Integration

```python
async def enrich_with_knowledge(self, request: StrategyRequest):
    # Query Knowledge Graph for relevant patterns
    joker_synergies = await self.knowledge_graph.query("""
        query GetSynergies($jokers: [String!]) {
            jokerSynergies(jokerNames: $jokers) {
                joker1
                joker2
                strength
                winRate
            }
        }
    """, variables={"jokers": request.game_state.jokers})
    
    # Include in prompt context
    request.context.synergies = joker_synergies
    return request
```

### Batch Analysis for Post-Game Learning

```python
async def analyze_game_batch(self, game_histories: List[GameHistory]):
    # Aggregate multiple games for efficient analysis
    batch_prompt = self.create_batch_analysis_prompt(game_histories)
    
    # Single API call for multiple games
    analysis = await self.claude.analyze(batch_prompt, 
                                       extended_thinking=True)
    
    # Extract and store insights
    for insight in analysis.strategic_insights:
        await self.publish_knowledge_update(insight)
```

## Risk Mitigation

### API Rate Limit Management
- Token bucket algorithm with 100/hour capacity
- Automatic fallback to cached strategies
- Priority queue for critical decisions
- Circuit breaker pattern for API failures

### Cache Poisoning Prevention
- Version tagging for all cached entries
- Periodic validation against known good strategies
- Automatic expiry for low-confidence responses
- A/B testing of cached vs fresh responses

### Cost Control Measures
- Only consult Claude for decisions with <70% confidence
- Batch non-urgent requests
- Aggressive semantic caching (target 85%+ hit rate)
- Progressive complexity based on game state

## Performance Targets

- **Response Time**: <5s for strategy advice (including cache lookup)
- **Cache Hit Rate**: >85% for common game scenarios
- **API Usage**: <100 requests/hour sustained
- **Confidence Accuracy**: 90% correlation between confidence and outcome
- **Memory Usage**: <1GB including Redis shared allocation

## Success Criteria

1. **Cost Efficiency**: Operate within 100 requests/hour limit
2. **Decision Quality**: Provide valuable strategic insights
3. **Integration**: Seamless Event Bus communication
4. **Reliability**: 99.9% uptime with graceful degradation
5. **Learning**: Demonstrable improvement in advice quality over time

## Resource Requirements

### Development Approach
Single developer or small team with LLM and game AI experience.

### Technical Skills
- **Python**: Async programming, LangChain framework
- **LLM Integration**: Prompt engineering, caching strategies
- **Event-Driven Systems**: Message queue patterns
- **Game AI**: Understanding of strategic decision making

### Infrastructure
- Redis (shared with Analytics): Vector search capability
- Python 3.11+ environment
- Access to Claude API
- Development allocation of API tokens

## Key Deliverables

By Week 7:
- Async Event Bus consumer for strategy requests
- Semantic caching with 85%+ hit rate
- Rate-limited Claude integration
- Fallback strategy system
- Post-game batch analysis
- Integration with Knowledge Graph
- Production monitoring and alerts

This plan provides a practical approach to integrating Claude as a strategic advisor within the strict constraints of API limits and system architecture.