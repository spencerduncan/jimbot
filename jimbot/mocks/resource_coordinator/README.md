# Mock Resource Coordinator

A lightweight mock implementation of the Resource Coordinator service for JimBot
development and testing.

## Overview

This mock Resource Coordinator provides:

- gRPC service implementation matching the production interface
- Always-grant mode for development (configurable)
- Request tracking and history
- Web UI for monitoring
- Python client library
- Docker support

## Quick Start

### Running with Docker Compose

```bash
cd jimbot/mocks/resource_coordinator
docker-compose up -d
```

This starts:

- Resource Coordinator on port 50051
- Web UI on http://localhost:8080

### Running Locally

1. Generate Python code from proto files:

```bash
cd /home/spduncan/jimbot
python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. jimbot/proto/resource_coordinator.proto
```

2. Start the server:

```bash
python -m jimbot.mocks.resource_coordinator.server --port 50051 --mode always_grant
```

3. Start the web UI (optional):

```bash
python -m jimbot.mocks.resource_coordinator.web_ui --port 8080
```

## Response Modes

The mock supports three response modes:

### 1. Always Grant (Default)

Always grants resource requests regardless of capacity.

```bash
python -m jimbot.mocks.resource_coordinator.server --mode always_grant
```

### 2. Simulate Contention

Randomly denies or queues requests based on configured probabilities.

```bash
python -m jimbot.mocks.resource_coordinator.server \
  --mode simulate_contention \
  --deny-probability 0.1 \
  --queue-probability 0.2
```

### 3. Respect Limits

Enforces actual resource limits and denies requests when capacity is exceeded.

```bash
python -m jimbot.mocks.resource_coordinator.server --mode respect_limits
```

## Using the Python Client

```python
from jimbot.mocks.resource_coordinator.client import ResourceCoordinatorClient

# Create client
with ResourceCoordinatorClient(host='localhost', port=50051) as client:
    # Request GPU resources
    success, message, request_id = client.request_gpu(
        component='ray_rllib',
        memory_mb=8000,  # 8GB
        priority='HIGH',
        duration_seconds=3600,  # 1 hour
        metadata={'job_id': '12345'}
    )

    if success:
        print(f"GPU allocated: {request_id}")

        # Do work...

        # Release when done
        success, message = client.release_resource(request_id, 'ray_rllib')

    # Check resource status
    status = client.get_status()
    print(status)
```

## Configuration

Use JSON configuration files for different scenarios:

```json
{
  "response_mode": "respect_limits",
  "gpu_capacity": 24000,
  "claude_capacity": 100,
  "memory_capacity": 32768,
  "cpu_capacity": 16
}
```

Load configuration:

```bash
python -m jimbot.mocks.resource_coordinator.server --config config.json
```

## Resource Types

- **GPU**: GPU memory in MB (default: 24GB)
- **CLAUDE_API**: API requests per hour (default: 100)
- **MEMORY**: System memory in MB (default: 32GB)
- **CPU**: CPU cores (default: 16)

## Web UI Features

Access the web UI at http://localhost:8080 to see:

- System health status
- Real-time resource usage
- Active allocations table
- Auto-refresh every 5 seconds

## Integration with Other Components

### Ray RLlib Integration

```python
# In Ray RLlib component
from jimbot.mocks.resource_coordinator.client import ResourceCoordinatorClient

class RayRLlibTrainer:
    def __init__(self):
        self.rc_client = ResourceCoordinatorClient()
        self.gpu_request_id = None

    def acquire_resources(self):
        success, msg, req_id = self.rc_client.request_gpu(
            component='ray_rllib',
            memory_mb=20000,  # 20GB for training
            priority='HIGH'
        )
        if success:
            self.gpu_request_id = req_id
        else:
            raise RuntimeError(f"Failed to acquire GPU: {msg}")

    def release_resources(self):
        if self.gpu_request_id:
            self.rc_client.release_resource(
                self.gpu_request_id,
                'ray_rllib'
            )
```

### Analytics Integration

```python
# In Analytics component
def run_analysis():
    with ResourceCoordinatorClient() as client:
        # Request Claude API quota
        success, msg, req_id = client.request_claude_api(
            component='analytics',
            requests_per_hour=10,
            priority='NORMAL'
        )

        if not success:
            # Fall back to local analysis
            return run_local_analysis()

        try:
            # Run Claude-enhanced analysis
            return run_claude_analysis()
        finally:
            # Always release
            client.release_resource(req_id, 'analytics')
```

## Testing Different Scenarios

### Test Resource Exhaustion

```python
# Exhaust GPU resources
client = ResourceCoordinatorClient()

# Request all GPU memory
success1, _, req1 = client.request_gpu('test1', 20000)
success2, _, req2 = client.request_gpu('test2', 5000)  # Should fail in respect_limits mode
```

### Test Priority Handling

```python
# High priority request should succeed even under contention
success, _, _ = client.request_gpu(
    component='critical_job',
    memory_mb=8000,
    priority='CRITICAL'
)
```

## Troubleshooting

### Server won't start

- Check port 50051 is not in use: `lsof -i :50051`
- Ensure proto files are compiled
- Check Python dependencies are installed

### Client connection errors

- Verify server is running: `curl localhost:50051` (should fail with HTTP/2
  error)
- Check firewall/network settings
- Verify correct host/port in client

### Web UI not updating

- Check browser console for errors
- Verify coordinator is accessible from web UI container
- Check CORS settings if running in different domains

## Development

### Adding New Resource Types

1. Update `resource_coordinator.proto`:

```protobuf
enum ResourceType {
  // ...existing types...
  RESOURCE_TYPE_DISK = 5;
}
```

2. Update server capacities:

```python
self.capacities[resource_coordinator_pb2.RESOURCE_TYPE_DISK] = 1000000  # 1TB in MB
```

3. Add client helper method:

```python
def request_disk(self, component: str, size_mb: int, **kwargs):
    return self._request_resource(
        component=component,
        resource_type=resource_coordinator_pb2.RESOURCE_TYPE_DISK,
        quantity=size_mb,
        **kwargs
    )
```

## Performance Notes

- The mock is designed for development, not production performance
- Request handling is synchronous (fine for testing)
- History is kept in memory (will grow over time)
- No persistence between restarts

## Next Steps

When the real Rust Resource Coordinator is ready:

1. Ensure it implements the same gRPC interface
2. Update client connection settings
3. No code changes needed in components using the client library
