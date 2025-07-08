#!/usr/bin/env python3
"""
Enhanced CI Health Monitor

Comprehensive CI health monitoring system that integrates all monitoring
components: health checks, metrics storage, alerting, and dashboard generation.
"""

import asyncio
import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

# Add jimbot to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from jimbot.infrastructure.monitoring import (
    CIHealthMonitor, CIDashboard, NotificationManager, NotificationConfig,
    MetricsStorage, MetricPoint, WorkflowMetrics, SystemHealthSnapshot
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class EnhancedCIMonitor:
    """Enhanced CI monitoring system with comprehensive capabilities"""
    
    def __init__(self, storage_path: str = "ci_metrics.db"):
        self.health_monitor = CIHealthMonitor()
        self.metrics_storage = MetricsStorage(storage_path)
        self.notification_manager = NotificationManager()
        self.dashboard = CIDashboard(self.health_monitor)
        
    async def run_health_check(self) -> dict:
        """Run comprehensive health check and store results"""
        try:
            logger.info("Running comprehensive CI health check...")
            
            # Get system health
            system_health = await self.health_monitor.get_system_health()
            
            # Store system health snapshot
            await self._store_health_snapshot(system_health)
            
            # Handle alerts if any
            if system_health.alerts:
                await self._handle_alerts(system_health.alerts)
            
            # Generate summary
            summary = {
                'timestamp': system_health.timestamp.isoformat(),
                'overall_status': system_health.overall_status.value,
                'success_rate': system_health.system_metrics.get('overall_success_rate', 0),
                'healthy_checks': system_health.system_metrics.get('healthy_checks', 0),
                'total_checks': system_health.system_metrics.get('total_checks', 0),
                'active_alerts': len(system_health.alerts),
                'workflows': len(system_health.workflow_health)
            }
            
            logger.info(f"Health check completed: {summary}")
            return summary
            
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            raise
    
    async def _store_health_snapshot(self, system_health):
        """Store system health snapshot in metrics storage"""
        try:
            # Convert workflow health to storage format
            workflow_metrics = []
            for workflow_name, health in system_health.workflow_health.items():
                workflow_metrics.append(WorkflowMetrics(
                    timestamp=health.timestamp,
                    workflow_name=workflow_name,
                    success_rate=health.success_rate,
                    avg_duration=health.avg_duration,
                    total_runs=health.metrics.get('total_runs', 0),
                    successful_runs=health.metrics.get('successful_runs', 0),
                    failed_runs=health.metrics.get('failed_runs', 0),
                    status=health.status.value
                ))
            
            # Create system health snapshot
            snapshot = SystemHealthSnapshot(
                timestamp=system_health.timestamp,
                overall_status=system_health.overall_status.value,
                overall_success_rate=system_health.system_metrics.get('overall_success_rate', 0),
                healthy_checks=system_health.system_metrics.get('healthy_checks', 0),
                total_checks=system_health.system_metrics.get('total_checks', 0),
                active_alerts=len(system_health.alerts),
                workflow_metrics=workflow_metrics
            )
            
            # Store in database
            await self.metrics_storage.store_system_health_snapshot(snapshot)
            logger.info("Health snapshot stored successfully")
            
        except Exception as e:
            logger.error(f"Failed to store health snapshot: {str(e)}")
    
    async def _handle_alerts(self, alerts: list):
        """Handle system alerts through notification system"""
        try:
            for alert in alerts:
                results = await self.notification_manager.send_alert(alert)
                logger.info(f"Alert notifications sent: {results}")
                
        except Exception as e:
            logger.error(f"Failed to handle alerts: {str(e)}")
    
    async def generate_dashboard(self, output_path: str = "ci-dashboard.html"):
        """Generate HTML dashboard"""
        try:
            logger.info("Generating CI dashboard...")
            
            await self.dashboard.save_dashboard_html(output_path)
            logger.info(f"Dashboard generated: {output_path}")
            
            # Also generate JSON data
            json_data = await self.dashboard.generate_json_data()
            json_path = output_path.replace('.html', '.json')
            
            with open(json_path, 'w') as f:
                f.write(json_data)
            
            logger.info(f"Dashboard JSON data: {json_path}")
            
        except Exception as e:
            logger.error(f"Failed to generate dashboard: {str(e)}")
            raise
    
    async def test_notifications(self):
        """Test notification system"""
        try:
            logger.info("Testing notification system...")
            
            results = await self.notification_manager.send_test_notification()
            
            config_status = self.notification_manager.get_configuration_status()
            logger.info(f"Notification channels configured: {config_status}")
            
            return results
            
        except Exception as e:
            logger.error(f"Notification test failed: {str(e)}")
            raise
    
    async def cleanup_old_data(self, retention_days: int = 30):
        """Clean up old metrics data"""
        try:
            logger.info(f"Cleaning up data older than {retention_days} days...")
            
            deleted_counts = await self.metrics_storage.cleanup_old_data(retention_days)
            logger.info(f"Cleanup completed: {deleted_counts}")
            
            return deleted_counts
            
        except Exception as e:
            logger.error(f"Data cleanup failed: {str(e)}")
            raise
    
    async def get_database_stats(self):
        """Get database statistics"""
        try:
            stats = await self.metrics_storage.get_database_stats()
            logger.info(f"Database stats: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get database stats: {str(e)}")
            return {}
    
    async def start_continuous_monitoring(self, interval_minutes: int = 5):
        """Start continuous monitoring loop"""
        try:
            logger.info(f"Starting continuous monitoring (interval: {interval_minutes} minutes)")
            
            while True:
                try:
                    # Run health check
                    await self.run_health_check()
                    
                    # Generate dashboard
                    await self.generate_dashboard()
                    
                    # Wait for next check
                    await asyncio.sleep(interval_minutes * 60)
                    
                except KeyboardInterrupt:
                    logger.info("Monitoring stopped by user")
                    break
                except Exception as e:
                    logger.error(f"Error in monitoring loop: {str(e)}")
                    await asyncio.sleep(60)  # Wait 1 minute before retrying
                    
        except Exception as e:
            logger.error(f"Continuous monitoring failed: {str(e)}")
            raise


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Enhanced CI Health Monitoring System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s check                    # Run single health check
  %(prog)s dashboard               # Generate dashboard
  %(prog)s monitor --interval 10   # Start continuous monitoring
  %(prog)s test-notifications      # Test notification system
  %(prog)s cleanup --days 7        # Clean up data older than 7 days
  %(prog)s stats                   # Show database statistics
        """
    )
    
    parser.add_argument('command', choices=[
        'check', 'dashboard', 'monitor', 'test-notifications', 'cleanup', 'stats'
    ], help='Command to execute')
    
    parser.add_argument('--output', '-o', default='ci-dashboard.html',
                       help='Output path for dashboard (default: ci-dashboard.html)')
    
    parser.add_argument('--interval', '-i', type=int, default=5,
                       help='Monitoring interval in minutes (default: 5)')
    
    parser.add_argument('--days', '-d', type=int, default=30,
                       help='Retention period in days for cleanup (default: 30)')
    
    parser.add_argument('--storage', '-s', default='ci_metrics.db',
                       help='Database path for metrics storage (default: ci_metrics.db)')
    
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Initialize monitor
    monitor = EnhancedCIMonitor(args.storage)
    
    try:
        if args.command == 'check':
            summary = await monitor.run_health_check()
            print(f"\\nCI Health Summary:")
            print(f"Status: {summary['overall_status'].upper()}")
            print(f"Success Rate: {summary['success_rate']:.1f}%")
            print(f"Health Checks: {summary['healthy_checks']}/{summary['total_checks']}")
            print(f"Active Alerts: {summary['active_alerts']}")
            print(f"Workflows: {summary['workflows']}")
            
        elif args.command == 'dashboard':
            await monitor.generate_dashboard(args.output)
            print(f"Dashboard generated: {args.output}")
            
        elif args.command == 'monitor':
            await monitor.start_continuous_monitoring(args.interval)
            
        elif args.command == 'test-notifications':
            results = await monitor.test_notifications()
            print("Notification test results:")
            for result in results:
                print(f"  - {result}")
                
        elif args.command == 'cleanup':
            deleted_counts = await monitor.cleanup_old_data(args.days)
            print(f"Cleaned up {sum(deleted_counts)} records older than {args.days} days")
            
        elif args.command == 'stats':
            stats = await monitor.get_database_stats()
            print("Database Statistics:")
            print(f"  Metric Points: {stats.get('metric_points_count', 0)}")
            print(f"  Workflow Metrics: {stats.get('workflow_metrics_count', 0)}")
            print(f"  Health Snapshots: {stats.get('snapshots_count', 0)}")
            print(f"  Database Size: {stats.get('database_size_mb', 0):.2f} MB")
            
    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
    except Exception as e:
        logger.error(f"Operation failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())