"""
Metric collection service for JimBot performance monitoring.

This module handles the collection, batching, and storage of time-series metrics
in QuestDB. It subscribes to events from the Event Bus and transforms them into
metrics for analysis.
"""

import asyncio
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from collections import defaultdict
import logging

from jimbot.shared.event_bus import EventBus, Event
from jimbot.shared.interfaces.analytics_pb2 import MetricData, MetricBatch

logger = logging.getLogger(__name__)


@dataclass
class Metric:
    """Represents a single metric data point."""
    name: str
    value: float
    timestamp: int  # microseconds since epoch
    tags: Dict[str, str]


class MetricCollector:
    """
    Collects and batches metrics for efficient storage in QuestDB.
    
    Features:
    - Subscribes to Event Bus for game and system events
    - Batches metrics in 1-second windows for efficiency
    - Handles multiple metric types and tags
    - Implements circuit breaker for memory protection
    """
    
    def __init__(self, 
                 event_bus: EventBus,
                 questdb_host: str = "localhost",
                 questdb_port: int = 8812,
                 batch_window_seconds: float = 1.0,
                 max_batch_size: int = 1000):
        """
        Initialize the metric collector.
        
        Args:
            event_bus: The central event bus for subscriptions
            questdb_host: QuestDB host address
            questdb_port: QuestDB Postgres wire protocol port
            batch_window_seconds: Time window for batching metrics
            max_batch_size: Maximum metrics per batch
        """
        self.event_bus = event_bus
        self.questdb_host = questdb_host
        self.questdb_port = questdb_port
        self.batch_window = batch_window_seconds
        self.max_batch_size = max_batch_size
        
        # Metric batching
        self.metric_buffer: List[Metric] = []
        self.buffer_lock = asyncio.Lock()
        
        # Metric definitions
        self.metric_definitions = self._define_metrics()
        
        # Performance tracking
        self.metrics_collected = 0
        self.batches_sent = 0
        self.last_batch_time = time.time()
        
    def _define_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Define the metrics to collect from various events."""
        return {
            # System metrics
            "decision_latency": {
                "event_types": ["DecisionMade"],
                "extractor": lambda e: e.data.get("latency_ms"),
                "tags": ["component", "game_id", "round"]
            },
            "memory_usage": {
                "event_types": ["SystemMetrics"],
                "extractor": lambda e: e.data.get("memory_mb"),
                "tags": ["component", "allocation_type"]
            },
            "gpu_utilization": {
                "event_types": ["SystemMetrics"],
                "extractor": lambda e: e.data.get("gpu_percent"),
                "tags": ["device", "operation"]
            },
            
            # Game metrics
            "game_score": {
                "event_types": ["GameEnded"],
                "extractor": lambda e: e.data.get("final_score"),
                "tags": ["win_loss", "rounds_survived", "strategy"]
            },
            "round_score": {
                "event_types": ["RoundCompleted"],
                "extractor": lambda e: e.data.get("score"),
                "tags": ["game_id", "round", "blind_name"]
            },
            "joker_value": {
                "event_types": ["JokerPurchased"],
                "extractor": lambda e: e.data.get("perceived_value"),
                "tags": ["joker_name", "game_id", "round"]
            },
            
            # Learning metrics
            "ppo_loss": {
                "event_types": ["TrainingStep"],
                "extractor": lambda e: e.data.get("ppo_loss"),
                "tags": ["model_version", "training_iteration"]
            },
            "exploration_rate": {
                "event_types": ["DecisionMade"],
                "extractor": lambda e: e.data.get("exploration_prob"),
                "tags": ["game_id", "strategy_type"]
            },
            
            # Integration metrics
            "claude_latency": {
                "event_types": ["ClaudeQuery"],
                "extractor": lambda e: e.data.get("response_time_ms"),
                "tags": ["query_type", "cache_hit"]
            },
            "memgraph_query_time": {
                "event_types": ["MemgraphQuery"],
                "extractor": lambda e: e.data.get("query_time_ms"),
                "tags": ["query_type", "result_count"]
            }
        }
    
    async def start(self):
        """Start the metric collector service."""
        logger.info("Starting metric collector service")
        
        # Subscribe to relevant events
        await self._subscribe_to_events()
        
        # Start the batch processor
        asyncio.create_task(self._batch_processor())
        
        logger.info("Metric collector service started")
    
    async def _subscribe_to_events(self):
        """Subscribe to all events that generate metrics."""
        event_types = set()
        for metric_def in self.metric_definitions.values():
            event_types.update(metric_def["event_types"])
        
        for event_type in event_types:
            await self.event_bus.subscribe(event_type, self._handle_event)
            
        logger.info(f"Subscribed to {len(event_types)} event types")
    
    async def _handle_event(self, event: Event):
        """Process an event and extract relevant metrics."""
        try:
            for metric_name, definition in self.metric_definitions.items():
                if event.event_type in definition["event_types"]:
                    value = definition["extractor"](event)
                    if value is not None:
                        tags = self._extract_tags(event, definition["tags"])
                        await self.record_metric(metric_name, value, tags)
                        
        except Exception as e:
            logger.error(f"Error processing event {event.event_type}: {e}")
    
    def _extract_tags(self, event: Event, tag_names: List[str]) -> Dict[str, str]:
        """Extract tags from an event based on tag definitions."""
        tags = {}
        for tag_name in tag_names:
            if tag_name in event.data:
                tags[tag_name] = str(event.data[tag_name])
            elif hasattr(event, tag_name):
                tags[tag_name] = str(getattr(event, tag_name))
        return tags
    
    async def record_metric(self, name: str, value: float, 
                          tags: Optional[Dict[str, str]] = None):
        """
        Record a metric value.
        
        Args:
            name: Metric name
            value: Metric value
            tags: Optional tags for the metric
        """
        metric = Metric(
            name=name,
            value=value,
            timestamp=time.time_ns() // 1000,  # microseconds
            tags=tags or {}
        )
        
        async with self.buffer_lock:
            self.metric_buffer.append(metric)
            self.metrics_collected += 1
            
            # Force batch if buffer is full
            if len(self.metric_buffer) >= self.max_batch_size:
                await self._send_batch()
    
    async def record_metric_at(self, name: str, value: float, 
                             timestamp: datetime,
                             tags: Optional[Dict[str, str]] = None):
        """Record a metric with a specific timestamp."""
        metric = Metric(
            name=name,
            value=value,
            timestamp=int(timestamp.timestamp() * 1_000_000),  # microseconds
            tags=tags or {}
        )
        
        async with self.buffer_lock:
            self.metric_buffer.append(metric)
            self.metrics_collected += 1
    
    async def _batch_processor(self):
        """Background task that periodically sends metric batches."""
        while True:
            await asyncio.sleep(self.batch_window)
            await self._send_batch()
    
    async def _send_batch(self):
        """Send the current batch of metrics to QuestDB."""
        async with self.buffer_lock:
            if not self.metric_buffer:
                return
                
            batch = self.metric_buffer[:]
            self.metric_buffer.clear()
        
        try:
            await self._write_to_questdb(batch)
            self.batches_sent += 1
            self.last_batch_time = time.time()
            
            logger.debug(f"Sent batch of {len(batch)} metrics to QuestDB")
            
        except Exception as e:
            logger.error(f"Failed to send metric batch: {e}")
            # Re-add metrics to buffer on failure
            async with self.buffer_lock:
                self.metric_buffer.extend(batch)
    
    async def _write_to_questdb(self, metrics: List[Metric]):
        """Write metrics to QuestDB using Postgres wire protocol."""
        # TODO: Implement actual QuestDB connection
        # This is a placeholder for the actual implementation
        pass
    
    def get_stats(self) -> Dict[str, Any]:
        """Get collector statistics."""
        return {
            "metrics_collected": self.metrics_collected,
            "batches_sent": self.batches_sent,
            "current_buffer_size": len(self.metric_buffer),
            "last_batch_time": self.last_batch_time,
            "metrics_per_second": self.metrics_collected / (time.time() - self.last_batch_time)
            if time.time() > self.last_batch_time else 0
        }


class MetricAggregator:
    """
    Aggregates metrics over time windows for efficient storage and querying.
    
    Features:
    - 1-minute, 1-hour, and 1-day aggregations
    - Min/max/avg/count statistics
    - Percentile calculations
    - Automatic old data cleanup
    """
    
    def __init__(self, questdb_client):
        self.questdb_client = questdb_client
        self.aggregation_intervals = {
            "1m": 60,
            "1h": 3600,
            "1d": 86400
        }
    
    async def aggregate_metrics(self):
        """Run metric aggregation for all intervals."""
        for interval_name, seconds in self.aggregation_intervals.items():
            await self._aggregate_interval(interval_name, seconds)
    
    async def _aggregate_interval(self, interval_name: str, seconds: int):
        """Aggregate metrics for a specific time interval."""
        # TODO: Implement aggregation logic
        pass