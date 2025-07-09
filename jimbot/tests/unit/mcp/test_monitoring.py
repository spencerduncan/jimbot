"""
Test cases for MCP monitoring and metrics functionality.

These tests ensure that the MCP server properly collects and manages
performance metrics and security events.
"""

import time
import json
from unittest.mock import patch, MagicMock

from jimbot.mcp.utils.monitoring import (
    MetricsCollector,
    MetricPoint,
    TimingContext,
    get_metrics_collector
)


class TestMetricsCollector:
    """Test cases for MetricsCollector class."""

    def setup_method(self):
        """Setup test fixtures."""
        self.metrics = MetricsCollector()

    def test_counter_increment(self):
        """Test counter increment functionality."""
        metric_name = "test_counter"
        
        # Initial value should be 0
        assert self.metrics.get_counter(metric_name) == 0.0
        
        # Increment by 1
        self.metrics.increment(metric_name)
        assert self.metrics.get_counter(metric_name) == 1.0
        
        # Increment by custom value
        self.metrics.increment(metric_name, 5.0)
        assert self.metrics.get_counter(metric_name) == 6.0

    def test_gauge_values(self):
        """Test gauge value functionality."""
        metric_name = "test_gauge"
        
        # Initial value should be 0
        assert self.metrics.get_gauge(metric_name) == 0.0
        
        # Set gauge value
        self.metrics.gauge(metric_name, 42.5)
        assert self.metrics.get_gauge(metric_name) == 42.5

    def test_security_events(self):
        """Test security event logging."""
        client_id = "test_client_1"
        event_type = "invalid_json"
        details = {"error": "Invalid JSON format"}
        
        # Record security event
        self.metrics.security_event(event_type, client_id, details)
        
        # Check that counter was incremented
        assert self.metrics.get_counter(f"security_events_{event_type}_total") == 1.0
        
        # Check that event was recorded
        events = self.metrics.get_security_events()
        assert len(events) == 1
        assert events[0]["type"] == event_type
        assert events[0]["client_id"] == client_id
        assert events[0]["details"] == details

    def test_health_status_healthy(self):
        """Test health status when system is healthy."""
        # Add some normal metrics
        self.metrics.increment("events_processed_total", 100)
        self.metrics.increment("processing_errors_total", 2)  # 2% error rate
        
        health = self.metrics.get_health_status()
        assert health["status"] == "healthy"
        assert len(health["issues"]) == 0

    def test_health_status_unhealthy(self):
        """Test health status when system is unhealthy."""
        # Add metrics indicating high error rate
        self.metrics.increment("events_processed_total", 100)
        self.metrics.increment("processing_errors_total", 15)  # 15% error rate
        
        health = self.metrics.get_health_status()
        assert health["status"] == "unhealthy"
        assert len(health["issues"]) > 0
        assert any("error rate" in issue for issue in health["issues"])


class TestTimingContext:
    """Test cases for TimingContext class."""

    def setup_method(self):
        """Setup test fixtures."""
        self.metrics = MetricsCollector()

    def test_timing_context_success(self):
        """Test timing context with successful operation."""
        metric_name = "test_operation"
        
        with TimingContext(self.metrics, metric_name):
            time.sleep(0.001)  # Small delay
        
        # Should have recorded timing
        stats = self.metrics.get_timing_stats(metric_name)
        assert stats["count"] == 1
        assert stats["min"] >= 1.0  # At least 1ms


if __name__ == "__main__":
    # Run basic tests without pytest
    print("Running basic monitoring tests...")
    
    metrics = MetricsCollector()
    
    # Test counter
    metrics.increment("test_counter", 5)
    print(f"Counter test: {metrics.get_counter('test_counter')}")
    
    # Test gauge
    metrics.gauge("test_gauge", 42.5)
    print(f"Gauge test: {metrics.get_gauge('test_gauge')}")
    
    # Test security event
    metrics.security_event("test_event", "test_client", {"test": "data"})
    events = metrics.get_security_events()
    print(f"Security event test: {len(events)} events recorded")
    
    print("Basic monitoring tests completed successfully!")