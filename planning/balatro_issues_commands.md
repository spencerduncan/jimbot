# BalatroMCP GitHub Issue Creation Commands

This file contains GitHub CLI (`gh`) commands to create tracking issues for BalatroMCP development.

## Prerequisites

First, create the balatro-mod label:
```bash
gh label create balatro-mod --description "Issues related to BalatroMCP mod development" --color 0e8a16
```

## Issue Creation Commands

### 1. BalatroMCP Stability & Testing

```bash
gh issue create \
  --title "BalatroMCP Stability & Testing - Comprehensive Test Suite" \
  --body "## Description
Develop a comprehensive test suite for BalatroMCP to ensure stability and reliability of the mod interface.

## Current State
- Basic mod structure exists in \`mods/BalatroMCP/\`
- Event bus client implemented (\`event_bus_client.lua\`)
- Action executor in development (\`action_executor.lua\`)
- Basic logger implemented (\`logger.lua\`)

## Acceptance Criteria
- [ ] Unit tests for all major components (event_bus_client, action_executor, logger)
- [ ] Integration tests for game state synchronization
- [ ] Performance tests confirming <100ms event batching
- [ ] Mock game environment for testing without running Balatro
- [ ] CI/CD pipeline for automated testing
- [ ] Test coverage > 80%

## Technical Requirements
- Use busted or similar Lua testing framework
- Create test fixtures for common game states
- Implement test doubles for game API calls
- Document testing procedures in README

## References
- Current implementation: \`mods/BalatroMCP/\`
- Event aggregation requirement: <100ms latency (CLAUDE.md)" \
  --label "balatro-mod,testing,enhancement" \
  --assignee @me
```

### 2. Action Executor Improvements

```bash
gh issue create \
  --title "Action Executor Improvements - Complete Action Implementation" \
  --body "## Description
Complete and improve the action executor module, building on the existing \`go_to_shop\` function implementation.

## Current State
- \`action_executor.lua\` contains partial implementation
- \`go_to_shop\` function shows pattern for action implementation
- Need to implement remaining game actions

## Acceptance Criteria
- [ ] Complete implementation of all game actions:
  - [ ] Card selection/deselection
  - [ ] Card playing
  - [ ] Card discarding
  - [ ] Joker purchasing
  - [ ] Pack opening
  - [ ] Voucher purchasing
  - [ ] Reroll actions
- [ ] Robust error handling for invalid actions
- [ ] Action validation before execution
- [ ] Action result reporting back to MCP
- [ ] Comprehensive logging of all actions

## Technical Requirements
- Follow existing \`go_to_shop\` pattern
- Ensure thread-safe execution
- Implement action queueing if needed
- Return standardized action results

## References
- Current implementation: \`mods/BalatroMCP/action_executor.lua\`
- Interface specification: \`planning/interface_specification.md\`" \
  --label "balatro-mod,enhancement,priority-high" \
  --assignee @me
```

### 3. Event Schema Documentation

```bash
gh issue create \
  --title "Event Schema Documentation - Document All Event Types" \
  --body "## Description
Create comprehensive documentation for all event types emitted by BalatroMCP, with examples and schemas.

## Current State
- Events defined in interface specification
- Event bus client sends events
- Need detailed documentation for each event type

## Acceptance Criteria
- [ ] Document all event types:
  - [ ] Game state events (round_start, round_end, ante_change)
  - [ ] Card events (card_played, card_discarded, card_enhanced)
  - [ ] Shop events (shop_entered, item_purchased, reroll)
  - [ ] Score events (hand_scored, chips_calculated, mult_applied)
  - [ ] Joker events (joker_triggered, joker_added, joker_sold)
- [ ] Provide JSON examples for each event
- [ ] Document event flow diagrams
- [ ] Create event validation schemas
- [ ] Generate event type constants file

## Deliverables
- \`docs/event_schema.md\` - comprehensive event documentation
- \`mods/BalatroMCP/event_types.lua\` - event type constants
- Event flow diagrams in \`docs/diagrams/\`

## References
- Interface specification: \`planning/interface_specification.md\`
- Current events: \`mods/BalatroMCP/event_bus_client.lua\`" \
  --label "balatro-mod,documentation" \
  --assignee @me
```

### 4. Performance Monitoring

```bash
gh issue create \
  --title "Performance Monitoring - Ensure <100ms Event Batching" \
  --body "## Description
Implement performance monitoring to ensure event batching meets the <100ms latency requirement.

## Current State
- Basic event sending implemented
- No performance monitoring in place
- 100ms batch window specified in requirements

## Acceptance Criteria
- [ ] Implement performance metrics collection:
  - [ ] Event generation timestamp
  - [ ] Event send timestamp
  - [ ] Batch assembly time
  - [ ] Network latency
- [ ] Create performance dashboard/logs
- [ ] Implement automatic performance alerts
- [ ] Optimize hot paths if needed
- [ ] Document performance tuning guide

## Technical Requirements
- Minimal overhead from monitoring itself
- Rolling window statistics (last 1000 events)
- Percentile calculations (p50, p95, p99)
- Integration with QuestDB for metrics storage

## References
- Performance target: <100ms (CLAUDE.md)
- Current implementation: \`mods/BalatroMCP/event_bus_client.lua\`" \
  --label "balatro-mod,performance,monitoring" \
  --assignee @me
```

### 5. Error Handling & Recovery

```bash
gh issue create \
  --title "Error Handling & Recovery - Handle Game Crashes and Reconnections" \
  --body "## Description
Implement robust error handling and recovery mechanisms for game crashes, network issues, and reconnections.

## Current State
- Basic error logging exists
- No recovery mechanisms implemented
- Need graceful degradation

## Acceptance Criteria
- [ ] Implement error handling for:
  - [ ] Game crashes/restarts
  - [ ] Network disconnections
  - [ ] MCP server unavailability
  - [ ] Invalid game states
  - [ ] Lua runtime errors
- [ ] Create automatic reconnection logic
- [ ] Implement event buffer for offline mode
- [ ] Add circuit breaker pattern
- [ ] Create error recovery documentation

## Technical Requirements
- Exponential backoff for reconnections
- Local event buffer (max 1000 events)
- Graceful degradation without blocking game
- Clear error messages in logs

## References
- Current logger: \`mods/BalatroMCP/logger.lua\`
- Event bus client: \`mods/BalatroMCP/event_bus_client.lua\`" \
  --label "balatro-mod,error-handling,reliability" \
  --assignee @me
```

### 6. Configuration Management

```bash
gh issue create \
  --title "Configuration Management - Document All Config Options" \
  --body "## Description
Improve configuration management and create comprehensive documentation for all configuration options.

## Current State
- Basic config exists in \`config.lua\`
- Limited configuration options
- No config validation

## Acceptance Criteria
- [ ] Enhance configuration system:
  - [ ] Environment-based config loading
  - [ ] Config validation on startup
  - [ ] Runtime config updates (where safe)
  - [ ] Default config with overrides
- [ ] Document all config options:
  - [ ] Server endpoints
  - [ ] Performance tuning
  - [ ] Logging levels
  - [ ] Feature flags
- [ ] Create config examples for different scenarios
- [ ] Implement config hot-reload where possible

## Deliverables
- Enhanced \`mods/BalatroMCP/config.lua\`
- \`docs/configuration.md\` - comprehensive config guide
- \`mods/BalatroMCP/config.example.lua\` - example configurations

## References
- Current config: \`mods/BalatroMCP/config.lua\`
- Mod structure: \`mods/BalatroMCP/mod.json\`" \
  --label "balatro-mod,configuration,documentation" \
  --assignee @me
```

## Bulk Creation

To create all issues at once:
```bash
# Create the label first
gh label create balatro-mod --description "Issues related to BalatroMCP mod development" --color 0e8a16

# Then run each gh issue create command above
```

## Additional Labels

Consider creating these additional labels for better organization:
```bash
gh label create priority-high --color d93f0b
gh label create reliability --color 1d76db
gh label create monitoring --color f9d0c4
```