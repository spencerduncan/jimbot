#!/bin/bash
# Health check script for JimBot services

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Service groups
INFRA_SERVICES=("memgraph" "questdb" "eventstore" "redis")
APP_SERVICES=("jimbot-mcp" "jimbot-ray-head" "jimbot-ray-worker" "jimbot-claude-gateway" "jimbot-analytics")
ALL_SERVICES=("${INFRA_SERVICES[@]}" "${APP_SERVICES[@]}")

# Parse arguments
TARGET=${1:-all}

# Health check functions
check_container_health() {
    local service=$1
    local status=$(docker inspect --format='{{.State.Health.Status}}' "$service" 2>/dev/null || echo "not found")
    
    case $status in
        "healthy")
            echo -e "${GREEN}✓${NC} $service: Healthy"
            return 0
            ;;
        "unhealthy")
            echo -e "${RED}✗${NC} $service: Unhealthy"
            return 1
            ;;
        "starting")
            echo -e "${YELLOW}⟳${NC} $service: Starting..."
            return 2
            ;;
        "not found")
            echo -e "${RED}✗${NC} $service: Not found"
            return 1
            ;;
        *)
            echo -e "${YELLOW}?${NC} $service: Unknown status ($status)"
            return 2
            ;;
    esac
}

check_port() {
    local name=$1
    local host=$2
    local port=$3
    
    if nc -z "$host" "$port" 2>/dev/null; then
        echo -e "${GREEN}✓${NC} $name port $port: Open"
        return 0
    else
        echo -e "${RED}✗${NC} $name port $port: Closed"
        return 1
    fi
}

check_http_endpoint() {
    local name=$1
    local url=$2
    local expected_code=${3:-200}
    
    local response=$(curl -s -o /dev/null -w "%{http_code}" "$url" 2>/dev/null || echo "000")
    
    if [[ "$response" == "$expected_code" ]]; then
        echo -e "${GREEN}✓${NC} $name: HTTP $response"
        return 0
    else
        echo -e "${RED}✗${NC} $name: HTTP $response (expected $expected_code)"
        return 1
    fi
}

check_memgraph() {
    echo "Checking Memgraph..."
    check_container_health "jimbot-memgraph"
    check_port "Memgraph Bolt" "localhost" "7687"
    check_port "Memgraph Lab" "localhost" "3000"
    
    # Check if we can execute a query
    if docker exec jimbot-memgraph echo "RETURN 1;" | cypher-shell -u "" -p "" >/dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} Memgraph query: Success"
    else
        echo -e "${RED}✗${NC} Memgraph query: Failed"
    fi
}

check_questdb() {
    echo "Checking QuestDB..."
    check_container_health "jimbot-questdb"
    check_port "QuestDB HTTP" "localhost" "9000"
    check_port "QuestDB ILP" "localhost" "8812"
    check_http_endpoint "QuestDB API" "http://localhost:9000/exec?query=SELECT%201" "200"
}

check_eventstore() {
    echo "Checking EventStore..."
    check_container_health "jimbot-eventstore"
    check_port "EventStore HTTP" "localhost" "2113"
    check_port "EventStore TCP" "localhost" "1113"
    check_http_endpoint "EventStore Health" "http://localhost:2113/health/live" "204"
}

check_redis() {
    echo "Checking Redis..."
    check_container_health "jimbot-redis"
    check_port "Redis" "localhost" "6379"
    
    # Check if we can ping Redis
    if docker exec jimbot-redis redis-cli ping | grep -q "PONG"; then
        echo -e "${GREEN}✓${NC} Redis ping: PONG"
    else
        echo -e "${RED}✗${NC} Redis ping: Failed"
    fi
}

check_mcp() {
    echo "Checking MCP..."
    check_container_health "jimbot-mcp"
    check_port "MCP WebSocket" "localhost" "${MCP_PORT:-8765}"
    
    # Check WebSocket connectivity (basic check)
    # In production, you'd want a proper WebSocket health check
    echo -e "${YELLOW}!${NC} MCP WebSocket: Manual verification needed"
}

check_ray() {
    echo "Checking Ray..."
    check_container_health "jimbot-ray-head"
    check_container_health "jimbot-ray-worker"
    check_port "Ray Dashboard" "localhost" "8265"
    check_http_endpoint "Ray Dashboard" "http://localhost:8265" "200"
    
    # Check Ray cluster status
    if docker exec jimbot-ray-head ray status >/dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} Ray cluster: Running"
        
        # Get node count
        local nodes=$(docker exec jimbot-ray-head ray status | grep -c "node_id" || echo "0")
        echo -e "${GREEN}✓${NC} Ray nodes: $nodes"
    else
        echo -e "${RED}✗${NC} Ray cluster: Not running"
    fi
}

check_claude() {
    echo "Checking Claude Gateway..."
    check_container_health "jimbot-claude-gateway"
    check_port "Claude API" "localhost" "8766"
    check_http_endpoint "Claude Health" "http://localhost:8766/health" "200"
}

check_analytics() {
    echo "Checking Analytics..."
    check_container_health "jimbot-analytics"
    check_port "Metrics API" "localhost" "${METRICS_PORT:-8080}"
    check_http_endpoint "Metrics Health" "http://localhost:${METRICS_PORT:-8080}/health" "200"
    check_http_endpoint "Metrics Endpoint" "http://localhost:${METRICS_PORT:-8080}/metrics" "200"
}

check_resources() {
    echo -e "\nResource Usage:"
    
    # Memory usage
    local total_mem=$(free -h | awk '/^Mem:/ {print $2}')
    local used_mem=$(free -h | awk '/^Mem:/ {print $3}')
    local free_mem=$(free -h | awk '/^Mem:/ {print $4}')
    echo "System Memory: $used_mem used / $total_mem total ($free_mem free)"
    
    # Docker resource usage
    echo -e "\nDocker Container Resources:"
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}" | grep jimbot || true
    
    # GPU usage (if available)
    if command -v nvidia-smi >/dev/null 2>&1; then
        echo -e "\nGPU Usage:"
        nvidia-smi --query-gpu=name,memory.used,memory.total,utilization.gpu --format=csv,noheader,nounits | \
            awk -F', ' '{printf "  %s: %s/%s MB (%s%% utilization)\n", $1, $2, $3, $4}'
    fi
}

# Main execution
echo -e "${GREEN}JimBot Health Check${NC}"
echo "===================="

overall_status=0

case $TARGET in
    "infra")
        for service in check_memgraph check_questdb check_eventstore check_redis; do
            echo
            $service || overall_status=1
        done
        ;;
    "app")
        for service in check_mcp check_ray check_claude check_analytics; do
            echo
            $service || overall_status=1
        done
        ;;
    "all")
        for service in check_memgraph check_questdb check_eventstore check_redis \
                      check_mcp check_ray check_claude check_analytics; do
            echo
            $service || overall_status=1
        done
        check_resources
        ;;
    *)
        echo "Usage: $0 [infra|app|all]"
        exit 1
        ;;
esac

echo
echo "===================="
if [[ $overall_status -eq 0 ]]; then
    echo -e "${GREEN}All health checks passed!${NC}"
else
    echo -e "${RED}Some health checks failed!${NC}"
    exit $overall_status
fi