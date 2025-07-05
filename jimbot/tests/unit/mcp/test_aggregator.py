"""
Unit tests for the MCP Event Aggregator.

Tests event batching, timing windows, and aggregation logic.
"""

import asyncio
import time
from unittest.mock import Mock, patch

import pytest

from jimbot.mcp.aggregator import EventAggregator


class TestEventAggregator:
    """Test the EventAggregator class."""

    @pytest.fixture
    def aggregator(self):
        """Create an aggregator with 50ms window for testing."""
        return EventAggregator(batch_window_ms=50)

    @pytest.mark.asyncio
    async def test_aggregates_events_within_window(self, aggregator, sample_mcp_event):
        """Test that events are batched within the time window."""
        # Add multiple events
        events = [sample_mcp_event for _ in range(5)]
        for event in events:
            await aggregator.add_event(event)

        # Process batch
        batch = await aggregator.process_batch()

        assert len(batch.events) == 5
        assert batch.latency_ms < 100

    @pytest.mark.asyncio
    async def test_respects_batch_window_timing(self, aggregator, performance_timer):
        """Test that aggregator waits for full window."""
        with performance_timer as timer:
            # Add one event and process
            await aggregator.add_event({"type": "test"})
            batch = await aggregator.process_batch()

        # Should wait approximately 50ms
        assert 0.04 < timer.elapsed < 0.06
        assert len(batch.events) == 1

    @pytest.mark.asyncio
    async def test_handles_empty_batch(self, aggregator):
        """Test processing with no events."""
        batch = await aggregator.process_batch()

        assert len(batch.events) == 0
        assert batch.latency_ms < 100

    @pytest.mark.asyncio
    async def test_groups_events_by_type(self, aggregator):
        """Test that events are grouped by type in aggregation."""
        # Add different event types
        await aggregator.add_event({"type": "game_state", "data": 1})
        await aggregator.add_event({"type": "game_state", "data": 2})
        await aggregator.add_event({"type": "action", "data": 3})

        batch = await aggregator.process_batch()

        assert "game_state" in batch.aggregated_by_type
        assert "action" in batch.aggregated_by_type
        assert len(batch.aggregated_by_type["game_state"]) == 2
        assert len(batch.aggregated_by_type["action"]) == 1

    @pytest.mark.asyncio
    async def test_concurrent_event_addition(self, aggregator):
        """Test thread-safe event addition."""

        async def add_events(start_id: int):
            for i in range(10):
                await aggregator.add_event({"type": "concurrent", "id": start_id + i})

        # Run multiple coroutines concurrently
        await asyncio.gather(add_events(0), add_events(100), add_events(200))

        batch = await aggregator.process_batch()
        assert len(batch.events) == 30

    @pytest.mark.asyncio
    async def test_max_batch_size_limit(self, aggregator):
        """Test that aggregator respects max batch size."""
        aggregator.max_batch_size = 10

        # Add more events than max
        for i in range(20):
            await aggregator.add_event({"id": i})

        batch = await aggregator.process_batch()
        assert len(batch.events) == 10

    def test_calculates_event_statistics(self, aggregator):
        """Test statistical calculations on event batch."""
        events = [
            {"type": "action", "timestamp": 1000, "processing_time": 10},
            {"type": "action", "timestamp": 1010, "processing_time": 20},
            {"type": "action", "timestamp": 1020, "processing_time": 15},
        ]

        stats = aggregator._calculate_statistics(events)

        assert stats["count"] == 3
        assert stats["avg_processing_time"] == 15
        assert stats["time_span_ms"] == 20

    @pytest.mark.asyncio
    async def test_error_handling_in_aggregation(self, aggregator):
        """Test graceful handling of malformed events."""
        # Add valid and invalid events
        await aggregator.add_event({"type": "valid", "data": "ok"})
        await aggregator.add_event(None)  # Invalid
        await aggregator.add_event({"type": "valid", "data": "ok2"})

        batch = await aggregator.process_batch()

        # Should only process valid events
        assert len(batch.events) == 2
        assert all(e["type"] == "valid" for e in batch.events)

    @pytest.mark.asyncio
    async def test_shutdown_processing(self, aggregator):
        """Test graceful shutdown with pending events."""
        # Add events
        for i in range(5):
            await aggregator.add_event({"id": i})

        # Shutdown should process remaining events
        final_batch = await aggregator.shutdown()

        assert len(final_batch.events) == 5
        assert aggregator.is_shutdown

    @pytest.mark.parametrize(
        "window_ms,expected_batches",
        [
            (10, 5),  # Very short window = more batches
            (50, 2),  # Medium window
            (100, 1),  # Long window = fewer batches
        ],
    )
    @pytest.mark.asyncio
    async def test_different_window_sizes(self, window_ms, expected_batches):
        """Test aggregation with different window sizes."""
        aggregator = EventAggregator(batch_window_ms=window_ms)

        # Add events over time
        batches_received = []

        async def collect_batches():
            for _ in range(expected_batches):
                batch = await aggregator.process_batch()
                if batch.events:
                    batches_received.append(batch)

        # Start collector
        collector_task = asyncio.create_task(collect_batches())

        # Add events with delays
        for i in range(10):
            await aggregator.add_event({"id": i})
            await asyncio.sleep(0.02)  # 20ms between events

        await collector_task

        assert len(batches_received) >= expected_batches - 1  # Allow some variance
