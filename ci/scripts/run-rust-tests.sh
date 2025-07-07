#!/bin/bash
# Rust test runner for Docker CI environment
# Migrated from native CI to Docker for consistency

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Rust Test Suite (Docker CI) ===${NC}"

# Ensure we're in the right directory
cd /workspace

# Set up Rust environment
export RUST_BACKTRACE=1
export CARGO_TERM_COLOR=always

# Function to run tests with proper error handling
run_test() {
    local test_name="$1"
    local test_cmd="$2"
    
    echo -e "${YELLOW}Running $test_name...${NC}"
    
    if eval "$test_cmd"; then
        echo -e "${GREEN}✅ $test_name passed${NC}"
        return 0
    else
        echo -e "${RED}❌ $test_name failed${NC}"
        return 1
    fi
}

# Check if Rust components exist
RUST_COMPONENTS_FOUND=false
if [ -f "Cargo.toml" ] || [ -f "services/event-bus-rust/Cargo.toml" ] || [ -f "jimbot/memgraph/mage_modules/Cargo.toml" ]; then
    RUST_COMPONENTS_FOUND=true
fi

if [ "$RUST_COMPONENTS_FOUND" = false ]; then
    echo -e "${YELLOW}No Rust components found, skipping Rust tests${NC}"
    exit 0
fi

# Install/update Rust toolchain components
echo -e "${YELLOW}Checking Rust toolchain...${NC}"
rustc --version
cargo --version

# Update dependencies
echo -e "${YELLOW}Updating Rust dependencies...${NC}"
if [ -f "Cargo.toml" ]; then
    cargo fetch
fi

# Run tests for main Rust components
if [ -f "Cargo.toml" ]; then
    run_test "Main Rust Tests" "
        cargo test --all-features --verbose
    "
    
    # Run with nextest if available (faster parallel testing)
    if cargo nextest --version >/dev/null 2>&1; then
        run_test "Nextest Suite" "
            cargo nextest run --all-features --verbose
        "
    fi
    
    # Generate coverage with tarpaulin
    run_test "Coverage Generation" "
        cargo tarpaulin \
            --all-features \
            --timeout 300 \
            --out Xml \
            --output-dir coverage \
            --exclude-files 'target/*' \
            --verbose
    "
fi

# Test Rust services separately
for service_dir in services/*/; do
    if [ -f "$service_dir/Cargo.toml" ]; then
        service_name=$(basename "$service_dir")
        echo -e "${YELLOW}Testing Rust service: $service_name${NC}"
        
        cd "$service_dir"
        
        # Run unit tests only for lightweight CI
        run_test "$service_name Unit Tests" "
            cargo test --bins --verbose
        "
        
        cd /workspace
    fi
done

# Test memgraph mage modules if they exist
if [ -f "jimbot/memgraph/mage_modules/Cargo.toml" ]; then
    echo -e "${YELLOW}Testing Memgraph MAGE modules${NC}"
    cd jimbot/memgraph/mage_modules
    
    run_test "MAGE Modules Tests" "
        cargo test --verbose
    "
    
    cd /workspace
fi

# Run security audit, formatting, and linting for each Rust component
echo -e "${YELLOW}Running security audit, formatting, and linting checks...${NC}"

# Function to run checks on a specific Rust project
run_checks_for_project() {
    local project_dir="$1"
    local project_name="$2"
    
    if [ -f "$project_dir/Cargo.toml" ]; then
        echo -e "${YELLOW}Running checks for $project_name${NC}"
        cd "$project_dir"
        
        # Security audit
        if cargo audit --version >/dev/null 2>&1; then
            run_test "$project_name Security Audit" "
                cargo audit --deny warnings
            "
        fi
        
        # Check formatting
        run_test "$project_name Format Check" "
            cargo fmt -- --check
        "
        
        # Run clippy lints
        run_test "$project_name Clippy Lints" "
            cargo clippy --all-targets --all-features -- -D warnings
        "
        
        cd /workspace
    fi
}

# Run checks for event-bus-rust
run_checks_for_project "services/event-bus-rust" "Event Bus"

# Run checks for memgraph mage modules
run_checks_for_project "jimbot/memgraph/mage_modules" "MAGE Modules"

echo -e "${GREEN}=== Rust tests completed successfully! ===${NC}"