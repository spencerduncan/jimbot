# Rust Development Environment Setup Guide

## Table of Contents
- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Rust Toolchain Installation](#rust-toolchain-installation)
- [VS Code Configuration](#vs-code-configuration)
- [Debugging Setup](#debugging-setup)
- [Performance Profiling Tools](#performance-profiling-tools)
- [JimBot-Specific Setup](#jimbot-specific-setup)
- [Common Development Workflows](#common-development-workflows)
- [Testing Best Practices](#testing-best-practices)
- [Benchmarking Setup](#benchmarking-setup)
- [Troubleshooting](#troubleshooting)

## Overview

This guide provides comprehensive setup instructions for Rust development in the JimBot project. JimBot is migrating performance-critical components to Rust to achieve:

- 5-10x performance improvements for event processing
- Memory safety without garbage collection overhead
- Excellent async/concurrent programming capabilities
- Type safety across component boundaries

### Key JimBot Components Being Developed in Rust
- **Event Bus**: Central message router (10,000+ events/second target)
- **Analytics**: High-speed data ingestion and time-series storage
- **Resource Coordinator**: System resource management (<1ms response time)
- **MAGE Modules**: Graph algorithms for strategy detection

## Prerequisites

### System Requirements
- **Operating System**: Linux (primary), macOS, or Windows with WSL2
- **RAM**: 8GB minimum, 16GB recommended for large builds
- **Storage**: 10GB free space for Rust toolchain and dependencies
- **Network**: Stable internet connection for dependency downloads

### Required Tools
Before installing Rust, ensure you have:

#### Linux/WSL2
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install build-essential curl git pkg-config libssl-dev

# CentOS/RHEL/Fedora
sudo yum groupinstall "Development Tools"
sudo yum install curl git openssl-devel pkg-config
```

#### macOS
```bash
# Install Xcode Command Line Tools
xcode-select --install

# Install Homebrew (if not already installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install required packages
brew install git curl openssl pkg-config
```

#### Windows
- Install [Git for Windows](https://git-scm.com/download/win)
- Install [Windows Subsystem for Linux 2 (WSL2)](https://docs.microsoft.com/en-us/windows/wsl/install)
- Follow Linux instructions within WSL2

## Rust Toolchain Installation

### 1. Install rustup (Rust Toolchain Installer)

```bash
# Download and install rustup
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# Follow the prompts (choose option 1 for default installation)
# Restart your shell or run:
source ~/.cargo/env
```

### 2. Verify Installation

```bash
# Check Rust version
rustc --version
cargo --version
rustup --version

# Expected output (versions may vary):
# rustc 1.75.0 (82e1608df 2023-12-21)
# cargo 1.75.0 (1d8b05cdd 2023-11-20)
# rustup 1.26.0 (5af9b9484 2023-04-05)
```

### 3. Configure Rust for JimBot Development

```bash
# Install stable toolchain (default)
rustup toolchain install stable

# Install nightly for advanced features and benchmarking
rustup toolchain install nightly

# Set stable as default
rustup default stable

# Add useful components
rustup component add rustfmt clippy rust-analyzer

# Add nightly components for benchmarking
rustup +nightly component add rustfmt clippy
```

### 4. Configure Cargo for Performance

Create `~/.cargo/config.toml`:

```toml
[build]
# Use all available CPU cores for builds
jobs = 0

# Enable incremental compilation for faster rebuilds
incremental = true

[target.x86_64-unknown-linux-gnu]
# Use faster linker on Linux
linker = "clang"
rustflags = ["-C", "link-arg=-fuse-ld=lld"]

[target.x86_64-apple-darwin]
# Use faster linker on macOS
rustflags = ["-C", "link-arg=-fuse-ld=lld"]

[profile.dev]
# Faster compilation for development
debug = 1
incremental = true

[profile.release]
# Optimized for JimBot's performance requirements
opt-level = 3
lto = true
codegen-units = 1
panic = "abort"

[profile.bench]
# Optimized for accurate benchmarking
debug = true
```

## VS Code Configuration

### 1. Install Required Extensions

Install these VS Code extensions:

```bash
# Install VS Code extensions via command line
code --install-extension rust-lang.rust-analyzer
code --install-extension vadimcn.vscode-lldb
code --install-extension serayuzgur.crates
code --install-extension tamasfe.even-better-toml
code --install-extension ms-vscode.test-adapter-converter
```

### 2. VS Code Settings Configuration

The project includes optimized VS Code settings in `.vscode/settings.json` for Rust development.

## Debugging Setup

### 1. Install CodeLLDB

CodeLLDB is included in the VS Code setup above. For command-line debugging:

#### Linux
```bash
# Install LLDB
sudo apt install lldb  # Ubuntu/Debian
sudo yum install lldb  # CentOS/RHEL/Fedora
```

#### macOS
```bash
# LLDB comes with Xcode Command Line Tools
# Verify installation
lldb --version
```

### 2. Debug Configuration

Create `.vscode/launch.json` (if not exists):

```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "type": "lldb",
            "request": "launch",
            "name": "Debug Rust Binary",
            "cargo": {
                "args": ["build", "--bin=${workspaceFolderBasename}"],
                "filter": {
                    "name": "${workspaceFolderBasename}",
                    "kind": "bin"
                }
            },
            "args": [],
            "cwd": "${workspaceFolder}",
            "console": "integratedTerminal",
            "environment": [],
            "sourceLanguages": ["rust"]
        },
        {
            "type": "lldb",
            "request": "launch",
            "name": "Debug Rust Test",
            "cargo": {
                "args": ["test", "--no-run", "--bin=${workspaceFolderBasename}"],
                "filter": {
                    "name": "${workspaceFolderBasename}",
                    "kind": "bin"
                }
            },
            "args": [],
            "cwd": "${workspaceFolder}",
            "console": "integratedTerminal",
            "environment": [],
            "sourceLanguages": ["rust"]
        }
    ]
}
```

### 3. Debugging Commands

```bash
# Build with debug symbols
cargo build

# Run with debugger attached
cargo run

# Debug tests
cargo test -- --nocapture

# Use rust-gdb/rust-lldb for command-line debugging
rust-lldb target/debug/your-binary
```

## Performance Profiling Tools

JimBot's performance requirements demand excellent profiling capabilities.

### 1. Install perf (Linux)

```bash
# Ubuntu/Debian
sudo apt install linux-tools-common linux-tools-generic linux-tools-$(uname -r)

# CentOS/RHEL/Fedora
sudo yum install perf
```

### 2. Install Flamegraph Tools

```bash
# Install flamegraph crate
cargo install flamegraph

# Install inferno (alternative flamegraph tool)
cargo install inferno

# For macOS, install additional tools
brew install dtrace  # macOS only
```

### 3. Profiling Commands

```bash
# CPU profiling with flamegraph
cargo flamegraph --bin your-binary

# Memory profiling with valgrind (Linux)
cargo build --release
valgrind --tool=massif target/release/your-binary

# Benchmark profiling
cargo +nightly bench --bench your-benchmark

# Custom perf profiling
perf record --call-graph=dwarf cargo run --release
perf report
```

### 4. Additional Profiling Tools

```bash
# Install additional profiling tools
cargo install cargo-profdata  # PGO profiling
cargo install cargo-cache     # Cargo cache analysis
cargo install cargo-bloat     # Binary size analysis
cargo install cargo-audit     # Security audit
```

## JimBot-Specific Setup

### 1. Clone JimBot Repository

```bash
# Clone the repository
git clone https://github.com/spencerduncan/jimbot.git
cd jimbot

# Install pre-commit hooks
pip install pre-commit
pre-commit install
```

### 2. JimBot Workspace Structure

JimBot uses a Cargo workspace for all Rust components:

```toml
# Cargo.toml (workspace root)
[workspace]
members = [
    "event-bus",
    "analytics", 
    "resource-coordinator",
    "mage-modules",
    "shared"
]

[workspace.dependencies]
# JimBot-specific shared dependencies
tokio = { version = "1.35", features = ["full"] }
tonic = "0.10"
prost = "0.12"
serde = { version = "1.0", features = ["derive"] }
async-trait = "0.1"
anyhow = "1.0"
tracing = "0.1"
dashmap = "5.5"
pyo3 = { version = "0.20", features = ["auto-initialize"] }
```

### 3. Environment Variables

Create `.env` file in project root:

```bash
# JimBot Rust Configuration
RUST_LOG=info
RUST_BACKTRACE=1

# Performance settings
RUSTFLAGS="-C target-cpu=native"

# Development settings
CARGO_INCREMENTAL=1
```

### 4. Protocol Buffers Setup

```bash
# Install protobuf compiler
# Ubuntu/Debian
sudo apt install protobuf-compiler

# macOS
brew install protobuf

# CentOS/RHEL/Fedora
sudo yum install protobuf-compiler

# Add to Cargo.toml
[build-dependencies]
tonic-build = "0.10"
```

## Common Development Workflows

### 1. Daily Development

```bash
# Check code quality
make check

# Run tests
make test

# Run benchmarks
make bench

# Format code
make fmt

# Run linter
make clippy

# Build optimized release
make release
```

### 2. Component Development

```bash
# Create new JimBot component
cargo new --lib new-component
cd new-component

# Add to workspace Cargo.toml
# Add component-specific dependencies

# Implement component following JimBot patterns
# Add comprehensive tests
# Add benchmarks for performance validation
```

### 3. Integration Testing

```bash
# Test component integration
cargo test --workspace

# Test with Python interop
cargo test --features python-interop

# Performance regression testing
cargo bench --workspace
```

## Testing Best Practices

### 1. Test Structure

```rust
#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_basic_functionality() {
        // Arrange
        let input = create_test_input();
        
        // Act
        let result = function_under_test(input);
        
        // Assert
        assert_eq!(result, expected_output());
    }
    
    #[tokio::test]
    async fn test_async_functionality() {
        // Test async code
        let result = async_function().await;
        assert!(result.is_ok());
    }
}
```

### 2. Integration Tests

```rust
// tests/integration_test.rs
use jimbot_component::*;

#[test]
fn test_component_integration() {
    // Test component integration
}
```

### 3. Property-Based Testing

```rust
// Add to Cargo.toml
[dev-dependencies]
proptest = "1.0"

use proptest::prelude::*;

proptest! {
    #[test]
    fn test_property(input in any::<YourType>()) {
        let result = your_function(input);
        // Assert properties that should always hold
        prop_assert!(result.is_valid());
    }
}
```

### 4. Testing Commands

```bash
# Run all tests
cargo test

# Run specific test
cargo test test_name

# Run tests with output
cargo test -- --nocapture

# Run tests in parallel
cargo test -- --test-threads=4

# Generate test coverage
cargo install tarpaulin
cargo tarpaulin --out Html
```

## Benchmarking Setup

JimBot's performance requirements demand rigorous benchmarking.

### 1. Criterion.rs Setup

```toml
# Add to Cargo.toml
[dev-dependencies]
criterion = { version = "0.5", features = ["html_reports"] }

[[bench]]
name = "performance"
harness = false
```

### 2. Benchmark Implementation

```rust
// benches/performance.rs
use criterion::{black_box, criterion_group, criterion_main, Criterion};
use your_crate::*;

fn benchmark_function(c: &mut Criterion) {
    let input = create_benchmark_input();
    
    c.bench_function("function_name", |b| {
        b.iter(|| {
            function_under_test(black_box(&input))
        })
    });
}

criterion_group!(benches, benchmark_function);
criterion_main!(benches);
```

### 3. Benchmarking Commands

```bash
# Run benchmarks
cargo bench

# Run specific benchmark
cargo bench benchmark_name

# Generate flamegraph during benchmark
cargo flamegraph --bench performance

# Compare benchmark results
cargo bench -- --save-baseline before
# Make changes
cargo bench -- --baseline before
```

### 4. Continuous Benchmarking

```bash
# Install cargo-criterion for better output
cargo install cargo-criterion

# Run with detailed output
cargo criterion

# Generate reports
cargo criterion --message-format=json > benchmark_results.json
```

## Troubleshooting

### Common Issues and Solutions

#### 1. Compilation Errors

```bash
# Clear cargo cache
cargo clean

# Update dependencies
cargo update

# Check for conflicting dependencies
cargo tree --duplicates
```

#### 2. Linker Errors

```bash
# Install missing system dependencies
# Ubuntu/Debian
sudo apt install build-essential libc6-dev

# macOS
xcode-select --install

# Update linker configuration in ~/.cargo/config.toml
```

#### 3. Performance Issues

```bash
# Check build profile
cargo build --release --verbose

# Profile compilation time
cargo +nightly build -Z timings

# Check binary size
cargo bloat --release
```

#### 4. IDE Issues

```bash
# Restart rust-analyzer
# In VS Code: Ctrl+Shift+P -> "Rust Analyzer: Restart Server"

# Check rust-analyzer logs
# In VS Code: View -> Output -> Select "Rust Analyzer Language Server"

# Update rust-analyzer
rustup component add rust-analyzer
```

#### 5. Dependency Issues

```bash
# Check dependency versions
cargo tree

# Audit for security issues
cargo audit

# Check for outdated dependencies
cargo install cargo-outdated
cargo outdated
```

### Performance Optimization Tips

1. **Use `--release` builds for benchmarking**
2. **Enable link-time optimization (LTO) in release profiles**
3. **Use `target-cpu=native` optimization**
4. **Profile before optimizing**
5. **Minimize allocations in hot paths**
6. **Use `#[inline]` judiciously**
7. **Leverage zero-cost abstractions**

### Memory Management

1. **Use `Rc<RefCell<T>>` for shared mutable data**
2. **Use `Arc<Mutex<T>>` for thread-safe shared data**
3. **Prefer `&str` over `String` when possible**
4. **Use `Vec::with_capacity()` when size is known**
5. **Consider using `Box<T>` for large stack allocations**

### Async Best Practices

1. **Use `tokio` for async runtime**
2. **Avoid blocking in async functions**
3. **Use `tokio::spawn()` for concurrent tasks**
4. **Use channels for communication between tasks**
5. **Handle errors properly with `Result<T, E>`**

## Additional Resources

### Documentation
- [The Rust Programming Language Book](https://doc.rust-lang.org/book/)
- [Rust by Example](https://doc.rust-lang.org/rust-by-example/)
- [The Cargo Book](https://doc.rust-lang.org/cargo/)
- [The Rustonomicon](https://doc.rust-lang.org/nomicon/)

### JimBot-Specific Resources
- [JimBot Rust Migration Plan](../planning/rust_migration_plan.md)
- [JimBot Architecture Documentation](./README.md)
- [Performance Requirements](../planning/rust_migration_summary.md)

### Community Resources
- [Rust Users Forum](https://users.rust-lang.org/)
- [Rust Subreddit](https://www.reddit.com/r/rust/)
- [This Week in Rust](https://this-week-in-rust.org/)

---

**Next Steps**: After completing this setup, refer to the [JimBot Development Workflows](./DEVELOPMENT_TOOLS.md) for project-specific development patterns and the Makefile for common commands.