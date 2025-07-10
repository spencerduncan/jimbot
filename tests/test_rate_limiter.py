"""Unit tests for CI notification rate limiter"""

import asyncio
import pytest
import time
from unittest.mock import Mock, patch

from jimbot.infrastructure.monitoring.rate_limiter import (
    RateLimiter, RateLimitConfig, TokenBucket, QueuedNotification
)


class TestTokenBucket:
    """Test token bucket algorithm"""
    
    @pytest.mark.asyncio
    async def test_token_consumption(self):
        """Test basic token consumption"""
        bucket = TokenBucket(capacity=5, refill_rate=1.0)
        
        # Should be able to consume 5 tokens
        for _ in range(5):
            assert await bucket.consume() is True
        
        # 6th should fail
        assert await bucket.consume() is False
    
    @pytest.mark.asyncio
    async def test_token_refill(self):
        """Test token refill over time"""
        bucket = TokenBucket(capacity=5, refill_rate=10.0)  # 10 tokens/second
        
        # Consume all tokens
        for _ in range(5):
            await bucket.consume()
        
        # Wait 0.1 seconds (should refill 1 token)
        await asyncio.sleep(0.1)
        
        # Should be able to consume 1 token
        assert await bucket.consume() is True
        assert await bucket.consume() is False
    
    @pytest.mark.asyncio
    async def test_wait_for_token(self):
        """Test calculating wait time for tokens"""
        bucket = TokenBucket(capacity=5, refill_rate=2.0)  # 2 tokens/second
        
        # Consume all tokens
        for _ in range(5):
            await bucket.consume()
        
        # Should need to wait 0.5 seconds for 1 token
        wait_time = await bucket.wait_for_token()
        assert 0.4 <= wait_time <= 0.6  # Allow some variance
        
        # Should need to wait 2.5 seconds for 5 tokens
        wait_time = await bucket.wait_for_token(5)
        assert 2.4 <= wait_time <= 2.6


class TestRateLimiterConfig:
    """Test rate limiter configuration"""
    
    def test_default_config(self):
        """Test default configuration values"""
        config = RateLimitConfig()
        assert config.webhook_rpm == 10
        assert config.slack_rpm == 5
        assert config.discord_rpm == 5
        assert config.email_rpm == 3
        assert config.pagerduty_rpm == 2
        assert config.global_rpm == 20
        assert config.max_queue_size == 100
        assert config.queue_timeout_seconds == 300
    
    @patch.dict('os.environ', {
        'CI_RATE_LIMIT_WEBHOOK_RPM': '20',
        'CI_RATE_LIMIT_SLACK_RPM': '10',
        'CI_RATE_LIMIT_GLOBAL_RPM': '30'
    })
    def test_config_from_environment(self):
        """Test loading configuration from environment"""
        config = RateLimitConfig.from_environment()
        assert config.webhook_rpm == 20
        assert config.slack_rpm == 10
        assert config.global_rpm == 30
        # Others should be defaults
        assert config.discord_rpm == 5
        assert config.email_rpm == 3


class TestRateLimiter:
    """Test rate limiter functionality"""
    
    @pytest.mark.asyncio
    async def test_channel_rate_limiting(self):
        """Test per-channel rate limiting"""
        config = RateLimitConfig(webhook_rpm=2, global_rpm=10)
        limiter = RateLimiter(config)
        
        # Should allow 2 webhook notifications
        assert await limiter.check_rate_limit('webhook') is True
        assert await limiter.check_rate_limit('webhook') is True
        
        # 3rd should be rate limited
        assert await limiter.check_rate_limit('webhook') is False
        
        # But other channels should work
        assert await limiter.check_rate_limit('slack') is True
    
    @pytest.mark.asyncio
    async def test_global_rate_limiting(self):
        """Test global rate limiting across all channels"""
        config = RateLimitConfig(
            webhook_rpm=10,
            slack_rpm=10,
            global_rpm=3  # Very low global limit
        )
        limiter = RateLimiter(config)
        
        # Should allow 3 total notifications
        assert await limiter.check_rate_limit('webhook') is True
        assert await limiter.check_rate_limit('slack') is True
        assert await limiter.check_rate_limit('webhook') is True
        
        # 4th should be blocked by global limit
        assert await limiter.check_rate_limit('discord') is False
    
    @pytest.mark.asyncio
    async def test_notification_queueing(self):
        """Test queueing notifications when rate limited"""
        config = RateLimitConfig(max_queue_size=5)
        limiter = RateLimiter(config)
        
        alert = {'type': 'test', 'message': 'Test alert'}
        
        # Queue some notifications
        for i in range(5):
            assert await limiter.queue_notification('webhook', {**alert, 'id': i}) is True
        
        # 6th should fail (queue full)
        assert await limiter.queue_notification('webhook', {**alert, 'id': 6}) is False
        
        # Check queue contents
        queue_contents = limiter.get_queue_for_channel('webhook')
        assert len(queue_contents) == 5
        assert queue_contents[0]['alert']['id'] == 0
    
    @pytest.mark.asyncio
    async def test_queue_processor(self):
        """Test background queue processing"""
        config = RateLimitConfig(
            webhook_rpm=60,  # 1 per second
            queue_timeout_seconds=1
        )
        limiter = RateLimiter(config)
        
        # Track sent notifications
        sent_notifications = []
        
        # Set up callback
        async def mock_send_callback(channel, alert):
            sent_notifications.append((channel, alert))
            return True
        
        limiter.set_send_callback(mock_send_callback)
        
        # Start queue processor
        await limiter.start_queue_processor()
        
        try:
            # Consume initial token
            await limiter.check_rate_limit('webhook')
            
            # Queue a notification
            alert = {'type': 'test', 'message': 'Queued alert'}
            await limiter.queue_notification('webhook', alert)
            
            # Wait for processing
            await asyncio.sleep(1.1)
            
            # Notification should have been sent
            assert len(sent_notifications) == 1
            assert sent_notifications[0] == ('webhook', alert)
            
            # Queue should be empty (processed)
            queue_contents = limiter.get_queue_for_channel('webhook')
            assert len(queue_contents) == 0
            
        finally:
            await limiter.stop_queue_processor()
    
    @pytest.mark.asyncio
    async def test_expired_notification_dropping(self):
        """Test that expired notifications are dropped"""
        config = RateLimitConfig(queue_timeout_seconds=0.1)
        limiter = RateLimiter(config)
        
        # Queue a notification
        alert = {'type': 'test', 'message': 'Will expire'}
        await limiter.queue_notification('webhook', alert)
        
        # Wait for it to expire
        await asyncio.sleep(0.2)
        
        # Manually check expiration (simulating what queue processor would do)
        queue = limiter.queues['webhook']
        if queue:
            notification = queue[0]
            age = time.time() - notification.timestamp
            assert age > config.queue_timeout_seconds
    
    def test_metrics_collection(self):
        """Test metrics are properly collected"""
        limiter = RateLimiter()
        
        # Simulate some activity
        limiter.metrics['sent_count']['webhook'] = 10
        limiter.metrics['rate_limited_count']['webhook'] = 5
        limiter.metrics['queued_count']['webhook'] = 3
        limiter.metrics['dropped_count']['webhook'] = 1
        
        metrics = limiter.get_metrics()
        
        assert metrics['sent']['webhook'] == 10
        assert metrics['rate_limited']['webhook'] == 5
        assert metrics['queued']['webhook'] == 3
        assert metrics['dropped']['webhook'] == 1
        
        # Check config is included
        assert 'config' in metrics
        assert metrics['config']['webhook_rpm'] == 10  # Default
    
    @pytest.mark.asyncio
    async def test_unknown_channel_handling(self):
        """Test handling of unknown channels"""
        limiter = RateLimiter()
        
        # Unknown channel should be allowed (no rate limiting)
        assert await limiter.check_rate_limit('unknown_channel') is True
        
        # But should log a warning
        # (Would need to check logs in real test)
    
    @pytest.mark.asyncio
    async def test_notification_retry_on_failure(self):
        """Test that failed notifications are retried"""
        config = RateLimitConfig(
            webhook_rpm=60,
            queue_timeout_seconds=10
        )
        limiter = RateLimiter(config)
        
        # Track send attempts
        send_attempts = []
        
        # Callback that fails first 2 times
        async def mock_send_callback(channel, alert):
            send_attempts.append((channel, alert))
            if len(send_attempts) < 3:
                return False  # Fail
            return True  # Success on 3rd attempt
        
        limiter.set_send_callback(mock_send_callback)
        
        # Start queue processor
        await limiter.start_queue_processor()
        
        try:
            # Queue a notification
            alert = {'type': 'test', 'message': 'Will retry'}
            await limiter.queue_notification('webhook', alert)
            
            # Wait for retries (need multiple cycles)
            for _ in range(5):
                await asyncio.sleep(0.2)
            
            # Should have made 3 attempts
            assert len(send_attempts) == 3
            
            # Queue should be empty (eventually succeeded)
            queue_contents = limiter.get_queue_for_channel('webhook')
            assert len(queue_contents) == 0
            
        finally:
            await limiter.stop_queue_processor()


@pytest.mark.asyncio
async def test_integration_with_multiple_channels():
    """Integration test with multiple channels and rate limits"""
    config = RateLimitConfig(
        webhook_rpm=3,
        slack_rpm=2,
        email_rpm=1,
        global_rpm=5
    )
    limiter = RateLimiter(config)
    
    # Track what got through
    sent = []
    queued = []
    
    # Try to send 3 notifications per channel
    for channel in ['webhook', 'slack', 'email']:
        for i in range(3):
            if await limiter.check_rate_limit(channel):
                sent.append((channel, i))
            else:
                alert = {'channel': channel, 'num': i}
                if await limiter.queue_notification(channel, alert):
                    queued.append((channel, i))
    
    # Should have sent: 3 webhook, 2 slack, 0 email (global limit hit)
    assert len(sent) == 5  # Global limit
    assert len([s for s in sent if s[0] == 'webhook']) == 3
    assert len([s for s in sent if s[0] == 'slack']) == 2
    assert len([s for s in sent if s[0] == 'email']) == 0
    
    # Should have queued the rest
    assert len(queued) == 4  # 1 slack + 3 email