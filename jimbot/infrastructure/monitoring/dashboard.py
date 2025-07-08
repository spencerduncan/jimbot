"""CI Dashboard Module

Web-based dashboard for CI health monitoring and metrics visualization.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict

from .ci_health import CIHealthMonitor, CISystemHealth, CIHealthStatus

logger = logging.getLogger(__name__)


@dataclass
class DashboardData:
    """Dashboard data structure"""
    timestamp: datetime
    system_health: CISystemHealth
    historical_metrics: Dict[str, List[Dict[str, Any]]]
    alerts: List[Dict[str, Any]]
    trends: Dict[str, Any]


class CIDashboard:
    """CI Health Dashboard"""
    
    def __init__(self, health_monitor: CIHealthMonitor):
        self.health_monitor = health_monitor
        self.data_retention_days = 30
        self.metrics_cache = {}
        self.trends_cache = {}
        
    async def generate_dashboard_data(self) -> DashboardData:
        """Generate comprehensive dashboard data"""
        try:
            # Get current system health
            system_health = await self.health_monitor.get_system_health()
            
            # Get historical metrics
            historical_metrics = await self._get_historical_metrics()
            
            # Calculate trends
            trends = await self._calculate_trends(historical_metrics)
            
            # Get recent alerts
            alerts = await self._get_recent_alerts()
            
            return DashboardData(
                timestamp=datetime.now(),
                system_health=system_health,
                historical_metrics=historical_metrics,
                alerts=alerts,
                trends=trends
            )
            
        except Exception as e:
            logger.error(f"Failed to generate dashboard data: {str(e)}")
            raise
    
    async def _get_historical_metrics(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get historical metrics for dashboard"""
        try:
            metrics = {}
            
            # Get success rate history
            metrics['success_rate'] = await self._get_success_rate_history()
            
            # Get workflow performance history
            metrics['workflow_performance'] = await self._get_workflow_performance_history()
            
            # Get system health history
            metrics['system_health'] = await self._get_system_health_history()
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to get historical metrics: {str(e)}")
            return {}
    
    async def _get_success_rate_history(self) -> List[Dict[str, Any]]:
        """Get success rate history over time"""
        try:
            history = []
            
            # Get data for last 30 days
            for days_back in range(30, 0, -1):
                date = datetime.now() - timedelta(days=days_back)
                
                # Calculate success rate for that day
                success_rate = await self._calculate_daily_success_rate(date)
                
                history.append({
                    'date': date.isoformat(),
                    'success_rate': success_rate,
                    'timestamp': date.timestamp()
                })
            
            return history
            
        except Exception as e:
            logger.error(f"Failed to get success rate history: {str(e)}")
            return []
    
    async def _calculate_daily_success_rate(self, date: datetime) -> float:
        """Calculate success rate for a specific day"""
        try:
            # This would ideally query stored metrics
            # For now, simulate with recent data
            system_health = await self.health_monitor.get_system_health()
            return system_health.system_metrics.get('overall_success_rate', 0.0)
            
        except Exception as e:
            logger.error(f"Failed to calculate daily success rate: {str(e)}")
            return 0.0
    
    async def _get_workflow_performance_history(self) -> List[Dict[str, Any]]:
        """Get workflow performance history"""
        try:
            history = []
            
            # Get current workflow health
            system_health = await self.health_monitor.get_system_health()
            
            for workflow_name, workflow_health in system_health.workflow_health.items():
                workflow_data = {
                    'workflow_name': workflow_name,
                    'success_rate': workflow_health.success_rate,
                    'avg_duration': workflow_health.avg_duration,
                    'status': workflow_health.status.value,
                    'recent_failures': len(workflow_health.recent_failures),
                    'last_run': workflow_health.last_run.isoformat() if workflow_health.last_run else None
                }
                history.append(workflow_data)
            
            return history
            
        except Exception as e:
            logger.error(f"Failed to get workflow performance history: {str(e)}")
            return []
    
    async def _get_system_health_history(self) -> List[Dict[str, Any]]:
        """Get system health component history"""
        try:
            history = []
            
            # Get current health check results
            health_results = await self.health_monitor.health_checker.run_checks()
            
            for component, result in health_results.items():
                component_data = {
                    'component': component,
                    'status': result.status.value,
                    'message': result.message,
                    'metrics': result.metrics,
                    'timestamp': result.timestamp
                }
                history.append(component_data)
            
            return history
            
        except Exception as e:
            logger.error(f"Failed to get system health history: {str(e)}")
            return []
    
    async def _calculate_trends(self, historical_metrics: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        """Calculate trends from historical data"""
        try:
            trends = {}
            
            # Success rate trend
            success_rate_data = historical_metrics.get('success_rate', [])
            if len(success_rate_data) >= 2:
                recent_rate = success_rate_data[-1]['success_rate']
                previous_rate = success_rate_data[-2]['success_rate']
                trends['success_rate_trend'] = {
                    'direction': 'up' if recent_rate > previous_rate else 'down' if recent_rate < previous_rate else 'stable',
                    'change': recent_rate - previous_rate,
                    'current': recent_rate,
                    'previous': previous_rate
                }
            
            # Workflow performance trends
            workflow_data = historical_metrics.get('workflow_performance', [])
            workflow_trends = {}
            
            for workflow in workflow_data:
                workflow_name = workflow['workflow_name']
                workflow_trends[workflow_name] = {
                    'success_rate': workflow['success_rate'],
                    'status': workflow['status'],
                    'trend': 'stable'  # Would calculate from historical data
                }
            
            trends['workflow_trends'] = workflow_trends
            
            return trends
            
        except Exception as e:
            logger.error(f"Failed to calculate trends: {str(e)}")
            return {}
    
    async def _get_recent_alerts(self) -> List[Dict[str, Any]]:
        """Get recent alerts for dashboard"""
        try:
            # Get current system health with alerts
            system_health = await self.health_monitor.get_system_health()
            
            # Add timestamps and format for display
            alerts = []
            for alert in system_health.alerts:
                alert_data = {
                    **alert,
                    'formatted_time': datetime.fromtimestamp(alert['timestamp']).strftime('%Y-%m-%d %H:%M:%S'),
                    'age_minutes': (datetime.now().timestamp() - alert['timestamp']) / 60
                }
                alerts.append(alert_data)
            
            # Sort by timestamp (newest first)
            alerts.sort(key=lambda x: x['timestamp'], reverse=True)
            
            return alerts
            
        except Exception as e:
            logger.error(f"Failed to get recent alerts: {str(e)}")
            return []
    
    async def generate_html_dashboard(self) -> str:
        """Generate HTML dashboard"""
        try:
            dashboard_data = await self.generate_dashboard_data()
            
            html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CI Health Dashboard</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .dashboard {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        .header {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }}
        .status-cards {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }}
        .card {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .status-healthy {{ border-left: 4px solid #28a745; }}
        .status-degraded {{ border-left: 4px solid #ffc107; }}
        .status-unhealthy {{ border-left: 4px solid #dc3545; }}
        .status-critical {{ border-left: 4px solid #6f42c1; }}
        .metric-value {{
            font-size: 2rem;
            font-weight: bold;
            margin: 10px 0;
        }}
        .metric-label {{
            color: #666;
            font-size: 0.9rem;
        }}
        .workflow-list {{
            list-style: none;
            padding: 0;
        }}
        .workflow-item {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px 0;
            border-bottom: 1px solid #eee;
        }}
        .workflow-status {{
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.8rem;
            font-weight: bold;
        }}
        .alert-item {{
            padding: 15px;
            margin: 10px 0;
            border-radius: 4px;
            border-left: 4px solid #dc3545;
        }}
        .alert-critical {{ background-color: #f8d7da; }}
        .alert-warning {{ background-color: #fff3cd; border-left-color: #ffc107; }}
        .refresh-time {{
            color: #666;
            font-size: 0.8rem;
            text-align: center;
            margin-top: 20px;
        }}
    </style>
</head>
<body>
    <div class="dashboard">
        <div class="header">
            <h1>CI Health Dashboard</h1>
            <p>Real-time monitoring of CI/CD pipeline health and performance</p>
        </div>
        
        <div class="status-cards">
            <div class="card status-{dashboard_data.system_health.overall_status.value}">
                <div class="metric-label">Overall Status</div>
                <div class="metric-value">{dashboard_data.system_health.overall_status.value.title()}</div>
                <div class="metric-label">Success Rate: {dashboard_data.system_health.system_metrics.get('overall_success_rate', 0):.1f}%</div>
            </div>
            
            <div class="card">
                <div class="metric-label">Active Workflows</div>
                <div class="metric-value">{len(dashboard_data.system_health.workflow_health)}</div>
                <div class="metric-label">Health Checks: {dashboard_data.system_health.system_metrics.get('healthy_checks', 0)}/{dashboard_data.system_health.system_metrics.get('total_checks', 0)}</div>
            </div>
            
            <div class="card">
                <div class="metric-label">Active Alerts</div>
                <div class="metric-value">{len(dashboard_data.alerts)}</div>
                <div class="metric-label">Last Update: {dashboard_data.timestamp.strftime('%H:%M:%S')}</div>
            </div>
        </div>
        
        <div class="card">
            <h2>Workflow Status</h2>
            <ul class="workflow-list">
                {self._generate_workflow_html(dashboard_data.system_health.workflow_health)}
            </ul>
        </div>
        
        {self._generate_alerts_html(dashboard_data.alerts)}
        
        <div class="refresh-time">
            Last refreshed: {dashboard_data.timestamp.strftime('%Y-%m-%d %H:%M:%S')}
        </div>
    </div>
    
    <script>
        // Auto-refresh every 5 minutes
        setTimeout(function() {{
            location.reload();
        }}, 5 * 60 * 1000);
    </script>
</body>
</html>
"""
            
            return html_content
            
        except Exception as e:
            logger.error(f"Failed to generate HTML dashboard: {str(e)}")
            return self._generate_error_html(str(e))
    
    def _generate_workflow_html(self, workflow_health: Dict[str, Any]) -> str:
        """Generate HTML for workflow status"""
        html = ""
        
        for workflow_name, health in workflow_health.items():
            status_class = f"workflow-status status-{health.status.value}"
            
            html += f"""
                <li class="workflow-item">
                    <div>
                        <strong>{workflow_name}</strong>
                        <br>
                        <small>Success Rate: {health.success_rate:.1f}%</small>
                    </div>
                    <div class="{status_class}">
                        {health.status.value.title()}
                    </div>
                </li>
            """
        
        return html
    
    def _generate_alerts_html(self, alerts: List[Dict[str, Any]]) -> str:
        """Generate HTML for alerts section"""
        if not alerts:
            return ""
        
        html = '<div class="card"><h2>Active Alerts</h2>'
        
        for alert in alerts:
            alert_class = f"alert-{alert['severity']}"
            
            html += f"""
                <div class="alert-item {alert_class}">
                    <strong>{alert['type'].replace('_', ' ').title()}</strong>
                    <br>
                    Component: {alert['component']}
                    <br>
                    {alert['message']}
                    <br>
                    <small>{alert['formatted_time']} ({alert['age_minutes']:.0f} minutes ago)</small>
                </div>
            """
        
        html += '</div>'
        return html
    
    def _generate_error_html(self, error_message: str) -> str:
        """Generate error HTML page"""
        return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CI Dashboard Error</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .error-container {{
            max-width: 600px;
            margin: 0 auto;
            background: white;
            padding: 40px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            text-align: center;
        }}
        .error-message {{
            color: #dc3545;
            font-size: 1.2rem;
            margin: 20px 0;
        }}
    </style>
</head>
<body>
    <div class="error-container">
        <h1>Dashboard Error</h1>
        <div class="error-message">
            Failed to load dashboard data: {error_message}
        </div>
        <p>Please try refreshing the page or contact your administrator.</p>
    </div>
</body>
</html>
"""
    
    async def save_dashboard_html(self, output_path: str = "ci-dashboard.html"):
        """Save dashboard HTML to file"""
        try:
            html_content = await self.generate_html_dashboard()
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            logger.info(f"Dashboard HTML saved to {output_path}")
            
        except Exception as e:
            logger.error(f"Failed to save dashboard HTML: {str(e)}")
            raise
    
    async def generate_json_data(self) -> str:
        """Generate JSON data for API consumption"""
        try:
            dashboard_data = await self.generate_dashboard_data()
            
            # Convert to JSON-serializable format
            json_data = {
                'timestamp': dashboard_data.timestamp.isoformat(),
                'system_health': {
                    'overall_status': dashboard_data.system_health.overall_status.value,
                    'system_metrics': dashboard_data.system_health.system_metrics,
                    'workflow_health': {
                        name: {
                            'workflow_name': health.workflow_name,
                            'status': health.status.value,
                            'success_rate': health.success_rate,
                            'avg_duration': health.avg_duration,
                            'recent_failures': health.recent_failures,
                            'last_run': health.last_run.isoformat() if health.last_run else None,
                            'metrics': health.metrics
                        }
                        for name, health in dashboard_data.system_health.workflow_health.items()
                    }
                },
                'alerts': dashboard_data.alerts,
                'trends': dashboard_data.trends,
                'historical_metrics': dashboard_data.historical_metrics
            }
            
            return json.dumps(json_data, indent=2)
            
        except Exception as e:
            logger.error(f"Failed to generate JSON data: {str(e)}")
            raise