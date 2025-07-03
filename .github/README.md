# CI/CD Documentation

This directory contains the Continuous Integration and Continuous Deployment
(CI/CD) configuration for the Jimbot project, including comprehensive support
for Rust components.

## Overview

The CI/CD pipeline is designed to:

- Automatically build, test, and deploy Rust components
- Ensure code quality through formatting, linting, and security checks
- Provide multi-platform Docker builds
- Implement semantic versioning and automated releases
- Monitor dependencies for security vulnerabilities

## Workflows

### 1. Rust CI/CD Pipeline (`rust-ci-cd.yml`)

**Triggers:**

- Push to `main` or `develop` branches with Rust changes
- Pull requests with Rust changes
- Manual workflow dispatch

**Features:**

- **Component Detection**: Automatically detects all Rust components in the
  repository
- **Quality Checks**: Runs `cargo fmt`, `cargo clippy`, and tests on both stable
  and nightly Rust
- **Code Coverage**: Uses `cargo-tarpaulin` to generate coverage reports and
  uploads to Codecov
- **Security Audit**: Runs `cargo-audit` to detect known security
  vulnerabilities
- **Multi-Platform Docker**: Builds Docker images for `linux/amd64` and
  `linux/arm64`
- **Semantic Versioning**: Automatically determines version bumps based on
  commit messages
- **Release Automation**: Creates GitHub releases with proper versioning

**Jobs:**

1. `detect-changes`: Finds all Rust components and determines if there are
   changes
2. `rust-quality-checks`: Runs formatting, linting, building, and testing
3. `rust-coverage`: Generates code coverage reports
4. `security-audit`: Checks for security vulnerabilities
5. `docker-build`: Builds multi-platform Docker images
6. `semantic-release`: Creates automated releases for main branch
7. `manual-release`: Allows manual release creation
8. `notification`: Provides workflow summary

### 2. Rust Security Audit (`rust-security.yml`)

**Triggers:**

- Daily at 2 AM UTC (scheduled)
- Push to `main` with dependency changes
- Pull requests with dependency changes
- Manual workflow dispatch

**Features:**

- **Security Audit**: Daily vulnerability scanning with `cargo-audit`
- **License Compliance**: Checks for problematic licenses using `cargo-license`
- **Supply Chain Security**: Uses `cargo-deny` and `cargo-geiger` for supply
  chain analysis
- **Automated Alerting**: Creates GitHub issues when vulnerabilities are found

### 3. Dependabot Configuration (`dependabot.yml`)

**Features:**

- **Rust Dependencies**: Weekly updates for Cargo dependencies
- **Grouped Updates**: Groups related dependencies (e.g., serde*, tokio*)
- **Security Focus**: Prioritizes security updates over major version bumps
- **Multi-Component**: Supports Rust components in different directories

## Setup Instructions

### For New Rust Components

1. **Create Your Rust Project Structure:**

   ```bash
   mkdir -p services/your-component
   cd services/your-component
   cargo init --name your-component
   ```

2. **Add a Dockerfile (Optional):**
   - Copy the `Dockerfile.rust-template` to your component directory
   - Customize it for your specific needs
   - Update the binary name and exposed ports

3. **Configure Component-Specific Settings:**

   ```toml
   # In your Cargo.toml
   [package]
   name = "your-component"
   version = "0.1.0"
   edition = "2021"
   authors = ["spencerduncan"]
   license = "MIT"
   description = "Your component description"
   repository = "https://github.com/spencerduncan/jimbot-main"
   ```

4. **Add Security Configuration (Optional):**

   ```toml
   # Create deny.toml for supply chain security
   [licenses]
   allow = ["MIT", "Apache-2.0", "BSD-3-Clause"]
   deny = ["GPL-2.0", "GPL-3.0"]

   [advisories]
   vulnerability = "deny"
   unmaintained = "warn"
   ```

### Environment Variables and Secrets

The following secrets should be configured in your GitHub repository:

- `CODECOV_TOKEN`: For uploading code coverage reports
- `GITHUB_TOKEN`: Automatically provided by GitHub Actions

### Docker Registry Configuration

By default, the pipeline uses GitHub Container Registry (ghcr.io). Images are
tagged as:

- `ghcr.io/your-org/your-repo/rust-component-name:latest`
- `ghcr.io/your-org/your-repo/rust-component-name:sha-abc123`
- `ghcr.io/your-org/your-repo/rust-component-name:v1.0.0`

## Usage

### Running CI/CD Locally

To test your changes locally before pushing:

```bash
# Format code
cargo fmt --all

# Run clippy
cargo clippy --all-targets --all-features -- -D warnings

# Run tests
cargo test --all-features

# Check for security vulnerabilities
cargo audit

# Generate coverage report
cargo tarpaulin --all-features --workspace --out Html
```

### Manual Releases

You can trigger manual releases through the GitHub Actions interface:

1. Go to Actions → Rust CI/CD Pipeline
2. Click "Run workflow"
3. Select the release type: patch, minor, or major
4. Click "Run workflow"

### Semantic Versioning

The pipeline automatically determines version bumps based on commit messages:

- **Patch**: Bug fixes (default)
- **Minor**: New features (`feat:` prefix)
- **Major**: Breaking changes (`feat!:` or `BREAKING CHANGE:` in commit body)

### Security Monitoring

The security workflow runs daily and will:

1. Check for new vulnerabilities in dependencies
2. Verify license compliance
3. Analyze supply chain security
4. Create GitHub issues for any problems found

## Troubleshooting

### Common Issues

1. **"No Rust components found"**
   - Ensure you have `Cargo.toml` files in your component directories
   - Check that paths don't include `target/` directories

2. **Docker build failures**
   - Verify your Dockerfile exists and is correctly configured
   - Check that your Dockerfile uses the correct binary name

3. **Coverage reports not uploading**
   - Ensure `CODECOV_TOKEN` is configured in repository secrets
   - Check that tests are actually running

4. **Release failures**
   - Verify that your `Cargo.toml` has correct metadata
   - Ensure the working directory is clean

### Getting Help

1. Check the workflow logs in GitHub Actions
2. Review the job summaries for detailed information
3. Look at the artifact uploads for detailed reports
4. Check the security issues created by automated scans

## Best Practices

### Code Quality

- Always run `cargo fmt` before committing
- Address all `cargo clippy` warnings
- Maintain good test coverage (aim for >80%)
- Write meaningful commit messages for proper semantic versioning

### Security

- Regularly update dependencies
- Review security advisories for your dependencies
- Use `cargo audit` in your local development workflow
- Be cautious with unsafe code blocks

### Docker

- Use multi-stage builds to minimize image size
- Run containers as non-root users
- Include health checks in your containers
- Use specific version tags rather than `latest`

### Documentation

- Update this README when adding new components
- Document any special configuration requirements
- Include examples of how to use your components

## Future Enhancements

Planned improvements to the CI/CD pipeline:

- [ ] Integration with external security scanning tools
- [ ] Performance benchmarking automation
- [ ] Cross-compilation for additional platforms
- [ ] Integration testing between Rust and Python components
- [ ] Automatic documentation generation and publishing
