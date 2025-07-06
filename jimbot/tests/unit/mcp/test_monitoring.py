"""
Unit tests for MCP monitoring module.

Tests metrics collection and monitoring functionality.
"""

import time
import unittest
from unittest.mock import patch

from jimbot.mcp.utils.monitoring import MetricsCollector


class TestMetricsCollector(unittest.TestCase):
    """Test MetricsCollector functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.metrics = MetricsCollector()
        
    def test_counter_metrics(self):
        """Test counter metric functionality."""
        # Initial value should be 0
        self.assertEqual(self.metrics.get_counter("test_counter"), 0.0)
        
        # Increment by default (1)
        self.metrics.increment("test_counter")
        self.assertEqual(self.metrics.get_counter("test_counter"), 1.0)
        
        # Increment by custom value
        self.metrics.increment("test_counter", 5.0)
        self.assertEqual(self.metrics.get_counter("test_counter"), 6.0)
        
        # Multiple counters
        self.metrics.increment("counter2", 10.0)
        self.assertEqual(self.metrics.get_counter("test_counter"), 6.0)
        self.assertEqual(self.metrics.get_counter("counter2"), 10.0)
        
    def test_counter_with_labels(self):
        """Test counter metrics with labels."""
        # Counters with different labels are separate
        self.metrics.increment("requests", labels={"method": "GET"})
        self.metrics.increment("requests", labels={"method": "POST"})
        self.metrics.increment("requests", labels={"method": "GET"})
        
        self.assertEqual(
            self.metrics.get_counter("requests", labels={"method": "GET"}), 
            2.0
        )
        self.assertEqual(
            self.metrics.get_counter("requests", labels={"method": "POST"}), 
            1.0
        )
        
    def test_gauge_metrics(self):
        """Test gauge metric functionality."""
        # Initial value should be 0
        self.assertEqual(self.metrics.get_gauge("test_gauge"), 0.0)
        
        # Set gauge value
        self.metrics.gauge("test_gauge", 42.5)
        self.assertEqual(self.metrics.get_gauge("test_gauge"), 42.5)
        
        # Update gauge value
        self.metrics.gauge("test_gauge", 10.0)
        self.assertEqual(self.metrics.get_gauge("test_gauge"), 10.0)
        
    def test_gauge_with_labels(self):
        """Test gauge metrics with labels."""
        self.metrics.gauge("cpu_usage", 50.0, labels={"core": "0"})
        self.metrics.gauge("cpu_usage", 75.0, labels={"core": "1"})
        
        self.assertEqual(
            self.metrics.get_gauge("cpu_usage", labels={"core": "0"}),
            50.0
        )
        self.assertEqual(
            self.metrics.get_gauge("cpu_usage", labels={"core": "1"}),
            75.0
        )
        
    def test_histogram_metrics(self):
        """Test histogram metric functionality."""
        # Empty histogram stats
        stats = self.metrics.get_histogram_stats("test_histogram")
        self.assertEqual(stats["count"], 0)
        self.assertEqual(stats["min"], 0.0)
        self.assertEqual(stats["max"], 0.0)
        self.assertEqual(stats["mean"], 0.0)
        
        # Add values
        values = [10, 20, 30, 40, 50]
        for val in values:
            self.metrics.histogram("test_histogram", val)
            
        stats = self.metrics.get_histogram_stats("test_histogram")
        self.assertEqual(stats["count"], 5)
        self.assertEqual(stats["min"], 10)
        self.assertEqual(stats["max"], 50)
        self.assertEqual(stats["mean"], 30)
        self.assertEqual(stats["p50"], 30)  # Median
        
    def test_histogram_percentiles(self):
        """Test histogram percentile calculations."""
        # Add 100 values
        for i in range(100):
            self.metrics.histogram("latency", i)
            
        stats = self.metrics.get_histogram_stats("latency")
        self.assertEqual(stats["count"], 100)
        self.assertEqual(stats["min"], 0)
        self.assertEqual(stats["max"], 99)
        self.assertAlmostEqual(stats["mean"], 49.5)
        
        # Check percentiles
        self.assertEqual(stats["p50"], 50)  # 50th percentile
        self.assertEqual(stats["p95"], 95)  # 95th percentile
        self.assertEqual(stats["p99"], 99)  # 99th percentile
        
    def test_histogram_max_size(self):
        """Test that histogram respects max size."""
        metrics = MetricsCollector(history_size=10)
        
        # Add more values than history size
        for i in range(20):
            metrics.histogram("limited", i)
            
        # Should only keep last 10 values
        stats = metrics.get_histogram_stats("limited")
        self.assertEqual(stats["count"], 10)
        self.assertEqual(stats["min"], 10)  # First 10 values discarded
        self.assertEqual(stats["max"], 19)
        
    def test_get_all_metrics(self):
        """Test getting all metrics at once."""
        # Add various metrics
        self.metrics.increment("counter1", 5)
        self.metrics.gauge("gauge1", 42)
        self.metrics.histogram("hist1", 100)
        self.metrics.histogram("hist1", 200)
        
        all_metrics = self.metrics.get_all_metrics()
        
        # Check structure
        self.assertIn("timestamp", all_metrics)
        self.assertIn("counters", all_metrics)
        self.assertIn("gauges", all_metrics)
        self.assertIn("histograms", all_metrics)
        
        # Check values
        self.assertEqual(all_metrics["counters"]["counter1"], 5)
        self.assertEqual(all_metrics["gauges"]["gauge1"], 42)
        self.assertEqual(all_metrics["histograms"]["hist1"]["count"], 2)
        self.assertEqual(all_metrics["histograms"]["hist1"]["mean"], 150)
        
    def test_reset_metrics(self):
        """Test resetting all metrics."""
        # Add some metrics
        self.metrics.increment("counter", 10)
        self.metrics.gauge("gauge", 50)
        self.metrics.histogram("hist", 100)
        
        # Reset
        self.metrics.reset()
        
        # All should be cleared
        self.assertEqual(self.metrics.get_counter("counter"), 0.0)
        self.assertEqual(self.metrics.get_gauge("gauge"), 0.0)
        self.assertEqual(self.metrics.get_histogram_stats("hist")["count"], 0)
        
    def test_cleanup_old_metrics(self):
        """Test cleanup of old metrics."""
        # Add metrics at different times
        self.metrics.increment("old_metric")
        
        # Mock time to make metric appear old
        with patch('time.time', return_value=time.time() + 4000):
            self.metrics.increment("new_metric")
            
            # Cleanup metrics older than 1 hour
            self.metrics.cleanup_old_metrics(max_age_seconds=3600)
            
        # Old metric should be gone
        self.assertEqual(self.metrics.get_counter("old_metric"), 0.0)
        # New metric should remain
        self.assertEqual(self.metrics.get_counter("new_metric"), 1.0)
        
    def test_prometheus_export(self):
        """Test Prometheus format export."""
        # Add various metrics
        self.metrics.increment("events_total", 100)
        self.metrics.gauge("connections", 5)
        self.metrics.histogram("latency_ms", 10)
        self.metrics.histogram("latency_ms", 20)
        self.metrics.histogram("latency_ms", 30)
        
        # Export to Prometheus format
        output = self.metrics.export_prometheus()
        
        # Check format
        lines = output.split('\n')
        self.assertIn("mcp_events_total 100", lines)
        self.assertIn("mcp_connections 5", lines)
        
        # Check histogram metrics
        histogram_lines = [l for l in lines if "latency_ms" in l]
        self.assertTrue(any("mcp_latency_ms_count 3" in l for l in histogram_lines))
        self.assertTrue(any("mcp_latency_ms_min 10" in l for l in histogram_lines))
        self.assertTrue(any("mcp_latency_ms_max 30" in l for l in histogram_lines))
        self.assertTrue(any("mcp_latency_ms_mean 20" in l for l in histogram_lines))
        
    def test_label_key_format(self):
        """Test that labels are formatted correctly in keys."""
        # Single label
        self.metrics.increment("requests", labels={"method": "GET"})
        key = self.metrics._make_key("requests", {"method": "GET"})
        self.assertEqual(key, "requests{method=GET}")
        
        # Multiple labels (should be sorted)
        labels = {"method": "POST", "status": "200", "endpoint": "/api"}
        self.metrics.increment("requests", labels=labels)
        key = self.metrics._make_key("requests", labels)
        self.assertEqual(key, "requests{endpoint=/api,method=POST,status=200}")
        
    def test_timestamps_recorded(self):
        """Test that timestamps are recorded for metrics."""
        # Add metric
        self.metrics.increment("test")
        
        # Check timestamp was recorded
        self.assertIn("test", self.metrics._timestamps)
        timestamp = self.metrics._timestamps["test"]
        
        # Should be recent
        self.assertLess(abs(time.time() - timestamp), 1.0)
        
    def test_thread_safety_simulation(self):
        """Test basic thread safety (simplified test)."""
        # This is a basic test - real thread safety would require actual threading
        
        # Rapid updates to same counter
        for i in range(100):
            self.metrics.increment("concurrent_counter")
            
        self.assertEqual(self.metrics.get_counter("concurrent_counter"), 100.0)
        
        # Rapid updates to histogram
        for i in range(100):
            self.metrics.histogram("concurrent_hist", i)
            
        stats = self.metrics.get_histogram_stats("concurrent_hist")
        self.assertEqual(stats["count"], 100)


if __name__ == "__main__":
    unittest.main()