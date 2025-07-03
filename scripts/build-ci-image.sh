#!/bin/bash
# Build and validate CI Docker image
# This script builds the CI image with proper versioning and validates all tools

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
DOCKERFILE_PATH="${PROJECT_ROOT}/jimbot/deployment/docker/ci/Dockerfile.ci"
TOOL_VERSIONS_FILE="${PROJECT_ROOT}/.github/tool-versions.yml"
IMAGE_NAME="jimbot/ci-tools"
REGISTRY="ghcr.io"

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    local missing_tools=()
    
    # Check for required tools
    for tool in docker yq jq; do
        if ! command -v "$tool" &> /dev/null; then
            missing_tools+=("$tool")
        fi
    done
    
    if [ ${#missing_tools[@]} -ne 0 ]; then
        print_error "Missing required tools: ${missing_tools[*]}"
        print_error "Please install them before running this script."
        exit 1
    fi
    
    # Check Docker daemon
    if ! docker info &> /dev/null; then
        print_error "Docker daemon is not running"
        exit 1
    fi
    
    print_status "Prerequisites check passed"
}

# Parse tool versions from YAML
parse_versions() {
    print_status "Parsing tool versions from ${TOOL_VERSIONS_FILE}..."
    
    # Export versions as environment variables
    export PYTHON_VERSION=$(yq e '.python.version' "$TOOL_VERSIONS_FILE")
    export LUA_VERSION=$(yq e '.lua.version' "$TOOL_VERSIONS_FILE")
    export GO_VERSION=$(yq e '.go.version' "$TOOL_VERSIONS_FILE")
    export STYLUA_VERSION=$(yq e '.lua_tools.stylua' "$TOOL_VERSIONS_FILE")
    export BUF_VERSION=$(yq e '.protobuf.buf' "$TOOL_VERSIONS_FILE")
    export PROTOC_VERSION=$(yq e '.protobuf.protoc' "$TOOL_VERSIONS_FILE")
    export CMAKE_VERSION=$(yq e '.cpp_tools.cmake' "$TOOL_VERSIONS_FILE")
    
    print_status "Parsed versions:"
    echo "  Python: $PYTHON_VERSION"
    echo "  Lua: $LUA_VERSION"
    echo "  Go: $GO_VERSION"
    echo "  StyLua: $STYLUA_VERSION"
    echo "  Buf: $BUF_VERSION"
    echo "  Protoc: $PROTOC_VERSION"
    echo "  CMake: $CMAKE_VERSION"
}

# Calculate version tag based on tool versions
calculate_version_tag() {
    local version_string="${PYTHON_VERSION}-${LUA_VERSION}-${GO_VERSION}"
    local version_hash=$(echo -n "$version_string" | sha256sum | cut -c1-8)
    export VERSION_TAG="1.0.0-${version_hash}"
    print_status "Calculated version tag: $VERSION_TAG"
}

# Build the Docker image
build_image() {
    print_status "Building Docker image..."
    
    local build_args=(
        --build-arg "PYTHON_VERSION=${PYTHON_VERSION}"
        --build-arg "LUA_VERSION=${LUA_VERSION}"
        --build-arg "GO_VERSION=${GO_VERSION}"
        --build-arg "STYLUA_VERSION=${STYLUA_VERSION}"
        --build-arg "BUF_VERSION=${BUF_VERSION}"
        --build-arg "PROTOC_VERSION=${PROTOC_VERSION}"
        --build-arg "CMAKE_VERSION=${CMAKE_VERSION}"
    )
    
    # Build with multiple tags
    docker build \
        "${build_args[@]}" \
        -t "${IMAGE_NAME}:latest" \
        -t "${IMAGE_NAME}:${VERSION_TAG}" \
        -f "$DOCKERFILE_PATH" \
        "$PROJECT_ROOT"
    
    print_status "Docker image built successfully"
}

# Validate the built image
validate_image() {
    print_status "Validating Docker image..."
    
    local validation_failed=false
    
    # Define tools to check with their expected commands
    declare -A tool_checks=(
        ["Python"]="python --version"
        ["Lua"]="lua -v"
        ["Go"]="go version"
        ["CMake"]="cmake --version"
        ["Protoc"]="protoc --version"
        ["Buf"]="buf --version"
        ["StyLua"]="stylua --version"
        ["Black"]="black --version"
        ["Flake8"]="flake8 --version"
        ["MyPy"]="mypy --version"
        ["LuaCheck"]="luacheck --version"
        ["Clang-Format"]="clang-format-15 --version"
        ["Clang-Tidy"]="clang-tidy-15 --version"
        ["CppCheck"]="cppcheck --version"
    )
    
    # Run validation checks
    for tool in "${!tool_checks[@]}"; do
        print_status "Checking $tool..."
        if docker run --rm "${IMAGE_NAME}:latest" bash -c "${tool_checks[$tool]}" &> /dev/null; then
            echo -e "  ${GREEN}✓${NC} $tool is working"
        else
            echo -e "  ${RED}✗${NC} $tool check failed"
            validation_failed=true
        fi
    done
    
    # Check image size
    local image_size=$(docker image inspect "${IMAGE_NAME}:latest" --format='{{.Size}}' | numfmt --to=iec)
    print_status "Image size: $image_size"
    
    # Warn if image is too large
    local size_mb=$(docker image inspect "${IMAGE_NAME}:latest" --format='{{.Size}}' | awk '{print int($1/1024/1024)}')
    if [ "$size_mb" -gt 2048 ]; then
        print_warning "Image size exceeds 2GB. Consider optimizing the Dockerfile."
    fi
    
    if [ "$validation_failed" = true ]; then
        print_error "Image validation failed"
        exit 1
    fi
    
    print_status "Image validation passed"
}

# Run smoke tests
run_smoke_tests() {
    print_status "Running smoke tests..."
    
    # Test Python linting
    docker run --rm -v "${PROJECT_ROOT}:/workspace" -w /workspace "${IMAGE_NAME}:latest" \
        bash -c "echo 'print(1)' | black --check -" || true
    
    # Test Lua formatting
    docker run --rm -v "${PROJECT_ROOT}:/workspace" -w /workspace "${IMAGE_NAME}:latest" \
        bash -c "echo 'local x = 1' | stylua --check -" || true
    
    # Test C++ formatting
    docker run --rm -v "${PROJECT_ROOT}:/workspace" -w /workspace "${IMAGE_NAME}:latest" \
        bash -c "echo 'int main() { return 0; }' | clang-format-15" || true
    
    print_status "Smoke tests completed"
}

# Push image to registry (optional)
push_image() {
    if [ "${PUSH_TO_REGISTRY:-false}" = "true" ]; then
        print_status "Pushing image to registry..."
        
        # Tag for registry
        docker tag "${IMAGE_NAME}:latest" "${REGISTRY}/${IMAGE_NAME}:latest"
        docker tag "${IMAGE_NAME}:${VERSION_TAG}" "${REGISTRY}/${IMAGE_NAME}:${VERSION_TAG}"
        
        # Push to registry
        docker push "${REGISTRY}/${IMAGE_NAME}:latest"
        docker push "${REGISTRY}/${IMAGE_NAME}:${VERSION_TAG}"
        
        print_status "Image pushed to registry"
    else
        print_status "Skipping registry push (set PUSH_TO_REGISTRY=true to enable)"
    fi
}

# Generate usage report
generate_report() {
    print_status "Generating build report..."
    
    local report_file="${PROJECT_ROOT}/ci-image-build-report.md"
    
    cat > "$report_file" << EOF
# CI Docker Image Build Report

Generated: $(date -u +'%Y-%m-%d %H:%M:%S UTC')

## Image Details
- **Name**: ${IMAGE_NAME}
- **Version**: ${VERSION_TAG}
- **Size**: $(docker image inspect "${IMAGE_NAME}:latest" --format='{{.Size}}' | numfmt --to=iec)
- **Base**: Ubuntu 22.04

## Tool Versions
$(docker run --rm "${IMAGE_NAME}:latest" cat /etc/ci-image-info)

## Layers
\`\`\`
$(docker history "${IMAGE_NAME}:latest" --format "table {{.CreatedBy}}\t{{.Size}}" | head -20)
\`\`\`

## Usage Examples

### Format Checking
\`\`\`bash
docker run --rm -v \$PWD:/workspace ${IMAGE_NAME}:latest black --check .
docker run --rm -v \$PWD:/workspace ${IMAGE_NAME}:latest stylua --check .
\`\`\`

### Linting
\`\`\`bash
docker run --rm -v \$PWD:/workspace ${IMAGE_NAME}:latest flake8 .
docker run --rm -v \$PWD:/workspace ${IMAGE_NAME}:latest luacheck .
\`\`\`

### In GitHub Actions
\`\`\`yaml
jobs:
  lint:
    runs-on: ubuntu-latest
    container:
      image: ${REGISTRY}/${IMAGE_NAME}:${VERSION_TAG}
    steps:
      - uses: actions/checkout@v4
      - run: make lint
\`\`\`
EOF
    
    print_status "Build report generated: $report_file"
}

# Main execution
main() {
    print_status "Starting CI Docker image build process..."
    
    check_prerequisites
    parse_versions
    calculate_version_tag
    build_image
    validate_image
    run_smoke_tests
    push_image
    generate_report
    
    print_status "CI Docker image build completed successfully!"
    echo
    echo "Image tags:"
    echo "  - ${IMAGE_NAME}:latest"
    echo "  - ${IMAGE_NAME}:${VERSION_TAG}"
    
    if [ "${PUSH_TO_REGISTRY:-false}" = "true" ]; then
        echo "  - ${REGISTRY}/${IMAGE_NAME}:latest"
        echo "  - ${REGISTRY}/${IMAGE_NAME}:${VERSION_TAG}"
    fi
}

# Run main function
main "$@"