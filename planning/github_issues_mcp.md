# MCP Communication Framework - GitHub Issues Dependency Graph

## Parent Epic

### [Epic]: MCP Communication Framework Implementation

**Description**
Implement the MCP Communication Framework as the primary event producer for the Balatro Sequential Learning System. This framework will handle game state events from BalatroMCP mod, aggregate them efficiently, and publish to the central Event Bus using Protocol Buffers over gRPC.

**Current State**
- BalatroMCP mod exists but has bugs in event aggregation
- Uses JSON/HTTP instead of planned Protobuf/gRPC
- No production Event Bus or MCP Server implementation

**Target Architecture**
```
BalatroMCP (Lua) --[HTTP]--> MCP Server (TypeScript) --[Protobuf/gRPC]--> Event Bus (Rust) ---> Components
```

**Acceptance Criteria**
- [ ] Event publishing with <100ms latency for hundreds of triggers
- [ ] 100% backward compatibility with BalatroMCP mod
- [ ] Handle 1000+ events/second with batching
- [ ] Full Event Bus and Resource Coordinator integration
- [ ] Comprehensive error handling and monitoring
- [ ] Production deployment ready

**Child Issues**
- [ ] #1: Fix BalatroMCP event aggregation bugs
- [ ] #2: Fix BalatroMCP retry logic and error handling  
- [ ] #3: Define Protocol Buffer schemas for Balatro events
- [ ] #4: Create Docker Compose development environment
- [ ] #5: Implement Event Bus infrastructure
- [ ] #6: Set up Protocol Buffer compilation pipeline
- [ ] #7: Implement MCP Server core with gRPC
- [ ] #8: Create BalatroMCP adapter layer
- [ ] #9: Implement complex event aggregation
- [ ] #10: Optimize performance and batching
- [ ] #11: Integrate Resource Coordinator
- [ ] #12: Create comprehensive test suite
- [ ] #13: Production hardening and monitoring
- [ ] #14: Documentation and deployment

**Parallel Work Streams**
- Stream 1 (Bug Fixes): #1, #2 → #8
- Stream 2 (Infrastructure): #3, #4 → #5, #6 → #7
- Stream 3 (Features): #7 → #9 → #10
- Stream 4 (Integration): #11 (can start after #3, #7)

---

## Child Issues

### Issue #1: [Bug]: Fix BalatroMCP event aggregation bugs

**Description**
The current BalatroMCP mod has an event_aggregator.lua file that appears to be unused. Events are sent individually without batching, causing performance issues during complex scoring sequences.

**Current Behavior**
- Individual HTTP requests for each game event
- No batching or aggregation
- Performance degradation with multiple joker triggers

**Acceptance Criteria**
- [ ] Implement event batching in BalatroMCP mod
- [ ] Integrate event_aggregator.lua into main event flow
- [ ] Add configurable batch window (default 100ms)
- [ ] Test with complex joker cascades (100+ triggers)

**Technical Requirements**
- Lua coroutines for non-blocking aggregation
- Queue events during batch window
- Single HTTP request per batch
- Maintain event ordering

**Dependencies**
- **Blocks**: #8 (adapter needs fixed aggregation)
- No blocking dependencies - can start immediately

**Implementation Notes**
```lua
-- In event_bus_client.lua
function EventBusClient:send_event_batch(events)
    -- Implement batch sending
end

-- In main.lua
-- Hook up aggregator to collect events
```

**Definition of Done**
- [ ] Event aggregation working in BalatroMCP
- [ ] Performance tests show <100ms for 100+ events
- [ ] No regression in existing functionality
- [ ] Unit tests for aggregation logic

---

### Issue #2: [Bug]: Fix BalatroMCP retry logic and error handling

**Description**
Current retry logic in BalatroMCP has issues with exponential backoff and doesn't handle network failures gracefully, causing game freezes.

**Current Issues**
- Retry blocks game thread
- No circuit breaker for persistent failures
- Inadequate error logging

**Acceptance Criteria**
- [ ] Non-blocking retry mechanism
- [ ] Circuit breaker after 3 consecutive failures
- [ ] Proper error logging with context
- [ ] Graceful degradation when event bus unavailable

**Technical Requirements**
- Async retry using Lua coroutines
- Configurable retry parameters
- Local event buffering during outages
- Health check endpoint integration

**Dependencies**
- **Blocks**: #8 (adapter needs reliable retry logic)
- No blocking dependencies - can start immediately

**Implementation Notes**
```lua
-- Add circuit breaker pattern
local CircuitBreaker = {
    failure_count = 0,
    is_open = false,
    reset_timeout = 60
}
```

**Definition of Done**
- [ ] Retry logic doesn't block game
- [ ] Circuit breaker prevents cascade failures
- [ ] Error handling tested with network failures
- [ ] Performance unchanged in happy path

---

### Issue #3: [Feature]: Define Protocol Buffer schemas for Balatro events

**Description**
Create comprehensive Protocol Buffer schemas for all Balatro game events, extending the base event types defined in the interface specification.

**Acceptance Criteria**
- [ ] Define schemas for all game state events
- [ ] Include Balatro-specific extensions (triggers, cascades)
- [ ] Version management strategy
- [ ] Schema validation rules

**Technical Requirements**
- Extend base Event and GameStateEvent messages
- Define TriggerEvent, CascadeInfo messages
- Include timing information for analysis
- Follow protobuf best practices

**Dependencies**
- **Blocks**: #6, #7, #11 (all need schemas)
- No blocking dependencies - can start immediately

**Implementation Notes**
Location: `/jimbot/proto/jimbot/events/v1/balatro_events.proto`

```protobuf
message BalatroGameStateEvent {
  GameStateEvent base = 1;
  repeated TriggerEvent triggers = 2;
  CascadeInfo cascade_info = 3;
}
```

**Definition of Done**
- [ ] All event types defined in protobuf
- [ ] Schema documentation complete
- [ ] Validation rules implemented
- [ ] Example messages for testing

---

### Issue #4: [Feature]: Create Docker Compose development environment

**Description**
Set up a complete development environment using Docker Compose for all MCP dependencies including Event Bus, databases, and monitoring.

**Acceptance Criteria**
- [ ] Docker Compose with all services
- [ ] Event Bus (NATS/Kafka) configured
- [ ] Development databases (Redis, EventStore)
- [ ] Monitoring stack (Prometheus, Grafana)
- [ ] One-command startup

**Technical Requirements**
- Use official Docker images
- Volume mounts for persistence
- Network isolation
- Environment variable configuration

**Dependencies**
- **Blocks**: #5 (Event Bus needs Docker environment)
- No blocking dependencies - can start immediately

**Implementation Notes**
Create `docker-compose.yml` with:
- NATS for Event Bus
- Redis for caching
- EventStoreDB for event sourcing
- Prometheus + Grafana for monitoring

**Definition of Done**
- [ ] All services start with docker-compose up
- [ ] Services are networked correctly
- [ ] Persistent volumes configured
- [ ] README with setup instructions

---

### Issue #5: [Feature]: Implement Event Bus infrastructure

**Description**
Set up production Event Bus using NATS or similar technology, implementing the gRPC service defined in the interface specification.

**Acceptance Criteria**
- [ ] Event Bus service running (NATS recommended)
- [ ] gRPC service implementation
- [ ] Topic-based routing
- [ ] At-least-once delivery guarantee
- [ ] Monitoring and health checks

**Technical Requirements**
- High throughput (1000+ msgs/sec)
- Low latency (<10ms publish)
- Persistent subscriptions
- Cluster support for HA

**Dependencies**
- **Blocked by**: #4 (needs Docker environment)
- **Blocks**: #7 (MCP Server needs Event Bus)

**Implementation Notes**
```go
// Implement EventBusService from proto
type eventBusServer struct {
    nats *nats.Conn
    pb.UnimplementedEventBusServiceServer
}
```

**Definition of Done**
- [ ] Event Bus service operational
- [ ] gRPC endpoints working
- [ ] Performance benchmarks met
- [ ] Integration tests passing

---

### Issue #6: [Feature]: Set up Protocol Buffer compilation pipeline

**Description**
Create build pipeline for compiling Protocol Buffer definitions to multiple languages (Go, TypeScript, Python) needed by different components.

**Acceptance Criteria**
- [ ] Automated protobuf compilation
- [ ] Multi-language support (Go, TS, Python)
- [ ] CI/CD integration
- [ ] Version management

**Technical Requirements**
- protoc with language plugins
- Makefile or build scripts
- Git hooks for validation
- Package publication setup

**Dependencies**
- **Blocked by**: #3 (needs schema definitions)
- **Blocks**: #7 (MCP Server needs compiled protos)

**Implementation Notes**
```makefile
# Makefile
proto-gen:
    protoc --go_out=. --go-grpc_out=. \
           --ts_out=. --python_out=. \
           proto/**/*.proto
```

**Definition of Done**
- [ ] Build scripts working for all languages
- [ ] CI validates proto changes
- [ ] Generated code in correct locations
- [ ] Documentation for adding new protos

---

### Issue #7: [Feature]: Implement MCP Server core with gRPC

**Description**
Create the TypeScript MCP Server that receives events from BalatroMCP, aggregates them, and publishes to Event Bus via gRPC.

**Acceptance Criteria**
- [ ] TypeScript server receiving HTTP events
- [ ] gRPC client publishing to Event Bus
- [ ] Basic event transformation
- [ ] Health check endpoints
- [ ] Prometheus metrics

**Technical Requirements**
- Node.js with TypeScript
- Express for HTTP endpoints
- gRPC client libraries
- Structured logging

**Dependencies**
- **Blocked by**: #5 (needs Event Bus), #6 (needs protos)
- **Blocks**: #8, #9, #10, #11 (all need MCP Server)

**Implementation Notes**
```typescript
class MCPServer {
  private eventBusClient: EventBusClient;
  private httpServer: Express;
  
  async handleGameEvent(event: any): Promise<void> {
    const protoEvent = this.transformToProto(event);
    await this.eventBusClient.publish(protoEvent);
  }
}
```

**Definition of Done**
- [ ] Server receiving HTTP events
- [ ] Publishing to Event Bus via gRPC
- [ ] Health checks operational
- [ ] Basic metrics exposed

---

### Issue #8: [Feature]: Create BalatroMCP adapter layer

**Description**
Implement adapter layer in MCP Server for backward compatibility with existing BalatroMCP mod, handling JSON to Protobuf conversion.

**Acceptance Criteria**
- [ ] Receive JSON events from BalatroMCP
- [ ] Convert to Protocol Buffer format
- [ ] Maintain compatibility with mod
- [ ] Handle legacy event formats

**Technical Requirements**
- JSON schema validation
- Event transformation logic
- Backward compatibility tests
- Performance optimization

**Dependencies**
- **Blocked by**: #1, #2 (needs fixed mod), #7 (needs MCP Server)
- **Blocks**: #12 (testing needs adapter)

**Implementation Notes**
```typescript
class BalatroMCPAdapter {
  async handleLegacyEvent(jsonEvent: any): Promise<Event> {
    // Validate and transform
    return this.transformToProto(jsonEvent);
  }
}
```

**Definition of Done**
- [ ] Adapter receiving mod events
- [ ] Correct protobuf transformation
- [ ] No breaking changes to mod
- [ ] Performance benchmarks met

---

### Issue #9: [Feature]: Implement complex event aggregation

**Description**
Add sophisticated event aggregation for joker cascades, scoring sequences, and complex game state changes with 100ms batch windows.

**Acceptance Criteria**
- [ ] 100ms batch aggregation window
- [ ] Cascade detection and grouping
- [ ] Trigger sequence preservation
- [ ] Efficient memory usage

**Technical Requirements**
- Time-based batching
- Event deduplication
- Cascade relationship tracking
- Memory-efficient queuing

**Dependencies**
- **Blocked by**: #7 (needs MCP Server core)
- **Blocks**: #10 (optimization needs aggregation)

**Implementation Notes**
```typescript
class EventAggregator {
  private batchWindow = 100; // ms
  private cascadeDetector: CascadeDetector;
  
  aggregate(events: Event[]): AggregatedEvent {
    // Group by cascade, preserve order
  }
}
```

**Definition of Done**
- [ ] 100ms batching working
- [ ] Cascade detection accurate
- [ ] Memory usage optimal
- [ ] Unit tests comprehensive

---

### Issue #10: [Enhancement]: Optimize performance and batching

**Description**
Optimize MCP Server for high-throughput scenarios, handling 1000+ events/second with adaptive batching and backpressure.

**Acceptance Criteria**
- [ ] Handle 1000+ events/second sustained
- [ ] Adaptive batch sizing
- [ ] Backpressure handling
- [ ] Memory usage under 500MB peak

**Technical Requirements**
- Performance profiling
- Memory optimization
- Adaptive algorithms
- Load testing framework

**Dependencies**
- **Blocked by**: #9 (needs aggregation logic)
- **Blocks**: #13 (production needs optimization)

**Implementation Notes**
- Use Node.js streams for backpressure
- Implement adaptive batch sizing
- Add memory monitoring
- Create load testing suite

**Definition of Done**
- [ ] Performance targets met
- [ ] Memory usage acceptable
- [ ] Load tests passing
- [ ] Profiling data documented

---

### Issue #11: [Feature]: Integrate Resource Coordinator

**Description**
Integrate MCP Server with Resource Coordinator for memory management and system resource allocation.

**Acceptance Criteria**
- [ ] Request resources before batching
- [ ] Respect memory grants
- [ ] Adaptive behavior on limits
- [ ] Resource usage reporting

**Technical Requirements**
- gRPC client for Resource Coordinator
- Memory usage tracking
- Adaptive algorithms
- Graceful degradation

**Dependencies**
- **Blocked by**: #3 (needs protos), #7 (needs MCP Server)
- **Blocks**: #13 (production needs resource management)

**Implementation Notes**
```typescript
async beforeBatch(): Promise<void> {
  const grant = await this.resourceCoordinator.request({
    memory_mb: 50,
    duration_ms: 1000
  });
  
  if (!grant.approved) {
    await this.adaptBatchSize();
  }
}
```

**Definition of Done**
- [ ] Resource requests working
- [ ] Memory limits respected
- [ ] Adaptive behavior tested
- [ ] Monitoring integrated

---

### Issue #12: [Testing]: Create comprehensive test suite

**Description**
Implement unit, integration, and end-to-end tests for the complete MCP framework including performance benchmarks.

**Acceptance Criteria**
- [ ] Unit tests >80% coverage
- [ ] Integration tests for all components
- [ ] End-to-end game scenarios
- [ ] Performance test suite
- [ ] CI/CD integration

**Technical Requirements**
- Jest for TypeScript tests
- gRPC test utilities
- Mock Event Bus for testing
- Load testing tools

**Dependencies**
- **Blocked by**: #8 (needs complete implementation)
- **Blocks**: #13 (production needs tests)

**Implementation Notes**
- Unit tests for all modules
- Integration tests with mock services
- E2E tests with real Balatro scenarios
- Performance benchmarks

**Definition of Done**
- [ ] All test suites passing
- [ ] Coverage targets met
- [ ] CI running all tests
- [ ] Performance benchmarks documented

---

### Issue #13: [Enhancement]: Production hardening and monitoring

**Description**
Add production-grade error handling, circuit breakers, comprehensive logging, and monitoring to MCP framework.

**Acceptance Criteria**
- [ ] Circuit breakers for all external calls
- [ ] Structured logging with correlation IDs
- [ ] Prometheus metrics comprehensive
- [ ] Alert rules defined
- [ ] Graceful shutdown handling

**Technical Requirements**
- Circuit breaker library
- Structured logging (Winston)
- Prometheus client
- Grafana dashboards

**Dependencies**
- **Blocked by**: #10, #11, #12 (needs stable system)
- **Blocks**: #14 (deployment needs hardening)

**Implementation Notes**
- Add circuit breakers to Event Bus client
- Implement correlation ID propagation
- Create Grafana dashboard templates
- Define SLO/SLA metrics

**Definition of Done**
- [ ] All error paths handled
- [ ] Monitoring comprehensive
- [ ] Dashboards created
- [ ] Runbooks written

---

### Issue #14: [Documentation]: Documentation and deployment

**Description**
Create comprehensive documentation, deployment scripts, and operational runbooks for the MCP framework.

**Acceptance Criteria**
- [ ] API documentation complete
- [ ] Deployment automation
- [ ] Operational runbooks
- [ ] Architecture diagrams
- [ ] Performance tuning guide

**Technical Requirements**
- OpenAPI documentation
- Kubernetes manifests
- Terraform modules
- Ansible playbooks

**Dependencies**
- **Blocked by**: #13 (needs production-ready system)
- All other work must be complete

**Implementation Notes**
- Use OpenAPI for REST endpoints
- Create Helm charts for K8s
- Document all configuration
- Include troubleshooting guides

**Definition of Done**
- [ ] All documentation complete
- [ ] Deployment automated
- [ ] Runbooks tested
- [ ] Knowledge transfer done

---

## Dependency Graph Summary

```
Immediate Start (No Dependencies):
├── #1: Fix BalatroMCP aggregation bugs
├── #2: Fix BalatroMCP retry logic
├── #3: Define Protocol Buffer schemas
└── #4: Create Docker environment

First Wave (Single Dependencies):
├── #5: Event Bus infrastructure (needs #4)
└── #6: Protocol Buffer compilation (needs #3)

Core Implementation:
└── #7: MCP Server core (needs #5, #6)
    ├── #8: BalatroMCP adapter (needs #1, #2, #7)
    ├── #9: Complex aggregation (needs #7)
    └── #11: Resource Coordinator (needs #3, #7)

Advanced Features:
└── #10: Performance optimization (needs #9)

Final Phase:
├── #12: Test suite (needs #8)
└── #13: Production hardening (needs #10, #11, #12)
    └── #14: Documentation (needs #13)

Parallel Work Streams:
- Infrastructure: #4 → #5 → #7
- Schemas: #3 → #6 → #7
- Bug Fixes: #1, #2 → #8
- Features: #7 → #9 → #10
- Integration: #7 → #11
```

This dependency graph maximizes parallelization by allowing 4 issues to start immediately, creating multiple work streams that can progress independently until convergence points.