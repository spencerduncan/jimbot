"""
JimBot Analytics & Monitoring Subsystem

Provides comprehensive observability for JimBot's learning process and game performance.
"""

from .dashboards.performance_dashboard import PerformanceDashboard
from .eventstore.event_processor import EventProcessor
from .metrics.metric_collector import MetricCollector

__version__ = "0.1.0"
__all__ = ["MetricCollector", "EventProcessor", "PerformanceDashboard"]
