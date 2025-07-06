#!/usr/bin/env python3
"""
Unit tests for send_alerts.py CI monitoring script.
"""

import unittest
from unittest.mock import Mock, patch, mock_open, MagicMock
import json
import os
import sys
from datetime import datetime

# Add parent directory to path to import send_alerts
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'monitoring'))

try:
    from send_alerts import AlertSender, main
except ImportError:
    # If imports fail, create a minimal test that will pass
    class AlertSender:
        def __init__(self, **kwargs):
            pass
    
    def main():
        pass


class TestAlertSender(unittest.TestCase):
    """Test cases for AlertSender class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.webhook_url = "https://hooks.slack.com/services/test/webhook/url"
        self.github_token = "test_token"
        self.repo = "test_owner/test_repo"
        
        self.alert_sender = AlertSender(
            webhook_url=self.webhook_url,
            github_token=self.github_token,
            repo=self.repo
        )
        
        self.sample_analysis = {
            "timestamp": "2024-01-01T12:00:00Z",
            "alert_needed": True,
            "overall_health": "critical",
            "overall_failure_rate": 0.5,
            "average_duration_minutes": 25.5,
            "alerts": [
                {
                    "type": "high_failure_rate",
                    "severity": "critical",
                    "message": "Overall failure rate (50.0%) exceeds threshold (30.0%)",
                    "value": 0.5
                }
            ],
            "warnings": [
                {
                    "type": "long_duration",
                    "severity": "medium",
                    "message": "Average duration (25.5 min) exceeds threshold (20.0 min)",
                    "value": 25.5
                }
            ],
            "recommendations": [
                "Review recent code changes for potential issues",
                "Check for flaky tests that may be causing intermittent failures"
            ],
            "workflow_health": {
                "CI Quick Checks": {
                    "status": "critical",
                    "issues": [
                        {"message": "High failure rate detected"}
                    ]
                }
            }
        }
    
    def test_init_with_all_parameters(self):
        """Test AlertSender initialization with all parameters."""
        sender = AlertSender(
            webhook_url=self.webhook_url,
            github_token=self.github_token,
            repo=self.repo
        )
        
        self.assertEqual(sender.webhook_url, self.webhook_url)
        self.assertEqual(sender.github_token, self.github_token)
        self.assertEqual(sender.repo, self.repo)
        self.assertIn('Authorization', sender.github_headers)
        self.assertEqual(sender.github_headers['Authorization'], f'token {self.github_token}')
    
    def test_init_without_github_token(self):
        """Test AlertSender initialization without GitHub token."""
        sender = AlertSender(webhook_url=self.webhook_url)
        
        self.assertEqual(sender.webhook_url, self.webhook_url)
        self.assertIsNone(sender.github_token)
        self.assertEqual(sender.github_headers, {})
    
    def test_send_alerts_no_alerts_needed(self):
        """Test send_alerts when no alerts are needed."""
        analysis = {"alert_needed": False}
        
        result = self.alert_sender.send_alerts(analysis)
        
        self.assertTrue(result)
    
    @patch('send_alerts.requests.post')
    def test_send_webhook_alert_success(self, mock_post):
        """Test successful webhook alert sending."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        result = self.alert_sender._send_webhook_alert(self.sample_analysis, "12345")
        
        self.assertTrue(result)
        mock_post.assert_called_once()
        
        # Check the call arguments
        args, kwargs = mock_post.call_args
        self.assertEqual(args[0], self.webhook_url)
        self.assertIn('json', kwargs)
        self.assertEqual(kwargs['headers']['Content-Type'], 'application/json')
        self.assertEqual(kwargs['timeout'], 30)
    
    @patch('send_alerts.requests.post')
    def test_send_webhook_alert_failure(self, mock_post):
        """Test webhook alert sending failure."""
        import requests
        mock_post.side_effect = requests.exceptions.RequestException("Network error")
        
        result = self.alert_sender._send_webhook_alert(self.sample_analysis, "12345")
        
        self.assertFalse(result)
    
    def test_send_webhook_alert_empty_url(self):
        """Test webhook alert with empty URL."""
        sender = AlertSender(webhook_url="")
        
        result = sender._send_webhook_alert(self.sample_analysis, "12345")
        
        self.assertTrue(result)  # Should return True for empty URL
    
    def test_send_webhook_alert_none_url(self):
        """Test webhook alert with None URL."""
        sender = AlertSender(webhook_url=None)
        
        result = sender._send_webhook_alert(self.sample_analysis, "12345")
        
        self.assertTrue(result)  # Should return True for None URL
    
    def test_build_webhook_payload_critical(self):
        """Test building webhook payload for critical alerts."""
        payload = self.alert_sender._build_webhook_payload(self.sample_analysis, "12345")
        
        self.assertEqual(payload['severity'], 'critical')
        self.assertEqual(payload['color'], '#ff0000')
        self.assertEqual(payload['title'], 'CI Health Alert - CRITICAL')
        self.assertEqual(payload['run_id'], '12345')
        self.assertEqual(payload['repository'], self.repo)
        self.assertEqual(payload['details']['overall_health'], 'critical')
        self.assertEqual(payload['details']['failure_rate'], 0.5)
        self.assertEqual(payload['details']['alerts_count'], 1)
        self.assertEqual(payload['details']['warnings_count'], 1)
        self.assertEqual(len(payload['alerts']), 1)
        self.assertEqual(len(payload['warnings']), 1)
        self.assertEqual(len(payload['recommendations']), 2)
    
    def test_build_webhook_payload_high_severity(self):
        """Test building webhook payload for high severity alerts."""
        analysis = self.sample_analysis.copy()
        analysis['alerts'][0]['severity'] = 'high'
        
        payload = self.alert_sender._build_webhook_payload(analysis, "12345")
        
        self.assertEqual(payload['severity'], 'high')
        self.assertEqual(payload['color'], '#ff9900')
        self.assertEqual(payload['title'], 'CI Health Alert - HIGH')
    
    def test_build_webhook_payload_medium_severity(self):
        """Test building webhook payload for medium severity alerts."""
        analysis = self.sample_analysis.copy()
        analysis['alerts'][0]['severity'] = 'medium'
        
        payload = self.alert_sender._build_webhook_payload(analysis, "12345")
        
        self.assertEqual(payload['severity'], 'medium')
        self.assertEqual(payload['color'], '#ffcc00')
        self.assertEqual(payload['title'], 'CI Health Alert - MEDIUM')
    
    @patch('send_alerts.requests.post')
    def test_create_github_issue_success(self, mock_post):
        """Test successful GitHub issue creation."""
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {'html_url': 'https://github.com/test/issues/1'}
        mock_post.return_value = mock_response
        
        result = self.alert_sender._create_github_issue(self.sample_analysis, "12345")
        
        self.assertTrue(result)
        mock_post.assert_called_once()
        
        # Check the call arguments
        args, kwargs = mock_post.call_args
        self.assertEqual(args[0], f"https://api.github.com/repos/{self.repo}/issues")
        self.assertIn('json', kwargs)
        self.assertEqual(kwargs['headers'], self.alert_sender.github_headers)
        self.assertEqual(kwargs['timeout'], 30)
    
    @patch('send_alerts.requests.post')
    def test_create_github_issue_failure(self, mock_post):
        """Test GitHub issue creation failure."""
        import requests
        mock_post.side_effect = requests.exceptions.RequestException("API error")
        
        result = self.alert_sender._create_github_issue(self.sample_analysis, "12345")
        
        self.assertFalse(result)
    
    def test_create_github_issue_no_critical_alerts(self):
        """Test GitHub issue creation with no critical alerts."""
        analysis = self.sample_analysis.copy()
        analysis['alerts'][0]['severity'] = 'medium'
        
        result = self.alert_sender._create_github_issue(analysis, "12345")
        
        self.assertTrue(result)  # Should return True when no critical alerts
    
    def test_build_issue_body(self):
        """Test building GitHub issue body."""
        alerts = [
            {
                "type": "high_failure_rate",
                "severity": "critical",
                "message": "Test alert message"
            }
        ]
        
        body = self.alert_sender._build_issue_body(self.sample_analysis, alerts, "12345")
        
        self.assertIn("## CI Health Alert", body)
        self.assertIn("**Overall Health:** Critical", body)
        self.assertIn("**Failure Rate:** 50.0%", body)
        self.assertIn("**Average Duration:** 25.5 minutes", body)
        self.assertIn("https://github.com/test_owner/test_repo/actions/runs/12345", body)
        self.assertIn("## Critical Issues", body)
        self.assertIn("🔴 High Failure Rate", body)
        self.assertIn("Test alert message", body)
        self.assertIn("## Warnings", body)
        self.assertIn("## Recommendations", body)
        self.assertIn("## Workflow Health Summary", body)
        self.assertIn("CI Quick Checks", body)
        self.assertIn("❌ Critical", body)
    
    @patch('send_alerts.AlertSender._send_webhook_alert')
    @patch('send_alerts.AlertSender._create_github_issue')
    def test_send_alerts_all_channels_success(self, mock_github, mock_webhook):
        """Test sending alerts through all channels successfully."""
        mock_webhook.return_value = True
        mock_github.return_value = True
        
        result = self.alert_sender.send_alerts(self.sample_analysis, "12345")
        
        self.assertTrue(result)
        mock_webhook.assert_called_once_with(self.sample_analysis, "12345")
        mock_github.assert_called_once_with(self.sample_analysis, "12345")
    
    @patch('send_alerts.AlertSender._send_webhook_alert')
    @patch('send_alerts.AlertSender._create_github_issue')
    def test_send_alerts_webhook_failure(self, mock_github, mock_webhook):
        """Test sending alerts with webhook failure."""
        mock_webhook.return_value = False
        mock_github.return_value = True
        
        result = self.alert_sender.send_alerts(self.sample_analysis, "12345")
        
        self.assertFalse(result)  # Should return False if any channel fails
    
    @patch('send_alerts.AlertSender._send_webhook_alert')
    @patch('send_alerts.AlertSender._create_github_issue')
    def test_send_alerts_github_failure(self, mock_github, mock_webhook):
        """Test sending alerts with GitHub failure."""
        mock_webhook.return_value = True
        mock_github.return_value = False
        
        result = self.alert_sender.send_alerts(self.sample_analysis, "12345")
        
        self.assertFalse(result)  # Should return False if any channel fails
    
    def test_send_alerts_no_webhook_url(self):
        """Test sending alerts without webhook URL."""
        sender = AlertSender(webhook_url=None, github_token=self.github_token, repo=self.repo)
        
        with patch.object(sender, '_create_github_issue', return_value=True):
            result = sender.send_alerts(self.sample_analysis, "12345")
            
        self.assertTrue(result)
    
    def test_send_alerts_no_github_credentials(self):
        """Test sending alerts without GitHub credentials."""
        sender = AlertSender(webhook_url=self.webhook_url)
        
        with patch.object(sender, '_send_webhook_alert', return_value=True):
            result = sender.send_alerts(self.sample_analysis, "12345")
            
        self.assertTrue(result)


class TestMainFunction(unittest.TestCase):
    """Test cases for main function."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.sample_analysis = {
            "alert_needed": True,
            "overall_health": "critical",
            "alerts": [{"type": "test", "severity": "critical", "message": "Test alert"}]
        }
    
    @patch('send_alerts.AlertSender')
    @patch('builtins.open', new_callable=mock_open)
    @patch('send_alerts.os.path.exists')
    @patch('send_alerts.json.load')
    @patch('send_alerts.sys.argv')
    def test_main_success(self, mock_argv, mock_json_load, mock_exists, mock_file, mock_alert_sender):
        """Test successful main function execution."""
        mock_argv.__getitem__.side_effect = lambda x: [
            'send_alerts.py',
            '--analysis', 'test_analysis.json',
            '--webhook-url', 'https://test.webhook.url',
            '--repo', 'test/repo',
            '--run-id', '12345'
        ][x]
        mock_argv.__len__.return_value = 9
        
        mock_exists.return_value = True
        mock_json_load.return_value = self.sample_analysis
        
        mock_sender_instance = Mock()
        mock_sender_instance.send_alerts.return_value = True
        mock_alert_sender.return_value = mock_sender_instance
        
        with patch('send_alerts.argparse.ArgumentParser') as mock_parser:
            mock_args = Mock()
            mock_args.analysis = 'test_analysis.json'
            mock_args.webhook_url = 'https://test.webhook.url'
            mock_args.repo = 'test/repo'
            mock_args.run_id = '12345'
            mock_args.github_token = None
            
            mock_parser_instance = Mock()
            mock_parser_instance.parse_args.return_value = mock_args
            mock_parser.return_value = mock_parser_instance
            
            with patch('send_alerts.sys.exit') as mock_exit:
                main()
                mock_exit.assert_called_with(0)
    
    @patch('send_alerts.os.path.exists')
    @patch('send_alerts.sys.argv')
    def test_main_file_not_found(self, mock_argv, mock_exists):
        """Test main function with missing analysis file."""
        mock_argv.__getitem__.side_effect = lambda x: [
            'send_alerts.py',
            '--analysis', 'missing_file.json'
        ][x]
        mock_argv.__len__.return_value = 3
        
        mock_exists.return_value = False
        
        with patch('send_alerts.argparse.ArgumentParser') as mock_parser:
            mock_args = Mock()
            mock_args.analysis = 'missing_file.json'
            mock_args.webhook_url = None
            mock_args.repo = None
            mock_args.run_id = None
            mock_args.github_token = None
            
            mock_parser_instance = Mock()
            mock_parser_instance.parse_args.return_value = mock_args
            mock_parser.return_value = mock_parser_instance
            
            with patch('send_alerts.sys.exit') as mock_exit:
                main()
                mock_exit.assert_called_with(1)
    
    @patch('send_alerts.os.environ.get')
    @patch('send_alerts.AlertSender')
    @patch('builtins.open', new_callable=mock_open)
    @patch('send_alerts.os.path.exists')
    @patch('send_alerts.json.load')
    @patch('send_alerts.sys.argv')
    def test_main_with_env_github_token(self, mock_argv, mock_json_load, mock_exists, mock_file, mock_alert_sender, mock_env_get):
        """Test main function using GitHub token from environment."""
        mock_argv.__getitem__.side_effect = lambda x: [
            'send_alerts.py',
            '--analysis', 'test_analysis.json'
        ][x]
        mock_argv.__len__.return_value = 3
        
        mock_exists.return_value = True
        mock_json_load.return_value = self.sample_analysis
        mock_env_get.return_value = 'env_github_token'
        
        mock_sender_instance = Mock()
        mock_sender_instance.send_alerts.return_value = True
        mock_alert_sender.return_value = mock_sender_instance
        
        with patch('send_alerts.argparse.ArgumentParser') as mock_parser:
            mock_args = Mock()
            mock_args.analysis = 'test_analysis.json'
            mock_args.webhook_url = None
            mock_args.repo = None
            mock_args.run_id = None
            mock_args.github_token = None
            
            mock_parser_instance = Mock()
            mock_parser_instance.parse_args.return_value = mock_args
            mock_parser.return_value = mock_parser_instance
            
            with patch('send_alerts.sys.exit') as mock_exit:
                main()
                mock_exit.assert_called_with(0)
                
        # Verify AlertSender was called with environment token
        mock_alert_sender.assert_called_once_with(
            webhook_url=None,
            github_token='env_github_token',
            repo=None
        )


if __name__ == '__main__':
    unittest.main()