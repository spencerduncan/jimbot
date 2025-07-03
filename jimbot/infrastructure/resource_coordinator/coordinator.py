"""Main Resource Coordinator Module

Coordinates all resource allocation across components.
"""

from typing import Any, Dict

from .gpu_allocator import GPUAllocator
from .rate_limiter import ClaudeRateLimiter
from .redis_coordinator import RedisCoordinator


class ResourceCoordinator:
    """Central resource coordinator"""

    def __init__(self):
        self.gpu_allocator = GPUAllocator()
        self.claude_limiter = ClaudeRateLimiter()
        self.redis_coordinator = RedisCoordinator()

    async def initialize(self):
        """Initialize all resource managers"""
        await self.redis_coordinator.initialize()

    async def get_status(self) -> Dict[str, Any]:
        """Get resource allocation status"""
        return {
            "gpu": self.gpu_allocator.get_status(),
            "claude": self.claude_limiter.get_status(),
            "redis": self.redis_coordinator.get_status(),
        }
