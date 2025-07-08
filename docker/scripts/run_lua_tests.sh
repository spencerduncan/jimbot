#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_color() {
    echo -e "${1}${2}${NC}"
}

# Function to print section headers
print_section() {
    echo
    print_color "$BLUE" "====================================="
    print_color "$BLUE" "    $1"
    print_color "$BLUE" "====================================="
    echo
}

# Initialize test results
OVERALL_SUCCESS=true
FAILED_TESTS=()

# Test environment information
print_section "LUA TESTING ENVIRONMENT"
print_color "$GREEN" "Lua version: $(lua -v)"
print_color "$GREEN" "LuaRocks version: $(luarocks --version | head -1)"
print_color "$GREEN" "Available Lua packages:"
luarocks list --installed

# Style check with StyLua
print_section "STYLE CHECKS"
if find . -name "*.lua" -type f | xargs stylua --check 2>/dev/null; then
    print_color "$GREEN" "✓ Style check passed"
else
    print_color "$RED" "✗ Style check failed"
    OVERALL_SUCCESS=false
    FAILED_TESTS+=("style-check")
fi

# Lint check with Luacheck
print_section "LINT CHECKS"
if find . -name "*.lua" -type f | xargs luacheck --config .luacheckrc 2>/dev/null; then
    print_color "$GREEN" "✓ Lint check passed"
else
    print_color "$RED" "✗ Lint check failed"
    OVERALL_SUCCESS=false
    FAILED_TESTS+=("lint-check")
fi

# Run unit tests (shop navigation test suite)
print_section "UNIT TESTS - SHOP NAVIGATION"
if [ -f "tests/run_tests.lua" ]; then
    if lua tests/run_tests.lua; then
        print_color "$GREEN" "✓ Shop navigation unit tests passed"
    else
        print_color "$RED" "✗ Shop navigation unit tests failed"
        OVERALL_SUCCESS=false
        FAILED_TESTS+=("shop-navigation-tests")
    fi
else
    print_color "$YELLOW" "⚠ Shop navigation test suite not found"
fi

# Run integration tests (game state test suite)
print_section "INTEGRATION TESTS - GAME STATE"
if [ -f "tests/run_all_tests.lua" ]; then
    if lua tests/run_all_tests.lua; then
        print_color "$GREEN" "✓ Game state integration tests passed"
    else
        print_color "$RED" "✗ Game state integration tests failed"
        OVERALL_SUCCESS=false
        FAILED_TESTS+=("game-state-tests")
    fi
else
    print_color "$YELLOW" "⚠ Game state test suite not found"
fi

# Run any Busted tests if they exist
print_section "BUSTED TESTS"
if find . -name "*_spec.lua" -type f | grep -q .; then
    if busted --verbose; then
        print_color "$GREEN" "✓ Busted tests passed"
    else
        print_color "$RED" "✗ Busted tests failed"
        OVERALL_SUCCESS=false
        FAILED_TESTS+=("busted-tests")
    fi
else
    print_color "$YELLOW" "⚠ No Busted test files found"
fi

# Coverage report (if enabled)
print_section "COVERAGE REPORT"
if command -v luacov >/dev/null 2>&1; then
    if luacov 2>/dev/null; then
        print_color "$GREEN" "✓ Coverage report generated"
        if [ -f luacov.report.out ]; then
            echo "Coverage Summary:"
            head -20 luacov.report.out
        fi
    else
        print_color "$YELLOW" "⚠ Coverage report generation failed"
    fi
else
    print_color "$YELLOW" "⚠ Coverage reporting not available"
fi

# Final summary
print_section "TEST SUMMARY"
if [ "$OVERALL_SUCCESS" = true ]; then
    print_color "$GREEN" "✓ All Lua tests passed successfully!"
    exit 0
else
    print_color "$RED" "✗ Some tests failed:"
    for test in "${FAILED_TESTS[@]}"; do
        print_color "$RED" "  - $test"
    done
    exit 1
fi