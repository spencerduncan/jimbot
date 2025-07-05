#!/usr/bin/env python3
"""
Integration test for the mock Resource Coordinator.
Run this after starting the server to verify everything works.
"""

import json
import time
from concurrent.futures import ThreadPoolExecutor

from client import ResourceCoordinatorClient


def test_basic_allocation():
    """Test basic resource allocation and release."""
    print("=== Testing Basic Allocation ===")

    with ResourceCoordinatorClient() as client:
        # Check health
        health = client.health_check()
        assert health["healthy"], "Server is not healthy"
        print(f"✓ Server healthy: v{health['version']}")

        # Request GPU
        success, msg, req_id = client.request_gpu(
            component="test_basic", memory_mb=4000, priority="NORMAL"
        )
        assert success, f"Failed to allocate GPU: {msg}"
        print(f"✓ GPU allocated: {req_id}")

        # Check status shows allocation
        status = client.get_status("GPU")
        gpu_status = status["resources"]["RESOURCE_TYPE_GPU"]
        assert gpu_status["allocated"] >= 4000, "GPU not properly allocated"
        print(f"✓ GPU status shows allocation: {gpu_status['allocated']}MB")

        # Release
        success, msg = client.release_resource(req_id, "test_basic")
        assert success, f"Failed to release: {msg}"
        print("✓ GPU released")

        # Verify released
        status = client.get_status("GPU")
        gpu_status = status["resources"]["RESOURCE_TYPE_GPU"]
        print(f"✓ GPU available after release: {gpu_status['available']}MB")


def test_multiple_resources():
    """Test allocating multiple resource types."""
    print("\n=== Testing Multiple Resources ===")

    with ResourceCoordinatorClient() as client:
        allocations = []

        # Request GPU
        success, msg, gpu_id = client.request_gpu(
            component="test_multi", memory_mb=8000, metadata={"test": "multi"}
        )
        assert success, f"GPU allocation failed: {msg}"
        allocations.append(("gpu", gpu_id))
        print("✓ GPU allocated")

        # Request Claude API
        success, msg, api_id = client.request_claude_api(
            component="test_multi", requests_per_hour=50
        )
        assert success, f"API allocation failed: {msg}"
        allocations.append(("api", api_id))
        print("✓ Claude API allocated")

        # Request Memory
        success, msg, mem_id = client.request_memory(
            component="test_multi", memory_mb=4096
        )
        assert success, f"Memory allocation failed: {msg}"
        allocations.append(("mem", mem_id))
        print("✓ Memory allocated")

        # Check all are allocated
        status = client.get_status()
        print("\nCurrent allocations:")
        for resource_type, resource_status in status["resources"].items():
            if resource_status["allocated"] > 0:
                print(
                    f"  {resource_type}: {resource_status['allocated']} / {resource_status['total_capacity']}"
                )

        # Release all
        for res_type, req_id in allocations:
            success, msg = client.release_resource(req_id, "test_multi")
            assert success, f"Failed to release {res_type}: {msg}"
        print("\n✓ All resources released")


def test_concurrent_requests():
    """Test concurrent resource requests."""
    print("\n=== Testing Concurrent Requests ===")

    def request_gpu(client, component_id):
        """Request GPU for a component."""
        success, msg, req_id = client.request_gpu(
            component=f"worker_{component_id}", memory_mb=2000, priority="NORMAL"
        )
        return component_id, success, msg, req_id

    with ResourceCoordinatorClient() as client:
        # Submit 5 concurrent requests
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = []
            for i in range(5):
                future = executor.submit(request_gpu, client, i)
                futures.append(future)

            # Collect results
            results = []
            for future in futures:
                results.append(future.result())

        # Check results
        successful = sum(1 for _, success, _, _ in results if success)
        print(f"✓ {successful}/5 concurrent requests succeeded")

        # Check total allocation
        status = client.get_status("GPU")
        gpu_status = status["resources"]["RESOURCE_TYPE_GPU"]
        expected = successful * 2000
        assert (
            gpu_status["allocated"] == expected
        ), f"Expected {expected}MB allocated, got {gpu_status['allocated']}MB"
        print(f"✓ Total GPU allocated: {gpu_status['allocated']}MB")

        # Release all successful allocations
        for comp_id, success, _, req_id in results:
            if success:
                client.release_resource(req_id, f"worker_{comp_id}")
        print("✓ All allocations released")


def test_resource_limits():
    """Test resource limit enforcement (requires respect_limits mode)."""
    print("\n=== Testing Resource Limits ===")
    print("NOTE: This test requires server in 'respect_limits' mode")

    with ResourceCoordinatorClient() as client:
        # Try to allocate more than available
        success1, msg1, req1 = client.request_gpu(
            component="test_limits", memory_mb=20000  # 20GB
        )

        if success1:
            print("✓ First large allocation succeeded")

            # This should fail if limits are enforced
            success2, msg2, req2 = client.request_gpu(
                component="test_limits", memory_mb=10000  # 10GB more
            )

            if not success2:
                print(f"✓ Second allocation correctly denied: {msg2}")
            else:
                print("⚠ Second allocation succeeded (limits not enforced)")
                client.release_resource(req2, "test_limits")

            client.release_resource(req1, "test_limits")
        else:
            print(f"⚠ First allocation failed: {msg1}")


def test_priority_levels():
    """Test different priority levels."""
    print("\n=== Testing Priority Levels ===")

    with ResourceCoordinatorClient() as client:
        priorities = ["LOW", "NORMAL", "HIGH", "CRITICAL"]

        for priority in priorities:
            success, msg, req_id = client.request_gpu(
                component="test_priority", memory_mb=1000, priority=priority
            )

            if success:
                print(f"✓ {priority} priority request succeeded")
                client.release_resource(req_id, "test_priority")
            else:
                print(f"✗ {priority} priority request failed: {msg}")


def main():
    """Run all tests."""
    print("Mock Resource Coordinator Integration Tests")
    print("=" * 50)

    try:
        test_basic_allocation()
        test_multiple_resources()
        test_concurrent_requests()
        test_resource_limits()
        test_priority_levels()

        print("\n" + "=" * 50)
        print("✓ All tests completed successfully!")

    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
