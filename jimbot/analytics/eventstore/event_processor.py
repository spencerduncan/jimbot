"""
Event processing and storage service for game history and replay functionality.

This module handles the storage of game events in EventStoreDB for complete
game history, replay capability, and advanced analysis.
"""

import asyncio
import uuid
from datetime import datetime
from typing import Dict, List, Any, AsyncIterator
from dataclasses import dataclass
from enum import Enum
import logging

from jimbot.shared.event_bus import EventBus, Event

logger = logging.getLogger(__name__)


class EventCategory(Enum):
    """Categories for organizing events in EventStore."""

    GAME = "game"
    SYSTEM = "system"
    TRAINING = "training"
    DECISION = "decision"


@dataclass
class StoredEvent:
    """Represents an event to be stored in EventStoreDB."""

    event_id: str
    event_type: str
    stream_name: str
    data: Dict[str, Any]
    metadata: Dict[str, Any]
    timestamp: datetime


class EventProcessor:
    """
    Processes and stores events in EventStoreDB for game history and analysis.

    Features:
    - Stores complete game histories for replay
    - Maintains system event logs
    - Supports event projections for analysis
    - Handles event versioning and schema evolution
    """

    def __init__(
        self,
        event_bus: EventBus,
        eventstore_host: str = "localhost",
        eventstore_port: int = 2113,
        batch_size: int = 100,
    ):
        """
        Initialize the event processor.

        Args:
            event_bus: The central event bus for subscriptions
            eventstore_host: EventStoreDB host address
            eventstore_port: EventStoreDB HTTP port
            batch_size: Number of events to batch before writing
        """
        self.event_bus = event_bus
        self.eventstore_host = eventstore_host
        self.eventstore_port = eventstore_port
        self.batch_size = batch_size

        # Event batching
        self.event_queue: asyncio.Queue = asyncio.Queue()
        self.processed_count = 0

        # Event schema definitions
        self.event_schemas = self._define_event_schemas()

        # Game tracking
        self.active_games: Dict[str, Dict[str, Any]] = {}

    def _define_event_schemas(self) -> Dict[str, Dict[str, Any]]:
        """Define schemas for different event types."""
        return {
            # Game lifecycle events
            "GameStarted": {
                "category": EventCategory.GAME,
                "required_fields": ["game_id", "seed", "stake", "deck"],
                "stream_prefix": "game-",
            },
            "GameEnded": {
                "category": EventCategory.GAME,
                "required_fields": [
                    "game_id",
                    "final_score",
                    "rounds_survived",
                    "outcome",
                ],
                "stream_prefix": "game-",
            },
            # Round events
            "RoundStarted": {
                "category": EventCategory.GAME,
                "required_fields": ["game_id", "round", "blind_name", "blind_chips"],
                "stream_prefix": "game-",
            },
            "RoundCompleted": {
                "category": EventCategory.GAME,
                "required_fields": ["game_id", "round", "score", "money_earned"],
                "stream_prefix": "game-",
            },
            # Decision events
            "DecisionMade": {
                "category": EventCategory.DECISION,
                "required_fields": [
                    "game_id",
                    "decision_type",
                    "action",
                    "state_summary",
                ],
                "stream_prefix": "decision-",
            },
            "JokerPurchased": {
                "category": EventCategory.DECISION,
                "required_fields": ["game_id", "joker_name", "cost", "slot_position"],
                "stream_prefix": "decision-",
            },
            "HandPlayed": {
                "category": EventCategory.GAME,
                "required_fields": ["game_id", "cards_played", "hand_type", "score"],
                "stream_prefix": "game-",
            },
            # System events
            "ModelCheckpoint": {
                "category": EventCategory.SYSTEM,
                "required_fields": [
                    "model_version",
                    "training_iteration",
                    "performance_metrics",
                ],
                "stream_prefix": "system-",
            },
            "ComponentError": {
                "category": EventCategory.SYSTEM,
                "required_fields": [
                    "component",
                    "error_type",
                    "error_message",
                    "recovery_action",
                ],
                "stream_prefix": "system-",
            },
            # Training events
            "TrainingStep": {
                "category": EventCategory.TRAINING,
                "required_fields": [
                    "iteration",
                    "loss",
                    "learning_rate",
                    "samples_processed",
                ],
                "stream_prefix": "training-",
            },
            "StrategyUpdate": {
                "category": EventCategory.TRAINING,
                "required_fields": [
                    "old_strategy",
                    "new_strategy",
                    "reason",
                    "performance_delta",
                ],
                "stream_prefix": "training-",
            },
        }

    async def start(self):
        """Start the event processor service."""
        logger.info("Starting event processor service")

        # Subscribe to relevant events
        await self._subscribe_to_events()

        # Start the batch processor
        asyncio.create_task(self._batch_processor())

        # Start the game tracker
        asyncio.create_task(self._game_tracker())

        logger.info("Event processor service started")

    async def _subscribe_to_events(self):
        """Subscribe to all events that should be stored."""
        for event_type in self.event_schemas.keys():
            await self.event_bus.subscribe(event_type, self._handle_event)

        logger.info(f"Subscribed to {len(self.event_schemas)} event types")

    async def _handle_event(self, event: Event):
        """Process an incoming event."""
        try:
            # Validate event against schema
            schema = self.event_schemas.get(event.event_type)
            if not schema:
                logger.warning(f"No schema defined for event type: {event.event_type}")
                return

            # Validate required fields
            for field in schema["required_fields"]:
                if field not in event.data:
                    logger.error(
                        f"Missing required field '{field}' in {event.event_type}"
                    )
                    return

            # Create stored event
            stored_event = StoredEvent(
                event_id=str(uuid.uuid4()),
                event_type=event.event_type,
                stream_name=self._get_stream_name(event, schema),
                data=event.data,
                metadata={
                    "timestamp": event.timestamp.isoformat(),
                    "source": event.source,
                    "correlation_id": getattr(event, "correlation_id", None),
                    "category": schema["category"].value,
                },
                timestamp=event.timestamp,
            )

            # Queue for batch processing
            await self.event_queue.put(stored_event)

            # Update game tracking if applicable
            if schema["category"] == EventCategory.GAME:
                await self._update_game_tracking(event)

        except Exception as e:
            logger.error(f"Error processing event {event.event_type}: {e}")

    def _get_stream_name(self, event: Event, schema: Dict[str, Any]) -> str:
        """Generate the stream name for an event."""
        prefix = schema["stream_prefix"]

        # Use game_id for game-related streams
        if "game_id" in event.data:
            return f"{prefix}{event.data['game_id']}"

        # Use date for system streams
        elif schema["category"] == EventCategory.SYSTEM:
            return f"{prefix}{datetime.now().strftime('%Y-%m-%d')}"

        # Use model version for training streams
        elif "model_version" in event.data:
            return f"{prefix}{event.data['model_version']}"

        # Default to category
        return f"{prefix}default"

    async def _update_game_tracking(self, event: Event):
        """Update active game tracking."""
        game_id = event.data.get("game_id")
        if not game_id:
            return

        if event.event_type == "GameStarted":
            self.active_games[game_id] = {
                "start_time": event.timestamp,
                "events": 1,
                "last_event": event.timestamp,
            }
        elif game_id in self.active_games:
            self.active_games[game_id]["events"] += 1
            self.active_games[game_id]["last_event"] = event.timestamp

            if event.event_type == "GameEnded":
                # Archive game info
                game_info = self.active_games.pop(game_id)
                duration = (event.timestamp - game_info["start_time"]).total_seconds()
                logger.info(
                    f"Game {game_id} completed: {game_info['events']} events, "
                    f"{duration:.1f} seconds"
                )

    async def _batch_processor(self):
        """Process events in batches for efficient storage."""
        batch: List[StoredEvent] = []

        while True:
            try:
                # Wait for events with timeout
                timeout = 1.0  # 1 second batch window
                deadline = asyncio.get_event_loop().time() + timeout

                while len(batch) < self.batch_size:
                    remaining = deadline - asyncio.get_event_loop().time()
                    if remaining <= 0:
                        break

                    try:
                        event = await asyncio.wait_for(
                            self.event_queue.get(), timeout=remaining
                        )
                        batch.append(event)
                    except asyncio.TimeoutError:
                        break

                # Process batch if we have events
                if batch:
                    await self._write_batch(batch)
                    self.processed_count += len(batch)
                    batch.clear()

            except Exception as e:
                logger.error(f"Error in batch processor: {e}")
                await asyncio.sleep(1)

    async def _write_batch(self, events: List[StoredEvent]):
        """Write a batch of events to EventStoreDB."""
        # TODO: Implement actual EventStoreDB connection
        # This is a placeholder for the actual implementation
        logger.debug(f"Writing batch of {len(events)} events to EventStoreDB")

    async def store_event(
        self, stream: str, event_type: str, data: Dict[str, Any]
    ) -> str:
        """
        Store a single event directly.

        Args:
            stream: The stream name
            event_type: The event type
            data: The event data

        Returns:
            The event ID
        """
        event_id = str(uuid.uuid4())
        stored_event = StoredEvent(
            event_id=event_id,
            event_type=event_type,
            stream_name=stream,
            data=data,
            metadata={"timestamp": datetime.utcnow().isoformat(), "source": "direct"},
            timestamp=datetime.utcnow(),
        )

        await self._write_batch([stored_event])
        return event_id

    async def read_stream(
        self, stream_name: str, start_position: int = 0, count: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Read events from a stream.

        Args:
            stream_name: The stream to read from
            start_position: Starting position in the stream
            count: Maximum number of events to read

        Returns:
            List of events from the stream
        """
        # TODO: Implement actual EventStoreDB read
        return []

    async def read_game_history(self, game_id: str) -> List[Dict[str, Any]]:
        """
        Read the complete history of a game.

        Args:
            game_id: The game ID to read

        Returns:
            List of all events for the game in chronological order
        """
        events = []

        # Read from game stream
        game_events = await self.read_stream(f"game-{game_id}")
        events.extend(game_events)

        # Read from decision stream
        decision_events = await self.read_stream(f"decision-{game_id}")
        events.extend(decision_events)

        # Sort by timestamp
        events.sort(key=lambda e: e.get("metadata", {}).get("timestamp", ""))

        return events

    async def _game_tracker(self):
        """Monitor active games and clean up stale entries."""
        while True:
            await asyncio.sleep(60)  # Check every minute

            now = datetime.utcnow()
            stale_games = []

            for game_id, info in self.active_games.items():
                # Consider game stale if no events for 5 minutes
                if (now - info["last_event"]).total_seconds() > 300:
                    stale_games.append(game_id)

            for game_id in stale_games:
                logger.warning(f"Removing stale game {game_id} from tracking")
                self.active_games.pop(game_id)

    def get_stats(self) -> Dict[str, Any]:
        """Get processor statistics."""
        return {
            "events_processed": self.processed_count,
            "queue_size": self.event_queue.qsize(),
            "active_games": len(self.active_games),
            "active_game_ids": list(self.active_games.keys()),
        }


class GameReplayer:
    """
    Provides game replay functionality using stored events.

    Features:
    - Step through game events
    - Reconstruct game state at any point
    - Analyze decision paths
    - Generate replay visualizations
    """

    def __init__(self, event_processor: EventProcessor):
        self.event_processor = event_processor

    async def replay_game(self, game_id: str) -> AsyncIterator[Dict[str, Any]]:
        """
        Replay a game by yielding events in sequence.

        Args:
            game_id: The game to replay

        Yields:
            Game events with reconstructed state
        """
        events = await self.event_processor.read_game_history(game_id)

        game_state = {
            "money": 4,
            "hands": 4,
            "discards": 3,
            "jokers": [],
            "round": 1,
            "score": 0,
        }

        for event in events:
            # Update game state based on event
            game_state = self._update_game_state(game_state, event)

            # Yield event with current state
            yield {
                "event": event,
                "state": game_state.copy(),
                "timestamp": event.get("metadata", {}).get("timestamp"),
            }

    def _update_game_state(
        self, state: Dict[str, Any], event: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update game state based on an event."""
        event_type = event.get("event_type")
        data = event.get("data", {})

        if event_type == "RoundStarted":
            state["round"] = data.get("round", state["round"])

        elif event_type == "JokerPurchased":
            state["jokers"].append(
                {"name": data.get("joker_name"), "position": data.get("slot_position")}
            )
            state["money"] -= data.get("cost", 0)

        elif event_type == "RoundCompleted":
            state["score"] = data.get("score", state["score"])
            state["money"] += data.get("money_earned", 0)

        return state
