# Docker and Docker Compose Best Practices for Machine Learning Projects

## Table of Contents

1. [Dockerfile Best Practices](#dockerfile-best-practices)
2. [Docker Compose Patterns](#docker-compose-patterns)
3. [Volume Management and Data Persistence](#volume-management-and-data-persistence)
4. [Networking Between Services](#networking-between-services)
5. [Resource Limits and Constraints](#resource-limits-and-constraints)
6. [Development vs Production Configurations](#development-vs-production-configurations)
7. [Health Checks and Restart Policies](#health-checks-and-restart-policies)
8. [Secrets Management](#secrets-management)
9. [Container Orchestration Patterns](#container-orchestration-patterns)
10. [GPU Support for ML Workloads](#gpu-support-for-ml-workloads)
11. [Service-Specific Configurations](#service-specific-configurations)

## 1. Dockerfile Best Practices

### Multi-Stage Builds for ML Projects

Multi-stage builds can significantly reduce container size. For ML projects,
this is crucial as dependencies like TensorFlow, PyTorch, and scientific
libraries can be large.

```dockerfile
# Stage 1: Build stage with full development dependencies
FROM python:3.10-slim AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: Runtime stage with minimal dependencies
FROM python:3.10-slim AS runtime

# Install only runtime dependencies
RUN apt-get update && apt-get install -y \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code
WORKDIR /app
COPY . .

# Run application
CMD ["python", "main.py"]
```

### GPU-Enabled Dockerfile

```dockerfile
# Use NVIDIA CUDA base image
FROM nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04 AS base

# Install Python
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Stage for building with GPU support
FROM base AS builder

# Install build tools
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install ML frameworks with GPU support
RUN pip3 install --no-cache-dir \
    torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118 \
    tensorflow[and-cuda] \
    ray[default]

# Final stage
FROM base AS runtime

# Copy installed packages
COPY --from=builder /usr/local/lib/python3.10/dist-packages /usr/local/lib/python3.10/dist-packages

WORKDIR /app
COPY . .

CMD ["python3", "train.py"]
```

### Caching Best Practices

```dockerfile
# Bad: Copying everything before installing dependencies
COPY . .
RUN pip install -r requirements.txt

# Good: Copy only requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
```

## 2. Docker Compose Patterns

### Multi-Service ML Application

```yaml
version: '3.8'

services:
  # Ray head node
  ray-head:
    build:
      context: .
      dockerfile: Dockerfile.ray
    container_name: ray-head
    ports:
      - '8265:8265' # Ray dashboard
      - '6379:6379' # Ray GCS
      - '10001:10001' # Ray client
    environment:
      - RAY_HEAD_SERVICE_HOST=ray-head
    command: ray start --head --dashboard-host 0.0.0.0
    deploy:
      resources:
        limits:
          cpus: '4'
          memory: 8G
        reservations:
          cpus: '2'
          memory: 4G
    networks:
      - ml-network
    volumes:
      - ray-data:/tmp/ray
      - ./models:/models
    healthcheck:
      test: ['CMD', 'ray', 'status']
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  # Ray worker node
  ray-worker:
    build:
      context: .
      dockerfile: Dockerfile.ray
    depends_on:
      ray-head:
        condition: service_healthy
    environment:
      - RAY_HEAD_SERVICE_HOST=ray-head
    command: ray start --address ray-head:6379
    deploy:
      replicas: 2
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    networks:
      - ml-network
    volumes:
      - ./models:/models

  # Memgraph database
  memgraph:
    image: memgraph/memgraph-platform:latest
    container_name: memgraph
    ports:
      - '7687:7687' # Bolt protocol
      - '3000:3000' # Memgraph Lab
    environment:
      - MEMGRAPH_USER=memgraph
      - MEMGRAPH_PASSWORD=password
    volumes:
      - memgraph-data:/var/lib/memgraph
      - memgraph-log:/var/log/memgraph
      - ./memgraph.conf:/etc/memgraph/memgraph.conf
    deploy:
      resources:
        limits:
          cpus: '4'
          memory: 12G
        reservations:
          cpus: '2'
          memory: 10G
    networks:
      - ml-network
    healthcheck:
      test:
        [
          'CMD',
          'mg_client',
          '-u',
          'memgraph',
          '-p',
          'password',
          '--output-format=csv',
          '--execute',
          'RETURN 1',
        ]
      interval: 30s
      timeout: 10s
      retries: 3

  # QuestDB for time-series metrics
  questdb:
    image: questdb/questdb:latest
    container_name: questdb
    ports:
      - '9000:9000' # REST API & Web Console
      - '8812:8812' # PostgreSQL wire protocol
      - '9009:9009' # InfluxDB line protocol
    environment:
      - QDB_CAIRO_COMMIT_LAG=1000
      - QDB_CAIRO_MAX_UNCOMMITTED_ROWS=100000
      - QDB_LINE_TCP_MAINTENANCE_JOB_INTERVAL=5m
    volumes:
      - questdb-data:/var/lib/questdb
      - ./questdb.conf:/etc/questdb/server.conf
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G
    networks:
      - ml-network
    healthcheck:
      test: ['CMD', 'curl', '-f', 'http://localhost:9000']
      interval: 30s
      timeout: 10s
      retries: 3

  # EventStoreDB for event sourcing
  eventstore:
    image: eventstore/eventstore:latest
    container_name: eventstore
    ports:
      - '2113:2113' # HTTP API & UI
      - '1113:1113' # TCP
    environment:
      - EVENTSTORE_CLUSTER_SIZE=1
      - EVENTSTORE_RUN_PROJECTIONS=All
      - EVENTSTORE_START_STANDARD_PROJECTIONS=true
      - EVENTSTORE_INSECURE=true # Only for development
      - EVENTSTORE_ENABLE_ATOM_PUB_OVER_HTTP=true
    volumes:
      - eventstore-data:/var/lib/eventstore
      - eventstore-logs:/var/log/eventstore
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 2G
        reservations:
          cpus: '0.5'
          memory: 1G
    networks:
      - ml-network
    healthcheck:
      test: ['CMD', 'curl', '-f', 'http://localhost:2113/health/live']
      interval: 30s
      timeout: 10s
      retries: 3

  # ML training service
  ml-training:
    build:
      context: .
      dockerfile: Dockerfile.training
    depends_on:
      - ray-head
      - memgraph
      - questdb
    environment:
      - RAY_ADDRESS=ray://ray-head:10001
      - MEMGRAPH_HOST=memgraph
      - QUESTDB_HOST=questdb
      - CUDA_VISIBLE_DEVICES=0
    volumes:
      - ./src:/app/src
      - ./models:/models
      - training-cache:/cache
    deploy:
      resources:
        limits:
          cpus: '4'
          memory: 8G
        reservations:
          cpus: '2'
          memory: 4G
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    networks:
      - ml-network
    restart: unless-stopped

networks:
  ml-network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16

volumes:
  ray-data:
  memgraph-data:
  memgraph-log:
  questdb-data:
  eventstore-data:
  eventstore-logs:
  training-cache:
```

## 3. Volume Management and Data Persistence

### Best Practices for ML Data

```yaml
volumes:
  # Named volumes for databases
  memgraph-data:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /data/memgraph

  # Model storage with backup
  models:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /data/models
    labels:
      backup: 'daily'

  # Training datasets
  datasets:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /data/datasets
    labels:
      readonly: 'true'

  # Shared memory for Ray
  ray-shm:
    driver: local
    driver_opts:
      type: tmpfs
      device: tmpfs
      o: size=2g
```

### Volume Configuration for Services

```yaml
services:
  ml-service:
    volumes:
      # Read-only dataset mount
      - datasets:/data:ro
      # Model output with specific permissions
      - models:/models:rw
      # Temporary cache
      - type: tmpfs
        target: /tmp
        tmpfs:
          size: 1G
      # Config files
      - type: bind
        source: ./config
        target: /app/config
        read_only: true
```

## 4. Networking Between Services

### Custom Network Configuration

```yaml
networks:
  # Frontend network for external access
  frontend:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/24

  # Backend network for internal services
  backend:
    driver: bridge
    internal: true
    ipam:
      config:
        - subnet: 172.21.0.0/24

  # Data network for database communication
  data:
    driver: bridge
    internal: true
    ipam:
      config:
        - subnet: 172.22.0.0/24
```

### Service Discovery Pattern

```yaml
services:
  api:
    networks:
      - frontend
      - backend
    environment:
      - DB_HOST=postgres
      - CACHE_HOST=redis
      - ML_SERVICE=ml-inference

  ml-inference:
    networks:
      - backend
      - data
    environment:
      - MODEL_REGISTRY=memgraph
      - METRICS_DB=questdb
```

## 5. Resource Limits and Constraints

### CPU and Memory Limits

```yaml
services:
  ml-training:
    deploy:
      resources:
        limits:
          cpus: '4.0'
          memory: 16G
        reservations:
          cpus: '2.0'
          memory: 8G
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]

  ray-worker:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 8G
        reservations:
          cpus: '1.0'
          memory: 4G
    # Ray-specific shared memory
    shm_size: 2g
```

### Resource Allocation Strategy

```yaml
# Total system: 32GB RAM, 8 CPU cores, 1 GPU
services:
  # High-priority services with guaranteed resources
  memgraph:
    deploy:
      resources:
        limits:
          cpus: '4'
          memory: 12G
        reservations:
          cpus: '2'
          memory: 10G # 2GB safety margin

  # Elastic services that can scale
  ray-cluster:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 8G
        reservations:
          cpus: '1'
          memory: 4G

  # Low-priority services
  monitoring:
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 512M
```

## 6. Development vs Production Configurations

### Base Configuration (docker-compose.yml)

```yaml
version: '3.8'

services:
  app:
    image: ${APP_IMAGE:-ml-app:latest}
    environment:
      - ENV=${ENV:-development}
      - LOG_LEVEL=${LOG_LEVEL:-info}
    networks:
      - default
```

### Development Override (docker-compose.dev.yml)

```yaml
version: '3.8'

services:
  app:
    build:
      context: .
      target: development
    volumes:
      - .:/app
      - /app/node_modules
    environment:
      - ENV=development
      - LOG_LEVEL=debug
      - DEBUG=true
    ports:
      - '5678:5678' # Python debugger
    command: python -m debugpy --listen 0.0.0.0:5678 main.py

  memgraph:
    environment:
      - MEMGRAPH_TELEMETRY_ENABLED=false
    ports:
      - '3000:3000' # Memgraph Lab

  questdb:
    ports:
      - '9000:9000' # Web console

  eventstore:
    environment:
      - EVENTSTORE_INSECURE=true
```

### Production Override (docker-compose.prod.yml)

```yaml
version: '3.8'

services:
  app:
    image: ml-app:${VERSION}
    environment:
      - ENV=production
      - LOG_LEVEL=warning
    deploy:
      replicas: 3
      restart_policy:
        condition: any
        delay: 5s
        max_attempts: 3
      update_config:
        parallelism: 1
        delay: 10s
        failure_action: rollback

  memgraph:
    environment:
      - MEMGRAPH_SSL_CERT=/etc/ssl/certs/cert.pem
      - MEMGRAPH_SSL_KEY=/etc/ssl/private/key.pem
    volumes:
      - ./certs:/etc/ssl:ro
    deploy:
      resources:
        limits:
          cpus: '4'
          memory: 12G

  eventstore:
    environment:
      - EVENTSTORE_INSECURE=false
      - EVENTSTORE_CERTIFICATE=/etc/eventstore/certs/node.crt
      - EVENTSTORE_CERTIFICATE_PRIVATE_KEY=/etc/eventstore/certs/node.key
```

### Running Different Configurations

```bash
# Development
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up

# Production
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# With environment file
docker-compose --env-file .env.production -f docker-compose.yml -f docker-compose.prod.yml up -d
```

## 7. Health Checks and Restart Policies

### Comprehensive Health Checks

```yaml
services:
  ml-api:
    healthcheck:
      test: ['CMD', 'curl', '-f', 'http://localhost:8080/health']
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    restart: unless-stopped

  ray-head:
    healthcheck:
      test: ['CMD', 'ray', 'status']
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s
    restart: on-failure:5

  memgraph:
    healthcheck:
      test: |
        CMD mg_client -u memgraph -p password \
        --output-format=csv --execute "MATCH (n) RETURN count(n) LIMIT 1"
      interval: 30s
      timeout: 10s
      retries: 3
    restart: always

  questdb:
    healthcheck:
      test: ['CMD', 'curl', '-f', 'http://localhost:9000']
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped
    depends_on:
      - volumes-init
```

### Restart Policies

```yaml
services:
  # Critical services - always restart
  database:
    restart: always
    deploy:
      restart_policy:
        condition: any
        delay: 5s

  # Development services - restart on failure only
  ml-notebook:
    restart: on-failure:3
    deploy:
      restart_policy:
        condition: on-failure
        delay: 5s
        max_attempts: 3

  # Batch jobs - no restart
  data-migration:
    restart: 'no'
    deploy:
      restart_policy:
        condition: none
```

## 8. Secrets Management

### Docker Secrets Configuration

```yaml
version: '3.8'

secrets:
  db_password:
    file: ./secrets/db_password.txt
  api_key:
    file: ./secrets/api_key.txt
  ssl_cert:
    file: ./certs/server.crt
  ssl_key:
    file: ./certs/server.key

services:
  app:
    secrets:
      - db_password
      - api_key
    environment:
      - DB_PASSWORD_FILE=/run/secrets/db_password
      - API_KEY_FILE=/run/secrets/api_key

  memgraph:
    secrets:
      - db_password
      - ssl_cert
      - ssl_key
    environment:
      - MEMGRAPH_PASSWORD_FILE=/run/secrets/db_password
      - MEMGRAPH_SSL_CERT=/run/secrets/ssl_cert
      - MEMGRAPH_SSL_KEY=/run/secrets/ssl_key
```

### Environment-Based Secrets

```yaml
# .env.example
CLAUDE_API_KEY=your_api_key_here
DB_PASSWORD=your_password_here
MEMGRAPH_PASSWORD=your_password_here

# docker-compose.yml
services:
  ml-service:
    environment:
      - CLAUDE_API_KEY=${CLAUDE_API_KEY}
      - DB_PASSWORD=${DB_PASSWORD}
```

## 9. Container Orchestration Patterns

### Service Dependencies and Startup Order

```yaml
services:
  # Initialize volumes and configurations
  init-volumes:
    image: busybox
    volumes:
      - memgraph-data:/data/memgraph
      - questdb-data:/data/questdb
    command: |
      sh -c "
        mkdir -p /data/memgraph /data/questdb
        chmod 755 /data/memgraph /data/questdb
      "

  # Database tier
  memgraph:
    depends_on:
      init-volumes:
        condition: service_completed_successfully

  questdb:
    depends_on:
      init-volumes:
        condition: service_completed_successfully

  # Application tier
  ray-head:
    depends_on:
      memgraph:
        condition: service_healthy
      questdb:
        condition: service_healthy

  ml-training:
    depends_on:
      ray-head:
        condition: service_healthy
```

### Rolling Updates Pattern

```yaml
services:
  ml-api:
    deploy:
      replicas: 3
      update_config:
        parallelism: 1
        delay: 10s
        failure_action: rollback
        monitor: 30s
        max_failure_ratio: 0.3
      rollback_config:
        parallelism: 1
        delay: 10s
```

## 10. GPU Support for ML Workloads

### NVIDIA Docker Configuration

```yaml
services:
  ml-training:
    build:
      context: .
      dockerfile: Dockerfile.gpu
    runtime: nvidia
    environment:
      - NVIDIA_VISIBLE_DEVICES=all
      - NVIDIA_DRIVER_CAPABILITIES=compute,utility
      - CUDA_VISIBLE_DEVICES=0
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]

  # Multi-GPU configuration
  ml-distributed:
    runtime: nvidia
    environment:
      - NVIDIA_VISIBLE_DEVICES=0,1
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 2
              capabilities: [gpu]
```

### GPU-Optimized Dockerfile

```dockerfile
FROM nvidia/cuda:11.8.0-cudnn8-devel-ubuntu22.04

# Install Python and dependencies
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Install PyTorch with CUDA support
RUN pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# Install other ML libraries
RUN pip3 install \
    tensorflow[and-cuda] \
    jax[cuda11_pip] \
    -f https://storage.googleapis.com/jax-releases/jax_cuda_releases.html

WORKDIR /app
COPY . .

CMD ["python3", "train_gpu.py"]
```

## 11. Service-Specific Configurations

### Memgraph Configuration

```yaml
memgraph:
  image: memgraph/memgraph-platform:latest
  ports:
    - '7687:7687'
    - '3000:3000'
  environment:
    - MEMGRAPH_USER=memgraph
    - MEMGRAPH_PASSWORD=${MEMGRAPH_PASSWORD}
    - MEMGRAPH_STORAGE_MODE=IN_MEMORY_TRANSACTIONAL
    - MEMGRAPH_TELEMETRY_ENABLED=false
    - MEMGRAPH_LOG_LEVEL=WARNING
    - MEMGRAPH_MEMORY_LIMIT=10GB
    - MEMGRAPH_QUERY_TIMEOUT=300s
  volumes:
    - memgraph-data:/var/lib/memgraph
    - memgraph-log:/var/log/memgraph
    - ./memgraph/memgraph.conf:/etc/memgraph/memgraph.conf:ro
  command: ['--log-level=WARNING', '--also-log-to-stderr']
```

### QuestDB Configuration

```yaml
questdb:
  image: questdb/questdb:latest
  ports:
    - '9000:9000' # REST API & Web Console
    - '8812:8812' # PostgreSQL wire protocol
    - '9009:9009' # InfluxDB line protocol
  environment:
    - QDB_CAIRO_COMMIT_LAG=1000
    - QDB_CAIRO_MAX_UNCOMMITTED_ROWS=100000
    - QDB_LINE_TCP_MAINTENANCE_JOB_INTERVAL=5m
    - QDB_PG_ENABLED=true
    - QDB_PG_NET_BIND_TO=0.0.0.0:8812
    - QDB_HTTP_MIN_ENABLED=false
    - QDB_TELEMETRY_ENABLED=false
  volumes:
    - questdb-data:/var/lib/questdb
    - ./questdb/server.conf:/etc/questdb/server.conf:ro
```

### EventStoreDB Configuration

```yaml
eventstore:
  image: eventstore/eventstore:latest
  ports:
    - '2113:2113'
    - '1113:1113'
  environment:
    - EVENTSTORE_CLUSTER_SIZE=1
    - EVENTSTORE_RUN_PROJECTIONS=All
    - EVENTSTORE_START_STANDARD_PROJECTIONS=true
    - EVENTSTORE_MEM_DB_SIZE=2GB
    - EVENTSTORE_CHUNK_CACHE_SIZE=536870912
    - EVENTSTORE_STATS_PERIOD_SEC=300
    - EVENTSTORE_INSECURE=${EVENTSTORE_INSECURE:-false}
  volumes:
    - eventstore-data:/var/lib/eventstore
    - eventstore-logs:/var/log/eventstore
```

### Ray Cluster Configuration

```yaml
ray-head:
  build:
    context: .
    dockerfile: Dockerfile.ray
  ports:
    - '8265:8265' # Dashboard
    - '6379:6379' # GCS
    - '10001:10001' # Client
  environment:
    - RAY_HEAD_SERVICE_HOST=ray-head
    - RAY_REDIS_PASSWORD=${RAY_REDIS_PASSWORD}
    - RAY_PROMETHEUS_HOST=prometheus
    - RAY_METRICS_EXPORT_PORT=8080
  command: |
    ray start --head
    --port=6379
    --dashboard-host=0.0.0.0
    --metrics-export-port=8080
    --num-cpus=4
    --num-gpus=1
    --object-store-memory=2147483648
  shm_size: 2g # 30% of available RAM for Ray object store
```

## Example: Complete ML Project Configuration

### Project Structure

```
ml-project/
├── docker-compose.yml
├── docker-compose.dev.yml
├── docker-compose.prod.yml
├── .env.example
├── .env.development
├── .env.production
├── Dockerfile
├── Dockerfile.gpu
├── Dockerfile.ray
├── configs/
│   ├── memgraph.conf
│   ├── questdb.conf
│   └── ray.yaml
├── scripts/
│   ├── init-db.sh
│   ├── backup.sh
│   └── health-check.sh
└── secrets/
    ├── .gitignore
    └── README.md
```

### Complete docker-compose.yml

```yaml
version: '3.8'

x-common-variables: &common-variables
  TZ: ${TZ:-UTC}
  LOG_LEVEL: ${LOG_LEVEL:-info}

x-healthcheck-defaults: &healthcheck-defaults
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 40s

services:
  # Infrastructure services
  memgraph:
    image: memgraph/memgraph-platform:latest
    container_name: memgraph
    restart: unless-stopped
    ports:
      - '7687:7687'
      - '3000:3000'
    environment:
      <<: *common-variables
      MEMGRAPH_USER: memgraph
      MEMGRAPH_PASSWORD: ${MEMGRAPH_PASSWORD}
    volumes:
      - memgraph-data:/var/lib/memgraph
      - memgraph-log:/var/log/memgraph
    networks:
      - data
    healthcheck:
      <<: *healthcheck-defaults
      test:
        [
          'CMD',
          'mg_client',
          '-u',
          'memgraph',
          '-p',
          '${MEMGRAPH_PASSWORD}',
          '--execute',
          'RETURN 1',
        ]
    deploy:
      resources:
        limits:
          cpus: '4'
          memory: 12G
        reservations:
          cpus: '2'
          memory: 10G

  questdb:
    image: questdb/questdb:latest
    container_name: questdb
    restart: unless-stopped
    ports:
      - '9000:9000'
      - '8812:8812'
      - '9009:9009'
    environment:
      <<: *common-variables
      QDB_TELEMETRY_ENABLED: false
    volumes:
      - questdb-data:/var/lib/questdb
    networks:
      - data
    healthcheck:
      <<: *healthcheck-defaults
      test: ['CMD', 'curl', '-f', 'http://localhost:9000']
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G

  eventstore:
    image: eventstore/eventstore:latest
    container_name: eventstore
    restart: unless-stopped
    ports:
      - '2113:2113'
      - '1113:1113'
    environment:
      <<: *common-variables
      EVENTSTORE_CLUSTER_SIZE: 1
      EVENTSTORE_RUN_PROJECTIONS: All
    volumes:
      - eventstore-data:/var/lib/eventstore
      - eventstore-logs:/var/log/eventstore
    networks:
      - data
    healthcheck:
      <<: *healthcheck-defaults
      test: ['CMD', 'curl', '-f', 'http://localhost:2113/health/live']
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 2G

  # Ray cluster
  ray-head:
    build:
      context: .
      dockerfile: Dockerfile.ray
      target: ${BUILD_TARGET:-production}
    container_name: ray-head
    restart: unless-stopped
    ports:
      - '8265:8265'
      - '6379:6379'
      - '10001:10001'
    environment:
      <<: *common-variables
      RAY_HEAD_SERVICE_HOST: ray-head
    volumes:
      - ray-data:/tmp/ray
      - ./models:/models
    networks:
      - ml
      - data
    shm_size: 2g
    healthcheck:
      <<: *healthcheck-defaults
      test: ['CMD', 'ray', 'status']
    deploy:
      resources:
        limits:
          cpus: '4'
          memory: 8G
        reservations:
          cpus: '2'
          memory: 4G

  # ML application
  ml-app:
    build:
      context: .
      dockerfile: ${DOCKERFILE:-Dockerfile}
      target: ${BUILD_TARGET:-production}
    depends_on:
      ray-head:
        condition: service_healthy
      memgraph:
        condition: service_healthy
      questdb:
        condition: service_healthy
    environment:
      <<: *common-variables
      RAY_ADDRESS: ray://ray-head:10001
      MEMGRAPH_HOST: memgraph
      QUESTDB_HOST: questdb
      EVENTSTORE_HOST: eventstore
    volumes:
      - ./src:/app/src:ro
      - ./models:/models
      - ml-cache:/cache
    networks:
      - frontend
      - ml
      - data
    restart: unless-stopped
    deploy:
      resources:
        limits:
          cpus: '4'
          memory: 8G
        reservations:
          cpus: '2'
          memory: 4G
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]

networks:
  frontend:
    driver: bridge
  ml:
    driver: bridge
    internal: true
  data:
    driver: bridge
    internal: true

volumes:
  memgraph-data:
  memgraph-log:
  questdb-data:
  eventstore-data:
  eventstore-logs:
  ray-data:
  ml-cache:

secrets:
  memgraph_password:
    file: ./secrets/memgraph_password.txt
  api_keys:
    file: ./secrets/api_keys.json
```

This comprehensive guide provides best practices for Docker and Docker Compose
specifically tailored for machine learning projects, with examples relevant to
your JimBot project's technology stack.
