#!/usr/bin/env python3
"""Migration script for enabling rate-limited notifications in CI monitoring.

This script helps transition from the basic notification system to the
enhanced rate-limited version.
"""

import argparse
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from jimbot.infrastructure.monitoring import (
    EnhancedCIHealthMonitor,
    NotificationManager,
    RateLimitConfig
)


def check_environment():
    """Check current environment configuration."""
    print("Current Notification Configuration:")
    print("-" * 50)
    
    # Check existing notification settings
    channels = {
        'Webhook': 'CI_ALERT_WEBHOOK_URL',
        'Slack': 'CI_ALERT_SLACK_WEBHOOK',
        'Discord': 'CI_ALERT_DISCORD_WEBHOOK',
        'Email': 'CI_ALERT_EMAIL_RECIPIENTS',
        'PagerDuty': 'CI_ALERT_PAGERDUTY_ROUTING_KEY'
    }
    
    configured_channels = []
    for channel, env_var in channels.items():
        value = os.getenv(env_var)
        if value:
            print(f"✓ {channel}: Configured")
            configured_channels.append(channel.lower())
        else:
            print(f"✗ {channel}: Not configured")
    
    print("\nRate Limiting Configuration:")
    print("-" * 50)
    
    # Check rate limit settings
    rate_limits = {
        'Webhook': 'CI_RATE_LIMIT_WEBHOOK_RPM',
        'Slack': 'CI_RATE_LIMIT_SLACK_RPM', 
        'Discord': 'CI_RATE_LIMIT_DISCORD_RPM',
        'Email': 'CI_RATE_LIMIT_EMAIL_RPM',
        'PagerDuty': 'CI_RATE_LIMIT_PAGERDUTY_RPM',
        'Global': 'CI_RATE_LIMIT_GLOBAL_RPM'
    }
    
    config = RateLimitConfig.from_environment()
    defaults = RateLimitConfig()
    
    for limit_name, env_var in rate_limits.items():
        env_value = os.getenv(env_var)
        if env_value:
            print(f"✓ {limit_name}: {env_value} RPM (custom)")
        else:
            # Get default value
            if limit_name == 'Global':
                default = defaults.global_rpm
            else:
                default = getattr(defaults, f"{limit_name.lower()}_rpm")
            print(f"- {limit_name}: {default} RPM (default)")
    
    # Queue settings
    queue_size = os.getenv('CI_RATE_LIMIT_MAX_QUEUE_SIZE', defaults.max_queue_size)
    queue_timeout = os.getenv('CI_RATE_LIMIT_QUEUE_TIMEOUT', defaults.queue_timeout_seconds)
    
    print(f"\nQueue Configuration:")
    print(f"- Max Queue Size: {queue_size}")
    print(f"- Queue Timeout: {queue_timeout} seconds")
    
    return configured_channels


def generate_env_template(configured_channels):
    """Generate environment variable template."""
    print("\nRecommended Environment Variables:")
    print("-" * 50)
    print("# Add these to your environment or .env file:\n")
    
    # Only show rate limits for configured channels
    if 'webhook' in configured_channels:
        print("# Webhook rate limit (default: 10 per minute)")
        print("export CI_RATE_LIMIT_WEBHOOK_RPM=10")
    
    if 'slack' in configured_channels:
        print("\n# Slack rate limit (default: 5 per minute)")
        print("export CI_RATE_LIMIT_SLACK_RPM=5")
    
    if 'discord' in configured_channels:
        print("\n# Discord rate limit (default: 5 per minute)")
        print("export CI_RATE_LIMIT_DISCORD_RPM=5")
    
    if 'email' in configured_channels:
        print("\n# Email rate limit (default: 3 per minute)")
        print("export CI_RATE_LIMIT_EMAIL_RPM=3")
    
    if 'pagerduty' in configured_channels:
        print("\n# PagerDuty rate limit (default: 2 per minute)")
        print("export CI_RATE_LIMIT_PAGERDUTY_RPM=2")
    
    print("\n# Global rate limit across all channels (default: 20 per minute)")
    print("export CI_RATE_LIMIT_GLOBAL_RPM=20")
    
    print("\n# Queue configuration")
    print("export CI_RATE_LIMIT_MAX_QUEUE_SIZE=100")
    print("export CI_RATE_LIMIT_QUEUE_TIMEOUT=300  # 5 minutes")


def test_notification_system():
    """Test the notification system with rate limiting."""
    print("\nTesting Notification System:")
    print("-" * 50)
    
    try:
        import asyncio
        
        async def test():
            # Create notification manager
            manager = NotificationManager()
            
            # Test configuration
            config_status = manager.get_configuration_status()
            print("Channel Configuration:")
            for channel, configured in config_status.items():
                status = "✓" if configured else "✗"
                print(f"  {status} {channel.capitalize()}")
            
            # Show rate limit configuration
            metrics = manager.get_rate_limit_metrics()
            print("\nRate Limit Configuration:")
            config = metrics.get('config', {})
            for key, value in config.items():
                print(f"  {key}: {value}")
            
            # Send test notification
            print("\nSending test notification...")
            results = await manager.send_test_notification()
            
            print("\nResults:")
            for result in results:
                print(f"  - {result}")
            
            # Check metrics
            metrics = manager.get_rate_limit_metrics()
            print("\nMetrics after test:")
            print(f"  Sent: {metrics.get('sent', {})}")
            print(f"  Queued: {metrics.get('queued', {})}")
            print(f"  Rate Limited: {metrics.get('rate_limited', {})}")
            
            await manager.stop()
        
        asyncio.run(test())
        
    except Exception as e:
        print(f"Error testing notification system: {e}")
        return False
    
    return True


def main():
    """Main migration script."""
    parser = argparse.ArgumentParser(
        description='Migrate to rate-limited CI notifications'
    )
    parser.add_argument(
        '--check-only',
        action='store_true',
        help='Only check configuration without testing'
    )
    parser.add_argument(
        '--generate-env',
        action='store_true',
        help='Generate environment variable template'
    )
    parser.add_argument(
        '--test',
        action='store_true',
        help='Test the notification system'
    )
    
    args = parser.parse_args()
    
    print("CI Notification Rate Limiting Migration Tool")
    print("=" * 50)
    print()
    
    # Check environment
    configured_channels = check_environment()
    
    if args.generate_env or not args.check_only:
        generate_env_template(configured_channels)
    
    if args.test:
        print()
        if test_notification_system():
            print("\n✓ Notification system test passed!")
        else:
            print("\n✗ Notification system test failed!")
            sys.exit(1)
    
    if not any([args.check_only, args.generate_env, args.test]):
        print("\nMigration Steps:")
        print("-" * 50)
        print("1. Review the recommended environment variables above")
        print("2. Set appropriate rate limits for your environment")
        print("3. Run with --test to verify configuration")
        print("4. Update your CI monitoring code to use EnhancedCIHealthMonitor")
        print("5. Monitor rate limit metrics after deployment")
        print("\nFor more information, see docs/CI_RATE_LIMITING.md")


if __name__ == '__main__':
    main()