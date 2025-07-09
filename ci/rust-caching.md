# Rust CI Caching Configuration

## Overview

This document describes the Rust dependency caching implementation added to the CI workflows to significantly reduce build times.

## Implementation Details

### 1. GitHub Actions Cache Integration

All CI workflows now use the `Swatinem/rust-cache@v2` action which provides intelligent caching for:
- Cargo registry (`~/.cargo/registry`)
- Cargo git database (`~/.cargo/git`)
- Target directories for each workspace

### 2. Workspace Configuration

The caching is configured for all Rust projects in the repository:
- Root workspace (if Cargo.toml exists)
- `jimbot/memgraph/mage_modules`
- `services/balatro-emulator`
- `services/event-bus-rust`
- `jimbot/infrastructure/resource_coordinator_rust`

### 3. Docker Volume Mounts

Since our CI runs Rust commands inside Docker containers, we mount the host's cargo cache directories:
```bash
docker run --rm \
  -v ${{ github.workspace }}:/workspace \
  -v $HOME/.cargo/registry:/root/.cargo/registry \
  -v $HOME/.cargo/git:/root/.cargo/git \
  jimbot-ci:latest
```

### 4. Cache Keys

Different workflows use different cache keys to prevent conflicts:
- `rust-ci-tests`: For test workflows
- `rust-ci-quick`: For quick checks (format, lint)
- `rust-ci-integration`: For integration tests
- `rust-ci-scheduled`: For scheduled tests
- `rust-check`, `rust-test`, `rust-audit`: For standalone Rust CI

### 5. Performance Improvements

Expected improvements:
- Initial builds: 10-15 minutes → 10-15 minutes (no change)
- Subsequent builds: 10-15 minutes → 2-3 minutes (80% reduction)
- Incremental builds: <1 minute for small changes

### 6. Cache Management

- Caches are saved only from the main branch (`save-if: ${{ github.ref == 'refs/heads/main' }}`)
- Cache on failure is enabled to cache even failed builds
- GitHub automatically manages cache eviction (7 day retention)

## Monitoring Cache Effectiveness

You can monitor cache hit rates in the GitHub Actions UI:
1. Go to Actions tab
2. Select a workflow run
3. Look for "Cache Rust dependencies" step
4. Check for "Cache restored successfully" or "Cache not found"

## Future Improvements

1. Consider using `sccache` for distributed caching across multiple runners
2. Implement cache warming jobs that run on schedule
3. Add metrics collection for build time improvements