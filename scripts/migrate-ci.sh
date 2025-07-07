#!/bin/bash
# CI Migration Script - Archives old workflows and sets up new ones

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== CI Migration Script ===${NC}"

# Check if we're in the right directory
if [ ! -d ".github/workflows" ]; then
    echo -e "${RED}Error: .github/workflows directory not found${NC}"
    exit 1
fi

# Create archive directory
echo -e "${YELLOW}Creating archive directory...${NC}"
mkdir -p .github/workflows-archive

# List current workflows
echo -e "${YELLOW}Current workflows:${NC}"
ls -la .github/workflows/*.yml 2>/dev/null || echo "No workflows found"

# Archive old workflows
echo -e "${YELLOW}Archiving old workflows...${NC}"
OLD_WORKFLOWS=(
    "ci.yml"
    "code-quality.yml"
    "cpp-ci.yml"
    "docker-ci-only.yml"
    "docker-ci.yml"
    "gpu-tests.yml"
    "lua-ci.yml"
    "main-ci.yml"
    "release.yml"
    "rust-basic.yml"
    "rust-ci-cd.yml"
    "rust-security.yml"
    "ci-health-check.yml"
)

for workflow in "${OLD_WORKFLOWS[@]}"; do
    if [ -f ".github/workflows/$workflow" ]; then
        echo "  Archiving $workflow"
        mv ".github/workflows/$workflow" ".github/workflows-archive/" || true
    fi
done

# Ensure new workflows exist
echo -e "${YELLOW}Checking new workflows...${NC}"
NEW_WORKFLOWS=(
    "ci-quick.yml"
    "ci-tests.yml"
    "ci-integration.yml"
)

for workflow in "${NEW_WORKFLOWS[@]}"; do
    if [ -f ".github/workflows/$workflow" ]; then
        echo -e "  ${GREEN}✓${NC} $workflow exists"
    else
        echo -e "  ${RED}✗${NC} $workflow missing"
    fi
done

# Update branch protection (informational)
echo -e "${YELLOW}Branch protection updates needed:${NC}"
echo "  1. Remove old status checks:"
echo "     - CI"
echo "     - Main CI/CD Pipeline"
echo "     - Docker CI Pipeline"
echo "     - Code Quality"
echo "  2. Add new status checks:"
echo "     - CI Quick Checks"
echo "     - CI Test Suite"
echo "     - CI Integration Tests (for main/develop)"

# Summary
echo -e "${GREEN}=== Migration Summary ===${NC}"
echo "Old workflows archived to: .github/workflows-archive/"
echo "New workflows active in: .github/workflows/"
echo ""
echo "Next steps:"
echo "1. Commit these changes"
echo "2. Push to trigger new workflows"
echo "3. Update branch protection rules in GitHub settings"
echo "4. Monitor new workflow runs"

# List final state
echo -e "${YELLOW}Final workflow state:${NC}"
ls -la .github/workflows/*.yml 2>/dev/null || echo "No workflows found"