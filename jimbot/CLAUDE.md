# JimBot Root Directory

This directory contains all components of the JimBot sequential learning system for Balatro.

## Directory Structure

```
jimbot/
├── mcp/           # Model-Context-Protocol communication framework
├── memgraph/      # Knowledge graph components and MAGE modules
├── training/      # Ray RLlib training pipeline
├── llm/           # LangChain/Claude integration
├── analytics/     # QuestDB and EventStoreDB monitoring
├── infrastructure/# Shared utilities and event bus
├── tests/         # Unit, integration, and performance tests
├── deployment/    # Docker, Kubernetes, and CI/CD configs
├── docs/          # Architecture and API documentation
└── scripts/       # Utility and automation scripts
```

## Development Principles

1. **Sequential Thinking**: Take time to think through problems thoroughly before implementation
2. **Parallel Development**: Each component can be developed independently via clean interfaces
3. **Event-Driven Architecture**: All components communicate through the central Event Bus
4. **Resource Awareness**: Respect memory allocations (32GB total) and GPU coordination

## Quick Component Overview

- **MCP** (Weeks 1-3): Handles game state aggregation with <100ms latency
- **Memgraph** (Weeks 1-8): Stores strategies and synergies with <50ms query time
- **Training** (Weeks 2-8): Ray RLlib PPO implementation targeting >1000 games/hour
- **LLM** (Weeks 4-7): Claude consultation for <5% of decisions
- **Analytics** (Weeks 5-10): Real-time metrics and event persistence

## Integration Points

- Week 3: MCP ↔ Ray integration checkpoint
- Week 7: Memgraph ↔ Ray ↔ LangChain integration
- Week 10: Full system integration with monitoring

## Getting Started

Each subdirectory contains its own CLAUDE.md and README.md with specific instructions. Start with the component most relevant to your current task.

## Resource Allocation

- System/Buffer: 6GB
- Memgraph: 12GB (with 2GB safety margin)
- Ray/RLlib: 8GB
- Persistence Layer: 6GB
- Event Bus Infrastructure: Shared across components