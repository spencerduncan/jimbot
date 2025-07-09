#!/bin/bash
# Test script to verify Docker CI build for event-bus-rust

set -e

echo "=== Testing Docker CI Build for event-bus-rust ==="

# Build the Docker CI image
echo "Building Docker CI image..."
docker build -f docker/Dockerfile.ci-unified --target ci -t jimbot-ci-test:latest .

# Run the Rust build in the Docker container
echo "Running Rust build in Docker..."
docker run --rm -v $(pwd):/workspace jimbot-ci-test:latest bash -c "
    cd /workspace
    echo '=== Environment Info ==='
    echo 'Working directory:' \$(pwd)
    echo 'CI env var:' \$CI
    echo 'Directory structure:'
    ls -la
    echo
    echo '=== Proto files location ==='
    find . -name '*.proto' | head -10
    echo
    echo '=== Building event-bus-rust ==='
    cd services/event-bus-rust
    cargo build --verbose 2>&1 | head -50
"