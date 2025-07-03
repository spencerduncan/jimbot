# JimBot Style Guides

This directory contains comprehensive style guides for all languages and
technologies used in the JimBot project.

## Available Guides

### Core Languages

1. **[Python Style Guide](./python-style-guide.md)** - PEP 8 based, with Ray
   RLlib and async patterns
2. **[C++ Style Guide](./cpp-style-guide.md)** - High-performance computing
   focus for MAGE modules
3. **[JavaScript Style Guide](./javascript-style-guide.md)** - ES6+, WebSocket
   patterns, event-driven architecture
4. **[TypeScript Style Guide](./typescript-style-guide.md)** - Strict mode, type
   safety, generic patterns
5. **[Lua Style Guide](./lua-balatro-style-guide.md)** - Balatro mod development
   with SMODS framework

### Query & Data Languages

6. **[Cypher Style Guide](./cypher-style-guide.md)** - Memgraph queries,
   performance patterns
7. **[SQL Style Guide](./sql-style-guide.md)** - QuestDB time-series patterns,
   analytics
8. **[Protocol Buffers Style Guide](./protobuf-style-guide.md)** - Proto3,
   versioning, gRPC services

### Infrastructure

9. **[Docker/Compose Guide](./docker-compose-guide.md)** - Multi-service ML
   setup, GPU support

## Key Principles Across All Guides

- **Consistency** - Unified patterns across the entire codebase
- **Performance** - Optimized for JimBot's real-time requirements (<100ms
  latency)
- **Type Safety** - Strong typing in all applicable languages
- **Error Handling** - Graceful degradation and recovery
- **Documentation** - Clear, self-documenting code with examples
- **Security** - Best practices for API keys, data validation

## Quick Reference

| Language   | Formatter    | Linter       | Key Framework |
| ---------- | ------------ | ------------ | ------------- |
| Python     | Black        | mypy, flake8 | Ray RLlib     |
| C++        | clang-format | clang-tidy   | Memgraph MAGE |
| JavaScript | Prettier     | ESLint       | MCP/WebSocket |
| TypeScript | Prettier     | ESLint + tsc | Strict mode   |
| Lua        | -            | luacheck     | SMODS/Balatro |
| SQL        | -            | -            | QuestDB       |
| Cypher     | -            | -            | Memgraph      |
| Protobuf   | clang-format | buf          | gRPC          |

## Integration Points

Each style guide includes specific patterns for JimBot's architecture:

- Event aggregation (100ms batching)
- Memgraph knowledge graph queries (<50ms target)
- Ray RLlib training patterns
- Claude AI integration with rate limiting
- Balatro game state management

## Usage

1. Read the relevant style guide before contributing code
2. Configure your editor with the recommended formatters/linters
3. Run formatters before committing
4. Follow the examples and patterns in each guide
5. When in doubt, prioritize consistency with existing code
