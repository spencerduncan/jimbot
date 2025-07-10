## Lessons Learned - Issue #324
**Scope**: mods/BalatroMCP/
**Date**: 2025-07-08
**Context**: Fixed event aggregation bugs in BalatroMCP mod

### What Worked Well
- The event_aggregator.lua module was already well-implemented with proper batching logic
- Integration was straightforward - just needed to connect components properly
- Backward compatibility was easy to maintain by redirecting direct calls

### Pitfalls to Avoid
- Always run stylua before committing Lua files to avoid CI failures
- The aggregator needs event_bus reference after both are initialized
- Don't forget to flush aggregator after scoring sequences complete

### Key Insights
- Event aggregation reduces HTTP requests from 100+ to 2-3 for complex cascades
- High priority events (errors) should flush immediately
- Game state deduplication is important - only keep latest per frame
- Joker trigger hooks need to check if we're in a scoring sequence

### Recommendations for Future Work
- Consider making batch window configurable via environment variable
- Add metrics for aggregation performance (events/second, batch sizes)
- Consider adding circuit breaker for event bus failures
- May want to add compression for very large batches