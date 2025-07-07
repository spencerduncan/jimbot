#!/bin/bash
set -euo pipefail

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Change to workspace root
cd /workspace

echo -e "${GREEN}=== Running Full Integration Test Suite ===${NC}"

# Function to run a test and capture results
run_test() {
    local test_name=$1
    local test_command=$2
    
    echo -e "${YELLOW}Running: $test_name${NC}"
    if eval "$test_command"; then
        echo -e "${GREEN}✓ $test_name passed${NC}"
        return 0
    else
        echo -e "${RED}✗ $test_name failed${NC}"
        return 1
    fi
}

# Track failures
FAILED_TESTS=()

# Run Python integration tests
if [ -d "jimbot/tests/integration" ]; then
    if ! run_test "Python Integration Tests" "pytest jimbot/tests/integration -v"; then
        FAILED_TESTS+=("Python Integration Tests")
    fi
fi

# Run Rust integration tests for each service
for service_dir in services/*/; do
    if [ -f "$service_dir/Cargo.toml" ] && [ -d "$service_dir/tests" ]; then
        service_name=$(basename "$service_dir")
        echo -e "${YELLOW}Testing Rust service: $service_name${NC}"
        
        cd "$service_dir"
        
        # Build the service
        cargo build --release
        
        # Special handling for services that need to be running
        case "$service_name" in
            event-bus-rust)
                # Start the service
                ./target/release/event-bus-rust &
                SERVICE_PID=$!
                
                # Wait for service to be ready
                echo "Waiting for $service_name to start..."
                READY=false
                for i in {1..30}; do
                    if curl -s http://localhost:8080/health > /dev/null 2>&1; then
                        echo "Service is ready!"
                        READY=true
                        break
                    fi
                    sleep 1
                done
                
                if [ "$READY" = true ]; then
                    # Run integration tests
                    if ! run_test "$service_name Integration Tests" "cargo test --tests --verbose"; then
                        FAILED_TESTS+=("$service_name Integration Tests")
                    fi
                else
                    echo -e "${RED}$service_name failed to start${NC}"
                    FAILED_TESTS+=("$service_name Startup")
                fi
                
                # Stop the service
                kill $SERVICE_PID 2>/dev/null || true
                wait $SERVICE_PID 2>/dev/null || true
                ;;
            *)
                # For other services, just run the tests
                if ! run_test "$service_name Integration Tests" "cargo test --tests --verbose"; then
                    FAILED_TESTS+=("$service_name Integration Tests")
                fi
                ;;
        esac
        
        cd /workspace
    fi
done

# Run end-to-end tests if they exist
if [ -d "tests/e2e" ]; then
    if ! run_test "End-to-End Tests" "pytest tests/e2e -v"; then
        FAILED_TESTS+=("End-to-End Tests")
    fi
fi

# Summary
echo -e "\n${GREEN}=== Integration Test Summary ===${NC}"
if [ ${#FAILED_TESTS[@]} -eq 0 ]; then
    echo -e "${GREEN}All integration tests passed!${NC}"
    exit 0
else
    echo -e "${RED}Failed tests:${NC}"
    for test in "${FAILED_TESTS[@]}"; do
        echo -e "${RED}  - $test${NC}"
    done
    exit 1
fi