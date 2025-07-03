"""
Event aggregation implementation with <100ms batch processing.

This module implements the core event aggregation logic that batches
incoming events in 100ms windows for efficient processing.
"""

import asyncio
import logging
import time
from collections import deque
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class BatchStats:
    """Statistics for a processed batch."""

    batch_id: str
    event_count: int
    processing_time_ms: float
    queue_size_at_start: int
    timestamp: float


class EventAggregator:
    """
    High-performance event aggregator with <100ms batch processing.

    This aggregator collects events from the MCP server and processes them
    in configurable time windows (default 100ms) to achieve optimal throughput
    while maintaining low latency.

    Attributes:
        batch_window_ms: Batch window duration in milliseconds
        max_queue_size: Maximum event queue size
        max_batch_size: Maximum events per batch
        event_queue: Async queue for incoming events
        batch_handler: Callback for processing batches
        stats: Recent batch statistics
    """

    def __init__(
        self,
        batch_window_ms: int = 100,
        max_queue_size: int = 10000,
        max_batch_size: int = 1000,
    ):
        """
        Initialize event aggregator.

        Args:
            batch_window_ms: Duration of batch window in milliseconds
            max_queue_size: Maximum size of event queue
            max_batch_size: Maximum number of events per batch
        """
        self.batch_window = batch_window_ms / 1000.0  # Convert to seconds
        self.max_batch_size = max_batch_size
        self.event_queue = asyncio.Queue(maxsize=max_queue_size)
        self.batch_handler: Optional[Callable] = None
        self.delivery_handlers: List[Callable] = []
        self._running = False
        self._processor_task: Optional[asyncio.Task] = None
        self._batch_count = 0
        self.stats = deque(maxlen=100)  # Keep last 100 batch stats

        logger.info(
            f"EventAggregator initialized: window={batch_window_ms}ms, "
            f"max_queue={max_queue_size}, max_batch={max_batch_size}"
        )

    async def start(self):
        """Start the event aggregator."""
        if self._running:
            logger.warning("Aggregator already running")
            return

        self._running = True
        self._processor_task = asyncio.create_task(self._process_batches())
        logger.info("Event aggregator started")

    async def stop(self):
        """Stop the event aggregator."""
        if not self._running:
            return

        logger.info("Stopping event aggregator...")
        self._running = False

        # Process remaining events
        if not self.event_queue.empty():
            events = []
            while not self.event_queue.empty():
                try:
                    events.append(self.event_queue.get_nowait())
                except asyncio.QueueEmpty:
                    break

            if events:
                await self._process_batch(events)

        # Cancel processor task
        if self._processor_task:
            self._processor_task.cancel()
            try:
                await self._processor_task
            except asyncio.CancelledError:
                pass

        logger.info("Event aggregator stopped")

    async def add_event(self, event: Dict) -> bool:
        """
        Add an event to the aggregation queue.

        Args:
            event: Event data dictionary

        Returns:
            True if event was added, False if queue is full
        """
        try:
            self.event_queue.put_nowait(event)
            return True
        except asyncio.QueueFull:
            logger.warning(
                f"Event queue full (size={self.event_queue.qsize()}), " "dropping event"
            )
            return False

    def set_batch_handler(self, handler: Callable[[List[Dict]], None]):
        """
        Set the batch processing handler.

        Args:
            handler: Async function to process event batches
        """
        self.batch_handler = handler

    def add_delivery_handler(self, handler: Callable[[List[Dict]], None]):
        """
        Add a delivery handler for processed batches.

        Multiple handlers can be added for different destinations
        (e.g., Ray, Memgraph, monitoring).

        Args:
            handler: Async function to deliver events
        """
        self.delivery_handlers.append(handler)

    async def _process_batches(self):
        """
        Main batch processing loop.

        This method runs continuously while the aggregator is active,
        collecting events in time windows and processing them in batches.
        """
        logger.info("Batch processor started")

        while self._running:
            try:
                await self._process_single_batch()
            except Exception as e:
                logger.error(f"Error in batch processor: {e}", exc_info=True)
                # Continue processing after error
                await asyncio.sleep(0.1)

        logger.info("Batch processor stopped")

    async def _process_single_batch(self):
        """Process a single batch of events."""
        batch_start = time.time()
        events = []
        queue_size_start = self.event_queue.qsize()

        # Collect events for batch_window duration
        while (time.time() - batch_start) < self.batch_window:
            remaining = self.batch_window - (time.time() - batch_start)

            if remaining <= 0:
                break

            try:
                # Wait for event or timeout
                event = await asyncio.wait_for(
                    self.event_queue.get(), timeout=remaining
                )
                events.append(event)

                # Check batch size limit
                if len(events) >= self.max_batch_size:
                    logger.debug(f"Batch size limit reached ({self.max_batch_size})")
                    break

            except asyncio.TimeoutError:
                # Normal timeout, end of batch window
                break
            except Exception as e:
                logger.error(f"Error collecting event: {e}")

        # Process batch if we have events
        if events:
            # Process without blocking next batch window
            asyncio.create_task(self._process_batch(events))

            # Record statistics
            processing_time = (time.time() - batch_start) * 1000
            self._batch_count += 1

            stats = BatchStats(
                batch_id=f"batch_{self._batch_count}",
                event_count=len(events),
                processing_time_ms=processing_time,
                queue_size_at_start=queue_size_start,
                timestamp=batch_start,
            )
            self.stats.append(stats)

            # Log performance warnings
            if processing_time > self.batch_window * 1000 * 1.5:
                logger.warning(
                    f"Batch processing exceeded target window: "
                    f"{processing_time:.1f}ms > {self.batch_window * 1000}ms"
                )

    async def _process_batch(self, events: List[Dict]):
        """
        Process a batch of events.

        Args:
            events: List of event dictionaries
        """
        process_start = time.time()

        try:
            # Run batch handler if set
            if self.batch_handler:
                await self._run_handler(self.batch_handler, events)

            # Run all delivery handlers
            if self.delivery_handlers:
                await asyncio.gather(
                    *[
                        self._run_handler(handler, events)
                        for handler in self.delivery_handlers
                    ],
                    return_exceptions=True,
                )

            # Log batch completion
            process_time = (time.time() - process_start) * 1000
            logger.debug(
                f"Processed batch of {len(events)} events in {process_time:.1f}ms"
            )

        except Exception as e:
            logger.error(
                f"Error processing batch of {len(events)} events: {e}", exc_info=True
            )

    async def _run_handler(self, handler: Callable, events: List[Dict]):
        """
        Run a handler function with proper error handling.

        Args:
            handler: Handler function to run
            events: Events to process
        """
        try:
            if asyncio.iscoroutinefunction(handler):
                await handler(events)
            else:
                # Run sync handler in executor
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, handler, events)
        except Exception as e:
            logger.error(f"Handler error: {e}", exc_info=True)

    def get_stats(self) -> Dict:
        """
        Get aggregator statistics.

        Returns:
            Dictionary of current statistics
        """
        if not self.stats:
            return {
                "batch_count": 0,
                "avg_batch_size": 0,
                "avg_processing_time_ms": 0,
                "current_queue_size": self.event_queue.qsize(),
            }

        recent_stats = list(self.stats)

        return {
            "batch_count": self._batch_count,
            "avg_batch_size": sum(s.event_count for s in recent_stats)
            / len(recent_stats),
            "avg_processing_time_ms": sum(s.processing_time_ms for s in recent_stats)
            / len(recent_stats),
            "max_processing_time_ms": max(s.processing_time_ms for s in recent_stats),
            "current_queue_size": self.event_queue.qsize(),
            "recent_batches": len(recent_stats),
        }


# Example usage for testing
async def example_batch_handler(events: List[Dict]):
    """Example batch handler for testing."""
    logger.info(f"Processing batch of {len(events)} events")
    # Simulate processing
    await asyncio.sleep(0.01)


if __name__ == "__main__":
    # Test aggregator
    async def test():
        # Configure logging
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )

        # Create aggregator
        aggregator = EventAggregator(batch_window_ms=100)
        aggregator.set_batch_handler(example_batch_handler)

        # Start aggregator
        await aggregator.start()

        # Send test events
        for i in range(100):
            event = {"type": "test", "id": i, "timestamp": time.time()}
            await aggregator.add_event(event)
            await asyncio.sleep(0.01)  # 10ms between events

        # Wait a bit
        await asyncio.sleep(1)

        # Print stats
        stats = aggregator.get_stats()
        print(f"Aggregator stats: {stats}")

        # Stop aggregator
        await aggregator.stop()

    asyncio.run(test())
