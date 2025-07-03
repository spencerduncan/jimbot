#!/usr/bin/env python3
"""
Mock Resource Coordinator Server

A simple mock implementation of the Resource Coordinator service that:
- Always grants resource requests (configurable)
- Tracks request history for debugging
- Can simulate different response scenarios
"""

import asyncio
import json
import logging

# These will be generated from the proto file
import sys
import time
import uuid
from concurrent import futures
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import grpc
from google.protobuf.timestamp_pb2 import Timestamp

sys.path.append("/home/spduncan/jimbot")
from jimbot.proto import resource_coordinator_pb2, resource_coordinator_pb2_grpc


class MockResourceCoordinator(
    resource_coordinator_pb2_grpc.ResourceCoordinatorServicer
):
    """Mock implementation of the Resource Coordinator service."""

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.start_time = time.time()
        self.allocations: Dict[str, Dict] = {}
        self.request_history: List[Dict] = []

        # Default capacities
        self.capacities = {
            resource_coordinator_pb2.RESOURCE_TYPE_GPU: self.config.get(
                "gpu_capacity", 24000
            ),  # 24GB
            resource_coordinator_pb2.RESOURCE_TYPE_CLAUDE_API: self.config.get(
                "claude_capacity", 100
            ),  # 100 req/hr
            resource_coordinator_pb2.RESOURCE_TYPE_MEMORY: self.config.get(
                "memory_capacity", 32768
            ),  # 32GB
            resource_coordinator_pb2.RESOURCE_TYPE_CPU: self.config.get(
                "cpu_capacity", 16
            ),  # 16 cores
        }

        # Current usage
        self.usage = {
            resource_coordinator_pb2.RESOURCE_TYPE_GPU: 0,
            resource_coordinator_pb2.RESOURCE_TYPE_CLAUDE_API: 0,
            resource_coordinator_pb2.RESOURCE_TYPE_MEMORY: 0,
            resource_coordinator_pb2.RESOURCE_TYPE_CPU: 0,
        }

        # Response modes
        self.response_mode = self.config.get("response_mode", "always_grant")
        self.deny_probability = self.config.get("deny_probability", 0.0)
        self.queue_probability = self.config.get("queue_probability", 0.0)

        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    def RequestResource(self, request, context):
        """Handle resource allocation request."""
        self.logger.info(
            f"Resource request from {request.component}: "
            f"{request.quantity} {resource_coordinator_pb2.ResourceType.Name(request.resource)}"
        )

        # Generate response based on mode
        response = resource_coordinator_pb2.ResourceResponse()
        response.request_id = request.request_id

        # Record request
        request_record = {
            "request_id": request.request_id,
            "component": request.component,
            "resource": resource_coordinator_pb2.ResourceType.Name(request.resource),
            "quantity": request.quantity,
            "priority": resource_coordinator_pb2.Priority.Name(request.priority),
            "timestamp": datetime.now().isoformat(),
            "metadata": dict(request.metadata),
        }

        # Determine response based on mode
        import random

        if self.response_mode == "always_grant":
            response.status = resource_coordinator_pb2.REQUEST_STATUS_GRANTED
        elif self.response_mode == "simulate_contention":
            rand = random.random()
            if rand < self.deny_probability:
                response.status = resource_coordinator_pb2.REQUEST_STATUS_DENIED
            elif rand < self.deny_probability + self.queue_probability:
                response.status = resource_coordinator_pb2.REQUEST_STATUS_QUEUED
            else:
                response.status = resource_coordinator_pb2.REQUEST_STATUS_GRANTED
        elif self.response_mode == "respect_limits":
            # Check if we have capacity
            if (
                self.usage[request.resource] + request.quantity
                <= self.capacities[request.resource]
            ):
                response.status = resource_coordinator_pb2.REQUEST_STATUS_GRANTED
            else:
                response.status = resource_coordinator_pb2.REQUEST_STATUS_DENIED

        # Handle granted requests
        if response.status == resource_coordinator_pb2.REQUEST_STATUS_GRANTED:
            response.message = "Resource allocated successfully"
            response.token = str(uuid.uuid4())
            response.granted_quantity = request.quantity

            # Set timestamps
            now = Timestamp()
            now.GetCurrentTime()
            response.granted_at.CopyFrom(now)

            # Calculate expiration
            if request.duration.seconds > 0:
                expires = datetime.now() + timedelta(seconds=request.duration.seconds)
            else:
                expires = datetime.now() + timedelta(hours=1)  # Default 1 hour

            expires_ts = Timestamp()
            expires_ts.FromDatetime(expires)
            response.expires_at.CopyFrom(expires_ts)

            # Track allocation
            self.allocations[request.request_id] = {
                "component": request.component,
                "resource": request.resource,
                "quantity": request.quantity,
                "token": response.token,
                "allocated_at": datetime.now(),
                "expires_at": expires,
            }

            # Update usage
            self.usage[request.resource] += request.quantity

        elif response.status == resource_coordinator_pb2.REQUEST_STATUS_DENIED:
            response.message = f"Insufficient {resource_coordinator_pb2.ResourceType.Name(request.resource)} available"
        else:  # QUEUED
            response.message = (
                "Request queued, will be processed when resources are available"
            )

        # Record response
        request_record["status"] = resource_coordinator_pb2.RequestStatus.Name(
            response.status
        )
        request_record["granted_quantity"] = response.granted_quantity
        self.request_history.append(request_record)

        return response

    def ReleaseResource(self, request, context):
        """Handle resource release."""
        self.logger.info(
            f"Release request from {request.component} for {request.request_id}"
        )

        response = resource_coordinator_pb2.ReleaseResponse()

        if request.request_id in self.allocations:
            allocation = self.allocations[request.request_id]
            if allocation["token"] == request.token:
                # Release the resource
                self.usage[allocation["resource"]] -= allocation["quantity"]
                del self.allocations[request.request_id]

                response.success = True
                response.message = "Resource released successfully"

                # Record release
                self.request_history.append(
                    {
                        "request_id": request.request_id,
                        "component": request.component,
                        "action": "release",
                        "timestamp": datetime.now().isoformat(),
                        "success": True,
                    }
                )
            else:
                response.success = False
                response.message = "Invalid token"
        else:
            response.success = False
            response.message = "Request ID not found"

        return response

    def GetResourceStatus(self, request, context):
        """Get current resource status."""
        response = resource_coordinator_pb2.ResourceStatusResponse()

        # If specific resource requested
        if request.resource != resource_coordinator_pb2.RESOURCE_TYPE_UNSPECIFIED:
            resources = [request.resource]
        else:
            resources = list(self.capacities.keys())

        for resource in resources:
            status = resource_coordinator_pb2.ResourceStatus()
            status.resource = resource
            status.total_capacity = self.capacities[resource]
            status.allocated = self.usage[resource]
            status.available = status.total_capacity - status.allocated

            # Add allocation details
            for req_id, alloc in self.allocations.items():
                if alloc["resource"] == resource:
                    info = resource_coordinator_pb2.AllocationInfo()
                    info.request_id = req_id
                    info.component = alloc["component"]
                    info.quantity = alloc["quantity"]

                    allocated_ts = Timestamp()
                    allocated_ts.FromDatetime(alloc["allocated_at"])
                    info.allocated_at.CopyFrom(allocated_ts)

                    expires_ts = Timestamp()
                    expires_ts.FromDatetime(alloc["expires_at"])
                    info.expires_at.CopyFrom(expires_ts)

                    status.allocations.append(info)

            response.statuses.append(status)

        # Set timestamp
        now = Timestamp()
        now.GetCurrentTime()
        response.timestamp.CopyFrom(now)

        return response

    def HealthCheck(self, request, context):
        """Health check endpoint."""
        response = resource_coordinator_pb2.HealthCheckResponse()
        response.healthy = True
        response.version = "1.0.0-mock"
        response.uptime_seconds = int(time.time() - self.start_time)
        response.metadata["mode"] = self.response_mode
        response.metadata["allocations"] = str(len(self.allocations))
        response.metadata["requests_processed"] = str(len(self.request_history))

        return response

    def StreamResourceStatus(self, request, context):
        """Stream resource status updates."""
        self.logger.info("Starting resource status stream")

        try:
            while context.is_active():
                # Get current status for requested resource
                if (
                    request.resource
                    != resource_coordinator_pb2.RESOURCE_TYPE_UNSPECIFIED
                ):
                    resources = [request.resource]
                else:
                    resources = list(self.capacities.keys())

                for resource in resources:
                    status = resource_coordinator_pb2.ResourceStatus()
                    status.resource = resource
                    status.total_capacity = self.capacities[resource]
                    status.allocated = self.usage[resource]
                    status.available = status.total_capacity - status.allocated

                    yield status

                # Stream updates every 5 seconds
                asyncio.run(asyncio.sleep(5))

        except Exception as e:
            self.logger.error(f"Error in status stream: {e}")
            context.abort(grpc.StatusCode.INTERNAL, str(e))

    def get_request_history(self) -> List[Dict]:
        """Get request history for debugging."""
        return self.request_history

    def clear_expired_allocations(self):
        """Clean up expired allocations."""
        now = datetime.now()
        expired = []

        for req_id, alloc in self.allocations.items():
            if alloc["expires_at"] < now:
                expired.append(req_id)

        for req_id in expired:
            alloc = self.allocations[req_id]
            self.usage[alloc["resource"]] -= alloc["quantity"]
            del self.allocations[req_id]
            self.logger.info(f"Expired allocation {req_id} from {alloc['component']}")


def serve(port: int = 50051, config: Optional[Dict] = None):
    """Start the gRPC server."""
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    coordinator = MockResourceCoordinator(config)
    resource_coordinator_pb2_grpc.add_ResourceCoordinatorServicer_to_server(
        coordinator, server
    )

    server.add_insecure_port(f"[::]:{port}")
    server.start()

    logging.info(f"Mock Resource Coordinator started on port {port}")
    logging.info(f"Mode: {config.get('response_mode', 'always_grant')}")

    # Start background task to clean up expired allocations
    async def cleanup_loop():
        while True:
            await asyncio.sleep(60)  # Check every minute
            coordinator.clear_expired_allocations()

    # Run server
    try:
        asyncio.run(cleanup_loop())
    except KeyboardInterrupt:
        server.stop(0)
        logging.info("Server stopped")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Mock Resource Coordinator Server")
    parser.add_argument("--port", type=int, default=50051, help="Port to listen on")
    parser.add_argument(
        "--mode",
        choices=["always_grant", "simulate_contention", "respect_limits"],
        default="always_grant",
        help="Response mode",
    )
    parser.add_argument(
        "--deny-probability",
        type=float,
        default=0.1,
        help="Probability of denying requests in simulate_contention mode",
    )
    parser.add_argument(
        "--queue-probability",
        type=float,
        default=0.2,
        help="Probability of queueing requests in simulate_contention mode",
    )
    parser.add_argument("--config", type=str, help="Path to JSON config file")

    args = parser.parse_args()

    config = {
        "response_mode": args.mode,
        "deny_probability": args.deny_probability,
        "queue_probability": args.queue_probability,
    }

    if args.config:
        with open(args.config, "r") as f:
            config.update(json.load(f))

    serve(args.port, config)
