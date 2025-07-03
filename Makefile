# Jimbot CI/CD Makefile
# Provides convenient commands for local development that mirror CI checks

.PHONY: help format lint test clean install-tools

# Default target
help:
	@echo "Available targets:"
	@echo "  make install-tools  - Install all CI tools locally"
	@echo "  make format        - Format all code (Python, Lua, C++)"
	@echo "  make lint          - Run all linters"
	@echo "  make test          - Run all tests"
	@echo "  make clean         - Clean temporary files"
	@echo "  make ci-local      - Run full CI pipeline locally"

# Install CI tools
install-tools:
	@echo "Installing CI tools..."
	# Python tools
	pip install -r requirements-dev.txt || pip install black isort flake8 mypy pylint bandit safety pytest pytest-cov
	# Lua tools
	@if command -v luarocks >/dev/null 2>&1; then \
		sudo luarocks install luacheck; \
		sudo luarocks install busted; \
	else \
		echo "Warning: LuaRocks not installed, skipping Lua tools"; \
	fi
	# Download StyLua
	@if [ ! -f /usr/local/bin/stylua ]; then \
		wget -q https://github.com/JohnnyMorganz/StyLua/releases/download/v0.20.0/stylua-linux-x86_64.zip && \
		unzip -q stylua-linux-x86_64.zip && \
		sudo mv stylua /usr/local/bin/ && \
		rm stylua-linux-x86_64.zip; \
	fi

# Format all code
format:
	@echo "Formatting code..."
	# Python
	@if command -v black >/dev/null 2>&1; then \
		black jimbot/ tests/ 2>/dev/null || true; \
		isort jimbot/ tests/ 2>/dev/null || true; \
	else \
		echo "Warning: Python formatters not installed"; \
	fi
	# Lua
	@if command -v stylua >/dev/null 2>&1; then \
		find . -name "*.lua" -type f -not -path "./node_modules/*" | xargs stylua 2>/dev/null || true; \
	else \
		echo "Warning: StyLua not installed"; \
	fi
	# C++
	@if command -v clang-format-15 >/dev/null 2>&1; then \
		find . \( -name "*.cpp" -o -name "*.h" \) -not -path "./node_modules/*" | xargs clang-format-15 -i 2>/dev/null || true; \
	else \
		echo "Warning: clang-format not installed"; \
	fi

# Run all linters
lint:
	@echo "Running linters..."
	# Python
	@if command -v flake8 >/dev/null 2>&1; then \
		flake8 jimbot/ tests/ --count --statistics || true; \
	fi
	@if command -v mypy >/dev/null 2>&1; then \
		mypy jimbot/ --ignore-missing-imports || true; \
	fi
	@if command -v pylint >/dev/null 2>&1; then \
		pylint jimbot/ --exit-zero || true; \
	fi
	# Lua
	@if command -v luacheck >/dev/null 2>&1; then \
		find . -name "*.lua" -type f -not -path "./node_modules/*" | xargs luacheck || true; \
	fi
	# Security
	@if command -v bandit >/dev/null 2>&1; then \
		bandit -r jimbot/ || true; \
	fi

# Run tests
test:
	@echo "Running tests..."
	# Python tests
	@if command -v pytest >/dev/null 2>&1; then \
		pytest tests/ -v --cov=jimbot --cov-report=term-missing || true; \
	else \
		echo "Warning: pytest not installed"; \
	fi
	# Lua tests
	@if command -v busted >/dev/null 2>&1; then \
		busted tests/ || true; \
	else \
		echo "Warning: busted not installed"; \
	fi

# Clean temporary files
clean:
	@echo "Cleaning temporary files..."
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name ".pytest_cache" -delete
	find . -type d -name ".mypy_cache" -delete
	rm -rf htmlcov/
	rm -f .coverage
	rm -f bandit-report.json
	rm -f stylua-linux-x86_64.zip

# Run full CI pipeline locally
ci-local: format lint test
	@echo "CI pipeline complete!"
	@echo "Run 'git diff' to see formatting changes"

# Check formatting without modifying files
format-check:
	@echo "Checking code format..."
	# Python
	@if command -v black >/dev/null 2>&1; then \
		black --check jimbot/ tests/ || exit 1; \
		isort --check-only jimbot/ tests/ || exit 1; \
	fi
	# Lua
	@if command -v stylua >/dev/null 2>&1; then \
		find . -name "*.lua" -type f | xargs stylua --check || exit 1; \
	fi