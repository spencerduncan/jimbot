#!/bin/bash
# GitHub Issue Creation Commands for MCP Communication Framework
# This script creates all issues with proper dependency relationships

echo "Creating MCP Communication Framework Issues..."

# Create parent epic first
EPIC_ID=$(gh issue create \
  --title "[Epic]: MCP Communication Framework Implementation" \
  --body-file <(sed -n '/### \[Epic\]: MCP Communication Framework Implementation/,/^---$/p' github_issues_mcp.md | sed '1d;$d') \
  --label "epic,project" \
  --project "JimBot Development" \
  | grep -o '[0-9]*$')

echo "Created Epic #$EPIC_ID"

# Create immediate start issues (no dependencies)
ISSUE_1=$(gh issue create \
  --title "[Bug]: Fix BalatroMCP event aggregation bugs" \
  --body-file <(sed -n '/### Issue #1:/,/^---$/p' github_issues_mcp.md | sed '1d;$d') \
  --label "bug,can-start-immediately,high-priority" \
  | grep -o '[0-9]*$')

ISSUE_2=$(gh issue create \
  --title "[Bug]: Fix BalatroMCP retry logic and error handling" \
  --body-file <(sed -n '/### Issue #2:/,/^---$/p' github_issues_mcp.md | sed '1d;$d') \
  --label "bug,can-start-immediately,high-priority" \
  | grep -o '[0-9]*$')

ISSUE_3=$(gh issue create \
  --title "[Feature]: Define Protocol Buffer schemas for Balatro events" \
  --body-file <(sed -n '/### Issue #3:/,/^---$/p' github_issues_mcp.md | sed '1d;$d') \
  --label "feature,can-start-immediately,schemas" \
  | grep -o '[0-9]*$')

ISSUE_4=$(gh issue create \
  --title "[Feature]: Create Docker Compose development environment" \
  --body-file <(sed -n '/### Issue #4:/,/^---$/p' github_issues_mcp.md | sed '1d;$d') \
  --label "feature,can-start-immediately,infrastructure" \
  | grep -o '[0-9]*$')

echo "Created immediate start issues: #$ISSUE_1, #$ISSUE_2, #$ISSUE_3, #$ISSUE_4"

# Create first wave dependencies
ISSUE_5=$(gh issue create \
  --title "[Feature]: Implement Event Bus infrastructure" \
  --body-file <(sed -n '/### Issue #5:/,/^---$/p' github_issues_mcp.md | sed '1d;$d') \
  --label "feature,infrastructure,blocked" \
  | grep -o '[0-9]*$')

ISSUE_6=$(gh issue create \
  --title "[Feature]: Set up Protocol Buffer compilation pipeline" \
  --body-file <(sed -n '/### Issue #6:/,/^---$/p' github_issues_mcp.md | sed '1d;$d') \
  --label "feature,build-tools,blocked" \
  | grep -o '[0-9]*$')

# Add blocking relationships
gh issue comment $ISSUE_5 --body "Blocked by: #$ISSUE_4 (Docker environment)"
gh issue comment $ISSUE_4 --body "Blocks: #$ISSUE_5"

gh issue comment $ISSUE_6 --body "Blocked by: #$ISSUE_3 (Protocol Buffer schemas)"
gh issue comment $ISSUE_3 --body "Blocks: #$ISSUE_6"

# Create core implementation
ISSUE_7=$(gh issue create \
  --title "[Feature]: Implement MCP Server core with gRPC" \
  --body-file <(sed -n '/### Issue #7:/,/^---$/p' github_issues_mcp.md | sed '1d;$d') \
  --label "feature,core,blocked" \
  | grep -o '[0-9]*$')

gh issue comment $ISSUE_7 --body "Blocked by: #$ISSUE_5 (Event Bus), #$ISSUE_6 (Protobuf compilation)"
gh issue comment $ISSUE_5 --body "Blocks: #$ISSUE_7"
gh issue comment $ISSUE_6 --body "Blocks: #$ISSUE_7"

# Create dependent features
ISSUE_8=$(gh issue create \
  --title "[Feature]: Create BalatroMCP adapter layer" \
  --body-file <(sed -n '/### Issue #8:/,/^---$/p' github_issues_mcp.md | sed '1d;$d') \
  --label "feature,integration,blocked" \
  | grep -o '[0-9]*$')

gh issue comment $ISSUE_8 --body "Blocked by: #$ISSUE_1 (aggregation bugs), #$ISSUE_2 (retry bugs), #$ISSUE_7 (MCP Server)"
gh issue comment $ISSUE_1 --body "Blocks: #$ISSUE_8"
gh issue comment $ISSUE_2 --body "Blocks: #$ISSUE_8"
gh issue comment $ISSUE_7 --body "Blocks: #$ISSUE_8, #$ISSUE_9, #$ISSUE_11"

# Continue with remaining issues...
ISSUE_9=$(gh issue create \
  --title "[Feature]: Implement complex event aggregation" \
  --body-file <(sed -n '/### Issue #9:/,/^---$/p' github_issues_mcp.md | sed '1d;$d') \
  --label "feature,performance,blocked" \
  | grep -o '[0-9]*$')

ISSUE_10=$(gh issue create \
  --title "[Enhancement]: Optimize performance and batching" \
  --body-file <(sed -n '/### Issue #10:/,/^---$/p' github_issues_mcp.md | sed '1d;$d') \
  --label "enhancement,performance,blocked" \
  | grep -o '[0-9]*$')

ISSUE_11=$(gh issue create \
  --title "[Feature]: Integrate Resource Coordinator" \
  --body-file <(sed -n '/### Issue #11:/,/^---$/p' github_issues_mcp.md | sed '1d;$d') \
  --label "feature,integration,blocked" \
  | grep -o '[0-9]*$')

ISSUE_12=$(gh issue create \
  --title "[Testing]: Create comprehensive test suite" \
  --body-file <(sed -n '/### Issue #12:/,/^---$/p' github_issues_mcp.md | sed '1d;$d') \
  --label "testing,quality,blocked" \
  | grep -o '[0-9]*$')

ISSUE_13=$(gh issue create \
  --title "[Enhancement]: Production hardening and monitoring" \
  --body-file <(sed -n '/### Issue #13:/,/^---$/p' github_issues_mcp.md | sed '1d;$d') \
  --label "enhancement,production,blocked" \
  | grep -o '[0-9]*$')

ISSUE_14=$(gh issue create \
  --title "[Documentation]: Documentation and deployment" \
  --body-file <(sed -n '/### Issue #14:/,/^---$/p' github_issues_mcp.md | sed '1d;$d') \
  --label "documentation,deployment,blocked" \
  | grep -o '[0-9]*$')

# Add remaining blocking relationships
gh issue comment $ISSUE_9 --body "Blocked by: #$ISSUE_7"
gh issue comment $ISSUE_10 --body "Blocked by: #$ISSUE_9"
gh issue comment $ISSUE_9 --body "Blocks: #$ISSUE_10"
gh issue comment $ISSUE_11 --body "Blocked by: #$ISSUE_3, #$ISSUE_7"
gh issue comment $ISSUE_3 --body "Blocks: #$ISSUE_11"
gh issue comment $ISSUE_12 --body "Blocked by: #$ISSUE_8"
gh issue comment $ISSUE_8 --body "Blocks: #$ISSUE_12"
gh issue comment $ISSUE_13 --body "Blocked by: #$ISSUE_10, #$ISSUE_11, #$ISSUE_12"
gh issue comment $ISSUE_10 --body "Blocks: #$ISSUE_13"
gh issue comment $ISSUE_11 --body "Blocks: #$ISSUE_13"
gh issue comment $ISSUE_12 --body "Blocks: #$ISSUE_13"
gh issue comment $ISSUE_14 --body "Blocked by: #$ISSUE_13"
gh issue comment $ISSUE_13 --body "Blocks: #$ISSUE_14"

# Link all issues to parent epic
gh issue comment $EPIC_ID --body "Child issues created:
- #$ISSUE_1: Fix BalatroMCP event aggregation bugs
- #$ISSUE_2: Fix BalatroMCP retry logic  
- #$ISSUE_3: Define Protocol Buffer schemas
- #$ISSUE_4: Create Docker environment
- #$ISSUE_5: Event Bus infrastructure
- #$ISSUE_6: Protocol Buffer compilation
- #$ISSUE_7: MCP Server core
- #$ISSUE_8: BalatroMCP adapter
- #$ISSUE_9: Complex event aggregation
- #$ISSUE_10: Performance optimization
- #$ISSUE_11: Resource Coordinator integration
- #$ISSUE_12: Test suite
- #$ISSUE_13: Production hardening
- #$ISSUE_14: Documentation

Parallel work streams:
- Bug Fixes: #$ISSUE_1, #$ISSUE_2 → #$ISSUE_8
- Infrastructure: #$ISSUE_4 → #$ISSUE_5 → #$ISSUE_7
- Schemas: #$ISSUE_3 → #$ISSUE_6 → #$ISSUE_7
- Features: #$ISSUE_7 → #$ISSUE_9 → #$ISSUE_10
- Integration: #$ISSUE_7 → #$ISSUE_11"

echo "All issues created with dependency relationships!"
echo "Epic: #$EPIC_ID"
echo "Issues that can start immediately: #$ISSUE_1, #$ISSUE_2, #$ISSUE_3, #$ISSUE_4"