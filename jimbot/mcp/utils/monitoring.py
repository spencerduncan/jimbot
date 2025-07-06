"""
Monitoring and metrics collection for MCP server.

Provides performance metrics and monitoring capabilities.
"""

import time
from collections import defaultdict, deque
from datetime import datetime
from typing import Any, Dict, List, Optional, Union


class MetricsCollector:
    """
    Collects and stores performance metrics for the MCP server.
    
    Provides counters, gauges, and histograms for monitoring server performance
    and detecting potential issues.
    """
    
    def __init__(self, history_size: int = 1000):
        """
        Initialize metrics collector.
        
        Args:
            history_size: Maximum number of historical values to keep per metric
        """
        self.history_size = history_size
        self._counters: Dict[str, float] = defaultdict(float)
        self._gauges: Dict[str, float] = defaultdict(float)
        self._histograms: Dict[str, deque] = defaultdict(lambda: deque(maxlen=history_size))
        self._timestamps: Dict[str, float] = {}
        
    def increment(self, name: str, value: float = 1.0, labels: Optional[Dict[str, str]] = None):
        """
        Increment a counter metric.
        
        Args:
            name: Metric name
            value: Amount to increment by
            labels: Optional labels for metric categorization
        """
        key = self._make_key(name, labels)
        self._counters[key] += value
        self._timestamps[key] = time.time()
        
    def gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """
        Set a gauge metric value.
        
        Args:
            name: Metric name
            value: Current value
            labels: Optional labels for metric categorization
        """
        key = self._make_key(name, labels)
        self._gauges[key] = value
        self._timestamps[key] = time.time()
        
    def histogram(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """
        Record a value in a histogram metric.
        
        Args:
            name: Metric name
            value: Value to record
            labels: Optional labels for metric categorization
        """
        key = self._make_key(name, labels)
        self._histograms[key].append(value)
        self._timestamps[key] = time.time()
        
    def get_counter(self, name: str, labels: Optional[Dict[str, str]] = None) -> float:
        """Get current counter value."""
        key = self._make_key(name, labels)
        return self._counters.get(key, 0.0)
        
    def get_gauge(self, name: str, labels: Optional[Dict[str, str]] = None) -> float:
        """Get current gauge value."""
        key = self._make_key(name, labels)
        return self._gauges.get(key, 0.0)
        
    def get_histogram_stats(self, name: str, labels: Optional[Dict[str, str]] = None) -> Dict[str, float]:
        """
        Get statistical summary of histogram values.
        
        Returns:
            Dictionary with min, max, mean, p50, p95, p99 values
        """
        key = self._make_key(name, labels)
        values = list(self._histograms.get(key, []))
        
        if not values:
            return {
                "count": 0,
                "min": 0.0,
                "max": 0.0,
                "mean": 0.0,
                "p50": 0.0,
                "p95": 0.0,
                "p99": 0.0
            }
            
        values.sort()
        count = len(values)
        
        return {
            "count": count,
            "min": values[0],
            "max": values[-1],
            "mean": sum(values) / count,
            "p50": self._percentile(values, 0.50),
            "p95": self._percentile(values, 0.95),
            "p99": self._percentile(values, 0.99)
        }
        
    def get_all_metrics(self) -> Dict[str, Any]:
        """
        Get all collected metrics.
        
        Returns:
            Dictionary containing all counters, gauges, and histogram stats
        """
        metrics = {
            "timestamp": datetime.utcnow().isoformat(),
            "counters": dict(self._counters),
            "gauges": dict(self._gauges),
            "histograms": {}
        }
        
        # Add histogram statistics
        for key in self._histograms:
            metrics["histograms"][key] = self.get_histogram_stats(key)
            
        return metrics
        
    def reset(self):
        """Reset all metrics to initial state."""
        self._counters.clear()
        self._gauges.clear()
        self._histograms.clear()
        self._timestamps.clear()
        
    def cleanup_old_metrics(self, max_age_seconds: int = 3600):
        """
        Remove metrics that haven't been updated recently.
        
        Args:
            max_age_seconds: Maximum age for metrics to keep
        """
        current_time = time.time()
        cutoff = current_time - max_age_seconds
        
        # Find old metrics
        old_keys = [
            key for key, timestamp in self._timestamps.items()
            if timestamp < cutoff
        ]
        
        # Remove old metrics
        for key in old_keys:
            self._counters.pop(key, None)
            self._gauges.pop(key, None)
            self._histograms.pop(key, None)
            self._timestamps.pop(key, None)
            
    def _make_key(self, name: str, labels: Optional[Dict[str, str]] = None) -> str:
        """Create a unique key for a metric with labels."""
        if not labels:
            return name
            
        # Sort labels for consistent keys
        label_parts = [f"{k}={v}" for k, v in sorted(labels.items())]
        return f"{name}{{{','.join(label_parts)}}}"
        
    def _percentile(self, sorted_values: List[float], percentile: float) -> float:
        """Calculate percentile value from sorted list."""
        if not sorted_values:
            return 0.0
            
        index = int(len(sorted_values) * percentile)
        if index >= len(sorted_values):
            index = len(sorted_values) - 1
            
        return sorted_values[index]
        
    def export_prometheus(self) -> str:
        """
        Export metrics in Prometheus format.
        
        Returns:
            Metrics formatted for Prometheus scraping
        """
        lines = []
        
        # Export counters
        for key, value in self._counters.items():
            lines.append(f"mcp_{key} {value}")
            
        # Export gauges
        for key, value in self._gauges.items():
            lines.append(f"mcp_{key} {value}")
            
        # Export histogram stats
        for key, values in self._histograms.items():
            stats = self.get_histogram_stats(key)
            base_name = f"mcp_{key}"
            
            lines.append(f"{base_name}_count {stats['count']}")
            lines.append(f"{base_name}_min {stats['min']}")
            lines.append(f"{base_name}_max {stats['max']}")
            lines.append(f"{base_name}_mean {stats['mean']}")
            lines.append(f"{base_name}_p50 {stats['p50']}")
            lines.append(f"{base_name}_p95 {stats['p95']}")
            lines.append(f"{base_name}_p99 {stats['p99']}")
            
        return "\n".join(lines)