#!/usr/bin/env python3
"""
Collect CI metrics from GitHub Actions API.

This script collects workflow run data including:
- Success/failure rates
- Duration statistics
- Queue times
- Test coverage (if available)
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional
import requests


class GitHubMetricsCollector:
    """Collects CI metrics from GitHub Actions API."""
    
    def __init__(self, repo: str, token: str):
        self.repo = repo
        self.token = token
        self.headers = {
            'Authorization': f'token {token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        self.base_url = f'https://api.github.com/repos/{repo}'
        
    def collect_workflow_runs(self, days: int = 7) -> List[Dict[str, Any]]:
        """Collect workflow runs from the past N days."""
        since = datetime.now(timezone.utc) - timedelta(days=days)
        runs = []
        
        # Get all workflows
        workflows_url = f'{self.base_url}/actions/workflows'
        response = requests.get(workflows_url, headers=self.headers)
        response.raise_for_status()
        workflows = response.json()['workflows']
        
        # Collect runs for each workflow
        for workflow in workflows:
            if workflow['state'] != 'active':
                continue
                
            runs_url = f"{self.base_url}/actions/workflows/{workflow['id']}/runs"
            params = {
                'created': f'>={since.isoformat()}',
                'per_page': 100
            }
            
            while runs_url:
                response = requests.get(runs_url, headers=self.headers, params=params)
                response.raise_for_status()
                data = response.json()
                
                for run in data['workflow_runs']:
                    runs.append({
                        'id': run['id'],
                        'workflow_name': workflow['name'],
                        'workflow_id': workflow['id'],
                        'status': run['status'],
                        'conclusion': run['conclusion'],
                        'created_at': run['created_at'],
                        'updated_at': run['updated_at'],
                        'run_started_at': run['run_started_at'],
                        'html_url': run['html_url'],
                        'branch': run['head_branch'],
                        'event': run['event'],
                        'run_number': run['run_number'],
                        'duration_seconds': self._calculate_duration(run),
                        'queue_time_seconds': self._calculate_queue_time(run)
                    })
                
                # Check for next page
                runs_url = response.links.get('next', {}).get('url')
                params = {}  # Clear params for pagination
                
        return runs
    
    def _calculate_duration(self, run: Dict[str, Any]) -> Optional[float]:
        """Calculate run duration in seconds."""
        if run['status'] != 'completed' or not run['run_started_at']:
            return None
            
        started = datetime.fromisoformat(run['run_started_at'].replace('Z', '+00:00'))
        updated = datetime.fromisoformat(run['updated_at'].replace('Z', '+00:00'))
        return (updated - started).total_seconds()
    
    def _calculate_queue_time(self, run: Dict[str, Any]) -> Optional[float]:
        """Calculate queue time in seconds."""
        if not run['run_started_at']:
            return None
            
        created = datetime.fromisoformat(run['created_at'].replace('Z', '+00:00'))
        started = datetime.fromisoformat(run['run_started_at'].replace('Z', '+00:00'))
        return (started - created).total_seconds()
    
    def collect_job_metrics(self, run_id: int) -> List[Dict[str, Any]]:
        """Collect job-level metrics for a specific run."""
        jobs_url = f'{self.base_url}/actions/runs/{run_id}/jobs'
        response = requests.get(jobs_url, headers=self.headers)
        response.raise_for_status()
        
        jobs = []
        for job in response.json()['jobs']:
            jobs.append({
                'id': job['id'],
                'name': job['name'],
                'status': job['status'],
                'conclusion': job['conclusion'],
                'started_at': job['started_at'],
                'completed_at': job['completed_at'],
                'duration_seconds': self._calculate_job_duration(job)
            })
        return jobs
    
    def _calculate_job_duration(self, job: Dict[str, Any]) -> Optional[float]:
        """Calculate job duration in seconds."""
        if not job['started_at'] or not job['completed_at']:
            return None
            
        started = datetime.fromisoformat(job['started_at'].replace('Z', '+00:00'))
        completed = datetime.fromisoformat(job['completed_at'].replace('Z', '+00:00'))
        return (completed - started).total_seconds()
    
    def collect_test_coverage(self) -> Optional[Dict[str, float]]:
        """Collect test coverage metrics if available."""
        # Check for coverage reports in recent artifacts
        # This is a simplified implementation - real implementation would
        # parse coverage reports from artifacts or use coverage services
        return {
            'python_coverage': None,  # Would parse from coverage.xml
            'rust_coverage': None,    # Would parse from tarpaulin output
            'overall_coverage': None
        }
    
    def generate_metrics_summary(self, runs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate summary statistics from workflow runs."""
        if not runs:
            return {
                'total_runs': 0,
                'workflows': {},
                'overall': {
                    'success_rate': 0,
                    'failure_rate': 0,
                    'average_duration_minutes': 0,
                    'average_queue_time_seconds': 0
                }
            }
        
        # Group by workflow
        workflows = {}
        for run in runs:
            workflow_name = run['workflow_name']
            if workflow_name not in workflows:
                workflows[workflow_name] = {
                    'runs': [],
                    'success_count': 0,
                    'failure_count': 0,
                    'total_count': 0,
                    'durations': [],
                    'queue_times': []
                }
            
            workflows[workflow_name]['runs'].append(run)
            workflows[workflow_name]['total_count'] += 1
            
            if run['conclusion'] == 'success':
                workflows[workflow_name]['success_count'] += 1
            elif run['conclusion'] in ['failure', 'timed_out']:
                workflows[workflow_name]['failure_count'] += 1
                
            if run['duration_seconds']:
                workflows[workflow_name]['durations'].append(run['duration_seconds'])
            if run['queue_time_seconds']:
                workflows[workflow_name]['queue_times'].append(run['queue_time_seconds'])
        
        # Calculate workflow statistics
        for workflow_name, data in workflows.items():
            total = data['total_count']
            data['success_rate'] = data['success_count'] / total if total > 0 else 0
            data['failure_rate'] = data['failure_count'] / total if total > 0 else 0
            data['average_duration_minutes'] = (
                sum(data['durations']) / len(data['durations']) / 60 
                if data['durations'] else 0
            )
            data['average_queue_time_seconds'] = (
                sum(data['queue_times']) / len(data['queue_times'])
                if data['queue_times'] else 0
            )
            # Remove raw runs data to keep output clean
            del data['runs']
            del data['durations']
            del data['queue_times']
        
        # Calculate overall statistics
        total_runs = len(runs)
        successful_runs = sum(1 for r in runs if r['conclusion'] == 'success')
        failed_runs = sum(1 for r in runs if r['conclusion'] in ['failure', 'timed_out'])
        all_durations = [r['duration_seconds'] for r in runs if r['duration_seconds']]
        all_queue_times = [r['queue_time_seconds'] for r in runs if r['queue_time_seconds']]
        
        return {
            'collection_timestamp': datetime.now(timezone.utc).isoformat(),
            'total_runs': total_runs,
            'workflows': workflows,
            'overall': {
                'success_rate': successful_runs / total_runs if total_runs > 0 else 0,
                'failure_rate': failed_runs / total_runs if total_runs > 0 else 0,
                'average_duration_minutes': (
                    sum(all_durations) / len(all_durations) / 60
                    if all_durations else 0
                ),
                'average_queue_time_seconds': (
                    sum(all_queue_times) / len(all_queue_times)
                    if all_queue_times else 0
                )
            },
            'test_coverage': self.collect_test_coverage(),
            'recent_failures': self._get_recent_failures(runs, limit=10)
        }
    
    def _get_recent_failures(self, runs: List[Dict[str, Any]], limit: int = 10) -> List[Dict[str, Any]]:
        """Get the most recent failed runs."""
        failures = [
            {
                'workflow_name': r['workflow_name'],
                'run_number': r['run_number'],
                'branch': r['branch'],
                'url': r['html_url'],
                'failed_at': r['updated_at'],
                'event': r['event']
            }
            for r in runs
            if r['conclusion'] in ['failure', 'timed_out']
        ]
        
        # Sort by date descending
        failures.sort(key=lambda x: x['failed_at'], reverse=True)
        return failures[:limit]


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Collect CI metrics from GitHub Actions')
    parser.add_argument('--repo', required=True, help='GitHub repository (owner/repo)')
    parser.add_argument('--token', required=True, help='GitHub personal access token')
    parser.add_argument('--days', type=int, default=7, help='Number of days to look back')
    parser.add_argument('--output', required=True, help='Output JSON file path')
    
    args = parser.parse_args()
    
    try:
        collector = GitHubMetricsCollector(args.repo, args.token)
        
        print(f"Collecting workflow runs from the past {args.days} days...")
        runs = collector.collect_workflow_runs(args.days)
        
        print(f"Found {len(runs)} workflow runs")
        
        print("Generating metrics summary...")
        summary = collector.generate_metrics_summary(runs)
        
        # Save to file
        os.makedirs(os.path.dirname(args.output), exist_ok=True)
        with open(args.output, 'w') as f:
            json.dump(summary, f, indent=2)
            
        print(f"Metrics saved to {args.output}")
        
        # Print summary
        print("\nSummary:")
        print(f"  Total runs: {summary['total_runs']}")
        print(f"  Overall success rate: {summary['overall']['success_rate']:.1%}")
        print(f"  Average duration: {summary['overall']['average_duration_minutes']:.1f} minutes")
        
    except Exception as e:
        print(f"Error collecting metrics: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()