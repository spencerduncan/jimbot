"""JimBot Infrastructure Package

Provides core infrastructure components for communication and resource management.
"""

from .config import ConfigManager
from .event_bus import EventAggregator, EventBus
from .logging import get_logger
from .monitoring import MetricsCollector
from .resource_coordinator import ClaudeRateLimiter, GPUAllocator, ResourceCoordinator

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
