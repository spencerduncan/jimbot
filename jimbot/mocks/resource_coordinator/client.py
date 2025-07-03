#!/usr/bin/env python3
"""
Client library for the Resource Coordinator service.
"""

import uuid
from typing import Dict, Optional, Tuple

import grpc

import sys

sys.path.append("/home/spduncan/jimbot")
from jimbot.proto import resource_coordinator_pb2
from jimbot.proto import resource_coordinator_pb2_grpc


class ResourceCoordinatorClient:
    """Client for interacting with the Resource Coordinator service."""

    def __init__(self, host: str = "localhost", port: int = 50051):
        """Initialize the client.

        Args:
            host: Resource Coordinator host
            port: Resource Coordinator port
        """
        self.channel = grpc.insecure_channel(f"{host}:{port}")
        self.stub = resource_coordinator_pb2_grpc.ResourceCoordinatorStub(self.channel)
        self._allocations: Dict[str, str] = {}  # request_id -> token mapping

    def request_gpu(
        self,
        component: str,
        memory_mb: int,
        priority: str = "NORMAL",
        timeout_seconds: int = 60,
        duration_seconds: int = 3600,
        metadata: Optional[Dict[str, str]] = None,
    ) -> Tuple[bool, str, Optional[str]]:
        """Request GPU resources.

        Args:
            component: Name of the requesting component
            memory_mb: Amount of GPU memory in MB
            priority: Request priority (LOW, NORMAL, HIGH, CRITICAL)
            timeout_seconds: Max time to wait for resource
            duration_seconds: Expected usage duration
            metadata: Additional metadata

        Returns:
            Tuple of (success, message, request_id)
        """
        return self._request_resource(
            component=component,
            resource_type=resource_coordinator_pb2.RESOURCE_TYPE_GPU,
            quantity=memory_mb,
            priority=priority,
            timeout_seconds=timeout_seconds,
            duration_seconds=duration_seconds,
            metadata=metadata,
        )

    def request_claude_api(
        self,
        component: str,
        requests_per_hour: int = 1,
        priority: str = "NORMAL",
        timeout_seconds: int = 60,
        duration_seconds: int = 3600,
        metadata: Optional[Dict[str, str]] = None,
    ) -> Tuple[bool, str, Optional[str]]:
        """Request Claude API quota.

        Args:
            component: Name of the requesting component
            requests_per_hour: Number of API requests per hour
            priority: Request priority
            timeout_seconds: Max time to wait for resource
            duration_seconds: Expected usage duration
            metadata: Additional metadata

        Returns:
            Tuple of (success, message, request_id)
        """
        return self._request_resource(
            component=component,
            resource_type=resource_coordinator_pb2.RESOURCE_TYPE_CLAUDE_API,
            quantity=requests_per_hour,
            priority=priority,
            timeout_seconds=timeout_seconds,
            duration_seconds=duration_seconds,
            metadata=metadata,
        )

    def request_memory(
        self,
        component: str,
        memory_mb: int,
        priority: str = "NORMAL",
        timeout_seconds: int = 60,
        duration_seconds: int = 3600,
        metadata: Optional[Dict[str, str]] = None,
    ) -> Tuple[bool, str, Optional[str]]:
        """Request memory resources.

        Args:
            component: Name of the requesting component
            memory_mb: Amount of memory in MB
            priority: Request priority
            timeout_seconds: Max time to wait for resource
            duration_seconds: Expected usage duration
            metadata: Additional metadata

        Returns:
            Tuple of (success, message, request_id)
        """
        return self._request_resource(
            component=component,
            resource_type=resource_coordinator_pb2.RESOURCE_TYPE_MEMORY,
            quantity=memory_mb,
            priority=priority,
            timeout_seconds=timeout_seconds,
            duration_seconds=duration_seconds,
            metadata=metadata,
        )

    def _request_resource(
        self,
        component: str,
        resource_type: int,
        quantity: int,
        priority: str,
        timeout_seconds: int,
        duration_seconds: int,
        metadata: Optional[Dict[str, str]],
    ) -> Tuple[bool, str, Optional[str]]:
        """Internal method to request resources."""
        request = resource_coordinator_pb2.ResourceRequest()
        request.request_id = str(uuid.uuid4())
        request.component = component
        request.resource = resource_type
        request.quantity = quantity

        # Set priority
        priority_map = {
            "LOW": resource_coordinator_pb2.PRIORITY_LOW,
            "NORMAL": resource_coordinator_pb2.PRIORITY_NORMAL,
            "HIGH": resource_coordinator_pb2.PRIORITY_HIGH,
            "CRITICAL": resource_coordinator_pb2.PRIORITY_CRITICAL,
        }
        request.priority = priority_map.get(
            priority.upper(), resource_coordinator_pb2.PRIORITY_NORMAL
        )

        # Set timeout
        request.timeout.seconds = timeout_seconds

        # Set duration
        request.duration.seconds = duration_seconds

        # Add metadata
        if metadata:
            for key, value in metadata.items():
                request.metadata[key] = value

        try:
            response = self.stub.RequestResource(request)

            if response.status == resource_coordinator_pb2.REQUEST_STATUS_GRANTED:
                # Store the allocation info
                self._allocations[request.request_id] = response.token
                return True, response.message, request.request_id
            else:
                return False, response.message, request.request_id

        except grpc.RpcError as e:
            return False, f"RPC error: {e}", None

    def release_resource(self, request_id: str, component: str) -> Tuple[bool, str]:
        """Release a previously allocated resource.

        Args:
            request_id: The request ID from allocation
            component: Name of the component releasing the resource

        Returns:
            Tuple of (success, message)
        """
        if request_id not in self._allocations:
            return False, "Request ID not found in local allocations"

        request = resource_coordinator_pb2.ReleaseRequest()
        request.request_id = request_id
        request.token = self._allocations[request_id]
        request.component = component

        try:
            response = self.stub.ReleaseResource(request)

            if response.success:
                del self._allocations[request_id]

            return response.success, response.message

        except grpc.RpcError as e:
            return False, f"RPC error: {e}"

    def get_status(self, resource_type: Optional[str] = None) -> Dict:
        """Get current resource status.

        Args:
            resource_type: Optional specific resource type to query

        Returns:
            Dictionary with resource status information
        """
        request = resource_coordinator_pb2.ResourceStatusRequest()

        if resource_type:
            type_map = {
                "GPU": resource_coordinator_pb2.RESOURCE_TYPE_GPU,
                "CLAUDE_API": resource_coordinator_pb2.RESOURCE_TYPE_CLAUDE_API,
                "MEMORY": resource_coordinator_pb2.RESOURCE_TYPE_MEMORY,
                "CPU": resource_coordinator_pb2.RESOURCE_TYPE_CPU,
            }
            request.resource = type_map.get(
                resource_type.upper(),
                resource_coordinator_pb2.RESOURCE_TYPE_UNSPECIFIED,
            )

        try:
            response = self.stub.GetResourceStatus(request)

            result = {
                "timestamp": response.timestamp.ToDatetime().isoformat(),
                "resources": {},
            }

            for status in response.statuses:
                resource_name = resource_coordinator_pb2.ResourceType.Name(
                    status.resource
                )
                result["resources"][resource_name] = {
                    "total_capacity": status.total_capacity,
                    "available": status.available,
                    "allocated": status.allocated,
                    "allocations": [],
                }

                for alloc in status.allocations:
                    result["resources"][resource_name]["allocations"].append(
                        {
                            "request_id": alloc.request_id,
                            "component": alloc.component,
                            "quantity": alloc.quantity,
                            "allocated_at": alloc.allocated_at.ToDatetime().isoformat(),
                            "expires_at": alloc.expires_at.ToDatetime().isoformat(),
                        }
                    )

            return result

        except grpc.RpcError as e:
            return {"error": str(e)}

    def health_check(self) -> Dict:
        """Perform a health check.

        Returns:
            Dictionary with health status
        """
        request = resource_coordinator_pb2.HealthCheckRequest()

        try:
            response = self.stub.HealthCheck(request)

            return {
                "healthy": response.healthy,
                "version": response.version,
                "uptime_seconds": response.uptime_seconds,
                "metadata": dict(response.metadata),
            }

        except grpc.RpcError as e:
            return {"healthy": False, "error": str(e)}

    def close(self):
        """Close the gRPC channel."""
        self.channel.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


# Example usage
if __name__ == "__main__":
    import time
    import json

    # Create client
    with ResourceCoordinatorClient() as client:
        # Check health
        print("Health Check:")
        print(json.dumps(client.health_check(), indent=2))
        print()

        # Request GPU resource
        print("Requesting GPU resource...")
        success, message, request_id = client.request_gpu(
            component="test_client",
            memory_mb=8000,  # 8GB
            priority="NORMAL",
            metadata={"job_type": "training", "model": "test_model"},
        )
        print(f"Success: {success}, Message: {message}, Request ID: {request_id}")
        print()

        if success and request_id:
            # Check status
            print("Resource Status:")
            print(json.dumps(client.get_status(), indent=2))
            print()

            # Wait a bit
            time.sleep(2)

            # Release resource
            print("Releasing resource...")
            success, message = client.release_resource(request_id, "test_client")
            print(f"Success: {success}, Message: {message}")
            print()

            # Check status again
            print("Resource Status After Release:")
            print(json.dumps(client.get_status(), indent=2))
