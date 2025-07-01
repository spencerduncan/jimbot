# MCP Communication Framework Development Plan

## Executive Summary

This development plan outlines the implementation of the MCP Communication Framework for the Balatro Sequential Learning System as part of the Week 0-3 development phase. The framework will serve as the primary event producer, publishing game state changes to the central Event Bus using Protocol Buffers over gRPC, while maintaining compatibility with the existing BalatroMCP mod.

## Current System Analysis

The existing implementation provides a solid foundation with three core components:

**MCP Server Infrastructure**: The `/mcp-server/` directory contains a basic file-based communication system using JSON-RPC 2.0 protocol. This provides reliable message passing but lacks sophisticated event aggregation capabilities needed for complex scoring sequences.

**State Extraction Framework**: The `/state_extractor/` module includes multiple specialized extractors that parse game state effectively. These extractors form the basis for enhanced event capture but require extension to handle high-frequency scoring events.

**Action Validation System**: The `/action_executor/` module implements blind selection and reroll validators. This validation framework ensures game rule compliance but needs enhancement for batch processing support.

## Technical Architecture Design

### Event Bus Integration

The MCP framework acts as the primary event producer for the JimBot system, publishing standardized Protocol Buffer messages to the central Event Bus:

```typescript
import { Event, GameStateEvent, EventType } from './proto/jimbot/events/v1/events_pb';
import { EventBusClient } from './clients/event_bus_client';

class MCPEventPublisher {
  private eventBusClient: EventBusClient;
  private batchAggregator: BatchAggregator;
  
  async publishGameState(gameState: BalatroGameState): Promise<void> {
    // Convert to Protocol Buffer format
    const event = new Event();
    event.setEventId(uuidv4());
    event.setType(EventType.GAME_STATE);
    event.setSource('mcp_server');
    event.setTimestamp(Timestamp.now());
    
    const gameStateEvent = this.convertToProto(gameState);
    event.setPayload(Any.pack(gameStateEvent));
    
    // Batch for efficiency (100ms window)
    await this.batchAggregator.add(event);
  }
}
```

### Batch Aggregation Strategy

To handle hundreds of scoring triggers per hand efficiently, the MCP implements a 100ms batch window:

```typescript
class BatchAggregator {
  private batchWindow = 100; // milliseconds
  private eventQueue: Event[] = [];
  private batchTimer: NodeJS.Timeout | null = null;
  
  async add(event: Event): Promise<void> {
    this.eventQueue.push(event);
    
    if (!this.batchTimer) {
      this.batchTimer = setTimeout(() => this.flush(), this.batchWindow);
    }
  }
  
  private async flush(): Promise<void> {
    if (this.eventQueue.length === 0) return;
    
    // Aggregate similar events
    const aggregated = this.aggregateEvents(this.eventQueue);
    
    // Publish to Event Bus
    await this.eventBusClient.publishBatch(aggregated);
    
    this.eventQueue = [];
    this.batchTimer = null;
  }
  
  private aggregateEvents(events: Event[]): Event[] {
    // Group by event type and aggregate scoring cascades
    return this.groupByType(events).map(group => 
      this.createAggregatedEvent(group)
    );
  }
}
```

### Protocol Buffer Schema Integration

The MCP uses the standardized Protocol Buffer schemas defined in the interface specification:

```protobuf
// Extends base GameStateEvent with Balatro-specific fields
message BalatroGameStateEvent {
  GameStateEvent base = 1;
  
  // Balatro-specific extensions
  repeated TriggerEvent triggers = 2;
  CascadeInfo cascade_info = 3;
  TimingInfo timing = 4;
}

message TriggerEvent {
  string joker_name = 1;
  string trigger_type = 2;
  int32 chips_added = 3;
  int32 mult_added = 4;
  float mult_multiplier = 5;
  int64 timestamp_micros = 6;
}

message CascadeInfo {
  string cascade_id = 1;
  repeated string joker_chain = 2;
  int32 total_triggers = 3;
}
```

## Development Timeline (Weeks 0-3)

### Week 0: Interface Specification and Setup

**Objective**: Define Protocol Buffer schemas and set up Event Bus infrastructure

- Define Protocol Buffer schemas for all event types
- Set up Event Bus infrastructure (using NATS or similar)
- Implement Resource Coordinator stub
- Create development environment with Docker Compose
- Deliverables: Working Event Bus, defined schemas, development environment

### Week 1: Core MCP Implementation

**Objective**: Implement MCP as primary event producer with BalatroMCP integration

#### Days 1-2: Event Publisher Implementation
- Implement MCPEventPublisher with gRPC client
- Create BatchAggregator with 100ms window
- Set up Protocol Buffer compilation pipeline
- Deliverables: Core event publishing infrastructure

#### Days 3-4: BalatroMCP Integration
- Create adapter for existing BalatroMCP mod messages
- Implement state extraction with event conversion
- Maintain backward compatibility layer
- Deliverables: Full BalatroMCP compatibility

#### Day 5: Testing and Monitoring
- Unit tests for event publishing
- Integration tests with Event Bus
- Implement health check and metrics endpoints
- Deliverables: Tested MCP with observability

### Week 2: Advanced Features and Optimization

**Objective**: Implement complex event tracking and performance optimization

#### Days 1-2: Complex Scoring Capture
- Implement trigger event tracking for joker cascades
- Create cascade detection and aggregation logic
- Add timing information for turn-based decisions
- Deliverables: Full scoring event capture

#### Days 3-4: Performance Optimization
- Optimize batch processing for 1000+ events/second
- Implement backpressure handling
- Add circuit breaker for Event Bus failures
- Deliverables: Production-ready performance

#### Day 5: Resource Coordination
- Integrate with Resource Coordinator
- Implement memory usage monitoring
- Add adaptive batching based on resources
- Deliverables: Resource-aware MCP server

### Week 3: Integration and Production Readiness

**Objective**: Complete system integration and validate production readiness

#### Days 1-2: Full System Integration
- End-to-end testing with all components
- Validate event flow to Knowledge Graph and Ray
- Performance testing under load
- Deliverables: Validated integration

#### Days 3-4: Production Hardening
- Implement comprehensive error handling
- Add operational logging and alerts
- Create deployment scripts and configuration
- Deliverables: Production-ready system

#### Day 5: Documentation and Handoff
- Complete API documentation
- Create operator runbooks
- Knowledge transfer session
- Deliverables: Fully documented system

## Integration Points

### Event Bus Integration

The MCP publishes events that are consumed by multiple components:

```typescript
// Events consumed by Knowledge Graph
await eventBus.publish({
  type: EventType.GAME_STATE,
  payload: gameStateEvent,
  topics: ['game.state', 'knowledge.update']
});

// Events consumed by Ray RLlib
await eventBus.publish({
  type: EventType.LEARNING_DECISION,
  payload: decisionRequest,
  topics: ['learning.decision.request']
});

// Events consumed by Analytics
await eventBus.publish({
  type: EventType.METRIC,
  payload: performanceMetric,
  topics: ['metrics.game', 'metrics.performance']
});
```

### BalatroMCP Compatibility

The framework maintains full compatibility with the existing mod:

```typescript
class BalatroMCPAdapter {
  constructor(
    private legacyClient: BalatroMCPClient,
    private eventPublisher: MCPEventPublisher
  ) {}
  
  async handleLegacyMessage(message: any): Promise<void> {
    // Convert legacy format to Protocol Buffer
    const gameState = this.convertLegacyFormat(message);
    
    // Publish to Event Bus
    await this.eventPublisher.publishGameState(gameState);
    
    // Maintain legacy response if needed
    return this.createLegacyResponse(gameState);
  }
}
```

### Resource Coordinator Integration

MCP respects system resource limits:

```typescript
class ResourceAwareMCP {
  async beforePublish(): Promise<void> {
    const grant = await this.resourceCoordinator.requestResource({
      component: 'mcp_server',
      type: ResourceType.MEMORY_MB,
      amount: 50, // 50MB for batch
      duration_ms: 1000
    });
    
    if (!grant.approved) {
      await this.throttle();
    }
  }
}
```

## Risk Assessment and Mitigation

### Technical Risks

**Event Bus Overload** (Medium probability)
- Mitigation: Implement backpressure and adaptive batching
- Monitoring: Queue depth and latency metrics
- Fallback: Local buffering with retry logic

**Protocol Buffer Version Conflicts** (Low probability)
- Mitigation: Strict versioning policy, backward compatibility tests
- Monitoring: Schema validation in CI/CD
- Fallback: Version negotiation protocol

**BalatroMCP Integration Issues** (Medium probability)
- Mitigation: Maintain adapter pattern for isolation
- Monitoring: Legacy message success rate
- Fallback: Direct mod communication mode

### Integration Risks

**Week 3 Checkpoint Dependencies** (High probability)
- Risk: Other components need MCP events before Week 3
- Mitigation: Provide mock Event Bus producer by Week 1
- Monitoring: Daily integration status checks

**Resource Contention** (Medium probability)
- Risk: Memory pressure from high event volume
- Mitigation: Aggressive batching and compression
- Monitoring: Memory usage alerts at 80% threshold

## Resource Requirements

### Development Approach

This component is designed for implementation by a single developer or small team as part of the overall JimBot project.

### Technical Skills Required

- **TypeScript/Node.js**: Primary development language
- **gRPC/Protocol Buffers**: For Event Bus integration
- **Game Integration**: Understanding of BalatroMCP mod structure
- **Event Processing**: Experience with streaming and batching

### Memory Allocation

As specified in the interface specification:
- **MCP Server**: 2GB RAM (shared with Headless Balatro)
- **Peak Usage**: During batch aggregation windows
- **Steady State**: ~200MB for normal operation

## Validation Strategy

### Performance Benchmarks

- Event capture latency: <100ms for hundreds of triggers
- Batch processing: 1000+ events/second sustained
- Memory usage: <100MB steady state, <500MB peak
- System availability: 99.9% uptime target

### Testing Approach

**Unit Testing**: Comprehensive coverage for event aggregation, joker interactions, and data integrity with >80% coverage target.

**Integration Testing**: Daily compatibility validation with existing BalatroMCP mod, ensuring zero regression.

**Performance Testing**: Load scenarios from 50 to 1000+ events/second with graceful degradation validation.

**End-to-End Validation**: Complex gameplay scenarios including extended sessions, error recovery, and edge cases.

## Success Criteria

The MCP Communication Framework will be considered successful when it:

1. **Event Publishing**: Publishes game state events to Event Bus with <100ms latency
2. **Compatibility**: Maintains 100% backward compatibility with BalatroMCP mod
3. **Performance**: Handles 1000+ events/second with batching
4. **Integration**: Successfully integrates with Event Bus and Resource Coordinator
5. **Reliability**: Implements circuit breakers and error handling
6. **Observability**: Provides health checks, metrics, and structured logging
7. **Resource Efficiency**: Operates within 2GB memory allocation

## Key Deliverables

By the end of Week 3:
- Fully functional MCP server publishing to Event Bus
- Protocol Buffer schemas for all Balatro events
- Integration tests with other components
- Operational documentation and runbooks
- Performance benchmarks meeting targets

This plan aligns with the overall JimBot architecture, providing the critical event ingestion layer that feeds the Knowledge Graph, Learning System, and Analytics components.