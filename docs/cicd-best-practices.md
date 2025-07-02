# CI/CD Best Practices for Multi-Language Projects

This guide provides comprehensive CI/CD configuration templates and best practices for the JimBot project, which uses Python, Lua, C++, Protocol Buffers, and various databases.

## Table of Contents

1. [Overview](#overview)
2. [GitHub Actions Workflows](#github-actions-workflows)
3. [Pre-commit Framework](#pre-commit-framework)
4. [Development Environment Setup](#development-environment-setup)
5. [Docker-based Development](#docker-based-development)
6. [Code Quality Tools](#code-quality-tools)
7. [Automated Dependency Updates](#automated-dependency-updates)
8. [GPU Testing Considerations](#gpu-testing-considerations)
9. [Best Practices](#best-practices)

## Overview

The JimBot project requires a comprehensive CI/CD pipeline that handles:
- Multiple programming languages (Python, Lua, C++, Protocol Buffers)
- GPU-accelerated machine learning workloads
- Microservices architecture with Docker
- Database integration (Memgraph, QuestDB, EventStoreDB)
- Real-time event processing

## GitHub Actions Workflows

### Main CI/CD Workflow

Create `.github/workflows/main-ci.yml`:

```yaml
name: Main CI/CD Pipeline

on:
  push:
    branches: [ main, develop, 'feature/**' ]
  pull_request:
    branches: [ main, develop ]
  schedule:
    # Run nightly for security updates
    - cron: '0 2 * * *'

env:
  PYTHON_VERSION: '3.10'
  LUA_VERSION: '5.4'
  CMAKE_VERSION: '3.25'
  PROTOC_VERSION: '3.21.12'
  DOCKER_BUILDKIT: 1
  COMPOSE_DOCKER_CLI_BUILD: 1

jobs:
  # Job 1: Format checking across all languages
  format-check:
    name: Format Check
    runs-on: ubuntu-latest
    steps:
    - name: Checkout code
      uses: actions/checkout@v4
      with:
        fetch-depth: 0  # Full history for better diffing

    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: ${{ env.PYTHON_VERSION }}

    - name: Install formatters
      run: |
        # Python formatters
        pip install black isort
        
        # Lua formatter
        wget https://github.com/JohnnyMorganz/StyLua/releases/latest/download/stylua-linux.zip
        unzip stylua-linux.zip
        chmod +x stylua
        sudo mv stylua /usr/local/bin/
        
        # C++ formatter
        sudo apt-get update
        sudo apt-get install -y clang-format-15
        
        # Protocol Buffers formatter
        go install github.com/bufbuild/buf/cmd/buf@latest
        echo "export PATH=$PATH:$(go env GOPATH)/bin" >> $GITHUB_ENV

    - name: Check Python formatting
      run: |
        black --check jimbot tests scripts
        isort --check-only jimbot tests scripts

    - name: Check Lua formatting
      run: |
        find . -name "*.lua" -type f | xargs stylua --check

    - name: Check C++ formatting
      run: |
        find . -name "*.cpp" -o -name "*.h" | xargs clang-format-15 --dry-run --Werror

    - name: Check Protocol Buffers formatting
      run: |
        buf format --diff

  # Job 2: Linting for all languages
  lint:
    name: Lint Code
    runs-on: ubuntu-latest
    needs: format-check
    strategy:
      matrix:
        include:
          - language: python
            files: 'jimbot tests scripts'
          - language: lua
            files: 'mods balatro'
          - language: cpp
            files: 'jimbot/memgraph/mage_modules'
          - language: protobuf
            files: 'jimbot/proto'
    
    steps:
    - name: Checkout code
      uses: actions/checkout@v4

    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: ${{ env.PYTHON_VERSION }}

    - name: Cache dependencies
      uses: actions/cache@v4
      with:
        path: |
          ~/.cache/pip
          ~/.luarocks
          ~/.cache/buf
        key: ${{ runner.os }}-lint-${{ matrix.language }}-${{ hashFiles('**/requirements*.txt', '**/rockspec', '**/buf.yaml') }}

    - name: Install linters
      run: |
        case "${{ matrix.language }}" in
          python)
            pip install flake8 mypy pylint bandit safety
            pip install -r jimbot/infrastructure/requirements.txt
            ;;
          lua)
            sudo apt-get update
            sudo apt-get install -y lua5.4 luarocks
            sudo luarocks install luacheck
            ;;
          cpp)
            sudo apt-get update
            sudo apt-get install -y clang-tidy-15 cppcheck
            ;;
          protobuf)
            go install github.com/bufbuild/buf/cmd/buf@latest
            echo "export PATH=$PATH:$(go env GOPATH)/bin" >> $GITHUB_ENV
            ;;
        esac

    - name: Run linters
      run: |
        case "${{ matrix.language }}" in
          python)
            flake8 ${{ matrix.files }} --config=.flake8
            mypy ${{ matrix.files }} --config-file=mypy.ini
            pylint ${{ matrix.files }} --rcfile=.pylintrc
            bandit -r ${{ matrix.files }} -ll
            safety check
            ;;
          lua)
            luacheck ${{ matrix.files }} --config .luacheckrc
            ;;
          cpp)
            find ${{ matrix.files }} -name "*.cpp" -o -name "*.h" | xargs clang-tidy-15
            cppcheck --enable=all --error-exitcode=1 ${{ matrix.files }}
            ;;
          protobuf)
            cd ${{ matrix.files }} && buf lint
            ;;
        esac

  # Job 3: Unit tests with coverage
  test-unit:
    name: Unit Tests
    runs-on: ubuntu-latest
    needs: lint
    strategy:
      matrix:
        component: [mcp, memgraph, training, llm, analytics, infrastructure]
    
    steps:
    - name: Checkout code
      uses: actions/checkout@v4

    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: ${{ env.PYTHON_VERSION }}

    - name: Cache dependencies
      uses: actions/cache@v4
      with:
        path: ~/.cache/pip
        key: ${{ runner.os }}-pip-${{ matrix.component }}-${{ hashFiles('**/requirements*.txt') }}

    - name: Install dependencies
      run: |
        pip install --upgrade pip setuptools wheel
        pip install -r jimbot/infrastructure/requirements.txt
        pip install pytest pytest-cov pytest-asyncio pytest-benchmark pytest-timeout
        if [ -f "jimbot/${{ matrix.component }}/requirements.txt" ]; then
          pip install -r jimbot/${{ matrix.component }}/requirements.txt
        fi

    - name: Run unit tests
      run: |
        pytest jimbot/tests/unit/${{ matrix.component }}/ \
          -v \
          --cov=jimbot.${{ matrix.component }} \
          --cov-report=xml \
          --cov-report=term-missing \
          --cov-fail-under=80 \
          --benchmark-skip \
          --timeout=300

    - name: Upload coverage
      uses: codecov/codecov-action@v4
      with:
        file: ./coverage.xml
        flags: unit-${{ matrix.component }}
        name: unit-${{ matrix.component }}-coverage

  # Job 4: Integration tests
  test-integration:
    name: Integration Tests
    runs-on: ubuntu-latest
    needs: test-unit
    
    steps:
    - name: Checkout code
      uses: actions/checkout@v4

    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: ${{ env.PYTHON_VERSION }}

    - name: Set up Docker Buildx
      uses: docker/setup-buildx-action@v3

    - name: Start test services
      run: |
        docker-compose -f docker-compose.minimal.yml up -d
        docker-compose -f jimbot/deployment/docker-compose.yml up -d test-services
        
        # Wait for services to be healthy
        timeout 300s bash -c 'until docker ps | grep -E "healthy|running" | wc -l | grep -q "$(docker ps -q | wc -l)"; do sleep 5; done'

    - name: Run integration tests
      run: |
        pip install -r jimbot/infrastructure/requirements.txt
        pip install pytest pytest-asyncio pytest-timeout requests
        
        pytest jimbot/tests/integration/ \
          -v \
          --timeout=600 \
          --tb=short

    - name: Collect service logs
      if: failure()
      run: |
        docker-compose logs > docker-logs.txt
        docker ps -a

    - name: Upload logs
      if: failure()
      uses: actions/upload-artifact@v4
      with:
        name: integration-test-logs
        path: docker-logs.txt

    - name: Stop services
      if: always()
      run: |
        docker-compose -f docker-compose.minimal.yml down -v
        docker-compose -f jimbot/deployment/docker-compose.yml down -v

  # Job 5: GPU tests (self-hosted runner required)
  test-gpu:
    name: GPU Tests
    runs-on: [self-hosted, gpu]
    needs: test-unit
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    
    steps:
    - name: Checkout code
      uses: actions/checkout@v4

    - name: Set up Python with CUDA
      run: |
        # Assuming CUDA is pre-installed on self-hosted runner
        python -m venv venv-gpu
        source venv-gpu/bin/activate
        pip install --upgrade pip
        pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
        pip install -r jimbot/training/requirements.txt

    - name: Verify GPU availability
      run: |
        source venv-gpu/bin/activate
        python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}'); print(f'GPU count: {torch.cuda.device_count()}')"

    - name: Run GPU tests
      run: |
        source venv-gpu/bin/activate
        pytest jimbot/tests/unit/training/ \
          -v \
          -m gpu \
          --timeout=1800

    - name: Run training smoke test
      run: |
        source venv-gpu/bin/activate
        python -m jimbot.training.run --test-mode --max-iterations=10

  # Job 6: Build and test Docker images
  build-docker:
    name: Build Docker Images
    runs-on: ubuntu-latest
    needs: [test-unit, lint]
    strategy:
      matrix:
        service: [mcp, ray, claude, analytics, memgraph]
    
    steps:
    - name: Checkout code
      uses: actions/checkout@v4

    - name: Set up Docker Buildx
      uses: docker/setup-buildx-action@v3

    - name: Log in to Docker Hub
      if: github.event_name != 'pull_request'
      uses: docker/login-action@v3
      with:
        username: ${{ secrets.DOCKER_USERNAME }}
        password: ${{ secrets.DOCKER_TOKEN }}

    - name: Build and test image
      uses: docker/build-push-action@v5
      with:
        context: .
        file: jimbot/deployment/docker/services/Dockerfile.${{ matrix.service }}
        target: test
        load: true
        tags: jimbot/${{ matrix.service }}:test
        cache-from: type=gha
        cache-to: type=gha,mode=max

    - name: Run container tests
      run: |
        docker run --rm jimbot/${{ matrix.service }}:test pytest /app/tests/

    - name: Security scan with Trivy
      uses: aquasecurity/trivy-action@master
      with:
        image-ref: jimbot/${{ matrix.service }}:test
        format: 'sarif'
        output: 'trivy-${{ matrix.service }}.sarif'
        severity: 'CRITICAL,HIGH'

    - name: Upload Trivy results
      uses: github/codeql-action/upload-sarif@v3
      with:
        sarif_file: 'trivy-${{ matrix.service }}.sarif'

    - name: Build and push production image
      if: github.event_name != 'pull_request'
      uses: docker/build-push-action@v5
      with:
        context: .
        file: jimbot/deployment/docker/services/Dockerfile.${{ matrix.service }}
        push: true
        tags: |
          jimbot/${{ matrix.service }}:latest
          jimbot/${{ matrix.service }}:${{ github.sha }}
        cache-from: type=gha
        cache-to: type=gha,mode=max

  # Job 7: Performance benchmarks
  benchmark:
    name: Performance Benchmarks
    runs-on: ubuntu-latest
    needs: build-docker
    if: github.event_name == 'push'
    
    steps:
    - name: Checkout code
      uses: actions/checkout@v4

    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: ${{ env.PYTHON_VERSION }}

    - name: Install dependencies
      run: |
        pip install -r jimbot/infrastructure/requirements.txt
        pip install pytest pytest-benchmark

    - name: Run benchmarks
      run: |
        pytest jimbot/tests/performance/ \
          --benchmark-only \
          --benchmark-json=benchmark.json \
          --benchmark-autosave

    - name: Store benchmark results
      uses: benchmark-action/github-action-benchmark@v1
      with:
        tool: 'pytest'
        output-file-path: benchmark.json
        github-token: ${{ secrets.GITHUB_TOKEN }}
        auto-push: true
        comment-on-alert: true
        alert-threshold: '150%'
        fail-on-alert: true

  # Job 8: Documentation build
  docs:
    name: Build Documentation
    runs-on: ubuntu-latest
    needs: format-check
    
    steps:
    - name: Checkout code
      uses: actions/checkout@v4

    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: ${{ env.PYTHON_VERSION }}

    - name: Install documentation tools
      run: |
        pip install sphinx sphinx-rtd-theme myst-parser autodoc

    - name: Build documentation
      run: |
        cd docs
        make clean
        make html

    - name: Upload documentation
      uses: actions/upload-artifact@v4
      with:
        name: documentation
        path: docs/_build/html/

  # Job 9: Release
  release:
    name: Create Release
    runs-on: ubuntu-latest
    needs: [build-docker, test-integration, benchmark]
    if: startsWith(github.ref, 'refs/tags/v')
    
    steps:
    - name: Checkout code
      uses: actions/checkout@v4

    - name: Generate changelog
      id: changelog
      run: |
        # Generate changelog from commits
        echo "CHANGELOG<<EOF" >> $GITHUB_OUTPUT
        git log --pretty=format:"- %s" $(git describe --tags --abbrev=0 HEAD^)..HEAD >> $GITHUB_OUTPUT
        echo "EOF" >> $GITHUB_OUTPUT

    - name: Create Release
      uses: actions/create-release@v1
      env:
        GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
      with:
        tag_name: ${{ github.ref }}
        release_name: Release ${{ github.ref }}
        body: |
          ## Changes in this release
          ${{ steps.changelog.outputs.CHANGELOG }}
          
          ## Docker Images
          - `jimbot/mcp:${{ github.ref_name }}`
          - `jimbot/ray:${{ github.ref_name }}`
          - `jimbot/claude:${{ github.ref_name }}`
          - `jimbot/analytics:${{ github.ref_name }}`
          - `jimbot/memgraph:${{ github.ref_name }}`
        draft: false
        prerelease: ${{ contains(github.ref, '-rc') || contains(github.ref, '-beta') }}
```

### Language-Specific Workflows

Create `.github/workflows/lua-ci.yml`:

```yaml
name: Lua CI

on:
  push:
    paths:
      - '**.lua'
      - 'mods/**'
      - 'balatro/**'
  pull_request:
    paths:
      - '**.lua'
      - 'mods/**'
      - 'balatro/**'

jobs:
  lua-checks:
    name: Lua Checks
    runs-on: ubuntu-latest
    
    steps:
    - name: Checkout code
      uses: actions/checkout@v4

    - name: Set up Lua
      uses: leafo/gh-actions-lua@v10
      with:
        luaVersion: "5.4"

    - name: Set up LuaRocks
      uses: leafo/gh-actions-luarocks@v4

    - name: Install dependencies
      run: |
        luarocks install luacheck
        luarocks install luacov
        luarocks install busted

    - name: Run luacheck
      run: |
        luacheck . --config .luacheckrc

    - name: Run tests
      run: |
        busted --coverage

    - name: Generate coverage report
      run: |
        luacov
        luacov-console

    - name: Upload coverage
      uses: codecov/codecov-action@v4
      with:
        files: ./luacov.report.out
        flags: lua
```

Create `.github/workflows/cpp-ci.yml`:

```yaml
name: C++ CI

on:
  push:
    paths:
      - '**.cpp'
      - '**.h'
      - '**/CMakeLists.txt'
  pull_request:
    paths:
      - '**.cpp'
      - '**.h'
      - '**/CMakeLists.txt'

jobs:
  cpp-checks:
    name: C++ Checks
    runs-on: ubuntu-latest
    
    steps:
    - name: Checkout code
      uses: actions/checkout@v4

    - name: Install dependencies
      run: |
        sudo apt-get update
        sudo apt-get install -y cmake clang-15 clang-tidy-15 cppcheck lcov

    - name: Configure CMake
      run: |
        cmake -B build \
          -DCMAKE_C_COMPILER=clang-15 \
          -DCMAKE_CXX_COMPILER=clang++-15 \
          -DCMAKE_BUILD_TYPE=Debug \
          -DCMAKE_EXPORT_COMPILE_COMMANDS=ON \
          -DENABLE_COVERAGE=ON

    - name: Run clang-tidy
      run: |
        find . -name "*.cpp" -o -name "*.h" | xargs clang-tidy-15 -p build

    - name: Run cppcheck
      run: |
        cppcheck --enable=all --error-exitcode=1 --project=build/compile_commands.json

    - name: Build
      run: |
        cmake --build build --parallel

    - name: Run tests
      run: |
        cd build
        ctest --output-on-failure

    - name: Generate coverage
      run: |
        lcov --capture --directory build --output-file coverage.info
        lcov --remove coverage.info '/usr/*' --output-file coverage.info

    - name: Upload coverage
      uses: codecov/codecov-action@v4
      with:
        files: ./coverage.info
        flags: cpp
```

## Pre-commit Framework

Create `.pre-commit-config.yaml`:

```yaml
# See https://pre-commit.com for more information
# See https://pre-commit.com/hooks.html for more hooks
repos:
  # General
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
        args: ['--allow-multiple-documents']
      - id: check-added-large-files
        args: ['--maxkb=5000']
      - id: check-case-conflict
      - id: check-merge-conflict
      - id: check-json
      - id: check-toml
      - id: check-xml
      - id: detect-private-key
      - id: mixed-line-ending
        args: ['--fix=lf']

  # Python
  - repo: https://github.com/psf/black
    rev: 24.1.1
    hooks:
      - id: black
        language_version: python3.10
        args: ['--line-length=100']

  - repo: https://github.com/pycqa/isort
    rev: 5.13.2
    hooks:
      - id: isort
        args: ['--profile=black', '--line-length=100']

  - repo: https://github.com/pycqa/flake8
    rev: 7.0.0
    hooks:
      - id: flake8
        args: ['--max-line-length=100', '--extend-ignore=E203,W503']
        additional_dependencies: [flake8-docstrings, flake8-bugbear]

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.8.0
    hooks:
      - id: mypy
        additional_dependencies: [types-all]
        args: ['--ignore-missing-imports']

  - repo: https://github.com/pycqa/bandit
    rev: 1.7.6
    hooks:
      - id: bandit
        args: ['-ll', '-r', 'jimbot']

  # Lua
  - repo: https://github.com/JohnnyMorganz/StyLua
    rev: v0.19.1
    hooks:
      - id: stylua

  - repo: https://github.com/lunarmodules/luacheck
    rev: v1.1.2
    hooks:
      - id: luacheck

  # C++
  - repo: https://github.com/pre-commit/mirrors-clang-format
    rev: v17.0.6
    hooks:
      - id: clang-format
        types_or: [c++, c]

  # Protocol Buffers
  - repo: https://github.com/bufbuild/buf
    rev: v1.28.1
    hooks:
      - id: buf-format
      - id: buf-lint

  # Docker
  - repo: https://github.com/hadolint/hadolint
    rev: v2.12.0
    hooks:
      - id: hadolint-docker
        args: ['--ignore', 'DL3008', '--ignore', 'DL3009']

  # Security
  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.4.0
    hooks:
      - id: detect-secrets
        args: ['--baseline', '.secrets.baseline']

  # Documentation
  - repo: https://github.com/pre-commit/mirrors-prettier
    rev: v4.0.0-alpha.8
    hooks:
      - id: prettier
        types_or: [markdown, yaml]

  # Shell scripts
  - repo: https://github.com/shellcheck-py/shellcheck-py
    rev: v0.9.0.6
    hooks:
      - id: shellcheck

  # Git commit messages
  - repo: https://github.com/commitizen-tools/commitizen
    rev: v3.13.0
    hooks:
      - id: commitizen
        stages: [commit-msg]

# Local hooks
  - repo: local
    hooks:
      - id: pytest-check
        name: pytest-check
        entry: pytest
        language: system
        pass_filenames: false
        always_run: true
        args: ['tests/unit/', '--tb=short', '-q']
```

## Development Environment Setup

Create `scripts/setup-dev-env.sh`:

```bash
#!/bin/bash
set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Setting up JimBot development environment...${NC}"

# Detect OS
OS="unknown"
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="linux"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macos"
elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
    OS="windows"
fi

echo "Detected OS: $OS"

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to install system dependencies
install_system_deps() {
    echo -e "${YELLOW}Installing system dependencies...${NC}"
    
    if [[ "$OS" == "linux" ]]; then
        sudo apt-get update
        sudo apt-get install -y \
            python3.10 python3.10-dev python3.10-venv \
            lua5.4 liblua5.4-dev luarocks \
            cmake clang clang-tidy clang-format \
            protobuf-compiler \
            git curl wget \
            docker.io docker-compose \
            nvidia-docker2  # For GPU support
            
    elif [[ "$OS" == "macos" ]]; then
        # Install Homebrew if not present
        if ! command_exists brew; then
            /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        fi
        
        brew update
        brew install \
            python@3.10 \
            lua luarocks \
            cmake llvm \
            protobuf \
            docker docker-compose
            
    elif [[ "$OS" == "windows" ]]; then
        echo "Please install the following manually:"
        echo "- Python 3.10 from python.org"
        echo "- Lua 5.4 from lua.org"
        echo "- CMake from cmake.org"
        echo "- Docker Desktop from docker.com"
        echo "- Protocol Buffers from github.com/protocolbuffers/protobuf"
        exit 1
    fi
}

# Function to setup Python environment
setup_python() {
    echo -e "${YELLOW}Setting up Python environment...${NC}"
    
    # Create virtual environment
    python3.10 -m venv venv
    source venv/bin/activate
    
    # Upgrade pip and install base tools
    pip install --upgrade pip setuptools wheel
    
    # Install development dependencies
    pip install \
        black isort flake8 mypy pylint bandit safety \
        pytest pytest-cov pytest-asyncio pytest-benchmark pytest-timeout \
        pre-commit \
        sphinx sphinx-rtd-theme myst-parser
    
    # Install project requirements
    if [[ -f "jimbot/infrastructure/requirements.txt" ]]; then
        pip install -r jimbot/infrastructure/requirements.txt
    fi
    
    # Install component-specific requirements
    for req in jimbot/*/requirements.txt; do
        if [[ -f "$req" ]]; then
            echo "Installing $req..."
            pip install -r "$req"
        fi
    done
}

# Function to setup Lua environment
setup_lua() {
    echo -e "${YELLOW}Setting up Lua environment...${NC}"
    
    # Install Lua development tools
    sudo luarocks install luacheck
    sudo luarocks install luacov
    sudo luarocks install busted
    sudo luarocks install penlight
    
    # Download and install StyLua
    if [[ "$OS" == "linux" ]]; then
        wget https://github.com/JohnnyMorganz/StyLua/releases/latest/download/stylua-linux.zip
        unzip stylua-linux.zip
        chmod +x stylua
        sudo mv stylua /usr/local/bin/
        rm stylua-linux.zip
    elif [[ "$OS" == "macos" ]]; then
        wget https://github.com/JohnnyMorganz/StyLua/releases/latest/download/stylua-macos.zip
        unzip stylua-macos.zip
        chmod +x stylua
        sudo mv stylua /usr/local/bin/
        rm stylua-macos.zip
    fi
}

# Function to setup C++ environment
setup_cpp() {
    echo -e "${YELLOW}Setting up C++ environment...${NC}"
    
    # Create build directory
    mkdir -p build
    
    # Configure CMake
    cmake -B build \
        -DCMAKE_BUILD_TYPE=Debug \
        -DCMAKE_EXPORT_COMPILE_COMMANDS=ON \
        -DENABLE_TESTING=ON \
        -DENABLE_COVERAGE=ON
}

# Function to setup Protocol Buffers
setup_protobuf() {
    echo -e "${YELLOW}Setting up Protocol Buffers...${NC}"
    
    # Install buf
    if ! command_exists buf; then
        curl -sSL https://github.com/bufbuild/buf/releases/latest/download/buf-Linux-x86_64 -o buf
        chmod +x buf
        sudo mv buf /usr/local/bin/
    fi
    
    # Compile proto files
    cd jimbot/proto
    protoc --python_out=.. *.proto
    cd ../..
}

# Function to setup pre-commit hooks
setup_precommit() {
    echo -e "${YELLOW}Setting up pre-commit hooks...${NC}"
    
    pre-commit install
    pre-commit install --hook-type commit-msg
    pre-commit run --all-files || true  # Run once to download all tools
}

# Function to setup Docker environment
setup_docker() {
    echo -e "${YELLOW}Setting up Docker environment...${NC}"
    
    # Add user to docker group
    if [[ "$OS" == "linux" ]]; then
        sudo usermod -aG docker $USER
        echo "You may need to log out and back in for docker group changes to take effect"
    fi
    
    # Pull base images
    docker pull python:3.10-slim
    docker pull ubuntu:22.04
    docker pull memgraph/memgraph-platform:latest
    docker pull questdb/questdb:latest
    docker pull eventstore/eventstore:latest
}

# Function to create configuration files
create_configs() {
    echo -e "${YELLOW}Creating configuration files...${NC}"
    
    # Create .env file
    if [[ ! -f ".env" ]]; then
        cat > .env << EOF
# Environment configuration
ENVIRONMENT=development
DEBUG=true

# Python
PYTHONPATH=\${PYTHONPATH}:${PWD}

# Docker
COMPOSE_PROJECT_NAME=jimbot
DOCKER_BUILDKIT=1
COMPOSE_DOCKER_CLI_BUILD=1

# GPU
CUDA_VISIBLE_DEVICES=0

# Services
MEMGRAPH_HOST=localhost
MEMGRAPH_PORT=7687
QUESTDB_HOST=localhost
QUESTDB_PORT=9000
EVENTSTORE_HOST=localhost
EVENTSTORE_PORT=2113

# Claude API
CLAUDE_API_KEY=your-api-key-here
CLAUDE_RATE_LIMIT=100
EOF
    fi
    
    # Create .flake8
    if [[ ! -f ".flake8" ]]; then
        cat > .flake8 << EOF
[flake8]
max-line-length = 100
extend-ignore = E203, W503
exclude = .git,__pycache__,venv,build,dist
max-complexity = 10
EOF
    fi
    
    # Create mypy.ini
    if [[ ! -f "mypy.ini" ]]; then
        cat > mypy.ini << EOF
[mypy]
python_version = 3.10
warn_return_any = True
warn_unused_configs = True
disallow_untyped_defs = True
ignore_missing_imports = True
exclude = venv|build|dist
EOF
    fi
    
    # Create .pylintrc
    if [[ ! -f ".pylintrc" ]]; then
        pylint --generate-rcfile > .pylintrc
    fi
    
    # Create .luacheckrc
    if [[ ! -f ".luacheckrc" ]]; then
        cat > .luacheckrc << EOF
std = "lua54"
codes = true
ignore = {"212", "213"}
globals = {"G", "SMODS", "love"}
exclude_files = {"libs/*", "vendor/*"}
EOF
    fi
    
    # Create .clang-format
    if [[ ! -f ".clang-format" ]]; then
        cat > .clang-format << EOF
---
Language: Cpp
BasedOnStyle: Google
IndentWidth: 4
ColumnLimit: 100
AllowShortFunctionsOnASingleLine: Inline
AllowShortIfStatementsOnASingleLine: Never
EOF
    fi
    
    # Create buf.yaml
    if [[ ! -f "buf.yaml" ]]; then
        cat > buf.yaml << EOF
version: v1
breaking:
  use:
    - FILE
lint:
  use:
    - DEFAULT
EOF
    fi
}

# Function to verify installation
verify_installation() {
    echo -e "${YELLOW}Verifying installation...${NC}"
    
    local all_good=true
    
    # Check Python
    if python --version | grep -q "3.10"; then
        echo -e "${GREEN}✓ Python 3.10${NC}"
    else
        echo -e "${RED}✗ Python 3.10${NC}"
        all_good=false
    fi
    
    # Check Lua
    if lua -v | grep -q "5.4"; then
        echo -e "${GREEN}✓ Lua 5.4${NC}"
    else
        echo -e "${RED}✗ Lua 5.4${NC}"
        all_good=false
    fi
    
    # Check Docker
    if docker --version > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Docker${NC}"
    else
        echo -e "${RED}✗ Docker${NC}"
        all_good=false
    fi
    
    # Check pre-commit
    if pre-commit --version > /dev/null 2>&1; then
        echo -e "${GREEN}✓ pre-commit${NC}"
    else
        echo -e "${RED}✗ pre-commit${NC}"
        all_good=false
    fi
    
    if $all_good; then
        echo -e "${GREEN}All dependencies installed successfully!${NC}"
    else
        echo -e "${RED}Some dependencies are missing. Please check the output above.${NC}"
        exit 1
    fi
}

# Main installation flow
main() {
    # Check if running in project root
    if [[ ! -f "CLAUDE.md" ]]; then
        echo -e "${RED}Please run this script from the project root directory${NC}"
        exit 1
    fi
    
    # Install system dependencies
    install_system_deps
    
    # Setup language environments
    setup_python
    setup_lua
    setup_cpp
    setup_protobuf
    
    # Setup development tools
    setup_precommit
    setup_docker
    
    # Create configuration files
    create_configs
    
    # Verify installation
    verify_installation
    
    echo -e "${GREEN}Development environment setup complete!${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Activate Python virtual environment: source venv/bin/activate"
    echo "2. Start Docker services: docker-compose up -d"
    echo "3. Run tests: pytest"
    echo "4. Make your first commit to test pre-commit hooks"
}

# Run main function
main
```

## Docker-based Development

Create `docker-compose.dev.yml`:

```yaml
version: '3.8'

services:
  # Development container with all tools installed
  dev-env:
    build:
      context: .
      dockerfile: Dockerfile.dev
    image: jimbot-dev:latest
    volumes:
      - .:/workspace
      - /var/run/docker.sock:/var/run/docker.sock
      - ~/.gitconfig:/etc/gitconfig:ro
      - ~/.ssh:/root/.ssh:ro
    environment:
      - DISPLAY=${DISPLAY}
      - PYTHONPATH=/workspace
    working_dir: /workspace
    command: /bin/bash
    stdin_open: true
    tty: true
    networks:
      - jimbot
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]

  # Jupyter notebook for interactive development
  jupyter:
    image: jupyter/tensorflow-notebook:latest
    ports:
      - "8888:8888"
    volumes:
      - .:/home/jovyan/work
    environment:
      - JUPYTER_ENABLE_LAB=yes
    networks:
      - jimbot

  # Code quality dashboard
  sonarqube:
    image: sonarqube:community
    ports:
      - "9001:9000"
    environment:
      - SONAR_ES_BOOTSTRAP_CHECKS_DISABLE=true
    volumes:
      - sonarqube_data:/opt/sonarqube/data
      - sonarqube_extensions:/opt/sonarqube/extensions
      - sonarqube_logs:/opt/sonarqube/logs
    networks:
      - jimbot

  # Development database for testing
  postgres-test:
    image: postgres:15
    environment:
      - POSTGRES_DB=jimbot_test
      - POSTGRES_USER=jimbot
      - POSTGRES_PASSWORD=testpass
    ports:
      - "5433:5432"
    networks:
      - jimbot

  # Redis for caching and rate limiting
  redis-dev:
    image: redis:7-alpine
    ports:
      - "6380:6379"
    networks:
      - jimbot

  # Prometheus for metrics
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
    networks:
      - jimbot

  # Grafana for visualization
  grafana:
    image: grafana/grafana:latest
    ports:
      - "3001:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana_data:/var/lib/grafana
    networks:
      - jimbot

networks:
  jimbot:
    driver: bridge

volumes:
  sonarqube_data:
  sonarqube_extensions:
  sonarqube_logs:
  grafana_data:
```

Create `Dockerfile.dev`:

```dockerfile
FROM nvidia/cuda:11.8.0-cudnn8-devel-ubuntu22.04

# Prevent interactive prompts
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    # Python
    python3.10 python3.10-dev python3.10-venv python3-pip \
    # Lua
    lua5.4 liblua5.4-dev luarocks \
    # C++ development
    build-essential cmake clang clang-tidy clang-format \
    cppcheck lcov \
    # Protocol Buffers
    protobuf-compiler libprotobuf-dev \
    # Development tools
    git curl wget vim nano htop \
    docker.io \
    # GPU tools
    nvidia-utils-515 \
    && rm -rf /var/lib/apt/lists/*

# Install Python development tools
RUN pip3 install --upgrade pip setuptools wheel && \
    pip3 install \
    black isort flake8 mypy pylint bandit safety \
    pytest pytest-cov pytest-asyncio pytest-benchmark \
    pre-commit \
    jupyter notebook ipython \
    torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# Install Lua development tools
RUN luarocks install luacheck && \
    luarocks install luacov && \
    luarocks install busted

# Install stylua
RUN wget https://github.com/JohnnyMorganz/StyLua/releases/latest/download/stylua-linux.zip && \
    unzip stylua-linux.zip && \
    chmod +x stylua && \
    mv stylua /usr/local/bin/ && \
    rm stylua-linux.zip

# Install buf for Protocol Buffers
RUN curl -sSL https://github.com/bufbuild/buf/releases/latest/download/buf-Linux-x86_64 -o /usr/local/bin/buf && \
    chmod +x /usr/local/bin/buf

# Install Go for additional tools
RUN wget https://go.dev/dl/go1.21.5.linux-amd64.tar.gz && \
    tar -C /usr/local -xzf go1.21.5.linux-amd64.tar.gz && \
    rm go1.21.5.linux-amd64.tar.gz
ENV PATH=$PATH:/usr/local/go/bin

# Install additional development tools
RUN go install github.com/bufbuild/buf/cmd/buf@latest && \
    go install github.com/fullstorydev/grpcurl/cmd/grpcurl@latest

# Create workspace directory
WORKDIR /workspace

# Set up entrypoint
COPY scripts/docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["/bin/bash"]
```

## Code Quality Tools Integration

Create `.github/workflows/code-quality.yml`:

```yaml
name: Code Quality

on:
  pull_request:
    branches: [ main, develop ]

jobs:
  sonarqube:
    name: SonarQube Analysis
    runs-on: ubuntu-latest
    
    steps:
    - name: Checkout code
      uses: actions/checkout@v4
      with:
        fetch-depth: 0  # Shallow clones should be disabled for better analysis

    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: '3.10'

    - name: Install dependencies
      run: |
        pip install coverage pytest pytest-cov

    - name: Run tests with coverage
      run: |
        pytest --cov=jimbot --cov-report=xml --cov-report=term

    - name: SonarQube Scan
      uses: SonarSource/sonarqube-scan-action@master
      env:
        GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        SONAR_TOKEN: ${{ secrets.SONAR_TOKEN }}
        SONAR_HOST_URL: ${{ secrets.SONAR_HOST_URL }}

  codeclimate:
    name: CodeClimate Analysis
    runs-on: ubuntu-latest
    
    steps:
    - name: Checkout code
      uses: actions/checkout@v4

    - name: Run CodeClimate
      uses: paambaati/codeclimate-action@v5.0.0
      env:
        CC_TEST_REPORTER_ID: ${{ secrets.CC_TEST_REPORTER_ID }}
      with:
        coverageCommand: pytest --cov=jimbot --cov-report=xml
        debug: true

  codeql:
    name: CodeQL Analysis
    runs-on: ubuntu-latest
    permissions:
      actions: read
      contents: read
      security-events: write
    
    strategy:
      fail-fast: false
      matrix:
        language: [ 'python', 'cpp' ]
    
    steps:
    - name: Checkout repository
      uses: actions/checkout@v4

    - name: Initialize CodeQL
      uses: github/codeql-action/init@v3
      with:
        languages: ${{ matrix.language }}

    - name: Autobuild
      uses: github/codeql-action/autobuild@v3

    - name: Perform CodeQL Analysis
      uses: github/codeql-action/analyze@v3
```

## Automated Dependency Updates

Create `.github/dependabot.yml`:

```yaml
version: 2
updates:
  # Python dependencies
  - package-ecosystem: "pip"
    directory: "/"
    schedule:
      interval: "weekly"
      day: "monday"
      time: "04:00"
    open-pull-requests-limit: 10
    labels:
      - "dependencies"
      - "python"
    reviewers:
      - "spencerduncan"
    commit-message:
      prefix: "chore"
      include: "scope"

  # Docker dependencies
  - package-ecosystem: "docker"
    directory: "/jimbot/deployment/docker/services"
    schedule:
      interval: "weekly"
    labels:
      - "dependencies"
      - "docker"

  # GitHub Actions
  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"
    labels:
      - "dependencies"
      - "github-actions"

  # npm dependencies (if any)
  - package-ecosystem: "npm"
    directory: "/"
    schedule:
      interval: "weekly"
    labels:
      - "dependencies"
      - "javascript"
```

Create `.github/renovate.json` (alternative to Dependabot):

```json
{
  "$schema": "https://docs.renovatebot.com/renovate-schema.json",
  "extends": [
    "config:base"
  ],
  "packageRules": [
    {
      "description": "Automatically merge minor and patch updates",
      "matchUpdateTypes": ["minor", "patch"],
      "automerge": true
    },
    {
      "description": "Require approval for major updates",
      "matchUpdateTypes": ["major"],
      "automerge": false
    },
    {
      "description": "Group Python dependencies",
      "matchLanguages": ["python"],
      "groupName": "python dependencies",
      "groupSlug": "python"
    },
    {
      "description": "Group Docker dependencies",
      "matchDatasources": ["docker"],
      "groupName": "docker dependencies",
      "groupSlug": "docker"
    },
    {
      "description": "Security updates",
      "matchDatasources": ["pypi"],
      "matchPackageNames": ["safety", "bandit"],
      "automerge": true,
      "schedule": ["at any time"]
    }
  ],
  "vulnerabilityAlerts": {
    "enabled": true,
    "labels": ["security"]
  },
  "timezone": "America/New_York",
  "schedule": ["before 5am on monday"],
  "prConcurrentLimit": 10,
  "prCreation": "immediate",
  "semanticCommits": "enabled",
  "labels": ["dependencies"],
  "assignees": ["spencerduncan"]
}
```

## GPU Testing Considerations

Create `.github/workflows/gpu-tests.yml`:

```yaml
name: GPU Tests

on:
  push:
    branches: [ main ]
    paths:
      - 'jimbot/training/**'
      - 'jimbot/memgraph/mage_modules/**'
  pull_request:
    branches: [ main ]
    paths:
      - 'jimbot/training/**'
      - 'jimbot/memgraph/mage_modules/**'
  schedule:
    # Run weekly to ensure GPU compatibility
    - cron: '0 0 * * 0'

jobs:
  gpu-tests:
    name: GPU Tests
    runs-on: [self-hosted, gpu]
    container:
      image: nvidia/cuda:11.8.0-cudnn8-devel-ubuntu22.04
      options: --gpus all
    
    steps:
    - name: Checkout code
      uses: actions/checkout@v4

    - name: Set up Python with CUDA
      run: |
        apt-get update
        apt-get install -y python3.10 python3.10-dev python3-pip
        pip3 install --upgrade pip
        pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

    - name: Install dependencies
      run: |
        pip3 install -r jimbot/training/requirements.txt
        pip3 install pytest pytest-timeout pytest-benchmark

    - name: Verify GPU availability
      run: |
        nvidia-smi
        python3 -c "import torch; print(f'PyTorch version: {torch.__version__}'); print(f'CUDA available: {torch.cuda.is_available()}'); print(f'GPU count: {torch.cuda.device_count()}')"

    - name: Run GPU unit tests
      run: |
        pytest jimbot/tests/unit/training/ -v -m gpu --timeout=1800

    - name: Run GPU integration tests
      run: |
        pytest jimbot/tests/integration/gpu/ -v --timeout=3600

    - name: Run training benchmark
      run: |
        python3 -m jimbot.training.run --benchmark --max-iterations=100

    - name: Profile GPU memory usage
      run: |
        nsys profile --stats=true python3 -m jimbot.training.run --profile --max-iterations=10

    - name: Upload profiling results
      uses: actions/upload-artifact@v4
      with:
        name: gpu-profiling-results
        path: |
          *.qdrep
          *.sqlite
```

## Best Practices

Create `docs/cicd-practices.md`:

```markdown
# CI/CD Best Practices for JimBot

## General Principles

1. **Fast Feedback**: Keep CI runs under 10 minutes for PR builds
2. **Parallelization**: Run independent jobs in parallel
3. **Caching**: Cache dependencies aggressively
4. **Fail Fast**: Run quick checks (formatting, linting) before expensive tests
5. **Progressive Testing**: Unit → Integration → E2E → Performance
6. **Security First**: Run security scans on every PR

## Language-Specific Guidelines

### Python
- Use `black` for consistent formatting
- Run `mypy` for type checking
- Minimum 80% code coverage
- Use `pytest-xdist` for parallel test execution

### Lua
- Use `stylua` for formatting
- Run `luacheck` for static analysis
- Test with multiple Lua versions if supporting multiple

### C++
- Use `clang-format` for consistent style
- Run `clang-tidy` and `cppcheck` for static analysis
- Use `AddressSanitizer` in debug builds
- Generate coverage reports with `lcov`

### Protocol Buffers
- Use `buf` for linting and breaking change detection
- Version your schemas properly
- Generate code in CI to ensure consistency

## Docker Best Practices

1. **Multi-stage builds**: Separate build and runtime stages
2. **Layer caching**: Order Dockerfile commands for optimal caching
3. **Security scanning**: Run Trivy or similar on all images
4. **Size optimization**: Use slim base images, remove build dependencies
5. **Health checks**: Define health checks for all services

## GPU Testing Best Practices

1. **Self-hosted runners**: Use dedicated GPU machines
2. **Resource limits**: Set GPU memory limits to prevent OOM
3. **Profiling**: Regular profiling to catch performance regressions
4. **Multiple GPU tests**: Test multi-GPU configurations
5. **CUDA compatibility**: Test with multiple CUDA versions

## Monitoring and Alerting

1. **Build status badges**: Display in README
2. **Slack/Discord notifications**: Alert on failures
3. **Performance tracking**: Monitor test execution times
4. **Flaky test detection**: Automatically retry and report flaky tests
5. **Cost monitoring**: Track CI/CD resource usage

## Security Considerations

1. **Secret management**: Use GitHub Secrets or similar
2. **Dependency scanning**: Regular vulnerability scans
3. **Code scanning**: SAST tools on every commit
4. **Container scanning**: Scan all Docker images
5. **License compliance**: Check dependency licenses

## Release Process

1. **Semantic versioning**: Use conventional commits
2. **Automated changelogs**: Generate from commit messages
3. **Release notes**: Include breaking changes, new features
4. **Rollback plan**: Document and test rollback procedures
5. **Smoke tests**: Run after each deployment

## Troubleshooting

Common issues and solutions:

1. **Flaky tests**: Use retry logic, investigate root causes
2. **Slow builds**: Profile and optimize, use better caching
3. **GPU tests failing**: Check CUDA versions, driver compatibility
4. **Memory issues**: Set appropriate resource limits
5. **Network timeouts**: Use retry logic, consider mirrors

## Continuous Improvement

1. **Regular reviews**: Monthly CI/CD performance reviews
2. **Developer feedback**: Survey team about pain points
3. **Metrics tracking**: Build times, failure rates, MTTR
4. **Tool updates**: Keep CI/CD tools up to date
5. **Documentation**: Keep this guide updated
```

This comprehensive CI/CD configuration provides:

1. **Multi-language support**: Handles Python, Lua, C++, and Protocol Buffers
2. **GPU testing**: Dedicated workflows for GPU-accelerated code
3. **Docker integration**: Build, test, and push container images
4. **Code quality**: Multiple static analysis and security scanning tools
5. **Automated updates**: Dependabot and Renovate configurations
6. **Development environment**: Scripts and Docker setup for consistent dev environments
7. **Pre-commit hooks**: Catch issues before they reach CI
8. **Performance tracking**: Benchmark results and profiling
9. **Documentation**: Comprehensive best practices guide

The configuration is modular and can be adapted based on specific project needs while maintaining high code quality standards.