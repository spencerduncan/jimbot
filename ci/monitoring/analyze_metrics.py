#!/usr/bin/env python3
"""
Analyze CI metrics and determine if alerts are needed.

This script:
- Loads metrics from the collector
- Compares against defined thresholds
- Identifies anomalies and trends
- Determines if alerts should be sent
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import yaml


class MetricsAnalyzer:
    """Analyzes CI metrics for anomalies and threshold violations."""
    
    def __init__(self, thresholds: Dict[str, Any]):
        self.thresholds = thresholds
        
    def analyze(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze metrics and generate analysis report."""
        analysis = {
            'timestamp': datetime.utcnow().isoformat(),
            'alert_needed': False,
            'alerts': [],
            'warnings': [],
            'overall_health': 'healthy',
            'workflow_health': {}
        }
        
        # Check overall metrics
        overall = metrics['overall']
        analysis.update({
            'overall_success_rate': overall['success_rate'],
            'overall_failure_rate': overall['failure_rate'],
            'average_duration_minutes': overall['average_duration_minutes'],
            'average_queue_time_seconds': overall['average_queue_time_seconds']
        })
        
        # Check failure rate threshold
        if overall['failure_rate'] > self.thresholds.get('max_failure_rate', 0.3):
            analysis['alerts'].append({
                'type': 'high_failure_rate',
                'severity': 'high',
                'message': f"Overall failure rate ({overall['failure_rate']:.1%}) exceeds threshold ({self.thresholds['max_failure_rate']:.1%})",
                'value': overall['failure_rate']
            })
            analysis['alert_needed'] = True
            analysis['overall_health'] = 'critical'
        
        # Check duration increase (would need historical data for proper comparison)
        max_duration = self.thresholds.get('max_average_duration_minutes', 30)
        if overall['average_duration_minutes'] > max_duration:
            analysis['warnings'].append({
                'type': 'long_duration',
                'severity': 'medium',
                'message': f"Average duration ({overall['average_duration_minutes']:.1f} min) exceeds threshold ({max_duration} min)",
                'value': overall['average_duration_minutes']
            })
            if analysis['overall_health'] == 'healthy':
                analysis['overall_health'] = 'degraded'
        
        # Check queue time threshold
        max_queue_time = self.thresholds.get('max_queue_time_seconds', 300)
        if overall['average_queue_time_seconds'] > max_queue_time:
            analysis['warnings'].append({
                'type': 'high_queue_time',
                'severity': 'medium',
                'message': f"Average queue time ({overall['average_queue_time_seconds']:.0f}s) exceeds threshold ({max_queue_time}s)",
                'value': overall['average_queue_time_seconds']
            })
        
        # Analyze individual workflows
        for workflow_name, workflow_data in metrics['workflows'].items():
            workflow_health = self._analyze_workflow(workflow_name, workflow_data)
            analysis['workflow_health'][workflow_name] = workflow_health
            
            # Propagate critical workflow issues
            if workflow_health['status'] == 'critical':
                analysis['alert_needed'] = True
                if analysis['overall_health'] != 'critical':
                    analysis['overall_health'] = 'critical'
            elif workflow_health['status'] == 'degraded' and analysis['overall_health'] == 'healthy':
                analysis['overall_health'] = 'degraded'
        
        # Check for recent failure patterns
        if metrics.get('recent_failures'):
            failure_pattern = self._analyze_failure_pattern(metrics['recent_failures'])
            if failure_pattern:
                analysis['alerts'].append(failure_pattern)
                analysis['alert_needed'] = True
        
        # Add recommendations
        analysis['recommendations'] = self._generate_recommendations(analysis)
        
        return analysis
    
    def _analyze_workflow(self, name: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze individual workflow health."""
        workflow_analysis = {
            'name': name,
            'status': 'healthy',
            'issues': [],
            'metrics': {
                'success_rate': data['success_rate'],
                'failure_rate': data['failure_rate'],
                'average_duration_minutes': data['average_duration_minutes'],
                'total_runs': data['total_count']
            }
        }
        
        # Check workflow-specific thresholds
        workflow_thresholds = self.thresholds.get('workflows', {}).get(name, {})
        
        # Use workflow-specific or default thresholds
        max_failure_rate = workflow_thresholds.get(
            'max_failure_rate', 
            self.thresholds.get('max_failure_rate', 0.3)
        )
        
        if data['failure_rate'] > max_failure_rate:
            workflow_analysis['status'] = 'critical'
            workflow_analysis['issues'].append({
                'type': 'high_failure_rate',
                'message': f"Failure rate {data['failure_rate']:.1%} exceeds threshold {max_failure_rate:.1%}"
            })
        
        # Check for workflow-specific duration thresholds
        if name in self.thresholds.get('workflow_duration_limits', {}):
            max_duration = self.thresholds['workflow_duration_limits'][name]
            if data['average_duration_minutes'] > max_duration:
                if workflow_analysis['status'] == 'healthy':
                    workflow_analysis['status'] = 'degraded'
                workflow_analysis['issues'].append({
                    'type': 'long_duration',
                    'message': f"Average duration {data['average_duration_minutes']:.1f} min exceeds limit {max_duration} min"
                })
        
        # Check for low run count (possible issue with triggers)
        if data['total_count'] < self.thresholds.get('min_runs_per_week', 10):
            workflow_analysis['issues'].append({
                'type': 'low_run_count',
                'message': f"Only {data['total_count']} runs in the period (expected >= {self.thresholds.get('min_runs_per_week', 10)})"
            })
        
        return workflow_analysis
    
    def _analyze_failure_pattern(self, recent_failures: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Detect patterns in recent failures."""
        if len(recent_failures) < 3:
            return None
        
        # Check for repeated failures in same workflow
        workflow_failures = {}
        for failure in recent_failures[:10]:  # Look at last 10 failures
            workflow = failure['workflow_name']
            workflow_failures[workflow] = workflow_failures.get(workflow, 0) + 1
        
        # Alert if any workflow has 3+ recent failures
        for workflow, count in workflow_failures.items():
            if count >= 3:
                return {
                    'type': 'repeated_failures',
                    'severity': 'high',
                    'message': f"Workflow '{workflow}' has {count} failures in recent runs",
                    'workflow': workflow,
                    'failure_count': count
                }
        
        # Check for failures on specific branch
        branch_failures = {}
        for failure in recent_failures[:5]:
            branch = failure.get('branch', 'unknown')
            branch_failures[branch] = branch_failures.get(branch, 0) + 1
        
        for branch, count in branch_failures.items():
            if count >= 3 and branch in ['main', 'develop', 'master']:
                return {
                    'type': 'branch_failures',
                    'severity': 'critical',
                    'message': f"Critical branch '{branch}' has {count} recent failures",
                    'branch': branch,
                    'failure_count': count
                }
        
        return None
    
    def _generate_recommendations(self, analysis: Dict[str, Any]) -> List[str]:
        """Generate actionable recommendations based on analysis."""
        recommendations = []
        
        # High failure rate recommendations
        if any(a['type'] == 'high_failure_rate' for a in analysis['alerts']):
            recommendations.extend([
                "Review recent code changes for potential issues",
                "Check for flaky tests that may be causing intermittent failures",
                "Verify external dependencies and services are available"
            ])
        
        # Long duration recommendations
        if any(w['type'] == 'long_duration' for w in analysis['warnings']):
            recommendations.extend([
                "Consider parallelizing test execution",
                "Review and optimize slow-running tests",
                "Check for resource constraints on runners"
            ])
        
        # High queue time recommendations
        if any(w['type'] == 'high_queue_time' for w in analysis['warnings']):
            recommendations.extend([
                "Consider adding more concurrent job runners",
                "Review workflow triggers to reduce concurrent runs",
                "Check GitHub Actions service status"
            ])
        
        # Repeated failures recommendations
        if any(a['type'] == 'repeated_failures' for a in analysis['alerts']):
            recommendations.extend([
                "Investigate the specific failing workflow for root cause",
                "Consider temporarily disabling the workflow if not critical",
                "Review recent changes to the workflow configuration"
            ])
        
        return list(set(recommendations))  # Remove duplicates


def load_default_thresholds() -> Dict[str, Any]:
    """Load default threshold values."""
    return {
        'max_failure_rate': 0.3,  # 30% failure rate
        'max_average_duration_minutes': 30,
        'max_queue_time_seconds': 300,  # 5 minutes
        'min_runs_per_week': 10,
        'workflow_duration_limits': {
            'CI Quick Checks': 10,
            'CI Test Suite': 20,
            'CI Integration Tests': 30
        },
        'workflows': {
            'CI Quick Checks': {
                'max_failure_rate': 0.1  # More strict for quick checks
            }
        }
    }


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Analyze CI metrics')
    parser.add_argument('--metrics', required=True, help='Input metrics JSON file')
    parser.add_argument('--thresholds', help='Thresholds YAML file')
    parser.add_argument('--output', required=True, help='Output analysis JSON file')
    
    args = parser.parse_args()
    
    try:
        # Load metrics
        with open(args.metrics, 'r') as f:
            metrics = json.load(f)
        
        # Load thresholds
        if args.thresholds and os.path.exists(args.thresholds):
            with open(args.thresholds, 'r') as f:
                thresholds = yaml.safe_load(f)
        else:
            thresholds = load_default_thresholds()
        
        # Analyze metrics
        analyzer = MetricsAnalyzer(thresholds)
        analysis = analyzer.analyze(metrics)
        
        # Save analysis
        os.makedirs(os.path.dirname(args.output), exist_ok=True)
        with open(args.output, 'w') as f:
            json.dump(analysis, f, indent=2)
        
        # Print summary
        print(f"Analysis complete: {analysis['overall_health']}")
        print(f"Alert needed: {analysis['alert_needed']}")
        
        if analysis['alerts']:
            print("\nAlerts:")
            for alert in analysis['alerts']:
                print(f"  - [{alert['severity']}] {alert['message']}")
        
        if analysis['warnings']:
            print("\nWarnings:")
            for warning in analysis['warnings']:
                print(f"  - [{warning['severity']}] {warning['message']}")
        
        if analysis['recommendations']:
            print("\nRecommendations:")
            for rec in analysis['recommendations']:
                print(f"  - {rec}")
        
    except Exception as e:
        print(f"Error analyzing metrics: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()