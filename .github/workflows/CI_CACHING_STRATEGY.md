# CI Caching Strategy

## Overview
This document describes the caching strategy for Python dependencies in CI workflows.

## Workflows with Direct Python Caching

### ci-health-monitor.yml
- Uses `actions/setup-python@v5` with built-in pip caching
- Cache key based on: `**/requirements*.txt`, `**/pyproject.toml`, `setup.py`
- Expected improvement: ~2-3 minutes to ~10 seconds for pip install

## Docker-based Workflows

The following workflows use Docker for Python execution:
- `ci-tests.yml`
- `ci-integration.yml`
- `ci-quick.yml`

### Why Direct pip Caching Isn't Used
These workflows run Python inside Docker containers built from `docker/Dockerfile.ci-unified`. The Python dependencies are installed during the Docker build process, not in the GitHub Actions workflow directly.

### Existing Caching Strategy
These workflows already benefit from Docker layer caching:
```yaml
cache-from: type=gha
cache-to: type=gha,mode=max
```

This caches the entire Docker build, including:
- Base OS packages
- Python installation
- pip packages installed in the Dockerfile
- Other language toolchains (Rust, Lua)

### Benefits
- First build: Full Docker build including all dependencies
- Subsequent builds: Reuses cached layers if dependencies haven't changed
- Cache invalidation: Automatic when Dockerfile or dependency files change

## Cache Key Strategy

For workflows using direct Python setup:
- Primary cache key: OS + Python version + hash of dependency files
- Restore keys fallback to partial matches for faster builds

## Monitoring Cache Effectiveness

Check workflow run times to verify cache hits:
1. Look for "Cache restored successfully" in setup-python step
2. Compare pip install times between cache hit vs miss
3. Monitor overall workflow duration improvements

## Future Improvements

If Docker-based workflows need faster Python dependency updates:
1. Consider adding requirements.txt copying and pip install as separate Docker layers
2. Use multi-stage builds to optimize caching
3. Implement dependency pinning for reproducible builds