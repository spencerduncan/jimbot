#!/bin/bash
# CI script for running Lua tests in Docker environment
# Part of Sprint 2.4: Migrate Lua test suite to Docker environment

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_color() {
    echo -e "${1}${2}${NC}"
}

# Function to print section headers
print_section() {
    echo
    print_color "$BLUE" "=====================================
    $1
    ====================================="
    echo
}

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
DOCKER_COMPOSE_FILE="$PROJECT_ROOT/docker/docker-compose.lua-test.yml"
TIMEOUT=${TIMEOUT:-600}  # 10 minutes timeout
COVERAGE=${COVERAGE:-false}
PERFORMANCE=${PERFORMANCE:-false}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --coverage)
            COVERAGE=true
            shift
            ;;
        --performance)
            PERFORMANCE=true
            shift
            ;;
        --timeout)
            TIMEOUT="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo "Options:"
            echo "  --coverage      Enable coverage reporting"
            echo "  --performance   Enable performance testing"
            echo "  --timeout N     Set timeout in seconds (default: 600)"
            echo "  --help          Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Change to project root
cd "$PROJECT_ROOT"

print_section "DOCKER-BASED LUA TEST RUNNER"
print_color "$GREEN" "Project root: $PROJECT_ROOT"
print_color "$GREEN" "Docker Compose file: $DOCKER_COMPOSE_FILE"
print_color "$GREEN" "Timeout: ${TIMEOUT}s"
print_color "$GREEN" "Coverage: $COVERAGE"
print_color "$GREEN" "Performance: $PERFORMANCE"

# Verify required files exist
if [[ ! -f "$DOCKER_COMPOSE_FILE" ]]; then
    print_color "$RED" "Error: Docker Compose file not found: $DOCKER_COMPOSE_FILE"
    exit 1
fi

if [[ ! -f "docker/Dockerfile.lua-test" ]]; then
    print_color "$RED" "Error: Lua test Dockerfile not found: docker/Dockerfile.lua-test"
    exit 1
fi

# Build the Docker image
print_section "BUILDING LUA TEST IMAGE"
print_color "$YELLOW" "Building Docker image for Lua testing..."
if docker compose -f "$DOCKER_COMPOSE_FILE" build lua-test; then
    print_color "$GREEN" "✓ Docker image built successfully"
else
    print_color "$RED" "✗ Failed to build Docker image"
    exit 1
fi

# Clean up any existing containers
print_section "CLEANING UP EXISTING CONTAINERS"
print_color "$YELLOW" "Removing any existing test containers..."
docker compose -f "$DOCKER_COMPOSE_FILE" down -v 2>/dev/null || true

# Determine which service to run
SERVICE="lua-test"
if [[ "$COVERAGE" == "true" ]]; then
    SERVICE="lua-test-coverage"
    print_color "$YELLOW" "Running with coverage reporting..."
elif [[ "$PERFORMANCE" == "true" ]]; then
    SERVICE="lua-test-perf"
    print_color "$YELLOW" "Running with performance testing..."
fi

# Run the tests
print_section "RUNNING LUA TESTS"
print_color "$YELLOW" "Starting Lua test suite in Docker container..."
print_color "$YELLOW" "Service: $SERVICE"

# Create a temporary file for exit code
EXIT_CODE_FILE=$(mktemp)
trap 'rm -f "$EXIT_CODE_FILE"' EXIT

# Run tests with timeout
if timeout "$TIMEOUT" docker compose -f "$DOCKER_COMPOSE_FILE" run --rm "$SERVICE"; then
    echo "0" > "$EXIT_CODE_FILE"
    print_color "$GREEN" "✓ Lua tests completed successfully"
else
    EXIT_CODE=$?
    echo "$EXIT_CODE" > "$EXIT_CODE_FILE"
    if [[ $EXIT_CODE -eq 124 ]]; then
        print_color "$RED" "✗ Lua tests timed out after ${TIMEOUT}s"
    else
        print_color "$RED" "✗ Lua tests failed with exit code: $EXIT_CODE"
    fi
fi

# Clean up containers
print_section "CLEANING UP"
print_color "$YELLOW" "Cleaning up Docker containers..."
docker compose -f "$DOCKER_COMPOSE_FILE" down -v 2>/dev/null || true

# Copy coverage reports if enabled
if [[ "$COVERAGE" == "true" ]]; then
    print_section "COVERAGE REPORTS"
    print_color "$YELLOW" "Extracting coverage reports..."
    
    # Create coverage directory
    mkdir -p coverage/lua
    
    # Copy coverage files from Docker volume
    CONTAINER_ID=$(docker compose -f "$DOCKER_COMPOSE_FILE" ps -q lua-test-coverage 2>/dev/null || true)
    if [[ -n "$CONTAINER_ID" ]]; then
        docker cp "$CONTAINER_ID:/app/coverage/." coverage/lua/ 2>/dev/null || true
        print_color "$GREEN" "✓ Coverage reports extracted to coverage/lua/"
    else
        print_color "$YELLOW" "⚠ No coverage container found"
    fi
fi

# Show final results
print_section "FINAL RESULTS"
FINAL_EXIT_CODE=$(cat "$EXIT_CODE_FILE")
if [[ $FINAL_EXIT_CODE -eq 0 ]]; then
    print_color "$GREEN" "✓ All Lua tests passed successfully!"
    print_color "$GREEN" "✓ Docker-based Lua testing environment is working correctly"
    
    # Show test summary
    echo
    print_color "$BLUE" "Test Summary:"
    print_color "$GREEN" "  - Style checks: ✓"
    print_color "$GREEN" "  - Lint checks: ✓"
    print_color "$GREEN" "  - Unit tests: ✓"
    print_color "$GREEN" "  - Integration tests: ✓"
    
    if [[ "$COVERAGE" == "true" ]]; then
        print_color "$GREEN" "  - Coverage report: ✓"
    fi
    
    if [[ "$PERFORMANCE" == "true" ]]; then
        print_color "$GREEN" "  - Performance test: ✓"
    fi
else
    print_color "$RED" "✗ Lua tests failed!"
    print_color "$RED" "✗ Please check the logs above for details"
fi

exit $FINAL_EXIT_CODE