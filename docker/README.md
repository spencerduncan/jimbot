# Docker Configuration

This directory contains Docker configurations for the JimBot project, including optimized Dockerfiles with BuildKit cache mount support and the Docker-based Lua testing infrastructure implemented as part of **Sprint 2.4: Migrate Lua test suite to Docker environment**.

## BuildKit Configuration

All Dockerfiles in this project are optimized to use BuildKit cache mounts for apt package caching. This significantly reduces build times by caching downloaded packages between builds.

### Enabling BuildKit

BuildKit must be enabled for the cache mounts to work. You can enable it in several ways:

1. **Environment Variable** (Recommended):
   ```bash
   export DOCKER_BUILDKIT=1
   docker build .
   ```

2. **Docker Configuration**:
   Add to `/etc/docker/daemon.json`:
   ```json
   {
     "features": {
       "buildkit": true
     }
   }
   ```

3. **Docker Compose**:
   ```bash
   DOCKER_BUILDKIT=1 docker-compose build
   ```

### Benefits

- Reduces apt package download time from 2-3 minutes to 10-30 seconds
- Lower network bandwidth usage
- More reliable builds (less dependent on mirror availability)
- Faster developer feedback loops

### How It Works

The Dockerfiles use BuildKit cache mounts for `/var/cache/apt` and `/var/lib/apt`:

```dockerfile
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y \
    package1 package2 \
    && rm -rf /var/lib/apt/lists/*
```

The `sharing=locked` ensures safe concurrent access when building multiple images.

## Docker-based Lua Testing Environment

## Overview

The Lua testing environment provides a containerized, reproducible solution for running Lua tests in both development and CI environments. It includes:

- **Isolated testing environment** with all required Lua tools pre-installed
- **Multiple testing profiles** (standard, coverage, performance, development)
- **Comprehensive test runner** with style checks, linting, and test execution
- **CI integration** with GitHub Actions
- **Coverage reporting** and performance testing capabilities

## Files

### Docker Configuration

- `Dockerfile.lua-test` - Multi-stage Dockerfile for Lua testing environment
- `docker-compose.lua-test.yml` - Docker Compose configuration with multiple profiles

### CI Scripts

- `../ci/scripts/run-lua-tests.sh` - Main CI script for running Lua tests
- `../.github/workflows/lua-ci.yml` - GitHub Actions workflow for Lua CI

## Quick Start

### Running Tests Locally

```bash
# Build and run standard tests
docker-compose -f docker/docker-compose.lua-test.yml up lua-test

# Run with coverage reporting
docker-compose -f docker/docker-compose.lua-test.yml --profile coverage up lua-test-coverage

# Run performance tests
docker-compose -f docker/docker-compose.lua-test.yml --profile perf up lua-test-perf

# Start development environment (interactive)
docker-compose -f docker/docker-compose.lua-test.yml --profile dev up lua-test-dev
```

### Using the CI Script

```bash
# Run standard tests
bash ci/scripts/run-lua-tests.sh

# Run with coverage
bash ci/scripts/run-lua-tests.sh --coverage

# Run performance tests
bash ci/scripts/run-lua-tests.sh --performance

# Set custom timeout
bash ci/scripts/run-lua-tests.sh --timeout 300
```

## Testing Profiles

### Standard Testing (`lua-test`)

- **Purpose**: Basic test execution with style and lint checks
- **Components**:
  - StyLua code formatting validation
  - Luacheck linting
  - Unit tests (shop navigation suite)
  - Integration tests (game state suite)
  - Basic error reporting

### Coverage Testing (`lua-test-coverage`)

- **Purpose**: Test execution with code coverage reporting
- **Components**:
  - All standard testing components
  - LuaCov coverage analysis
  - LCOV report generation
  - Coverage artifacts for CI

### Performance Testing (`lua-test-perf`)

- **Purpose**: Performance measurement and timing analysis
- **Components**:
  - All standard testing components
  - Timing measurements for each test suite
  - Performance metrics collection
  - Resource usage monitoring

### Development Environment (`lua-test-dev`)

- **Purpose**: Interactive development and debugging
- **Components**:
  - All testing tools available
  - Interactive shell access
  - Development utilities (vim, htop, etc.)
  - Persistent container for debugging

## Test Suites

### Shop Navigation Tests (`tests/run_tests.lua`)

- **Focus**: Unit tests for shop navigation bug fixes
- **Coverage**: 10 unit tests covering navigation logic
- **Key Tests**:
  - `navigate_menu` does not call `evaluate_round`
  - Shop function priority order
  - Fallback mechanisms
  - Error handling

### Game State Tests (`tests/run_all_tests.lua`)

- **Focus**: Integration tests for game state extraction
- **Coverage**: Full game state workflow testing
- **Key Tests**:
  - State extraction accuracy
  - Integration with game mechanics
  - Error recovery

## CI Integration

### GitHub Actions Workflow

The `lua-ci.yml` workflow provides:

- **Matrix Testing**: Runs all three testing profiles in parallel
- **Artifact Collection**: Saves test results and coverage reports
- **Performance Monitoring**: Tracks test execution times
- **Integration Testing**: Validates Docker environment setup

### Trigger Conditions

Tests run automatically on:
- Pushes to main branches
- Pull requests to main branches
- Changes to Lua files or test configuration

## Configuration Files

### `.luacheckrc`
```lua
-- Luacheck configuration for code quality
std = "lua54"
ignore = {
    "211", -- unused local variable
    "212", -- unused argument
    "213", -- unused loop variable
}
```

### `.stylua.toml`
```toml
# StyLua configuration for code formatting
column_width = 100
line_endings = "Unix"
indent_type = "Spaces"
indent_width = 4
```

## Development Workflow

### Local Development

1. **Start development environment**:
   ```bash
   docker-compose -f docker/docker-compose.lua-test.yml --profile dev up lua-test-dev
   ```

2. **Access interactive shell**:
   ```bash
   docker exec -it jimbot-lua-test-dev bash
   ```

3. **Run individual tests**:
   ```bash
   # Inside container
   lua tests/run_tests.lua
   lua tests/run_all_tests.lua
   luacheck tests/
   stylua --check tests/
   ```

### Adding New Tests

1. **Create test file** in appropriate directory (`tests/unit/` or `tests/integration/`)
2. **Add to test suite** in `run_tests.lua` or `run_all_tests.lua`
3. **Test locally** using development environment
4. **Verify CI integration** by running the full test suite

### Debugging Test Failures

1. **Use development environment** for interactive debugging
2. **Check container logs** for detailed error messages
3. **Run individual test components** to isolate issues
4. **Verify configuration files** are properly mounted

## Performance Considerations

### Resource Usage

- **Memory**: ~100MB per container
- **CPU**: Moderate during test execution
- **Disk**: ~50MB for images, ~10MB for volumes

### Optimization

- **Docker layer caching** reduces build times
- **Volume caching** for LuaRocks packages
- **Multi-stage builds** minimize final image size
- **Parallel test execution** in CI matrix

## Troubleshooting

### Common Issues

1. **Build failures**: Check Dockerfile syntax and dependencies
2. **Test failures**: Verify test files are properly mounted
3. **Permission errors**: Ensure proper user permissions in container
4. **Network issues**: Check Docker network configuration

### Debug Commands

```bash
# Check container status
docker-compose -f docker/docker-compose.lua-test.yml ps

# View logs
docker-compose -f docker/docker-compose.lua-test.yml logs lua-test

# Interactive debugging
docker-compose -f docker/docker-compose.lua-test.yml run --rm lua-test-dev bash

# Validate configuration
docker-compose -f docker/docker-compose.lua-test.yml config
```

## Migration Benefits

### Before (Host-based Testing)

- ❌ Environment inconsistencies between local and CI
- ❌ Dependency management issues
- ❌ Limited testing capabilities
- ❌ No coverage reporting
- ❌ Manual test execution

### After (Docker-based Testing)

- ✅ Consistent environment across all platforms
- ✅ Isolated dependencies and tools
- ✅ Comprehensive testing profiles
- ✅ Automated coverage reporting
- ✅ CI integration with GitHub Actions
- ✅ Performance monitoring
- ✅ Interactive development environment

## Future Enhancements

### Planned Improvements

1. **Busted Integration**: Add support for Busted testing framework
2. **Parallel Test Execution**: Run test suites in parallel for faster results
3. **Test Result Caching**: Cache test results for unchanged files
4. **Enhanced Coverage**: Add branch coverage and complexity metrics
5. **Performance Benchmarking**: Historical performance tracking

### Integration Opportunities

1. **Main CI Pipeline**: Integration with existing CI workflows
2. **Pre-commit Hooks**: Automatic test execution on commits
3. **IDE Integration**: VS Code development containers
4. **Quality Gates**: Automated quality checks with failure thresholds

## Conclusion

The Docker-based Lua testing environment provides a robust, scalable solution for Lua testing in the JimBot project. It addresses the key requirements of Sprint 2.4 by:

- **Modernizing** the testing infrastructure
- **Improving** CI integration and reliability
- **Providing** comprehensive testing capabilities
- **Enabling** consistent development experience

This implementation ensures that Lua tests can be executed reliably across different environments while providing developers with the tools they need for effective testing and debugging.