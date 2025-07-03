# JimBot - Sequential Learning System for Balatro

JimBot is an AI system that masters Balatro through a combination of knowledge
graphs, reinforcement learning, and strategic LLM consultation. The system is
designed to run on a single workstation with 32GB RAM and RTX 3090 GPU.

## System Overview

JimBot combines five major components to create a comprehensive learning system:

1. **MCP Server**: Real-time game state communication
2. **Memgraph Knowledge Base**: Strategic knowledge storage
3. **Ray RLlib Training**: Reinforcement learning pipeline
4. **Claude AI Integration**: Strategic consultation
5. **Analytics Platform**: Performance monitoring and replay

## Quick Start

```bash
# 1. Set up Python environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt

# 2. Start infrastructure services
docker-compose up -d

# 3. Initialize knowledge graph
python -m jimbot.memgraph.init

# 4. Start MCP server
python -m jimbot.mcp.server

# 5. Launch training pipeline
python -m jimbot.training.run
```

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  BalatroMCP │────▶│  MCP Server  │────▶│  Event Bus  │
└─────────────┘     └──────────────┘     └──────┬──────┘
                                                 │
                    ┌────────────────────────────┼────────────────────────────┐
                    │                            │                            │
              ┌─────▼──────┐            ┌───────▼────────┐            ┌──────▼──────┐
              │  Memgraph  │            │   Ray RLlib    │            │  Analytics  │
              │ Knowledge  │◀──────────▶│   Training     │            │  Platform   │
              └────────────┘            └───────┬────────┘            └─────────────┘
                                                │
                                        ┌───────▼────────┐
                                        │  Claude LLM    │
                                        │  Integration   │
                                        └────────────────┘
```

## Development Timeline

The project follows a 10-week development timeline with parallel workstreams:

- **Weeks 1-3**: MCP framework and event aggregation
- **Weeks 1-8**: Memgraph schema and query optimization
- **Weeks 2-8**: Ray RLlib training pipeline
- **Weeks 4-7**: Claude AI integration
- **Weeks 5-10**: Analytics and monitoring

## Performance Targets

- **MCP**: <100ms event aggregation latency
- **Memgraph**: <50ms query response time
- **Ray**: >1000 games/hour training throughput
- **Claude**: <5% of decisions require consultation

## Documentation

- `/docs/architecture/`: System design documents
- `/docs/api/`: Component API specifications
- Each component directory contains specific CLAUDE.md and README.md

## Testing

```bash
# Run all tests
pytest

# Component-specific tests
pytest tests/unit/mcp/
pytest tests/integration/
pytest tests/performance/ --benchmark
```

## Contributing

See CONTRIBUTING.md for development guidelines and code standards.

## License

[License information]
