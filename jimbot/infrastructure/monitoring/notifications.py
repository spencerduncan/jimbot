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
    
    def __init__(self, config: Optional[NotificationConfig] = None):
        self.config = config or NotificationConfig.from_environment()
        self.notification_history = []
        
    async def send_alert(self, alert: Dict[str, Any]) -> List[str]:
        """Send alert through all configured channels"""
        results = []
        
        try:
            # Send through various channels in parallel
            tasks = []
            
            if self.config.webhook_url:
                tasks.append(self._send_webhook_notification(alert))
            
            if self.config.slack_webhook:
                tasks.append(self._send_slack_notification(alert))
            
            if self.config.discord_webhook:
                tasks.append(self._send_discord_notification(alert))
            
            if self.config.email_recipients:
                tasks.append(self._send_email_notification(alert))
            
            if self.config.pagerduty_routing_key:
                tasks.append(self._send_pagerduty_notification(alert))
            
            # Execute all notifications
            if tasks:
                notification_results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for i, result in enumerate(notification_results):
                    if isinstance(result, Exception):
                        results.append(f"Channel {i} failed: {str(result)}")
                    else:
                        results.append(result)
            else:
                results.append("No notification channels configured")
            
            # Log notification attempt
            self._log_notification(alert, results)
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to send alert notifications: {str(e)}")
            return [f"Notification system error: {str(e)}"]
    
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