"""
JimBot Analytics & Monitoring Subsystem

Provides comprehensive observability for JimBot's learning process and game performance.
"""

from .metrics.metric_collector import MetricCollector
from .eventstore.event_processor import EventProcessor
from .dashboards.performance_dashboard import PerformanceDashboard

__version__ = "0.1.0"
__all__ = ["MetricCollector", "EventProcessor", "PerformanceDashboard"]