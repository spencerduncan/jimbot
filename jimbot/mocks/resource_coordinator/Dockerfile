FROM python:3.9-slim

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir \
    grpcio \
    grpcio-tools \
    flask \
    protobuf

# Copy proto files
COPY jimbot/proto/*.proto /app/jimbot/proto/

# Generate Python code from proto files
RUN python -m grpc_tools.protoc \
    -I/app \
    --python_out=/app \
    --grpc_python_out=/app \
    jimbot/proto/resource_coordinator.proto

# Copy application files
COPY jimbot/mocks/resource_coordinator/*.py /app/jimbot/mocks/resource_coordinator/
COPY jimbot/mocks/resource_coordinator/config_examples.json /app/jimbot/mocks/resource_coordinator/

# Create empty __init__.py files for proper module structure
RUN mkdir -p /app/jimbot/proto && \
    touch /app/jimbot/__init__.py && \
    touch /app/jimbot/proto/__init__.py && \
    touch /app/jimbot/mocks/__init__.py && \
    touch /app/jimbot/mocks/resource_coordinator/__init__.py

# Expose ports
EXPOSE 50051 8080

# Default command runs the server
CMD ["python", "-m", "jimbot.mocks.resource_coordinator.server", "--mode", "always_grant"]