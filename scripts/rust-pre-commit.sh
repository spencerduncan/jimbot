#!/bin/bash
# Pre-commit script for Rust components
# Run this script before committing to ensure CI/CD will pass

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_step() {
    echo -e "${BLUE}==>${NC} $1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to install Rust tools if missing
install_rust_tools() {
    local tools_needed=()
    
    if ! command_exists cargo-fmt; then
        tools_needed+=("rustfmt")
    fi
    
    if ! command_exists cargo-clippy; then
        tools_needed+=("clippy")
    fi
    
    if ! command_exists cargo-audit; then
        tools_needed+=("cargo-audit")
    fi
    
    if ! command_exists cargo-tarpaulin; then
        tools_needed+=("cargo-tarpaulin")
    fi
    
    if [ ${#tools_needed[@]} -gt 0 ]; then
        print_step "Installing missing Rust tools: ${tools_needed[*]}"
        
        # Install rustfmt and clippy via rustup
        if [[ " ${tools_needed[*]} " =~ " rustfmt " ]]; then
            rustup component add rustfmt
        fi
        
        if [[ " ${tools_needed[*]} " =~ " clippy " ]]; then
            rustup component add clippy
        fi
        
        # Install cargo tools
        if [[ " ${tools_needed[*]} " =~ " cargo-audit " ]]; then
            cargo install cargo-audit
        fi
        
        if [[ " ${tools_needed[*]} " =~ " cargo-tarpaulin " ]]; then
            cargo install cargo-tarpaulin
        fi
    fi
}

# Function to find all Rust components
find_rust_components() {
    find . -name "Cargo.toml" -not -path "./target/*" -not -path "*/target/*" | while read -r cargo_file; do
        dirname "$cargo_file"
    done
}

# Function to run checks for a single component
run_component_checks() {
    local component_dir="$1"
    local component_name
    component_name=$(basename "$component_dir")
    
    print_step "Checking Rust component: $component_name"
    
    cd "$component_dir"
    
    # Check formatting
    print_step "Running cargo fmt check..."
    if cargo fmt --all -- --check; then
        print_success "Formatting check passed"
    else
        print_error "Formatting check failed"
        print_warning "Run 'cargo fmt --all' to fix formatting issues"
        return 1
    fi
    
    # Run clippy
    print_step "Running clippy..."
    if cargo clippy --all-targets --all-features -- -D warnings; then
        print_success "Clippy check passed"
    else
        print_error "Clippy check failed"
        print_warning "Fix clippy warnings before committing"
        return 1
    fi
    
    # Build
    print_step "Building..."
    if cargo build --all-features; then
        print_success "Build successful"
    else
        print_error "Build failed"
        return 1
    fi
    
    # Run tests
    print_step "Running tests..."
    if cargo test --all-features; then
        print_success "Tests passed"
    else
        print_error "Tests failed"
        return 1
    fi
    
    # Security audit
    print_step "Running security audit..."
    if cargo audit; then
        print_success "Security audit passed"
    else
        print_warning "Security vulnerabilities found - check dependencies"
        # Don't fail on security audit, just warn
    fi
    
    # Generate coverage report (optional)
    if command_exists cargo-tarpaulin; then
        print_step "Generating coverage report..."
        if cargo tarpaulin --all-features --workspace --timeout 120 --out Html --output-dir ./coverage/ 2>/dev/null; then
            print_success "Coverage report generated in ./coverage/"
        else
            print_warning "Coverage report generation failed (non-critical)"
        fi
    else
        print_warning "cargo-tarpaulin not installed, skipping coverage"
    fi
    
    cd - >/dev/null
    return 0
}

# Main function
main() {
    echo -e "${BLUE}╔══════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║          Rust Pre-Commit Checks             ║${NC}"
    echo -e "${BLUE}╚══════════════════════════════════════════════╝${NC}"
    echo
    
    # Check if we're in a git repository
    if ! git rev-parse --git-dir >/dev/null 2>&1; then
        print_error "This script must be run from within a git repository"
        exit 1
    fi
    
    # Check if Rust is installed
    if ! command_exists cargo; then
        print_error "Rust/Cargo not found. Please install Rust first."
        exit 1
    fi
    
    # Install required tools
    install_rust_tools
    
    # Find all Rust components
    local components
    components=($(find_rust_components))
    
    if [ ${#components[@]} -eq 0 ]; then
        print_warning "No Rust components found in the repository"
        exit 0
    fi
    
    print_step "Found ${#components[@]} Rust component(s)"
    
    # Track overall success
    local overall_success=true
    local failed_components=()
    
    # Run checks for each component
    for component in "${components[@]}"; do
        if ! run_component_checks "$component"; then
            overall_success=false
            failed_components+=("$(basename "$component")")
        fi
        echo
    done
    
    # Summary
    echo -e "${BLUE}╔══════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║                   Summary                    ║${NC}"
    echo -e "${BLUE}╚══════════════════════════════════════════════╝${NC}"
    
    if [ "$overall_success" = true ]; then
        print_success "All pre-commit checks passed!"
        print_success "Your code is ready for commit and should pass CI/CD"
        exit 0
    else
        print_error "Pre-commit checks failed for: ${failed_components[*]}"
        print_error "Please fix the issues before committing"
        exit 1
    fi
}

# Run the script
main "$@"