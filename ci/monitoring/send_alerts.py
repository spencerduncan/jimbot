#!/usr/bin/env python3
"""
Send alerts for CI health issues.

This script:
- Reads analysis results from analyze_metrics.py
- Sends alerts via webhook if URL is provided
- Creates GitHub issues for critical problems
- Handles multiple alert channels and severity levels
"""

import argparse
import json
import os
import sys
from datetime import datetime
from typing import Dict, List, Any, Optional
import requests
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AlertSender:
    """Handles sending alerts through multiple channels."""
    
    def __init__(self, webhook_url: Optional[str] = None, github_token: Optional[str] = None, repo: Optional[str] = None):
        self.webhook_url = webhook_url
        self.github_token = github_token
        self.repo = repo
        self.github_headers = {
            'Authorization': f'token {github_token}',
            'Accept': 'application/vnd.github.v3+json'
        } if github_token else {}
        
    def send_alerts(self, analysis: Dict[str, Any], run_id: Optional[str] = None) -> bool:
        """Send alerts based on analysis results."""
        if not analysis.get('alert_needed', False):
            logger.info("No alerts needed based on analysis")
            return True
            
        logger.info(f"Sending alerts for {len(analysis.get('alerts', []))} issues")
        
        success = True
        
        # Send webhook alert if URL is provided
        if self.webhook_url:
            try:
                webhook_success = self._send_webhook_alert(analysis, run_id)
                if not webhook_success:
                    success = False
            except Exception as e:
                logger.error(f"Failed to send webhook alert: {e}")
                success = False
        else:
            logger.info("No webhook URL provided, skipping webhook alert")
            
        # Create GitHub issue for critical alerts
        create_issues = os.environ.get('CREATE_GITHUB_ISSUES', 'true').lower() == 'true'
        if not create_issues:
            logger.info("GitHub issue creation is disabled via CREATE_GITHUB_ISSUES environment variable")
        elif self.github_token and self.repo:
            try:
                issue_success = self._create_github_issue(analysis, run_id)
                if not issue_success:
                    success = False
            except Exception as e:
                logger.error(f"Failed to create GitHub issue: {e}")
                success = False
        else:
            logger.info("No GitHub token/repo provided, skipping GitHub issue creation")
            
        # Log alert summary
        self._log_alert_summary(analysis)
        
        return success
        
    def _send_webhook_alert(self, analysis: Dict[str, Any], run_id: Optional[str] = None) -> bool:
        """Send alert via webhook."""
        if not self.webhook_url or self.webhook_url.strip() == "":
            logger.info("Webhook URL is empty or None, skipping webhook alert")
            return True
            
        payload = self._build_webhook_payload(analysis, run_id)
        
        try:
            response = requests.post(
                self.webhook_url,
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            response.raise_for_status()
            logger.info(f"Webhook alert sent successfully (status: {response.status_code})")
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send webhook alert: {e}")
            return False
            
    def _build_webhook_payload(self, analysis: Dict[str, Any], run_id: Optional[str] = None) -> Dict[str, Any]:
        """Build webhook payload with alert details."""
        alerts = analysis.get('alerts', [])
        warnings = analysis.get('warnings', [])
        
        # Determine overall severity
        has_critical = any(alert.get('severity') == 'critical' for alert in alerts)
        has_high = any(alert.get('severity') == 'high' for alert in alerts)
        
        if has_critical:
            severity = 'critical'
            color = '#ff0000'  # Red
        elif has_high:
            severity = 'high'
            color = '#ff9900'  # Orange
        else:
            severity = 'medium'
            color = '#ffcc00'  # Yellow
            
        payload = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'severity': severity,
            'service': 'CI Health Monitor',
            'title': f'CI Health Alert - {severity.upper()}',
            'description': f'CI system health degraded: {analysis.get("overall_health", "unknown")}',
            'details': {
                'overall_health': analysis.get('overall_health'),
                'failure_rate': analysis.get('overall_failure_rate'),
                'average_duration': analysis.get('average_duration_minutes'),
                'alerts_count': len(alerts),
                'warnings_count': len(warnings)
            },
            'alerts': alerts,
            'warnings': warnings,
            'recommendations': analysis.get('recommendations', []),
            'run_id': run_id,
            'repository': self.repo
        }
        
        # Add color for services that support it (like Discord, Slack)
        if color:
            payload['color'] = color
            
        return payload
        
    def _create_github_issue(self, analysis: Dict[str, Any], run_id: Optional[str] = None) -> bool:
        """Create GitHub issue for critical alerts."""
        # Only create issues for critical or high severity alerts
        critical_alerts = [
            alert for alert in analysis.get('alerts', [])
            if alert.get('severity') in ['critical', 'high']
        ]
        
        if not critical_alerts:
            logger.info("No critical/high severity alerts, skipping GitHub issue creation")
            return True
            
        # Check for existing open CI health alert issues
        try:
            search_url = f"https://api.github.com/repos/{self.repo}/issues"
            search_params = {
                'state': 'open',
                'labels': 'ci,health-alert',
                'per_page': 100
            }
            
            response = requests.get(search_url, params=search_params, headers=self.github_headers, timeout=30)
            response.raise_for_status()
            
            existing_issues = response.json()
            
            # Check if there's already an open CI health alert issue
            for issue in existing_issues:
                if '[CI Health Alert]' in issue.get('title', ''):
                    # Update the existing issue instead of creating a new one
                    logger.info(f"Found existing CI health alert issue #{issue['number']}, updating it")
                    return self._update_github_issue(issue['number'], analysis, critical_alerts, run_id)
                    
        except requests.exceptions.RequestException as e:
            logger.warning(f"Failed to check for existing issues: {e}")
            # Continue to create a new issue if we can't check for existing ones
            
        # No existing issue found, create a new one
        issue_title = f"[CI Health Alert] {analysis.get('overall_health', 'degraded').title()} - {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}"
        issue_body = self._build_issue_body(analysis, critical_alerts, run_id)
        
        try:
            url = f"https://api.github.com/repos/{self.repo}/issues"
            issue_data = {
                'title': issue_title,
                'body': issue_body,
                'labels': ['ci', 'health-alert', f'severity-{analysis.get("overall_health", "unknown")}']
            }
            
            response = requests.post(url, json=issue_data, headers=self.github_headers, timeout=30)
            response.raise_for_status()
            
            issue_url = response.json()['html_url']
            logger.info(f"GitHub issue created successfully: {issue_url}")
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to create GitHub issue: {e}")
            return False
            
    def _update_github_issue(self, issue_number: int, analysis: Dict[str, Any], alerts: List[Dict[str, Any]], run_id: Optional[str] = None) -> bool:
        """Update existing GitHub issue with new alert information."""
        try:
            # Get current issue to preserve original content
            issue_url = f"https://api.github.com/repos/{self.repo}/issues/{issue_number}"
            response = requests.get(issue_url, headers=self.github_headers, timeout=30)
            response.raise_for_status()
            
            current_issue = response.json()
            current_body = current_issue.get('body', '')
            
            # Build update section
            update_parts = [
                "",
                "---",
                "",
                f"## Update - {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
                "",
                f"**Overall Health:** {analysis.get('overall_health', 'unknown').title()}",
                f"**Failure Rate:** {analysis.get('overall_failure_rate', 0):.1%}",
                f"**Average Duration:** {analysis.get('average_duration_minutes', 0):.1f} minutes",
                ""
            ]
            
            if run_id:
                update_parts.extend([
                    f"**Related Run:** https://github.com/{self.repo}/actions/runs/{run_id}",
                    ""
                ])
                
            # Add new critical issues
            if alerts:
                update_parts.extend([
                    "### Latest Critical Issues",
                    ""
                ])
                
                for alert in alerts:
                    severity_emoji = {
                        'critical': '🔴',
                        'high': '🟠',
                        'medium': '🟡'
                    }.get(alert.get('severity', 'medium'), '🟡')
                    
                    update_parts.extend([
                        f"- {severity_emoji} **{alert.get('type', 'Unknown Issue').replace('_', ' ').title()}**: {alert.get('message', 'No message provided')}",
                    ])
                update_parts.append("")
                
            # Combine original body with update
            updated_body = current_body + '\n' + '\n'.join(update_parts)
            
            # Update the issue
            update_data = {
                'body': updated_body,
                'state': 'open'  # Ensure it stays open
            }
            
            response = requests.patch(issue_url, json=update_data, headers=self.github_headers, timeout=30)
            response.raise_for_status()
            
            logger.info(f"Updated existing issue #{issue_number}")
            
            # Add a comment for visibility
            comment_url = f"{issue_url}/comments"
            comment_data = {
                'body': f"🔄 CI Health Alert updated at {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}\n\nOverall health: **{analysis.get('overall_health', 'unknown').title()}**\nFailure rate: **{analysis.get('overall_failure_rate', 0):.1%}**"
            }
            
            requests.post(comment_url, json=comment_data, headers=self.github_headers, timeout=30)
            
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to update GitHub issue: {e}")
            return False
            
    def _build_issue_body(self, analysis: Dict[str, Any], alerts: List[Dict[str, Any]], run_id: Optional[str] = None) -> str:
        """Build GitHub issue body with alert details."""
        body_parts = [
            "## CI Health Alert",
            "",
            f"**Overall Health:** {analysis.get('overall_health', 'unknown').title()}",
            f"**Timestamp:** {analysis.get('timestamp', 'unknown')}",
            f"**Failure Rate:** {analysis.get('overall_failure_rate', 0):.1%}",
            f"**Average Duration:** {analysis.get('average_duration_minutes', 0):.1f} minutes",
            ""
        ]
        
        if run_id:
            body_parts.extend([
                f"**Related Run:** https://github.com/{self.repo}/actions/runs/{run_id}",
                ""
            ])
            
        if alerts:
            body_parts.extend([
                "## Critical Issues",
                ""
            ])
            
            for alert in alerts:
                severity_emoji = {
                    'critical': '🔴',
                    'high': '🟠',
                    'medium': '🟡'
                }.get(alert.get('severity', 'medium'), '🟡')
                
                body_parts.extend([
                    f"### {severity_emoji} {alert.get('type', 'Unknown Issue').replace('_', ' ').title()}",
                    f"**Severity:** {alert.get('severity', 'medium').title()}",
                    f"**Message:** {alert.get('message', 'No message provided')}",
                    ""
                ])
                
        warnings = analysis.get('warnings', [])
        if warnings:
            body_parts.extend([
                "## Warnings",
                ""
            ])
            
            for warning in warnings:
                body_parts.extend([
                    f"- **{warning.get('type', 'Unknown').replace('_', ' ').title()}:** {warning.get('message', 'No message')}",
                ])
            body_parts.append("")
            
        recommendations = analysis.get('recommendations', [])
        if recommendations:
            body_parts.extend([
                "## Recommendations",
                ""
            ])
            
            for rec in recommendations:
                body_parts.append(f"- {rec}")
            body_parts.append("")
            
        workflow_health = analysis.get('workflow_health', {})
        if workflow_health:
            body_parts.extend([
                "## Workflow Health Summary",
                ""
            ])
            
            for workflow_name, health in workflow_health.items():
                status_emoji = {
                    'healthy': '✅',
                    'degraded': '⚠️',
                    'critical': '❌'
                }.get(health.get('status', 'unknown'), '❓')
                
                body_parts.extend([
                    f"- **{workflow_name}:** {status_emoji} {health.get('status', 'unknown').title()}",
                ])
                
                if health.get('issues'):
                    for issue in health['issues']:
                        body_parts.append(f"  - {issue.get('message', 'No message')}")
            body_parts.append("")
            
        body_parts.extend([
            "---",
            "",
            f"*This issue was automatically created by the CI Health Monitor at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}*"
        ])
        
        return '\n'.join(body_parts)
        
    def _log_alert_summary(self, analysis: Dict[str, Any]):
        """Log summary of alerts sent."""
        alerts = analysis.get('alerts', [])
        warnings = analysis.get('warnings', [])
        
        logger.info(f"Alert summary:")
        logger.info(f"  Overall health: {analysis.get('overall_health', 'unknown')}")
        logger.info(f"  Alerts: {len(alerts)}")
        logger.info(f"  Warnings: {len(warnings)}")
        
        if alerts:
            logger.info("  Alert details:")
            for alert in alerts:
                logger.info(f"    - [{alert.get('severity', 'unknown')}] {alert.get('type', 'unknown')}: {alert.get('message', 'no message')}")
                
        if warnings:
            logger.info("  Warning details:")
            for warning in warnings:
                logger.info(f"    - [{warning.get('severity', 'unknown')}] {warning.get('type', 'unknown')}: {warning.get('message', 'no message')}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Send CI health alerts')
    parser.add_argument('--analysis', required=True, help='Analysis JSON file from analyze_metrics.py')
    parser.add_argument('--webhook-url', help='Webhook URL for alerts (optional)')
    parser.add_argument('--repo', help='GitHub repository (owner/repo)')
    parser.add_argument('--run-id', help='GitHub Actions run ID')
    parser.add_argument('--github-token', help='GitHub token for issue creation')
    
    args = parser.parse_args()
    
    # Get GitHub token from environment if not provided
    github_token = args.github_token or os.environ.get('GITHUB_TOKEN')
    
    try:
        # Load analysis results
        if not os.path.exists(args.analysis):
            logger.error(f"Analysis file not found: {args.analysis}")
            sys.exit(1)
            
        with open(args.analysis, 'r') as f:
            analysis = json.load(f)
            
        # Create alert sender
        alert_sender = AlertSender(
            webhook_url=args.webhook_url,
            github_token=github_token,
            repo=args.repo
        )
        
        # Send alerts
        success = alert_sender.send_alerts(analysis, args.run_id)
        
        if success:
            logger.info("All alerts sent successfully")
            sys.exit(0)
        else:
            logger.error("Some alerts failed to send")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Error sending alerts: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()