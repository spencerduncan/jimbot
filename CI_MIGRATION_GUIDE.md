# CI Dependencies Migration Guide

This guide provides step-by-step instructions for migrating from the current tool installation approach to the hybrid solution.

## Migration Overview

The hybrid approach combines:
1. **Docker images** for complex tool environments
2. **GitHub Actions** for language runtimes
3. **Caching** for package installations
4. **Version pinning** for consistency

## Phase 1: Preparation (Day 1)

### 1.1 Create Version Configuration
```bash
# Already created: .github/tool-versions.yml
# Review and adjust versions as needed
```

### 1.2 Build CI Docker Image
```bash
# Build locally first
./scripts/build-ci-image.sh

# Test the image
docker run --rm -v $PWD:/workspace jimbot/ci-tools:latest black --version
```

### 1.3 Set Up GitHub Container Registry
```yaml
# Add to repository settings:
# Settings → Actions → General → Workflow permissions
# - Read and write permissions
# - Allow GitHub Actions to create and approve pull requests
```

## Phase 2: Gradual Migration (Days 2-5)

### 2.1 Migrate Format Checking (Low Risk)
```yaml
# Update format-check job in .github/workflows/main-ci.yml
# Replace tool installation with container usage
# See main-ci-hybrid.yml for example
```

### 2.2 Test in Feature Branch
```bash
# Create test branch
git checkout -b ci/hybrid-migration

# Update workflow file
cp .github/workflows/main-ci-hybrid.yml .github/workflows/main-ci.yml

# Push and monitor
git push origin ci/hybrid-migration
```

### 2.3 Performance Monitoring
Track metrics before and after:
- Total workflow time
- Tool installation time
- Failure rate
- Cache hit rate

## Phase 3: Full Rollout (Week 2)

### 3.1 Update All Workflows
Priority order:
1. `format-check` - Uses Docker (lowest risk)
2. `lint` - Hybrid approach
3. `test-unit` - Keep existing, add caching
4. `build-docker` - No changes needed
5. `test-integration` - Gradual migration

### 3.2 Create Automation
```yaml
# .github/workflows/ci-image-update.yml
name: Update CI Image
on:
  push:
    paths:
      - '.github/tool-versions.yml'
      - 'jimbot/deployment/docker/ci/Dockerfile.ci'
  schedule:
    - cron: '0 0 * * 0' # Weekly
```

### 3.3 Documentation Update
- Update CONTRIBUTING.md with new CI process
- Add troubleshooting guide
- Document local development with CI image

## Phase 4: Optimization (Ongoing)

### 4.1 Image Size Reduction
```dockerfile
# Use multi-stage builds
FROM base AS python-tools
# Install Python tools

FROM base AS lua-tools
# Install Lua tools

FROM base AS final
COPY --from=python-tools /usr/local /usr/local
COPY --from=lua-tools /usr/local /usr/local
```

### 4.2 Parallel Job Execution
```yaml
# Use job matrix for parallel execution
strategy:
  matrix:
    component: [python, lua, cpp]
```

### 4.3 Smart Caching
```yaml
# Cache based on lock files
- uses: actions/cache@v4
  with:
    path: ~/.cache/pip
    key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements*.txt', '.github/tool-versions.yml') }}
```

## Migration Checklist

### Pre-Migration
- [ ] Review current tool versions
- [ ] Test CI image locally
- [ ] Set up container registry access
- [ ] Create rollback plan

### During Migration
- [ ] Monitor CI performance metrics
- [ ] Check for new failure patterns
- [ ] Validate tool compatibility
- [ ] Update documentation

### Post-Migration
- [ ] Remove old installation scripts
- [ ] Update developer onboarding
- [ ] Schedule regular image updates
- [ ] Create success metrics dashboard

## Rollback Plan

If issues occur:

1. **Immediate Rollback**
   ```bash
   git revert <migration-commit>
   git push origin main
   ```

2. **Partial Rollback**
   - Keep Docker for formatting
   - Revert to direct installation for problematic tools

3. **Debug Mode**
   ```yaml
   # Add debug output
   - name: Debug environment
     run: |
       echo "Available tools:"
       which python lua go cmake
       echo "Versions:"
       python --version
       lua -v
   ```

## Common Issues and Solutions

### Issue: Docker pull timeout
**Solution**: Use fallback to direct installation
```yaml
- name: Pull CI image with fallback
  run: |
    if ! docker pull ${{ env.CI_IMAGE }}; then
      echo "Falling back to direct installation"
      bash scripts/install-ci-tools.sh
    fi
```

### Issue: Cache corruption
**Solution**: Bust cache with new key
```yaml
cache-key: ${{ runner.os }}-tools-v2-${{ hashFiles('.github/tool-versions.yml') }}
```

### Issue: Tool version mismatch
**Solution**: Validate versions in workflow
```yaml
- name: Validate tool versions
  run: |
    docker run --rm ${{ env.CI_IMAGE }} \
      python -c "import black; assert black.__version__ == '23.12.1'"
```

## Success Metrics

Track these KPIs:

1. **Build Time Reduction**
   - Target: 50% reduction in setup time
   - Measure: Average workflow duration

2. **Reliability Improvement**
   - Target: <1% tool installation failures
   - Measure: Workflow failure rate

3. **Developer Satisfaction**
   - Target: Faster feedback loops
   - Measure: PR-to-merge time

4. **Cost Efficiency**
   - Target: Reduced GitHub Actions minutes
   - Measure: Monthly usage reports

## Support

For issues or questions:
1. Check CI logs for detailed errors
2. Run `./scripts/build-ci-image.sh` locally to reproduce
3. Open issue with `ci-infrastructure` label
4. Tag @platform-team for urgent issues