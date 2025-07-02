# Rust Migration Plan for JimBot

## Executive Summary

This plan outlines the migration of JimBot components to Rust wherever technically feasible and beneficial. Rust offers superior performance, memory safety, and excellent async/concurrent programming capabilities, making it ideal for high-performance components in the JimBot architecture.

## Existing Implementation Status

The project already has a working BalatroMCP Lua mod that:
- Extracts complete game state from Balatro
- Sends events via REST API to an event bus endpoint
- Supports headless operation and event batching
- Includes a Python test server for development

This existing implementation provides a solid foundation that the Rust components will integrate with.

## Component Migration Strategy

### 1. Event Bus (Week 0-1) - **HIGH PRIORITY**
**Current**: Python test server (temporary)  
**Target**: Rust implementation  
**Rationale**: Replace the Python test server with a production-ready Rust event bus that can handle the existing BalatroMCP REST API

**Key Requirements**:
- Maintain REST API compatibility with existing BalatroMCP mod
- Support `/api/v1/events` and `/api/v1/events/batch` endpoints
- Add gRPC interface for other components
- Implement proper event routing to consumers

**Implementation**:
```rust
// REST API compatibility layer for BalatroMCP
use axum::{routing::post, Json, Router};
use tokio::sync::mpsc;

pub struct EventBusService {
    event_sender: mpsc::Sender<Event>,
    subscribers: Arc<RwLock<HashMap<String, Vec<Subscriber>>>>,
}

impl EventBusService {
    pub fn create_rest_router(&self) -> Router {
        Router::new()
            .route("/api/v1/events", post(Self::handle_single_event))
            .route("/api/v1/events/batch", post(Self::handle_batch_events))
            .with_state(self.clone())
    }
    
    async fn handle_single_event(
        State(svc): State<EventBusService>,
        Json(event): Json<Event>,
    ) -> Result<Json<Value>, StatusCode> {
        svc.event_sender.send(event).await?;
        Ok(Json(json!({"status": "ok"})))
    }
}
```

### 2. MCP Server - **CLARIFICATION NEEDED**
**Current State**: The existing BalatroMCP Lua mod already implements the MCP functionality directly in Lua, communicating with the Event Bus via REST.

**Options**:
1. **Keep current architecture**: BalatroMCP (Lua) → Event Bus (Rust)
   - Pros: Already working, minimal changes needed
   - Cons: Less performant than native integration

2. **Create Rust MCP proxy**: BalatroMCP (Lua) → MCP Proxy (Rust) → Event Bus
   - Pros: Better aggregation, Protocol Buffer conversion
   - Cons: Additional component, more complexity

3. **Enhanced Lua mod**: Upgrade BalatroMCP to use more efficient protocols
   - Pros: Single component, direct integration
   - Cons: Limited by Lua capabilities

**Recommendation**: Option 1 for now, with potential future optimization via Option 2 if performance becomes an issue.

### 3. Analytics Component (Week 5-6) - **HIGH PRIORITY**
**Current**: TypeScript  
**Target**: Rust  
**Rationale**: High-throughput data ingestion requires maximum performance

**Implementation Approach**:
- Use `questdb-rs` for QuestDB integration
- `eventstore-rs` for EventStoreDB
- Native time-series compression
- Zero-copy deserialization

### 4. Resource Coordinator (Week 2) - **MEDIUM PRIORITY**
**Current**: Python  
**Target**: Rust  
**Rationale**: Critical system component managing resources needs deterministic performance

**Benefits**:
- Lock-free data structures for resource allocation
- Predictable latency
- Native Prometheus metrics with `prometheus` crate

### 5. MAGE Modules (Week 4) - **MEDIUM PRIORITY**
**Current**: Python/C++  
**Target**: Rust  
**Rationale**: Rust is officially supported by MAGE and offers C++ performance with memory safety

**Example MAGE Module in Rust**:
```rust
use memgraph_rust::*;

#[query_module]
mod balatro_algorithms {
    use super::*;
    
    #[read_procedure]
    fn detect_joker_synergies(
        ctx: &Context,
        min_occurrences: i64,
        min_win_rate: f64,
    ) -> Result<RecordStream> {
        // Rust implementation with zero-cost abstractions
        let query = r#"
            MATCH (r:Run)-[:USED_JOKER]->(j1:Joker)
            MATCH (r)-[:USED_JOKER]->(j2:Joker)
            WHERE j1.id < j2.id AND r.outcome = 'win'
            RETURN j1, j2, count(r) as wins
        "#;
        
        ctx.execute_query(query)
            .filter(|record| {
                let win_rate = record["wins"].as_f64() / record["total"].as_f64();
                win_rate >= min_win_rate
            })
            .collect()
    }
}
```

### 6. Components Remaining in Original Languages

#### Ray RLlib (Python) - **NO MIGRATION**
- Deep integration with Python ML ecosystem
- Would require complete rewrite of Ray framework
- Use PyO3 for Rust-Python interop where needed

#### Claude/LangChain (Python) - **NO MIGRATION**  
- LangChain is Python-only
- Create Rust gRPC client for communication

#### Memgraph Core (C++) - **NO MIGRATION**
- Third-party database
- Use Rust client libraries

#### Headless Balatro (Lua) - **NO MIGRATION**
- Game logic deeply integrated with Lua/LÖVE 2D
- Maintain existing Lua implementation
- MCP Server (in Rust) will handle the interface

## Integration Patterns

### Rust-Python Interop
```rust
// Using PyO3 for Python integration
use pyo3::prelude::*;

#[pyfunction]
fn process_game_state(state: &PyDict) -> PyResult<Vec<f32>> {
    // Rust processing of Python data
    Ok(extract_features(state))
}

#[pymodule]
fn jimbot_rust(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(process_game_state, m)?)?;
    Ok(())
}
```

### Rust-Lua Communication
The MCP Server (in Rust) will communicate with Headless Balatro (Lua) via:
- File-based IPC (existing approach)
- Named pipes for lower latency
- Shared memory for high-frequency updates

## Updated Component Registry

| Component | Language | Primary Interface | Secondary Interface |
|-----------|----------|------------------|-------------------|
| MCP Server | **Rust** | gRPC Event Producer | REST Health/Config |
| Memgraph | Python/Cypher | GraphQL Query | gRPC Mutations |
| Ray RLlib | Python | gRPC Model Serving | REST Job Management |
| Claude/LangChain | Python | Async Queue | REST Cache Management |
| Analytics | **Rust** | Event Consumer | SQL Query Interface |
| Headless Balatro | **Lua** | File/IPC Communication | REST Debug Interface |
| Event Bus | **Rust** | gRPC Streaming | REST Admin API |
| Resource Coordinator | **Rust** | gRPC Service | Prometheus Metrics |
| MAGE Modules | **Rust** | Cypher Procedures | N/A |

## Development Timeline Adjustments

### Week 0: Foundation
- Set up Rust development environment
- Create shared Rust workspace with common dependencies
- Implement Protocol Buffer schemas in Rust
- Begin Event Bus implementation in Rust

### Week 1: Core Infrastructure
- Complete Event Bus in Rust
- Start MCP Server migration to Rust
- Implement Resource Coordinator in Rust
- Create Rust-Python interop layer

### Week 2-3: MCP and Integration
- Complete MCP Server in Rust
- Implement batch aggregation with lock-free structures
- Create efficient IPC mechanism for Lua communication
- Performance testing and optimization

### Week 4: MAGE Modules
- Implement Balatro-specific algorithms in Rust
- Create Rust MAGE module template
- Benchmark against Python implementations

### Week 5-6: Analytics
- Migrate Analytics component to Rust
- Implement high-performance time-series ingestion
- Create Rust-based Grafana data source

## Performance Benefits

### Expected Improvements
- **Event Bus**: 5-10x throughput increase
- **MCP Server**: 10x reduction in event processing latency
- **Analytics**: 3-5x improvement in ingestion rate
- **Resource Coordinator**: Deterministic <1ms response times
- **MAGE Modules**: 2-5x faster graph algorithms

### Memory Benefits
- Reduced memory usage (no GC overhead)
- Predictable memory patterns
- Better cache locality
- Zero-copy processing where possible

## Risk Mitigation

### Technical Risks
1. **Learning Curve**: Rust has a steeper learning curve
   - Mitigation: Start with Event Bus (already planned for Rust)
   - Provide Rust training resources

2. **Ecosystem Maturity**: Some libraries less mature than TypeScript/Python
   - Mitigation: Use well-established crates
   - Contribute back to open source where needed

3. **Integration Complexity**: More complex FFI with Python components
   - Mitigation: Use PyO3 for seamless integration
   - Create clear interface boundaries

## Key Rust Dependencies

```toml
[workspace]
members = ["event-bus", "mcp-server", "analytics", "resource-coordinator", "mage-modules"]

[workspace.dependencies]
tokio = { version = "1.35", features = ["full"] }
tonic = "0.10"
prost = "0.12"
serde = { version = "1.0", features = ["derive"] }
async-trait = "0.1"
anyhow = "1.0"
tracing = "0.1"
dashmap = "5.5"
pyo3 = { version = "0.20", features = ["auto-initialize"] }
```

## Integration with Existing BalatroMCP

### Current Implementation Details
The BalatroMCP Lua mod provides:
- Complete game state extraction (jokers, cards, money, etc.)
- REST API client with retry logic and connection testing
- Event batching with configurable windows (default 100ms)
- Headless mode support for server deployment
- Action execution for AI control
- JSON serialization (no Protocol Buffers yet)

### Migration Path
1. **Phase 1**: Deploy Rust Event Bus that accepts BalatroMCP's REST API
2. **Phase 2**: Add Protocol Buffer conversion in Event Bus
3. **Phase 3**: Implement other Rust components that consume from Event Bus
4. **Phase 4**: Optional - Add binary protocol support to BalatroMCP

### Compatibility Requirements
The Rust Event Bus MUST:
- Accept JSON payloads at `/api/v1/events` and `/api/v1/events/batch`
- Return `{"status": "ok"}` responses
- Handle the existing event schema from BalatroMCP
- Convert JSON events to Protocol Buffers internally

## Conclusion

Migrating to Rust wherever possible will provide JimBot with:
- Superior performance for high-frequency operations
- Memory safety without garbage collection overhead
- Excellent async/concurrent programming model
- Better resource utilization on the single workstation
- Type safety across component boundaries

The migration maintains compatibility with components that must remain in their original languages (Ray, LangChain, Memgraph, Headless Balatro) while maximizing performance where it matters most. The existing BalatroMCP implementation provides a working foundation that accelerates development.