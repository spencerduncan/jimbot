"""Rate Limiter Module

Implements rate limiting for Claude API calls.
"""

import asyncio
import time
from collections import deque
from typing import Optional
from datetime import datetime


class ClaudeRateLimiter:
    """Rate limiter for Claude API"""
    
    def __init__(self, hourly_limit: int = 100):
        self.hourly_limit = hourly_limit
        self.window = deque()
        self.lock = asyncio.Lock()
        
    async def acquire(self) -> bool:
        """Try to acquire API call permission"""
        async with self.lock:
            now = time.time()
            # Clean old timestamps
            while self.window and self.window[0] < now - 3600:
                self.window.popleft()
                
            if len(self.window) < self.hourly_limit:
                self.window.append(now)
                return True
                
            return False
            
    def get_status(self):
        """Get rate limiter status"""
        return {
            'requests_used': len(self.window),
            'requests_remaining': max(0, self.hourly_limit - len(self.window))
        }