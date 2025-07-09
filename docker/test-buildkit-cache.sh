#!/bin/bash
# Script to test BuildKit cache mount effectiveness

set -e

echo "Testing BuildKit apt cache mount effectiveness..."
echo

# Check if BuildKit is enabled
if [ -z "$DOCKER_BUILDKIT" ] || [ "$DOCKER_BUILDKIT" != "1" ]; then
    echo "WARNING: DOCKER_BUILDKIT is not set to 1"
    echo "Please run: export DOCKER_BUILDKIT=1"
    echo "Continuing anyway..."
    echo
fi

# Create a temporary test Dockerfile
TEST_DIR=$(mktemp -d)
cat > "$TEST_DIR/Dockerfile" << 'EOF'
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

# Install packages with BuildKit cache mount
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

CMD echo "Build successful!"
EOF

cd "$TEST_DIR"

echo "First build (cache will be populated):"
echo "======================================"
time docker build -t buildkit-cache-test:1 .
echo

echo "Second build (should use cache):"
echo "================================"
time docker build -t buildkit-cache-test:2 .
echo

echo "Cleaning up..."
docker rmi buildkit-cache-test:1 buildkit-cache-test:2 >/dev/null 2>&1 || true
rm -rf "$TEST_DIR"

echo "Test complete! The second build should be significantly faster than the first."
echo "If both builds took similar time, BuildKit cache mounts may not be working properly."