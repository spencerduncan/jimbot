#!/bin/bash
# Comprehensive CI Pipeline Failure Analysis Runner
# This script executes all failure tests and generates a complete report

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m'

# Configuration
REPORT_DIR="ci-failure-analysis-report-$(date +%Y%m%d-%H%M%S)"
SUMMARY_FILE="$REPORT_DIR/EXECUTIVE_SUMMARY.md"

# Create report directory
mkdir -p "$REPORT_DIR"

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%H:%M:%S')]${NC} $1" | tee -a "$REPORT_DIR/execution.log"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$REPORT_DIR/execution.log"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a "$REPORT_DIR/execution.log"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$REPORT_DIR/execution.log"
}

# Initialize summary
init_summary() {
    cat > "$SUMMARY_FILE" << 'EOF'
# CI Pipeline Failure Analysis Report

**Generated**: $(date)
**Working Directory**: $(pwd)
**System**: $(uname -a)

## Executive Summary

This report provides a comprehensive analysis of the CI pipeline failure points, cascades, and recovery mechanisms.

## Key Findings

### Critical Issues Identified

1. **Merge Conflict in CI Configuration**
   - File: `.github/workflows/main-ci.yml`
   - Impact: Complete pipeline failure
   - Priority: CRITICAL - Must be resolved immediately

2. **Single Points of Failure**
   - `format-check` job blocks entire pipeline
   - No fallback for network failures
   - Docker daemon dependency is critical

3. **Missing Recovery Mechanisms**
   - No automatic retry for network operations
   - Limited fallback strategies
   - No state persistence for recovery

## Test Results Summary
EOF
}

# Check environment
check_environment() {
    log "Checking environment..."
    
    {
        echo "### Environment Status"
        echo
        echo "| Component | Status | Version |"
        echo "|-----------|--------|---------|"
        
        # Check Python
        if command -v python3 &> /dev/null; then
            version=$(python3 --version 2>&1 | cut -d' ' -f2)
            echo "| Python | ✓ Available | $version |"
        else
            echo "| Python | ✗ Missing | N/A |"
        fi
        
        # Check Docker
        if command -v docker &> /dev/null && docker info &> /dev/null; then
            version=$(docker --version | cut -d' ' -f3 | sed 's/,$//')
            echo "| Docker | ✓ Running | $version |"
        else
            echo "| Docker | ✗ Not Available | N/A |"
        fi
        
        # Check Git
        if command -v git &> /dev/null; then
            version=$(git --version | cut -d' ' -f3)
            echo "| Git | ✓ Available | $version |"
        else
            echo "| Git | ✗ Missing | N/A |"
        fi
        
        # Check disk space
        available=$(df -h / | tail -1 | awk '{print $4}')
        echo "| Disk Space | ✓ | $available available |"
        
        # Check memory
        available=$(free -h | grep Mem | awk '{print $4}')
        echo "| Memory | ✓ | $available available |"
        
        echo
    } >> "$SUMMARY_FILE"
}

# Analyze CI configuration
analyze_ci_config() {
    log "Analyzing CI configuration..."
    
    {
        echo "### CI Configuration Analysis"
        echo
        
        if [ -f ".github/workflows/main-ci.yml" ]; then
            if grep -q "<<<<<<< HEAD" .github/workflows/main-ci.yml; then
                echo "❌ **CRITICAL**: Merge conflict detected in CI configuration!"
                echo
                echo "```"
                grep -n -A2 -B2 "<<<<<<< HEAD" .github/workflows/main-ci.yml || true
                echo "```"
            else
                echo "✓ CI configuration file is clean"
            fi
            
            # Count jobs
            job_count=$(grep -c "^\s*[a-zA-Z-]*:$" .github/workflows/main-ci.yml 2>/dev/null || echo "0")
            echo
            echo "- Total jobs defined: $job_count"
            echo "- Matrix strategies detected: $(grep -c "matrix:" .github/workflows/main-ci.yml 2>/dev/null || echo "0")"
            echo "- Conditional jobs: $(grep -c "if:" .github/workflows/main-ci.yml 2>/dev/null || echo "0")"
        else
            echo "❌ CI configuration file not found!"
        fi
        
        echo
    } >> "$SUMMARY_FILE"
}

# Run failure simulations
run_failure_simulations() {
    log "Running failure simulations..."
    
    {
        echo "### Failure Simulation Results"
        echo
        echo "| Test | Result | Details |"
        echo "|------|--------|---------|"
    } >> "$SUMMARY_FILE"
    
    # Make scripts executable
    chmod +x simulate-ci-pipeline.sh 2>/dev/null || true
    chmod +x test-ci-failures.py 2>/dev/null || true
    
    # Run CI simulation
    if [ -f "simulate-ci-pipeline.sh" ]; then
        log "Running CI pipeline simulation..."
        if ./simulate-ci-pipeline.sh > "$REPORT_DIR/simulation.log" 2>&1; then
            echo "| CI Simulation | ✓ Passed | Pipeline would succeed |" >> "$SUMMARY_FILE"
            success "CI simulation completed"
        else
            echo "| CI Simulation | ✗ Failed | See simulation.log |" >> "$SUMMARY_FILE"
            warning "CI simulation failed (expected for testing)"
        fi
    else
        echo "| CI Simulation | ⚠ Skipped | Script not found |" >> "$SUMMARY_FILE"
    fi
    
    # Run Python failure tests
    if [ -f "test-ci-failures.py" ]; then
        log "Running Python failure tests..."
        if python3 test-ci-failures.py > "$REPORT_DIR/failure-tests.log" 2>&1; then
            echo "| Failure Tests | ✓ Passed | All scenarios tested |" >> "$SUMMARY_FILE"
            success "Failure tests completed"
        else
            echo "| Failure Tests | ⚠ Partial | Some tests failed |" >> "$SUMMARY_FILE"
            warning "Some failure tests failed"
        fi
    else
        echo "| Failure Tests | ⚠ Skipped | Script not found |" >> "$SUMMARY_FILE"
    fi
    
    echo >> "$SUMMARY_FILE"
}

# Generate failure cascade visualization
generate_visualizations() {
    log "Generating visualizations..."
    
    {
        echo "### Failure Cascade Visualization"
        echo
        echo '```mermaid'
        echo 'graph TD'
        echo '    subgraph "Entry Point"'
        echo '        A[format-check]'
        echo '    end'
        echo '    '
        echo '    subgraph "Tier 2"'
        echo '        B[lint]'
        echo '        C[docs]'
        echo '    end'
        echo '    '
        echo '    subgraph "Tier 3"'
        echo '        D[test-unit]'
        echo '        E[build-docker]'
        echo '    end'
        echo '    '
        echo '    subgraph "Tier 4"'
        echo '        F[test-integration]'
        echo '        G[test-gpu]'
        echo '        H[benchmark]'
        echo '    end'
        echo '    '
        echo '    subgraph "Final"'
        echo '        I[release]'
        echo '    end'
        echo '    '
        echo '    A --> B'
        echo '    A --> C'
        echo '    B --> D'
        echo '    B --> E'
        echo '    D --> F'
        echo '    D --> G'
        echo '    E --> H'
        echo '    E --> I'
        echo '    F --> I'
        echo '    H --> I'
        echo '    '
        echo '    style A fill:#f9f,stroke:#333,stroke-width:4px'
        echo '    style I fill:#9f9,stroke:#333,stroke-width:4px'
        echo '```'
        echo
    } >> "$SUMMARY_FILE"
}

# Generate recommendations
generate_recommendations() {
    log "Generating recommendations..."
    
    {
        echo "## Recommendations"
        echo
        echo "### Immediate Actions (Priority: CRITICAL)"
        echo
        echo "1. **Resolve merge conflict in `.github/workflows/main-ci.yml`**"
        echo "   - This is blocking all CI operations"
        echo "   - Review both versions and merge appropriately"
        echo
        echo "2. **Add retry logic for network operations**"
        echo "   \`\`\`yaml"
        echo "   - name: Download with retry"
        echo "     run: |"
        echo "       for i in {1..3}; do"
        echo "         wget \$URL && break || sleep 5"
        echo "       done"
        echo "   \`\`\`"
        echo
        echo "3. **Implement job-level timeouts**"
        echo "   \`\`\`yaml"
        echo "   jobs:"
        echo "     test:"
        echo "       timeout-minutes: 30"
        echo "   \`\`\`"
        echo
        echo "### Short-term Improvements (Priority: HIGH)"
        echo
        echo "1. **Reduce single points of failure**"
        echo "   - Make format-check non-blocking for some jobs"
        echo "   - Add alternative paths for critical operations"
        echo
        echo "2. **Add health checks before jobs**"
        echo "   - Verify Docker daemon"
        echo "   - Check disk space"
        echo "   - Validate network connectivity"
        echo
        echo "3. **Implement partial success handling**"
        echo "   - Use \`continue-on-error\` for non-critical steps"
        echo "   - Add \`fail-fast: false\` to matrix strategies"
        echo
        echo "### Long-term Enhancements (Priority: MEDIUM)"
        echo
        echo "1. **Create fallback workflows**"
        echo "   - Minimal CI for when full pipeline fails"
        echo "   - Emergency release process"
        echo
        echo "2. **Add monitoring and alerting**"
        echo "   - Pipeline duration tracking"
        echo "   - Failure rate monitoring"
        echo "   - Resource usage alerts"
        echo
        echo "3. **Implement state persistence**"
        echo "   - Save job artifacts between runs"
        echo "   - Enable resumable pipelines"
        echo
    } >> "$SUMMARY_FILE"
}

# Generate detailed report sections
generate_detailed_reports() {
    log "Generating detailed reports..."
    
    # Copy all analysis files to report directory
    cp ci-pipeline-analysis.md "$REPORT_DIR/" 2>/dev/null || true
    cp ci-failure-cascade-analysis.md "$REPORT_DIR/" 2>/dev/null || true
    cp ci-failure-test-scenarios.yaml "$REPORT_DIR/" 2>/dev/null || true
    cp ci-failure-test-report.json "$REPORT_DIR/" 2>/dev/null || true
    
    # Generate index
    cat > "$REPORT_DIR/INDEX.md" << EOF
# CI Pipeline Failure Analysis - Complete Report

## Report Contents

1. [Executive Summary](EXECUTIVE_SUMMARY.md) - High-level findings and recommendations
2. [Pipeline Analysis](ci-pipeline-analysis.md) - Detailed job analysis
3. [Failure Cascades](ci-failure-cascade-analysis.md) - Cascade patterns and impacts
4. [Test Scenarios](ci-failure-test-scenarios.yaml) - Validation test definitions
5. [Execution Log](execution.log) - Raw execution output

## Quick Links

- [Critical Issues](#critical-issues)
- [Recommendations](#recommendations)
- [Test Results](#test-results)

## Report Generated
- **Date**: $(date)
- **Duration**: See execution.log
- **Status**: Complete
EOF
}

# Main execution
main() {
    echo -e "${PURPLE}=== CI Pipeline Failure Analysis ===${NC}"
    echo
    
    init_summary
    check_environment
    analyze_ci_config
    run_failure_simulations
    generate_visualizations
    generate_recommendations
    generate_detailed_reports
    
    # Final summary
    {
        echo
        echo "## Analysis Complete"
        echo
        echo "- Report generated in: \`$REPORT_DIR/\`"
        echo "- Total files: $(find "$REPORT_DIR" -type f | wc -l)"
        echo "- Key findings documented"
        echo "- Recommendations provided"
        echo
        echo "### Next Steps"
        echo
        echo "1. Review the executive summary"
        echo "2. Resolve critical issues"
        echo "3. Implement recommended fixes"
        echo "4. Re-run analysis to verify improvements"
    } >> "$SUMMARY_FILE"
    
    success "Analysis complete! Report available in: $REPORT_DIR/"
    echo
    echo "View the executive summary:"
    echo "  cat $SUMMARY_FILE"
    echo
    echo "View the complete index:"
    echo "  cat $REPORT_DIR/INDEX.md"
}

# Run main
main "$@"