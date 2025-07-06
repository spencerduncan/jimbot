# CI Health Monitoring and Alerting System

This document describes the comprehensive CI health monitoring and alerting system implemented for JimBot. The system provides real-time visibility into CI pipeline health, automated alerting for failures, and historical metrics tracking.

## Overview

The CI monitoring system consists of several integrated components:

- **Health Monitoring**: Continuous monitoring of CI workflows and infrastructure
- **Alerting System**: Multi-channel notifications for critical issues
- **Dashboard**: Web-based visualization of CI health metrics
- **Metrics Storage**: Historical data tracking and analysis
- **Automated Workflows**: GitHub Actions integration for continuous monitoring

## Components

### 1. CI Health Monitor (`jimbot/infrastructure/monitoring/ci_health.py`)

The core monitoring system that:
- Monitors GitHub Actions workflows
- Checks GitHub API health and rate limits
- Assesses runner availability
- Validates CI dependencies (Docker, external services)
- Calculates success rates and performance metrics
- Generates alerts for critical issues

**Key Features:**
- Real-time health assessment
- Configurable thresholds for different health levels
- Dependency health checking
- Integration with existing health check infrastructure

### 2. Notification System (`jimbot/infrastructure/monitoring/notifications.py`)

Multi-channel notification system supporting:
- **Webhook notifications**: Generic HTTP webhooks
- **Slack integration**: Rich formatted messages with attachments
- **Discord integration**: Embedded messages with color coding
- **Email notifications**: HTML and text format emails
- **PagerDuty integration**: Critical alert escalation

**Configuration:**
Set environment variables to enable different notification channels:
```bash
# Webhook notifications
export CI_ALERT_WEBHOOK_URL="https://your-webhook-url.com"

# Slack notifications
export CI_ALERT_SLACK_WEBHOOK="https://hooks.slack.com/services/..."

# Discord notifications
export CI_ALERT_DISCORD_WEBHOOK="https://discord.com/api/webhooks/..."

# Email notifications
export CI_ALERT_EMAIL_SMTP_SERVER="smtp.gmail.com"
export CI_ALERT_EMAIL_SMTP_PORT="587"
export CI_ALERT_EMAIL_USERNAME="your-email@gmail.com"
export CI_ALERT_EMAIL_PASSWORD="your-app-password"
export CI_ALERT_EMAIL_RECIPIENTS="dev-team@example.com,ops@example.com"

# PagerDuty notifications
export CI_ALERT_PAGERDUTY_ROUTING_KEY="your-pagerduty-routing-key"
```

### 3. Dashboard System (`jimbot/infrastructure/monitoring/dashboard.py`)

Web-based dashboard providing:
- Real-time CI health status
- Workflow success rate visualization
- Active alerts display
- Historical trend analysis
- System health component status

**Features:**
- Responsive HTML interface
- Auto-refresh capability
- JSON API for external consumption
- Export capabilities

### 4. Metrics Storage (`jimbot/infrastructure/monitoring/metrics_storage.py`)

Persistent storage system for:
- Individual metric points
- Workflow performance history
- System health snapshots
- Historical trend analysis

**Database Schema:**
- `metric_points`: Individual measurements
- `workflow_metrics`: Workflow-specific metrics
- `system_health_snapshots`: Complete system state captures

### 5. Enhanced CI Monitor Script (`scripts/enhanced-ci-monitor.py`)

Command-line interface for:
- Running health checks
- Generating dashboards
- Testing notifications
- Continuous monitoring
- Data cleanup and maintenance

## Usage

### Basic Health Check

```bash
# Run a single health check
./scripts/enhanced-ci-monitor.py check

# Generate dashboard
./scripts/enhanced-ci-monitor.py dashboard

# Test notification system
./scripts/enhanced-ci-monitor.py test-notifications
```

### Continuous Monitoring

```bash
# Start continuous monitoring (default: 5-minute intervals)
./scripts/enhanced-ci-monitor.py monitor

# Custom monitoring interval
./scripts/enhanced-ci-monitor.py monitor --interval 10
```

### Data Management

```bash
# View database statistics
./scripts/enhanced-ci-monitor.py stats

# Clean up old data (default: 30 days retention)
./scripts/enhanced-ci-monitor.py cleanup --days 7
```

### Python API Usage

```python
from jimbot.infrastructure.monitoring import (
    CIHealthMonitor, CIDashboard, NotificationManager, MetricsStorage
)

# Initialize components
health_monitor = CIHealthMonitor()
dashboard = CIDashboard(health_monitor)
notification_manager = NotificationManager()
metrics_storage = MetricsStorage()

# Run health check
system_health = await health_monitor.get_system_health()

# Generate dashboard
dashboard_data = await dashboard.generate_dashboard_data()

# Send alert
if system_health.alerts:
    for alert in system_health.alerts:
        await notification_manager.send_alert(alert)
```

## GitHub Actions Integration

### Automated Health Monitoring (`.github/workflows/ci-health-check.yml`)

The CI health check workflow:
- Runs every hour automatically
- Can be triggered manually
- Uses the enhanced monitoring system
- Creates GitHub issues for critical problems
- Updates CI health badges

**Workflow Features:**
- Enhanced CI status reporting
- Automatic issue creation for critical failures
- Badge generation for README display
- Detailed health reports

### Health Check Badges

Add CI health badges to your README:

```markdown
![CI Health](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/your-org/your-repo/main/.github/badges/ci-health.json)
```

## Alert Configuration

### Health Thresholds

The system uses configurable thresholds:
- **Healthy**: ≥90% success rate
- **Degraded**: 70-89% success rate
- **Unhealthy**: 50-69% success rate
- **Critical**: <50% success rate

### Alert Types

1. **Workflow Critical**: Workflow success rate below critical threshold
2. **Workflow Unhealthy**: Workflow success rate below healthy threshold
3. **Health Check Failure**: Infrastructure health check failures
4. **GitHub API Issues**: Rate limiting or connectivity problems
5. **Runner Availability**: GitHub Actions runner shortage

### Alert Cooldowns

Alerts have configurable cooldown periods (default: 1 hour) to prevent spam while ensuring critical issues are escalated.

## Dashboard Features

### Real-time Status Cards

- Overall system health status
- Success rate percentage
- Active workflow count
- Alert count with timestamp

### Workflow Status List

- Individual workflow health status
- Success rates and recent performance
- Color-coded status indicators
- Last run timestamps

### Alert Management

- Active alerts with severity levels
- Alert timestamps and aging
- Detailed alert descriptions
- Component-specific information

### Auto-refresh

The dashboard automatically refreshes every 5 minutes to provide up-to-date information.

## Testing

Run the comprehensive test suite:

```bash
# Run all tests
pytest tests/test_ci_monitoring.py -v

# Run specific test categories
pytest tests/test_ci_monitoring.py::TestCIHealthMonitor -v
pytest tests/test_ci_monitoring.py::TestNotificationManager -v
pytest tests/test_ci_monitoring.py::TestMetricsStorage -v
pytest tests/test_ci_monitoring.py::TestCIDashboard -v

# Run integration tests
pytest tests/test_ci_monitoring.py::TestIntegration -v
```

### Test Coverage

The test suite covers:
- Health monitoring functionality
- Notification system behavior
- Metrics storage operations
- Dashboard generation
- Integration workflows
- Error handling and recovery

## Configuration Examples

### Environment Configuration

Create a `.env` file or set environment variables:

```bash
# Basic configuration
CI_ALERT_WEBHOOK_URL=https://your-webhook.com/ci-alerts
CI_ALERT_SLACK_WEBHOOK=https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK

# Email configuration for Gmail
CI_ALERT_EMAIL_SMTP_SERVER=smtp.gmail.com
CI_ALERT_EMAIL_SMTP_PORT=587
CI_ALERT_EMAIL_USERNAME=your-email@gmail.com
CI_ALERT_EMAIL_PASSWORD=your-app-password
CI_ALERT_EMAIL_RECIPIENTS=team@example.com

# Advanced configuration
CI_HEALTH_CHECK_INTERVAL=300  # 5 minutes
CI_METRICS_RETENTION_DAYS=30
CI_ALERT_COOLDOWN_HOURS=1
```

### Slack Webhook Setup

1. Create a Slack app in your workspace
2. Add an Incoming Webhook to your app
3. Copy the webhook URL
4. Set the `CI_ALERT_SLACK_WEBHOOK` environment variable

### Discord Webhook Setup

1. Go to your Discord server settings
2. Navigate to Integrations → Webhooks
3. Create a new webhook
4. Copy the webhook URL
5. Set the `CI_ALERT_DISCORD_WEBHOOK` environment variable

## Monitoring Best Practices

### 1. Regular Health Checks

- Set up automated hourly health checks
- Monitor during peak usage periods
- Track trends over time

### 2. Alert Configuration

- Configure multiple notification channels for redundancy
- Set appropriate alert thresholds for your team
- Use alert cooldowns to prevent notification fatigue

### 3. Dashboard Usage

- Bookmark the dashboard for quick access
- Review trends regularly to identify patterns
- Use the JSON API for custom integrations

### 4. Data Maintenance

- Regularly clean up old metrics data
- Monitor database size and performance
- Back up important historical data

### 5. Testing and Validation

- Test notification channels regularly
- Validate alert thresholds with your team
- Run integration tests in CI/CD pipeline

## Troubleshooting

### Common Issues

**GitHub API Rate Limiting:**
- Check API rate limit status in health checks
- Implement API key rotation if needed
- Monitor usage patterns

**Notification Failures:**
- Verify webhook URLs and credentials
- Check network connectivity
- Review notification logs

**Database Issues:**
- Check disk space for SQLite database
- Verify database permissions
- Monitor database size growth

**Dashboard Not Loading:**
- Check for Python dependency issues
- Verify file permissions
- Review error logs

### Debug Mode

Enable verbose logging for troubleshooting:

```bash
./scripts/enhanced-ci-monitor.py check --verbose
```

### Health Check Validation

Verify system components manually:

```bash
# Check GitHub CLI connectivity
gh auth status

# Test GitHub API access
gh api rate_limit

# Verify Python dependencies
python -c "import aiohttp, asyncio; print('Dependencies OK')"
```

## Integration Examples

### Custom Webhook Handler

```python
from flask import Flask, request
import json

app = Flask(__name__)

@app.route('/ci-webhook', methods=['POST'])
def handle_ci_alert():
    alert_data = request.json
    
    # Process alert
    print(f"Received CI alert: {alert_data['alert']['type']}")
    
    # Custom logic here
    if alert_data['alert']['severity'] == 'critical':
        # Escalate to on-call team
        escalate_alert(alert_data)
    
    return {'status': 'received'}, 200
```

### Custom Dashboard Integration

```javascript
// Fetch CI health data
fetch('/ci-dashboard.json')
    .then(response => response.json())
    .then(data => {
        updateHealthStatus(data.system_health.overall_status);
        updateWorkflowList(data.system_health.workflow_health);
        updateAlerts(data.alerts);
    });
```

## Future Enhancements

Planned improvements include:
- Advanced trend analysis and prediction
- Integration with more monitoring tools
- Custom metric collection capabilities
- Advanced alerting rules engine
- Performance optimization features
- Enhanced dashboard customization

## Support

For questions or issues with the CI monitoring system:

1. Check this documentation
2. Review the test suite for examples
3. Check GitHub Issues for known problems
4. Create a new issue with detailed information

## Contributing

When contributing to the CI monitoring system:

1. Add tests for new functionality
2. Update documentation for changes
3. Follow existing code patterns
4. Test with multiple notification channels
5. Validate dashboard changes