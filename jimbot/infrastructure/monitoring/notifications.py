"""Notification System for CI Health Monitoring

Provides various notification channels for CI health alerts and status updates.
"""

import asyncio
import json
import logging
import os
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from .rate_limiter import RateLimiter, RateLimitConfig

logger = logging.getLogger(__name__)


@dataclass
class NotificationConfig:
    """Configuration for notification channels"""
    webhook_url: Optional[str] = None
    slack_webhook: Optional[str] = None
    discord_webhook: Optional[str] = None
    email_smtp_server: Optional[str] = None
    email_smtp_port: int = 587
    email_username: Optional[str] = None
    email_password: Optional[str] = None
    email_recipients: List[str] = None
    pagerduty_routing_key: Optional[str] = None
    
    @classmethod
    def from_environment(cls) -> 'NotificationConfig':
        """Create configuration from environment variables"""
        return cls(
            webhook_url=os.getenv('CI_ALERT_WEBHOOK_URL'),
            slack_webhook=os.getenv('CI_ALERT_SLACK_WEBHOOK'),
            discord_webhook=os.getenv('CI_ALERT_DISCORD_WEBHOOK'),
            email_smtp_server=os.getenv('CI_ALERT_EMAIL_SMTP_SERVER'),
            email_smtp_port=int(os.getenv('CI_ALERT_EMAIL_SMTP_PORT', '587')),
            email_username=os.getenv('CI_ALERT_EMAIL_USERNAME'),
            email_password=os.getenv('CI_ALERT_EMAIL_PASSWORD'),
            email_recipients=os.getenv('CI_ALERT_EMAIL_RECIPIENTS', '').split(',') if os.getenv('CI_ALERT_EMAIL_RECIPIENTS') else [],
            pagerduty_routing_key=os.getenv('CI_ALERT_PAGERDUTY_ROUTING_KEY')
        )


class NotificationManager:
    """Manages all notification channels for CI alerts"""
    
    def __init__(self, config: Optional[NotificationConfig] = None, 
                 rate_limiter: Optional[RateLimiter] = None):
        self.config = config or NotificationConfig.from_environment()
        self.notification_history = []
        self.rate_limiter = rate_limiter or RateLimiter()
        self._started = False
        
    async def start(self):
        """Start the notification manager (including rate limiter)"""
        if not self._started:
            # Register callback for rate limiter to send notifications
            self.rate_limiter.set_send_callback(self._send_notification)
            await self.rate_limiter.start_queue_processor()
            self._started = True
            logger.info("NotificationManager started with rate limiting")
    
    async def stop(self):
        """Stop the notification manager"""
        if self._started:
            await self.rate_limiter.stop_queue_processor()
            self._started = False
            logger.info("NotificationManager stopped")
    
    async def send_alert(self, alert: Dict[str, Any]) -> List[str]:
        """Send alert through all configured channels with rate limiting"""
        results = []
        
        # Ensure rate limiter is started
        if not self._started:
            await self.start()
        
        try:
            # Prepare channels and their send functions
            channels = []
            
            if self.config.webhook_url:
                channels.append(('webhook', self._send_webhook_notification))
            
            if self.config.slack_webhook:
                channels.append(('slack', self._send_slack_notification))
            
            if self.config.discord_webhook:
                channels.append(('discord', self._send_discord_notification))
            
            if self.config.email_recipients:
                channels.append(('email', self._send_email_notification))
            
            if self.config.pagerduty_routing_key:
                channels.append(('pagerduty', self._send_pagerduty_notification))
            
            # Send notifications with rate limiting
            tasks = []
            for channel_name, send_func in channels:
                # Check rate limit
                if await self.rate_limiter.check_rate_limit(channel_name):
                    # Can send immediately
                    tasks.append(send_func(alert))
                    results.append(f"{channel_name}: sending")
                else:
                    # Rate limited - queue it
                    if await self.rate_limiter.queue_notification(channel_name, alert):
                        results.append(f"{channel_name}: queued (rate limited)")
                    else:
                        results.append(f"{channel_name}: dropped (queue full)")
            
            # Execute immediate sends
            if tasks:
                notification_results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Update results with actual send results
                task_idx = 0
                for i, result_msg in enumerate(results):
                    if ": sending" in result_msg:
                        channel = result_msg.split(":")[0]
                        if task_idx < len(notification_results):
                            result = notification_results[task_idx]
                            if isinstance(result, Exception):
                                results[i] = f"{channel}: failed - {str(result)}"
                            else:
                                results[i] = result
                            task_idx += 1
            
            if not channels:
                results.append("No notification channels configured")
            
            # Log notification attempt
            self._log_notification(alert, results)
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to send alert notifications: {str(e)}")
            return [f"Notification system error: {str(e)}"]
    
    async def _send_notification(self, channel: str, alert: Dict[str, Any]) -> bool:
        """Send a single notification to a specific channel
        
        This method is called by the rate limiter when processing queued notifications.
        
        Args:
            channel: The notification channel ('webhook', 'slack', etc.)
            alert: The alert data to send
            
        Returns:
            bool: True if notification was sent successfully
        """
        try:
            # Get the appropriate send method for the channel
            send_methods = {
                'webhook': self._send_webhook_notification,
                'slack': self._send_slack_notification,
                'discord': self._send_discord_notification,
                'email': self._send_email_notification,
                'pagerduty': self._send_pagerduty_notification
            }
            
            send_method = send_methods.get(channel)
            if not send_method:
                logger.error(f"Unknown notification channel: {channel}")
                return False
                
            # Check if channel is configured
            if channel == 'webhook' and not self.config.webhook_url:
                return False
            elif channel == 'slack' and not self.config.slack_webhook:
                return False
            elif channel == 'discord' and not self.config.discord_webhook:
                return False
            elif channel == 'email' and not self.config.email_smtp_server:
                return False
            elif channel == 'pagerduty' and not self.config.pagerduty_routing_key:
                return False
                
            # Send the notification
            result = await send_method(alert)
            
            # Check if successful (result should contain "success" or not contain "error"/"failed")
            success = "success" in result.lower() or ("error" not in result.lower() and "failed" not in result.lower())
            
            if success:
                logger.info(f"Successfully sent {channel} notification: {result}")
            else:
                logger.warning(f"Failed to send {channel} notification: {result}")
                
            return success
            
        except Exception as e:
            logger.error(f"Error sending {channel} notification: {str(e)}")
            return False
    
    async def _send_webhook_notification(self, alert: Dict[str, Any]) -> str:
        """Send generic webhook notification"""
        try:
            import aiohttp
            
            payload = {
                'type': 'ci_alert',
                'alert': alert,
                'timestamp': alert.get('timestamp', datetime.now().timestamp()),
                'severity': alert.get('severity', 'unknown'),
                'component': alert.get('component', 'unknown'),
                'message': alert.get('message', 'No message provided')
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.config.webhook_url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        return "Webhook notification sent successfully"
                    else:
                        return f"Webhook notification failed: HTTP {response.status}"
                        
        except Exception as e:
            return f"Webhook notification error: {str(e)}"
    
    async def _send_slack_notification(self, alert: Dict[str, Any]) -> str:
        """Send Slack notification"""
        try:
            import aiohttp
            
            severity_emoji = {
                'critical': '🚨',
                'warning': '⚠️',
                'info': 'ℹ️'
            }
            
            severity_color = {
                'critical': 'danger',
                'warning': 'warning',
                'info': 'good'
            }
            
            emoji = severity_emoji.get(alert.get('severity', 'info'), '❓')
            color = severity_color.get(alert.get('severity', 'info'), '#666666')
            
            timestamp = alert.get('timestamp', datetime.now().timestamp())
            formatted_time = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S UTC')
            
            payload = {
                'text': f"{emoji} CI Health Alert",
                'attachments': [
                    {
                        'color': color,
                        'title': f"{alert.get('type', 'Unknown').replace('_', ' ').title()}",
                        'fields': [
                            {
                                'title': 'Component',
                                'value': alert.get('component', 'Unknown'),
                                'short': True
                            },
                            {
                                'title': 'Severity',
                                'value': alert.get('severity', 'Unknown').title(),
                                'short': True
                            },
                            {
                                'title': 'Message',
                                'value': alert.get('message', 'No details provided'),
                                'short': False
                            },
                            {
                                'title': 'Time',
                                'value': formatted_time,
                                'short': True
                            }
                        ],
                        'footer': 'CI Health Monitor',
                        'ts': timestamp
                    }
                ]
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.config.slack_webhook,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        return "Slack notification sent successfully"
                    else:
                        response_text = await response.text()
                        return f"Slack notification failed: HTTP {response.status} - {response_text}"
                        
        except Exception as e:
            return f"Slack notification error: {str(e)}"
    
    async def _send_discord_notification(self, alert: Dict[str, Any]) -> str:
        """Send Discord notification"""
        try:
            import aiohttp
            
            severity_emoji = {
                'critical': '🚨',
                'warning': '⚠️',
                'info': 'ℹ️'
            }
            
            severity_color = {
                'critical': 15158332,  # Red
                'warning': 16776960,   # Yellow
                'info': 3447003        # Blue
            }
            
            emoji = severity_emoji.get(alert.get('severity', 'info'), '❓')
            color = severity_color.get(alert.get('severity', 'info'), 6710886)  # Gray
            
            timestamp = alert.get('timestamp', datetime.now().timestamp())
            formatted_time = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S UTC')
            
            payload = {
                'embeds': [
                    {
                        'title': f"{emoji} CI Health Alert",
                        'description': f"**{alert.get('type', 'Unknown').replace('_', ' ').title()}**",
                        'color': color,
                        'fields': [
                            {
                                'name': 'Component',
                                'value': alert.get('component', 'Unknown'),
                                'inline': True
                            },
                            {
                                'name': 'Severity',
                                'value': alert.get('severity', 'Unknown').title(),
                                'inline': True
                            },
                            {
                                'name': 'Message',
                                'value': alert.get('message', 'No details provided'),
                                'inline': False
                            }
                        ],
                        'footer': {
                            'text': 'CI Health Monitor'
                        },
                        'timestamp': datetime.fromtimestamp(timestamp).isoformat()
                    }
                ]
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.config.discord_webhook,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status in [200, 204]:
                        return "Discord notification sent successfully"
                    else:
                        response_text = await response.text()
                        return f"Discord notification failed: HTTP {response.status} - {response_text}"
                        
        except Exception as e:
            return f"Discord notification error: {str(e)}"
    
    async def _send_email_notification(self, alert: Dict[str, Any]) -> str:
        """Send email notification"""
        try:
            if not all([self.config.email_smtp_server, self.config.email_username, 
                       self.config.email_password, self.config.email_recipients]):
                return "Email notification skipped: incomplete configuration"
            
            # Create email message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"CI Alert: {alert.get('type', 'Unknown').replace('_', ' ').title()}"
            msg['From'] = self.config.email_username
            msg['To'] = ', '.join(self.config.email_recipients)
            
            # Create text content
            timestamp = alert.get('timestamp', datetime.now().timestamp())
            formatted_time = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S UTC')
            
            text_content = f"""
CI Health Alert

Type: {alert.get('type', 'Unknown').replace('_', ' ').title()}
Component: {alert.get('component', 'Unknown')}
Severity: {alert.get('severity', 'Unknown').title()}
Time: {formatted_time}

Message:
{alert.get('message', 'No details provided')}

--
CI Health Monitoring System
"""
            
            # Create HTML content
            severity_color = {
                'critical': '#dc3545',
                'warning': '#ffc107',
                'info': '#17a2b8'
            }
            
            color = severity_color.get(alert.get('severity', 'info'), '#6c757d')
            
            html_content = f"""
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
        <h2 style="color: {color}; border-bottom: 2px solid {color}; padding-bottom: 10px;">
            CI Health Alert
        </h2>
        
        <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
            <tr>
                <td style="padding: 8px; font-weight: bold; width: 120px;">Type:</td>
                <td style="padding: 8px;">{alert.get('type', 'Unknown').replace('_', ' ').title()}</td>
            </tr>
            <tr style="background-color: #f8f9fa;">
                <td style="padding: 8px; font-weight: bold;">Component:</td>
                <td style="padding: 8px;">{alert.get('component', 'Unknown')}</td>
            </tr>
            <tr>
                <td style="padding: 8px; font-weight: bold;">Severity:</td>
                <td style="padding: 8px; color: {color}; font-weight: bold;">
                    {alert.get('severity', 'Unknown').title()}
                </td>
            </tr>
            <tr style="background-color: #f8f9fa;">
                <td style="padding: 8px; font-weight: bold;">Time:</td>
                <td style="padding: 8px;">{formatted_time}</td>
            </tr>
        </table>
        
        <div style="background-color: #f8f9fa; padding: 15px; border-left: 4px solid {color}; margin: 20px 0;">
            <h4 style="margin-top: 0;">Message:</h4>
            <p>{alert.get('message', 'No details provided')}</p>
        </div>
        
        <hr style="border: none; border-top: 1px solid #ddd; margin: 30px 0;">
        <p style="font-size: 12px; color: #666; text-align: center;">
            CI Health Monitoring System
        </p>
    </div>
</body>
</html>
"""
            
            # Attach parts
            msg.attach(MIMEText(text_content, 'plain'))
            msg.attach(MIMEText(html_content, 'html'))
            
            # Send email in background thread
            def send_email():
                with smtplib.SMTP(self.config.email_smtp_server, self.config.email_smtp_port) as server:
                    server.starttls()
                    server.login(self.config.email_username, self.config.email_password)
                    server.send_message(msg)
            
            await asyncio.to_thread(send_email)
            
            return f"Email notification sent to {len(self.config.email_recipients)} recipients"
            
        except Exception as e:
            return f"Email notification error: {str(e)}"
    
    async def _send_pagerduty_notification(self, alert: Dict[str, Any]) -> str:
        """Send PagerDuty notification"""
        try:
            import aiohttp
            
            # Map severity to PagerDuty severity
            severity_map = {
                'critical': 'critical',
                'warning': 'warning',
                'info': 'info'
            }
            
            payload = {
                'routing_key': self.config.pagerduty_routing_key,
                'event_action': 'trigger',
                'payload': {
                    'summary': f"CI Alert: {alert.get('type', 'Unknown').replace('_', ' ').title()}",
                    'source': alert.get('component', 'CI System'),
                    'severity': severity_map.get(alert.get('severity', 'info'), 'info'),
                    'component': alert.get('component', 'Unknown'),
                    'group': 'CI/CD Pipeline',
                    'class': 'CI Health',
                    'custom_details': {
                        'alert_type': alert.get('type', 'unknown'),
                        'message': alert.get('message', 'No details provided'),
                        'timestamp': alert.get('timestamp', datetime.now().timestamp())
                    }
                }
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    'https://events.pagerduty.com/v2/enqueue',
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 202:
                        response_data = await response.json()
                        return f"PagerDuty notification sent: {response_data.get('dedup_key', 'unknown')}"
                    else:
                        response_text = await response.text()
                        return f"PagerDuty notification failed: HTTP {response.status} - {response_text}"
                        
        except Exception as e:
            return f"PagerDuty notification error: {str(e)}"
    
    def _log_notification(self, alert: Dict[str, Any], results: List[str]):
        """Log notification attempt"""
        notification_record = {
            'timestamp': datetime.now().isoformat(),
            'alert': alert,
            'results': results,
            'success_count': len([r for r in results if 'successfully' in r or 'sent' in r])
        }
        
        self.notification_history.append(notification_record)
        
        # Keep only last 100 notifications
        if len(self.notification_history) > 100:
            self.notification_history = self.notification_history[-100:]
        
        logger.info(f"Notification sent for {alert.get('type', 'unknown')} alert. "
                   f"Results: {notification_record['success_count']}/{len(results)} successful")
    
    async def send_test_notification(self) -> List[str]:
        """Send test notification to all configured channels"""
        test_alert = {
            'type': 'test_notification',
            'component': 'notification_system',
            'severity': 'info',
            'message': 'This is a test notification to verify the notification system is working correctly.',
            'timestamp': datetime.now().timestamp()
        }
        
        results = await self.send_alert(test_alert)
        logger.info(f"Test notification completed. Results: {results}")
        return results
    
    def get_notification_history(self) -> List[Dict[str, Any]]:
        """Get recent notification history"""
        return self.notification_history.copy()
    
    def get_configuration_status(self) -> Dict[str, bool]:
        """Get status of notification channel configurations"""
        return {
            'webhook': bool(self.config.webhook_url),
            'slack': bool(self.config.slack_webhook),
            'discord': bool(self.config.discord_webhook),
            'email': bool(all([
                self.config.email_smtp_server,
                self.config.email_username,
                self.config.email_password,
                self.config.email_recipients
            ])),
            'pagerduty': bool(self.config.pagerduty_routing_key)
        }
    
    def get_rate_limit_metrics(self) -> Dict[str, Any]:
        """Get rate limiting metrics"""
        return self.rate_limiter.get_metrics()
    
    def get_queued_notifications(self, channel: Optional[str] = None) -> Dict[str, List[Dict[str, Any]]]:
        """Get queued notifications by channel"""
        if channel:
            return {channel: self.rate_limiter.get_queue_for_channel(channel)}
        else:
            # Get all channels
            channels = ['webhook', 'slack', 'discord', 'email', 'pagerduty']
            return {
                ch: self.rate_limiter.get_queue_for_channel(ch) 
                for ch in channels
            }
    
    async def process_queued_notifications(self) -> Dict[str, int]:
        """Manually trigger processing of queued notifications"""
        results = {}
        
        # Check each channel's queue
        for channel in ['webhook', 'slack', 'discord', 'email', 'pagerduty']:
            queue = self.rate_limiter.queues.get(channel, [])
            processed = 0
            
            while queue and await self.rate_limiter.check_rate_limit(channel):
                notification = queue.popleft()
                
                # Get the appropriate send function
                send_func = None
                if channel == 'webhook' and self.config.webhook_url:
                    send_func = self._send_webhook_notification
                elif channel == 'slack' and self.config.slack_webhook:
                    send_func = self._send_slack_notification
                elif channel == 'discord' and self.config.discord_webhook:
                    send_func = self._send_discord_notification
                elif channel == 'email' and self.config.email_recipients:
                    send_func = self._send_email_notification
                elif channel == 'pagerduty' and self.config.pagerduty_routing_key:
                    send_func = self._send_pagerduty_notification
                
                if send_func:
                    try:
                        await send_func(notification.alert)
                        processed += 1
                    except Exception as e:
                        logger.error(f"Failed to send queued {channel} notification: {str(e)}")
            
            results[channel] = processed
        
        return results