#!/bin/bash
# Generate Protocol Buffer code for multiple languages

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Base directories
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
PROTO_DIR="$SCRIPT_DIR"
OUTPUT_BASE="$PROJECT_ROOT/generated"

# Create output directories
echo -e "${YELLOW}Creating output directories...${NC}"
mkdir -p "$OUTPUT_BASE/python/jimbot/proto"
mkdir -p "$OUTPUT_BASE/rust/src/proto"
mkdir -p "$OUTPUT_BASE/typescript/src/proto"

# Check if protoc is installed
if ! command -v protoc &> /dev/null; then
    echo -e "${RED}protoc is not installed. Please install Protocol Buffers compiler.${NC}"
    exit 1
fi

# Check if buf is installed (optional but recommended)
if command -v buf &> /dev/null; then
    echo -e "${GREEN}Using buf for code generation...${NC}"
    USE_BUF=true
else
    echo -e "${YELLOW}buf not found, using protoc directly...${NC}"
    USE_BUF=false
fi

# Python generation
echo -e "${YELLOW}Generating Python code...${NC}"
if [ "$USE_BUF" = true ]; then
    cd "$PROJECT_ROOT"
    buf generate --template buf.gen.python.yaml
else
    protoc \
        --proto_path="$PROTO_DIR" \
        --proto_path="$PROJECT_ROOT" \
        --python_out="$OUTPUT_BASE/python" \
        --pyi_out="$OUTPUT_BASE/python" \
        "$PROTO_DIR"/*.proto
fi

# Copy Python files to the main project
cp -r "$OUTPUT_BASE/python/jimbot/proto/"* "$PROJECT_ROOT/jimbot/proto/"
touch "$PROJECT_ROOT/jimbot/proto/__init__.py"

# Rust generation (if rust-protobuf is installed)
if command -v protoc-gen-rust &> /dev/null; then
    echo -e "${YELLOW}Generating Rust code...${NC}"
    if [ "$USE_BUF" = true ]; then
        cd "$PROJECT_ROOT"
        buf generate --template buf.gen.rust.yaml
    else
        protoc \
            --proto_path="$PROTO_DIR" \
            --proto_path="$PROJECT_ROOT" \
            --rust_out="$OUTPUT_BASE/rust/src/proto" \
            "$PROTO_DIR"/*.proto
    fi
    
    # Create mod.rs for Rust
    echo "// Auto-generated module declarations" > "$OUTPUT_BASE/rust/src/proto/mod.rs"
    for proto in "$PROTO_DIR"/*.proto; do
        basename=$(basename "$proto" .proto)
        echo "pub mod $basename;" >> "$OUTPUT_BASE/rust/src/proto/mod.rs"
    done
else
    echo -e "${YELLOW}Skipping Rust generation (protoc-gen-rust not found)${NC}"
fi

# TypeScript generation (if protoc-gen-ts is installed)
if command -v protoc-gen-ts &> /dev/null; then
    echo -e "${YELLOW}Generating TypeScript code...${NC}"
    if [ "$USE_BUF" = true ]; then
        cd "$PROJECT_ROOT"
        buf generate --template buf.gen.typescript.yaml
    else
        protoc \
            --proto_path="$PROTO_DIR" \
            --proto_path="$PROJECT_ROOT" \
            --plugin="protoc-gen-ts=$(which protoc-gen-ts)" \
            --ts_out="$OUTPUT_BASE/typescript/src/proto" \
            --js_out="import_style=commonjs,binary:$OUTPUT_BASE/typescript/src/proto" \
            "$PROTO_DIR"/*.proto
    fi
    
    # Create index.ts
    echo "// Auto-generated exports" > "$OUTPUT_BASE/typescript/src/proto/index.ts"
    for proto in "$PROTO_DIR"/*.proto; do
        basename=$(basename "$proto" .proto)
        echo "export * from './$basename';" >> "$OUTPUT_BASE/typescript/src/proto/index.ts"
    done
else
    echo -e "${YELLOW}Skipping TypeScript generation (protoc-gen-ts not found)${NC}"
fi

# Generate documentation
if command -v protoc-gen-doc &> /dev/null; then
    echo -e "${YELLOW}Generating documentation...${NC}"
    protoc \
        --proto_path="$PROTO_DIR" \
        --proto_path="$PROJECT_ROOT" \
        --doc_out="$OUTPUT_BASE/docs" \
        --doc_opt=markdown,proto_docs.md \
        "$PROTO_DIR"/*.proto
else
    echo -e "${YELLOW}Skipping documentation generation (protoc-gen-doc not found)${NC}"
fi

echo -e "${GREEN}Code generation complete!${NC}"
echo -e "${GREEN}Generated files in: $OUTPUT_BASE${NC}"

# Summary
echo -e "\n${YELLOW}Summary:${NC}"
echo -e "- Python files copied to: $PROJECT_ROOT/jimbot/proto/"
[ -d "$OUTPUT_BASE/rust" ] && echo -e "- Rust files in: $OUTPUT_BASE/rust/src/proto/"
[ -d "$OUTPUT_BASE/typescript" ] && echo -e "- TypeScript files in: $OUTPUT_BASE/typescript/src/proto/"
[ -f "$OUTPUT_BASE/docs/proto_docs.md" ] && echo -e "- Documentation in: $OUTPUT_BASE/docs/proto_docs.md"