"""
Monitoring and metrics collection for MCP server.

This module provides metrics collection and monitoring capabilities
for the MCP server to track performance and security events.
"""

import time
import logging
from typing import Dict, Any, List, Optional
from collections import defaultdict, deque
from dataclasses import dataclass
from threading import Lock
import json

logger = logging.getLogger(__name__)


@dataclass
class MetricPoint:
    """Represents a single metric measurement."""
    name: str
    value: float
    timestamp: float
    tags: Dict[str, str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = {}


class MetricsCollector:
    """Collects and stores metrics for MCP server operations."""
    
    def __init__(self, max_history_size: int = 10000):
        """
        Initialize metrics collector.
        
        Args:
            max_history_size: Maximum number of metric points to keep in memory
        """
        self.max_history_size = max_history_size
        self._lock = Lock()
        
        # Metric storage
        self._counters: Dict[str, float] = defaultdict(float)
        self._gauges: Dict[str, float] = defaultdict(float)
        self._histograms: Dict[str, List[float]] = defaultdict(list)
        self._timers: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        
        # Metric history
        self._history: deque = deque(maxlen=max_history_size)
        
        # Security metrics
        self._security_events: deque = deque(maxlen=1000)
        
        # Performance tracking
        self._performance_snapshots: deque = deque(maxlen=100)
        self._last_snapshot_time = time.time()
        
    def increment(self, metric_name: str, value: float = 1.0, tags: Dict[str, str] = None):
        """
        Increment a counter metric.
        
        Args:
            metric_name: Name of the metric
            value: Value to increment by
            tags: Optional metric tags
        """
        with self._lock:
            self._counters[metric_name] += value
            self._add_to_history(metric_name, value, tags)
    
    def decrement(self, metric_name: str, value: float = 1.0, tags: Dict[str, str] = None):
        """
        Decrement a counter metric.
        
        Args:
            metric_name: Name of the metric
            value: Value to decrement by
            tags: Optional metric tags
        """
        self.increment(metric_name, -value, tags)
    
    def gauge(self, metric_name: str, value: float, tags: Dict[str, str] = None):
        """
        Set a gauge metric value.
        
        Args:
            metric_name: Name of the metric
            value: Current value
            tags: Optional metric tags
        """
        with self._lock:
            self._gauges[metric_name] = value
            self._add_to_history(metric_name, value, tags)
    
    def histogram(self, metric_name: str, value: float, tags: Dict[str, str] = None):
        """
        Add a value to a histogram metric.
        
        Args:
            metric_name: Name of the metric
            value: Value to add
            tags: Optional metric tags
        """
        with self._lock:
            self._histograms[metric_name].append(value)
            # Keep only recent values
            if len(self._histograms[metric_name]) > 1000:
                self._histograms[metric_name] = self._histograms[metric_name][-1000:]
            self._add_to_history(metric_name, value, tags)
    
    def timing(self, metric_name: str, duration: float, tags: Dict[str, str] = None):
        """
        Record a timing metric.
        
        Args:
            metric_name: Name of the metric
            duration: Duration in seconds
            tags: Optional metric tags
        """
        with self._lock:
            self._timers[metric_name].append(duration)
            self._add_to_history(metric_name, duration, tags)
    
    def security_event(self, event_type: str, client_id: str, details: Dict[str, Any] = None):
        """
        Record a security event.
        
        Args:
            event_type: Type of security event
            client_id: Client identifier
            details: Additional event details
        """
        event = {
            'type': event_type,
            'client_id': client_id,
            'timestamp': time.time(),
            'details': details or {}
        }
        
        with self._lock:
            self._security_events.append(event)
            self.increment(f'security_events_{event_type}_total')
        
        logger.warning(f"Security event [{event_type}] from client {client_id}: {details}")
    
    def _add_to_history(self, metric_name: str, value: float, tags: Dict[str, str] = None):
        """Add metric point to history."""
        point = MetricPoint(
            name=metric_name,
            value=value,
            timestamp=time.time(),
            tags=tags or {}
        )
        self._history.append(point)
    
    def get_counter(self, metric_name: str) -> float:
        """Get current counter value."""
        with self._lock:
            return self._counters.get(metric_name, 0.0)
    
    def get_gauge(self, metric_name: str) -> float:
        """Get current gauge value."""
        with self._lock:
            return self._gauges.get(metric_name, 0.0)
    
    def get_histogram_stats(self, metric_name: str) -> Dict[str, float]:
        """Get histogram statistics."""
        with self._lock:
            values = self._histograms.get(metric_name, [])
            if not values:
                return {}
            
            values = sorted(values)
            count = len(values)
            
            return {
                'count': count,
                'min': values[0],
                'max': values[-1],
                'mean': sum(values) / count,
                'p50': values[int(count * 0.5)],
                'p95': values[int(count * 0.95)],
                'p99': values[int(count * 0.99)],
            }
    
    def get_timing_stats(self, metric_name: str) -> Dict[str, float]:
        """Get timing statistics."""
        with self._lock:
            values = list(self._timers.get(metric_name, []))
            if not values:
                return {}
            
            values = sorted(values)
            count = len(values)
            
            return {
                'count': count,
                'min': values[0] * 1000,  # Convert to milliseconds
                'max': values[-1] * 1000,
                'mean': sum(values) / count * 1000,
                'p50': values[int(count * 0.5)] * 1000,
                'p95': values[int(count * 0.95)] * 1000,
                'p99': values[int(count * 0.99)] * 1000,
            }
    
    def get_security_events(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent security events."""
        with self._lock:
            events = list(self._security_events)
            return events[-limit:] if events else []
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """Get all current metrics."""
        with self._lock:
            return {
                'counters': dict(self._counters),
                'gauges': dict(self._gauges),
                'histograms': {k: self.get_histogram_stats(k) for k in self._histograms.keys()},
                'timers': {k: self.get_timing_stats(k) for k in self._timers.keys()},
                'security_events_count': len(self._security_events),
                'metrics_history_size': len(self._history)
            }
    
    def take_performance_snapshot(self):
        """Take a performance snapshot."""
        now = time.time()
        
        # Only take snapshot if enough time has passed
        if now - self._last_snapshot_time < 60:  # 1 minute minimum
            return
        
        snapshot = {
            'timestamp': now,
            'metrics': self.get_all_metrics(),
            'system_stats': self._get_system_stats()
        }
        
        with self._lock:
            self._performance_snapshots.append(snapshot)
            self._last_snapshot_time = now
    
    def _get_system_stats(self) -> Dict[str, Any]:
        """Get system statistics."""
        try:
            import psutil
            
            # Get process info
            process = psutil.Process()
            
            return {
                'cpu_percent': process.cpu_percent(),
                'memory_mb': process.memory_info().rss / 1024 / 1024,
                'open_files': len(process.open_files()),
                'connections': len(process.connections()),
                'threads': process.num_threads()
            }
        except ImportError:
            # psutil not available, return basic stats
            return {
                'timestamp': time.time(),
                'message': 'psutil not available for detailed system stats'
            }
    
    def get_performance_snapshots(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent performance snapshots."""
        with self._lock:
            snapshots = list(self._performance_snapshots)
            return snapshots[-limit:] if snapshots else []
    
    def export_metrics(self, format: str = 'json') -> str:
        """
        Export metrics in specified format.
        
        Args:
            format: Export format ('json' or 'prometheus')
            
        Returns:
            str: Formatted metrics
        """
        if format == 'json':
            return json.dumps(self.get_all_metrics(), indent=2)
        elif format == 'prometheus':
            return self._export_prometheus()
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def _export_prometheus(self) -> str:
        """Export metrics in Prometheus format."""
        lines = []
        
        # Export counters
        for name, value in self._counters.items():
            lines.append(f"# TYPE {name} counter")
            lines.append(f"{name} {value}")
        
        # Export gauges
        for name, value in self._gauges.items():
            lines.append(f"# TYPE {name} gauge")
            lines.append(f"{name} {value}")
        
        # Export histogram summaries
        for name in self._histograms.keys():
            stats = self.get_histogram_stats(name)
            if stats:
                lines.append(f"# TYPE {name} histogram")
                for stat_name, stat_value in stats.items():
                    lines.append(f"{name}_{stat_name} {stat_value}")
        
        return '\n'.join(lines)
    
    def reset_metrics(self):
        """Reset all metrics (useful for testing)."""
        with self._lock:
            self._counters.clear()
            self._gauges.clear()
            self._histograms.clear()
            self._timers.clear()
            self._history.clear()
            self._security_events.clear()
            self._performance_snapshots.clear()
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get health status based on metrics."""
        with self._lock:
            # Check error rates
            total_events = self.get_counter('events_processed_total')
            error_events = self.get_counter('processing_errors_total')
            invalid_events = self.get_counter('invalid_messages_total')
            
            error_rate = (error_events / total_events) if total_events > 0 else 0
            invalid_rate = (invalid_events / total_events) if total_events > 0 else 0
            
            # Check security events
            security_events_count = len(self._security_events)
            recent_security_events = sum(1 for e in self._security_events 
                                       if e['timestamp'] > time.time() - 300)  # Last 5 minutes
            
            # Determine health status
            health_status = 'healthy'
            issues = []
            
            if error_rate > 0.1:  # More than 10% errors
                health_status = 'unhealthy'
                issues.append(f'High error rate: {error_rate:.2%}')
            
            if invalid_rate > 0.05:  # More than 5% invalid messages
                health_status = 'degraded'
                issues.append(f'High invalid message rate: {invalid_rate:.2%}')
            
            if recent_security_events > 10:  # More than 10 security events in 5 minutes
                health_status = 'security_alert'
                issues.append(f'High security event rate: {recent_security_events} in 5 minutes')
            
            return {
                'status': health_status,
                'issues': issues,
                'metrics': {
                    'total_events': total_events,
                    'error_rate': error_rate,
                    'invalid_rate': invalid_rate,
                    'security_events_total': security_events_count,
                    'recent_security_events': recent_security_events
                }
            }


# Context manager for timing operations
class TimingContext:
    """Context manager for timing operations."""
    
    def __init__(self, metrics_collector: MetricsCollector, metric_name: str, tags: Dict[str, str] = None):
        self.metrics_collector = metrics_collector
        self.metric_name = metric_name
        self.tags = tags
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time is not None:
            duration = time.time() - self.start_time
            self.metrics_collector.timing(self.metric_name, duration, self.tags)


# Global metrics collector instance
_metrics_collector = MetricsCollector()


def get_metrics_collector() -> MetricsCollector:
    """Get the global metrics collector instance."""
    return _metrics_collector


def time_operation(metric_name: str, tags: Dict[str, str] = None):
    """
    Decorator for timing operations.
    
    Args:
        metric_name: Name of the timing metric
        tags: Optional metric tags
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            with TimingContext(_metrics_collector, metric_name, tags):
                return func(*args, **kwargs)
        return wrapper
    return decorator