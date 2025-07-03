# CI System Dependencies Analysis

## Executive Summary

The current CI system installs tools on-demand in each workflow run, leading to reliability issues, increased build times, and potential version inconsistencies. This analysis examines all CI dependencies, their installation methods, failure points, and proposes solutions with trade-off analysis.

## 1. Complete Tool Inventory

### 1.1 Python Tools
| Tool | Version | Installation Method | Purpose | Failure Risk |
|------|---------|-------------------|---------|--------------|
| Python | 3.10 | setup-python@v5 | Runtime | Low - GitHub Action |
| black | Latest | pip install | Code formatting | Medium - PyPI availability |
| isort | Latest | pip install | Import sorting | Medium - PyPI availability |
| flake8 | Latest | pip install | Linting | Medium - PyPI availability |
| mypy | Latest | pip install | Type checking | Medium - PyPI availability |
| pylint | Latest | pip install | Linting | Medium - PyPI availability |
| bandit | Latest | pip install | Security analysis | Medium - PyPI availability |
| safety | Latest | pip install | Dependency scanning | Medium - PyPI availability |
| pytest | Latest | pip install | Testing | Medium - PyPI availability |
| pytest-cov | Latest | pip install | Coverage | Medium - PyPI availability |

### 1.2 Lua Tools
| Tool | Version | Installation Method | Purpose | Failure Risk |
|------|---------|-------------------|---------|--------------|
| Lua | 5.4 | apt-get | Runtime | Low - Ubuntu repos |
| LuaRocks | Latest | apt-get | Package manager | Low - Ubuntu repos |
| luacheck | Latest | luarocks install | Linting | High - LuaRocks server |
| StyLua | v0.20.0 | wget from GitHub | Formatting | High - GitHub releases, network |
| busted | Latest | luarocks install | Testing | High - LuaRocks server |
| luacov | Latest | luarocks install | Coverage | High - LuaRocks server |

### 1.3 C++ Tools
| Tool | Version | Installation Method | Purpose | Failure Risk |
|------|---------|-------------------|---------|--------------|
| clang-format-15 | 15 | apt-get | Formatting | Low - Ubuntu repos |
| clang-tidy-15 | 15 | apt-get | Linting | Low - Ubuntu repos |
| cppcheck | Latest | apt-get | Static analysis | Low - Ubuntu repos |
| cmake | 3.25 | Environment variable | Build system | N/A - not installed |

### 1.4 Protocol Buffers Tools
| Tool | Version | Installation Method | Purpose | Failure Risk |
|------|---------|-------------------|---------|--------------|
| protoc | 3.21.12 | Environment variable | Compiler | N/A - not installed |
| buf | Latest | go install | Linting/formatting | High - requires Go, network |

### 1.5 Container Tools
| Tool | Version | Installation Method | Purpose | Failure Risk |
|------|---------|-------------------|---------|--------------|
| Docker | Latest | Pre-installed | Container runtime | Low - GitHub runner |
| Docker Buildx | Latest | setup-buildx@v3 | Multi-arch builds | Low - GitHub Action |
| Trivy | Latest | aquasecurity/trivy-action | Security scanning | Low - GitHub Action |

### 1.6 Documentation Tools
| Tool | Version | Installation Method | Purpose | Failure Risk |
|------|---------|-------------------|---------|--------------|
| sphinx | Latest | pip install | Documentation | Medium - PyPI availability |
| sphinx-rtd-theme | Latest | pip install | Documentation theme | Medium - PyPI availability |
| myst-parser | Latest | pip install | Markdown support | Medium - PyPI availability |
| autodoc | Latest | pip install | API docs | Medium - PyPI availability |

## 2. Identified Problems

### 2.1 Network Reliability Issues
- **StyLua Download**: Uses wget with retry logic, indicating past failures
- **Go-based tools**: Require Go installation plus network access to download
- **LuaRocks packages**: Depend on LuaRocks server availability

### 2.2 Version Management
- Most tools use "latest" version, leading to potential inconsistencies
- Only specific versions: Python 3.10, Lua 5.4, clang tools (15), StyLua (v0.20.0)
- No lockfile mechanism for most package managers

### 2.3 Installation Time Overhead
- Each job reinstalls tools from scratch
- No sharing of installed tools between jobs
- Sequential installation increases critical path

### 2.4 Multiple Package Managers
- apt-get (system packages)
- pip (Python packages)
- luarocks (Lua packages)
- go install (Go packages)
- wget/curl (direct downloads)

### 2.5 Missing Tools
- CMake version specified in env but never installed
- protoc version specified in env but never installed
- Go not installed but required for buf

## 3. Root Cause Analysis

### 3.1 Systemic Issues
1. **No standardized environment**: Each job builds its environment from scratch
2. **Dependency on external services**: PyPI, LuaRocks, GitHub releases, apt repositories
3. **Lack of version pinning**: Most tools float to latest versions
4. **No centralized tool management**: Each workflow manages its own dependencies
5. **Missing abstraction layer**: Direct installation commands in workflow files

### 3.2 Failure Patterns
- Network timeouts during downloads
- Package repository unavailability
- Version conflicts between tools
- Missing system dependencies for compilation
- Race conditions in parallel jobs

## 4. Solution Analysis

### Solution 1: Pre-built Docker Image

**Implementation**:
```dockerfile
FROM ubuntu:22.04
# Install all CI tools with specific versions
# Push to registry: jimbot/ci-tools:v1.0.0
```

**Pros**:
- Consistent environment across all jobs
- Fast startup (pull vs install)
- Version control for entire toolchain
- Can be tested independently
- Supports local development

**Cons**:
- Requires maintenance of Docker image
- Storage costs for image registry
- Initial download time for large images
- Need to rebuild for tool updates

**Time Impact**:
- Current: ~5-10 minutes per job for installation
- Docker: ~1-2 minutes for image pull

### Solution 2: GitHub Actions Tool Cache

**Implementation**:
```yaml
- name: Cache tools
  uses: actions/cache@v4
  with:
    path: |
      ~/.local/bin
      ~/.luarocks
      ~/go/bin
    key: ${{ runner.os }}-tools-${{ hashFiles('**/tool-versions.txt') }}
```

**Pros**:
- Native GitHub Actions integration
- Automatic cache invalidation
- No external dependencies
- Incremental updates possible

**Cons**:
- Cache can be evicted
- Still need installation logic
- Cache restore time overhead
- 10GB cache size limit

**Time Impact**:
- First run: Same as current
- Cached runs: ~30-60 seconds for restore

### Solution 3: Language-Specific Setup Actions

**Implementation**:
```yaml
- uses: actions/setup-python@v5
- uses: leafo/gh-actions-lua@v10
- uses: actions/setup-go@v5
```

**Pros**:
- Maintained by community
- Optimized for CI environments
- Handle version management
- Good caching built-in

**Cons**:
- Dependency on third-party actions
- Not available for all tools
- Inconsistent interfaces
- Limited customization

**Time Impact**:
- ~30 seconds per language setup

### Solution 4: Hybrid Approach (Recommended)

**Implementation**:
1. Use language-specific setup actions where available
2. Create custom Docker image for remaining tools
3. Use GitHub Actions cache for user packages
4. Version pin everything in a central file

```yaml
# .github/tool-versions.yml
python: "3.10"
lua: "5.4"
stylua: "v0.20.0"
buf: "v1.28.1"
# ... etc
```

**Pros**:
- Best of all approaches
- Gradual migration possible
- Fallback mechanisms
- Maximum reliability

**Cons**:
- More complex setup
- Multiple maintenance points
- Requires documentation

## 5. Recommended Implementation Plan

### Phase 1: Immediate Stabilization (1-2 days)
1. Add version pinning for all tools
2. Implement retry logic for all downloads
3. Add fallback mirrors for critical tools
4. Create tool-versions.yml file

### Phase 2: Docker Image Creation (3-5 days)
1. Create Dockerfile.ci based on Dockerfile.dev
2. Build and test CI-specific image
3. Publish to GitHub Container Registry
4. Update one workflow as proof of concept

### Phase 3: Workflow Migration (1 week)
1. Migrate format-check job to Docker
2. Migrate lint jobs to hybrid approach
3. Update remaining jobs incrementally
4. Add performance metrics

### Phase 4: Optimization (Ongoing)
1. Implement caching strategies
2. Parallelize tool installation
3. Create toolchain update automation
4. Monitor and optimize image size

## 6. Trade-off Summary

| Approach | Speed | Reliability | Maintenance | Flexibility | Cost |
|----------|--------|------------|-------------|-------------|------|
| Current | Slow | Low | Low | High | Low |
| Docker | Fast | High | Medium | Medium | Medium |
| Cache | Medium | Medium | Low | High | Low |
| Setup Actions | Fast | High | Low | Low | Low |
| Hybrid | Fast | High | Medium | High | Medium |

## 7. Metrics for Success

1. **Build Time Reduction**: Target 50% reduction in setup time
2. **Failure Rate**: Reduce tool installation failures to <1%
3. **Version Consistency**: 100% deterministic builds
4. **Developer Experience**: Local/CI parity

## 8. Risk Mitigation

1. **Docker Registry Outage**: Keep fallback to direct installation
2. **Large Image Size**: Use multi-stage builds, separate images by language
3. **Version Conflicts**: Comprehensive testing before updates
4. **Migration Risks**: Gradual rollout with feature flags

## Conclusion

The current approach of installing tools on-demand is unsustainable. The hybrid approach offers the best balance of speed, reliability, and maintainability. By combining Docker images for complex tools with GitHub Actions for language runtimes and caching for package installations, we can achieve a robust CI system that scales with the project's needs.