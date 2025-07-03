"""JimBot Infrastructure Package

Provides core infrastructure components for communication and resource management.
"""

from .event_bus import EventBus, EventAggregator
from .resource_coordinator import ResourceCoordinator, GPUAllocator, ClaudeRateLimiter
from .config import ConfigManager
from .logging import get_logger
from .monitoring import MetricsCollector

__all__ = [
    "EventBus",
    "EventAggregator",
    "ResourceCoordinator",
    "GPUAllocator",
    "ClaudeRateLimiter",
    "ConfigManager",
    "get_logger",
    "MetricsCollector",
]

__version__ = "0.1.0"
