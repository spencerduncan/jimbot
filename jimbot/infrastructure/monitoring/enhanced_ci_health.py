"""Enhanced CI Health Monitoring with Rate Limited Notifications

This module extends the CI health monitoring system to use the rate-limited
notification system.
"""

import logging
from typing import Optional, List, Dict, Any

from .ci_health import CIHealthMonitor
from .notifications import NotificationManager
from .rate_limiter import RateLimiter, RateLimitConfig

logger = logging.getLogger(__name__)


class EnhancedCIHealthMonitor:
    """CI Health Monitor with integrated rate-limited notifications
    
    This class uses composition to combine CI health monitoring with rate-limited
    notifications, rather than inheriting from CIHealthMonitor.
    """
    
    def __init__(self, 
                 metrics_collector=None,
                 health_checker=None,
                 notification_manager: Optional[NotificationManager] = None,
                 rate_limit_config: Optional[RateLimitConfig] = None):
        """
        Initialize enhanced CI health monitor
        
        Args:
            metrics_collector: Metrics collection system
            health_checker: Health checking system
            notification_manager: Optional pre-configured notification manager
            rate_limit_config: Optional rate limiting configuration
        """
        # Compose with CIHealthMonitor instead of inheriting
        self.health_monitor = CIHealthMonitor(metrics_collector, health_checker)
        
        # Set up notification manager with rate limiting
        if notification_manager:
            self.notification_manager = notification_manager
        else:
            rate_limiter = RateLimiter(rate_limit_config)
            self.notification_manager = NotificationManager(rate_limiter=rate_limiter)
        
        self._notification_started = False
        
        # Configure the health monitor to use our alert processing
        self._setup_alert_routing()
    
    def _setup_alert_routing(self):
        """Configure the health monitor to route alerts through our notification system"""
        # Store the original alert handler if there is one
        if hasattr(self.health_monitor, 'alert_handler'):
            self._original_alert_handler = self.health_monitor.alert_handler
        
        # Set our process_alert as the alert handler
        if hasattr(self.health_monitor, 'set_alert_handler'):
            self.health_monitor.set_alert_handler(self.process_alert)
        elif hasattr(self.health_monitor, 'alert_handler'):
            self.health_monitor.alert_handler = self.process_alert
    
    async def start_monitoring(self):
        """Start monitoring with notification system"""
        # Start notification manager
        if not self._notification_started:
            await self.notification_manager.start()
            self._notification_started = True
            logger.info("Started enhanced CI monitoring with rate limiting")
        
        # Start the underlying health monitor
        await self.health_monitor.start_monitoring()
    
    async def stop_monitoring(self):
        """Stop monitoring and cleanup"""
        # Stop notification manager
        if self._notification_started:
            await self.notification_manager.stop()
            self._notification_started = False
        
        # Stop the underlying health monitor
        await self.health_monitor.stop_monitoring()
        
        logger.info("Stopped enhanced CI monitoring")
    
    async def process_alert(self, alert: Dict[str, Any]):
        """Override to use rate-limited notification manager"""
        try:
            # Send through notification manager (handles rate limiting)
            results = await self.notification_manager.send_alert(alert)
            
            # Log results
            logger.info(f"Alert notification results: {results}")
            
            # Track metrics
            for result in results:
                if "queued" in result:
                    self.health_monitor.metrics_collector.increment_counter("ci_alerts_queued")
                elif "dropped" in result:
                    self.health_monitor.metrics_collector.increment_counter("ci_alerts_dropped")
                elif "failed" in result:
                    self.health_monitor.metrics_collector.increment_counter("ci_alerts_failed")
                else:
                    self.health_monitor.metrics_collector.increment_counter("ci_alerts_sent")
                    
        except Exception as e:
            logger.error(f"Failed to process alert notification: {str(e)}")
            self.health_monitor.metrics_collector.increment_counter("ci_alerts_error")
    
    def get_notification_metrics(self) -> Dict[str, Any]:
        """Get notification system metrics"""
        return {
            'rate_limits': self.notification_manager.get_rate_limit_metrics(),
            'queued_notifications': self.notification_manager.get_queued_notifications(),
            'notification_history': self.notification_manager.get_notification_history()[-10:]  # Last 10
        }
    
    # Delegate common methods to the underlying health monitor
    async def check_health(self) -> Dict[str, Any]:
        """Delegate health check to underlying monitor"""
        return await self.health_monitor.check_health()
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get all metrics including notification metrics"""
        base_metrics = self.health_monitor.get_metrics()
        base_metrics['notifications'] = self.get_notification_metrics()
        return base_metrics
    
    async def monitor_workflow(self, workflow_id: str, repo: str):
        """Delegate workflow monitoring to underlying monitor"""
        return await self.health_monitor.monitor_workflow(workflow_id, repo)
    
    async def check_workflow_health(self, workflow_id: str, repo: str) -> Dict[str, Any]:
        """Delegate workflow health check to underlying monitor"""
        return await self.health_monitor.check_workflow_health(workflow_id, repo)
    
    async def process_notification_queue(self) -> Dict[str, int]:
        """Manually process queued notifications"""
        return await self.notification_manager.process_queued_notifications()
    
    def get_rate_limit_config(self) -> Dict[str, Any]:
        """Get current rate limit configuration"""
        metrics = self.notification_manager.get_rate_limit_metrics()
        return metrics.get('config', {})