# Docker & Docker Compose Best Practices for JimBot

This guide defines Docker and Docker Compose conventions for the JimBot project's multi-service ML architecture.

## Table of Contents
1. [General Principles](#general-principles)
2. [Dockerfile Best Practices](#dockerfile-best-practices)
3. [Docker Compose Patterns](#docker-compose-patterns)
4. [Volume Management](#volume-management)
5. [Networking](#networking)
6. [Resource Management](#resource-management)
7. [Development vs Production](#development-vs-production)
8. [Health Checks](#health-checks)
9. [Security](#security)
10. [GPU Support](#gpu-support)

## General Principles

### Core Guidelines
- **One process per container** - Each service runs independently
- **Immutable infrastructure** - Containers are disposable
- **12-Factor App principles** - Configuration via environment
- **Minimal base images** - Alpine or distroless when possible
- **Layer caching optimization** - Order matters in Dockerfiles

### Project Structure
```
jimbot/
├── docker/
│   ├── services/
│   │   ├── memgraph/
│   │   │   ├── Dockerfile
│   │   │   └── config/
│   │   ├── ray/
│   │   │   ├── Dockerfile
│   │   │   └── entrypoint.sh
│   │   └── app/
│   │       ├── Dockerfile
│   │       └── requirements.txt
│   └── scripts/
│       ├── wait-for-it.sh
│       └── health-check.sh
├── docker-compose.yml
├── docker-compose.dev.yml
├── docker-compose.prod.yml
└── .env.example
```

## Dockerfile Best Practices

### Multi-Stage Build Pattern
```dockerfile
# docker/services/app/Dockerfile
# Build stage
FROM python:3.9-slim AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Runtime stage
FROM python:3.9-slim

# Install runtime dependencies only
RUN apt-get update && apt-get install -y \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Create non-root user
RUN useradd -m -u 1000 jimbot
USER jimbot

# Copy application code
WORKDIR /app
COPY --chown=jimbot:jimbot . .

# Set Python environment
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000
CMD ["python", "-m", "jimbot.main"]
```

### GPU-Enabled Dockerfile
```dockerfile
# docker/services/ray/Dockerfile
FROM nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04

# Install Python and Ray
RUN apt-get update && apt-get install -y \
    python3.9 python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Install Ray with GPU support
RUN pip3 install --no-cache-dir \
    ray[default,tune]==2.9.0 \
    torch==2.0.1 \
    torchvision==0.15.2

# Configure Ray
ENV RAY_USE_MULTIPROCESSING_CPU_COUNT=1
ENV OMP_NUM_THREADS=1

WORKDIR /app
CMD ["ray", "start", "--head", "--port=6379", "--dashboard-host=0.0.0.0"]
```

### Memgraph with Custom Modules
```dockerfile
# docker/services/memgraph/Dockerfile
FROM memgraph/memgraph-mage:latest

# Copy custom MAGE modules
COPY mage_modules/ /usr/lib/memgraph/query_modules/

# Copy configuration
COPY memgraph.conf /etc/memgraph/memgraph.conf

# Create volume directories
RUN mkdir -p /var/lib/memgraph /var/log/memgraph

VOLUME ["/var/lib/memgraph", "/var/log/memgraph"]
EXPOSE 7687 3000

CMD ["memgraph", "--config", "/etc/memgraph/memgraph.conf"]
```

## Docker Compose Patterns

### Base Configuration
```yaml
# docker-compose.yml
version: '3.9'

x-common-variables: &common-variables
  LOG_LEVEL: ${LOG_LEVEL:-info}
  ENVIRONMENT: ${ENVIRONMENT:-development}

services:
  # Knowledge Graph Database
  memgraph:
    build:
      context: ./docker/services/memgraph
      dockerfile: Dockerfile
    container_name: jimbot-memgraph
    restart: unless-stopped
    ports:
      - "7687:7687"  # Bolt protocol
      - "3000:3000"  # Memgraph Lab
    volumes:
      - memgraph_data:/var/lib/memgraph
      - ./mage_modules:/mage_modules:ro
    environment:
      <<: *common-variables
      MEMGRAPH_LOG_LEVEL: INFO
      MEMGRAPH_MEMORY_LIMIT: 12G
    deploy:
      resources:
        limits:
          memory: 12G
        reservations:
          memory: 10G
    healthcheck:
      test: ["CMD", "echo", "MATCH (n) RETURN n LIMIT 1;", "|", "mgconsole"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    networks:
      - data_network
      - backend_network

  # Time-Series Database
  questdb:
    image: questdb/questdb:7.3
    container_name: jimbot-questdb
    restart: unless-stopped
    ports:
      - "9000:9000"  # HTTP API
      - "8812:8812"  # PostgreSQL wire protocol
      - "9009:9009"  # InfluxDB line protocol
    volumes:
      - questdb_data:/var/lib/questdb
    environment:
      <<: *common-variables
      QDB_LOG_LEVEL: INFO
      QDB_SHARED_WORKER_COUNT: 2
      QDB_CAIRO_MAX_UNCOMMITTED_ROWS: 100000
    deploy:
      resources:
        limits:
          memory: 4G
        reservations:
          memory: 3G
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/exec?query=SELECT%201"]
      interval: 30s
      timeout: 10s
      retries: 3
    networks:
      - data_network
      - monitoring_network

  # Event Store
  eventstore:
    image: eventstore/eventstore:23.10.0-bookworm-slim
    container_name: jimbot-eventstore
    restart: unless-stopped
    ports:
      - "2113:2113"  # HTTP API & UI
      - "1113:1113"  # TCP
    volumes:
      - eventstore_data:/var/lib/eventstore
      - eventstore_logs:/var/log/eventstore
    environment:
      <<: *common-variables
      EVENTSTORE_CLUSTER_SIZE: 1
      EVENTSTORE_RUN_PROJECTIONS: All
      EVENTSTORE_START_STANDARD_PROJECTIONS: true
      EVENTSTORE_EXT_TCP_PORT: 1113
      EVENTSTORE_HTTP_PORT: 2113
      EVENTSTORE_INSECURE: ${EVENTSTORE_INSECURE:-false}
      EVENTSTORE_ENABLE_ATOM_PUB_OVER_HTTP: true
    deploy:
      resources:
        limits:
          memory: 2G
        reservations:
          memory: 1G
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:2113/health/live"]
      interval: 30s
      timeout: 10s
      retries: 3
    networks:
      - data_network
      - backend_network

  # Ray Head Node
  ray-head:
    build:
      context: ./docker/services/ray
      dockerfile: Dockerfile
    container_name: jimbot-ray-head
    restart: unless-stopped
    shm_size: 2G  # Shared memory for Ray object store
    ports:
      - "6379:6379"    # Ray port
      - "8265:8265"    # Ray dashboard
      - "10001:10001"  # Client port
    volumes:
      - ray_data:/tmp/ray
      - ./jimbot:/app/jimbot:ro
    environment:
      <<: *common-variables
      RAY_HEAD_SERVICE_HOST: ray-head
      RAY_HEAD_SERVICE_PORT: 6379
      RAY_OBJECT_STORE_MEMORY: 2147483648  # 2GB
      CUDA_VISIBLE_DEVICES: 0
    deploy:
      resources:
        limits:
          memory: 8G
          cpus: '4'
        reservations:
          memory: 6G
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    healthcheck:
      test: ["CMD", "ray", "status"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s
    networks:
      - backend_network
      - compute_network

  # JimBot Application
  app:
    build:
      context: .
      dockerfile: docker/services/app/Dockerfile
      args:
        PYTHON_VERSION: 3.9
    container_name: jimbot-app
    restart: unless-stopped
    ports:
      - "8000:8000"  # MCP server
    volumes:
      - ./jimbot:/app/jimbot:ro
      - ./config:/app/config:ro
      - app_logs:/app/logs
    environment:
      <<: *common-variables
      # Service endpoints
      MEMGRAPH_HOST: memgraph
      MEMGRAPH_PORT: 7687
      QUESTDB_HOST: questdb
      QUESTDB_PORT: 8812
      EVENTSTORE_HOST: eventstore
      EVENTSTORE_PORT: 2113
      RAY_ADDRESS: ray-head:6379
      # Claude AI
      ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY}
      CLAUDE_RATE_LIMIT: 100
    depends_on:
      memgraph:
        condition: service_healthy
      questdb:
        condition: service_healthy
      eventstore:
        condition: service_healthy
      ray-head:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    networks:
      - frontend_network
      - backend_network

volumes:
  memgraph_data:
    driver: local
  questdb_data:
    driver: local
  eventstore_data:
    driver: local
  eventstore_logs:
    driver: local
  ray_data:
    driver: local
  app_logs:
    driver: local

networks:
  frontend_network:
    driver: bridge
  backend_network:
    driver: bridge
    internal: true
  data_network:
    driver: bridge
    internal: true
  compute_network:
    driver: bridge
    internal: true
  monitoring_network:
    driver: bridge
```

## Volume Management

### Named Volumes for Persistence
```yaml
volumes:
  # Database volumes
  memgraph_data:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /data/jimbot/memgraph
  
  questdb_data:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /data/jimbot/questdb
```

### Development Bind Mounts
```yaml
# docker-compose.dev.yml
services:
  app:
    volumes:
      - ./jimbot:/app/jimbot:rw  # Hot reload
      - ./tests:/app/tests:ro
      - ./scripts:/app/scripts:ro
```

### Temporary Volumes
```yaml
services:
  ray-head:
    tmpfs:
      - /tmp/ray:size=2G  # In-memory for performance
```

## Networking

### Network Segmentation
```yaml
networks:
  # External-facing services
  frontend_network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/24
  
  # Internal service communication
  backend_network:
    driver: bridge
    internal: true
    ipam:
      config:
        - subnet: 172.21.0.0/24
  
  # Database layer
  data_network:
    driver: bridge
    internal: true
    ipam:
      config:
        - subnet: 172.22.0.0/24
```

### Service Discovery
```yaml
services:
  app:
    environment:
      # Use service names for internal communication
      MEMGRAPH_HOST: memgraph
      QUESTDB_HOST: questdb
    extra_hosts:
      - "host.docker.internal:host-gateway"
```

## Resource Management

### Memory Allocation Strategy
```yaml
# Total system: 32GB
# Reserved for OS: 6GB
# Available: 26GB

services:
  memgraph:
    deploy:
      resources:
        limits:
          memory: 12G
        reservations:
          memory: 10G
  
  ray-head:
    deploy:
      resources:
        limits:
          memory: 8G
          cpus: '4'
        reservations:
          memory: 6G
  
  questdb:
    deploy:
      resources:
        limits:
          memory: 4G
        reservations:
          memory: 3G
  
  eventstore:
    deploy:
      resources:
        limits:
          memory: 2G
        reservations:
          memory: 1G
```

### GPU Allocation
```yaml
services:
  ray-head:
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
              device_ids: ['0']  # Specific GPU
```

## Development vs Production

### Development Overrides
```yaml
# docker-compose.dev.yml
services:
  memgraph:
    ports:
      - "7444:7444"  # Debug port
    environment:
      MEMGRAPH_LOG_LEVEL: DEBUG
    command: ["memgraph", "--log-level=DEBUG", "--also-log-to-stderr"]
  
  app:
    build:
      target: development  # Dev stage with debugging tools
    volumes:
      - ./jimbot:/app/jimbot:rw
    environment:
      DEBUG: "true"
      RELOAD: "true"
    command: ["python", "-m", "debugpy", "--listen", "0.0.0.0:5678", "-m", "jimbot.main"]
```

### Production Configuration
```yaml
# docker-compose.prod.yml
services:
  memgraph:
    restart: always
    environment:
      MEMGRAPH_SSL_CERT: /certs/cert.pem
      MEMGRAPH_SSL_KEY: /certs/key.pem
    volumes:
      - ./certs:/certs:ro
  
  app:
    restart: always
    environment:
      ENVIRONMENT: production
      LOG_LEVEL: warning
    deploy:
      replicas: 2
      update_config:
        parallelism: 1
        delay: 10s
        order: start-first
```

## Health Checks

### Service-Specific Health Checks
```yaml
services:
  memgraph:
    healthcheck:
      test: ["CMD", "echo", "MATCH (n) RETURN n LIMIT 1;", "|", "mgconsole"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
  
  questdb:
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/exec?query=SELECT%201"]
      interval: 30s
      timeout: 10s
      retries: 3
  
  ray-head:
    healthcheck:
      test: ["CMD", "ray", "status"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 60s  # Ray takes time to start
```

### Custom Health Check Script
```bash
#!/bin/bash
# docker/scripts/health-check.sh
set -e

# Check if service is responding
response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health)

if [ "$response" -eq 200 ]; then
    exit 0
else
    exit 1
fi
```

## Security

### Secrets Management
```yaml
# docker-compose.yml
services:
  app:
    environment:
      ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY}
    secrets:
      - db_password
      - api_keys

secrets:
  db_password:
    file: ./secrets/db_password.txt
  api_keys:
    file: ./secrets/api_keys.json
```

### Security Best Practices
```dockerfile
# Run as non-root user
RUN useradd -m -u 1000 jimbot
USER jimbot

# Don't expose unnecessary ports
EXPOSE 8000

# Use read-only root filesystem
# docker-compose.yml
services:
  app:
    read_only: true
    tmpfs:
      - /tmp
      - /var/run
```

### Network Security
```yaml
networks:
  # Internal networks for sensitive services
  data_network:
    internal: true
  
  # Frontend with restricted access
  frontend_network:
    driver: bridge
    driver_opts:
      com.docker.network.bridge.enable_icc: "false"
```

## GPU Support

### NVIDIA Docker Configuration
```yaml
# Ensure nvidia-docker2 is installed
# Add to /etc/docker/daemon.json:
# {
#   "default-runtime": "nvidia",
#   "runtimes": {
#     "nvidia": {
#       "path": "nvidia-container-runtime",
#       "runtimeArgs": []
#     }
#   }
# }

services:
  ray-head:
    runtime: nvidia
    environment:
      NVIDIA_VISIBLE_DEVICES: all
      NVIDIA_DRIVER_CAPABILITIES: compute,utility
      CUDA_VISIBLE_DEVICES: 0
```

### Multi-GPU Support
```yaml
services:
  ray-worker-gpu-0:
    extends: ray-head
    environment:
      CUDA_VISIBLE_DEVICES: 0
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              device_ids: ['0']
              capabilities: [gpu]
  
  ray-worker-gpu-1:
    extends: ray-head
    environment:
      CUDA_VISIBLE_DEVICES: 1
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              device_ids: ['1']
              capabilities: [gpu]
```

## Deployment Commands

### Development
```bash
# Start all services
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d

# View logs
docker-compose logs -f app

# Rebuild specific service
docker-compose build --no-cache app
```

### Production
```bash
# Deploy with production settings
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Rolling update
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d --no-deps --scale app=2 app

# Backup volumes
docker run --rm -v jimbot_memgraph_data:/data -v $(pwd):/backup alpine tar czf /backup/memgraph_backup.tar.gz -C /data .
```

### Monitoring
```bash
# Check resource usage
docker stats

# Inspect service health
docker-compose ps

# View service logs
docker-compose logs --tail=100 -f memgraph
```

## Best Practices Summary

1. **Use multi-stage builds** to minimize image size
2. **Order Dockerfile commands** for optimal caching
3. **Run services as non-root** users
4. **Define health checks** for all services
5. **Use named volumes** for persistent data
6. **Segment networks** by service tier
7. **Set resource limits** to prevent memory issues
8. **Use environment-specific** compose files
9. **Implement proper secrets** management
10. **Monitor and log** all services