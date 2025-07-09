# CI Notification Rate Limiting

## Overview

The CI notification system now includes sophisticated rate limiting to prevent overwhelming external services during periods of high alert activity. This builds upon the existing cooldown system with per-channel rate limits, global limits, and intelligent queueing.

## Features

### Per-Channel Rate Limiting
Each notification channel has its own rate limit to respect the specific constraints of that service:

- **Webhook**: 10 notifications per minute (default)
- **Slack**: 5 notifications per minute (default)
- **Discord**: 5 notifications per minute (default)
- **Email**: 3 notifications per minute (default)
- **PagerDuty**: 2 notifications per minute (default)

### Global Rate Limiting
A global rate limit (default: 20 per minute) prevents the total notification volume from overwhelming the system, regardless of individual channel limits.

### Intelligent Queueing
When notifications are rate limited, they are queued for later delivery:
- Maximum queue size: 100 notifications per channel
- Queue timeout: 5 minutes (notifications older than this are dropped)
- Background processing attempts to send queued notifications as rate limits allow

### Token Bucket Algorithm
The rate limiter uses a token bucket algorithm for smooth rate limiting:
- Tokens are consumed when notifications are sent
- Tokens refill continuously at the configured rate
- Provides burst capability up to the bucket capacity

## Configuration

### Environment Variables

Configure rate limits via environment variables:

```bash
# Per-channel limits (notifications per minute)
export CI_RATE_LIMIT_WEBHOOK_RPM=10
export CI_RATE_LIMIT_SLACK_RPM=5
export CI_RATE_LIMIT_DISCORD_RPM=5
export CI_RATE_LIMIT_EMAIL_RPM=3
export CI_RATE_LIMIT_PAGERDUTY_RPM=2

# Global limit (total notifications per minute)
export CI_RATE_LIMIT_GLOBAL_RPM=20

# Queue configuration
export CI_RATE_LIMIT_MAX_QUEUE_SIZE=100
export CI_RATE_LIMIT_QUEUE_TIMEOUT=300  # seconds
```

### Existing Cooldown Integration

The rate limiting system works alongside the existing alert cooldown mechanism:
- **Alert Cooldown**: Prevents duplicate alerts for the same issue (default: 1 hour)
- **Rate Limiting**: Prevents overwhelming notification channels with different alerts

Both systems work together to provide comprehensive notification control.

## Usage

### Basic Integration

```python
from jimbot.infrastructure.monitoring.enhanced_ci_health import EnhancedCIHealthMonitor

# Create monitor with rate limiting
monitor = EnhancedCIHealthMonitor()

# Start monitoring (includes notification system)
await monitor.start_monitoring()

# Alerts are automatically rate limited
# No code changes needed for basic usage
```

### Advanced Usage

```python
from jimbot.infrastructure.monitoring.notifications import NotificationManager
from jimbot.infrastructure.monitoring.rate_limiter import RateLimiter, RateLimitConfig

# Custom rate limit configuration
rate_config = RateLimitConfig(
    webhook_rpm=20,
    slack_rpm=10,
    global_rpm=30
)

# Create rate limiter
rate_limiter = RateLimiter(rate_config)

# Create notification manager with custom rate limiter
notification_manager = NotificationManager(rate_limiter=rate_limiter)

# Send alert (automatically rate limited)
results = await notification_manager.send_alert(alert)

# Check results
for result in results:
    if "sent" in result:
        print(f"Notification sent: {result}")
    elif "queued" in result:
        print(f"Notification queued due to rate limit: {result}")
    elif "dropped" in result:
        print(f"Notification dropped (queue full): {result}")
```

### Monitoring Rate Limits

```python
# Get rate limit metrics
metrics = monitor.get_notification_metrics()
print(f"Rate limit metrics: {metrics['rate_limits']}")
print(f"Queued notifications: {metrics['queued_notifications']}")

# Get specific channel queue
webhook_queue = notification_manager.get_queued_notifications('webhook')
print(f"Webhook queue: {webhook_queue}")

# Manually process queued notifications
processed = await monitor.process_notification_queue()
print(f"Processed notifications: {processed}")
```

## Metrics

The rate limiter tracks the following metrics:

- **sent**: Successfully sent notifications per channel
- **rate_limited**: Notifications that hit rate limits
- **queued**: Notifications added to queue
- **dropped**: Notifications dropped due to full queue
- **queue_sizes**: Current size of each channel's queue

Access metrics via:
```python
metrics = notification_manager.get_rate_limit_metrics()
```

## Best Practices

### Setting Rate Limits

1. **Start Conservative**: Begin with lower limits and increase based on monitoring
2. **Consider Service Limits**: Respect the rate limits of external services
3. **Monitor Queue Sizes**: If queues frequently fill up, consider increasing limits
4. **Global vs Channel**: Global limit should be ≤ sum of critical channel limits

### Queue Management

1. **Queue Timeout**: Set timeout based on alert relevance duration
2. **Queue Size**: Balance between buffering capacity and memory usage
3. **Manual Processing**: Use `process_notification_queue()` during low-activity periods

### Integration with Existing Systems

1. **Preserve Cooldowns**: Rate limiting complements, doesn't replace, alert cooldowns
2. **Priority Channels**: Configure higher limits for critical channels (e.g., PagerDuty)
3. **Graceful Degradation**: System continues to function even if some channels are rate limited

## Troubleshooting

### Common Issues

**Q: Notifications are being dropped**
- Check queue sizes: `get_rate_limit_metrics()['queue_sizes']`
- Increase `CI_RATE_LIMIT_MAX_QUEUE_SIZE` if queues are full
- Increase rate limits if appropriate

**Q: Critical alerts are delayed**
- Increase rate limit for critical channels (e.g., PagerDuty)
- Consider separate notification path for critical alerts
- Reduce rate limits for less critical channels

**Q: How to test rate limiting**
```python
# Send test notifications
test_manager = NotificationManager()
await test_manager.send_test_notification()

# Check metrics
metrics = test_manager.get_rate_limit_metrics()
print(metrics)
```

## Architecture

```
┌─────────────────┐
│   CI Alert      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Alert Cooldown  │ ← Prevents duplicate alerts (existing)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Rate Limiter   │ ← New: Prevents channel overload
├─────────────────┤
│ • Token Buckets │
│ • Global Limit  │
│ • Queue Manager │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Notifications   │
├─────────────────┤
│ • Webhook       │
│ • Slack         │
│ • Discord       │
│ • Email         │
│ • PagerDuty     │
└─────────────────┘
```

## Migration Guide

For existing deployments:

1. **No Code Changes Required**: The enhanced system is backward compatible
2. **Default Limits**: Conservative defaults prevent issues
3. **Gradual Rollout**: Test with one notification channel first
4. **Monitor Metrics**: Use `get_rate_limit_metrics()` to understand behavior

## Future Enhancements

Potential improvements for future releases:

1. **Dynamic Rate Limits**: Adjust limits based on time of day or alert severity
2. **Priority Queues**: High-priority alerts bypass queues
3. **Circuit Breaker**: Disable channels that consistently fail
4. **Rate Limit Sharing**: Coordinate limits across multiple instances