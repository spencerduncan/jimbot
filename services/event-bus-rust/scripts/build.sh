#!/bin/bash
# Build script for the Rust Event Bus

set -e

echo "Building Rust Event Bus..."

# Check if we're in the right directory
if [ ! -f "Cargo.toml" ]; then
    echo "Error: Cargo.toml not found. Please run this script from the event-bus-rust directory."
    exit 1
fi

# Build using Docker if cargo is not available
if ! command -v cargo &> /dev/null; then
    echo "Cargo not found, building with Docker..."
    
    # Build the Docker image
    docker build -t jimbot-event-bus:latest \
        --build-arg RUST_LOG=debug \
        -f Dockerfile \
        ../..
    
    echo "Docker build completed!"
    echo "To run: docker run -p 8080:8080 -p 50051:50051 jimbot-event-bus:latest"
else
    echo "Building with cargo..."
    
    # Install dependencies and build
    cargo build --release
    
    echo "Build completed!"
    echo "Binary location: target/release/event-bus-rust"
fi