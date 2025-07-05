"""Profiler Module

Performance profiling utilities.
"""

import asyncio
import logging
import time
from functools import wraps
from typing import Any, Callable

logger = logging.getLogger(__name__)


class Profiler:
    """Performance profiling utilities"""

    def __init__(self, metrics_collector=None):
        self.metrics_collector = metrics_collector

    def profile(self, name: str):
        """Decorator to profile function execution time"""

        def decorator(func: Callable):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                start = time.time()
                try:
                    result = await func(*args, **kwargs)
                    return result
                finally:
                    duration = time.time() - start
                    self._record_timing(name, duration)

            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                start = time.time()
                try:
                    result = func(*args, **kwargs)
                    return result
                finally:
                    duration = time.time() - start
                    self._record_timing(name, duration)

            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            else:
                return sync_wrapper

        return decorator

    def _record_timing(self, name: str, duration: float):
        """Record timing metric"""
        if self.metrics_collector:
            self.metrics_collector.record_histogram(
                f"function.duration.{name}", duration * 1000  # Convert to ms
            )
        logger.debug(f"{name} took {duration*1000:.2f}ms")
