#!/usr/bin/env python3
"""
Generate CI health dashboard HTML page.

Creates a comprehensive dashboard showing:
- Overall CI health status
- Workflow-specific metrics
- Trends and charts
- Recent failures
- Recommendations
"""

import argparse
import json
import os
import sys
from datetime import datetime
from typing import Dict, List, Any
import base64
import io
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import Rectangle
import seaborn as sns


class DashboardGenerator:
    """Generates HTML dashboard for CI health monitoring."""
    
    def __init__(self):
        # Set style for charts
        plt.style.use('seaborn-v0_8-darkgrid')
        sns.set_palette("husl")
        
    def generate(self, metrics: Dict[str, Any], analysis: Dict[str, Any]) -> str:
        """Generate complete HTML dashboard."""
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        
        # Generate charts
        charts = self._generate_charts(metrics, analysis)
        
        # Build HTML
        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CI Health Dashboard - Jimbot</title>
    <meta http-equiv="refresh" content="300"> <!-- Auto-refresh every 5 minutes -->
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 0;
            background-color: #f5f5f5;
            color: #333;
        }}
        .header {{
            background-color: #0366d6;
            color: white;
            padding: 1rem 2rem;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 2rem;
        }}
        .status-card {{
            background: white;
            border-radius: 8px;
            padding: 1.5rem;
            margin-bottom: 2rem;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .status-header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 1rem;
        }}
        .status-indicator {{
            display: inline-block;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            margin-right: 0.5rem;
        }}
        .status-healthy {{ background-color: #28a745; }}
        .status-degraded {{ background-color: #ffc107; }}
        .status-critical {{ background-color: #dc3545; }}
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }}
        .metric-card {{
            background: white;
            border-radius: 8px;
            padding: 1.5rem;
            text-align: center;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .metric-value {{
            font-size: 2.5rem;
            font-weight: bold;
            margin: 0.5rem 0;
        }}
        .metric-label {{
            color: #666;
            font-size: 0.9rem;
        }}
        .chart-container {{
            background: white;
            border-radius: 8px;
            padding: 1.5rem;
            margin-bottom: 2rem;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .chart-image {{
            max-width: 100%;
            height: auto;
        }}
        .workflow-table {{
            width: 100%;
            border-collapse: collapse;
        }}
        .workflow-table th, .workflow-table td {{
            padding: 0.75rem;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        .workflow-table th {{
            background-color: #f8f9fa;
            font-weight: 600;
        }}
        .alert-box {{
            border-radius: 8px;
            padding: 1rem;
            margin-bottom: 1rem;
        }}
        .alert-critical {{
            background-color: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }}
        .alert-warning {{
            background-color: #fff3cd;
            color: #856404;
            border: 1px solid #ffeeba;
        }}
        .recommendations {{
            background: #e7f3ff;
            border: 1px solid #b3d7ff;
            border-radius: 8px;
            padding: 1rem;
            margin-top: 1rem;
        }}
        .recommendations h3 {{
            margin-top: 0;
            color: #0366d6;
        }}
        .recommendations ul {{
            margin-bottom: 0;
        }}
        .timestamp {{
            color: #666;
            font-size: 0.9rem;
            text-align: right;
        }}
        .failures-list {{
            list-style: none;
            padding: 0;
        }}
        .failure-item {{
            padding: 0.5rem;
            margin-bottom: 0.5rem;
            background: #f8f9fa;
            border-radius: 4px;
            font-size: 0.9rem;
        }}
        .failure-item a {{
            color: #0366d6;
            text-decoration: none;
        }}
        .failure-item a:hover {{
            text-decoration: underline;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>CI Health Dashboard</h1>
        <p>Real-time monitoring of GitHub Actions CI/CD pipeline health</p>
    </div>
    
    <div class="container">
        <p class="timestamp">Last updated: {timestamp}</p>
        
        <!-- Overall Status -->
        <div class="status-card">
            <div class="status-header">
                <h2>
                    <span class="status-indicator status-{analysis['overall_health']}"></span>
                    Overall Health: {analysis['overall_health'].title()}
                </h2>
            </div>
            
            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="metric-value">{analysis['overall_success_rate']:.1%}</div>
                    <div class="metric-label">Success Rate</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{analysis['average_duration_minutes']:.1f}</div>
                    <div class="metric-label">Avg Duration (min)</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{metrics['total_runs']}</div>
                    <div class="metric-label">Total Runs (7 days)</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{analysis['average_queue_time_seconds']:.0f}s</div>
                    <div class="metric-label">Avg Queue Time</div>
                </div>
            </div>
        </div>
        
        <!-- Alerts and Warnings -->
        {self._generate_alerts_html(analysis)}
        
        <!-- Charts -->
        <div class="chart-container">
            <h3>Success Rate by Workflow</h3>
            <img src="data:image/png;base64,{charts['success_rate_chart']}" class="chart-image" alt="Success Rate Chart">
        </div>
        
        <div class="chart-container">
            <h3>Average Duration by Workflow</h3>
            <img src="data:image/png;base64,{charts['duration_chart']}" class="chart-image" alt="Duration Chart">
        </div>
        
        <!-- Workflow Details -->
        <div class="status-card">
            <h3>Workflow Health Details</h3>
            <table class="workflow-table">
                <thead>
                    <tr>
                        <th>Workflow</th>
                        <th>Status</th>
                        <th>Success Rate</th>
                        <th>Avg Duration</th>
                        <th>Total Runs</th>
                    </tr>
                </thead>
                <tbody>
                    {self._generate_workflow_rows(analysis['workflow_health'])}
                </tbody>
            </table>
        </div>
        
        <!-- Recent Failures -->
        {self._generate_failures_html(metrics.get('recent_failures', []))}
        
        <!-- Recommendations -->
        {self._generate_recommendations_html(analysis.get('recommendations', []))}
    </div>
</body>
</html>
"""
        return html
    
    def _generate_charts(self, metrics: Dict[str, Any], analysis: Dict[str, Any]) -> Dict[str, str]:
        """Generate charts and return as base64 encoded strings."""
        charts = {}
        
        # Success rate by workflow
        workflows = []
        success_rates = []
        for name, data in metrics['workflows'].items():
            workflows.append(name)
            success_rates.append(data['success_rate'] * 100)
        
        if workflows:
            fig, ax = plt.subplots(figsize=(10, 6))
            bars = ax.bar(workflows, success_rates)
            
            # Color bars based on success rate
            for i, (bar, rate) in enumerate(zip(bars, success_rates)):
                if rate >= 90:
                    bar.set_color('#28a745')
                elif rate >= 70:
                    bar.set_color('#ffc107')
                else:
                    bar.set_color('#dc3545')
            
            ax.set_ylabel('Success Rate (%)')
            ax.set_title('Workflow Success Rates')
            ax.set_ylim(0, 100)
            
            # Add value labels on bars
            for bar, rate in zip(bars, success_rates):
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height + 1,
                       f'{rate:.1f}%', ha='center', va='bottom')
            
            plt.xticks(rotation=45, ha='right')
            plt.tight_layout()
            
            charts['success_rate_chart'] = self._fig_to_base64(fig)
            plt.close(fig)
        
        # Duration by workflow
        workflows = []
        durations = []
        for name, data in metrics['workflows'].items():
            workflows.append(name)
            durations.append(data['average_duration_minutes'])
        
        if workflows:
            fig, ax = plt.subplots(figsize=(10, 6))
            bars = ax.bar(workflows, durations)
            
            # Color bars based on duration thresholds
            for bar, duration in zip(bars, durations):
                if duration <= 10:
                    bar.set_color('#28a745')
                elif duration <= 20:
                    bar.set_color('#ffc107')
                else:
                    bar.set_color('#dc3545')
            
            ax.set_ylabel('Average Duration (minutes)')
            ax.set_title('Workflow Average Durations')
            
            # Add value labels
            for bar, duration in zip(bars, durations):
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height + 0.5,
                       f'{duration:.1f}', ha='center', va='bottom')
            
            plt.xticks(rotation=45, ha='right')
            plt.tight_layout()
            
            charts['duration_chart'] = self._fig_to_base64(fig)
            plt.close(fig)
        
        return charts
    
    def _fig_to_base64(self, fig) -> str:
        """Convert matplotlib figure to base64 string."""
        buffer = io.BytesIO()
        fig.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.read()).decode('utf-8')
        buffer.close()
        return image_base64
    
    def _generate_alerts_html(self, analysis: Dict[str, Any]) -> str:
        """Generate HTML for alerts and warnings."""
        html = ""
        
        if analysis.get('alerts'):
            for alert in analysis['alerts']:
                html += f"""
                <div class="alert-box alert-critical">
                    <strong>Alert:</strong> {alert['message']}
                </div>
                """
        
        if analysis.get('warnings'):
            for warning in analysis['warnings']:
                html += f"""
                <div class="alert-box alert-warning">
                    <strong>Warning:</strong> {warning['message']}
                </div>
                """
        
        return html
    
    def _generate_workflow_rows(self, workflow_health: Dict[str, Any]) -> str:
        """Generate table rows for workflow health."""
        rows = ""
        for name, health in workflow_health.items():
            status_class = f"status-{health['status']}"
            rows += f"""
                <tr>
                    <td>{name}</td>
                    <td><span class="status-indicator {status_class}"></span>{health['status'].title()}</td>
                    <td>{health['metrics']['success_rate']:.1%}</td>
                    <td>{health['metrics']['average_duration_minutes']:.1f} min</td>
                    <td>{health['metrics']['total_runs']}</td>
                </tr>
            """
        return rows
    
    def _generate_failures_html(self, failures: List[Dict[str, Any]]) -> str:
        """Generate HTML for recent failures."""
        if not failures:
            return ""
        
        html = """
        <div class="status-card">
            <h3>Recent Failures</h3>
            <ul class="failures-list">
        """
        
        for failure in failures[:10]:
            failed_at = datetime.fromisoformat(failure['failed_at'].replace('Z', '+00:00'))
            time_ago = self._format_time_ago(failed_at)
            
            html += f"""
                <li class="failure-item">
                    <a href="{failure['url']}" target="_blank">
                        {failure['workflow_name']} #{failure['run_number']}
                    </a>
                    - {failure['branch']} - {failure['event']} - {time_ago}
                </li>
            """
        
        html += """
            </ul>
        </div>
        """
        return html
    
    def _generate_recommendations_html(self, recommendations: List[str]) -> str:
        """Generate HTML for recommendations."""
        if not recommendations:
            return ""
        
        html = """
        <div class="recommendations">
            <h3>Recommendations</h3>
            <ul>
        """
        
        for rec in recommendations:
            html += f"<li>{rec}</li>"
        
        html += """
            </ul>
        </div>
        """
        return html
    
    def _format_time_ago(self, dt: datetime) -> str:
        """Format datetime as time ago string."""
        now = datetime.utcnow()
        if not dt.tzinfo:
            dt = dt.replace(tzinfo=None)
        else:
            dt = dt.replace(tzinfo=None)
        
        diff = now - dt
        
        if diff.days > 0:
            return f"{diff.days} days ago"
        elif diff.seconds > 3600:
            return f"{diff.seconds // 3600} hours ago"
        elif diff.seconds > 60:
            return f"{diff.seconds // 60} minutes ago"
        else:
            return "just now"


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Generate CI health dashboard')
    parser.add_argument('--metrics', required=True, help='Input metrics JSON file')
    parser.add_argument('--analysis', required=True, help='Input analysis JSON file')
    parser.add_argument('--output', required=True, help='Output HTML file')
    
    args = parser.parse_args()
    
    try:
        # Load data
        with open(args.metrics, 'r') as f:
            metrics = json.load(f)
        
        with open(args.analysis, 'r') as f:
            analysis = json.load(f)
        
        # Generate dashboard
        generator = DashboardGenerator()
        html = generator.generate(metrics, analysis)
        
        # Save HTML
        os.makedirs(os.path.dirname(args.output), exist_ok=True)
        with open(args.output, 'w') as f:
            f.write(html)
        
        print(f"Dashboard generated: {args.output}")
        
    except Exception as e:
        print(f"Error generating dashboard: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()