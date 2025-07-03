"""
Performance dashboard service for real-time monitoring and visualization.

This module provides dashboard functionality for monitoring JimBot's performance,
learning progress, and game statistics.
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Tuple

logger = logging.getLogger(__name__)


class DashboardType(Enum):
    """Types of dashboards available."""

    SYSTEM_HEALTH = "system_health"
    GAME_PERFORMANCE = "game_performance"
    LEARNING_PROGRESS = "learning_progress"
    COMPONENT_LATENCY = "component_latency"
    STRATEGY_ANALYSIS = "strategy_analysis"


@dataclass
class DashboardPanel:
    """Represents a single panel in a dashboard."""

    title: str
    panel_type: str  # graph, stat, table, heatmap
    query: str
    refresh_interval: int  # seconds
    display_options: Dict[str, Any]


class PerformanceDashboard:
    """
    Provides dashboard functionality for monitoring JimBot performance.

    Features:
    - Real-time metric visualization
    - Historical trend analysis
    - Alert status display
    - Custom dashboard creation
    """

    def __init__(
        self,
        questdb_host: str = "localhost",
        questdb_port: int = 8812,
        eventstore_host: str = "localhost",
        eventstore_port: int = 2113,
    ):
        """
        Initialize the performance dashboard.

        Args:
            questdb_host: QuestDB host for metrics
            questdb_port: QuestDB port
            eventstore_host: EventStoreDB host for events
            eventstore_port: EventStoreDB port
        """
        self.questdb_host = questdb_host
        self.questdb_port = questdb_port
        self.eventstore_host = eventstore_host
        self.eventstore_port = eventstore_port

        # Dashboard definitions
        self.dashboards = self._define_dashboards()

        # Cache for dashboard data
        self.data_cache: Dict[str, Tuple[Any, datetime]] = {}
        self.cache_ttl = timedelta(seconds=5)

    def _define_dashboards(self) -> Dict[DashboardType, List[DashboardPanel]]:
        """Define the standard dashboards and their panels."""
        return {
            DashboardType.SYSTEM_HEALTH: [
                DashboardPanel(
                    title="CPU Usage by Component",
                    panel_type="graph",
                    query="""
                        SELECT timestamp, component, avg(value) as cpu_percent
                        FROM cpu_usage
                        WHERE timestamp > dateadd('m', -30, now())
                        SAMPLE BY 1m
                        PARTITION BY component
                    """,
                    refresh_interval=30,
                    display_options={"y_axis": "CPU %", "max_y": 100, "stacked": False},
                ),
                DashboardPanel(
                    title="Memory Usage",
                    panel_type="graph",
                    query="""
                        SELECT timestamp, component, avg(value) as memory_mb
                        FROM memory_usage
                        WHERE timestamp > dateadd('h', -1, now())
                        SAMPLE BY 1m
                        PARTITION BY component
                    """,
                    refresh_interval=30,
                    display_options={
                        "y_axis": "Memory (MB)",
                        "max_y": 6144,  # 6GB limit
                        "warning_threshold": 5120,  # 5GB warning
                        "critical_threshold": 5632,  # 5.5GB critical
                    },
                ),
                DashboardPanel(
                    title="GPU Utilization",
                    panel_type="stat",
                    query="""
                        SELECT avg(value) as gpu_percent,
                               max(value) as max_gpu,
                               min(value) as min_gpu
                        FROM gpu_utilization
                        WHERE timestamp > dateadd('m', -5, now())
                    """,
                    refresh_interval=10,
                    display_options={
                        "unit": "%",
                        "precision": 1,
                        "color_thresholds": [50, 75, 90],
                    },
                ),
                DashboardPanel(
                    title="Component Status",
                    panel_type="table",
                    query="""
                        SELECT component,
                               last(status) as current_status,
                               last(timestamp) as last_heartbeat,
                               count(*) as heartbeat_count
                        FROM component_heartbeat
                        WHERE timestamp > dateadd('m', -5, now())
                        GROUP BY component
                    """,
                    refresh_interval=5,
                    display_options={
                        "columns": ["Component", "Status", "Last Seen", "Count"],
                        "status_colors": {
                            "healthy": "green",
                            "warning": "yellow",
                            "error": "red",
                        },
                    },
                ),
            ],
            DashboardType.GAME_PERFORMANCE: [
                DashboardPanel(
                    title="Win Rate Trend",
                    panel_type="graph",
                    query="""
                        SELECT timestamp,
                               count(*) as total_games,
                               sum(CASE WHEN outcome = 'win' THEN 1 ELSE 0 END) as wins,
                               100.0 * sum(CASE WHEN outcome = 'win' THEN 1 ELSE 0 END) / count(*) as win_rate
                        FROM game_results
                        WHERE timestamp > dateadd('d', -7, now())
                        SAMPLE BY 1h
                    """,
                    refresh_interval=60,
                    display_options={
                        "y_axis": "Win Rate %",
                        "show_totals": True,
                        "target_line": 10,  # 10% target win rate
                    },
                ),
                DashboardPanel(
                    title="Score Distribution",
                    panel_type="heatmap",
                    query="""
                        SELECT final_score,
                               rounds_survived,
                               count(*) as game_count
                        FROM game_results
                        WHERE timestamp > dateadd('d', -1, now())
                        GROUP BY final_score, rounds_survived
                    """,
                    refresh_interval=120,
                    display_options={
                        "x_axis": "Rounds Survived",
                        "y_axis": "Final Score",
                        "color_scale": "viridis",
                    },
                ),
                DashboardPanel(
                    title="Average Score by Strategy",
                    panel_type="graph",
                    query="""
                        SELECT timestamp,
                               strategy_type,
                               avg(final_score) as avg_score,
                               count(*) as games_played
                        FROM game_results
                        WHERE timestamp > dateadd('h', -24, now())
                        SAMPLE BY 1h
                        PARTITION BY strategy_type
                    """,
                    refresh_interval=60,
                    display_options={
                        "y_axis": "Average Score",
                        "show_game_count": True,
                    },
                ),
                DashboardPanel(
                    title="Current Game Stats",
                    panel_type="stat",
                    query="""
                        SELECT count(DISTINCT game_id) as active_games,
                               avg(round) as avg_round,
                               avg(score) as avg_score
                        FROM game_state_current
                        WHERE last_update > dateadd('m', -5, now())
                    """,
                    refresh_interval=5,
                    display_options={"show_sparkline": True},
                ),
            ],
            DashboardType.LEARNING_PROGRESS: [
                DashboardPanel(
                    title="Loss Curves",
                    panel_type="graph",
                    query="""
                        SELECT timestamp,
                               avg(ppo_loss) as policy_loss,
                               avg(value_loss) as value_loss,
                               avg(entropy) as entropy
                        FROM training_metrics
                        WHERE timestamp > dateadd('h', -6, now())
                        SAMPLE BY 5m
                    """,
                    refresh_interval=30,
                    display_options={
                        "y_axis": "Loss",
                        "log_scale": True,
                        "show_smoothed": True,
                    },
                ),
                DashboardPanel(
                    title="Exploration vs Exploitation",
                    panel_type="graph",
                    query="""
                        SELECT timestamp,
                               avg(exploration_rate) as exploration,
                               1 - avg(exploration_rate) as exploitation
                        FROM decision_metrics
                        WHERE timestamp > dateadd('h', -3, now())
                        SAMPLE BY 1m
                    """,
                    refresh_interval=30,
                    display_options={
                        "y_axis": "Probability",
                        "stacked": True,
                        "max_y": 1.0,
                    },
                ),
                DashboardPanel(
                    title="Model Performance",
                    panel_type="table",
                    query="""
                        SELECT model_version,
                               training_iteration,
                               avg_reward,
                               win_rate,
                               timestamp
                        FROM model_checkpoints
                        WHERE timestamp > dateadd('d', -7, now())
                        ORDER BY timestamp DESC
                        LIMIT 10
                    """,
                    refresh_interval=300,
                    display_options={
                        "highlight_best": True,
                        "metrics": ["avg_reward", "win_rate"],
                    },
                ),
                DashboardPanel(
                    title="Learning Rate",
                    panel_type="stat",
                    query="""
                        SELECT last(learning_rate) as current_lr,
                               last(training_iteration) as iteration
                        FROM training_metrics
                    """,
                    refresh_interval=60,
                    display_options={"format": "scientific", "show_iteration": True},
                ),
            ],
            DashboardType.COMPONENT_LATENCY: [
                DashboardPanel(
                    title="End-to-End Decision Latency",
                    panel_type="graph",
                    query="""
                        SELECT timestamp,
                               avg(value) as avg_latency,
                               max(value) as max_latency,
                               percentile_cont(0.95) WITHIN GROUP (ORDER BY value) as p95_latency
                        FROM decision_latency
                        WHERE timestamp > dateadd('h', -1, now())
                        SAMPLE BY 30s
                    """,
                    refresh_interval=10,
                    display_options={
                        "y_axis": "Latency (ms)",
                        "target_line": 100,
                        "warning_line": 200,
                        "critical_line": 500,
                    },
                ),
                DashboardPanel(
                    title="Component Latency Breakdown",
                    panel_type="graph",
                    query="""
                        SELECT timestamp,
                               component,
                               avg(value) as avg_latency
                        FROM component_latency
                        WHERE timestamp > dateadd('m', -30, now())
                        SAMPLE BY 1m
                        PARTITION BY component
                    """,
                    refresh_interval=30,
                    display_options={"y_axis": "Latency (ms)", "stacked": True},
                ),
                DashboardPanel(
                    title="API Call Latency",
                    panel_type="table",
                    query="""
                        SELECT api_name,
                               count(*) as call_count,
                               avg(latency) as avg_latency,
                               max(latency) as max_latency,
                               sum(CASE WHEN cache_hit THEN 1 ELSE 0 END) / count(*) as cache_hit_rate
                        FROM api_calls
                        WHERE timestamp > dateadd('h', -1, now())
                        GROUP BY api_name
                    """,
                    refresh_interval=60,
                    display_options={
                        "sort_by": "call_count",
                        "highlight_slow": 1000,  # ms
                    },
                ),
            ],
            DashboardType.STRATEGY_ANALYSIS: [
                DashboardPanel(
                    title="Strategy Usage",
                    panel_type="graph",
                    query="""
                        SELECT timestamp,
                               strategy_name,
                               count(*) as usage_count
                        FROM strategy_selections
                        WHERE timestamp > dateadd('h', -6, now())
                        SAMPLE BY 10m
                        PARTITION BY strategy_name
                    """,
                    refresh_interval=60,
                    display_options={"y_axis": "Usage Count", "show_percentage": True},
                ),
                DashboardPanel(
                    title="Strategy Performance Matrix",
                    panel_type="heatmap",
                    query="""
                        SELECT strategy_name,
                               round_number,
                               avg(score_achieved) as avg_score,
                               count(*) as attempts
                        FROM strategy_performance
                        WHERE timestamp > dateadd('d', -1, now())
                        GROUP BY strategy_name, round_number
                    """,
                    refresh_interval=300,
                    display_options={
                        "x_axis": "Round",
                        "y_axis": "Strategy",
                        "metric": "avg_score",
                        "show_counts": True,
                    },
                ),
                DashboardPanel(
                    title="Joker Synergy Network",
                    panel_type="graph",
                    query="""
                        SELECT j1.name as joker1,
                               j2.name as joker2,
                               count(*) as co_occurrence,
                               avg(game_score) as avg_score_together
                        FROM joker_combinations j1
                        JOIN joker_combinations j2 ON j1.game_id = j2.game_id
                        WHERE j1.name < j2.name
                          AND timestamp > dateadd('d', -3, now())
                        GROUP BY j1.name, j2.name
                        HAVING count(*) > 10
                    """,
                    refresh_interval=600,
                    display_options={
                        "graph_type": "network",
                        "edge_weight": "co_occurrence",
                        "node_size": "avg_score_together",
                    },
                ),
            ],
        }

    async def get_dashboard_data(self, dashboard_type: DashboardType) -> Dict[str, Any]:
        """
        Get data for a specific dashboard.

        Args:
            dashboard_type: The type of dashboard to retrieve

        Returns:
            Dashboard data including all panel results
        """
        panels = self.dashboards.get(dashboard_type, [])
        dashboard_data = {
            "type": dashboard_type.value,
            "timestamp": datetime.utcnow().isoformat(),
            "panels": [],
        }

        for panel in panels:
            panel_data = await self._get_panel_data(panel)
            dashboard_data["panels"].append(
                {
                    "title": panel.title,
                    "type": panel.panel_type,
                    "data": panel_data,
                    "options": panel.display_options,
                }
            )

        return dashboard_data

    async def _get_panel_data(self, panel: DashboardPanel) -> Any:
        """Get data for a specific panel, using cache if available."""
        cache_key = f"{panel.title}:{panel.query}"

        # Check cache
        if cache_key in self.data_cache:
            data, timestamp = self.data_cache[cache_key]
            if datetime.utcnow() - timestamp < self.cache_ttl:
                return data

        # Execute query
        data = await self._execute_query(panel.query)

        # Update cache
        self.data_cache[cache_key] = (data, datetime.utcnow())

        return data

    async def _execute_query(self, query: str) -> Any:
        """Execute a query against QuestDB."""
        # TODO: Implement actual QuestDB query execution
        # This is a placeholder
        return {"placeholder": "data"}

    async def export_dashboard(
        self, dashboard_type: DashboardType, format: str = "json"
    ) -> str:
        """
        Export dashboard configuration.

        Args:
            dashboard_type: Dashboard to export
            format: Export format (json, yaml)

        Returns:
            Exported dashboard configuration
        """
        panels = self.dashboards.get(dashboard_type, [])

        export_data = {
            "dashboard": {
                "title": dashboard_type.value.replace("_", " ").title(),
                "type": dashboard_type.value,
                "panels": [
                    {
                        "title": panel.title,
                        "type": panel.panel_type,
                        "query": panel.query,
                        "refresh": panel.refresh_interval,
                        "options": panel.display_options,
                    }
                    for panel in panels
                ],
            }
        }

        if format == "json":
            return json.dumps(export_data, indent=2)
        else:
            raise ValueError(f"Unsupported export format: {format}")

    def create_custom_dashboard(self, name: str, panels: List[DashboardPanel]):
        """
        Create a custom dashboard.

        Args:
            name: Dashboard name
            panels: List of panels for the dashboard
        """
        # Store custom dashboard configuration
        # This could be persisted to a configuration file

    async def get_alerts(self) -> List[Dict[str, Any]]:
        """
        Get current active alerts based on dashboard metrics.

        Returns:
            List of active alerts
        """
        alerts = []

        # Check memory usage
        memory_query = """
            SELECT component, last(value) as memory_mb
            FROM memory_usage
            WHERE timestamp > dateadd('m', -5, now())
            GROUP BY component
        """
        memory_data = await self._execute_query(memory_query)  # noqa: F841 - TODO: implement alert logic

        # Check latency
        latency_query = """
            SELECT percentile_cont(0.95) WITHIN GROUP (ORDER BY value) as p95_latency
            FROM decision_latency
            WHERE timestamp > dateadd('m', -5, now())
        """
        latency_data = await self._execute_query(latency_query)  # noqa: F841 - TODO: implement alert logic

        # Generate alerts based on thresholds
        # TODO: Implement actual alert logic

        return alerts
