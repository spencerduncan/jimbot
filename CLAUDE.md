# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with
code in this repository.

## Project Overview

JimBot is a sequential learning system designed to master the card game Balatro
by combining knowledge graphs, reinforcement learning, and Claude AI
integration. The system runs on a single workstation with 32GB RAM and RTX 3090
GPU.

## System Architecture

### Core Components

1. **Memgraph (Knowledge Graph) - 12GB RAM**
   - Stores game schema, strategies, and synergies
   - Custom algorithms for joker/deck analysis
   - MAGE modules in C++ for performance

2. **Ray RLlib (Learning Orchestration) - 8GB RAM**
   - PPO algorithm for sequential decision making
   - Checkpoint management and model persistence
   - Integration with Memgraph for memory queries

3. **Claude via LangChain (LLM Integration)**
   - Strategy consultation for exploratory decisions
   - Meta-analysis of unsuccessful runs
   - Cost-optimized with 100 requests/hour limit

4. **MCP (Communication Framework)**
   - Event aggregation from BalatroMCP mod
   - 100ms batch processing for game state updates
   - WebSocket communication with game client

5. **QuestDB + EventStoreDB (Persistence) - 6GB RAM**
   - QuestDB: Real-time performance metrics
   - EventStoreDB: Complete game histories

## Development Commands

### Environment Setup

```bash
# Create Python virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

# Install core dependencies (when requirements.txt is created)
pip install -r requirements.txt
```

### Docker Services

```bash
# Start Memgraph
docker run -p 7687:7687 -p 3000:3000 -v memgraph_data:/var/lib/memgraph memgraph/memgraph-platform

# Start QuestDB
docker run -p 9000:9000 -p 8812:8812 -v questdb_data:/var/lib/questdb questdb/questdb

# Start EventStoreDB
docker run -p 2113:2113 -p 1113:1113 eventstore/eventstore --insecure
```

### Development Workflow

```bash
# Run MCP server (once implemented)
python -m jimbot.mcp.server

# Run Ray head node
ray start --head --port=6379

# Run training pipeline
python -m jimbot.training.run

# Run tests
pytest tests/
pytest tests/unit/ -v  # Unit tests only
pytest tests/integration/ -v  # Integration tests only
```

## Key Development Patterns

### MCP Event Aggregation

```python
# jimbot/mcp/aggregator.py
class EventAggregator:
    def __init__(self, batch_window_ms=100):
        self.batch_window = batch_window_ms
        self.event_queue = asyncio.Queue()

    async def process_batch(self):
        events = []
        deadline = time.time() + (self.batch_window / 1000)
        while time.time() < deadline:
            try:
                event = await asyncio.wait_for(
                    self.event_queue.get(),
                    timeout=deadline - time.time()
                )
                events.append(event)
            except asyncio.TimeoutError:
                break
        return self.aggregate_events(events)
```

### Memgraph Schema

```cypher
// Core game entities
CREATE (:Joker {name: STRING, rarity: STRING, cost: INTEGER});
CREATE (:Card {suit: STRING, rank: STRING, enhancement: STRING});
CREATE (:Synergy {type: STRING, multiplier: FLOAT});

// Relationships
CREATE (j1:Joker)-[:SYNERGIZES_WITH {strength: FLOAT}]->(j2:Joker);
CREATE (j:Joker)-[:REQUIRES]->(c:Card);
```

### Claude Integration Pattern

```python
# jimbot/llm/claude_strategy.py
class ClaudeStrategyAdvisor:
    def __init__(self, hourly_limit=100):
        self.rate_limiter = RateLimiter(hourly_limit)

    async def get_strategic_advice(self, game_state, knowledge_graph):
        if not self.rate_limiter.can_request():
            return self.get_cached_strategy(game_state)

        context = self.build_context(game_state, knowledge_graph)
        return await self.query_claude(context)
```

### Ray RLlib Configuration

```python
# jimbot/training/config.py
PPO_CONFIG = {
    "framework": "torch",
    "num_workers": 2,  # Limited by 8GB allocation
    "rollout_fragment_length": 200,
    "train_batch_size": 4000,
    "sgd_minibatch_size": 128,
    "num_sgd_iter": 30,
    "model": {
        "custom_model": "BalatroNet",
        "custom_model_config": {
            "memgraph_embedding_dim": 128,
            "hidden_layers": [512, 512]
        }
    }
}
```

## Important Integration Points

- **Week 3**: MCP ↔ Ray integration checkpoint
- **Week 7**: Memgraph ↔ Ray ↔ LangChain integration
- **Week 10**: Full system integration with monitoring

## Performance Targets

- MCP: <100ms event aggregation latency
- Memgraph: <50ms query response time
- Ray: >1000 games/hour training throughput
- Claude: <5% of decisions require LLM consultation

## Testing Strategy

```bash
# Unit tests for individual components
pytest tests/unit/mcp/ -v
pytest tests/unit/memgraph/ -v
pytest tests/unit/ray/ -v

# Integration tests
pytest tests/integration/ -v --slow

# Performance benchmarks
pytest tests/performance/ -v --benchmark
```

## Development Timeline

The project follows a 10-week timeline with 5 parallel development streams:

1. **MCP Development** (Weeks 1-3): Communication framework and event
   aggregation
2. **Memgraph Development** (Weeks 1-8): Knowledge graph and query optimization
3. **Ray RLlib Development** (Weeks 2-8): RL training pipeline
4. **LangChain Integration** (Weeks 4-7): Claude AI strategy advisor
5. **Monitoring & Analytics** (Weeks 5-10): QuestDB metrics and EventStoreDB
   persistence

## Memory Allocation Strategy

Total: 32GB RAM

- System/Buffer: 6GB
- Memgraph: 12GB (with 2GB safety margin)
- Ray/RLlib: 8GB
- Persistence Layer: 6GB

## Risk Mitigation

1. **Memory Pressure**: Use Ray's object spilling if needed
2. **Integration Complexity**: Implement circuit breakers between components
3. **LLM Costs**: Aggressive caching and fallback strategies

## Quick Start

1. Clone the repository
2. Set up Python environment
3. Start Docker services (Memgraph, QuestDB, EventStoreDB)
4. Configure MCP connection to BalatroMCP mod
5. Run initial training pipeline with synthetic data

## Planning Status

All planning documents have been updated to address initial inconsistencies:

### Resolved Issues

✓ **Timeline Alignment**: All components now follow unified 10-week timeline
with Week 0 foundation ✓ **Memory Allocation**: Fixed conflicts, total 32GB
properly allocated with Event Bus infrastructure ✓ **Interface Specification**:
Created comprehensive `interface_specification.md` with Protocol Buffers ✓
**Event Schema**: Defined canonical schemas in interface specification ✓
**Resource Coordination**: Added Resource Coordinator for GPU/API management ✓
**Headless Integration**: Updated headless plan with Week 1-2 timeline

### Key Architecture Decisions

- **Event Bus Pattern**: All components communicate via central Event Bus
- **Protocol Buffers**: Language-agnostic serialization for all events
- **Async Patterns**: Claude uses async queue, others use gRPC/REST
- **Shared Resources**: Redis shared between Claude/Analytics, GPU coordinated

### Development Approach

- Single developer or small team per component
- Parallel development enabled by clean interfaces
- Progressive integration at Weeks 3, 7, and 10
- Mock implementations for early testing

See `planning/interface_specification.md` for complete technical details and
`planning/timeline_reconciliation.md` for unified timeline.
