"""Event Publisher Module

Provides publisher interface for components.
"""

from typing import Any, Optional


class Publisher:
    """Publisher interface for event bus"""

    def __init__(self, event_bus, source: str):
        self.event_bus = event_bus
        self.source = source

    async def publish(
        self, topic: str, data: Any, correlation_id: Optional[str] = None
    ):
        """Publish event to topic"""
        await self.event_bus.publish(topic, data, self.source, correlation_id)
