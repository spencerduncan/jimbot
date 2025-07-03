"""Metrics Collector Module

Collects and exports metrics for all components.
"""

import asyncio
import logging
import time
from collections import defaultdict
from typing import Dict, List

logger = logging.getLogger(__name__)


class MetricsCollector:
    """Collects metrics from all components"""

    def __init__(self, flush_interval: float = 1.0):
        self.flush_interval = flush_interval
        self.counters: Dict[str, int] = defaultdict(int)
        self.gauges: Dict[str, float] = {}
        self.histograms: Dict[str, List[float]] = defaultdict(list)
        self.last_flush = time.time()
        self._flush_task = None

    async def start(self):
        """Start metrics collection"""
        self._flush_task = asyncio.create_task(self._flush_loop())

    async def stop(self):
        """Stop metrics collection"""
        if self._flush_task:
            self._flush_task.cancel()

    def increment_counter(
        self, name: str, value: int = 1, labels: Dict[str, str] = None
    ):
        """Increment a counter metric"""
        key = self._make_key(name, labels)
        self.counters[key] += value

    def set_gauge(self, name: str, value: float, labels: Dict[str, str] = None):
        """Set a gauge metric"""
        key = self._make_key(name, labels)
        self.gauges[key] = value

    def record_histogram(self, name: str, value: float, labels: Dict[str, str] = None):
        """Record a histogram value"""
        key = self._make_key(name, labels)
        self.histograms[key].append(value)

    async def _flush_loop(self):
        """Periodically flush metrics"""
        while True:
            await asyncio.sleep(self.flush_interval)
            await self.flush()

    async def flush(self):
        """Flush metrics to storage"""
        # TODO: Send to QuestDB
        logger.debug(
            f"Flushing {len(self.counters)} counters, "
            f"{len(self.gauges)} gauges, "
            f"{len(self.histograms)} histograms"
        )

        # Reset histograms after flush
        self.histograms.clear()
        self.last_flush = time.time()

    def _make_key(self, name: str, labels: Dict[str, str] = None) -> str:
        """Create metric key with labels"""
        if not labels:
            return name
        label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"
