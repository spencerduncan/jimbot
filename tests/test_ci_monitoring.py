"""
Tests for CI Health Monitoring System

Comprehensive test suite for all CI monitoring components including
health checks, alerting, dashboard generation, and metrics storage.
"""

import asyncio
import json
import pytest
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock

# Import monitoring components
from jimbot.infrastructure.monitoring import (
    CIHealthMonitor, CIHealthStatus, CIWorkflowHealth, CISystemHealth,
    CIDashboard, DashboardData, NotificationManager, NotificationConfig,
    MetricsStorage, MetricPoint, WorkflowMetrics, SystemHealthSnapshot,
    HealthChecker, HealthStatus, MetricsCollector
)


class TestCIHealthMonitor:
    """Test suite for CI Health Monitor"""
    
    @pytest.fixture
    def health_monitor(self):
        """Create CI health monitor instance"""
        return CIHealthMonitor()
    
    @pytest.mark.asyncio
    async def test_github_api_health_check(self, health_monitor):
        """Test GitHub API health check"""
        with patch('subprocess.run') as mock_run:
            # Mock successful API response
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = json.dumps({
                "resources": {
                    "core": {
                        "limit": 5000,
                        "remaining": 4500
                    }
                }
            })
            
            result = await health_monitor._check_github_api()
            
            assert result['status'] == HealthStatus.HEALTHY
            assert 'GitHub API healthy' in result['message']
            assert result['metrics']['rate_limit_remaining'] == 4500
    
    @pytest.mark.asyncio
    async def test_github_api_rate_limit_warning(self, health_monitor):
        """Test GitHub API rate limit warning"""
        with patch('subprocess.run') as mock_run:
            # Mock high usage API response
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = json.dumps({
                "resources": {
                    "core": {
                        "limit": 5000,
                        "remaining": 250  # Only 5% remaining
                    }
                }
            })
            
            result = await health_monitor._check_github_api()
            
            assert result['status'] == HealthStatus.DEGRADED
            assert 'rate limit at' in result['message']
    
    @pytest.mark.asyncio
    async def test_workflow_health_assessment(self, health_monitor):
        """Test workflow health assessment"""
        with patch('subprocess.run') as mock_run:
            # Mock workflow runs response
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = json.dumps([
                {
                    "conclusion": "success",
                    "createdAt": datetime.now().isoformat() + "Z",
                    "status": "completed",
                    "url": "https://github.com/test/repo/actions/runs/1",
                    "workflowName": "Test Workflow"
                },
                {
                    "conclusion": "failure",
                    "createdAt": (datetime.now() - timedelta(hours=1)).isoformat() + "Z",
                    "status": "completed",
                    "url": "https://github.com/test/repo/actions/runs/2",
                    "workflowName": "Test Workflow"
                }
            ])
            
            workflow_health = await health_monitor._get_workflow_health("Test Workflow")
            
            assert workflow_health.workflow_name == "Test Workflow"
            assert workflow_health.success_rate == 50.0  # 1 success out of 2 runs
            assert workflow_health.status == CIHealthStatus.UNHEALTHY  # Below 70% threshold
    
    @pytest.mark.asyncio
    async def test_system_health_aggregation(self, health_monitor):
        """Test system health aggregation"""
        with patch.object(health_monitor, '_get_workflow_health') as mock_workflow:
            with patch.object(health_monitor.health_checker, 'run_checks') as mock_checks:
                # Mock workflow health
                mock_workflow.return_value = CIWorkflowHealth(
                    workflow_name="Test Workflow",
                    status=CIHealthStatus.HEALTHY,
                    success_rate=95.0,
                    avg_duration=120.0,
                    recent_failures=[],
                    last_run=datetime.now(),
                    metrics={},
                    timestamp=datetime.now()
                )
                
                # Mock health checks
                mock_checks.return_value = {}
                
                system_health = await health_monitor.get_system_health()
                
                assert isinstance(system_health, CISystemHealth)
                assert system_health.overall_status == CIHealthStatus.HEALTHY
                assert "Test Workflow" in system_health.workflow_health


class TestNotificationManager:
    """Test suite for Notification Manager"""
    
    @pytest.fixture
    def notification_config(self):
        """Create test notification configuration"""
        return NotificationConfig(
            webhook_url="https://test.webhook.com",
            slack_webhook="https://hooks.slack.com/test",
            email_recipients=["test@example.com"]
        )
    
    @pytest.fixture
    def notification_manager(self, notification_config):
        """Create notification manager instance"""
        return NotificationManager(notification_config)
    
    @pytest.fixture
    def test_alert(self):
        """Create test alert"""
        return {
            'type': 'workflow_critical',
            'component': 'test_workflow',
            'severity': 'critical',
            'message': 'Test workflow has critical issues',
            'timestamp': datetime.now().timestamp()
        }
    
    @pytest.mark.asyncio
    async def test_webhook_notification(self, notification_manager, test_alert):
        """Test webhook notification"""
        with patch('aiohttp.ClientSession.post') as mock_post:
            # Mock successful webhook response
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_post.return_value.__aenter__.return_value = mock_response
            
            result = await notification_manager._send_webhook_notification(test_alert)
            
            assert "successfully" in result
            mock_post.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_slack_notification_formatting(self, notification_manager, test_alert):
        """Test Slack notification formatting"""
        with patch('aiohttp.ClientSession.post') as mock_post:
            # Mock successful Slack response
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_post.return_value.__aenter__.return_value = mock_response
            
            result = await notification_manager._send_slack_notification(test_alert)
            
            assert "successfully" in result
            
            # Verify payload structure
            call_args = mock_post.call_args
            payload = call_args[1]['json']
            
            assert 'text' in payload
            assert 'attachments' in payload
            assert payload['attachments'][0]['color'] == 'danger'  # Critical alert
    
    @pytest.mark.asyncio
    async def test_alert_handling_multiple_channels(self, notification_manager, test_alert):
        """Test alert handling across multiple channels"""
        with patch.object(notification_manager, '_send_webhook_notification') as mock_webhook:
            with patch.object(notification_manager, '_send_slack_notification') as mock_slack:
                mock_webhook.return_value = "Webhook sent successfully"
                mock_slack.return_value = "Slack sent successfully"
                
                results = await notification_manager.send_alert(test_alert)
                
                assert len(results) == 2
                assert all("successfully" in result for result in results)
    
    def test_configuration_status(self, notification_manager):
        """Test configuration status reporting"""
        status = notification_manager.get_configuration_status()
        
        assert isinstance(status, dict)
        assert 'webhook' in status
        assert 'slack' in status
        assert 'email' in status
        assert status['webhook'] is True  # Configured in fixture
        assert status['slack'] is True   # Configured in fixture


class TestMetricsStorage:
    """Test suite for Metrics Storage"""
    
    @pytest.fixture
    def temp_db(self):
        """Create temporary database for testing"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        storage = MetricsStorage(db_path)
        yield storage
        
        # Cleanup
        Path(db_path).unlink(missing_ok=True)
    
    @pytest.fixture
    def sample_metric_point(self):
        """Create sample metric point"""
        return MetricPoint(
            timestamp=datetime.now(),
            metric_name="test_metric",
            value=42.0,
            labels={"component": "test"},
            component="test_component"
        )
    
    @pytest.fixture
    def sample_workflow_metrics(self):
        """Create sample workflow metrics"""
        return WorkflowMetrics(
            timestamp=datetime.now(),
            workflow_name="Test Workflow",
            success_rate=85.0,
            avg_duration=120.0,
            total_runs=20,
            successful_runs=17,
            failed_runs=3,
            status="healthy"
        )
    
    @pytest.mark.asyncio
    async def test_store_metric_point(self, temp_db, sample_metric_point):
        """Test storing metric points"""
        await temp_db.store_metric_point(sample_metric_point)
        
        # Retrieve and verify
        metrics = await temp_db.get_metric_history("test_metric", "test_component")
        
        assert len(metrics) == 1
        assert metrics[0].metric_name == "test_metric"
        assert metrics[0].value == 42.0
        assert metrics[0].component == "test_component"
    
    @pytest.mark.asyncio
    async def test_store_workflow_metrics(self, temp_db, sample_workflow_metrics):
        """Test storing workflow metrics"""
        await temp_db.store_workflow_metrics(sample_workflow_metrics)
        
        # Retrieve and verify
        workflows = await temp_db.get_workflow_history("Test Workflow")
        
        assert len(workflows) == 1
        assert workflows[0].workflow_name == "Test Workflow"
        assert workflows[0].success_rate == 85.0
        assert workflows[0].total_runs == 20
    
    @pytest.mark.asyncio
    async def test_metric_aggregates(self, temp_db):
        """Test metric aggregation functions"""
        # Store multiple metric points
        timestamps = [datetime.now() - timedelta(hours=i) for i in range(5)]
        values = [10.0, 20.0, 30.0, 40.0, 50.0]
        
        for timestamp, value in zip(timestamps, values):
            metric = MetricPoint(
                timestamp=timestamp,
                metric_name="aggregate_test",
                value=value,
                labels={},
                component="test"
            )
            await temp_db.store_metric_point(metric)
        
        # Get aggregates
        aggregates = await temp_db.get_metric_aggregates("aggregate_test", "test")
        
        assert aggregates['min'] == 10.0
        assert aggregates['max'] == 50.0
        assert aggregates['avg'] == 30.0
        assert aggregates['count'] == 5
    
    @pytest.mark.asyncio
    async def test_data_cleanup(self, temp_db, sample_metric_point):
        """Test old data cleanup"""
        # Store metric with old timestamp
        old_metric = MetricPoint(
            timestamp=datetime.now() - timedelta(days=40),
            metric_name="old_metric",
            value=1.0,
            labels={},
            component="test"
        )
        await temp_db.store_metric_point(old_metric)
        await temp_db.store_metric_point(sample_metric_point)
        
        # Cleanup data older than 30 days
        deleted_counts = await temp_db.cleanup_old_data(30)
        
        assert deleted_counts[0] == 1  # One metric point deleted
        
        # Verify only recent data remains
        remaining_metrics = await temp_db.get_metric_history("test_metric", hours=24*365)  # Long period
        assert len(remaining_metrics) == 1
        assert remaining_metrics[0].metric_name == "test_metric"


class TestCIDashboard:
    """Test suite for CI Dashboard"""
    
    @pytest.fixture
    def mock_health_monitor(self):
        """Create mock health monitor"""
        monitor = Mock()
        monitor.get_system_health = AsyncMock()
        monitor.health_checker.run_checks = AsyncMock()
        return monitor
    
    @pytest.fixture
    def dashboard(self, mock_health_monitor):
        """Create dashboard instance"""
        return CIDashboard(mock_health_monitor)
    
    @pytest.fixture
    def sample_system_health(self):
        """Create sample system health data"""
        workflow_health = CIWorkflowHealth(
            workflow_name="Test Workflow",
            status=CIHealthStatus.HEALTHY,
            success_rate=90.0,
            avg_duration=120.0,
            recent_failures=[],
            last_run=datetime.now(),
            metrics={},
            timestamp=datetime.now()
        )
        
        return CISystemHealth(
            overall_status=CIHealthStatus.HEALTHY,
            workflow_health={"Test Workflow": workflow_health},
            system_metrics={
                'overall_success_rate': 90.0,
                'healthy_checks': 4,
                'total_checks': 5
            },
            alerts=[],
            timestamp=datetime.now()
        )
    
    @pytest.mark.asyncio
    async def test_dashboard_data_generation(self, dashboard, mock_health_monitor, sample_system_health):
        """Test dashboard data generation"""
        mock_health_monitor.get_system_health.return_value = sample_system_health
        mock_health_monitor.health_checker.run_checks.return_value = {}
        
        dashboard_data = await dashboard.generate_dashboard_data()
        
        assert isinstance(dashboard_data, DashboardData)
        assert dashboard_data.system_health.overall_status == CIHealthStatus.HEALTHY
        assert len(dashboard_data.system_health.workflow_health) == 1
    
    @pytest.mark.asyncio
    async def test_html_dashboard_generation(self, dashboard, mock_health_monitor, sample_system_health):
        """Test HTML dashboard generation"""
        mock_health_monitor.get_system_health.return_value = sample_system_health
        mock_health_monitor.health_checker.run_checks.return_value = {}
        
        html_content = await dashboard.generate_html_dashboard()
        
        assert isinstance(html_content, str)
        assert '<!DOCTYPE html>' in html_content
        assert 'CI Health Dashboard' in html_content
        assert 'Test Workflow' in html_content
    
    @pytest.mark.asyncio
    async def test_json_data_generation(self, dashboard, mock_health_monitor, sample_system_health):
        """Test JSON data generation"""
        mock_health_monitor.get_system_health.return_value = sample_system_health
        mock_health_monitor.health_checker.run_checks.return_value = {}
        
        json_data = await dashboard.generate_json_data()
        
        assert isinstance(json_data, str)
        
        # Parse and verify JSON structure
        data = json.loads(json_data)
        assert 'timestamp' in data
        assert 'system_health' in data
        assert data['system_health']['overall_status'] == 'healthy'


class TestIntegration:
    """Integration tests for the complete CI monitoring system"""
    
    @pytest.fixture
    def temp_storage(self):
        """Create temporary storage for integration tests"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        yield db_path
        
        # Cleanup
        Path(db_path).unlink(missing_ok=True)
    
    @pytest.mark.asyncio
    async def test_end_to_end_monitoring_flow(self, temp_storage):
        """Test complete end-to-end monitoring flow"""
        # Initialize all components
        health_monitor = CIHealthMonitor()
        metrics_storage = MetricsStorage(temp_storage)
        notification_config = NotificationConfig()
        notification_manager = NotificationManager(notification_config)
        dashboard = CIDashboard(health_monitor)
        
        # Mock external dependencies
        with patch('subprocess.run') as mock_run:
            # Mock GitHub API calls
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = json.dumps({
                "resources": {"core": {"limit": 5000, "remaining": 4500}}
            })
            
            # Run health check
            system_health = await health_monitor.get_system_health()
            
            # Verify system health
            assert isinstance(system_health, CISystemHealth)
            
            # Store metrics
            workflow_metrics = []
            for workflow_name, health in system_health.workflow_health.items():
                workflow_metric = WorkflowMetrics(
                    timestamp=health.timestamp,
                    workflow_name=workflow_name,
                    success_rate=health.success_rate,
                    avg_duration=health.avg_duration,
                    total_runs=0,
                    successful_runs=0,
                    failed_runs=0,
                    status=health.status.value
                )
                workflow_metrics.append(workflow_metric)
                await metrics_storage.store_workflow_metrics(workflow_metric)
            
            # Generate dashboard
            dashboard_data = await dashboard.generate_dashboard_data()
            
            # Verify dashboard generation
            assert isinstance(dashboard_data, DashboardData)
            
            # Test notifications if alerts exist
            if system_health.alerts:
                with patch.object(notification_manager, 'send_alert') as mock_send:
                    mock_send.return_value = ["Test notification sent"]
                    
                    for alert in system_health.alerts:
                        results = await notification_manager.send_alert(alert)
                        assert len(results) > 0
    
    @pytest.mark.asyncio
    async def test_error_handling_and_recovery(self, temp_storage):
        """Test error handling and recovery mechanisms"""
        health_monitor = CIHealthMonitor()
        
        # Test with failing GitHub API
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = Exception("GitHub API unavailable")
            
            # Should handle errors gracefully
            system_health = await health_monitor.get_system_health()
            
            # Should still return a valid system health object
            assert isinstance(system_health, CISystemHealth)
            
            # Should have recorded the failure
            assert len(system_health.alerts) > 0 or system_health.overall_status != CIHealthStatus.HEALTHY


# Pytest configuration and fixtures
@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])