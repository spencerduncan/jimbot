# Event Bus Phased Implementation Plan

## Overview

This document outlines a phased approach to implementing the Event Bus that addresses the circular dependency with Protocol Buffers and enables other components to start development immediately. The plan breaks implementation into 4 phases, with Phase 1 providing immediate value for BalatroMCP testing.

## Current State Analysis

### Existing Implementation
- **BalatroMCP**: Already has a working REST client sending JSON events
- **Test Server**: Python-based test server exists but not production-ready
- **Event Format**: Well-defined JSON structure already in use

### Key Issues Identified
1. **Circular Dependency**: Protocol Buffers definition requires Event Bus, but Event Bus implementation references Protocol Buffers
2. **Blocking Factor**: Other components cannot start until Event Bus is available
3. **Production Readiness**: Current test server is not suitable for production use
4. **Language Decision**: Event Bus planned for Rust but needs immediate availability

## Phase 1: Minimal REST API (Week 0, Days 1-3)

### Goal
Provide immediate REST API compatibility for BalatroMCP testing without Protocol Buffer dependencies.

### Deliverables
1. **Rust REST Server** with endpoints:
   - `POST /events` - Single event ingestion
   - `POST /events/batch` - Batch event ingestion
   - `GET /health` - Health check endpoint
   - `GET /metrics` - Basic Prometheus metrics

2. **JSON Schema Validation**:
   - Accept existing BalatroMCP JSON format
   - Basic validation of required fields
   - Store events in memory buffer

3. **Docker Deployment**:
   ```dockerfile
   FROM rust:1.75-slim
   WORKDIR /app
   COPY . .
   RUN cargo build --release
   CMD ["./target/release/event-bus"]
   ```

### Implementation Details
```rust
// Minimal server structure
use axum::{Router, Json};
use serde::{Deserialize, Serialize};

#[derive(Deserialize, Serialize)]
struct Event {
    event_id: String,
    event_type: String,
    source: String,
    timestamp: i64,
    version: i32,
    payload: serde_json::Value,
}

async fn ingest_event(Json(event): Json<Event>) -> Result<Json<Response>, Error> {
    // Basic validation
    // Store in memory buffer
    // Return success
}
```

### Time Estimate: 3 days
- Day 1: Basic REST server setup
- Day 2: JSON validation and memory storage
- Day 3: Docker deployment and testing

## Phase 2: Protocol Buffer Integration (Week 0-1, Days 4-7)

### Goal
Add Protocol Buffer support while maintaining JSON backward compatibility.

### Deliverables
1. **Protocol Buffer Definitions**:
   - Move protobuf definitions to separate repository/module
   - Generate Rust code from `.proto` files
   - Create JSON ↔ Protobuf converters

2. **Dual Format Support**:
   - Accept JSON via REST (for BalatroMCP)
   - Accept Protobuf via gRPC (for future components)
   - Internal storage uses Protobuf format

3. **Event Persistence**:
   - Replace memory buffer with persistent queue (RocksDB)
   - Implement event retention policies
   - Add event replay capabilities

### Implementation Details
```rust
// Protobuf conversion layer
impl From<JsonEvent> for ProtoEvent {
    fn from(json: JsonEvent) -> Self {
        // Convert JSON to Protobuf
    }
}

// Dual endpoint support
let app = Router::new()
    .route("/events", post(json_handler))
    .route("/grpc", grpc_service);
```

### Time Estimate: 4 days
- Day 1: Protobuf schema definitions
- Day 2: Code generation and conversion logic
- Day 3: RocksDB integration
- Day 4: Testing and validation

## Phase 3: Full gRPC Interface (Week 1, Days 8-12)

### Goal
Implement complete gRPC interface for high-performance component communication.

### Deliverables
1. **gRPC Services**:
   - Unary RPC: `PublishEvent`
   - Streaming RPC: `SubscribeEvents`
   - Bidirectional streaming: `StreamEvents`

2. **Subscription Management**:
   - Topic-based filtering
   - Consumer group support
   - At-least-once delivery guarantees

3. **Performance Optimizations**:
   - Connection pooling
   - Batch processing
   - Zero-copy where possible

### Implementation Details
```rust
#[tonic::async_trait]
impl EventBus for EventBusService {
    async fn publish_event(&self, request: Request<Event>) -> Result<Response<PublishResponse>> {
        // Handle event publishing
    }
    
    type SubscribeEventsStream = ReceiverStream<Result<Event, Status>>;
    
    async fn subscribe_events(&self, request: Request<SubscribeRequest>) 
        -> Result<Response<Self::SubscribeEventsStream>, Status> {
        // Handle event subscription
    }
}
```

### Time Estimate: 5 days
- Days 1-2: gRPC service implementation
- Day 3: Subscription management
- Days 4-5: Performance optimization and testing

## Phase 4: Production Hardening (Week 2, Days 13-17)

### Goal
Optimize performance, add monitoring, and ensure production readiness.

### Deliverables
1. **Performance Enhancements**:
   - Event batching (100ms windows)
   - Compression for large payloads
   - Connection multiplexing
   - Target: <10ms p99 latency

2. **Observability**:
   - Prometheus metrics (latency, throughput, errors)
   - OpenTelemetry tracing
   - Structured logging
   - Grafana dashboards

3. **Reliability Features**:
   - Circuit breakers
   - Retry logic with exponential backoff
   - Dead letter queue
   - Graceful shutdown

4. **Operational Tools**:
   - Event replay utility
   - Schema migration tools
   - Performance benchmarks
   - Integration test suite

### Time Estimate: 5 days
- Day 1: Performance optimization
- Day 2: Metrics and monitoring
- Day 3: Reliability features
- Days 4-5: Testing and documentation

## Dependencies and Integration Points

### Phase 1 Enables
- BalatroMCP can immediately test with production-like Event Bus
- Analytics team can start consuming events (even if just JSON)
- Performance baseline established

### Phase 2 Enables
- Other components can start Protobuf integration
- Schema versioning and evolution testing
- Event persistence for replay scenarios

### Phase 3 Enables
- Ray RLlib high-performance integration
- Memgraph streaming updates
- Full component integration testing

### Phase 4 Enables
- Production deployment
- Performance guarantees
- SLA monitoring

## Risk Mitigation

### Technical Risks
1. **Rust Learning Curve**
   - Mitigation: Start with simple implementation, iterate
   - Fallback: Use existing Rust web frameworks (Axum, Tonic)

2. **Performance Requirements**
   - Mitigation: Benchmark early and often
   - Fallback: Horizontal scaling if needed

3. **Integration Complexity**
   - Mitigation: Maintain backward compatibility at each phase
   - Fallback: Keep Python test server as emergency backup

### Timeline Risks
1. **Phase 1 Delays**
   - Impact: Blocks BalatroMCP testing
   - Mitigation: Can extend Python test server if needed

2. **Protocol Buffer Issues**
   - Impact: Delays other component integration
   - Mitigation: JSON fallback for all components

## Success Criteria

### Phase 1
- [ ] BalatroMCP successfully sends events
- [ ] 1000+ events/second throughput
- [ ] Docker container < 100MB

### Phase 2
- [ ] JSON → Protobuf conversion working
- [ ] Events persisted to disk
- [ ] Schema versioning implemented

### Phase 3
- [ ] gRPC clients can subscribe
- [ ] < 50ms p99 latency
- [ ] 10,000+ events/second throughput

### Phase 4
- [ ] 99.9% uptime over 24 hours
- [ ] < 10ms p99 latency
- [ ] Full observability stack deployed

## Conclusion

This phased approach delivers immediate value while building toward the full Event Bus implementation. By starting with REST/JSON compatibility, we unblock BalatroMCP testing within 3 days while laying the foundation for the complete system. Each phase delivers concrete value and enables parallel development across the JimBot ecosystem.