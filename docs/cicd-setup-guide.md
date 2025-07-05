# CI/CD Setup Guide

This guide provides instructions for setting up and using the CI/CD pipeline for
the JimBot project.

## Quick Start

### Local Development Setup

1. **Run the setup script**:

   ```bash
   ./scripts/setup-dev-env.sh
   ```

2. **Activate the Python virtual environment**:

   ```bash
   source venv/bin/activate
   ```

3. **Install pre-commit hooks**:

   ```bash
   pre-commit install
   ```

4. **Start development services**:
   ```bash
   docker-compose -f docker-compose.dev.yml up -d
   ```

### Docker Development Environment

For a fully containerized development environment:

```bash
# Build and start the development container
docker-compose -f docker-compose.dev.yml up -d dev-env

# Enter the development container
docker-compose -f docker-compose.dev.yml exec dev-env bash

# Inside the container, all tools are pre-installed
```

## CI/CD Pipeline Overview

### GitHub Actions Workflows

1. **Main CI/CD Pipeline** (`.github/workflows/main-ci.yml`)
   - Runs on all pushes and PRs
   - Executes format checks, linting, unit tests, integration tests
   - Builds and pushes Docker images
   - Runs performance benchmarks

2. **Specialized Workflows**
   - **GPU Tests** (`.github/workflows/gpu-tests.yml`): GPU-accelerated code testing
   - **Rust CI/CD** (`.github/workflows/rust-ci-cd.yml`): Rust-specific CI/CD with semantic release
   - **Rust Security** (`.github/workflows/rust-security.yml`): Security audits for Rust dependencies

3. **Code Quality** (`.github/workflows/code-quality.yml`)
   - SonarQube analysis
   - CodeClimate checks
   - CodeQL security scanning

### Pre-commit Hooks

Pre-commit hooks run automatically before each commit:

- **Python**: black, isort, flake8, mypy, bandit
- **Lua**: stylua, luacheck
- **C++**: clang-format
- **Protocol Buffers**: buf format and lint
- **Docker**: hadolint
- **Security**: detect-secrets
- **Documentation**: prettier
- **Shell**: shellcheck

### Automated Dependency Updates

- **Dependabot**: Configured for Python, Docker, and GitHub Actions
- **Renovate**: Alternative to Dependabot with more features

## Running CI/CD Locally

### Format Checks

```bash
# Python
black --check jimbot tests scripts
isort --check-only jimbot tests scripts

# Lua
stylua --check .

# C++
find . -name "*.cpp" -o -name "*.h" | xargs clang-format --dry-run --Werror

# All formatters via pre-commit
pre-commit run --all-files
```

### Linting

```bash
# Python
flake8 jimbot tests
mypy jimbot
pylint jimbot
bandit -r jimbot

# Lua
luacheck . --config .luacheckrc

# C++
clang-tidy jimbot/memgraph/mage_modules/*.cpp
cppcheck --enable=all jimbot/memgraph/mage_modules/
```

### Testing

```bash
# Python unit tests
pytest jimbot/tests/unit/ -v --cov=jimbot

# Python integration tests (requires services)
docker-compose -f docker-compose.minimal.yml up -d
pytest jimbot/tests/integration/ -v

# Performance benchmarks
pytest jimbot/tests/performance/ --benchmark-only

# GPU tests (requires GPU)
pytest jimbot/tests/unit/training/ -m gpu
```

### Building Docker Images

```bash
# Build a specific service
docker build -f jimbot/deployment/docker/services/Dockerfile.mcp -t jimbot/mcp:local .

# Build all services
docker-compose -f jimbot/deployment/docker-compose.yml build
```

## Code Quality Tools

### SonarQube

Access the local SonarQube instance:

1. Start SonarQube:

   ```bash
   docker-compose -f docker-compose.dev.yml up -d sonarqube
   ```

2. Access at http://localhost:9001
   - Default credentials: admin/admin

3. Run analysis:
   ```bash
   sonar-scanner \
     -Dsonar.projectKey=jimbot \
     -Dsonar.sources=. \
     -Dsonar.host.url=http://localhost:9001 \
     -Dsonar.login=your-token
   ```

### Code Coverage

View coverage reports:

```bash
# Generate HTML coverage report
pytest --cov=jimbot --cov-report=html

# Open in browser
open htmlcov/index.html
```

## GPU Testing

### Self-hosted Runner Setup

For GPU tests, set up a self-hosted GitHub Actions runner:

1. Go to Settings → Actions → Runners in your GitHub repository
2. Click "New self-hosted runner"
3. Follow the installation instructions
4. Add GPU label:
   ```bash
   ./config.sh --labels gpu
   ```

### Local GPU Testing

```bash
# Verify GPU availability
nvidia-smi

# Run GPU tests locally
python -c "import torch; print(torch.cuda.is_available())"
pytest jimbot/tests/unit/training/ -m gpu
```

## Monitoring and Metrics

### Prometheus & Grafana

1. Start monitoring stack:

   ```bash
   docker-compose -f docker-compose.dev.yml up -d prometheus grafana
   ```

2. Access:
   - Prometheus: http://localhost:9090
   - Grafana: http://localhost:3001 (admin/admin)

3. Import dashboards from `jimbot/analytics/dashboards/`

## Troubleshooting

### Common Issues

1. **Pre-commit hook failures**

   ```bash
   # Skip hooks temporarily
   git commit --no-verify

   # Fix issues and re-run
   pre-commit run --all-files
   ```

2. **Docker build failures**

   ```bash
   # Clear Docker cache
   docker system prune -a

   # Rebuild without cache
   docker-compose build --no-cache
   ```

3. **Test failures**

   ```bash
   # Run specific test with verbose output
   pytest path/to/test.py::test_function -vvs

   # Debug with pdb
   pytest --pdb
   ```

4. **GPU not detected**

   ```bash
   # Check NVIDIA drivers
   nvidia-smi

   # Verify CUDA installation
   nvcc --version

   # Check PyTorch CUDA
   python -c "import torch; print(torch.cuda.is_available())"
   ```

## Best Practices

1. **Commit Messages**: Use conventional commits

   ```
   feat: add new feature
   fix: resolve bug
   docs: update documentation
   test: add tests
   chore: update dependencies
   ```

2. **Branch Protection**: Enable these rules on main branch:
   - Require PR reviews
   - Require status checks to pass
   - Require branches to be up to date
   - Include administrators

3. **Secrets Management**:
   - Never commit secrets
   - Use GitHub Secrets for CI/CD
   - Use `.env` files locally (gitignored)

4. **Performance**:
   - Keep CI runs under 10 minutes
   - Use caching aggressively
   - Run expensive tests only on main branch

## CI/CD Metrics

Track these metrics for continuous improvement:

- **Build Time**: Target < 10 minutes for PR builds
- **Test Coverage**: Maintain > 80% coverage
- **Flaky Test Rate**: Target < 1%
- **Deployment Frequency**: Track releases per week
- **Mean Time to Recovery**: Track incident resolution time

## Additional Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Pre-commit Documentation](https://pre-commit.com/)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)
- [Python Testing Best Practices](https://docs.pytest.org/en/latest/goodpractices.html)
- [Lua Style Guide](https://github.com/luarocks/lua-style-guide)
