"""Rate Limiting for CI Notification System

Provides sophisticated rate limiting for notification channels to prevent
overwhelming external services during high alert periods.
"""

import asyncio
import time
from collections import deque, defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional, Deque, Any, List
import logging

logger = logging.getLogger(__name__)


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting"""
    # Per-channel limits (notifications per minute)
    webhook_rpm: int = 10
    slack_rpm: int = 5
    discord_rpm: int = 5
    email_rpm: int = 3
    pagerduty_rpm: int = 2
    
    # Queue configuration
    max_queue_size: int = 100
    queue_timeout_seconds: int = 300  # 5 minutes
    
    # Global limits
    global_rpm: int = 20  # Total across all channels
    
    @classmethod
    def from_environment(cls) -> 'RateLimitConfig':
        """Create configuration from environment variables"""
        import os
        
        return cls(
            webhook_rpm=int(os.getenv('CI_RATE_LIMIT_WEBHOOK_RPM', '10')),
            slack_rpm=int(os.getenv('CI_RATE_LIMIT_SLACK_RPM', '5')),
            discord_rpm=int(os.getenv('CI_RATE_LIMIT_DISCORD_RPM', '5')),
            email_rpm=int(os.getenv('CI_RATE_LIMIT_EMAIL_RPM', '3')),
            pagerduty_rpm=int(os.getenv('CI_RATE_LIMIT_PAGERDUTY_RPM', '2')),
            max_queue_size=int(os.getenv('CI_RATE_LIMIT_MAX_QUEUE_SIZE', '100')),
            queue_timeout_seconds=int(os.getenv('CI_RATE_LIMIT_QUEUE_TIMEOUT', '300')),
            global_rpm=int(os.getenv('CI_RATE_LIMIT_GLOBAL_RPM', '20'))
        )


class TokenBucket:
    """Token bucket algorithm for rate limiting"""
    
    def __init__(self, capacity: int, refill_rate: float):
        """
        Initialize token bucket
        
        Args:
            capacity: Maximum number of tokens
            refill_rate: Tokens added per second
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = float(capacity)
        self.last_refill = time.time()
        self.lock = asyncio.Lock()
    
    async def consume(self, tokens: int = 1) -> bool:
        """
        Attempt to consume tokens
        
        Returns:
            True if tokens were consumed, False if insufficient tokens
        """
        async with self.lock:
            # Refill tokens based on elapsed time
            now = time.time()
            elapsed = now - self.last_refill
            self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
            self.last_refill = now
            
            # Try to consume
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False
    
    async def wait_for_token(self, tokens: int = 1) -> float:
        """
        Calculate wait time for tokens to become available
        
        Returns:
            Seconds to wait (0 if tokens available now)
        """
        async with self.lock:
            # Refill tokens
            now = time.time()
            elapsed = now - self.last_refill
            current_tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
            
            if current_tokens >= tokens:
                return 0.0
            
            # Calculate wait time
            needed_tokens = tokens - current_tokens
            wait_time = needed_tokens / self.refill_rate
            return wait_time


@dataclass 
class QueuedNotification:
    """A notification waiting in the rate limit queue"""
    channel: str
    alert: Dict[str, Any]
    timestamp: float
    attempts: int = 0


class RateLimiter:
    """Advanced rate limiter for CI notifications"""
    
    def __init__(self, config: Optional[RateLimitConfig] = None):
        self.config = config or RateLimitConfig.from_environment()
        
        # Create token buckets for each channel
        self.channel_buckets = {
            'webhook': TokenBucket(
                capacity=self.config.webhook_rpm,
                refill_rate=self.config.webhook_rpm / 60.0
            ),
            'slack': TokenBucket(
                capacity=self.config.slack_rpm,
                refill_rate=self.config.slack_rpm / 60.0
            ),
            'discord': TokenBucket(
                capacity=self.config.discord_rpm,
                refill_rate=self.config.discord_rpm / 60.0
            ),
            'email': TokenBucket(
                capacity=self.config.email_rpm,
                refill_rate=self.config.email_rpm / 60.0
            ),
            'pagerduty': TokenBucket(
                capacity=self.config.pagerduty_rpm,
                refill_rate=self.config.pagerduty_rpm / 60.0
            )
        }
        
        # Global rate limit bucket
        self.global_bucket = TokenBucket(
            capacity=self.config.global_rpm,
            refill_rate=self.config.global_rpm / 60.0
        )
        
        # Notification queues per channel
        self.queues: Dict[str, Deque[QueuedNotification]] = defaultdict(deque)
        
        # Metrics
        self.metrics = {
            'rate_limited_count': defaultdict(int),
            'queued_count': defaultdict(int),
            'dropped_count': defaultdict(int),
            'sent_count': defaultdict(int)
        }
        
        # Background task for processing queues
        self.queue_processor_task = None
        
    async def check_rate_limit(self, channel: str) -> bool:
        """
        Check if a notification can be sent for a channel
        
        Returns:
            True if notification can be sent, False if rate limited
        """
        if channel not in self.channel_buckets:
            logger.warning(f"Unknown channel: {channel}")
            return True
            
        # Check channel-specific limit
        channel_bucket = self.channel_buckets[channel]
        if not await channel_bucket.consume():
            self.metrics['rate_limited_count'][channel] += 1
            return False
            
        # Check global limit
        if not await self.global_bucket.consume():
            # Return the channel token since we can't use it
            channel_bucket.tokens += 1
            self.metrics['rate_limited_count']['global'] += 1
            return False
            
        self.metrics['sent_count'][channel] += 1
        return True
    
    async def queue_notification(self, channel: str, alert: Dict[str, Any]) -> bool:
        """
        Queue a notification that was rate limited
        
        Returns:
            True if queued successfully, False if queue is full
        """
        queue = self.queues[channel]
        
        # Check queue size limit
        if len(queue) >= self.config.max_queue_size:
            self.metrics['dropped_count'][channel] += 1
            logger.warning(f"Dropping notification for {channel}: queue full")
            return False
            
        # Add to queue
        notification = QueuedNotification(
            channel=channel,
            alert=alert,
            timestamp=time.time()
        )
        queue.append(notification)
        self.metrics['queued_count'][channel] += 1
        
        logger.info(f"Queued notification for {channel}: {alert.get('type', 'unknown')}")
        return True
    
    async def start_queue_processor(self):
        """Start background task to process queued notifications"""
        if self.queue_processor_task is None:
            self.queue_processor_task = asyncio.create_task(self._process_queues())
            logger.info("Started rate limiter queue processor")
    
    async def stop_queue_processor(self):
        """Stop the queue processor"""
        if self.queue_processor_task:
            self.queue_processor_task.cancel()
            try:
                await self.queue_processor_task
            except asyncio.CancelledError:
                pass
            self.queue_processor_task = None
            logger.info("Stopped rate limiter queue processor")
    
    async def _process_queues(self):
        """Background task to process queued notifications"""
        while True:
            try:
                # Process each channel's queue
                for channel, queue in self.queues.items():
                    if not queue:
                        continue
                        
                    # Check if we can send from this channel
                    if await self.check_rate_limit(channel):
                        # Get oldest notification
                        notification = queue.popleft()
                        
                        # Check if notification has expired
                        age = time.time() - notification.timestamp
                        if age > self.config.queue_timeout_seconds:
                            logger.warning(f"Dropping expired notification for {channel}")
                            self.metrics['dropped_count'][channel] += 1
                            continue
                            
                        # Yield to allow actual sending
                        # The caller will handle the actual notification
                        logger.info(f"Processing queued notification for {channel}")
                
                # Small delay to prevent busy waiting
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Error processing notification queue: {str(e)}")
                await asyncio.sleep(1)  # Back off on error
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get rate limiter metrics"""
        queue_sizes = {channel: len(queue) for channel, queue in self.queues.items()}
        
        return {
            'rate_limited': dict(self.metrics['rate_limited_count']),
            'queued': dict(self.metrics['queued_count']),
            'dropped': dict(self.metrics['dropped_count']),
            'sent': dict(self.metrics['sent_count']),
            'queue_sizes': queue_sizes,
            'config': {
                'webhook_rpm': self.config.webhook_rpm,
                'slack_rpm': self.config.slack_rpm,
                'discord_rpm': self.config.discord_rpm,
                'email_rpm': self.config.email_rpm,
                'pagerduty_rpm': self.config.pagerduty_rpm,
                'global_rpm': self.config.global_rpm
            }
        }
    
    def get_queue_for_channel(self, channel: str) -> List[Dict[str, Any]]:
        """Get queued notifications for a specific channel"""
        return [
            {
                'alert': n.alert,
                'queued_at': datetime.fromtimestamp(n.timestamp).isoformat(),
                'age_seconds': time.time() - n.timestamp,
                'attempts': n.attempts
            }
            for n in self.queues.get(channel, [])
        ]