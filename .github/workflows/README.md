# GitHub Actions Workflows

This directory contains the consolidated CI/CD workflows for the JimBot project.

## Active Workflows

### 1. CI Quick Checks (`ci-quick.yml`)
- **Trigger**: All pushes and PRs
- **Duration**: ~5 minutes
- **Purpose**: Fast feedback on code quality
- **Checks**:
  - Python formatting (black, isort)
  - Python linting (flake8, pylint, mypy)
  - Rust formatting and linting
  - Security audits

### 2. CI Test Suite (`ci-tests.yml`)
- **Trigger**: All pushes and PRs
- **Duration**: ~10-15 minutes
- **Purpose**: Comprehensive testing
- **Matrix**:
  - Python unit tests with coverage
  - Rust tests with tarpaulin
  - Basic integration tests

### 3. CI Integration Tests (`ci-integration.yml`)
- **Trigger**: Main/develop branches and PRs
- **Duration**: ~20-30 minutes
- **Purpose**: Full system integration testing
- **Services**: QuestDB, Memgraph, Event Bus
- **Tests**: Cross-component integration

## Unified Docker Image

All workflows use `Dockerfile.ci-unified` which includes:
- Python 3.10 with all test dependencies
- Rust 1.75 with cargo tools
- C++ 17 with CMake and clang
- Lua 5.4 with busted
- Node.js 18 for additional tooling

## Migration Notes

Previous workflows have been archived to `.github/workflows-archive/`.
The new consolidated approach reduces 14 workflows to 3, improving:
- Maintenance burden
- CI runtime efficiency
- Dependency management
- Cache utilization

## Local Testing

To test these workflows locally:

```bash
# Quick checks
docker build -f Dockerfile.ci-unified -t jimbot-ci:latest .
docker run --rm -v $(pwd):/workspace jimbot-ci:latest bash ci/scripts/run-quick-checks.sh

# Test suite
docker compose -f docker-compose.ci.yml up ci-runner
```