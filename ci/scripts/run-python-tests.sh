#!/bin/bash
# Python test runner for Docker CI environment
# Migrated from native CI to Docker for consistency

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Python Test Suite (Docker CI) ===${NC}"

# Ensure we're in the right directory
cd /app

# Set up environment
export PYTHONPATH="/app:${PYTHONPATH}"
export CI=true

# Function to run tests with proper error handling
run_test() {
    local test_name="$1"
    local test_cmd="$2"
    
    echo -e "${YELLOW}Running $test_name...${NC}"
    
    if eval "$test_cmd"; then
        echo -e "${GREEN}✅ $test_name passed${NC}"
        return 0
    else
        echo -e "${RED}❌ $test_name failed${NC}"
        return 1
    fi
}

# Install test dependencies (already in Dockerfile but ensure they're available)
echo -e "${YELLOW}Checking Python test dependencies...${NC}"
python3 -c "import pytest, coverage; print('All test dependencies available')"

# Run unit tests with coverage
run_test "Unit Tests" "
    pytest jimbot/tests/unit/ \
        -v \
        --cov=jimbot \
        --cov-report=xml \
        --cov-report=term-missing \
        --cov-report=html \
        --junit-xml=test-results-unit.xml \
        --tb=short
"

# Run performance tests if they exist
if [ -d "jimbot/tests/performance" ]; then
    run_test "Performance Tests" "
        pytest jimbot/tests/performance/ \
            -v \
            --benchmark-only \
            --benchmark-json=benchmark-results.json \
            --tb=short
    "
fi

# Generate coverage summary
echo -e "${YELLOW}Coverage Summary:${NC}"
coverage report --show-missing --skip-covered

# Check coverage threshold (80%)
coverage_percent=$(coverage report | grep TOTAL | awk '{print $4}' | sed 's/%//')
if [ "$coverage_percent" -lt 80 ]; then
    echo -e "${RED}❌ Coverage $coverage_percent% is below 80% threshold${NC}"
    exit 1
else
    echo -e "${GREEN}✅ Coverage $coverage_percent% meets threshold${NC}"
fi

echo -e "${GREEN}=== Python tests completed successfully! ===${NC}"