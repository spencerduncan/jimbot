# Timeline and Resource Reconciliation

## Overall Project Timeline (10 Weeks)

### Week 0: Foundation and Interface Specification
- **All Teams**: Define Protocol Buffer schemas
- **Infrastructure**: Set up Event Bus and Resource Coordinator
- **Environment**: Create Docker Compose development environment
- **Deliverable**: Working Event Bus with defined interfaces

### Weeks 1-3: MCP Development (Critical Path)
- **Week 1**: Core MCP implementation and BalatroMCP integration
- **Week 2**: Complex scoring capture and optimization
- **Week 3**: System integration and production readiness
- **Dependencies**: Provides events for all other components

### Weeks 1-8: Knowledge Graph Development
- **Weeks 1-2**: Foundation, Event Bus integration, schema
- **Weeks 3-4**: GraphQL API and analytics algorithms
- **Weeks 5-6**: Ray integration and advanced analytics
- **Weeks 7-8**: Optimization and production readiness
- **Dependencies**: Consumes MCP events, provides queries to Ray/Claude

### Weeks 2-8: Ray RLlib Development
- **Week 2**: Foundation and Event Bus integration
- **Week 3**: Core RL algorithms (PPO, DQN)
- **Week 4**: Knowledge Graph integration
- **Week 5**: Advanced learning features
- **Week 6**: Performance optimization
- **Week 7**: Production hardening
- **Week 8**: Final integration
- **Dependencies**: Needs MCP events (Week 3), KG queries (Week 4)

### Weeks 4-7: Claude Integration
- **Week 4**: Foundation and Event Bus async queue
- **Week 5**: Semantic caching and optimization
- **Week 6**: Advanced strategy analysis
- **Week 7**: Production hardening
- **Dependencies**: Needs game context from Ray/KG

### Weeks 5-10: Analytics Development
- **Week 5**: Foundation and Event Bus integration
- **Week 6**: Schema implementation
- **Week 7**: Query optimization and MLflow
- **Week 8**: Grafana dashboards
- **Week 9**: Advanced analytics
- **Week 10**: Production readiness
- **Dependencies**: Consumes all event types

### Headless Balatro (Parallel Track)
- Developed independently
- Must integrate with MCP by Week 2
- Shares 2GB allocation with MCP

## Memory Allocation Summary (32GB Total)

### Infrastructure (5GB)
- **Event Bus**: 2GB (NATS or similar)
- **Resource Coordinator**: 1GB
- **Redis Cache**: 2GB (shared between Claude and Analytics)

### Core Components (26GB)
- **Memgraph**: 10GB (reduced from 12GB)
- **Ray RLlib**: 8GB
  - Object Store: 2.5GB
  - Workers: 3.5GB
  - Checkpoints: 1GB
  - Buffer: 1GB
- **Analytics**: 5GB
  - QuestDB: 3GB
  - EventStoreDB: 2GB
- **MCP + Headless**: 2GB combined
- **Claude/LangChain**: 1GB (uses shared Redis)

### System Buffer (1GB)
- OS and burst capacity

## Critical Integration Points

### Week 3 Checkpoint
- MCP publishing events to Event Bus
- Ray consuming learning requests
- Knowledge Graph ingesting game states

### Week 7 Checkpoint
- Full bidirectional integration between Ray ↔ KG ↔ Claude
- Analytics capturing all event types
- End-to-end data flow validated

### Week 10 Final Integration
- All components operational
- Performance targets met
- Production deployment ready

## Risk Mitigation

### Timeline Risks
1. **MCP Delays**: Would impact all components
   - Mitigation: Mock Event Bus producer by Week 1
   
2. **Integration Complexity**: Multiple moving parts
   - Mitigation: Weekly integration tests, clear interfaces

### Resource Risks
1. **Memory Pressure**: Total allocation near limit
   - Mitigation: Aggressive pruning, Resource Coordinator management
   
2. **Redis Conflicts**: Shared between components
   - Mitigation: Namespace separation, monitoring

## Development Approach

This is designed as a single-developer or small team project with parallel development possible due to:
- Clean interface boundaries (Event Bus)
- Mock implementations for early testing
- Independent component development
- Progressive integration milestones

## Success Criteria

1. All components operational within memory limits
2. Event Bus latency <10ms
3. No integration blocking issues
4. Performance targets achieved
5. Clean handoff at Week 10

This reconciliation ensures all components align with the overall 10-week timeline while respecting resource constraints and dependencies.