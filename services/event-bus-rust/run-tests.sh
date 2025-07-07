#!/bin/bash
set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Parse command line arguments
RUN_INTEGRATION=true
RUN_UNIT=true
BUILD_MODE="debug"

while [[ $# -gt 0 ]]; do
    case $1 in
        --unit-only)
            RUN_INTEGRATION=false
            shift
            ;;
        --integration-only)
            RUN_UNIT=false
            shift
            ;;
        --release)
            BUILD_MODE="release"
            shift
            ;;
        --help)
            echo "Usage: $0 [options]"
            echo "Options:"
            echo "  --unit-only        Run only unit tests"
            echo "  --integration-only Run only integration tests"
            echo "  --release         Build in release mode"
            echo "  --help            Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

echo -e "${GREEN}Event Bus Rust Test Runner${NC}"
echo "=========================="

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

# Run unit tests if requested
if [ "$RUN_UNIT" = true ]; then
    echo -e "\n${YELLOW}Running unit tests...${NC}"
    cargo test --bins --verbose
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Unit tests passed${NC}"
    else
        echo -e "${RED}✗ Unit tests failed${NC}"
        exit 1
    fi
fi

# Run integration tests if requested
if [ "$RUN_INTEGRATION" = true ]; then
    echo -e "\n${YELLOW}Building Event Bus service (${BUILD_MODE} mode)...${NC}"
    
    if [ "$BUILD_MODE" = "release" ]; then
        cargo build --release
        BINARY_PATH="./target/release/event-bus-rust"
    else
        cargo build
        BINARY_PATH="./target/debug/event-bus-rust"
    fi
    
    echo -e "\n${YELLOW}Starting Event Bus service...${NC}"
    $BINARY_PATH &
    SERVICE_PID=$!
    
    echo "Waiting for service to start (PID: $SERVICE_PID)..."
    
    # Wait for service to be ready
    MAX_ATTEMPTS=30
    ATTEMPT=0
    while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
        if curl -s http://localhost:8080/health > /dev/null 2>&1; then
            echo -e "${GREEN}✓ Service is ready!${NC}"
            break
        fi
        
        # Check if process is still running
        if ! kill -0 $SERVICE_PID 2>/dev/null; then
            echo -e "${RED}✗ Service failed to start${NC}"
            exit 1
        fi
        
        ATTEMPT=$((ATTEMPT + 1))
        if [ $ATTEMPT -eq $MAX_ATTEMPTS ]; then
            echo -e "${RED}✗ Service failed to start within 30 seconds${NC}"
            exit 1
        fi
        
        echo -n "."
        sleep 1
    done
    
    echo -e "\n${YELLOW}Running integration tests...${NC}"
    cargo test --test '*' --verbose
    
    TEST_RESULT=$?
    
    # Stop the service
    echo -e "\n${YELLOW}Stopping Event Bus service...${NC}"
    kill $SERVICE_PID 2>/dev/null || true
    wait $SERVICE_PID 2>/dev/null || true
    SERVICE_PID=""
    
    if [ $TEST_RESULT -eq 0 ]; then
        echo -e "${GREEN}✓ Integration tests passed${NC}"
    else
        echo -e "${RED}✗ Integration tests failed${NC}"
        exit 1
    fi
fi

echo -e "\n${GREEN}✓ All tests completed successfully!${NC}"