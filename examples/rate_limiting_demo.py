#!/usr/bin/env python3
"""Demonstration of the CI notification rate limiting system."""

import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from jimbot.infrastructure.monitoring import (
    NotificationManager,
    NotificationConfig,
    RateLimiter,
    RateLimitConfig
)


async def basic_demo():
    """Basic demonstration of rate limiting."""
    print("=== Basic Rate Limiting Demo ===\n")
    
    # Configure rate limits (very low for demo)
    rate_config = RateLimitConfig(
        webhook_rpm=3,  # 3 per minute
        slack_rpm=2,    # 2 per minute
        global_rpm=4    # 4 total per minute
    )
    
    # Create notification manager
    rate_limiter = RateLimiter(rate_config)
    
    # Mock notification config
    notif_config = NotificationConfig()
    notif_config.webhook_url = "https://example.com/webhook"
    notif_config.slack_webhook = "https://slack.com/webhook"
    
    manager = NotificationManager(
        config=notif_config,
        rate_limiter=rate_limiter
    )
    
    # Mock the actual send methods to avoid real HTTP calls
    async def mock_send(alert):
        await asyncio.sleep(0.1)  # Simulate network delay
        return f"{alert['type']} sent successfully"
    
    manager._send_webhook_notification = mock_send
    manager._send_slack_notification = mock_send
    
    # Start the manager
    await manager.start()
    
    print("Sending 6 alerts in rapid succession...")
    print("Rate limits: Webhook=3/min, Slack=2/min, Global=4/min\n")
    
    # Send multiple alerts
    for i in range(6):
        alert = {
            'type': f'test_alert_{i}',
            'severity': 'warning',
            'message': f'Test alert number {i}',
            'component': 'demo'
        }
        
        print(f"\nAlert {i}:")
        results = await manager.send_alert(alert)
        for result in results:
            print(f"  - {result}")
    
    # Show metrics
    print("\n=== Rate Limit Metrics ===")
    metrics = manager.get_rate_limit_metrics()
    print(f"Sent: {dict(metrics['sent'])}")
    print(f"Rate Limited: {dict(metrics['rate_limited'])}")
    print(f"Queued: {dict(metrics['queued'])}")
    print(f"Queue Sizes: {metrics['queue_sizes']}")
    
    # Show queued notifications
    print("\n=== Queued Notifications ===")
    queues = manager.get_queued_notifications()
    for channel, queue in queues.items():
        if queue:
            print(f"{channel}: {len(queue)} notifications queued")
            for notif in queue[:2]:  # Show first 2
                print(f"  - {notif['alert']['type']} (age: {notif['age_seconds']:.1f}s)")
    
    # Clean up
    await manager.stop()


async def queue_processing_demo():
    """Demonstrate queue processing."""
    print("\n\n=== Queue Processing Demo ===\n")
    
    # Very restrictive limits for demo
    rate_config = RateLimitConfig(
        webhook_rpm=1,  # 1 per minute (1 per second for demo)
        global_rpm=1
    )
    
    rate_limiter = RateLimiter(rate_config)
    
    notif_config = NotificationConfig()
    notif_config.webhook_url = "https://example.com/webhook"
    
    manager = NotificationManager(
        config=notif_config,
        rate_limiter=rate_limiter
    )
    
    # Mock send
    send_times = []
    async def mock_send_with_timing(alert):
        send_times.append(asyncio.get_event_loop().time())
        await asyncio.sleep(0.1)
        return f"{alert['type']} sent at {len(send_times)}"
    
    manager._send_webhook_notification = mock_send_with_timing
    
    await manager.start()
    
    print("Sending 3 alerts with 1/minute rate limit...")
    
    # Send 3 alerts quickly
    for i in range(3):
        alert = {'type': f'queued_{i}', 'message': f'Alert {i}'}
        results = await manager.send_alert(alert)
        print(f"Alert {i}: {results[0]}")
    
    print("\nWaiting for queue processor...")
    print("(In production, the queue processor runs continuously)")
    
    # Wait and manually trigger queue processing
    for i in range(3):
        await asyncio.sleep(1.5)  # Wait for rate limit to allow next
        processed = await manager.process_queued_notifications()
        if any(processed.values()):
            print(f"\nProcessed from queue: {processed}")
    
    # Show timing
    if len(send_times) > 1:
        print(f"\nActual send times (seconds between sends):")
        for i in range(1, len(send_times)):
            gap = send_times[i] - send_times[i-1]
            print(f"  Send {i-1} -> {i}: {gap:.1f}s")
    
    await manager.stop()


async def token_bucket_demo():
    """Demonstrate token bucket behavior."""
    print("\n\n=== Token Bucket Demo ===\n")
    
    from jimbot.infrastructure.monitoring.rate_limiter import TokenBucket
    
    # Create bucket with 3 tokens, refilling at 1 token/second
    bucket = TokenBucket(capacity=3, refill_rate=1.0)
    
    print("Token bucket: capacity=3, refill_rate=1/second")
    print("\nConsuming tokens:")
    
    # Consume all tokens
    for i in range(4):
        if await bucket.consume():
            print(f"  Token {i}: ✓ Consumed")
        else:
            print(f"  Token {i}: ✗ Denied (bucket empty)")
    
    print("\nWaiting 2 seconds for refill...")
    await asyncio.sleep(2)
    
    print("\nTrying again:")
    for i in range(3):
        if await bucket.consume():
            print(f"  Token {i}: ✓ Consumed")
        else:
            print(f"  Token {i}: ✗ Denied")


async def main():
    """Run all demos."""
    print("CI Notification Rate Limiting Demonstration")
    print("=" * 50)
    
    await basic_demo()
    await queue_processing_demo()
    await token_bucket_demo()
    
    print("\n" + "=" * 50)
    print("Demo complete!")
    print("\nKey Takeaways:")
    print("- Rate limits prevent overwhelming external services")
    print("- Notifications are queued when rate limited")
    print("- Token bucket allows burst capacity")
    print("- Queue processor handles delayed sending")
    print("\nSee docs/CI_RATE_LIMITING.md for more information")


if __name__ == '__main__':
    # For demo purposes, speed up the token refill
    import time
    original_time = time.time
    start_time = original_time()
    
    def fast_time():
        # Make time pass 60x faster for the demo
        return start_time + (original_time() - start_time) * 60
    
    # Patch time for demo (don't do this in production!)
    time.time = fast_time
    
    asyncio.run(main())