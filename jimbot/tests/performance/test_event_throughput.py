"""
Performance tests for event processing throughput.

Benchmarks the system's ability to handle high-volume event streams.
"""

import asyncio
import time
import json
import statistics
from typing import List, Dict
import pytest
import websockets

from jimbot.mcp.aggregator import EventAggregator
from jimbot.mcp.server import MCPServer


@pytest.mark.performance
class TestEventThroughput:
    """Test event processing performance and throughput."""
    
    @pytest.fixture
    def aggregator(self):
        """Create an event aggregator for testing."""
        return EventAggregator(batch_window_ms=100)
    
    @pytest.mark.benchmark
    def test_aggregator_throughput(self, aggregator, benchmark):
        """Benchmark event aggregation throughput."""
        events = []
        for i in range(1000):
            events.append({
                "type": "game_state",
                "timestamp": time.time(),
                "data": {
                    "ante": i % 8 + 1,
                    "money": i % 100,
                    "event_id": i
                }
            })
        
        async def process_events():
            for event in events:
                await aggregator.add_event(event)
            return await aggregator.process_batch()
        
        # Benchmark the processing
        result = benchmark(lambda: asyncio.run(process_events()))
        
        # Verify results
        assert len(result.events) == 1000
        assert result.latency_ms < 200  # Should process within 200ms
    
    @pytest.mark.asyncio
    async def test_websocket_message_rate(self):
        """Test maximum WebSocket message processing rate."""
        server = MCPServer(host="localhost", port=8898)
        server_task = asyncio.create_task(server.start())
        await asyncio.sleep(0.5)  # Let server start
        
        try:
            messages_sent = 0
            start_time = time.time()
            
            async with websockets.connect("ws://localhost:8898") as websocket:
                # Send messages for 5 seconds
                while time.time() - start_time < 5.0:
                    message = {
                        "type": "test",
                        "id": messages_sent,
                        "timestamp": time.time()
                    }
                    await websocket.send(json.dumps(message))
                    messages_sent += 1
                    
                    # Don't wait for response to maximize throughput
                    if messages_sent % 100 == 0:
                        await asyncio.sleep(0)  # Yield to event loop
            
            elapsed = time.time() - start_time
            rate = messages_sent / elapsed
            
            print(f"\nWebSocket throughput: {rate:.2f} messages/second")
            assert rate > 1000  # Should handle at least 1000 msg/sec
            
        finally:
            server.stop()
            await server_task
    
    def test_event_serialization_performance(self, benchmark):
        """Benchmark event serialization overhead."""
        complex_event = {
            "type": "game_state",
            "timestamp": time.time(),
            "data": {
                "ante": 5,
                "round": 2,
                "money": 150,
                "jokers": ["Joker", "Baseball Card", "DNA", "Blueprint", "Brainstorm"],
                "hand": ["AH", "KH", "QH", "JH", "10H", "9H", "8H", "7H"],
                "deck": [f"{r}{s}" for r in "23456789TJQKA" for s in "HDCS"][:44],
                "shop": {
                    "jokers": ["Fibonacci", "Hack"],
                    "vouchers": ["Blank", "Overstock"],
                    "packs": ["Arcana", "Buffoon", "Spectral"]
                },
                "stats": {
                    "hands_played": 45,
                    "discards_used": 32,
                    "money_earned": 1250,
                    "jokers_bought": 12
                }
            }
        }
        
        # Benchmark serialization
        result = benchmark(lambda: json.dumps(complex_event))
        
        # Should serialize quickly
        assert len(result) > 500  # Complex event should produce substantial JSON
    
    @pytest.mark.asyncio
    async def test_concurrent_aggregator_performance(self):
        """Test aggregator performance under concurrent load."""
        aggregator = EventAggregator(batch_window_ms=50)
        
        async def send_events(start_id: int, count: int) -> List[float]:
            latencies = []
            for i in range(count):
                start = time.perf_counter()
                await aggregator.add_event({
                    "type": "action",
                    "id": start_id + i,
                    "timestamp": time.time()
                })
                latencies.append((time.perf_counter() - start) * 1000)
            return latencies
        
        # Run concurrent senders
        start_time = time.time()
        tasks = [
            send_events(0, 1000),
            send_events(1000, 1000),
            send_events(2000, 1000),
            send_events(3000, 1000)
        ]
        
        all_latencies = await asyncio.gather(*tasks)
        elapsed = time.time() - start_time
        
        # Analyze performance
        flat_latencies = [l for latencies in all_latencies for l in latencies]
        avg_latency = statistics.mean(flat_latencies)
        p95_latency = statistics.quantiles(flat_latencies, n=20)[18]  # 95th percentile
        p99_latency = statistics.quantiles(flat_latencies, n=100)[98]  # 99th percentile
        
        events_per_second = 4000 / elapsed
        
        print(f"\nConcurrent aggregator performance:")
        print(f"  Events per second: {events_per_second:.2f}")
        print(f"  Average latency: {avg_latency:.3f}ms")
        print(f"  P95 latency: {p95_latency:.3f}ms")
        print(f"  P99 latency: {p99_latency:.3f}ms")
        
        # Performance requirements
        assert events_per_second > 5000  # Handle at least 5k events/sec
        assert avg_latency < 1.0  # Sub-millisecond average
        assert p99_latency < 10.0  # 99th percentile under 10ms
    
    @pytest.mark.asyncio
    async def test_memory_efficiency(self):
        """Test memory usage under sustained load."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        aggregator = EventAggregator(batch_window_ms=100, max_batch_size=1000)
        
        # Process many events
        for i in range(10000):
            await aggregator.add_event({
                "type": "test",
                "id": i,
                "data": "x" * 1000  # 1KB payload
            })
            
            if i % 1000 == 0:
                await aggregator.process_batch()
        
        # Final batch
        await aggregator.process_batch()
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        print(f"\nMemory usage:")
        print(f"  Initial: {initial_memory:.2f}MB")
        print(f"  Final: {final_memory:.2f}MB")
        print(f"  Increase: {memory_increase:.2f}MB")
        
        # Should not leak memory excessively
        assert memory_increase < 100  # Less than 100MB increase
    
    def test_batch_optimization(self, benchmark):
        """Test efficiency of event batching."""
        aggregator = EventAggregator(batch_window_ms=100)
        
        async def process_with_batching():
            batches_processed = 0
            
            # Simulate bursty traffic
            for burst in range(10):
                # Send burst of events
                for i in range(100):
                    await aggregator.add_event({"id": burst * 100 + i})
                
                # Process batch
                batch = await aggregator.process_batch()
                if batch.events:
                    batches_processed += 1
                
                # Simulate pause between bursts
                await asyncio.sleep(0.05)
            
            return batches_processed
        
        batches = benchmark(lambda: asyncio.run(process_with_batching()))
        
        # Should batch efficiently
        assert batches <= 15  # Should batch most events together
        print(f"\nBatching efficiency: {1000/batches:.1f} events per batch")