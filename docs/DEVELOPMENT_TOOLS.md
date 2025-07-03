# Development Tools Setup

This document provides a comprehensive overview of all development tools
configured for the JimBot project.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Language-Specific Tools](#language-specific-tools)
3. [Pre-commit Hooks](#pre-commit-hooks)
4. [CI/CD Pipeline](#cicd-pipeline)
5. [Development Environment](#development-environment)
6. [Troubleshooting](#troubleshooting)

## Quick Start

### Automated Setup

```bash
# Run the development environment setup script
./scripts/setup-dev-env.sh
```

### Manual Setup

```bash
# 1. Create Python virtual environment
python3 -m venv venv
source venv/bin/activate

# 2. Install Python dependencies
pip install -e ".[dev,test,docs]"

# 3. Install pre-commit hooks
pre-commit install

# 4. Run initial checks
pre-commit run --all-files
```

## Language-Specific Tools

### Python

| Tool         | Purpose          | Configuration    |
| ------------ | ---------------- | ---------------- |
| **Black**    | Code formatter   | `pyproject.toml` |
| **isort**    | Import sorter    | `pyproject.toml` |
| **Ruff**     | Fast linter      | `pyproject.toml` |
| **Flake8**   | Style checker    | `.flake8`        |
| **mypy**     | Type checker     | `mypy.ini`       |
| **pytest**   | Test runner      | `pyproject.toml` |
| **coverage** | Code coverage    | `pyproject.toml` |
| **bandit**   | Security scanner | `pyproject.toml` |

**Commands:**

```bash
# Format code
black jimbot tests
isort jimbot tests

# Lint code
ruff check jimbot tests
flake8 jimbot tests
mypy jimbot

# Run tests
pytest
pytest --cov=jimbot --cov-report=html

# Security scan
bandit -r jimbot
```

### Lua

| Tool         | Purpose        | Configuration  |
| ------------ | -------------- | -------------- |
| **StyLua**   | Code formatter | `.stylua.toml` |
| **luacheck** | Linter         | `.luacheckrc`  |
| **busted**   | Test framework | -              |
| **luacov**   | Coverage tool  | -              |

**Commands:**

```bash
# Format code
stylua .

# Lint code
luacheck .

# Run tests
busted

# Coverage
luacov
```

### C++

| Tool             | Purpose         | Configuration    |
| ---------------- | --------------- | ---------------- |
| **clang-format** | Code formatter  | `.clang-format`  |
| **clang-tidy**   | Linter          | `.clang-tidy`    |
| **cppcheck**     | Static analyzer | Command line     |
| **CMake**        | Build system    | `CMakeLists.txt` |
| **Google Test**  | Test framework  | -                |

**Commands:**

```bash
# Format code
find . -name "*.cpp" -o -name "*.hpp" | xargs clang-format -i

# Lint code
clang-tidy src/*.cpp -- -I/usr/include/memgraph
cppcheck --enable=all src/

# Build
cmake -B build
cmake --build build

# Test
cd build && ctest
```

### JavaScript/TypeScript

| Tool           | Purpose        | Configuration      |
| -------------- | -------------- | ------------------ |
| **Prettier**   | Code formatter | `.prettierrc.json` |
| **ESLint**     | Linter         | `.eslintrc.json`   |
| **TypeScript** | Type checker   | `tsconfig.json`    |
| **Vitest**     | Test runner    | `package.json`     |

**Commands:**

```bash
# Format code
npm run format

# Lint code
npm run lint

# Type check
npm run typecheck

# Run tests
npm test
```

### SQL

| Tool         | Purpose          | Configuration |
| ------------ | ---------------- | ------------- |
| **sqlfluff** | Formatter/Linter | `.sqlfluff`   |

**Commands:**

```bash
# Lint SQL
sqlfluff lint .

# Format SQL
sqlfluff fix .
```

### Protocol Buffers

| Tool       | Purpose        | Configuration |
| ---------- | -------------- | ------------- |
| **buf**    | Linter/Manager | `buf.yaml`    |
| **protoc** | Compiler       | -             |

**Commands:**

```bash
# Lint proto files
buf lint

# Format proto files
buf format -w

# Check breaking changes
buf breaking --against '.git#branch=main'
```

## Pre-commit Hooks

Pre-commit hooks run automatically before each commit to ensure code quality.

### Installed Hooks

- **General**: trailing whitespace, end of file fixer, large file check
- **Python**: Black, isort, Ruff, Flake8, mypy, bandit
- **Lua**: StyLua, luacheck
- **C++**: clang-format, clang-tidy
- **JavaScript/TypeScript**: Prettier, ESLint
- **SQL**: sqlfluff
- **Protocol Buffers**: buf lint/format
- **Docker**: hadolint
- **YAML**: yamllint
- **Markdown**: markdownlint

### Commands

```bash
# Install hooks
pre-commit install

# Run on all files
pre-commit run --all-files

# Run specific hook
pre-commit run black --all-files

# Update hooks
pre-commit autoupdate
```

## CI/CD Pipeline

### GitHub Actions Workflows

#### Main CI (`ci.yml`)

- Runs on every push and PR
- Matrix testing for Python 3.9, 3.10, 3.11
- Parallel jobs for each language
- Integration tests with Docker services
- Security scanning with Trivy and CodeQL

#### GPU Tests (`gpu-tests.yml`)

- Runs on self-hosted GPU runners
- Tests Ray distributed training
- GPU memory profiling
- Performance benchmarks

#### Release (`release.yml`)

- Triggered by version tags
- Builds Python packages
- Creates Docker images
- Publishes to PyPI
- Deploys documentation

### Running CI Locally

```bash
# Install act (GitHub Actions local runner)
brew install act  # macOS
# or
curl https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash  # Linux

# Run CI locally
act -j python-lint
act -j python-test
```

## Development Environment

### VS Code Extensions

Recommended extensions are defined in `.vscode/extensions.json`:

- Python (ms-python.python)
- Pylance (ms-python.vscode-pylance)
- Black Formatter (ms-python.black-formatter)
- Lua (sumneko.lua)
- C/C++ (ms-vscode.cpptools)
- ESLint (dbaeumer.vscode-eslint)
- Prettier (esbenp.prettier-vscode)
- Docker (ms-azuretools.vscode-docker)

### Docker Development

```bash
# Start development services
docker-compose -f docker-compose.dev.yml up -d

# View logs
docker-compose logs -f

# Run tests in container
docker-compose exec app pytest
```

### Environment Variables

Create a `.env` file:

```env
# API Keys
ANTHROPIC_API_KEY=your_key_here

# Database URLs
MEMGRAPH_HOST=localhost
MEMGRAPH_PORT=7687
QUESTDB_HOST=localhost
QUESTDB_PORT=8812

# Ray Configuration
RAY_ADDRESS=localhost:6379

# Development Settings
DEBUG=true
LOG_LEVEL=debug
```

## Troubleshooting

### Common Issues

#### Python Import Errors

```bash
# Ensure virtual environment is activated
source venv/bin/activate

# Reinstall in development mode
pip install -e ".[dev]"
```

#### Pre-commit Hook Failures

```bash
# Skip hooks temporarily
git commit --no-verify

# Fix and re-run
pre-commit run --all-files
```

#### Docker Issues

```bash
# Clean up containers
docker-compose down -v

# Rebuild images
docker-compose build --no-cache
```

#### Type Checking Errors

```bash
# Clear mypy cache
rm -rf .mypy_cache

# Reinstall type stubs
pip install -r requirements-types.txt
```

### Performance Tips

1. **Parallel Testing**

   ```bash
   pytest -n auto  # Use all CPU cores
   ```

2. **Incremental Type Checking**

   ```bash
   mypy --incremental jimbot
   ```

3. **Selective Pre-commit**

   ```bash
   pre-commit run --files file1.py file2.py
   ```

4. **Docker Layer Caching**
   ```bash
   DOCKER_BUILDKIT=1 docker build .
   ```

## Maintenance

### Updating Tools

```bash
# Update Python tools
pip install --upgrade -r requirements-dev.txt

# Update pre-commit hooks
pre-commit autoupdate

# Update npm packages
npm update

# Update system tools
brew upgrade  # macOS
sudo apt update && sudo apt upgrade  # Ubuntu
```

### Adding New Tools

1. Add tool configuration file
2. Update `.pre-commit-config.yaml`
3. Update CI workflow files
4. Update this documentation
5. Test locally and in CI

## Resources

- [Black Documentation](https://black.readthedocs.io/)
- [mypy Documentation](https://mypy.readthedocs.io/)
- [pytest Documentation](https://docs.pytest.org/)
- [Pre-commit Documentation](https://pre-commit.com/)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
