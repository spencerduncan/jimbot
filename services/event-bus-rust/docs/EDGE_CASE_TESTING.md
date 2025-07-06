# Event Bus Edge Case and Resilience Testing

This document describes the comprehensive edge case and resilience testing suite implemented for the Event Bus component.

## Overview

Following the successful Event Bus implementation, this testing suite ensures production resilience by thoroughly testing edge cases, error conditions, security boundaries, and performance under stress.

## Test Categories

### 1. Edge Case Tests (`edge_case_tests.rs`)

Tests the system's ability to handle malformed, invalid, or unexpected inputs gracefully.

#### Malformed JSON Events
- Invalid JSON syntax (unclosed braces, quotes, etc.)
- Type mismatches (numbers as strings, arrays as objects)
- Unicode and special characters
- Null bytes and control characters
- Extremely nested structures

#### Oversized Event Payloads
- 1MB, 10MB, and 100MB payloads
- Tests server's ability to reject or handle large inputs
- Verifies no memory exhaustion or crashes

#### Missing Required Fields
- Events without `type`, `source`, or `payload`
- Empty or null values in required fields
- Validates error responses are consistent and informative

#### Invalid Event Types
- Unknown event types
- SQL injection attempts in event types
- XSS payloads
- Path traversal attempts
- Unicode and special characters

#### Concurrent Connection Limits
- 100 simultaneous connections
- Tests connection pooling and resource management
- Validates fair handling across clients

#### Protocol Buffer Edge Cases
- Extreme numeric values (MAX/MIN integers, infinity, NaN)
- Very long strings
- Deeply nested structures
- Mixed type arrays
- Binary data encoding

### 2. Resilience Tests (`resilience_tests.rs`)

Tests system behavior under stress, failures, and resource exhaustion.

#### Sustained Load Resilience
- 60-second continuous load at 100 RPS
- Monitors success rate and response time degradation
- Validates no memory leaks or performance decay

#### Burst Traffic Patterns
- Multiple burst sizes: 50, 200, 1000, 2000 events
- Different intervals between bursts
- Tests system's ability to handle traffic spikes

#### Concurrent Client Connections
- 50 concurrent clients sending events
- Tests fair resource allocation
- Validates no client starvation

#### Memory Pressure Resilience
- Large payloads (1KB to 1MB per event)
- Tests memory management under pressure
- Validates graceful handling of memory constraints

#### Network Partition Simulation
- Very short timeouts to simulate network issues
- Tests recovery after network problems
- Validates system stability after connectivity issues

#### Graceful Degradation
- Progressive load increases
- Tests that performance degrades linearly, not exponentially
- Validates system maintains partial functionality under extreme load

#### Error Recovery Patterns
- Tests recovery after various error conditions
- Validates system returns to normal operation
- Tests health endpoint responsiveness after errors

#### Resource Exhaustion Recovery
- Deliberate resource pressure followed by recovery tests
- 10 concurrent tasks sending large batches
- Validates system recovery to normal operation

### 3. Security Tests (`security_tests.rs`)

Tests security boundaries and resistance to common attacks.

#### SQL Injection Attempts
- Common SQL injection payloads in all fields
- Validates proper input sanitization
- Ensures no database error exposure

#### XSS Injection Attempts
- Script tags, event handlers, and JavaScript URLs
- Tests input sanitization and output encoding
- Validates no script execution in responses

#### Command Injection Attempts
- Shell command injection payloads
- Tests that user input doesn't execute system commands
- Validates process isolation

#### Path Traversal Attempts
- Directory traversal sequences (`../`, `..\\`)
- URL-encoded variants
- Tests file system access protection

#### DoS Resistance
- 1000 rapid requests to test rate limiting
- Validates system remains responsive
- Tests that flood attacks don't crash the server

#### Resource Exhaustion Attacks
- Huge payloads to test memory exhaustion
- Deeply nested JSON to test CPU exhaustion
- Validates resource consumption limits

#### Input Validation Fuzzing
- Random byte sequences
- Invalid UTF-8 sequences
- Control characters
- Tests robustness against malformed input

#### Authentication Bypass Attempts
- Header manipulation attempts
- Tests that headers don't provide unauthorized access
- Validates security boundaries

#### Protocol Security
- Invalid HTTP methods on endpoints
- Tests that only allowed methods work
- Validates proper HTTP status codes

#### Information Disclosure
- Tests various endpoints for sensitive information
- Validates no passwords, secrets, or internal details exposed
- Tests error messages don't leak implementation details

### 4. Load Tests (`load_tests.rs`)

Tests performance characteristics under various load patterns.

#### Sustained Load Testing
- 5-minute continuous load (300 seconds for CI)
- Target: 50 RPS sustained
- Monitors success rate, response times, and degradation patterns

#### Burst Traffic Patterns
- High frequency small bursts (50 events × 20 bursts)
- Medium frequency medium bursts (200 events × 10 bursts)
- Low frequency large bursts (1000 events × 5 bursts)
- Very low frequency huge bursts (2000 events × 3 bursts)

#### Mixed Event Type Distributions
- Heartbeat heavy (70% heartbeat, 20% connection test, 10% money changed)
- Uniform distribution (25% each of 4 types)
- Game state heavy (60% game state, 30% round changed, 10% phase changed)
- Gameplay events (40% hand played, 30% cards discarded, 20% jokers changed, 10% round complete)

#### Client Connection Churn
- 20 concurrent clients with varying lifetimes (5-15 seconds)
- Tests connection establishment/teardown overhead
- Validates fair resource allocation during churn

#### Progressive Load Scaling
- Step-wise load increases: 10, 25, 50, 100, 200 RPS
- Identifies breaking points and performance characteristics
- Validates graceful degradation patterns

## Test Infrastructure

### Test Runner Script
`scripts/run_edge_case_tests.sh` provides:
- Server health checks before testing
- Organized test execution by category
- Detailed logging and progress reporting
- Test report generation
- Command-line options for selective testing

### Usage Examples

```bash
# Run all tests
./scripts/run_edge_case_tests.sh

# Run only security tests
./scripts/run_edge_case_tests.sh --category security

# Run with performance benchmarks
./scripts/run_edge_case_tests.sh --benchmarks

# Test against staging server
./scripts/run_edge_case_tests.sh --base-url http://staging:8080
```

### Environment Variables
- `BASE_URL`: Event Bus server URL (default: http://localhost:8080)
- `RUN_BENCHMARKS`: Set to 'true' for performance benchmarks

## Success Criteria

### Edge Case Tests
- ✅ No panics or crashes under any test scenario
- ✅ Graceful handling of all error conditions
- ✅ Clear error messages for invalid inputs
- ✅ Consistent error response format

### Resilience Tests
- ✅ >80% success rate under sustained load
- ✅ <10% performance degradation over time
- ✅ Linear degradation, not exponential
- ✅ Full recovery after error conditions

### Security Tests
- ✅ No SQL injection vulnerabilities
- ✅ No XSS vulnerabilities
- ✅ No command injection vulnerabilities
- ✅ No path traversal vulnerabilities
- ✅ DoS attacks don't crash the server
- ✅ No information disclosure

### Load Tests
- ✅ >95% success rate under normal load
- ✅ P95 response time <2 seconds
- ✅ Graceful degradation under extreme load
- ✅ Fair resource allocation across clients

## Integration with CI/CD

### Automated Testing
- Tests run in CI pipeline on every PR
- Staging environment testing before production deployment
- Nightly resilience testing with extended durations

### Monitoring Integration
- Test patterns inform production monitoring alerts
- Performance baselines established for capacity planning
- Security test cases inform WAF rules and monitoring

## Tools and Dependencies

### Testing Framework
- **Rust**: `cargo test` with `tokio::test` for async tests
- **HTTP Client**: `reqwest` for API testing
- **JSON**: `serde_json` for event construction
- **Concurrency**: `tokio` and `futures` for concurrent testing

### External Tools (Recommended)
- **Chaos Engineering**: Chaos Monkey for production failure injection
- **Load Testing**: Artillery or k6 for advanced load patterns
- **Fuzzing**: AFL or cargo-fuzz for deeper input fuzzing
- **Security Scanning**: OWASP ZAP for additional security testing

## Continuous Improvement

### Regular Updates
- New edge cases discovered in production added to test suite
- Performance baselines updated as system evolves
- Security tests updated with new attack vectors

### Metrics and Monitoring
- Test execution time tracking
- Success rate monitoring
- Performance regression detection
- Security posture assessment

## Troubleshooting

### Common Issues

#### Server Not Running
```
[ERROR] Event Bus server is not accessible at http://localhost:8080
[INFO] Please start the server with: cargo run
```
**Solution**: Start the Event Bus server before running tests.

#### Test Timeouts
```
Test timed out after 30 seconds
```
**Solution**: Check server performance, reduce load, or increase timeout values.

#### Connection Refused
```
Connection refused (os error 111)
```
**Solution**: Verify server is listening on correct port and accessible.

### Debug Mode
Run tests with debug logging:
```bash
RUST_LOG=debug cargo test --test edge_case_tests -- --nocapture
```

## Future Enhancements

### Planned Additions
- **Chaos Testing**: Automated failure injection during tests
- **Performance Profiling**: CPU and memory profiling during load tests
- **Network Simulation**: Bandwidth and latency variation testing
- **State Corruption**: Tests for data integrity under failures

### Advanced Scenarios
- **Multi-Region Testing**: Cross-region latency and failover
- **Version Compatibility**: Testing across different API versions
- **Integration Testing**: End-to-end testing with real game clients
- **Scalability Testing**: Horizontal scaling validation

## Contributing

### Adding New Tests
1. Identify edge case or failure scenario
2. Add test case to appropriate test file
3. Update documentation
4. Verify test fails appropriately before fix
5. Ensure test passes after implementation

### Test Guidelines
- Tests should be deterministic and repeatable
- Use appropriate timeouts for CI environments
- Log meaningful information for debugging
- Clean up resources properly
- Document expected behavior clearly

---

This comprehensive testing suite ensures the Event Bus is production-ready and can handle real-world edge cases, attacks, and stress conditions gracefully.