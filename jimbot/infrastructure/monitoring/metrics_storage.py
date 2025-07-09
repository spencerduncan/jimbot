"""Historical Metrics Storage for CI Health Monitoring

Provides persistent storage and retrieval of CI health metrics over time.
"""

import asyncio
import json
import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class MetricPoint:
    """Individual metric data point"""
    timestamp: datetime
    metric_name: str
    value: float
    labels: Dict[str, str]
    component: str


@dataclass
class WorkflowMetrics:
    """Workflow-specific metrics snapshot"""
    timestamp: datetime
    workflow_name: str
    success_rate: float
    avg_duration: float
    total_runs: int
    successful_runs: int
    failed_runs: int
    status: str


@dataclass
class SystemHealthSnapshot:
    """System health snapshot"""
    timestamp: datetime
    overall_status: str
    overall_success_rate: float
    healthy_checks: int
    total_checks: int
    active_alerts: int
    workflow_metrics: List[WorkflowMetrics]


class MetricsStorage:
    """Persistent storage for CI health metrics"""
    
    def __init__(self, db_path: str = "ci_metrics.db"):
        self.db_path = Path(db_path)
        self.connection = None
        self._ensure_database()
    
    def _ensure_database(self):
        """Ensure database and tables exist"""
        try:
            # Create database directory if it doesn't exist
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Initialize database
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS metric_points (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        metric_name TEXT NOT NULL,
                        value REAL NOT NULL,
                        component TEXT NOT NULL,
                        labels TEXT,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS workflow_metrics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        workflow_name TEXT NOT NULL,
                        success_rate REAL NOT NULL,
                        avg_duration REAL NOT NULL,
                        total_runs INTEGER NOT NULL,
                        successful_runs INTEGER NOT NULL,
                        failed_runs INTEGER NOT NULL,
                        status TEXT NOT NULL,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS system_health_snapshots (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        overall_status TEXT NOT NULL,
                        overall_success_rate REAL NOT NULL,
                        healthy_checks INTEGER NOT NULL,
                        total_checks INTEGER NOT NULL,
                        active_alerts INTEGER NOT NULL,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Create indexes for better query performance
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_metric_points_timestamp 
                    ON metric_points(timestamp)
                """)
                
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_metric_points_name_component 
                    ON metric_points(metric_name, component)
                """)
                
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_workflow_metrics_timestamp 
                    ON workflow_metrics(timestamp)
                """)
                
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_workflow_metrics_name 
                    ON workflow_metrics(workflow_name)
                """)
                
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_system_health_timestamp 
                    ON system_health_snapshots(timestamp)
                """)
                
                conn.commit()
                logger.info(f"Database initialized at {self.db_path}")
                
        except Exception as e:
            logger.error(f"Failed to initialize database: {str(e)}")
            raise
    
    async def store_metric_point(self, metric: MetricPoint):
        """Store individual metric point"""
        try:
            labels_json = json.dumps(metric.labels) if metric.labels else None
            
            def store():
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("""
                        INSERT INTO metric_points 
                        (timestamp, metric_name, value, component, labels)
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        metric.timestamp.isoformat(),
                        metric.metric_name,
                        metric.value,
                        metric.component,
                        labels_json
                    ))
                    conn.commit()
            
            await asyncio.to_thread(store)
            
        except Exception as e:
            logger.error(f"Failed to store metric point: {str(e)}")
            raise
    
    async def store_workflow_metrics(self, metrics: WorkflowMetrics):
        """Store workflow metrics snapshot"""
        try:
            def store():
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("""
                        INSERT INTO workflow_metrics 
                        (timestamp, workflow_name, success_rate, avg_duration, 
                         total_runs, successful_runs, failed_runs, status)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        metrics.timestamp.isoformat(),
                        metrics.workflow_name,
                        metrics.success_rate,
                        metrics.avg_duration,
                        metrics.total_runs,
                        metrics.successful_runs,
                        metrics.failed_runs,
                        metrics.status
                    ))
                    conn.commit()
            
            await asyncio.to_thread(store)
            
        except Exception as e:
            logger.error(f"Failed to store workflow metrics: {str(e)}")
            raise
    
    async def store_system_health_snapshot(self, snapshot: SystemHealthSnapshot):
        """Store system health snapshot"""
        try:
            def store():
                with sqlite3.connect(self.db_path) as conn:
                    # Store system health snapshot
                    conn.execute("""
                        INSERT INTO system_health_snapshots 
                        (timestamp, overall_status, overall_success_rate, 
                         healthy_checks, total_checks, active_alerts)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        snapshot.timestamp.isoformat(),
                        snapshot.overall_status,
                        snapshot.overall_success_rate,
                        snapshot.healthy_checks,
                        snapshot.total_checks,
                        snapshot.active_alerts
                    ))
                    
                    # Store associated workflow metrics
                    for workflow_metrics in snapshot.workflow_metrics:
                        conn.execute("""
                            INSERT INTO workflow_metrics 
                            (timestamp, workflow_name, success_rate, avg_duration, 
                             total_runs, successful_runs, failed_runs, status)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            workflow_metrics.timestamp.isoformat(),
                            workflow_metrics.workflow_name,
                            workflow_metrics.success_rate,
                            workflow_metrics.avg_duration,
                            workflow_metrics.total_runs,
                            workflow_metrics.successful_runs,
                            workflow_metrics.failed_runs,
                            workflow_metrics.status
                        ))
                    
                    conn.commit()
            
            await asyncio.to_thread(store)
            
        except Exception as e:
            logger.error(f"Failed to store system health snapshot: {str(e)}")
            raise
    
    async def get_metric_history(self, 
                                metric_name: str, 
                                component: str = None,
                                hours: int = 24) -> List[MetricPoint]:
        """Get metric history for specified period"""
        try:
            cutoff = datetime.now() - timedelta(hours=hours)
            
            def query():
                with sqlite3.connect(self.db_path) as conn:
                    if component:
                        cursor = conn.execute("""
                            SELECT timestamp, metric_name, value, component, labels
                            FROM metric_points
                            WHERE metric_name = ? AND component = ? AND timestamp >= ?
                            ORDER BY timestamp
                        """, (metric_name, component, cutoff.isoformat()))
                    else:
                        cursor = conn.execute("""
                            SELECT timestamp, metric_name, value, component, labels
                            FROM metric_points
                            WHERE metric_name = ? AND timestamp >= ?
                            ORDER BY timestamp
                        """, (metric_name, cutoff.isoformat()))
                    
                    return cursor.fetchall()
            
            rows = await asyncio.to_thread(query)
            
            metrics = []
            for row in rows:
                timestamp, name, value, comp, labels_json = row
                labels = json.loads(labels_json) if labels_json else {}
                
                metrics.append(MetricPoint(
                    timestamp=datetime.fromisoformat(timestamp),
                    metric_name=name,
                    value=value,
                    component=comp,
                    labels=labels
                ))
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to get metric history: {str(e)}")
            return []
    
    async def get_workflow_history(self, 
                                  workflow_name: str = None,
                                  hours: int = 24) -> List[WorkflowMetrics]:
        """Get workflow metrics history"""
        try:
            cutoff = datetime.now() - timedelta(hours=hours)
            
            def query():
                with sqlite3.connect(self.db_path) as conn:
                    if workflow_name:
                        cursor = conn.execute("""
                            SELECT timestamp, workflow_name, success_rate, avg_duration,
                                   total_runs, successful_runs, failed_runs, status
                            FROM workflow_metrics
                            WHERE workflow_name = ? AND timestamp >= ?
                            ORDER BY timestamp
                        """, (workflow_name, cutoff.isoformat()))
                    else:
                        cursor = conn.execute("""
                            SELECT timestamp, workflow_name, success_rate, avg_duration,
                                   total_runs, successful_runs, failed_runs, status
                            FROM workflow_metrics
                            WHERE timestamp >= ?
                            ORDER BY timestamp
                        """, (cutoff.isoformat(),))
                    
                    return cursor.fetchall()
            
            rows = await asyncio.to_thread(query)
            
            workflows = []
            for row in rows:
                timestamp, name, success_rate, avg_duration, total_runs, successful_runs, failed_runs, status = row
                
                workflows.append(WorkflowMetrics(
                    timestamp=datetime.fromisoformat(timestamp),
                    workflow_name=name,
                    success_rate=success_rate,
                    avg_duration=avg_duration,
                    total_runs=total_runs,
                    successful_runs=successful_runs,
                    failed_runs=failed_runs,
                    status=status
                ))
            
            return workflows
            
        except Exception as e:
            logger.error(f"Failed to get workflow history: {str(e)}")
            return []
    
    async def get_system_health_history(self, hours: int = 24) -> List[SystemHealthSnapshot]:
        """Get system health snapshots history"""
        try:
            cutoff = datetime.now() - timedelta(hours=hours)
            
            def query():
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.execute("""
                        SELECT timestamp, overall_status, overall_success_rate,
                               healthy_checks, total_checks, active_alerts
                        FROM system_health_snapshots
                        WHERE timestamp >= ?
                        ORDER BY timestamp
                    """, (cutoff.isoformat(),))
                    
                    return cursor.fetchall()
            
            rows = await asyncio.to_thread(query)
            
            snapshots = []
            for row in rows:
                timestamp, overall_status, overall_success_rate, healthy_checks, total_checks, active_alerts = row
                
                # Get workflow metrics for this timestamp
                workflow_metrics = await self.get_workflow_history_at_time(datetime.fromisoformat(timestamp))
                
                snapshots.append(SystemHealthSnapshot(
                    timestamp=datetime.fromisoformat(timestamp),
                    overall_status=overall_status,
                    overall_success_rate=overall_success_rate,
                    healthy_checks=healthy_checks,
                    total_checks=total_checks,
                    active_alerts=active_alerts,
                    workflow_metrics=workflow_metrics
                ))
            
            return snapshots
            
        except Exception as e:
            logger.error(f"Failed to get system health history: {str(e)}")
            return []
    
    async def get_workflow_history_at_time(self, timestamp: datetime) -> List[WorkflowMetrics]:
        """Get workflow metrics closest to a specific timestamp"""
        try:
            # Get metrics within 10 minutes of the specified timestamp
            time_window = timedelta(minutes=10)
            start_time = timestamp - time_window
            end_time = timestamp + time_window
            
            def query():
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.execute("""
                        SELECT timestamp, workflow_name, success_rate, avg_duration,
                               total_runs, successful_runs, failed_runs, status
                        FROM workflow_metrics
                        WHERE timestamp BETWEEN ? AND ?
                        ORDER BY ABS(julianday(timestamp) - julianday(?))
                    """, (start_time.isoformat(), end_time.isoformat(), timestamp.isoformat()))
                    
                    return cursor.fetchall()
            
            rows = await asyncio.to_thread(query)
            
            workflows = []
            seen_workflows = set()
            
            for row in rows:
                ts, name, success_rate, avg_duration, total_runs, successful_runs, failed_runs, status = row
                
                # Only include each workflow once (closest to target timestamp)
                if name not in seen_workflows:
                    seen_workflows.add(name)
                    workflows.append(WorkflowMetrics(
                        timestamp=datetime.fromisoformat(ts),
                        workflow_name=name,
                        success_rate=success_rate,
                        avg_duration=avg_duration,
                        total_runs=total_runs,
                        successful_runs=successful_runs,
                        failed_runs=failed_runs,
                        status=status
                    ))
            
            return workflows
            
        except Exception as e:
            logger.error(f"Failed to get workflow history at time: {str(e)}")
            return []
    
    async def get_metric_aggregates(self, 
                                   metric_name: str,
                                   component: str = None,
                                   hours: int = 24) -> Dict[str, float]:
        """Get metric aggregates (min, max, avg) for specified period"""
        try:
            cutoff = datetime.now() - timedelta(hours=hours)
            
            def query():
                with sqlite3.connect(self.db_path) as conn:
                    if component:
                        cursor = conn.execute("""
                            SELECT MIN(value), MAX(value), AVG(value), COUNT(*)
                            FROM metric_points
                            WHERE metric_name = ? AND component = ? AND timestamp >= ?
                        """, (metric_name, component, cutoff.isoformat()))
                    else:
                        cursor = conn.execute("""
                            SELECT MIN(value), MAX(value), AVG(value), COUNT(*)
                            FROM metric_points
                            WHERE metric_name = ? AND timestamp >= ?
                        """, (metric_name, cutoff.isoformat()))
                    
                    return cursor.fetchone()
            
            result = await asyncio.to_thread(query)
            
            if result and result[3] > 0:  # Check if we have data points
                min_val, max_val, avg_val, count = result
                return {
                    'min': min_val,
                    'max': max_val,
                    'avg': avg_val,
                    'count': count
                }
            else:
                return {
                    'min': 0.0,
                    'max': 0.0,
                    'avg': 0.0,
                    'count': 0
                }
                
        except Exception as e:
            logger.error(f"Failed to get metric aggregates: {str(e)}")
            return {}
    
    async def cleanup_old_data(self, retention_days: int = 30):
        """Clean up old metric data beyond retention period"""
        try:
            cutoff = datetime.now() - timedelta(days=retention_days)
            
            def cleanup():
                with sqlite3.connect(self.db_path) as conn:
                    # Clean up old metric points
                    cursor = conn.execute("""
                        DELETE FROM metric_points WHERE timestamp < ?
                    """, (cutoff.isoformat(),))
                    metric_points_deleted = cursor.rowcount
                    
                    # Clean up old workflow metrics
                    cursor = conn.execute("""
                        DELETE FROM workflow_metrics WHERE timestamp < ?
                    """, (cutoff.isoformat(),))
                    workflow_metrics_deleted = cursor.rowcount
                    
                    # Clean up old system health snapshots
                    cursor = conn.execute("""
                        DELETE FROM system_health_snapshots WHERE timestamp < ?
                    """, (cutoff.isoformat(),))
                    snapshots_deleted = cursor.rowcount
                    
                    conn.commit()
                    
                    return metric_points_deleted, workflow_metrics_deleted, snapshots_deleted
            
            deleted_counts = await asyncio.to_thread(cleanup)
            
            logger.info(f"Cleaned up old data: {deleted_counts[0]} metric points, "
                       f"{deleted_counts[1]} workflow metrics, {deleted_counts[2]} health snapshots")
            
            return deleted_counts
            
        except Exception as e:
            logger.error(f"Failed to cleanup old data: {str(e)}")
            raise
    
    async def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        try:
            def query_stats():
                with sqlite3.connect(self.db_path) as conn:
                    # Get table sizes
                    metric_points_count = conn.execute("SELECT COUNT(*) FROM metric_points").fetchone()[0]
                    workflow_metrics_count = conn.execute("SELECT COUNT(*) FROM workflow_metrics").fetchone()[0]
                    snapshots_count = conn.execute("SELECT COUNT(*) FROM system_health_snapshots").fetchone()[0]
                    
                    # Get date ranges
                    metric_points_range = conn.execute("""
                        SELECT MIN(timestamp), MAX(timestamp) FROM metric_points
                    """).fetchone()
                    
                    workflow_metrics_range = conn.execute("""
                        SELECT MIN(timestamp), MAX(timestamp) FROM workflow_metrics
                    """).fetchone()
                    
                    snapshots_range = conn.execute("""
                        SELECT MIN(timestamp), MAX(timestamp) FROM system_health_snapshots
                    """).fetchone()
                    
                    return {
                        'metric_points_count': metric_points_count,
                        'workflow_metrics_count': workflow_metrics_count,
                        'snapshots_count': snapshots_count,
                        'metric_points_range': metric_points_range,
                        'workflow_metrics_range': workflow_metrics_range,
                        'snapshots_range': snapshots_range
                    }
            
            stats = await asyncio.to_thread(query_stats)
            
            # Add file size
            file_size = self.db_path.stat().st_size if self.db_path.exists() else 0
            stats['database_size_bytes'] = file_size
            stats['database_size_mb'] = file_size / (1024 * 1024)
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get database stats: {str(e)}")
            return {}