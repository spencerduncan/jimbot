#!/bin/bash
# Script to run CI tests locally using Docker
# This helps developers test their changes before pushing

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Parse command line arguments
ACTION=${1:-all}
REBUILD=${2:-}

echo -e "${GREEN}=== JimBot Docker CI Runner ===${NC}"

# Function to build Docker image
build_image() {
    echo -e "${YELLOW}Building Docker CI image...${NC}"
    docker build -f Dockerfile.ci --target ci -t jimbot-ci:latest .
}

# Function to run format check
run_format_check() {
    echo -e "${YELLOW}Running format check...${NC}"
    docker run --rm -v $(pwd):/app:ro jimbot-ci:latest bash -c "
        black --check jimbot/ scripts/ services/ && 
        isort --check-only jimbot/ scripts/ services/
    "
}

# Function to run linters
run_lint() {
    echo -e "${YELLOW}Running linters...${NC}"
    docker run --rm -v $(pwd):/app:ro jimbot-ci:latest bash -c "
        flake8 jimbot/ --max-line-length=120 --ignore=E203,W503 &&
        pylint jimbot/ --fail-under=7.0 &&
        mypy jimbot/ --ignore-missing-imports
    "
}

# Function to run unit tests
run_unit_tests() {
    echo -e "${YELLOW}Running unit tests...${NC}"
    docker run --rm -v $(pwd):/app -e PYTHONPATH=/app jimbot-ci:latest \
        pytest jimbot/tests/unit/ -v --cov=jimbot
}

# Function to run integration tests
run_integration_tests() {
    echo -e "${YELLOW}Running integration tests with services...${NC}"
    docker-compose -f docker-compose.ci.yml up --build --abort-on-container-exit integration-tests
    docker-compose -f docker-compose.ci.yml down -v
}

# Function to run all tests
run_all_tests() {
    echo -e "${YELLOW}Running all tests...${NC}"
    docker run --rm -v $(pwd):/app -e CI=true jimbot-ci:latest /run_all_tests.sh
}

# Function to fix formatting issues
fix_format() {
    echo -e "${YELLOW}Fixing formatting issues...${NC}"
    docker run --rm -v $(pwd):/app jimbot-ci:latest bash -c "
        black jimbot/ scripts/ services/ &&
        isort jimbot/ scripts/ services/
    "
    echo -e "${GREEN}Formatting fixed!${NC}"
}

# Function to run interactive shell
run_shell() {
    echo -e "${YELLOW}Starting interactive shell...${NC}"
    docker run --rm -it -v $(pwd):/app jimbot-ci:latest /bin/bash
}

# Check if we need to rebuild
if [[ "$REBUILD" == "--rebuild" ]] || [[ ! "$(docker images -q jimbot-ci:latest 2> /dev/null)" ]]; then
    build_image
fi

# Execute requested action
case $ACTION in
    format|format-check)
        run_format_check
        ;;
    lint)
        run_lint
        ;;
    unit|unit-tests)
        run_unit_tests
        ;;
    integration|integration-tests)
        run_integration_tests
        ;;
    all)
        run_all_tests
        ;;
    fix|fix-format)
        fix_format
        ;;
    shell|bash)
        run_shell
        ;;
    build)
        build_image
        ;;
    *)
        echo -e "${RED}Unknown action: $ACTION${NC}"
        echo "Usage: $0 [action] [--rebuild]"
        echo "Actions:"
        echo "  format       - Run format check"
        echo "  lint         - Run linters"
        echo "  unit         - Run unit tests"
        echo "  integration  - Run integration tests"
        echo "  all          - Run all tests"
        echo "  fix          - Fix formatting issues"
        echo "  shell        - Start interactive shell"
        echo "  build        - Build Docker image only"
        exit 1
        ;;
esac

# Check exit code
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ $ACTION completed successfully!${NC}"
else
    echo -e "${RED}❌ $ACTION failed!${NC}"
    exit 1
fi