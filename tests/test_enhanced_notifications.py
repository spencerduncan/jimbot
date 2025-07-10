"""Unit tests for enhanced notification system with rate limiting"""

import asyncio
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from jimbot.infrastructure.monitoring.notifications import NotificationManager, NotificationConfig
from jimbot.infrastructure.monitoring.rate_limiter import RateLimiter, RateLimitConfig
from jimbot.infrastructure.monitoring.enhanced_ci_health import EnhancedCIHealthMonitor


class TestEnhancedNotificationManager:
    """Test notification manager with rate limiting"""
    
    @pytest.fixture
    def mock_config(self):
        """Create mock notification config"""
        config = NotificationConfig()
        config.webhook_url = "https://example.com/webhook"
        config.slack_webhook = "https://hooks.slack.com/test"
        config.discord_webhook = "https://discord.com/api/webhooks/test"
        config.email_recipients = ["test@example.com"]
        config.pagerduty_routing_key = "test-key"
        return config
    
    @pytest.fixture
    def rate_limiter(self):
        """Create rate limiter with test config"""
        config = RateLimitConfig(
            webhook_rpm=2,
            slack_rpm=1,
            global_rpm=3
        )
        return RateLimiter(config)
    
    @pytest.fixture
    def notification_manager(self, mock_config, rate_limiter):
        """Create notification manager with mocked config"""
        return NotificationManager(config=mock_config, rate_limiter=rate_limiter)
    
    @pytest.mark.asyncio
    async def test_rate_limited_notifications(self, notification_manager):
        """Test that notifications are rate limited"""
        # Mock the actual send methods
        notification_manager._send_webhook_notification = AsyncMock(return_value="webhook: sent")
        notification_manager._send_slack_notification = AsyncMock(return_value="slack: sent")
        
        alert = {
            'type': 'test_alert',
            'severity': 'warning',
            'message': 'Test message',
            'component': 'test'
        }
        
        # First round should work (within limits)
        results1 = await notification_manager.send_alert(alert)
        
        # Should have sent webhook and slack (2 out of 3 global limit)
        assert any("webhook: sent" in r for r in results1)
        assert any("slack: sent" in r for r in results1)
        
        # Second round should hit limits
        results2 = await notification_manager.send_alert(alert)
        
        # Should have queued notifications
        assert any("queued (rate limited)" in r for r in results2)
        
        # Verify actual sends
        assert notification_manager._send_webhook_notification.call_count <= 2  # webhook limit
        assert notification_manager._send_slack_notification.call_count <= 1   # slack limit
    
    @pytest.mark.asyncio
    async def test_queue_overflow_handling(self, notification_manager):
        """Test handling when rate limit queue is full"""
        # Set very small queue
        notification_manager.rate_limiter.config.max_queue_size = 1
        
        # Mock send methods
        notification_manager._send_webhook_notification = AsyncMock(return_value="sent")
        
        alert = {'type': 'test', 'message': 'Test'}
        
        # Fill up rate limit quickly
        for _ in range(5):
            await notification_manager.send_alert(alert)
        
        # Check results contain dropped notifications
        results = await notification_manager.send_alert(alert)
        assert any("dropped (queue full)" in r for r in results)
    
    @pytest.mark.asyncio
    async def test_notification_history(self, notification_manager):
        """Test notification history is maintained"""
        notification_manager._send_webhook_notification = AsyncMock(return_value="sent")
        
        alert = {'type': 'test', 'message': 'Test'}
        await notification_manager.send_alert(alert)
        
        history = notification_manager.get_notification_history()
        assert len(history) > 0
        assert history[0]['alert'] == alert
    
    @pytest.mark.asyncio
    async def test_manual_queue_processing(self, notification_manager):
        """Test manual processing of queued notifications"""
        # Mock send methods
        notification_manager._send_webhook_notification = AsyncMock(return_value="sent")
        notification_manager._send_slack_notification = AsyncMock(return_value="sent")
        
        # Queue some notifications
        alert = {'type': 'test', 'message': 'Queued'}
        await notification_manager.rate_limiter.queue_notification('webhook', alert)
        await notification_manager.rate_limiter.queue_notification('slack', alert)
        
        # Process queue
        processed = await notification_manager.process_queued_notifications()
        
        # Should have processed at least some
        assert sum(processed.values()) > 0
    
    def test_rate_limit_metrics(self, notification_manager):
        """Test rate limit metrics retrieval"""
        metrics = notification_manager.get_rate_limit_metrics()
        
        assert 'config' in metrics
        assert 'rate_limited' in metrics
        assert 'queued' in metrics
        assert 'sent' in metrics
        assert 'dropped' in metrics
    
    def test_queued_notifications_retrieval(self, notification_manager):
        """Test getting queued notifications"""
        # Add to internal queue directly for testing
        from jimbot.infrastructure.monitoring.rate_limiter import QueuedNotification
        notification = QueuedNotification(
            channel='webhook',
            alert={'type': 'test'},
            timestamp=1234567890
        )
        notification_manager.rate_limiter.queues['webhook'].append(notification)
        
        # Get all queues
        all_queued = notification_manager.get_queued_notifications()
        assert 'webhook' in all_queued
        assert len(all_queued['webhook']) == 1
        
        # Get specific channel
        webhook_queued = notification_manager.get_queued_notifications('webhook')
        assert len(webhook_queued['webhook']) == 1


class TestEnhancedCIHealthMonitor:
    """Test enhanced CI health monitor with rate limiting"""
    
    @pytest.fixture
    def mock_notification_manager(self):
        """Create mock notification manager"""
        manager = Mock(spec=NotificationManager)
        manager.send_alert = AsyncMock(return_value=["webhook: sent", "slack: queued"])
        manager.start = AsyncMock()
        manager.stop = AsyncMock()
        manager.get_rate_limit_metrics = Mock(return_value={'sent': {'webhook': 10}})
        manager.get_queued_notifications = Mock(return_value={'webhook': []})
        manager.get_notification_history = Mock(return_value=[])
        manager.process_queued_notifications = AsyncMock(return_value={'webhook': 2})
        return manager
    
    @pytest.fixture
    def mock_metrics_collector(self):
        """Create mock metrics collector"""
        collector = Mock()
        collector.increment_counter = Mock()
        collector.set_gauge = Mock()
        return collector
    
    @pytest.fixture
    def enhanced_monitor(self, mock_notification_manager, mock_metrics_collector):
        """Create enhanced CI health monitor"""
        monitor = EnhancedCIHealthMonitor(
            metrics_collector=mock_metrics_collector,
            notification_manager=mock_notification_manager
        )
        # Override some methods to prevent full initialization
        monitor._register_ci_health_checks = Mock()
        return monitor
    
    @pytest.mark.asyncio
    async def test_alert_processing_with_rate_limiting(self, enhanced_monitor):
        """Test alert processing uses rate-limited notifications"""
        alert = {
            'type': 'test_alert',
            'severity': 'warning',
            'message': 'Test',
            'timestamp': 1234567890
        }
        
        await enhanced_monitor._process_alert_notification(alert)
        
        # Should have called notification manager
        enhanced_monitor.notification_manager.send_alert.assert_called_once_with(alert)
        
        # Should track metrics
        enhanced_monitor.metrics_collector.increment_counter.assert_any_call('ci_alerts_sent')
        enhanced_monitor.metrics_collector.increment_counter.assert_any_call('ci_alerts_queued')
    
    @pytest.mark.asyncio
    async def test_start_stop_lifecycle(self, enhanced_monitor):
        """Test monitor starts and stops notification manager"""
        # Mock parent start_monitoring to prevent full execution
        with patch.object(EnhancedCIHealthMonitor, 'start_monitoring', 
                         new=AsyncMock()):
            await enhanced_monitor.start_monitoring()
            enhanced_monitor.notification_manager.start.assert_called_once()
        
        await enhanced_monitor.stop_monitoring()
        enhanced_monitor.notification_manager.stop.assert_called_once()
    
    def test_notification_metrics_retrieval(self, enhanced_monitor):
        """Test getting notification metrics"""
        metrics = enhanced_monitor.get_notification_metrics()
        
        assert 'rate_limits' in metrics
        assert 'queued_notifications' in metrics
        assert 'notification_history' in metrics
    
    @pytest.mark.asyncio
    async def test_manual_queue_processing(self, enhanced_monitor):
        """Test manual queue processing"""
        result = await enhanced_monitor.process_notification_queue()
        
        assert result == {'webhook': 2}
        enhanced_monitor.notification_manager.process_queued_notifications.assert_called_once()
    
    def test_rate_limit_config_retrieval(self, enhanced_monitor):
        """Test getting rate limit configuration"""
        enhanced_monitor.notification_manager.get_rate_limit_metrics.return_value = {
            'config': {
                'webhook_rpm': 10,
                'slack_rpm': 5
            }
        }
        
        config = enhanced_monitor.get_rate_limit_config()
        assert config['webhook_rpm'] == 10
        assert config['slack_rpm'] == 5


@pytest.mark.asyncio
async def test_integration_full_flow():
    """Integration test of full notification flow with rate limiting"""
    # Create real instances with test config
    rate_config = RateLimitConfig(
        webhook_rpm=2,
        slack_rpm=1,
        global_rpm=2,
        max_queue_size=5
    )
    rate_limiter = RateLimiter(rate_config)
    
    notif_config = NotificationConfig()
    notif_config.webhook_url = "https://example.com/webhook"
    notif_config.slack_webhook = "https://slack.com/webhook"
    
    notification_manager = NotificationManager(
        config=notif_config,
        rate_limiter=rate_limiter
    )
    
    # Mock actual HTTP calls
    with patch('aiohttp.ClientSession') as mock_session:
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value = mock_response
        
        # Send multiple alerts
        alerts = [
            {'type': f'alert_{i}', 'message': f'Test {i}', 'severity': 'warning'}
            for i in range(5)
        ]
        
        all_results = []
        for alert in alerts:
            results = await notification_manager.send_alert(alert)
            all_results.extend(results)
        
        # Should have mix of sent and queued
        sent_count = len([r for r in all_results if 'sent' in r])
        queued_count = len([r for r in all_results if 'queued' in r])
        
        assert sent_count == 2  # Global limit
        assert queued_count > 0  # Some were queued
        
        # Check metrics
        metrics = notification_manager.get_rate_limit_metrics()
        assert metrics['sent']['webhook'] + metrics['sent']['slack'] == 2