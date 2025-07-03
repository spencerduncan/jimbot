# Improved CI Pipeline

This directory contains an improved CI/CD pipeline designed to be resilient, informative, and developer-friendly.

## Key Features

### 1. **Health Checks**
- Pre-flight system health checks before running jobs
- Monitors disk space, memory, and network connectivity
- Prevents wasted compute on systems that will fail

### 2. **Graceful Degradation**
- Jobs continue even when non-critical tools are missing
- Partial results are better than no results
- Clear warnings about degraded functionality

### 3. **Retry Logic**
- Built-in retry mechanisms for network operations
- Exponential backoff to handle transient failures
- Fallback strategies for critical operations

### 4. **Better Error Messages**
- Clear indication of what failed and why
- Actionable error messages with fix suggestions
- Aggregated error reporting at the end

### 5. **Tool Version Management**
- Centralized version configuration in `.github/tool-versions.yml`
- Consistent tool versions across all jobs
- Easy updates in one place

### 6. **Monitoring and Metrics**
- Job timing metrics for performance tracking
- Success/failure rates for reliability monitoring
- Tool installation success tracking
- Comprehensive reports uploaded as artifacts

## Workflow Structure

### main-ci-improved.yml

The main workflow consists of several jobs:

1. **health-check**: System resource validation
2. **setup-tools**: Tool installation with retry logic
3. **format-check**: Code formatting validation
4. **lint**: Multi-language linting with parallel execution
5. **aggregate-results**: Final report generation
6. **notify**: Failure notifications (customizable)

### Key Design Decisions

#### Continue on Error
- Non-critical jobs use `continue-on-error: true`
- Prevents single failures from blocking entire pipeline
- Developers get maximum feedback from each run

#### Matrix Strategy for Linting
- Parallel execution for different languages
- `fail-fast: false` ensures all linters run
- Independent failure tracking per component

#### Artifact Upload
- All reports uploaded as artifacts
- 7-day retention for debugging
- 30-day retention for security reports

#### PR Comments
- Automated summary comments on pull requests
- Clear status indicators with emojis
- Warnings for degraded functionality

## Configuration Files

### .github/tool-versions.yml
Central configuration for all tool versions:
- Programming language versions
- Package versions with exact pins
- GitHub Actions versions
- Timeout and retry configuration
- Resource limits

### .github/workflows/scripts/retry.sh
Helper script providing:
- `retry_command()`: Retry with exponential backoff
- `retry_with_fallback()`: Primary and fallback strategies
- `check_network()`: Network connectivity validation
- `download_with_retry()`: Resilient file downloads
- `install_package()`: Package installation with retry

## Usage

### Running Locally
To test the CI pipeline locally:

```bash
# Install act (GitHub Actions local runner)
brew install act  # or your package manager

# Run the workflow
act -j format-check  # Run specific job
act                  # Run entire workflow
```

### Customizing for Your Needs

1. **Add New Tools**: Update `.github/tool-versions.yml`
2. **Add New Checks**: Add jobs following the existing pattern
3. **Change Notifications**: Modify the `notify` job
4. **Adjust Timeouts**: Update timeout values in tool-versions.yml

### Debugging Failures

1. Check the **health-check** job first
2. Look for warnings in orange/yellow
3. Download artifact reports for detailed analysis
4. Check retry attempts in logs

## Best Practices

1. **Version Pinning**: Always pin tool versions in tool-versions.yml
2. **Timeout Tuning**: Adjust timeouts based on actual run times
3. **Resource Monitoring**: Watch for resource exhaustion patterns
4. **Regular Updates**: Keep GitHub Actions versions current

## Migration from Existing CI

To migrate from an existing CI setup:

1. Copy `main-ci-improved.yml` to `.github/workflows/`
2. Copy `tool-versions.yml` to `.github/`
3. Copy the `scripts` directory to `.github/workflows/`
4. Update tool versions to match your requirements
5. Test with a draft PR first
6. Gradually migrate jobs from old workflow

## Troubleshooting

### Common Issues

**Network Failures**
- Check health-check network status
- Verify GitHub Actions service status
- Check for rate limiting

**Tool Installation Failures**
- Check tool-versions.yml for typos
- Verify package names and versions exist
- Check for dependency conflicts

**Timeout Issues**
- Increase timeouts in tool-versions.yml
- Check for resource contention
- Consider splitting large jobs

### Getting Help

1. Check artifact reports for detailed errors
2. Look for warnings in job logs
3. Review retry attempts for patterns
4. Check system health metrics

## Future Improvements

Potential enhancements to consider:
- Docker-based tool installation for better caching
- Self-hosted runners for more control
- Advanced caching strategies
- Integration with monitoring platforms
- Cost optimization through job scheduling