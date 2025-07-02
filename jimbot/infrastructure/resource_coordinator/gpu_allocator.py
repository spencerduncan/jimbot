"""GPU Allocator Module

Manages exclusive GPU access for training and inference.
"""

import asyncio
from contextlib import asynccontextmanager
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class GPUAllocator:
    """GPU allocation manager"""
    
    def __init__(self, default_timeout: float = 300):
        self.semaphore = asyncio.Semaphore(1)
        self.current_user: Optional[str] = None
        self.default_timeout = default_timeout
        
    @asynccontextmanager
    async def allocate(self, component_id: str, timeout: Optional[float] = None):
        """Allocate GPU exclusively"""
        timeout = timeout or self.default_timeout
        async with self.semaphore:
            self.current_user = component_id
            try:
                yield
            finally:
                self.current_user = None
                
    def get_status(self):
        """Get GPU allocation status"""
        return {
            'allocated': self.current_user is not None,
            'current_user': self.current_user
        }