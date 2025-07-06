# GitHub Issues Action Plan - Rust Migration

## Executive Summary

After reviewing all 51 existing GitHub issues against the Rust migration plan,
this document provides a clear action plan for aligning the project's issue
tracker with the new architecture.

## Immediate Actions (Do First)

### 1. Create Critical Missing Issues

Run these commands to create the missing infrastructure issues:

```bash
# Issue #52: Event Bus Implementation
gh issue create \
  --title "[Infrastructure]: Implement Rust Event Bus with REST API Compatibility" \
  --body "## Description
Implement production-ready Event Bus in Rust to replace Python test server and serve as central message router for all JimBot components.

## Context
- BalatroMCP mod already implemented and sending REST API events
- Must maintain backward compatibility with existing REST endpoints
- Will serve as foundation for all component communication

## Acceptance Criteria
- [ ] REST API endpoints compatible with BalatroMCP
  - [ ] POST /api/v1/events (single event)
  - [ ] POST /api/v1/events/batch (batch events)
- [ ] JSON to Protocol Buffer conversion
- [ ] gRPC service for other components
- [ ] Topic-based routing
- [ ] Docker deployment ready
- [ ] Health check endpoints
- [ ] Performance: 10,000+ events/second

## Technical Requirements
- Language: Rust
- Frameworks: Axum (REST), Tonic (gRPC)
- Deployment: Docker container

## Dependencies
- Blocks: Issues #7, #9, #17 (Event Bus consumers)" \
  --label "infrastructure,rust,critical,P0"

# Issue #53: Resource Coordinator Implementation
gh issue create \
  --title "[Infrastructure]: Implement Resource Coordinator in Rust" \
  --body "## Description
Implement Resource Coordinator service in Rust for managing GPU, memory, and API quotas across all JimBot components.

## Acceptance Criteria
- [ ] gRPC service interface
- [ ] GPU time slice management
- [ ] Memory allocation tracking (32GB total)
- [ ] Claude API rate limiting (100/hour)
- [ ] Request prioritization (HIGH, MEDIUM, LOW)
- [ ] Prometheus metrics export
- [ ] Docker deployment
- [ ] <1ms response time

## Technical Requirements
- Language: Rust
- Framework: Tonic (gRPC)
- Monitoring: Prometheus metrics

## Dependencies
- Blocks: Issue #13 (Resource Coordinator Integration)" \
  --label "infrastructure,rust,critical,P0"

# Issue #54: Protocol Buffer Schema Definitions
gh issue create \
  --title "[Infrastructure]: Define Protocol Buffer Schemas for All Events" \
  --body "## Description
Create comprehensive Protocol Buffer schemas for all event types, maintaining compatibility with existing BalatroMCP JSON format.

## Acceptance Criteria
- [ ] Base event structure (Event, EventType)
- [ ] Game state events (GameStateEvent)
- [ ] Learning decisions (LearningDecisionRequest/Response)
- [ ] Strategy requests (StrategyRequest/Response)
- [ ] Knowledge updates (KnowledgeUpdate)
- [ ] Metrics (Metric)
- [ ] JSON compatibility layer
- [ ] Version management strategy
- [ ] Code generation setup (Rust, Python, TypeScript)

## Technical Requirements
- Protocol Buffers v3
- Backward compatibility with JSON
- Generated code packages

## Dependencies
- Blocks: Issue #52 (Event Bus), all consumers" \
  --label "infrastructure,protobuf,critical,P0"

# Issue #55: Rust CI/CD Pipeline
gh issue create \
  --title "[DevOps]: Setup CI/CD Pipeline for Rust Components" \
  --body "## Description
Implement GitHub Actions workflow for automated build, test, and deployment of Rust components.

## Acceptance Criteria
- [ ] GitHub Actions workflow for Rust
- [ ] Automated testing on PR
- [ ] Code coverage with tarpaulin
- [ ] Cargo fmt and clippy checks
- [ ] Docker image building and pushing
- [ ] Multi-platform builds (linux/amd64, linux/arm64)
- [ ] Semantic versioning
- [ ] Release automation

## Technical Requirements
- GitHub Actions
- Docker Hub or GitHub Container Registry
- Coverage reporting to Codecov
- Rust stable and nightly testing

## Dependencies
- Required for all Rust components" \
  --label "devops,rust,infrastructure,P1"

# Issue #56: Docker Compose Development Environment
gh issue create \
  --title "[DevOps]: Complete Docker Compose Setup for Development" \
  --body "## Description
Create comprehensive Docker Compose configuration for local development with all services.

## Acceptance Criteria
- [ ] All services defined (Event Bus, Memgraph, QuestDB, EventStoreDB, etc.)
- [ ] Proper networking configuration
- [ ] Volume mounts for development
- [ ] Environment variable management
- [ ] Health checks for all services
- [ ] Quick start script
- [ ] Development vs production profiles

## Services to Include
- Event Bus (Rust)
- Resource Coordinator (Rust)
- Memgraph (10GB)
- QuestDB (3GB)
- EventStoreDB (2GB)
- Redis (shared cache)
- Grafana
- Prometheus

## Dependencies
- Requires Event Bus and Resource Coordinator images" \
  --label "devops,infrastructure,P1"
```

### 2. Update Existing Issues

Add comments to these issues explaining the Rust migration:

```bash
# Update Analytics Epic
gh issue comment 8 --body "## Rust Migration Update

The Analytics component will be implemented in Rust for improved performance:
- High-throughput event ingestion (target: 10,000+ events/sec)
- Native Protocol Buffer support
- Zero-copy deserialization
- Better memory efficiency

All child issues should be updated to reflect Rust implementation where applicable."

# Update MAGE Algorithms Issue
gh issue comment 31 --body "## Language Change: Python → Rust

Per the Rust migration plan, MAGE modules will be implemented in Rust instead of Python:
- Better performance (2-5x faster)
- Memory safety
- Official Rust support in MAGE

Example implementation:
\`\`\`rust
use memgraph_rust::*;

#[query_module]
mod balatro_algorithms {
    #[read_procedure]
    fn detect_joker_synergies(
        ctx: &Context,
        min_occurrences: i64,
        min_win_rate: f64,
    ) -> Result<RecordStream> {
        // Rust implementation
    }
}
\`\`\`"

# Update Analytics Consumer Issue
gh issue comment 17 --body "## Implementation Language: Rust

This Event Bus consumer will be implemented in Rust as part of the Analytics component:
- Using tokio for async processing
- Protocol Buffer deserialization with prost
- High-performance time-series ingestion"
```

### 3. Create Issue Labels

```bash
# Create Rust label if it doesn't exist
gh label create rust --description "Rust implementation" --color 0052CC

# Create priority labels if needed
gh label create P0 --description "Critical priority" --color FF0000
gh label create P1 --description "High priority" --color FF6600
gh label create P2 --description "Medium priority" --color FFAA00
gh label create P3 --description "Low priority" --color 33AA33
```

## Week 1 Actions

### Update Issue Dependencies

After creating new issues, update dependencies:

```bash
# Link Event Bus to consumers
gh issue edit 7 --add-label "blocked" --body-file - << EOF
[Current body content]

## Dependencies Update
- **Now blocked by**: Issue #52 (Event Bus Implementation)
EOF

# Similar updates for issues #9, #17
```

### Create Development Guides

```bash
# Issue #57: Rust Development Guide
gh issue create \
  --title "[Documentation]: Rust Development Environment Setup Guide" \
  --body "## Description
Create comprehensive guide for Rust development environment setup.

## Contents
- [ ] Rust toolchain installation (rustup)
- [ ] VS Code configuration with rust-analyzer
- [ ] Debugging setup (CodeLLDB)
- [ ] Performance profiling tools (perf, flamegraph)
- [ ] Common development workflows
- [ ] Testing best practices
- [ ] Benchmarking setup

## Target Audience
- New developers joining the project
- Existing developers new to Rust" \
  --label "documentation,rust,P2"
```

## Sprint Planning Updates

### Sprint 1 (Current)

1. Create all missing infrastructure issues ✓
2. Update existing issues with Rust notes
3. Set up basic Rust development environment
4. Begin Event Bus implementation

### Sprint 2

1. Complete Event Bus REST API
2. Implement Protocol Buffers
3. Start Resource Coordinator
4. Set up CI/CD pipeline

### Sprint 3

1. Complete Resource Coordinator
2. Add Event Bus gRPC interface
3. Begin Analytics component
4. Docker Compose setup

## Tracking Progress

### New Dashboard View

Create a GitHub Project board with these columns:

- **Rust Infrastructure** (new issues)
- **Needs Rust Update** (existing issues)
- **In Progress**
- **Review**
- **Done**

### Queries for Tracking

```bash
# All Rust issues
gh issue list --label rust

# Critical infrastructure
gh issue list --label "rust,P0"

# Issues needing updates
gh issue list --search "in:body Python implementation"
```

## Communication Template

For team communication about the changes:

```markdown
## Rust Migration Update

We're updating our architecture to use Rust for performance-critical components:

**What's Changing:**

- Event Bus: New Rust implementation (Issue #52)
- Analytics: Moving from TypeScript to Rust
- MAGE Modules: Moving from Python to Rust
- Resource Coordinator: New Rust service (Issue #53)

**What's NOT Changing:**

- BalatroMCP remains in Lua
- Ray RLlib remains in Python
- Claude/LangChain remains in Python
- All APIs and interfaces remain compatible

**Benefits:**

- 5-10x performance improvement
- Better resource utilization
- Type safety across components
- Lower operational costs

See planning/rust_migration_summary.md for details.
```

## Success Metrics

Track these metrics weekly:

- New infrastructure issues created: 5/5 ✓
- Existing issues updated: 0/10 (in progress)
- Rust components started: 0/4
- CI/CD pipeline ready: No
- Docker Compose ready: No

## Next Steps Checklist

- [ ] Run issue creation commands above
- [ ] Add update comments to affected issues
- [ ] Create missing labels
- [ ] Set up GitHub Project board
- [ ] Share communication with team
- [ ] Begin Event Bus implementation (Issue #52)

## References

- Full issue analysis: `planning/github_issues_reconciliation.md`
- Rust migration plan: `planning/rust_migration_plan.md`
- Original GitHub issues: `planning/github_issues_plan.md`
