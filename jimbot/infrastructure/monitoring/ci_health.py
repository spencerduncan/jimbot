"""CI Health Monitoring Module

Comprehensive CI health monitoring and alerting system that builds upon
the existing infrastructure monitoring capabilities.
"""

import asyncio
import json
import logging
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from .health import HealthChecker, HealthStatus, HealthCheckResult
from .metrics import MetricsCollector

logger = logging.getLogger(__name__)


class CIHealthStatus(Enum):
    """CI-specific health status levels"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


@dataclass
class CIWorkflowHealth:
    """Health status for a specific CI workflow"""
    workflow_name: str
    status: CIHealthStatus
    success_rate: float
    avg_duration: float
    recent_failures: List[Dict[str, Any]]
    last_run: Optional[datetime]
    metrics: Dict[str, Any]
    timestamp: datetime


@dataclass
class CISystemHealth:
    """Overall CI system health"""
    overall_status: CIHealthStatus
    workflow_health: Dict[str, CIWorkflowHealth]
    system_metrics: Dict[str, Any]
    alerts: List[Dict[str, Any]]
    timestamp: datetime


class CIHealthMonitor:
    """Comprehensive CI health monitoring system"""
    
    def __init__(self, 
                 metrics_collector: Optional[MetricsCollector] = None,
                 health_checker: Optional[HealthChecker] = None):
        self.metrics_collector = metrics_collector or MetricsCollector()
        self.health_checker = health_checker or HealthChecker()
        
        # CI-specific configuration
        self.workflows = [
            "CI Test Suite",
            "CI Quick Checks", 
            "CI Integration Tests"
        ]
        
        # Health thresholds
        self.thresholds = {
            "healthy": 90.0,
            "degraded": 70.0,
            "unhealthy": 50.0,
            "critical": 30.0
        }
        
        # Monitoring intervals
        self.check_interval = 300  # 5 minutes
        self.metrics_retention = 24 * 60 * 60  # 24 hours
        
        # Alert configuration
        self.alert_cooldown = 3600  # 1 hour
        self.last_alerts = {}
        
        # Register CI-specific health checks
        self._register_ci_health_checks()
    
    def _register_ci_health_checks(self):
        """Register CI-specific health checks"""
        self.health_checker.register_check("github_api", self._check_github_api)
        self.health_checker.register_check("workflow_runs", self._check_workflow_runs)
        self.health_checker.register_check("runner_availability", self._check_runner_availability)
        self.health_checker.register_check("dependency_health", self._check_dependency_health)
    
    async def _check_github_api(self) -> Dict[str, Any]:
        """Check GitHub API connectivity and rate limits"""
        try:
            result = await asyncio.to_thread(
                subprocess.run,
                ["gh", "api", "rate_limit"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                rate_limit = json.loads(result.stdout)
                core_limit = rate_limit.get("resources", {}).get("core", {})
                remaining = core_limit.get("remaining", 0)
                limit = core_limit.get("limit", 5000)
                
                utilization = (limit - remaining) / limit * 100
                
                if utilization > 90:
                    status = HealthStatus.DEGRADED
                    message = f"GitHub API rate limit at {utilization:.1f}%"
                elif utilization > 95:
                    status = HealthStatus.UNHEALTHY
                    message = f"GitHub API rate limit critical at {utilization:.1f}%"
                else:
                    status = HealthStatus.HEALTHY
                    message = f"GitHub API healthy ({remaining}/{limit} requests remaining)"
                
                return {
                    "status": status,
                    "message": message,
                    "metrics": {
                        "rate_limit_remaining": remaining,
                        "rate_limit_total": limit,
                        "utilization_percent": utilization
                    }
                }
            else:
                return {
                    "status": HealthStatus.UNHEALTHY,
                    "message": "GitHub API unavailable",
                    "metrics": {}
                }
        except Exception as e:
            return {
                "status": HealthStatus.UNHEALTHY,
                "message": f"GitHub API check failed: {str(e)}",
                "metrics": {}
            }
    
    async def _check_workflow_runs(self) -> Dict[str, Any]:
        """Check recent workflow run health"""
        try:
            healthy_workflows = 0
            total_workflows = len(self.workflows)
            issues = []
            
            for workflow in self.workflows:
                workflow_health = await self._get_workflow_health(workflow)
                
                if workflow_health.status in [CIHealthStatus.HEALTHY, CIHealthStatus.DEGRADED]:
                    healthy_workflows += 1
                else:
                    issues.append(f"{workflow}: {workflow_health.status.value}")
            
            health_ratio = healthy_workflows / total_workflows
            
            if health_ratio >= 0.8:
                status = HealthStatus.HEALTHY
                message = f"Workflow health good ({healthy_workflows}/{total_workflows} healthy)"
            elif health_ratio >= 0.6:
                status = HealthStatus.DEGRADED
                message = f"Workflow health degraded ({healthy_workflows}/{total_workflows} healthy)"
            else:
                status = HealthStatus.UNHEALTHY
                message = f"Workflow health poor ({healthy_workflows}/{total_workflows} healthy)"
            
            return {
                "status": status,
                "message": message,
                "metrics": {
                    "healthy_workflows": healthy_workflows,
                    "total_workflows": total_workflows,
                    "health_ratio": health_ratio,
                    "issues": issues
                }
            }
        except Exception as e:
            return {
                "status": HealthStatus.UNHEALTHY,
                "message": f"Workflow health check failed: {str(e)}",
                "metrics": {}
            }
    
    async def _check_runner_availability(self) -> Dict[str, Any]:
        """Check GitHub Actions runner availability"""
        try:
            # Check if we have any queued runs that might indicate runner issues
            result = await asyncio.to_thread(
                subprocess.run,
                ["gh", "run", "list", "--limit", "20", "--json", "status,conclusion"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                runs = json.loads(result.stdout)
                queued_runs = [r for r in runs if r.get("status") == "queued"]
                
                if len(queued_runs) > 10:
                    status = HealthStatus.UNHEALTHY
                    message = f"Many runs queued ({len(queued_runs)}) - possible runner shortage"
                elif len(queued_runs) > 5:
                    status = HealthStatus.DEGRADED
                    message = f"Several runs queued ({len(queued_runs)}) - monitoring runner capacity"
                else:
                    status = HealthStatus.HEALTHY
                    message = f"Runner availability good ({len(queued_runs)} queued)"
                
                return {
                    "status": status,
                    "message": message,
                    "metrics": {
                        "queued_runs": len(queued_runs),
                        "total_recent_runs": len(runs)
                    }
                }
            else:
                return {
                    "status": HealthStatus.UNKNOWN,
                    "message": "Cannot check runner availability",
                    "metrics": {}
                }
        except Exception as e:
            return {
                "status": HealthStatus.UNHEALTHY,
                "message": f"Runner availability check failed: {str(e)}",
                "metrics": {}
            }
    
    async def _check_dependency_health(self) -> Dict[str, Any]:
        """Check health of CI dependencies (Docker, external services)"""
        try:
            checks = []
            
            # Check Docker daemon
            docker_result = await asyncio.to_thread(
                subprocess.run,
                ["docker", "info"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if docker_result.returncode == 0:
                checks.append(("Docker", "healthy"))
            else:
                checks.append(("Docker", "unhealthy"))
            
            # Check if we can pull images (network connectivity)
            pull_result = await asyncio.to_thread(
                subprocess.run,
                ["docker", "pull", "hello-world"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if pull_result.returncode == 0:
                checks.append(("Docker Registry", "healthy"))
            else:
                checks.append(("Docker Registry", "degraded"))
            
            # Clean up test image
            await asyncio.to_thread(
                subprocess.run,
                ["docker", "rmi", "hello-world"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            healthy_deps = len([c for c in checks if c[1] == "healthy"])
            total_deps = len(checks)
            
            if healthy_deps == total_deps:
                status = HealthStatus.HEALTHY
                message = "All CI dependencies healthy"
            elif healthy_deps >= total_deps * 0.5:
                status = HealthStatus.DEGRADED
                message = f"Some CI dependencies unhealthy ({healthy_deps}/{total_deps})"
            else:
                status = HealthStatus.UNHEALTHY
                message = f"Critical CI dependencies unhealthy ({healthy_deps}/{total_deps})"
            
            return {
                "status": status,
                "message": message,
                "metrics": {
                    "healthy_dependencies": healthy_deps,
                    "total_dependencies": total_deps,
                    "dependency_checks": dict(checks)
                }
            }
        except Exception as e:
            return {
                "status": HealthStatus.UNHEALTHY,
                "message": f"Dependency health check failed: {str(e)}",
                "metrics": {}
            }
    
    async def _get_workflow_health(self, workflow_name: str) -> CIWorkflowHealth:
        """Get comprehensive health status for a specific workflow"""
        try:
            # Get recent workflow runs
            result = await asyncio.to_thread(
                subprocess.run,
                ["gh", "run", "list", f"--workflow={workflow_name}", "--limit", "50", 
                 "--json", "conclusion,createdAt,status,url,workflowName"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                return CIWorkflowHealth(
                    workflow_name=workflow_name,
                    status=CIHealthStatus.UNKNOWN,
                    success_rate=0.0,
                    avg_duration=0.0,
                    recent_failures=[],
                    last_run=None,
                    metrics={},
                    timestamp=datetime.now()
                )
            
            runs = json.loads(result.stdout)
            
            if not runs:
                return CIWorkflowHealth(
                    workflow_name=workflow_name,
                    status=CIHealthStatus.UNKNOWN,
                    success_rate=0.0,
                    avg_duration=0.0,
                    recent_failures=[],
                    last_run=None,
                    metrics={},
                    timestamp=datetime.now()
                )
            
            # Calculate success rate for recent runs (last 24 hours)
            cutoff = datetime.now() - timedelta(hours=24)
            recent_runs = [
                run for run in runs
                if datetime.fromisoformat(run["createdAt"].replace("Z", "+00:00")) > cutoff
            ]
            
            if not recent_runs:
                recent_runs = runs[:10]  # Fallback to last 10 runs
            
            successful_runs = [r for r in recent_runs if r.get("conclusion") == "success"]
            success_rate = len(successful_runs) / len(recent_runs) * 100 if recent_runs else 0
            
            # Get recent failures
            recent_failures = [
                {
                    "url": r["url"],
                    "created_at": r["createdAt"],
                    "conclusion": r.get("conclusion", "unknown")
                }
                for r in recent_runs[:5]
                if r.get("conclusion") in ["failure", "cancelled", "timed_out"]
            ]
            
            # Determine status based on success rate
            if success_rate >= self.thresholds["healthy"]:
                status = CIHealthStatus.HEALTHY
            elif success_rate >= self.thresholds["degraded"]:
                status = CIHealthStatus.DEGRADED
            elif success_rate >= self.thresholds["unhealthy"]:
                status = CIHealthStatus.UNHEALTHY
            else:
                status = CIHealthStatus.CRITICAL
            
            # Get last run time
            last_run = None
            if runs:
                last_run = datetime.fromisoformat(runs[0]["createdAt"].replace("Z", "+00:00"))
            
            return CIWorkflowHealth(
                workflow_name=workflow_name,
                status=status,
                success_rate=success_rate,
                avg_duration=0.0,  # TODO: Calculate from run details
                recent_failures=recent_failures,
                last_run=last_run,
                metrics={
                    "total_runs": len(runs),
                    "recent_runs": len(recent_runs),
                    "successful_runs": len(successful_runs),
                    "failed_runs": len(recent_runs) - len(successful_runs)
                },
                timestamp=datetime.now()
            )
        except Exception as e:
            logger.error(f"Error getting workflow health for {workflow_name}: {str(e)}")
            return CIWorkflowHealth(
                workflow_name=workflow_name,
                status=CIHealthStatus.UNKNOWN,
                success_rate=0.0,
                avg_duration=0.0,
                recent_failures=[],
                last_run=None,
                metrics={"error": str(e)},
                timestamp=datetime.now()
            )
    
    async def get_system_health(self) -> CISystemHealth:
        """Get comprehensive CI system health"""
        # Get health check results
        health_results = await self.health_checker.run_checks()
        
        # Get workflow health
        workflow_health = {}
        for workflow in self.workflows:
            workflow_health[workflow] = await self._get_workflow_health(workflow)
        
        # Calculate overall status
        overall_status = self._calculate_overall_status(health_results, workflow_health)
        
        # Generate system metrics
        system_metrics = self._generate_system_metrics(health_results, workflow_health)
        
        # Check for alerts
        alerts = await self._check_alerts(health_results, workflow_health)
        
        return CISystemHealth(
            overall_status=overall_status,
            workflow_health=workflow_health,
            system_metrics=system_metrics,
            alerts=alerts,
            timestamp=datetime.now()
        )
    
    def _calculate_overall_status(self, 
                                 health_results: Dict[str, HealthCheckResult],
                                 workflow_health: Dict[str, CIWorkflowHealth]) -> CIHealthStatus:
        """Calculate overall CI system health status"""
        # Check if any critical systems are unhealthy
        critical_systems = ["github_api", "workflow_runs"]
        for system in critical_systems:
            if system in health_results:
                if health_results[system].status == HealthStatus.UNHEALTHY:
                    return CIHealthStatus.CRITICAL
        
        # Check workflow health
        critical_workflows = sum(1 for wh in workflow_health.values() 
                               if wh.status == CIHealthStatus.CRITICAL)
        unhealthy_workflows = sum(1 for wh in workflow_health.values() 
                                if wh.status in [CIHealthStatus.CRITICAL, CIHealthStatus.UNHEALTHY])
        
        total_workflows = len(workflow_health)
        
        if critical_workflows > 0:
            return CIHealthStatus.CRITICAL
        elif unhealthy_workflows > total_workflows * 0.5:
            return CIHealthStatus.UNHEALTHY
        elif unhealthy_workflows > total_workflows * 0.3:
            return CIHealthStatus.DEGRADED
        else:
            return CIHealthStatus.HEALTHY
    
    def _generate_system_metrics(self, 
                               health_results: Dict[str, HealthCheckResult],
                               workflow_health: Dict[str, CIWorkflowHealth]) -> Dict[str, Any]:
        """Generate system-level metrics"""
        metrics = {}
        
        # Overall success rate
        if workflow_health:
            avg_success_rate = sum(wh.success_rate for wh in workflow_health.values()) / len(workflow_health)
            metrics["overall_success_rate"] = avg_success_rate
        
        # Health check metrics
        healthy_checks = sum(1 for hr in health_results.values() 
                           if hr.status == HealthStatus.HEALTHY)
        metrics["healthy_checks"] = healthy_checks
        metrics["total_checks"] = len(health_results)
        
        # Workflow status counts
        workflow_status_counts = {}
        for status in CIHealthStatus:
            workflow_status_counts[status.value] = sum(
                1 for wh in workflow_health.values() 
                if wh.status == status
            )
        metrics["workflow_status_counts"] = workflow_status_counts
        
        return metrics
    
    async def _check_alerts(self, 
                          health_results: Dict[str, HealthCheckResult],
                          workflow_health: Dict[str, CIWorkflowHealth]) -> List[Dict[str, Any]]:
        """Check for alert conditions"""
        alerts = []
        current_time = time.time()
        
        # Check for critical health issues
        for check_name, result in health_results.items():
            if result.status == HealthStatus.UNHEALTHY:
                alert_key = f"health_check_{check_name}"
                if self._should_alert(alert_key, current_time):
                    alerts.append({
                        "type": "health_check_failure",
                        "severity": "critical",
                        "component": check_name,
                        "message": result.message,
                        "timestamp": current_time
                    })
        
        # Check for workflow failures
        for workflow_name, wh in workflow_health.items():
            if wh.status == CIHealthStatus.CRITICAL:
                alert_key = f"workflow_critical_{workflow_name}"
                if self._should_alert(alert_key, current_time):
                    alerts.append({
                        "type": "workflow_critical",
                        "severity": "critical",
                        "component": workflow_name,
                        "message": f"Workflow {workflow_name} success rate critically low: {wh.success_rate:.1f}%",
                        "timestamp": current_time
                    })
            elif wh.status == CIHealthStatus.UNHEALTHY:
                alert_key = f"workflow_unhealthy_{workflow_name}"
                if self._should_alert(alert_key, current_time):
                    alerts.append({
                        "type": "workflow_unhealthy",
                        "severity": "warning",
                        "component": workflow_name,
                        "message": f"Workflow {workflow_name} success rate low: {wh.success_rate:.1f}%",
                        "timestamp": current_time
                    })
        
        return alerts
    
    def _should_alert(self, alert_key: str, current_time: float) -> bool:
        """Check if enough time has passed since last alert"""
        last_alert_time = self.last_alerts.get(alert_key, 0)
        if current_time - last_alert_time >= self.alert_cooldown:
            self.last_alerts[alert_key] = current_time
            return True
        return False
    
    async def start_monitoring(self):
        """Start continuous CI health monitoring"""
        logger.info("Starting CI health monitoring...")
        
        # Start metrics collector
        await self.metrics_collector.start()
        
        # Start monitoring loop
        while True:
            try:
                # Get system health
                system_health = await self.get_system_health()
                
                # Record metrics
                await self._record_metrics(system_health)
                
                # Log status
                logger.info(f"CI System Health: {system_health.overall_status.value}")
                
                # Handle alerts
                if system_health.alerts:
                    await self._handle_alerts(system_health.alerts)
                
                # Wait for next check
                await asyncio.sleep(self.check_interval)
                
            except Exception as e:
                logger.error(f"Error in CI health monitoring loop: {str(e)}")
                await asyncio.sleep(60)  # Wait 1 minute before retrying
    
    async def _record_metrics(self, system_health: CISystemHealth):
        """Record system health metrics"""
        # Record overall metrics
        self.metrics_collector.set_gauge(
            "ci_overall_success_rate",
            system_health.system_metrics.get("overall_success_rate", 0)
        )
        
        self.metrics_collector.set_gauge(
            "ci_healthy_checks",
            system_health.system_metrics.get("healthy_checks", 0)
        )
        
        # Record workflow metrics
        for workflow_name, wh in system_health.workflow_health.items():
            labels = {"workflow": workflow_name}
            
            self.metrics_collector.set_gauge(
                "ci_workflow_success_rate",
                wh.success_rate,
                labels
            )
            
            self.metrics_collector.set_gauge(
                "ci_workflow_status",
                1 if wh.status == CIHealthStatus.HEALTHY else 0,
                labels
            )
        
        # Record alert metrics
        self.metrics_collector.set_gauge(
            "ci_active_alerts",
            len(system_health.alerts)
        )
    
    async def _handle_alerts(self, alerts: List[Dict[str, Any]]):
        """Handle system alerts"""
        for alert in alerts:
            logger.warning(f"CI Alert: {alert['type']} - {alert['message']}")
            
            # Process alert through notification system
            await self._process_alert_notification(alert)
            
            # Create GitHub issue for critical alerts
            if alert['severity'] == 'critical':
                await self._create_alert_issue(alert)
    
    async def _process_alert_notification(self, alert: Dict[str, Any]):
        """Process alert through various notification channels"""
        try:
            # Webhook notification
            await self._send_webhook_notification(alert)
            
            # Email notification (if configured)
            await self._send_email_notification(alert)
            
            # Slack notification (if configured)
            await self._send_slack_notification(alert)
            
        except Exception as e:
            logger.error(f"Failed to send alert notification: {str(e)}")
    
    async def _send_webhook_notification(self, alert: Dict[str, Any]):
        """Send webhook notification for alert"""
        import os
        webhook_url = os.getenv('CI_ALERT_WEBHOOK_URL')
        if not webhook_url:
            return
        
        try:
            import aiohttp
            
            payload = {
                'type': 'ci_alert',
                'alert': alert,
                'timestamp': alert['timestamp'],
                'severity': alert['severity'],
                'component': alert['component'],
                'message': alert['message']
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(webhook_url, json=payload, timeout=10) as response:
                    if response.status == 200:
                        logger.info(f"Webhook notification sent for {alert['type']}")
                    else:
                        logger.warning(f"Webhook notification failed: {response.status}")
                        
        except Exception as e:
            logger.error(f"Failed to send webhook notification: {str(e)}")
    
    async def _send_email_notification(self, alert: Dict[str, Any]]):
        """Send email notification for alert"""
        import os
        email_recipients = os.getenv('CI_ALERT_EMAIL_RECIPIENTS')
        if not email_recipients:
            return
        
        try:
            # Email notification implementation would go here
            # For now, just log that it would be sent
            logger.info(f"Email notification would be sent to {email_recipients} for {alert['type']}")
            
        except Exception as e:
            logger.error(f"Failed to send email notification: {str(e)}")
    
    async def _send_slack_notification(self, alert: Dict[str, Any]]):
        """Send Slack notification for alert"""
        import os
        slack_webhook = os.getenv('CI_ALERT_SLACK_WEBHOOK')
        if not slack_webhook:
            return
        
        try:
            import aiohttp
            
            severity_emoji = {
                'critical': '🚨',
                'warning': '⚠️',
                'info': 'ℹ️'
            }
            
            emoji = severity_emoji.get(alert['severity'], '❓')
            
            payload = {
                'text': f"{emoji} CI Alert: {alert['type']}",
                'attachments': [
                    {
                        'color': 'danger' if alert['severity'] == 'critical' else 'warning',
                        'fields': [
                            {
                                'title': 'Component',
                                'value': alert['component'],
                                'short': True
                            },
                            {
                                'title': 'Severity',
                                'value': alert['severity'].title(),
                                'short': True
                            },
                            {
                                'title': 'Message',
                                'value': alert['message'],
                                'short': False
                            }
                        ],
                        'ts': alert['timestamp']
                    }
                ]
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(slack_webhook, json=payload, timeout=10) as response:
                    if response.status == 200:
                        logger.info(f"Slack notification sent for {alert['type']}")
                    else:
                        logger.warning(f"Slack notification failed: {response.status}")
                        
        except Exception as e:
            logger.error(f"Failed to send Slack notification: {str(e)}")
    
    async def _create_alert_issue(self, alert: Dict[str, Any]]):
        """Create GitHub issue for critical alerts"""
        try:
            # Check if similar issue already exists
            existing_issue = await self._check_existing_alert_issue(alert)
            if existing_issue:
                logger.info(f"Alert issue already exists: #{existing_issue}")
                return
            
            # Create new issue
            issue_title = f"🚨 CI Alert: {alert['type']} - {alert['component']}"
            issue_body = f"""## CI Alert Details

**Type**: {alert['type']}
**Component**: {alert['component']}
**Severity**: {alert['severity']}
**Timestamp**: {datetime.fromtimestamp(alert['timestamp']).isoformat()}

## Issue Description
{alert['message']}

## Immediate Actions Needed
- [ ] Investigate the root cause
- [ ] Check component health and dependencies
- [ ] Review recent changes that might have caused this
- [ ] Monitor for resolution

## Alert Context
This issue was automatically created by the CI Health Monitoring system.
"""
            
            result = await asyncio.to_thread(
                subprocess.run,
                [
                    'gh', 'issue', 'create',
                    '--title', issue_title,
                    '--body', issue_body,
                    '--label', 'infrastructure,critical,P0,devops,automated-alert',
                    '--assignee', 'spencerduncan'
                ],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                issue_url = result.stdout.strip()
                logger.info(f"Created alert issue: {issue_url}")
            else:
                logger.error(f"Failed to create alert issue: {result.stderr}")
                
        except Exception as e:
            logger.error(f"Failed to create alert issue: {str(e)}")
    
    async def _check_existing_alert_issue(self, alert: Dict[str, Any]]) -> Optional[str]:
        """Check if similar alert issue already exists"""
        try:
            search_query = f"is:open label:automated-alert {alert['type']} {alert['component']}"
            
            result = await asyncio.to_thread(
                subprocess.run,
                ['gh', 'issue', 'list', '--search', search_query, '--json', 'number'],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                issues = json.loads(result.stdout)
                if issues:
                    return issues[0]['number']
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to check existing alert issues: {str(e)}")
            return None