"""Event Subscriber Module

Provides subscriber interface for components.
"""

import logging
from typing import List

logger = logging.getLogger(__name__)


class Subscriber:
    """Subscriber interface for event bus"""

    def __init__(self, event_bus, component_name: str):
        self.event_bus = event_bus
        self.component_name = component_name
        self.subscriptions: List[str] = []

    def subscribe(self, pattern: str):
        """Subscribe to event pattern"""
        self.subscriptions.append(pattern)
        return self.event_bus.subscribe(pattern)
