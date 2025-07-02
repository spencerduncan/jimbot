# Deployment Guidelines for JimBot

This document provides Claude Code with guidance for deploying and scaling the JimBot system.

## Deployment Overview

JimBot is designed for single-workstation deployment with specific resource requirements:
- 32GB RAM total system memory
- NVIDIA RTX 3090 (24GB VRAM)
- Docker and Docker Compose for service orchestration
- Optional Kubernetes for production scaling

## Resource Allocation

### Memory Distribution
```yaml
System Components:
  System/OS: 6GB
  Memgraph: 12GB (10GB working + 2GB buffer)
  Ray/RLlib: 8GB
  Persistence (QuestDB + EventStore): 6GB
  
GPU Resources:
  Model Training: Up to 20GB VRAM
  Inference: ~4GB VRAM
```

### CPU Allocation
```yaml
Ray Workers: 2 cores
Memgraph: 2 cores  
Persistence: 1 core
MCP/API: 1 core
System: 2 cores
```

## Deployment Strategies

### Development Environment
- Docker Compose for all services
- Hot reload for Python components
- Shared volumes for model checkpoints
- Mock Claude API for testing

### Staging Environment
- Kubernetes with resource limits
- Persistent volumes for data
- Rate-limited Claude API access
- Performance monitoring enabled

### Production Environment
- Resource isolation via cgroups
- GPU scheduling for training/inference
- Automated backup strategies
- High availability for critical services

## Container Architecture

### Base Images
```dockerfile
# Python base for all Python services
FROM python:3.10-slim as python-base

# CUDA base for GPU-enabled services  
FROM nvidia/cuda:11.8.0-runtime-ubuntu22.04 as cuda-base
```

### Service Isolation
Each component runs in its own container:
- `jimbot-mcp`: WebSocket server and event aggregation
- `jimbot-memgraph`: Graph database (official image)
- `jimbot-ray-head`: Ray cluster head node
- `jimbot-ray-worker`: Ray worker nodes (GPU-enabled)
- `jimbot-claude`: Claude API gateway with rate limiting
- `jimbot-analytics`: Metrics aggregation and API
- `questdb`: Time-series metrics (official image)
- `eventstore`: Event sourcing (official image)

## Scaling Considerations

### Vertical Scaling (Current Design)
- Single powerful workstation
- Optimize memory usage per component
- GPU sharing between training and inference
- Efficient batch processing

### Horizontal Scaling (Future)
- Ray cluster across multiple nodes
- Memgraph read replicas
- Distributed Claude API calls
- Sharded event storage

### Bottleneck Mitigation
1. **Memory Pressure**
   - Enable Ray object spilling to disk
   - Implement Memgraph query result caching
   - Compress event payloads

2. **GPU Contention**
   - Time-slice GPU between training/inference
   - Queue training jobs during active play
   - Use smaller models for real-time inference

3. **API Rate Limits**
   - Aggressive response caching
   - Batch similar queries
   - Fallback to local strategies

## Deployment Workflow

### Initial Deployment
```bash
# 1. Build base images
docker-compose build base-images

# 2. Start infrastructure services
docker-compose up -d memgraph questdb eventstore

# 3. Initialize schemas and data
docker-compose run --rm jimbot-cli init-db

# 4. Start application services
docker-compose up -d

# 5. Verify health
docker-compose exec jimbot-cli health-check
```

### Rolling Updates
```bash
# 1. Build new images
docker-compose build jimbot-mcp jimbot-ray

# 2. Update services with zero downtime
docker-compose up -d --no-deps jimbot-mcp
docker-compose up -d --no-deps jimbot-ray-head

# 3. Drain and update workers
docker-compose exec jimbot-ray-head ray stop --workers-only
docker-compose up -d --no-deps jimbot-ray-worker
```

### Rollback Procedure
```bash
# 1. Stop problematic services
docker-compose stop jimbot-mcp

# 2. Restore previous version
docker-compose up -d jimbot-mcp:previous

# 3. Verify functionality
docker-compose exec jimbot-cli test-integration
```

## Monitoring & Observability

### Key Metrics to Track
```yaml
System:
  - Memory usage per container
  - GPU utilization and memory
  - CPU usage per service
  
Application:
  - MCP event processing latency
  - Memgraph query response times
  - Ray training throughput
  - Claude API usage and costs
  
Business:
  - Games played per hour
  - Win rate trends
  - Average ante reached
  - Strategy effectiveness
```

### Logging Strategy
- Structured JSON logging
- Centralized log aggregation
- Log levels: DEBUG (dev), INFO (staging), WARN (prod)
- Retention: 7 days (dev), 30 days (staging), 90 days (prod)

### Alerting Rules
```yaml
Critical:
  - Memory usage > 90% for 5 minutes
  - GPU memory exhausted
  - Service health check failures
  - Database connection failures

Warning:
  - Memory usage > 75% for 10 minutes
  - API rate limit approaching (>80%)
  - Training throughput < 500 games/hour
  - Query latency > 100ms (p95)
```

## Security Considerations

### Network Security
- Internal service communication only
- No external ports except MCP WebSocket
- TLS for all external connections
- API key rotation for Claude

### Data Security
- Encryption at rest for checkpoints
- Secure storage of API credentials
- Regular security updates for base images
- Principle of least privilege for service accounts

### Access Control
- Read-only database access for analytics
- Write permissions only for specific services
- Audit logging for all modifications
- Role-based access for management APIs

## Backup & Recovery

### Backup Strategy
```yaml
Continuous:
  - Ray model checkpoints (every hour)
  - Memgraph incremental backups
  
Daily:
  - Full Memgraph backup
  - QuestDB data export
  - EventStore snapshots
  
Weekly:
  - Complete system backup
  - Configuration backup
  - Docker image registry sync
```

### Recovery Procedures
1. **Service Failure**: Automatic restart with exponential backoff
2. **Data Corruption**: Restore from latest clean backup
3. **Complete System Failure**: Rebuild from infrastructure as code

## Performance Optimization

### Container Optimization
- Use slim base images
- Multi-stage builds for smaller images
- Compile Python bytecode in images
- Enable BuildKit cache mounts

### Resource Optimization
- CPU pinning for critical services
- NUMA-aware memory allocation
- GPU memory pooling
- Connection pooling for databases

### Startup Optimization
- Lazy loading of models
- Parallel service initialization
- Health check dependencies
- Graceful degradation

## Deployment Checklist

### Pre-deployment
- [ ] Resource requirements verified
- [ ] All tests passing
- [ ] Security scan completed
- [ ] Backup verified
- [ ] Rollback plan documented

### Deployment
- [ ] Services started in correct order
- [ ] Health checks passing
- [ ] Metrics flowing
- [ ] Logs accessible
- [ ] API endpoints responding

### Post-deployment
- [ ] Performance metrics normal
- [ ] No error spikes in logs
- [ ] Memory usage stable
- [ ] GPU utilization appropriate
- [ ] Business metrics tracking

## Troubleshooting Guide

### Common Issues

**Memory Exhaustion**
```bash
# Check memory usage
docker stats --no-stream

# Identify memory leaks
docker-compose exec jimbot-ray-head ray memory

# Emergency memory release
docker-compose restart jimbot-ray-worker
```

**GPU Issues**
```bash
# Check GPU status
nvidia-smi

# Reset GPU
nvidia-smi --gpu-reset

# Verify CUDA in container
docker-compose exec jimbot-ray-worker nvidia-smi
```

**Service Communication**
```bash
# Test internal DNS
docker-compose exec jimbot-mcp ping memgraph

# Check service logs
docker-compose logs -f jimbot-mcp

# Verify port bindings
docker-compose ps
```

## Cost Optimization

### Resource Usage
- Schedule training during off-peak hours
- Implement request batching for Claude API
- Use spot instances for non-critical workers
- Enable compression for event storage

### Monitoring Costs
- Track Claude API token usage
- Monitor storage growth rates
- Calculate per-game infrastructure cost
- Set budget alerts

## Future Considerations

### Multi-node Deployment
- Kubernetes operator for JimBot
- Distributed Ray cluster
- Memgraph Enterprise clustering
- Multi-region Claude API access

### Edge Deployment
- Lightweight inference-only mode
- Local strategy cache
- Reduced memory footprint
- Offline operation capability