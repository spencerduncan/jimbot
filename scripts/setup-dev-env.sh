#!/usr/bin/env bash
# Development environment setup script for JimBot
# Supports Ubuntu/Debian, macOS, and other Linux distros

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Detect OS
detect_os() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        if [ -f /etc/debian_version ]; then
            echo "debian"
        elif [ -f /etc/redhat-release ]; then
            echo "redhat"
        elif [ -f /etc/arch-release ]; then
            echo "arch"
        else
            echo "linux"
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macos"
    else
        echo "unknown"
    fi
}

OS=$(detect_os)
log_info "Detected OS: $OS"

# Check if running as root
if [ "$EUID" -eq 0 ]; then 
   log_error "Please do not run this script as root"
   exit 1
fi

# Install system dependencies
install_system_deps() {
    log_info "Installing system dependencies..."
    
    case $OS in
        debian)
            sudo apt-get update
            sudo apt-get install -y \
                build-essential \
                python3-dev \
                python3-pip \
                python3-venv \
                git \
                curl \
                wget \
                clang \
                clang-format \
                clang-tidy \
                cmake \
                ninja-build \
                pkg-config \
                libssl-dev \
                libffi-dev \
                nodejs \
                npm \
                lua5.1 \
                luarocks \
                protobuf-compiler \
                graphviz \
                redis-tools \
                postgresql-client \
                docker.io \
                docker-compose
            ;;
        macos)
            # Check if Homebrew is installed
            if ! command -v brew &> /dev/null; then
                log_error "Homebrew is required. Please install from https://brew.sh/"
                exit 1
            fi
            
            brew update
            brew install \
                python@3.9 \
                git \
                clang-format \
                cmake \
                ninja \
                node \
                lua \
                luarocks \
                protobuf \
                graphviz \
                redis \
                postgresql \
                docker \
                docker-compose
            ;;
        arch)
            sudo pacman -Syu --noconfirm
            sudo pacman -S --noconfirm \
                base-devel \
                python \
                python-pip \
                git \
                clang \
                cmake \
                ninja \
                nodejs \
                npm \
                lua \
                luarocks \
                protobuf \
                graphviz \
                redis \
                postgresql \
                docker \
                docker-compose
            ;;
        *)
            log_error "Unsupported OS. Please install dependencies manually."
            exit 1
            ;;
    esac
    
    log_success "System dependencies installed"
}

# Setup Python environment
setup_python() {
    log_info "Setting up Python environment..."
    
    # Create virtual environment if it doesn't exist
    if [ ! -d "venv" ]; then
        python3 -m venv venv
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Upgrade pip
    pip install --upgrade pip setuptools wheel
    
    # Install Python dependencies
    if [ -f "pyproject.toml" ]; then
        pip install -e ".[dev,test,docs]"
    elif [ -f "requirements.txt" ]; then
        pip install -r requirements.txt
        if [ -f "requirements-dev.txt" ]; then
            pip install -r requirements-dev.txt
        fi
    fi
    
    log_success "Python environment setup complete"
}

# Setup Lua environment
setup_lua() {
    log_info "Setting up Lua environment..."
    
    # Install Lua tools
    luarocks install luacheck --local
    luarocks install luacov --local
    luarocks install ldoc --local
    luarocks install busted --local
    
    # Add luarocks bin to PATH
    eval $(luarocks path)
    
    log_success "Lua environment setup complete"
}

# Setup Node.js environment
setup_nodejs() {
    log_info "Setting up Node.js environment..."
    
    # Install Node.js tools globally
    npm install -g \
        prettier \
        eslint \
        typescript \
        @types/node \
        vitest \
        pnpm
    
    # Install project dependencies if package.json exists
    if [ -f "package.json" ]; then
        npm install
    fi
    
    log_success "Node.js environment setup complete"
}

# Setup C++ environment
setup_cpp() {
    log_info "Setting up C++ environment..."
    
    # Create build directory
    mkdir -p build
    
    # Install additional C++ tools if needed
    if command -v pip &> /dev/null; then
        pip install cpplint cmake-format
    fi
    
    log_success "C++ environment setup complete"
}

# Setup Protocol Buffers
setup_protobuf() {
    log_info "Setting up Protocol Buffers..."
    
    # Install buf
    if ! command -v buf &> /dev/null; then
        # Install buf CLI
        curl -sSL https://github.com/bufbuild/buf/releases/latest/download/buf-Linux-x86_64 -o /tmp/buf
        chmod +x /tmp/buf
        sudo mv /tmp/buf /usr/local/bin/buf
    fi
    
    log_success "Protocol Buffers setup complete"
}

# Setup pre-commit hooks
setup_precommit() {
    log_info "Setting up pre-commit hooks..."
    
    # Install pre-commit
    pip install pre-commit
    
    # Install the git hooks
    pre-commit install
    pre-commit install --hook-type commit-msg
    
    # Run pre-commit on all files
    log_info "Running pre-commit on all files (this may take a while)..."
    pre-commit run --all-files || true
    
    log_success "Pre-commit hooks setup complete"
}

# Setup Docker
setup_docker() {
    log_info "Checking Docker setup..."
    
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install Docker Desktop or Docker Engine."
        return 1
    fi
    
    # Add user to docker group if on Linux
    if [[ "$OS" != "macos" ]]; then
        if ! groups | grep -q docker; then
            log_info "Adding user to docker group..."
            sudo usermod -aG docker $USER
            log_warning "You need to log out and back in for docker group changes to take effect"
        fi
    fi
    
    # Start Docker if not running
    if ! docker info &> /dev/null; then
        log_warning "Docker is not running. Please start Docker."
    else
        log_success "Docker is running"
    fi
}

# Setup development databases
setup_databases() {
    log_info "Setting up development databases..."
    
    # Create docker network if it doesn't exist
    docker network create jimbot-dev 2>/dev/null || true
    
    # Start Memgraph
    docker run -d \
        --name jimbot-memgraph \
        --network jimbot-dev \
        -p 7687:7687 \
        -p 3000:3000 \
        -v jimbot_memgraph_data:/var/lib/memgraph \
        memgraph/memgraph-platform || log_warning "Memgraph container already exists"
    
    # Start QuestDB
    docker run -d \
        --name jimbot-questdb \
        --network jimbot-dev \
        -p 9000:9000 \
        -p 8812:8812 \
        -p 9009:9009 \
        -v jimbot_questdb_data:/var/lib/questdb \
        questdb/questdb || log_warning "QuestDB container already exists"
    
    # Start EventStoreDB
    docker run -d \
        --name jimbot-eventstore \
        --network jimbot-dev \
        -p 2113:2113 \
        -p 1113:1113 \
        -v jimbot_eventstore_data:/var/lib/eventstore \
        eventstore/eventstore:latest --insecure || log_warning "EventStoreDB container already exists"
    
    log_success "Development databases setup complete"
}

# Create necessary directories
create_directories() {
    log_info "Creating project directories..."
    
    mkdir -p \
        jimbot/core \
        jimbot/mcp \
        jimbot/memgraph/mage_modules \
        jimbot/training \
        jimbot/llm \
        jimbot/utils \
        tests/unit \
        tests/integration \
        tests/performance \
        docs \
        proto \
        scripts \
        config
    
    log_success "Project directories created"
}

# Generate initial files
generate_initial_files() {
    log_info "Generating initial files..."
    
    # Create __init__.py files
    find jimbot -type d -exec touch {}/__init__.py \;
    
    # Create .gitignore if it doesn't exist
    if [ ! -f .gitignore ]; then
        cat > .gitignore << EOF
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
.venv/
*.egg-info/
dist/
build/
.pytest_cache/
.mypy_cache/
.coverage
htmlcov/
.hypothesis/

# Lua
*.luac

# C++
build/
*.o
*.so
*.dylib

# Node.js
node_modules/
npm-debug.log*
yarn-error.log*
.pnpm-debug.log*

# IDEs
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db

# Project specific
.env
.env.local
*.log
data/
logs/
models/
checkpoints/
.secrets.baseline
bandit-report.json

# Docker
.dockerignore
EOF
    fi
    
    log_success "Initial files generated"
}

# Main setup function
main() {
    log_info "Starting JimBot development environment setup..."
    
    # Create directories
    create_directories
    
    # Install system dependencies
    install_system_deps
    
    # Setup various environments
    setup_python
    setup_lua
    setup_nodejs
    setup_cpp
    setup_protobuf
    
    # Setup tools
    setup_precommit
    setup_docker
    
    # Optional: Setup databases
    read -p "Do you want to start development databases? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        setup_databases
    fi
    
    # Generate initial files
    generate_initial_files
    
    log_success "Development environment setup complete!"
    log_info "Next steps:"
    echo "  1. Activate Python virtual environment: source venv/bin/activate"
    echo "  2. Run tests: pytest"
    echo "  3. Start development: python -m jimbot.main"
    echo "  4. View documentation: python -m sphinx docs"
    
    if [[ "$OS" != "macos" ]] && ! groups | grep -q docker; then
        log_warning "Remember to log out and back in for docker group changes to take effect"
    fi
}

# Run main function
main