#!/bin/bash
# Script to generate code from Protocol Buffer schemas

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "Generating code from Protocol Buffer schemas..."

# Check if protoc is installed
if ! command -v protoc &> /dev/null; then
    echo "Error: protoc (Protocol Buffer compiler) is not installed."
    echo "Please install it from: https://grpc.io/docs/protoc-installation/"
    exit 1
fi

# Python generation
echo "Generating Python code..."
PYTHON_OUT="$PROJECT_ROOT/jimbot/proto"
mkdir -p "$PYTHON_OUT"

# Generate Python files with relative imports
protoc \
    --proto_path="$SCRIPT_DIR" \
    --python_out="$PYTHON_OUT" \
    "$SCRIPT_DIR"/jimbot/events/v1/*.proto

# Create __init__.py files for Python packages
touch "$PYTHON_OUT/__init__.py"
touch "$PYTHON_OUT/jimbot/__init__.py"
touch "$PYTHON_OUT/jimbot/events/__init__.py"
touch "$PYTHON_OUT/jimbot/events/v1/__init__.py"

# Rust generation (if prost is available)
if command -v cargo &> /dev/null; then
    echo "Generating Rust code..."
    RUST_OUT="$PROJECT_ROOT/services/event-bus-rust/src/proto"
    mkdir -p "$RUST_OUT"
    
    # Check if prost-build is in Cargo.toml
    if grep -q "prost-build" "$PROJECT_ROOT/services/event-bus-rust/Cargo.toml" 2>/dev/null; then
        # Use build.rs approach
        echo "Using build.rs for Rust code generation"
        cd "$PROJECT_ROOT/services/event-bus-rust"
        cargo build
    else
        echo "Warning: prost-build not found in Cargo.toml. Skipping Rust generation."
    fi
else
    echo "Skipping Rust generation (cargo not found)"
fi

# TypeScript generation (if protoc-gen-ts is available)
if command -v protoc-gen-ts &> /dev/null; then
    echo "Generating TypeScript code..."
    TS_OUT="$PROJECT_ROOT/jimbot/proto/typescript"
    mkdir -p "$TS_OUT"
    
    protoc \
        --proto_path="$SCRIPT_DIR" \
        --plugin="protoc-gen-ts=$(which protoc-gen-ts)" \
        --ts_out="$TS_OUT" \
        "$SCRIPT_DIR"/jimbot/events/v1/*.proto
else
    echo "Skipping TypeScript generation (protoc-gen-ts not found)"
fi

# Validate generated files
echo ""
echo "Code generation complete. Generated files:"
if [ -d "$PYTHON_OUT/jimbot/events/v1" ]; then
    echo "Python:"
    ls -la "$PYTHON_OUT/jimbot/events/v1/"*.py 2>/dev/null || echo "  No Python files generated"
fi

echo ""
echo "To use the generated code:"
echo "  Python: from jimbot.proto.jimbot.events.v1 import balatro_events_pb2"
echo "  Rust:   use crate::proto::jimbot::events::v1;"
echo ""
echo "Done!"