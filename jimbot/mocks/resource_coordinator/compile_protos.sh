#!/bin/bash
# Compile protocol buffer files for the Resource Coordinator

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$SCRIPT_DIR/../../.."

echo "Compiling proto files..."

# Ensure we're in the project root
cd "$PROJECT_ROOT"

# Compile the resource coordinator proto
python -m grpc_tools.protoc \
    -I. \
    --python_out=. \
    --grpc_python_out=. \
    jimbot/proto/resource_coordinator.proto

# Also compile balatro_events.proto if it exists
if [ -f "jimbot/proto/balatro_events.proto" ]; then
    python -m grpc_tools.protoc \
        -I. \
        --python_out=. \
        --grpc_python_out=. \
        jimbot/proto/balatro_events.proto
fi

echo "Proto compilation complete!"

# Create __init__.py in proto directory if it doesn't exist
if [ ! -f "jimbot/proto/__init__.py" ]; then
    echo "# Proto package" > jimbot/proto/__init__.py
fi

echo "Ready to run the mock Resource Coordinator!"