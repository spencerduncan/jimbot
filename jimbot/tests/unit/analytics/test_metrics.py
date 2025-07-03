"""
Unit tests for analytics and metrics collection.

Tests metric aggregation, storage, and querying.
"""

import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pytest
import numpy as np

from jimbot.analytics.metrics import MetricsCollector, PerformanceTracker
from jimbot.analytics.aggregator import MetricAggregator
from jimbot.analytics.queries import MetricQueryEngine


class TestMetricsCollector:
    """Test metrics collection functionality."""

    @pytest.fixture
    def collector(self):
        """Create a metrics collector."""
        return MetricsCollector(buffer_size=1000)

    def test_records_game_metrics(self, collector):
        """Test recording game performance metrics."""
        metrics = {
            "game_id": "test-123",
            "ante_reached": 6,
            "final_score": 45000,
            "duration_seconds": 1800,
            "jokers_used": ["Joker", "Baseball Card"],
            "win": False,
        }

        collector.record_game(metrics)

        assert len(collector.buffer) == 1
        assert collector.buffer[0]["ante_reached"] == 6

    def test_records_decision_metrics(self, collector):
        """Test recording individual decision metrics."""
        decision = {
            "type": "joker_purchase",
            "joker": "Blueprint",
            "cost": 8,
            "money_before": 20,
            "money_after": 12,
            "ante": 3,
            "timestamp": time.time(),
        }

        collector.record_decision(decision)

        assert len(collector.decision_buffer) == 1
        assert collector.decision_buffer[0]["joker"] == "Blueprint"

    def test_calculates_running_statistics(self, collector):
        """Test calculation of running statistics."""
        # Record multiple games
        for i in range(10):
            collector.record_game(
                {
                    "ante_reached": 4 + i % 3,
                    "win": i % 3 == 0,
                    "duration_seconds": 1500 + i * 100,
                }
            )

        stats = collector.get_statistics()

        assert stats["total_games"] == 10
        assert stats["win_rate"] == 0.4  # 4/10 wins
        assert stats["avg_ante"] > 4
        assert stats["avg_duration"] > 1500

    def test_buffer_overflow_handling(self, collector):
        """Test handling when buffer exceeds size limit."""
        collector.buffer_size = 5

        # Add more than buffer size
        for i in range(10):
            collector.record_game({"game_id": f"game-{i}"})

        assert len(collector.buffer) == 5
        # Should keep most recent
        assert collector.buffer[-1]["game_id"] == "game-9"

    def test_exports_metrics_batch(self, collector):
        """Test exporting metrics for persistence."""
        # Add some metrics
        for i in range(5):
            collector.record_game({"game_id": f"game-{i}"})
            collector.record_decision({"decision_id": f"decision-{i}"})

        batch = collector.export_batch()

        assert len(batch["games"]) == 5
        assert len(batch["decisions"]) == 5
        assert "timestamp" in batch
        assert "batch_id" in batch

        # Buffer should be cleared
        assert len(collector.buffer) == 0
        assert len(collector.decision_buffer) == 0


class TestPerformanceTracker:
    """Test performance tracking across components."""

    @pytest.fixture
    def tracker(self):
        """Create a performance tracker."""
        return PerformanceTracker()

    def test_tracks_operation_timing(self, tracker):
        """Test timing of operations."""
        with tracker.time_operation("mcp_event_processing"):
            time.sleep(0.01)  # Simulate work

        timing = tracker.get_timing("mcp_event_processing")
        assert timing["count"] == 1
        assert timing["avg_ms"] > 9  # At least 9ms
        assert timing["max_ms"] >= timing["avg_ms"]

    def test_tracks_multiple_operations(self, tracker):
        """Test tracking multiple operation types."""
        # Track different operations
        for _ in range(5):
            with tracker.time_operation("query"):
                time.sleep(0.005)

        for _ in range(3):
            with tracker.time_operation("training_step"):
                time.sleep(0.02)

        all_timings = tracker.get_all_timings()

        assert len(all_timings) == 2
        assert all_timings["query"]["count"] == 5
        assert all_timings["training_step"]["count"] == 3

    def test_calculates_percentiles(self, tracker):
        """Test percentile calculations for timing distributions."""
        # Create varied timings
        timings = [0.01, 0.02, 0.015, 0.05, 0.03, 0.025, 0.1, 0.02, 0.015, 0.02]

        for t in timings:
            with patch("time.perf_counter") as mock_time:
                mock_time.side_effect = [0, t]  # Start and end times
                with tracker.time_operation("test_op"):
                    pass

        stats = tracker.get_timing_statistics("test_op")

        assert stats["p50"] < stats["p95"]
        assert stats["p95"] < stats["p99"]
        assert stats["p99"] <= 100  # 100ms = 0.1s max

    def test_tracks_throughput(self, tracker):
        """Test throughput tracking."""
        # Record events processed
        tracker.record_throughput("events_processed", 1000)
        tracker.record_throughput("events_processed", 1200)
        tracker.record_throughput("events_processed", 800)

        throughput = tracker.get_throughput("events_processed")

        assert throughput["total"] == 3000
        assert throughput["avg_per_second"] > 0
        assert throughput["current_rate"] > 0

    def test_memory_tracking(self, tracker):
        """Test memory usage tracking."""
        tracker.record_memory_usage("model", 1024 * 1024 * 100)  # 100MB
        tracker.record_memory_usage("cache", 1024 * 1024 * 50)  # 50MB

        memory = tracker.get_memory_usage()

        assert memory["model"] == 100  # MB
        assert memory["cache"] == 50
        assert memory["total"] == 150


class TestMetricAggregator:
    """Test metric aggregation functionality."""

    @pytest.fixture
    def aggregator(self):
        """Create a metric aggregator."""
        return MetricAggregator()

    def test_aggregates_by_time_window(self, aggregator):
        """Test aggregation over time windows."""
        # Add metrics over time
        base_time = datetime.now()

        for i in range(24):  # 24 hours of data
            timestamp = base_time - timedelta(hours=23 - i)
            aggregator.add_metric(
                {"timestamp": timestamp, "ante_reached": 5 + (i % 3), "win": i % 4 == 0}
            )

        # Aggregate by hour
        hourly = aggregator.aggregate_by_hour()

        assert len(hourly) == 24
        assert all("avg_ante" in h for h in hourly)
        assert all("win_rate" in h for h in hourly)

    def test_aggregates_by_category(self, aggregator):
        """Test aggregation by categorical dimensions."""
        # Add metrics with categories
        for joker in ["Joker", "Baseball Card", "DNA"]:
            for i in range(10):
                aggregator.add_metric(
                    {
                        "joker_purchased": joker,
                        "ante_improvement": np.random.randint(0, 3),
                        "cost": 5 + np.random.randint(0, 5),
                    }
                )

        by_joker = aggregator.aggregate_by("joker_purchased")

        assert len(by_joker) == 3
        assert all("avg_ante_improvement" in stats for stats in by_joker.values())
        assert all("count" in stats for stats in by_joker.values())

    def test_calculates_correlations(self, aggregator):
        """Test correlation analysis between metrics."""
        # Generate correlated data
        for i in range(100):
            money_spent = i * 2
            ante_reached = 3 + (money_spent / 50)  # Positive correlation

            aggregator.add_metric(
                {
                    "money_spent_on_jokers": money_spent,
                    "ante_reached": int(ante_reached),
                    "win": ante_reached >= 6,
                }
            )

        correlations = aggregator.calculate_correlations(
            ["money_spent_on_jokers", "ante_reached"]
        )

        assert correlations["money_spent_on_jokers"]["ante_reached"] > 0.8

    def test_identifies_trends(self, aggregator):
        """Test trend identification in metrics."""
        # Create trending data
        base_time = datetime.now()

        for day in range(30):
            timestamp = base_time - timedelta(days=29 - day)
            # Improving win rate over time
            win_rate = 0.3 + (day / 100)

            for _ in range(10):  # 10 games per day
                aggregator.add_metric(
                    {"timestamp": timestamp, "win": np.random.random() < win_rate}
                )

        trend = aggregator.analyze_trend("win", days=30)

        assert trend["direction"] == "increasing"
        assert trend["change_percent"] > 10


class TestMetricQueryEngine:
    """Test metric querying and analysis."""

    @pytest.fixture
    def query_engine(self):
        """Create a query engine with mock data store."""
        engine = MetricQueryEngine()
        engine.data_store = Mock()
        return engine

    def test_queries_top_performing_strategies(self, query_engine):
        """Test finding best performing strategies."""
        query_engine.data_store.query.return_value = [
            {"strategy": "flush_focus", "avg_ante": 7.2, "win_rate": 0.65},
            {"strategy": "high_card_scaling", "avg_ante": 6.8, "win_rate": 0.55},
            {"strategy": "economy_first", "avg_ante": 6.5, "win_rate": 0.60},
        ]

        top_strategies = query_engine.get_top_strategies(limit=2)

        assert len(top_strategies) == 2
        assert top_strategies[0]["strategy"] == "flush_focus"
        assert top_strategies[0]["win_rate"] == 0.65

    def test_analyzes_joker_performance(self, query_engine):
        """Test joker performance analysis."""
        query_engine.data_store.query.return_value = [
            {"joker": "Blueprint", "avg_ante_gained": 1.8, "usage_count": 45},
            {"joker": "Joker", "avg_ante_gained": 0.5, "usage_count": 120},
            {"joker": "DNA", "avg_ante_gained": 1.5, "usage_count": 30},
        ]

        analysis = query_engine.analyze_joker_impact()

        assert analysis["most_impactful"] == "Blueprint"
        assert analysis["most_used"] == "Joker"
        assert len(analysis["rankings"]) == 3

    def test_generates_performance_report(self, query_engine):
        """Test comprehensive performance report generation."""
        # Mock various queries
        query_engine.data_store.query.side_effect = [
            [{"total_games": 1000, "total_wins": 450}],  # Overall stats
            [{"avg_ante": 5.8, "avg_duration": 1650}],  # Averages
            [{"strategy": "flush", "win_rate": 0.7}],  # Top strategy
            [{"joker": "Blueprint", "impact": 1.8}],  # Top joker
        ]

        report = query_engine.generate_performance_report(days=7)

        assert report["period_days"] == 7
        assert report["win_rate"] == 0.45
        assert report["top_strategy"]["strategy"] == "flush"
        assert report["top_joker"]["joker"] == "Blueprint"

    def test_custom_metric_queries(self, query_engine):
        """Test custom metric queries with filters."""
        query_engine.data_store.query.return_value = [
            {"hour": 14, "avg_win_rate": 0.62},
            {"hour": 15, "avg_win_rate": 0.58},
            {"hour": 16, "avg_win_rate": 0.65},
        ]

        results = query_engine.custom_query(
            metric="win_rate",
            group_by="hour_of_day",
            filters={"ante_reached": {">=": 6}},
        )

        assert len(results) == 3
        assert results[2]["hour"] == 16
        assert results[2]["avg_win_rate"] == 0.65
