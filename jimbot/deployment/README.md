# JimBot Deployment

This directory contains all deployment configurations and scripts for the JimBot
system.

## Directory Structure

```
deployment/
├── docker/              # Docker configurations
│   ├── base/           # Base image definitions
│   ├── services/       # Service-specific Dockerfiles
│   └── scripts/        # Container startup scripts
├── kubernetes/          # Kubernetes manifests (future)
│   ├── base/          # Base configurations
│   ├── overlays/      # Environment-specific overlays
│   └── operators/     # Custom operators
├── terraform/          # Infrastructure as code (future)
│   ├── modules/       # Reusable modules
│   └── environments/  # Environment configurations
├── scripts/            # Deployment automation scripts
│   ├── deploy.sh      # Main deployment script
│   ├── rollback.sh    # Rollback script
│   └── health.sh      # Health check script
├── docker-compose.yml  # Full system composition
├── .env.example       # Environment variables template
├── CLAUDE.md          # Deployment guidelines for Claude
└── README.md          # This file
```

## Quick Start

### Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+
- NVIDIA Container Toolkit (for GPU support)
- 32GB RAM minimum
- NVIDIA GPU with 8GB+ VRAM (recommended: RTX 3090)

### Local Development Deployment

1. **Clone and setup environment**

```bash
cd jimbot/deployment
cp .env.example .env
# Edit .env with your configuration
```

2. **Build and start services**

```bash
# Build all images
docker-compose build

# Start infrastructure services first
docker-compose up -d memgraph questdb eventstore

# Wait for services to be healthy
./scripts/health.sh infra

# Start application services
docker-compose up -d

# Check all services are running
docker-compose ps
```

3. **Initialize the system**

```bash
# Create database schemas
docker-compose exec jimbot-cli init-db

# Load initial knowledge graph data
docker-compose exec jimbot-cli load-knowledge-graph

# Verify system health
./scripts/health.sh all
```

4. **Access services**

- MCP WebSocket: `ws://localhost:8765`
- Memgraph Lab: `http://localhost:3000`
- QuestDB Console: `http://localhost:9000`
- EventStore UI: `http://localhost:2113`
- Metrics API: `http://localhost:8080/metrics`

### Staging Deployment

For staging environment with Kubernetes:

```bash
# Build and push images
./scripts/build-and-push.sh staging

# Deploy to Kubernetes
kubectl apply -k kubernetes/overlays/staging

# Wait for rollout
kubectl rollout status deployment/jimbot -n jimbot-staging

# Run smoke tests
./scripts/smoke-test.sh staging
```

### Production Deployment

For production deployment on single workstation:

```bash
# Ensure backups are current
./scripts/backup.sh

# Deploy with production configuration
ENVIRONMENT=production ./scripts/deploy.sh

# Verify deployment
./scripts/health.sh production

# Run integration tests
./scripts/integration-test.sh
```

## Service Configuration

### Resource Limits

Default resource allocations (customizable in `.env`):

| Service        | Memory Limit | CPU Limit | GPU |
| -------------- | ------------ | --------- | --- |
| memgraph       | 12GB         | 2 cores   | No  |
| ray-head       | 4GB          | 2 cores   | No  |
| ray-worker     | 4GB          | 2 cores   | Yes |
| mcp            | 1GB          | 1 core    | No  |
| claude-gateway | 512MB        | 0.5 cores | No  |
| analytics      | 1GB          | 1 core    | No  |
| questdb        | 3GB          | 1 core    | No  |
| eventstore     | 3GB          | 1 core    | No  |

### Environment Variables

Key environment variables (see `.env.example` for full list):

```bash
# Claude API Configuration
CLAUDE_API_KEY=your-api-key
CLAUDE_MODEL=claude-3-opus
CLAUDE_HOURLY_LIMIT=100

# Ray Configuration
RAY_HEAD_PORT=6379
RAY_NUM_WORKERS=2
RAY_WORKER_MEMORY=4g

# Memgraph Configuration
MEMGRAPH_HOST=memgraph
MEMGRAPH_PORT=7687
MEMGRAPH_MEMORY=12g

# MCP Configuration
MCP_PORT=8765
MCP_BATCH_WINDOW_MS=100

# Monitoring
METRICS_PORT=8080
LOG_LEVEL=INFO
```

## Deployment Commands

### Starting Services

```bash
# Start all services
docker-compose up -d

# Start specific service
docker-compose up -d jimbot-mcp

# Start with logs
docker-compose up jimbot-ray-worker

# Scale workers
docker-compose up -d --scale jimbot-ray-worker=3
```

### Stopping Services

```bash
# Stop all services
docker-compose down

# Stop and remove volumes (CAUTION: deletes data)
docker-compose down -v

# Stop specific service
docker-compose stop jimbot-mcp
```

### Updating Services

```bash
# Pull latest images
docker-compose pull

# Rebuild and update specific service
docker-compose build jimbot-mcp
docker-compose up -d jimbot-mcp

# Rolling update
./scripts/rolling-update.sh jimbot-mcp
```

### Monitoring & Logs

```bash
# View logs for all services
docker-compose logs -f

# View logs for specific service
docker-compose logs -f jimbot-mcp

# View last 100 lines
docker-compose logs --tail=100 jimbot-ray-worker

# Check resource usage
docker stats

# Run health checks
./scripts/health.sh
```

## Backup & Recovery

### Automated Backups

Backups run automatically via cron:

```bash
# Install backup cron job
./scripts/install-backup-cron.sh

# Manual backup
./scripts/backup.sh

# List backups
./scripts/list-backups.sh
```

### Recovery Procedures

```bash
# Restore from specific backup
./scripts/restore.sh backup-2024-01-15-1200.tar.gz

# Restore only Memgraph data
./scripts/restore.sh --service=memgraph backup-2024-01-15-1200.tar.gz

# Verify restore
./scripts/verify-restore.sh
```

## Troubleshooting

### Common Issues

**Services won't start**

```bash
# Check logs
docker-compose logs jimbot-mcp

# Verify resources
docker system df
df -h
free -h

# Clean up
docker system prune -a
```

**GPU not available**

```bash
# Check NVIDIA runtime
docker run --rm --gpus all nvidia/cuda:12.2.2-base nvidia-smi

# Verify compose GPU config
docker-compose config | grep -A5 gpu

# Restart Docker daemon
sudo systemctl restart docker
```

**Memory issues**

```bash
# Check memory usage
docker stats --no-stream

# Increase swap
sudo fallocate -l 16G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

**Network issues**

```bash
# Test internal communication
docker-compose exec jimbot-mcp ping memgraph

# Check port bindings
docker-compose ps

# Recreate network
docker-compose down
docker network rm jimbot_default
docker-compose up -d
```

### Debug Mode

Enable debug mode for verbose logging:

```bash
# Set debug environment
export JIMBOT_DEBUG=true
export LOG_LEVEL=DEBUG

# Run with debug
docker-compose up jimbot-mcp
```

## Performance Tuning

### Docker Configuration

Optimize Docker daemon (`/etc/docker/daemon.json`):

```json
{
  "storage-driver": "overlay2",
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  },
  "default-runtime": "nvidia",
  "default-ulimits": {
    "memlock": {
      "soft": -1,
      "hard": -1
    }
  }
}
```

### System Tuning

```bash
# Increase system limits
echo "vm.max_map_count=262144" | sudo tee -a /etc/sysctl.conf
sudo sysctl -p

# Disable swap for Memgraph
echo "vm.swappiness=1" | sudo tee -a /etc/sysctl.conf
```

## Security

### Hardening Checklist

- [ ] Change default passwords in `.env`
- [ ] Enable TLS for external connections
- [ ] Restrict network access with firewall rules
- [ ] Enable audit logging
- [ ] Regular security updates
- [ ] Implement secret rotation

### Network Security

```bash
# Create isolated network
docker network create --internal jimbot-internal

# Update compose to use internal network
# See docker-compose.yml for configuration
```

## Monitoring

### Metrics Collection

Metrics are exposed at `http://localhost:8080/metrics`:

```bash
# View current metrics
curl http://localhost:8080/metrics

# Specific metric
curl http://localhost:8080/metrics/mcp/latency
```

### Grafana Dashboards

Import provided dashboards:

1. System Overview: `dashboards/system-overview.json`
2. Game Performance: `dashboards/game-performance.json`
3. Training Progress: `dashboards/training-progress.json`

### Alerts

Configure alerts in `monitoring/alerts.yml`:

- High memory usage
- Service failures
- Training stalls
- API rate limit warnings

## Maintenance

### Regular Tasks

**Daily**

- Check service health
- Review error logs
- Monitor resource usage

**Weekly**

- Update base images
- Clean unused containers/images
- Review metrics trends
- Test backups

**Monthly**

- Security updates
- Performance analysis
- Capacity planning
- Disaster recovery drill

### Upgrade Procedures

```bash
# Backup before upgrade
./scripts/backup.sh

# Test upgrade in staging
./scripts/test-upgrade.sh staging

# Perform upgrade
./scripts/upgrade.sh

# Verify functionality
./scripts/post-upgrade-test.sh
```

## Support

For deployment issues:

1. Check service logs
2. Review troubleshooting guide
3. Consult CLAUDE.md for architectural guidance
4. Run diagnostic script: `./scripts/diagnose.sh`
