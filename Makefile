# JimBot Rust Development Makefile
# 
# This Makefile provides common commands for Rust development in the JimBot project.
# JimBot is migrating performance-critical components to Rust for 5-10x performance improvements.

# Variables
CARGO := cargo
CARGO_NIGHTLY := cargo +nightly
RUST_LOG ?= info
RUST_BACKTRACE ?= 1

# Export environment variables
export RUST_LOG
export RUST_BACKTRACE

# Default target
.PHONY: help
help: ## Show this help message
	@echo "JimBot Rust Development Commands"
	@echo "================================"
	@echo ""
	@echo "Development Commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-20s %s\n", $$1, $$2}'

# Development Commands
.PHONY: setup
setup: ## Initial setup for Rust development environment
	@echo "Setting up Rust development environment for JimBot..."
	rustup toolchain install stable nightly
	rustup default stable
	rustup component add rustfmt clippy rust-analyzer
	$(CARGO_NIGHTLY) install cargo-flamegraph cargo-audit cargo-bloat cargo-outdated tarpaulin
	@echo "✅ Rust development environment setup complete!"

.PHONY: check
check: ## Run comprehensive code quality checks
	@echo "Running code quality checks..."
	$(CARGO) fmt --all -- --check
	$(CARGO) clippy --workspace --all-targets --all-features -- -D warnings -W clippy::perf -W clippy::nursery
	$(CARGO) check --workspace --all-targets --all-features
	@echo "✅ Code quality checks passed!"

.PHONY: fmt
fmt: ## Format all Rust code
	@echo "Formatting Rust code..."
	$(CARGO) fmt --all
	@echo "✅ Code formatting complete!"

.PHONY: clippy
clippy: ## Run Clippy linter with JimBot-specific performance rules
	@echo "Running Clippy with performance optimizations..."
	$(CARGO) clippy --workspace --all-targets --all-features -- \
		-W clippy::perf \
		-W clippy::nursery \
		-W clippy::pedantic \
		-A clippy::module_name_repetitions \
		-A clippy::missing_errors_doc \
		-A clippy::missing_panics_doc
	@echo "✅ Clippy analysis complete!"

# Build Commands
.PHONY: build
build: ## Build all workspace crates in debug mode
	@echo "Building JimBot Rust components (debug)..."
	$(CARGO) build --workspace --all-features
	@echo "✅ Debug build complete!"

.PHONY: build-release
build-release: ## Build all workspace crates in release mode (optimized)
	@echo "Building JimBot Rust components (release)..."
	$(CARGO) build --workspace --all-features --release
	@echo "✅ Release build complete!"

.PHONY: build-event-bus
build-event-bus: ## Build Event Bus component (10,000+ events/second target)
	@echo "Building Event Bus component..."
	$(CARGO) build --package event-bus --all-features --release
	@echo "✅ Event Bus build complete!"

.PHONY: build-analytics
build-analytics: ## Build Analytics component (high-speed data ingestion)
	@echo "Building Analytics component..."
	$(CARGO) build --package analytics --all-features --release
	@echo "✅ Analytics build complete!"

.PHONY: build-resource-coordinator
build-resource-coordinator: ## Build Resource Coordinator (<1ms response time target)
	@echo "Building Resource Coordinator..."
	$(CARGO) build --package resource-coordinator --all-features --release
	@echo "✅ Resource Coordinator build complete!"

.PHONY: build-mage-modules
build-mage-modules: ## Build MAGE Modules (graph algorithms)
	@echo "Building MAGE Modules..."
	$(CARGO) build --package mage-modules --all-features --release
	@echo "✅ MAGE Modules build complete!"

# Testing Commands
.PHONY: test
test: ## Run all tests across the workspace
	@echo "Running JimBot Rust tests..."
	$(CARGO) test --workspace --all-features
	@echo "✅ All tests passed!"

.PHONY: test-unit
test-unit: ## Run unit tests only
	@echo "Running unit tests..."
	$(CARGO) test --workspace --lib --all-features
	@echo "✅ Unit tests passed!"

.PHONY: test-integration
test-integration: ## Run integration tests only
	@echo "Running integration tests..."
	$(CARGO) test --workspace --test '*' --all-features
	@echo "✅ Integration tests passed!"

.PHONY: test-coverage
test-coverage: ## Generate test coverage report (requires tarpaulin)
	@echo "Generating test coverage report..."
	$(CARGO) tarpaulin --workspace --all-features --out Html --output-dir target/coverage
	@echo "✅ Coverage report generated in target/coverage/"

.PHONY: test-event-bus
test-event-bus: ## Test Event Bus component performance
	@echo "Testing Event Bus component..."
	$(CARGO) test --package event-bus --all-features -- --nocapture
	@echo "✅ Event Bus tests complete!"

.PHONY: test-analytics
test-analytics: ## Test Analytics component performance
	@echo "Testing Analytics component..."
	$(CARGO) test --package analytics --all-features -- --nocapture
	@echo "✅ Analytics tests complete!"

# Benchmarking Commands
.PHONY: bench
bench: ## Run all benchmarks across the workspace
	@echo "Running JimBot performance benchmarks..."
	$(CARGO) bench --workspace --all-features
	@echo "✅ Benchmarks complete! Results in target/criterion/"

.PHONY: bench-event-bus
bench-event-bus: ## Benchmark Event Bus (target: 10,000+ events/second)
	@echo "Benchmarking Event Bus performance..."
	$(CARGO) bench --package event-bus --all-features
	@echo "✅ Event Bus benchmarks complete!"

.PHONY: bench-analytics
bench-analytics: ## Benchmark Analytics component (data ingestion speed)
	@echo "Benchmarking Analytics performance..."
	$(CARGO) bench --package analytics --all-features
	@echo "✅ Analytics benchmarks complete!"

.PHONY: bench-resource-coordinator
bench-resource-coordinator: ## Benchmark Resource Coordinator (target: <1ms response)
	@echo "Benchmarking Resource Coordinator..."
	$(CARGO) bench --package resource-coordinator --all-features
	@echo "✅ Resource Coordinator benchmarks complete!"

.PHONY: bench-mage
bench-mage: ## Benchmark MAGE algorithms (graph processing speed)
	@echo "Benchmarking MAGE algorithms..."
	$(CARGO) bench --package mage-modules --all-features
	@echo "✅ MAGE benchmarks complete!"

.PHONY: bench-compare
bench-compare: ## Compare benchmark results with baseline
	@echo "Comparing benchmarks with baseline..."
	$(CARGO) bench --workspace --all-features -- --save-baseline current
	@echo "✅ Baseline comparison complete!"

# Profiling Commands  
.PHONY: profile-flamegraph
profile-flamegraph: ## Generate flamegraph for performance profiling
	@echo "Generating flamegraph profile..."
	$(CARGO) flamegraph --bin event-bus --release
	@echo "✅ Flamegraph generated: flamegraph.svg"

.PHONY: profile-event-bus
profile-event-bus: ## Profile Event Bus component performance
	@echo "Profiling Event Bus performance..."
	$(CARGO) flamegraph --package event-bus --bin event-bus --release
	@echo "✅ Event Bus profiling complete!"

.PHONY: profile-analytics
profile-analytics: ## Profile Analytics component performance
	@echo "Profiling Analytics performance..."
	$(CARGO) flamegraph --package analytics --bin analytics --release  
	@echo "✅ Analytics profiling complete!"

# Maintenance Commands
.PHONY: clean
clean: ## Clean all build artifacts
	@echo "Cleaning build artifacts..."
	$(CARGO) clean
	rm -f flamegraph.svg
	rm -rf target/coverage/
	@echo "✅ Clean complete!"

.PHONY: update
update: ## Update all dependencies
	@echo "Updating Rust dependencies..."
	$(CARGO) update
	@echo "✅ Dependencies updated!"

.PHONY: audit
audit: ## Security audit of dependencies
	@echo "Running security audit..."
	$(CARGO) audit
	@echo "✅ Security audit complete!"

.PHONY: outdated
outdated: ## Check for outdated dependencies (requires cargo-outdated)
	@echo "Checking for outdated dependencies..."
	$(CARGO) outdated --workspace
	@echo "✅ Outdated dependency check complete!"

.PHONY: bloat
bloat: ## Analyze binary size (requires cargo-bloat)
	@echo "Analyzing binary size..."
	$(CARGO) bloat --release --crates
	@echo "✅ Binary analysis complete!"

# Documentation Commands
.PHONY: doc
doc: ## Generate documentation for all crates
	@echo "Generating documentation..."
	$(CARGO) doc --workspace --all-features --no-deps
	@echo "✅ Documentation generated in target/doc/"

.PHONY: doc-open
doc-open: ## Generate and open documentation in browser
	@echo "Generating and opening documentation..."
	$(CARGO) doc --workspace --all-features --no-deps --open
	@echo "✅ Documentation opened in browser!"

# Development Workflow Commands
.PHONY: dev
dev: fmt clippy test ## Complete development workflow (format, lint, test)
	@echo "✅ Development workflow complete!"

.PHONY: ci
ci: check test bench ## Full CI pipeline (check, test, benchmark)
	@echo "✅ CI pipeline complete!"

.PHONY: release-prep
release-prep: clean fmt clippy test bench build-release audit ## Prepare for release
	@echo "✅ Release preparation complete!"

# JimBot-Specific Performance Testing
.PHONY: perf-test
perf-test: ## Run comprehensive performance tests for JimBot requirements
	@echo "Running JimBot performance tests..."
	@echo "Testing Event Bus (target: 10,000+ events/second)..."
	$(CARGO) bench --package event-bus --bench throughput
	@echo "Testing Analytics (target: <10ms ingestion)..."
	$(CARGO) bench --package analytics --bench ingestion
	@echo "Testing Resource Coordinator (target: <1ms response)..."
	$(CARGO) bench --package resource-coordinator --bench response_time
	@echo "✅ Performance tests complete!"

.PHONY: python-interop-test
python-interop-test: ## Test Rust-Python interoperability (PyO3)
	@echo "Testing Rust-Python interoperability..."
	$(CARGO) test --workspace --features python-interop
	@echo "✅ Python interop tests complete!"

# Protocol Buffer Commands
.PHONY: proto-build
proto-build: ## Build Protocol Buffer definitions
	@echo "Building Protocol Buffer definitions..."
	$(CARGO) build --package shared --features proto
	@echo "✅ Protocol Buffer build complete!"

.PHONY: proto-check
proto-check: ## Validate Protocol Buffer definitions
	@echo "Validating Protocol Buffer definitions..."
	find . -name "*.proto" -exec protoc --lint_out=. {} \;
	@echo "✅ Protocol Buffer validation complete!"

# Container Support
.PHONY: docker-build
docker-build: ## Build Docker image for JimBot Rust components
	@echo "Building Docker image..."
	docker build -t jimbot-rust:latest -f Dockerfile.dev .
	@echo "✅ Docker image built!"

# Environment Setup
.PHONY: env-check
env-check: ## Check development environment setup
	@echo "Checking JimBot Rust development environment..."
	@echo "Rust version:"
	@rustc --version
	@echo "Cargo version:"
	@cargo --version
	@echo "Available toolchains:"
	@rustup toolchain list
	@echo "Installed components:"
	@rustup component list --installed
	@echo "Environment variables:"
	@echo "RUST_LOG=${RUST_LOG}"
	@echo "RUST_BACKTRACE=${RUST_BACKTRACE}"
	@echo "✅ Environment check complete!"

# Quick Commands
.PHONY: quick-check
quick-check: fmt clippy ## Quick code quality check (format + lint)
	@echo "✅ Quick check complete!"

.PHONY: quick-test
quick-test: test-unit ## Quick test run (unit tests only)
	@echo "✅ Quick tests complete!"

.PHONY: all
all: dev bench doc ## Build everything (development + benchmarks + docs)
	@echo "✅ Full build complete!"