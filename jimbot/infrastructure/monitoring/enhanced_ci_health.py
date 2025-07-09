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


class EnhancedCIHealthMonitor(CIHealthMonitor):
    """CI Health Monitor with integrated rate-limited notifications"""
    
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
        super().__init__(metrics_collector, health_checker)
        
        # Set up notification manager with rate limiting
        if notification_manager:
            self.notification_manager = notification_manager
        else:
            rate_limiter = RateLimiter(rate_limit_config)
            self.notification_manager = NotificationManager(rate_limiter=rate_limiter)
        
        self._notification_started = False
    
    async def start_monitoring(self):
        """Start monitoring with notification system"""
        # Start notification manager
        if not self._notification_started:
            await self.notification_manager.start()
            self._notification_started = True
            logger.info("Started enhanced CI monitoring with rate limiting")
        
        # Call parent start_monitoring
        await super().start_monitoring()
    
    async def stop_monitoring(self):
        """Stop monitoring and cleanup"""
        # Stop notification manager
        if self._notification_started:
            await self.notification_manager.stop()
            self._notification_started = False
        
        logger.info("Stopped enhanced CI monitoring")
    
    async def _process_alert_notification(self, alert: Dict[str, Any]):
        """Override to use rate-limited notification manager"""
        try:
            # Send through notification manager (handles rate limiting)
            results = await self.notification_manager.send_alert(alert)
            
            # Log results
            logger.info(f"Alert notification results: {results}")
            
            # Track metrics
            for result in results:
                if "queued" in result:
                    self.metrics_collector.increment_counter("ci_alerts_queued")
                elif "dropped" in result:
                    self.metrics_collector.increment_counter("ci_alerts_dropped")
                elif "failed" in result:
                    self.metrics_collector.increment_counter("ci_alerts_failed")
                else:
                    self.metrics_collector.increment_counter("ci_alerts_sent")
                    
        except Exception as e:
            logger.error(f"Failed to process alert notification: {str(e)}")
            self.metrics_collector.increment_counter("ci_alerts_error")
    
    def get_notification_metrics(self) -> Dict[str, Any]:
        """Get notification system metrics"""
        return {
            'rate_limits': self.notification_manager.get_rate_limit_metrics(),
            'queued_notifications': self.notification_manager.get_queued_notifications(),
            'notification_history': self.notification_manager.get_notification_history()[-10:]  # Last 10
        }
    
    async def process_notification_queue(self) -> Dict[str, int]:
        """Manually process queued notifications"""
        return await self.notification_manager.process_queued_notifications()
    
    def get_rate_limit_config(self) -> Dict[str, Any]:
        """Get current rate limit configuration"""
        metrics = self.notification_manager.get_rate_limit_metrics()
        return metrics.get('config', {})