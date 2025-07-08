#!/bin/bash
set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}Event Bus Integration Test Runner${NC}"
echo "=================================="

# Build the service
echo -e "\n${YELLOW}Building Event Bus service...${NC}"
cargo build --release

# Start the service
echo -e "\n${YELLOW}Starting Event Bus service...${NC}"
./target/release/event-bus-rust &
SERVICE_PID=$!

# Function to cleanup on exit
cleanup() {
    if [ ! -z "$SERVICE_PID" ]; then
        echo -e "\n${YELLOW}Stopping Event Bus service (PID: $SERVICE_PID)...${NC}"
        kill $SERVICE_PID 2>/dev/null || true
        wait $SERVICE_PID 2>/dev/null || true
    fi
}

# Set up cleanup trap
trap cleanup EXIT INT TERM

# Wait for service to be ready
echo "Waiting for service to start..."
READY=false
for i in {1..30}; do
    if curl -s http://localhost:8080/health > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Service is ready!${NC}"
        READY=true
        break
    fi
    if [ $i -eq 30 ]; then
        echo -e "${RED}✗ Service failed to start within 30 seconds${NC}"
        exit 1
    fi
    echo -n "."
    sleep 1
done

if [ "$READY" = true ]; then
    echo -e "\n${YELLOW}Running integration tests...${NC}"
    cargo test --tests --verbose
    TEST_RESULT=$?
    
    if [ $TEST_RESULT -eq 0 ]; then
        echo -e "\n${GREEN}✓ All integration tests passed!${NC}"
    else
        echo -e "\n${RED}✗ Some integration tests failed${NC}"
        exit $TEST_RESULT
    fi
else
    exit 1
fi