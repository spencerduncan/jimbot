#!/bin/bash
# Quick test script to validate Docker-based Lua testing environment

set -e

print_color() {
    echo -e "${1}${2}\033[0m"
}

print_section() {
    echo
    print_color "\033[0;34m" "=== $1 ==="
    echo
}

# Change to project root
cd "$(dirname "${BASH_SOURCE[0]}")/.."

print_section "DOCKER LUA TESTING VALIDATION"

# Check if Docker is available
if ! command -v docker >/dev/null 2>&1; then
    print_color "\033[0;31m" "Error: Docker is not installed"
    exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
    print_color "\033[0;31m" "Error: Docker Compose is not available"
    exit 1
fi

print_color "\033[0;32m" "✓ Docker and Docker Compose are available"

# Check required files
print_section "CHECKING FILES"

required_files=(
    "docker/Dockerfile.lua-test"
    "docker/docker-compose.lua-test.yml"
    "ci/scripts/run-lua-tests.sh"
    "tests/test_helper.lua"
    "tests/run_tests.lua"
)

for file in "${required_files[@]}"; do
    if [[ -f "$file" ]]; then
        print_color "\033[0;32m" "✓ $file exists"
    else
        print_color "\033[0;31m" "✗ $file missing"
        exit 1
    fi
done

# Validate Docker Compose file
print_section "VALIDATING DOCKER COMPOSE"

if docker compose -f docker/docker-compose.lua-test.yml config >/dev/null 2>&1; then
    print_color "\033[0;32m" "✓ Docker Compose file is valid"
else
    print_color "\033[0;31m" "✗ Docker Compose file is invalid"
    exit 1
fi

print_section "VALIDATION COMPLETE"
print_color "\033[0;32m" "🎉 Docker-based Lua testing environment is ready!"