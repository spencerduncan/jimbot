# Ray RLlib Learning Orchestration Development Plan

## Executive Summary

This development plan outlines the implementation of the learning orchestration system using Ray RLlib for the Balatro sequential learning project, to be developed during Weeks 2-8 of the overall project timeline. Operating within an 8GB memory allocation, the system will consume game state events from the Event Bus, make learning decisions, and publish decision responses while integrating with the Knowledge Graph and Claude advisory systems.

## System Overview and Constraints

The learning orchestration system serves as the central coordinator for all reinforcement learning activities within the Balatro project. Given the strict memory constraint of 8GB for Ray operations, the architecture prioritizes efficiency over raw parallelism. The system must seamlessly integrate with the Memgraph knowledge graph (12GB allocation), QuestDB/EventStore persistence layer (6GB allocation), and Claude integration layer while maintaining stable performance.

The technical approach leverages Ray version 2.47.1 with its new efficient API stack, PettingZoo for game environment management, and PyTorch 2.1.2 for neural network operations. The available RTX 3090 GPU with 24GB VRAM serves as a computational accelerator for training while respecting the 8GB system RAM constraint.

## Technical Architecture

### Event Bus Integration

Ray RLlib operates as both event consumer and producer in the JimBot architecture:

```python
from jimbot.proto.events_pb2 import Event, LearningDecisionRequest, LearningDecisionResponse
from jimbot.clients import EventBusClient

class RayLearningOrchestrator:
    def __init__(self):
        self.event_bus = EventBusClient()
        self.ray_server = self._init_ray_server()
        
    async def start(self):
        # Subscribe to learning decision requests
        await self.event_bus.subscribe(
            topics=['learning.decision.request'],
            handler=self.handle_decision_request
        )
        
    async def handle_decision_request(self, event: Event):
        request = LearningDecisionRequest()
        event.payload.Unpack(request)
        
        # Get decision from Ray model
        decision = await self.ray_server.get_decision(request)
        
        # Publish response
        response_event = self._create_response_event(decision)
        await self.event_bus.publish(response_event)
```

### gRPC Service Interface

Ray exposes a gRPC service for synchronous decision requests:

```python
class RayDecisionService(DecisionServicer):
    def GetDecision(self, request: LearningDecisionRequest, context):
        # Use trained policy for inference
        with self.inference_lock:
            obs = self._convert_game_state(request.game_state)
            action, info = self.policy.compute_single_action(obs)
            
        return LearningDecisionResponse(
            request_id=request.request_id,
            selected_action=self._decode_action(action),
            confidence=info['action_prob'],
            used_llm=False,
            strategy_name=self.current_strategy
        )
```

## Development Approach

This component is designed for implementation by a single developer or small team, focusing on memory-efficient RL algorithms and clean integration patterns.

## Development Timeline (Weeks 2-8)

### Week 2: Foundation and Event Bus Integration

**Objective**: Establish Ray infrastructure and Event Bus connectivity

- Set up Ray cluster with memory constraints (8GB limit)
- Implement Event Bus subscription for learning requests
- Create gRPC service endpoint for synchronous decisions
- Design Balatro game environment using Gymnasium API
- Implement basic PPO algorithm with memory-efficient config
- Deliverables: Working Ray setup consuming events from Event Bus

### Week 3: Core Algorithm Implementation

**Objective**: Implement memory-efficient RL algorithms

- Complete PPO implementation with action masking
- Add DQN with compressed replay buffer (4:1 compression)
- Integrate with Resource Coordinator for GPU allocation
- Implement checkpointing and model persistence
- Create training pipeline consuming game states
- Deliverables: Functional RL algorithms training on Balatro

### Week 4: Knowledge Graph Integration

**Objective**: Connect Ray with Memgraph for strategy storage/retrieval

- Implement GraphQL client for knowledge queries
- Create strategy persistence mechanism
- Add joker synergy detection networks
- Query knowledge graph during decision making
- Store discovered strategies and patterns
- Deliverables: Bidirectional integration with Knowledge Graph

### Week 5: Advanced Learning Features

**Objective**: Implement Balatro-specific learning enhancements

- Hierarchical exploration for multi-level decisions
- Population-based training via checkpoint swapping
- Experience prioritization for rare events
- Curriculum learning for progressive difficulty
- Integration with Claude advisor for exploration
- Deliverables: Advanced learning features operational

### Week 6: Performance Optimization

**Objective**: Optimize for production performance targets

- JIT compilation with Numba for critical paths
- Vectorized batch processing
- GPU utilization optimization
- Memory pooling and object reuse
- Achieve 10,000+ steps/second target
- Deliverables: Optimized system meeting performance targets

### Week 7: Production Hardening

**Objective**: Prepare for production deployment

- Implement fault tolerance and recovery
- Add comprehensive monitoring and alerts
- Create operational runbooks
- Stress testing under memory pressure
- Circuit breakers for downstream failures
- Deliverables: Production-ready system

### Week 8: Integration and Handoff

**Objective**: Complete system integration and documentation

- End-to-end testing with all components
- Performance validation under combined load
- Complete API and architecture documentation
- Knowledge transfer sessions
- Final bug fixes and optimizations
- Deliverables: Fully integrated and documented system

## Integration Patterns

### Knowledge Graph Queries

Ray queries Memgraph for strategic knowledge:

```python
class KnowledgeGraphClient:
    async def get_joker_synergies(self, jokers: List[str]) -> Dict:
        query = """
        MATCH (j1:Joker)-[s:SYNERGIZES_WITH]->(j2:Joker)
        WHERE j1.name IN $jokers AND j2.name IN $jokers
        RETURN j1.name, j2.name, s.strength
        """
        return await self.graph_client.query(query, jokers=jokers)
```

### Claude Advisory Integration

Ray requests strategic advice for exploration:

```python
async def request_claude_advice(self, game_state, confidence_threshold=0.7):
    if self.decision_confidence < confidence_threshold:
        # Request advice via Event Bus
        advice_request = StrategyRequest(
            game_state=game_state,
            context="low_confidence_decision"
        )
        await self.event_bus.publish_and_wait(advice_request)
```

### Resource Coordination

Ray respects GPU and memory allocations:

```python
async def allocate_training_resources(self):
    gpu_grant = await self.resource_coordinator.request({
        'type': ResourceType.GPU_COMPUTE,
        'amount': 100,  # 100ms time slice
        'component': 'ray_training'
    })
    
    if gpu_grant.approved:
        with gpu_grant:
            await self.run_training_step()
```

## Risk Mitigation

### Technical Risks

**Memory Exhaustion** (High probability)
- Continuous monitoring with alerts at 80% usage
- Automatic checkpoint and restart mechanisms
- Graceful degradation to smaller batch sizes

**Event Bus Latency** (Medium probability)
- Local caching of recent decisions
- Fallback to direct gRPC for critical paths
- Adaptive timeout management

**GPU Contention** (Low probability)
- Cooperative scheduling via Resource Coordinator
- CPU-only fallback for inference
- Priority queue for training vs inference

## Success Metrics

### Performance Targets
- **Throughput**: 10,000+ environment steps/second sustained
- **Latency**: <100ms decision response (95th percentile)
- **Memory**: Stable operation within 8GB allocation
- **Integration**: <10ms Event Bus publish/subscribe overhead

### Learning Effectiveness
- Progress from random to competent play within 1000 games
- Successful discovery of documented joker synergies
- Novel strategy generation validated by Knowledge Graph
- <5% of decisions require Claude consultation

### System Reliability
- 99.9% uptime during 8-hour training sessions
- Automatic recovery from Event Bus disconnections
- Graceful handling of memory pressure
- Zero data loss during checkpointing

## Memory Management Strategy

### Allocation Breakdown (8GB Total)
- Ray Object Store: 2.5GB
- Worker Processes: 3.5GB
- Model Checkpoints: 1GB
- Operating Buffer: 1GB

### Optimization Techniques
- Compressed state representations (4:1 ratio)
- Gradient accumulation for small batches
- Automatic object eviction policies
- GPU offloading for training computation

## Key Deliverables

By Week 8:
- Fully integrated Ray RLlib system
- Event Bus consumer and producer implementation
- gRPC service for synchronous decisions
- Knowledge Graph integration for strategy persistence
- Claude advisory system integration
- Performance meeting all targets
- Comprehensive documentation

This plan provides a practical approach to building the learning orchestration system as part of the larger JimBot project, with clear integration points and realistic resource constraints.