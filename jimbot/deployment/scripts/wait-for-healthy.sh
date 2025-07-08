#!/bin/bash
# Wait for services to become healthy

set -e

# Configuration
MAX_WAIT=${MAX_WAIT:-300}  # 5 minutes default
CHECK_INTERVAL=${CHECK_INTERVAL:-5}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Services to check (passed as arguments)
SERVICES=("$@")

if [[ ${#SERVICES[@]} -eq 0 ]]; then
    echo "Usage: $0 service1 service2 ..."
    exit 1
fi

echo "Waiting for services to become healthy..."
echo "Services: ${SERVICES[*]}"
echo "Timeout: ${MAX_WAIT}s"

start_time=$(date +%s)

# Function to check if a service is healthy
is_healthy() {
    local service=$1
    local container_name="jimbot-$service"
    
    # Check if container exists
    if ! docker ps -a --format "{{.Names}}" | grep -q "^$container_name$"; then
        return 1
    fi
    
    # Check health status
    local health_status=$(docker inspect --format='{{.State.Health.Status}}' "$container_name" 2>/dev/null || echo "none")
    
    if [[ "$health_status" == "healthy" ]]; then
        return 0
    else
        return 1
    fi
}

# Wait loop
while true; do
    all_healthy=true
    unhealthy_services=()
    
    for service in "${SERVICES[@]}"; do
        if is_healthy "$service"; then
            echo -e "${GREEN}✓${NC} $service: healthy"
        else
            echo -e "${YELLOW}⟳${NC} $service: waiting..."
            all_healthy=false
            unhealthy_services+=("$service")
        fi
    done
    
    if [[ "$all_healthy" == "true" ]]; then
        echo -e "${GREEN}All services are healthy!${NC}"
        exit 0
    fi
    
    # Check timeout
    current_time=$(date +%s)
    elapsed=$((current_time - start_time))
    
    if [[ $elapsed -gt $MAX_WAIT ]]; then
        echo -e "${RED}Timeout waiting for services to become healthy!${NC}"
        echo "Unhealthy services: ${unhealthy_services[*]}"
        
        # Show logs for unhealthy services
        for service in "${unhealthy_services[@]}"; do
            echo -e "\n${RED}Logs for $service:${NC}"
            docker logs --tail 50 "jimbot-$service" 2>&1 || true
        done
        
        exit 1
    fi
    
    # Show progress
    remaining=$((MAX_WAIT - elapsed))
    echo -e "${YELLOW}Waiting... (${remaining}s remaining)${NC}"
    
    sleep $CHECK_INTERVAL
done