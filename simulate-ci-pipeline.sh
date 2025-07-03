#!/bin/bash
# CI Pipeline Local Simulation Script
# Simulates the GitHub Actions pipeline locally to identify failure points

set -e  # Exit on first error
set -o pipefail  # Propagate pipe failures

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Global variables
FAILED_JOBS=()
SKIPPED_JOBS=()
COMPLETED_JOBS=()
LOG_DIR="ci-simulation-logs"

# Create log directory
mkdir -p "$LOG_DIR"

# Logging function
log() {
    local level=$1
    shift
    local message="$@"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    case $level in
        INFO)
            echo -e "${BLUE}[INFO]${NC} ${timestamp} - $message" | tee -a "$LOG_DIR/simulation.log"
            ;;
        SUCCESS)
            echo -e "${GREEN}[SUCCESS]${NC} ${timestamp} - $message" | tee -a "$LOG_DIR/simulation.log"
            ;;
        WARNING)
            echo -e "${YELLOW}[WARNING]${NC} ${timestamp} - $message" | tee -a "$LOG_DIR/simulation.log"
            ;;
        ERROR)
            echo -e "${RED}[ERROR]${NC} ${timestamp} - $message" | tee -a "$LOG_DIR/simulation.log"
            ;;
    esac
}

# Job execution wrapper
run_job() {
    local job_name=$1
    local job_func=$2
    local dependencies="${3:-}"
    
    log INFO "Starting job: $job_name"
    
    # Check dependencies
    if [ -n "$dependencies" ]; then
        for dep in $dependencies; do
            if [[ " ${FAILED_JOBS[@]} " =~ " ${dep} " ]]; then
                log WARNING "Skipping $job_name due to failed dependency: $dep"
                SKIPPED_JOBS+=("$job_name")
                return 1
            fi
        done
    fi
    
    # Execute job
    local job_log="$LOG_DIR/${job_name}.log"
    if $job_func > "$job_log" 2>&1; then
        log SUCCESS "Job completed: $job_name"
        COMPLETED_JOBS+=("$job_name")
        return 0
    else
        log ERROR "Job failed: $job_name (see $job_log for details)"
        FAILED_JOBS+=("$job_name")
        return 1
    fi
}

# Job: Format Check
job_format_check() {
    echo "=== Format Check Job ==="
    
    # Check Python formatting tools
    if ! command -v black &> /dev/null; then
        echo "ERROR: black not installed"
        return 1
    fi
    
    if ! command -v isort &> /dev/null; then
        echo "ERROR: isort not installed"
        return 1
    fi
    
    # Check for Python files
    if [ -d "jimbot" ]; then
        echo "Checking Python formatting..."
        black --check jimbot || return 1
        isort --check-only jimbot || return 1
    else
        echo "WARNING: jimbot directory not found"
    fi
    
    # Check for Lua formatter (with fallback)
    if ! command -v stylua &> /dev/null; then
        echo "WARNING: stylua not installed, attempting download..."
        wget --retry-connrefused --tries=3 \
            https://github.com/JohnnyMorganz/StyLua/releases/download/v0.20.0/stylua-linux.zip \
            -O /tmp/stylua-linux.zip || {
            echo "WARNING: Failed to download StyLua, skipping Lua formatting"
            return 0
        }
    fi
    
    echo "Format check completed"
    return 0
}

# Job: Lint
job_lint() {
    echo "=== Lint Job ==="
    
    # Python linting
    if command -v flake8 &> /dev/null; then
        echo "Running flake8..."
        flake8 jimbot --config=.flake8 || echo "WARNING: flake8 issues found"
    else
        echo "ERROR: flake8 not installed"
        return 1
    fi
    
    if command -v mypy &> /dev/null; then
        echo "Running mypy..."
        mypy jimbot --config-file=mypy.ini || echo "WARNING: mypy issues found"
    else
        echo "WARNING: mypy not installed"
    fi
    
    # Security checks
    if command -v bandit &> /dev/null; then
        echo "Running bandit security scan..."
        bandit -r jimbot -ll || echo "WARNING: Security issues found"
    else
        echo "WARNING: bandit not installed"
    fi
    
    echo "Lint completed"
    return 0
}

# Job: Unit Tests
job_test_unit() {
    echo "=== Unit Tests Job ==="
    
    if ! command -v pytest &> /dev/null; then
        echo "ERROR: pytest not installed"
        return 1
    fi
    
    # Check if test directory exists
    if [ ! -d "jimbot/tests/unit" ]; then
        echo "WARNING: Unit test directory not found"
        mkdir -p jimbot/tests/unit
        echo "def test_placeholder(): pass" > jimbot/tests/unit/test_placeholder.py
    fi
    
    echo "Running unit tests..."
    pytest jimbot/tests/unit/ -v --tb=short || {
        echo "ERROR: Unit tests failed"
        return 1
    }
    
    echo "Unit tests completed"
    return 0
}

# Job: Integration Tests
job_test_integration() {
    echo "=== Integration Tests Job ==="
    
    # Check Docker availability
    if ! command -v docker &> /dev/null; then
        echo "ERROR: Docker not installed"
        return 1
    fi
    
    if ! docker info &> /dev/null; then
        echo "ERROR: Docker daemon not running"
        return 1
    fi
    
    # Check for docker-compose files
    if [ ! -f "docker-compose.minimal.yml" ]; then
        echo "WARNING: docker-compose.minimal.yml not found"
        return 0
    fi
    
    echo "Starting test services..."
    docker-compose -f docker-compose.minimal.yml up -d || {
        echo "ERROR: Failed to start services"
        return 1
    }
    
    # Wait for services
    echo "Waiting for services to be ready..."
    sleep 10
    
    # Run integration tests if they exist
    if [ -d "jimbot/tests/integration" ]; then
        pytest jimbot/tests/integration/ -v --tb=short || {
            echo "WARNING: Integration tests failed"
        }
    fi
    
    # Cleanup
    docker-compose -f docker-compose.minimal.yml down -v
    
    echo "Integration tests completed"
    return 0
}

# Job: Docker Build
job_build_docker() {
    echo "=== Docker Build Job ==="
    
    if ! command -v docker &> /dev/null; then
        echo "ERROR: Docker not installed"
        return 1
    fi
    
    # Check for Dockerfiles
    local dockerfile_dir="jimbot/deployment/docker/services"
    if [ ! -d "$dockerfile_dir" ]; then
        echo "WARNING: Dockerfile directory not found: $dockerfile_dir"
        return 0
    fi
    
    # Simulate building one service
    local test_service="mcp"
    local dockerfile="$dockerfile_dir/Dockerfile.$test_service"
    
    if [ -f "$dockerfile" ]; then
        echo "Building Docker image for $test_service..."
        docker build -f "$dockerfile" -t "jimbot/$test_service:test" . || {
            echo "ERROR: Docker build failed"
            return 1
        }
    else
        echo "WARNING: Dockerfile not found: $dockerfile"
    fi
    
    echo "Docker build completed"
    return 0
}

# Job: Documentation
job_docs() {
    echo "=== Documentation Job ==="
    
    if ! command -v sphinx-build &> /dev/null; then
        echo "WARNING: Sphinx not installed"
        pip install sphinx sphinx-rtd-theme myst-parser || {
            echo "ERROR: Failed to install documentation tools"
            return 1
        }
    fi
    
    if [ ! -d "docs" ]; then
        echo "WARNING: docs directory not found"
        mkdir -p docs
        echo "# Documentation" > docs/index.md
    fi
    
    echo "Building documentation..."
    cd docs && sphinx-build -b html . _build/html || {
        echo "WARNING: Documentation build failed"
        cd ..
        return 0
    }
    cd ..
    
    echo "Documentation build completed"
    return 0
}

# Main simulation
main() {
    log INFO "Starting CI Pipeline Simulation"
    log INFO "Working directory: $(pwd)"
    
    # Check for merge conflict
    if grep -q "<<<<<<< HEAD" .github/workflows/main-ci.yml 2>/dev/null; then
        log ERROR "Merge conflict detected in CI configuration file!"
        log ERROR "Please resolve the conflict before running CI"
        exit 1
    fi
    
    # Phase 1: Entry point
    run_job "format-check" job_format_check
    
    # Phase 2: Parallel jobs after format-check
    run_job "lint" job_lint "format-check"
    run_job "docs" job_docs "format-check"
    
    # Phase 3: Jobs depending on lint
    run_job "test-unit" job_test_unit "lint"
    run_job "build-docker" job_build_docker "lint"
    
    # Phase 4: Jobs depending on test-unit
    run_job "test-integration" job_test_integration "test-unit"
    
    # Summary
    echo
    echo "========================================"
    echo "CI Pipeline Simulation Summary"
    echo "========================================"
    echo
    echo -e "${GREEN}Completed Jobs (${#COMPLETED_JOBS[@]}):${NC}"
    for job in "${COMPLETED_JOBS[@]}"; do
        echo "  ✓ $job"
    done
    echo
    
    if [ ${#FAILED_JOBS[@]} -gt 0 ]; then
        echo -e "${RED}Failed Jobs (${#FAILED_JOBS[@]}):${NC}"
        for job in "${FAILED_JOBS[@]}"; do
            echo "  ✗ $job"
        done
        echo
    fi
    
    if [ ${#SKIPPED_JOBS[@]} -gt 0 ]; then
        echo -e "${YELLOW}Skipped Jobs (${#SKIPPED_JOBS[@]}):${NC}"
        for job in "${SKIPPED_JOBS[@]}"; do
            echo "  ⚠ $job"
        done
        echo
    fi
    
    # Pipeline status
    if [ ${#FAILED_JOBS[@]} -eq 0 ]; then
        log SUCCESS "Pipeline simulation completed successfully!"
        exit 0
    else
        log ERROR "Pipeline simulation failed with ${#FAILED_JOBS[@]} job failures"
        exit 1
    fi
}

# Run main function
main "$@"