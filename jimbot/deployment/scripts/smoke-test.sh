#!/bin/bash
# Smoke tests for JimBot deployment

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test results
PASSED=0
FAILED=0

# Helper function for test execution
run_test() {
    local test_name=$1
    local test_command=$2
    
    echo -n "Testing $test_name... "
    
    if eval "$test_command" >/dev/null 2>&1; then
        echo -e "${GREEN}PASSED${NC}"
        ((PASSED++))
        return 0
    else
        echo -e "${RED}FAILED${NC}"
        ((FAILED++))
        return 1
    fi
}

echo -e "${GREEN}Running JimBot Smoke Tests${NC}"
echo "=========================="

# Test 1: Check all containers are running
run_test "Container status" "docker-compose ps --format json | jq -r '.[].State' | grep -v 'exited'"

# Test 2: Memgraph connectivity
run_test "Memgraph connection" "docker exec jimbot-memgraph echo 'RETURN 1;' | cypher-shell -u '' -p ''"

# Test 3: Redis connectivity
run_test "Redis connection" "docker exec jimbot-redis redis-cli ping | grep -q 'PONG'"

# Test 4: QuestDB HTTP API
run_test "QuestDB API" "curl -f -s http://localhost:9000/exec?query=SELECT%201"

# Test 5: EventStore health
run_test "EventStore health" "curl -f -s -o /dev/null -w '%{http_code}' http://localhost:2113/health/live | grep -q '204'"

# Test 6: Ray cluster status
run_test "Ray cluster" "docker exec jimbot-ray-head ray status"

# Test 7: MCP WebSocket port
run_test "MCP port open" "nc -z localhost ${MCP_PORT:-8765}"

# Test 8: Claude Gateway health
run_test "Claude Gateway" "curl -f -s http://localhost:8766/health"

# Test 9: Analytics API
run_test "Analytics API" "curl -f -s http://localhost:${METRICS_PORT:-8080}/health"

# Test 10: Metrics endpoint
run_test "Metrics endpoint" "curl -f -s http://localhost:${METRICS_PORT:-8080}/metrics | grep -q 'jimbot_'"

# Test 11: Ray Dashboard
run_test "Ray Dashboard" "curl -f -s -o /dev/null -w '%{http_code}' http://localhost:8265 | grep -q '200'"

# Test 12: Check memory usage is within limits
run_test "Memory usage" "docker stats --no-stream --format '{{.MemPerc}}' | awk '{gsub(/%/,\"\"); if(\$1 > 90) exit 1}'"

# Test 13: Check disk space
run_test "Disk space" "df -h / | awk 'NR==2 {gsub(/%/,\"\",\$5); if(\$5 > 90) exit 1}'"

# Test 14: Test data persistence
echo -n "Testing data persistence... "
TEST_KEY="smoke_test_$(date +%s)"
if docker exec jimbot-redis redis-cli SET "$TEST_KEY" "test_value" >/dev/null 2>&1 && \
   docker exec jimbot-redis redis-cli GET "$TEST_KEY" 2>/dev/null | grep -q "test_value" && \
   docker exec jimbot-redis redis-cli DEL "$TEST_KEY" >/dev/null 2>&1; then
    echo -e "${GREEN}PASSED${NC}"
    ((PASSED++))
else
    echo -e "${RED}FAILED${NC}"
    ((FAILED++))
fi

# Test 15: GPU availability (if applicable)
if [[ ! -f ".cpu-only" ]]; then
    run_test "GPU availability" "docker exec jimbot-ray-worker nvidia-smi"
fi

# Test 16: Model checkpoint directory
run_test "Checkpoint directory" "docker exec jimbot-ray-head test -d /app/checkpoints"

# Test 17: Log directory writable
run_test "Log directory" "docker exec jimbot-mcp touch /app/logs/test.log && docker exec jimbot-mcp rm /app/logs/test.log"

# Test 18: Basic MCP event processing
echo -n "Testing MCP event processing... "
if command -v wscat >/dev/null 2>&1; then
    if echo '{"type":"ping"}' | timeout 5 wscat -c ws://localhost:${MCP_PORT:-8765} 2>/dev/null | grep -q "pong"; then
        echo -e "${GREEN}PASSED${NC}"
        ((PASSED++))
    else
        echo -e "${RED}FAILED${NC}"
        ((FAILED++))
    fi
else
    echo -e "${YELLOW}SKIPPED${NC} (wscat not installed)"
fi

# Summary
echo "=========================="
echo -e "Tests Passed: ${GREEN}$PASSED${NC}"
echo -e "Tests Failed: ${RED}$FAILED${NC}"

if [[ $FAILED -eq 0 ]]; then
    echo -e "${GREEN}All smoke tests passed!${NC}"
    exit 0
else
    echo -e "${RED}Some smoke tests failed!${NC}"
    echo "Run './scripts/health.sh all' for detailed diagnostics"
    exit 1
fi