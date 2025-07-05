"""
Event handler implementation for MCP.

This module provides event handling logic for different game event types
and routing to appropriate processors.
"""

import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """Enumeration of Balatro game event types."""

    GAME_START = "game_start"
    HAND_PLAYED = "hand_played"
    JOKER_TRIGGERED = "joker_triggered"
    BLIND_DEFEATED = "blind_defeated"
    SHOP_ENTERED = "shop_entered"
    CARD_PURCHASED = "card_purchased"
    CARD_SOLD = "card_sold"
    CARD_DISCARDED = "card_discarded"
    CARD_ENHANCED = "card_enhanced"
    ROUND_STARTED = "round_started"
    ROUND_ENDED = "round_ended"
    GAME_OVER = "game_over"
    STATE_SNAPSHOT = "state_snapshot"
    ERROR = "error"
    UNKNOWN = "unknown"


@dataclass
class ProcessedEvent:
    """Processed event with metadata."""

    event_type: EventType
    game_id: str
    timestamp: float
    data: Dict
    metadata: Dict
    processing_time_ms: float


class EventHandler:
    """
    Central event handler for processing Balatro game events.

    This class routes events to appropriate handlers based on event type
    and maintains event processing statistics.
    """

    def __init__(self):
        """Initialize event handler."""
        self.handlers: Dict[EventType, List[Callable]] = {
            event_type: [] for event_type in EventType
        }
        self.preprocessors: List[Callable] = []
        self.postprocessors: List[Callable] = []
        self.stats = {
            "events_processed": 0,
            "events_by_type": {event_type.value: 0 for event_type in EventType},
            "processing_errors": 0,
        }

    def register_handler(
        self, event_type: EventType, handler: Callable[[Dict], Optional[Dict]]
    ):
        """
        Register a handler for a specific event type.

        Args:
            event_type: Type of event to handle
            handler: Function to process events of this type
        """
        self.handlers[event_type].append(handler)
        logger.debug(f"Registered handler for {event_type.value}")

    def register_preprocessor(self, preprocessor: Callable[[Dict], Dict]):
        """
        Register a preprocessor to run on all events.

        Args:
            preprocessor: Function to preprocess events
        """
        self.preprocessors.append(preprocessor)

    def register_postprocessor(self, postprocessor: Callable[[ProcessedEvent], None]):
        """
        Register a postprocessor to run after event processing.

        Args:
            postprocessor: Function to run after processing
        """
        self.postprocessors.append(postprocessor)

    async def process_event(self, event: Dict) -> Optional[ProcessedEvent]:
        """
        Process a single event through the handler pipeline.

        Args:
            event: Raw event dictionary

        Returns:
            Processed event or None if processing failed
        """
        start_time = time.time()

        try:
            # Run preprocessors
            for preprocessor in self.preprocessors:
                event = await self._run_processor(preprocessor, event)

            # Determine event type
            event_type = self._get_event_type(event)

            # Extract common fields
            game_id = event.get("game_id", "unknown")
            timestamp = event.get("timestamp", time.time())
            data = event.get("data", {})

            # Run type-specific handlers
            processed_data = data
            for handler in self.handlers[event_type]:
                result = await self._run_processor(handler, event)
                if result:
                    processed_data = result

            # Create processed event
            processing_time = (time.time() - start_time) * 1000
            processed_event = ProcessedEvent(
                event_type=event_type,
                game_id=game_id,
                timestamp=timestamp,
                data=processed_data,
                metadata={
                    "original_type": event.get("type"),
                    "client_id": event.get("_client_id"),
                    "received_at": event.get("_received_at"),
                    "processing_time_ms": processing_time,
                },
                processing_time_ms=processing_time,
            )

            # Run postprocessors
            for postprocessor in self.postprocessors:
                await self._run_processor(postprocessor, processed_event)

            # Update stats
            self.stats["events_processed"] += 1
            self.stats["events_by_type"][event_type.value] += 1

            return processed_event

        except Exception as e:
            logger.error(f"Error processing event: {e}", exc_info=True)
            self.stats["processing_errors"] += 1
            return None

    async def process_batch(self, events: List[Dict]) -> List[ProcessedEvent]:
        """
        Process a batch of events.

        Args:
            events: List of raw event dictionaries

        Returns:
            List of processed events (excludes failed events)
        """
        processed = []

        for event in events:
            result = await self.process_event(event)
            if result:
                processed.append(result)

        logger.debug(f"Processed batch: {len(processed)}/{len(events)} successful")

        return processed

    def _get_event_type(self, event: Dict) -> EventType:
        """
        Determine event type from raw event.

        Args:
            event: Raw event dictionary

        Returns:
            Corresponding EventType enum value
        """
        type_str = event.get("type", "").lower()

        # Try direct mapping
        for event_type in EventType:
            if event_type.value == type_str:
                return event_type

        # Handle special cases or aliases
        type_mapping = {
            "hand": EventType.HAND_PLAYED,
            "joker": EventType.JOKER_TRIGGERED,
            "blind": EventType.BLIND_DEFEATED,
            "shop": EventType.SHOP_ENTERED,
            "purchase": EventType.CARD_PURCHASED,
            "sell": EventType.CARD_SOLD,
            "discard": EventType.CARD_DISCARDED,
            "enhance": EventType.CARD_ENHANCED,
            "round_start": EventType.ROUND_STARTED,
            "round_end": EventType.ROUND_ENDED,
            "game_end": EventType.GAME_OVER,
            "snapshot": EventType.STATE_SNAPSHOT,
        }

        for key, event_type in type_mapping.items():
            if key in type_str:
                return event_type

        logger.warning(f"Unknown event type: {type_str}")
        return EventType.UNKNOWN

    async def _run_processor(self, processor: Callable, data):
        """
        Run a processor function with error handling.

        Args:
            processor: Processor function
            data: Data to process

        Returns:
            Processed data or original data if processor fails
        """
        try:
            if asyncio.iscoroutinefunction(processor):
                return await processor(data)
            else:
                return processor(data)
        except Exception as e:
            logger.error(f"Processor error: {e}", exc_info=True)
            return data

    def get_stats(self) -> Dict:
        """
        Get event processing statistics.

        Returns:
            Dictionary of statistics
        """
        return {
            **self.stats,
            "handlers_registered": {
                event_type.value: len(handlers)
                for event_type, handlers in self.handlers.items()
            },
        }


# Built-in event handlers


async def validate_game_start(event: Dict) -> Dict:
    """Validate and enrich game start events."""
    data = event.get("data", {})

    # Ensure required fields
    required = ["seed", "stake", "deck"]
    for field in required:
        if field not in data:
            raise ValueError(f"Missing required field: {field}")

    # Add defaults
    data.setdefault("starting_money", 4)
    data.setdefault("starting_hands", 4)
    data.setdefault("starting_discards", 3)

    return data


async def calculate_hand_score(event: Dict) -> Dict:
    """Calculate and validate hand scores."""
    data = event.get("data", {})

    # Validate hand data
    if "cards" not in data or not isinstance(data["cards"], list):
        raise ValueError("Invalid hand data: missing or invalid cards")

    # Add calculated fields
    data["card_count"] = len(data["cards"])

    # Ensure score fields
    data.setdefault("base_score", 0)
    data.setdefault("multiplier", 1)
    data["total_score"] = data.get("score", data["base_score"] * data["multiplier"])

    return data


async def track_money_flow(event: Dict) -> Dict:
    """Track money changes in shop events."""
    data = event.get("data", {})
    event_type = EventType(event.get("type"))

    if event_type == EventType.CARD_PURCHASED:
        data["money_change"] = -data.get("cost", 0)
    elif event_type == EventType.CARD_SOLD:
        data["money_change"] = data.get("sell_value", 0)

    return data


# Example handler registration
def create_default_handler() -> EventHandler:
    """Create event handler with default processors."""
    handler = EventHandler()

    # Register type-specific handlers
    handler.register_handler(EventType.GAME_START, validate_game_start)
    handler.register_handler(EventType.HAND_PLAYED, calculate_hand_score)
    handler.register_handler(EventType.CARD_PURCHASED, track_money_flow)
    handler.register_handler(EventType.CARD_SOLD, track_money_flow)

    # Add logging postprocessor
    async def log_event(event: ProcessedEvent):
        logger.debug(
            f"Processed {event.event_type.value} event for game {event.game_id} "
            f"in {event.processing_time_ms:.1f}ms"
        )

    handler.register_postprocessor(log_event)

    return handler


# Import asyncio for async support
import asyncio
