#!/bin/bash
set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}JimBot Development Container${NC}"
echo -e "${GREEN}=============================${NC}"

# Check GPU availability
if command -v nvidia-smi &> /dev/null; then
    echo -e "${YELLOW}GPU Status:${NC}"
    nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader,nounits | while read line; do
        echo "  - $line"
    done
else
    echo -e "${YELLOW}No GPU detected${NC}"
fi

# Set up Python path
export PYTHONPATH=/workspace:$PYTHONPATH

# Check if virtual environment exists
if [ -d "/workspace/venv" ]; then
    echo -e "${YELLOW}Activating Python virtual environment...${NC}"
    source /workspace/venv/bin/activate
fi

# Set up Git safe directory (for Docker volumes)
git config --global --add safe.directory /workspace

# Display helpful information
echo ""
echo -e "${GREEN}Available commands:${NC}"
echo "  - pytest: Run tests"
echo "  - black: Format Python code"
echo "  - stylua: Format Lua code"
echo "  - luacheck: Lint Lua code"
echo "  - buf: Protocol Buffer tools"
echo "  - pre-commit: Run pre-commit hooks"
echo ""
echo -e "${GREEN}Useful paths:${NC}"
echo "  - Project: /workspace"
echo "  - Python: $(which python3)"
echo "  - Lua: $(which lua)"
echo ""

# Execute command or start shell
exec "$@"