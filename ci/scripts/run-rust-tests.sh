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
if [ ! -f "Cargo.toml" ] && [ ! -d "services/event-bus-rust" ]; then
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
        
        run_test "$service_name Unit Tests" "
            cargo test --verbose
        "
        
        # Run integration tests if they exist
        if [ -d "tests" ]; then
            run_test "$service_name Integration Tests" "
                cargo test --test '*integration*' --verbose
            "
        fi
        
        # Run benchmarks if they exist
        if [ -d "benches" ]; then
            run_test "$service_name Benchmarks" "
                cargo bench --verbose
            "
        fi
        
        cd /workspace
    fi
done

# Security audit
echo -e "${YELLOW}Running security audit...${NC}"
if cargo audit --version >/dev/null 2>&1; then
    run_test "Security Audit" "
        cargo audit --deny warnings
    "
else
    echo -e "${YELLOW}cargo-audit not available, skipping security audit${NC}"
fi

# Check formatting
run_test "Format Check" "
    cargo fmt --all -- --check
"

# Run clippy lints
run_test "Clippy Lints" "
    cargo clippy --all-targets --all-features -- -D warnings
"

echo -e "${GREEN}=== Rust tests completed successfully! ===${NC}"