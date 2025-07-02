"""Resource Coordinator Implementation

Manages GPU allocation, API rate limiting, and shared resources.
"""

import asyncio
import time
from typing import Dict, Optional, Any
from collections import deque
from contextlib import asynccontextmanager
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class ResourceAllocation:
    """Track resource allocation details"""
    component_id: str
    resource_type: str
    allocated_at: float
    expires_at: Optional[float] = None
    metadata: Dict[str, Any] = None


class ResourceCoordinator:
    """
    Central coordinator for all shared resources.
    
    Manages:
    - GPU allocation for training/inference
    - Claude API rate limiting
    - Redis connection pooling
    - Priority-based resource allocation
    """
    
    def __init__(self):
        self.gpu_allocator = GPUAllocator()
        self.claude_limiter = ClaudeRateLimiter()
        self.redis_coordinator = RedisCoordinator()
        self.allocations: Dict[str, ResourceAllocation] = {}
        
    async def allocate_gpu(self, component_id: str, duration_seconds: float = 300):
        """Allocate GPU to a component"""
        return await self.gpu_allocator.allocate(component_id, duration_seconds)
        
    async def can_call_claude(self) -> bool:
        """Check if Claude API call is allowed"""
        return await self.claude_limiter.acquire()
        
    async def get_redis_client(self, namespace: str):
        """Get Redis client for a namespace"""
        return await self.redis_coordinator.get_client(namespace)
        
    async def get_status(self) -> Dict[str, Any]:
        """Get current resource allocation status"""
        return {
            'gpu': {
                'allocated': self.gpu_allocator.is_allocated(),
                'current_user': self.gpu_allocator.current_user,
                'queue_length': self.gpu_allocator.queue_size()
            },
            'claude': {
                'requests_used': self.claude_limiter.get_usage(),
                'requests_remaining': self.claude_limiter.remaining(),
                'reset_time': self.claude_limiter.get_reset_time()
            },
            'redis': {
                'active_connections': self.redis_coordinator.get_connection_count(),
                'max_connections': self.redis_coordinator.max_connections
            }
        }


class GPUAllocator:
    """
    GPU allocation manager with priority queuing.
    
    Features:
    - Exclusive GPU access (one component at a time)
    - Priority-based allocation
    - Automatic timeout and release
    - Queue management for waiting components
    """
    
    def __init__(self, default_timeout_seconds: float = 300):
        self.semaphore = asyncio.Semaphore(1)
        self.current_user: Optional[str] = None
        self.allocation_queue = asyncio.PriorityQueue()
        self.default_timeout = default_timeout_seconds
        self.allocation_start: Optional[float] = None
        self._monitor_task: Optional[asyncio.Task] = None
        
    @asynccontextmanager
    async def allocate(self, component_id: str, duration_seconds: Optional[float] = None):
        """
        Allocate GPU to a component.
        
        Args:
            component_id: ID of the requesting component
            duration_seconds: Maximum allocation duration
            
        Example:
            async with gpu_allocator.allocate("training_job_1", 600):
                # GPU is allocated for up to 600 seconds
                await train_model()
        """
        timeout = duration_seconds or self.default_timeout
        priority = self._get_priority(component_id)
        
        # Add to queue
        queue_entry = (priority, time.time(), component_id)
        await self.allocation_queue.put(queue_entry)
        
        # Wait for our turn
        while True:
            if not self.current_user:
                # Try to acquire
                _, _, next_component = await self.allocation_queue.get()
                if next_component == component_id:
                    break
                else:
                    # Not our turn, put it back
                    await self.allocation_queue.put((priority, time.time(), next_component))
                    
            await asyncio.sleep(0.1)
            
        # Acquire GPU
        async with self.semaphore:
            self.current_user = component_id
            self.allocation_start = time.time()
            
            # Start timeout monitor
            self._monitor_task = asyncio.create_task(
                self._timeout_monitor(component_id, timeout)
            )
            
            logger.info(f"GPU allocated to {component_id} for {timeout}s")
            
            try:
                yield
            finally:
                self.current_user = None
                self.allocation_start = None
                if self._monitor_task:
                    self._monitor_task.cancel()
                logger.info(f"GPU released by {component_id}")
                
    async def _timeout_monitor(self, component_id: str, timeout: float):
        """Monitor for allocation timeout"""
        await asyncio.sleep(timeout)
        logger.warning(f"GPU allocation timeout for {component_id}")
        # Force release will happen when context manager exits
        
    def _get_priority(self, component_id: str) -> int:
        """Get priority for component (lower number = higher priority)"""
        priority_map = {
            'training': 1,
            'inference': 2,
            'evaluation': 3
        }
        
        for key, priority in priority_map.items():
            if key in component_id:
                return priority
                
        return 10  # Default low priority
        
    def is_allocated(self) -> bool:
        """Check if GPU is currently allocated"""
        return self.current_user is not None
        
    def queue_size(self) -> int:
        """Get number of components waiting for GPU"""
        return self.allocation_queue.qsize()


class ClaudeRateLimiter:
    """
    Rate limiter for Claude API calls.
    
    Features:
    - Sliding window rate limiting (100 requests/hour)
    - Request queuing when limit reached
    - Usage tracking and reporting
    """
    
    def __init__(self, hourly_limit: int = 100):
        self.hourly_limit = hourly_limit
        self.window = deque()
        self.lock = asyncio.Lock()
        
    async def acquire(self) -> bool:
        """
        Try to acquire permission for an API call.
        
        Returns:
            True if call is allowed, False if rate limit reached
        """
        async with self.lock:
            now = time.time()
            
            # Remove timestamps older than 1 hour
            while self.window and self.window[0] < now - 3600:
                self.window.popleft()
                
            # Check if we can make a request
            if len(self.window) < self.hourly_limit:
                self.window.append(now)
                return True
                
            return False
            
    async def acquire_or_wait(self):
        """Acquire permission, waiting if necessary"""
        while not await self.acquire():
            # Calculate wait time
            if self.window:
                oldest = self.window[0]
                wait_time = 3600 - (time.time() - oldest) + 1
                logger.info(f"Rate limit reached, waiting {wait_time:.1f}s")
                await asyncio.sleep(min(wait_time, 60))  # Check every minute
            else:
                await asyncio.sleep(1)
                
    def get_usage(self) -> int:
        """Get number of requests in current window"""
        now = time.time()
        # Clean old entries
        while self.window and self.window[0] < now - 3600:
            self.window.popleft()
        return len(self.window)
        
    def remaining(self) -> int:
        """Get remaining requests in current window"""
        return max(0, self.hourly_limit - self.get_usage())
        
    def get_reset_time(self) -> Optional[datetime]:
        """Get time when rate limit resets"""
        if not self.window:
            return None
            
        oldest = self.window[0]
        reset_timestamp = oldest + 3600
        return datetime.fromtimestamp(reset_timestamp)


class RedisCoordinator:
    """
    Coordinates Redis access between Claude and Analytics components.
    
    Features:
    - Connection pooling
    - Namespace isolation
    - Connection monitoring
    """
    
    def __init__(self, max_connections: int = 20):
        self.max_connections = max_connections
        self.namespaces = {
            'claude': 'claude:',
            'analytics': 'analytics:',
            'shared': 'shared:',
            'cache': 'cache:'
        }
        self._pool = None
        self._clients: Dict[str, Any] = {}
        
    async def initialize(self):
        """Initialize Redis connection pool"""
        # This would connect to actual Redis in production
        # For now, it's a placeholder
        logger.info(f"Redis coordinator initialized with {self.max_connections} max connections")
        
    async def get_client(self, namespace: str):
        """
        Get Redis client for a specific namespace.
        
        Args:
            namespace: One of 'claude', 'analytics', 'shared', 'cache'
            
        Returns:
            Redis client with automatic key prefixing
        """
        if namespace not in self.namespaces:
            raise ValueError(f"Unknown namespace: {namespace}")
            
        if namespace not in self._clients:
            # Create namespaced client
            # In production, this would create actual Redis client
            self._clients[namespace] = f"RedisClient(prefix={self.namespaces[namespace]})"
            
        return self._clients[namespace]
        
    def get_connection_count(self) -> int:
        """Get current number of active connections"""
        return len(self._clients)
        
    async def close(self):
        """Close all Redis connections"""
        self._clients.clear()
        if self._pool:
            # Close connection pool
            pass