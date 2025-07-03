# JimBot

[![CI Health](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/spencerduncan/jimbot/main/.github/badges/ci-health.json)](https://github.com/spencerduncan/jimbot/actions)
[![Main CI](https://github.com/spencerduncan/jimbot/workflows/Main%20CI%2FCD%20Pipeline/badge.svg)](https://github.com/spencerduncan/jimbot/actions/workflows/main-ci.yml)
[![Code Quality](https://github.com/spencerduncan/jimbot/workflows/Code%20Quality/badge.svg)](https://github.com/spencerduncan/jimbot/actions/workflows/code-quality.yml)
[![Lua CI](https://github.com/spencerduncan/jimbot/workflows/Lua%20CI/badge.svg)](https://github.com/spencerduncan/jimbot/actions/workflows/lua-ci.yml)

A sequential learning system designed to master the card game Balatro by combining knowledge graphs, reinforcement learning, and Claude AI integration.

## System Architecture

JimBot runs on a single workstation with 32GB RAM and RTX 3090 GPU, featuring:

- **Memgraph (Knowledge Graph)** - 12GB RAM for game schema and strategies
- **Ray RLlib (Learning)** - 8GB RAM for PPO algorithm and model training  
- **Claude AI Integration** - Strategy consultation with cost optimization
- **MCP Communication** - Event aggregation from BalatroMCP mod
- **Persistence Layer** - QuestDB + EventStoreDB for metrics and histories

## Quick Start

1. Clone the repository
2. Set up Python environment: `python -m venv venv && source venv/bin/activate`
3. Start Docker services: `docker-compose up -d`
4. Configure MCP connection to BalatroMCP mod
5. Run training pipeline: `python -m jimbot.training.run`

## Development

- **CI Status**: Monitor build health with the CI Health badge above
- **Documentation**: See `docs/` for comprehensive guides
- **Testing**: Run `pytest tests/` for unit and integration tests
- **Code Quality**: Automated quality checks on all PRs

## Performance Targets

- MCP: <100ms event aggregation latency
- Memgraph: <50ms query response time  
- Ray: >1000 games/hour training throughput
- Claude: <5% of decisions require LLM consultation

For detailed setup and development information, see [CLAUDE.md](CLAUDE.md).