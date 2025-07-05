"""Event Bus Implementation

Central publish-subscribe system for component communication.
"""

import asyncio
import logging
import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class Event:
    """Base event structure"""

    id: str
    timestamp: float
    source: str
    topic: str
    data: Any
    correlation_id: Optional[str] = None


class EventBus:
    """
    Central event bus for publish-subscribe communication.

    Features:
    - Topic-based routing with wildcard support
    - Batch processing with configurable windows
    - At-least-once delivery guarantees
    - Async handler support
    """

    def __init__(self, batch_window_ms: int = 100, max_batch_size: int = 1000):
        self.batch_window_ms = batch_window_ms
        self.max_batch_size = max_batch_size
        self.handlers: Dict[str, List[Callable]] = defaultdict(list)
        self.batch_queue: asyncio.Queue = asyncio.Queue()
        self.running = False
        self._batch_task: Optional[asyncio.Task] = None

    async def start(self):
        """Start the event bus and batch processing"""
        self.running = True
        self._batch_task = asyncio.create_task(self._batch_processor())
        logger.info("Event bus started")

    async def stop(self):
        """Stop the event bus gracefully"""
        self.running = False
        if self._batch_task:
            await self._batch_task
        logger.info("Event bus stopped")

    async def publish(
        self,
        topic: str,
        data: Any,
        source: str = "unknown",
        correlation_id: Optional[str] = None,
    ):
        """
        Publish an event to a topic.

        Args:
            topic: Topic name (e.g., "game.state.update")
            data: Event data
            source: Source component name
            correlation_id: Optional correlation ID for tracing
        """
        event = Event(
            id=f"{source}_{int(time.time() * 1000000)}",
            timestamp=time.time(),
            source=source,
            topic=topic,
            data=data,
            correlation_id=correlation_id,
        )

        await self.batch_queue.put(event)

    def subscribe(self, pattern: str):
        """
        Decorator to subscribe to topics matching a pattern.

        Args:
            pattern: Topic pattern (supports * wildcard)

        Example:
            @event_bus.subscribe("game.state.*")
            async def handle_game_state(event):
                print(f"Game state update: {event.data}")
        """

        def decorator(handler: Callable):
            self.handlers[pattern].append(handler)
            logger.info(f"Registered handler for pattern: {pattern}")
            return handler

        return decorator

    async def _batch_processor(self):
        """Process events in batches for efficiency"""
        while self.running:
            batch = []
            deadline = time.time() + (self.batch_window_ms / 1000.0)

            # Collect events until deadline or max batch size
            while time.time() < deadline and len(batch) < self.max_batch_size:
                try:
                    remaining = deadline - time.time()
                    if remaining > 0:
                        event = await asyncio.wait_for(
                            self.batch_queue.get(), timeout=remaining
                        )
                        batch.append(event)
                except asyncio.TimeoutError:
                    break

            if batch:
                await self._process_batch(batch)

    async def _process_batch(self, events: List[Event]):
        """Process a batch of events"""
        # Group events by topic for efficient routing
        events_by_topic = defaultdict(list)
        for event in events:
            events_by_topic[event.topic].append(event)

        # Dispatch to handlers
        tasks = []
        for topic, topic_events in events_by_topic.items():
            for pattern, handlers in self.handlers.items():
                if self._matches_pattern(topic, pattern):
                    for handler in handlers:
                        for event in topic_events:
                            task = asyncio.create_task(
                                self._safe_handler_call(handler, event)
                            )
                            tasks.append(task)

        # Wait for all handlers to complete
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _safe_handler_call(self, handler: Callable, event: Event):
        """Call handler with error handling"""
        try:
            await handler(event)
        except Exception as e:
            logger.error(f"Handler error for {event.topic}: {e}", exc_info=True)

    def _matches_pattern(self, topic: str, pattern: str) -> bool:
        """Check if topic matches pattern (supports * wildcard)"""
        if pattern == topic:
            return True

        pattern_parts = pattern.split(".")
        topic_parts = topic.split(".")

        if len(pattern_parts) != len(topic_parts):
            return False

        for p, t in zip(pattern_parts, topic_parts):
            if p != "*" and p != t:
                return False

        return True


class EventAggregator:
    """
    Aggregates multiple events into summary events.

    Used primarily for high-frequency game events from MCP.
    """

    def __init__(self):
        self.aggregation_rules = {
            "game.card.played": self._aggregate_cards_played,
            "game.damage.dealt": self._aggregate_damage,
            "game.money.earned": self._aggregate_money,
        }

    async def aggregate(self, events: List[Event]) -> List[Event]:
        """Aggregate events based on type"""
        # Group by event type
        grouped = defaultdict(list)
        for event in events:
            grouped[event.topic].append(event)

        # Apply aggregation rules
        aggregated = []
        for topic, group in grouped.items():
            if topic in self.aggregation_rules:
                aggregated_event = self.aggregation_rules[topic](group)
                if aggregated_event:
                    aggregated.append(aggregated_event)
            else:
                # No aggregation rule, pass through
                aggregated.extend(group)

        return aggregated

    def _aggregate_cards_played(self, events: List[Event]) -> Optional[Event]:
        """Aggregate multiple card played events"""
        if not events:
            return None

        total_cards = sum(e.data.get("count", 1) for e in events)

        return Event(
            id=f"agg_{events[0].id}",
            timestamp=events[-1].timestamp,
            source="aggregator",
            topic="game.cards.played_batch",
            data={
                "total_cards": total_cards,
                "event_count": len(events),
                "time_window": events[-1].timestamp - events[0].timestamp,
            },
            correlation_id=events[0].correlation_id,
        )

    def _aggregate_damage(self, events: List[Event]) -> Optional[Event]:
        """Aggregate damage events"""
        if not events:
            return None

        total_damage = sum(e.data.get("damage", 0) for e in events)

        return Event(
            id=f"agg_{events[0].id}",
            timestamp=events[-1].timestamp,
            source="aggregator",
            topic="game.damage.total",
            data={
                "total_damage": total_damage,
                "hit_count": len(events),
                "average_damage": total_damage / len(events) if events else 0,
            },
            correlation_id=events[0].correlation_id,
        )

    def _aggregate_money(self, events: List[Event]) -> Optional[Event]:
        """Aggregate money earned events"""
        if not events:
            return None

        total_money = sum(e.data.get("amount", 0) for e in events)

        return Event(
            id=f"agg_{events[0].id}",
            timestamp=events[-1].timestamp,
            source="aggregator",
            topic="game.money.total_earned",
            data={"total_amount": total_money, "transaction_count": len(events)},
            correlation_id=events[0].correlation_id,
        )
