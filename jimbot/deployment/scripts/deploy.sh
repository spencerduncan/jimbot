#!/bin/bash
# Main deployment script for JimBot

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default values
ENVIRONMENT=${ENVIRONMENT:-development}
COMPOSE_FILE="docker-compose.yml"
ENV_FILE=".env"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --env)
            ENVIRONMENT="$2"
            shift 2
            ;;
        --file)
            COMPOSE_FILE="$2"
            shift 2
            ;;
        --no-build)
            NO_BUILD=true
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

echo -e "${GREEN}Deploying JimBot - Environment: ${ENVIRONMENT}${NC}"

# Check prerequisites
echo "Checking prerequisites..."
command -v docker >/dev/null 2>&1 || { echo -e "${RED}Docker is required but not installed.${NC}" >&2; exit 1; }
command -v docker-compose >/dev/null 2>&1 || { echo -e "${RED}Docker Compose is required but not installed.${NC}" >&2; exit 1; }

# Check for NVIDIA GPU if not in CPU-only mode
if [[ ! -f ".cpu-only" ]]; then
    if ! command -v nvidia-smi >/dev/null 2>&1; then
        echo -e "${YELLOW}Warning: NVIDIA GPU not detected. Running in CPU mode.${NC}"
        touch .cpu-only
    fi
fi

# Load environment variables
if [[ -f "$ENV_FILE" ]]; then
    echo "Loading environment from $ENV_FILE"
    export $(cat "$ENV_FILE" | grep -v '^#' | xargs)
else
    echo -e "${RED}Error: $ENV_FILE not found. Copy .env.example to .env and configure.${NC}"
    exit 1
fi

# Validate required environment variables
required_vars=("CLAUDE_API_KEY" "MEMGRAPH_MEMORY" "RAY_WORKER_MEMORY")
for var in "${required_vars[@]}"; do
    if [[ -z "${!var}" ]]; then
        echo -e "${RED}Error: Required environment variable $var is not set.${NC}"
        exit 1
    fi
done

# Create necessary directories
echo "Creating directories..."
mkdir -p logs backups checkpoints data/{memgraph,questdb,eventstore,redis}

# Pull or build images
if [[ "$NO_BUILD" != true ]]; then
    echo "Building Docker images..."
    if [[ "$DRY_RUN" == true ]]; then
        echo "[DRY RUN] docker-compose -f $COMPOSE_FILE build"
    else
        docker-compose -f "$COMPOSE_FILE" build
    fi
fi

# Stop existing services
echo "Stopping existing services..."
if [[ "$DRY_RUN" == true ]]; then
    echo "[DRY RUN] docker-compose -f $COMPOSE_FILE down"
else
    docker-compose -f "$COMPOSE_FILE" down
fi

# Start infrastructure services first
echo "Starting infrastructure services..."
INFRA_SERVICES="memgraph questdb eventstore redis"
if [[ "$DRY_RUN" == true ]]; then
    echo "[DRY RUN] docker-compose -f $COMPOSE_FILE up -d $INFRA_SERVICES"
else
    docker-compose -f "$COMPOSE_FILE" up -d $INFRA_SERVICES
    
    # Wait for services to be healthy
    echo "Waiting for infrastructure services to be healthy..."
    ./scripts/wait-for-healthy.sh $INFRA_SERVICES
fi

# Initialize databases if needed
if [[ ! -f ".initialized" ]]; then
    echo "Initializing databases..."
    if [[ "$DRY_RUN" == true ]]; then
        echo "[DRY RUN] docker-compose run --rm jimbot-cli python -m jimbot.cli init-db"
    else
        docker-compose run --rm jimbot-cli python -m jimbot.cli init-db
        touch .initialized
    fi
fi

# Start application services
echo "Starting application services..."
APP_SERVICES="jimbot-mcp jimbot-ray-head jimbot-ray-worker jimbot-claude-gateway jimbot-analytics"
if [[ "$DRY_RUN" == true ]]; then
    echo "[DRY RUN] docker-compose -f $COMPOSE_FILE up -d $APP_SERVICES"
else
    docker-compose -f "$COMPOSE_FILE" up -d $APP_SERVICES
    
    # Wait for services to be healthy
    echo "Waiting for application services to be healthy..."
    ./scripts/wait-for-healthy.sh $APP_SERVICES
fi

# Run post-deployment checks
echo "Running post-deployment checks..."
if [[ "$DRY_RUN" != true ]]; then
    ./scripts/health.sh all
    
    # Run smoke tests
    if [[ "$ENVIRONMENT" == "production" ]]; then
        ./scripts/smoke-test.sh
    fi
fi

echo -e "${GREEN}Deployment completed successfully!${NC}"

# Show service status
echo -e "\nService Status:"
if [[ "$DRY_RUN" != true ]]; then
    docker-compose -f "$COMPOSE_FILE" ps
fi

# Show access information
echo -e "\nAccess Information:"
echo "- MCP WebSocket: ws://localhost:${MCP_PORT:-8765}"
echo "- Ray Dashboard: http://localhost:8265"
echo "- Memgraph Lab: http://localhost:3000"
echo "- QuestDB Console: http://localhost:9000"
echo "- EventStore UI: http://localhost:2113"
echo "- Metrics API: http://localhost:${METRICS_PORT:-8080}"

# Show next steps
echo -e "\nNext Steps:"
echo "1. Monitor logs: docker-compose logs -f"
echo "2. Check metrics: curl http://localhost:${METRICS_PORT:-8080}/metrics"
echo "3. Run tests: ./scripts/test-integration.sh"