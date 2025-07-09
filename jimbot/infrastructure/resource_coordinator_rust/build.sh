#!/bin/bash
set -e

# Build script for Resource Coordinator

echo "Building Resource Coordinator..."

# Check if running in Docker
if [ -f /.dockerenv ]; then
    echo "Running in Docker container"
    DOCKER_BUILD=true
else
    echo "Running on host"
    DOCKER_BUILD=false
fi

# Build mode (debug or release)
BUILD_MODE=${1:-release}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Build mode: $BUILD_MODE${NC}"

# Check dependencies
check_dependency() {
    if ! command -v $1 &> /dev/null; then
        echo -e "${RED}Error: $1 is not installed${NC}"
        exit 1
    fi
}

if [ "$DOCKER_BUILD" = false ]; then
    echo "Checking dependencies..."
    check_dependency cargo
    check_dependency protoc
fi

# Clean previous builds
echo "Cleaning previous builds..."
if [ -d "target" ]; then
    rm -rf target/$BUILD_MODE
fi

# Format code
if [ "$BUILD_MODE" = "release" ]; then
    echo "Formatting code..."
    cargo fmt --check || {
        echo -e "${YELLOW}Warning: Code is not properly formatted. Run 'cargo fmt'${NC}"
    }
fi

# Run clippy for linting
echo "Running clippy..."
cargo clippy -- -D warnings || {
    echo -e "${RED}Error: Clippy found issues${NC}"
    exit 1
}

# Build the project
echo "Building project..."
if [ "$BUILD_MODE" = "release" ]; then
    cargo build --release
    BINARY_PATH="target/release/resource-coordinator"
else
    cargo build
    BINARY_PATH="target/debug/resource-coordinator"
fi

# Run tests
echo "Running tests..."
cargo test || {
    echo -e "${RED}Error: Tests failed${NC}"
    exit 1
}

# Check binary size
if [ -f "$BINARY_PATH" ]; then
    SIZE=$(du -h "$BINARY_PATH" | cut -f1)
    echo -e "${GREEN}Build successful! Binary size: $SIZE${NC}"
    echo "Binary location: $BINARY_PATH"
else
    echo -e "${RED}Error: Binary not found at $BINARY_PATH${NC}"
    exit 1
fi

# Generate documentation
if [ "$BUILD_MODE" = "release" ]; then
    echo "Generating documentation..."
    cargo doc --no-deps
    echo "Documentation generated at: target/doc/"
fi

# Docker build
if [ "$2" = "--docker" ] || [ "$DOCKER_BUILD" = true ]; then
    echo "Building Docker image..."
    docker build -t jimbot/resource-coordinator:latest .
    echo -e "${GREEN}Docker image built successfully${NC}"
fi

echo -e "${GREEN}Build completed successfully!${NC}"