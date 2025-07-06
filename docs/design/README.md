# JimBot Planning Documents

This directory contains all planning and architecture documents for the JimBot
project, including the Rust migration strategy.

## Document Index

### Core Planning Documents

1. **[top_level_plan.md](top_level_plan.md)** - Original high-level system
   architecture
2. **[interface_specification.md](interface_specification.md)** - Component
   interfaces and Protocol Buffer schemas (Updated for Rust)
3. **[timeline_reconciliation.md](timeline_reconciliation.md)** - Unified
   10-week development timeline

### Rust Migration Documents

4. **[rust_migration_plan.md](rust_migration_plan.md)** - Comprehensive Rust
   migration strategy
5. **[rust_migration_summary.md](rust_migration_summary.md)** - Executive
   summary of Rust migration
6. **[github_issues_plan.md](github_issues_plan.md)** - Original 20 GitHub
   issues plan (pre-existing issues)
7. **[github_issues_reconciliation.md](github_issues_reconciliation.md)** -
   Analysis of 51 existing issues vs Rust plan
8. **[github_issues_action_plan.md](github_issues_action_plan.md)** - Actionable
   steps to align issues with Rust migration

### Component Development Plans

9. **[mcp_dev_plan.md](mcp_dev_plan.md)** - MCP Communication Framework (Note:
   BalatroMCP already implemented)
10. **[knowledge_graph_dev_plan.md](knowledge_graph_dev_plan.md)** - Memgraph
    knowledge graph implementation
11. **[ray_rllib_dev_plan.md](ray_rllib_dev_plan.md)** - Ray RLlib learning
    orchestration
12. **[langchain_dev_plan.md](langchain_dev_plan.md)** - Claude/LangChain
    integration
13. **[analylitcs_dev_plan.md](analylitcs_dev_plan.md)** - Analytics and
    persistence layer (Migrating to Rust)
14. **[headless_dev_plan.md](headless_dev_plan.md)** - Headless Balatro
    implementation guide

## Current Status

### Implemented

- ✅ BalatroMCP Lua mod (fully functional)
- ✅ Game state extraction
- ✅ REST API event publishing
- ✅ Python test server

### GitHub Issues Status

- **Existing Issues**: 51 open issues (created before Rust migration)
- **Missing Issues**: Event Bus implementation, Resource Coordinator, Protocol
  Buffers, CI/CD
- **Issues Needing Updates**: Analytics (#8), MAGE (#31), and related issues
- **Action Required**: See
  [github_issues_action_plan.md](github_issues_action_plan.md)

### Planned (Rust Components)

- 🔄 Event Bus (replacing Python test server) - **Issue #52 to be created**
- 📋 Analytics Component - **Update issue #8**
- 📋 Resource Coordinator - **Issue #53 to be created**
- 📋 MAGE Modules - **Update issue #31**

### Planned (Python Components)

- 📋 Ray RLlib
- 📋 Claude/LangChain
- 📋 Memgraph integration

## Quick Links

- **Start Here**: [rust_migration_summary.md](rust_migration_summary.md)
- **Implementation Tasks**: [github_issues_plan.md](github_issues_plan.md)
- **Architecture**: [interface_specification.md](interface_specification.md)
- **Timeline**: [timeline_reconciliation.md](timeline_reconciliation.md)

## Key Decisions

1. **Rust for Infrastructure**: Event Bus, Analytics, Resource Coordinator, MAGE
   modules
2. **Keep Existing Languages**: Lua (BalatroMCP), Python (Ray, Claude)
3. **Protocol Buffers**: For cross-language communication
4. **Event-Driven Architecture**: Central Event Bus pattern

## Development Approach

- Single developer or small team
- 10-week timeline
- Parallel component development
- Progressive integration milestones (Weeks 3, 7, 10)
- CI/CD from the start

## Next Steps

1. Review [rust_migration_summary.md](rust_migration_summary.md)
2. Set up development environment
3. Start with Issue #1: Rust Event Bus
4. Follow sprint plan in [github_issues_plan.md](github_issues_plan.md)
