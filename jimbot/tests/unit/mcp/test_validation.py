"""
Unit tests for MCP event validation module.

Tests comprehensive input validation, rate limiting, and data sanitization.
"""

import json
import time
import unittest
from unittest.mock import patch

from jimbot.mcp.utils.validation import (
    ClientRateLimiter,
    sanitize_string,
    sanitize_event_data,
    validate_event,
    get_rate_limiter,
    MAX_EVENT_SIZE,
    EVENT_SCHEMA
)


class TestSanitization(unittest.TestCase):
    """Test data sanitization functions."""
    
    def test_sanitize_string_basic(self):
        """Test basic string sanitization."""
        # Normal string should pass through
        self.assertEqual(sanitize_string("hello world"), "hello world")
        
        # Long string should be truncated
        long_string = "x" * 2000
        self.assertEqual(len(sanitize_string(long_string)), 1000)
        
        # Null bytes should be removed
        self.assertEqual(sanitize_string("hello\0world"), "helloworld")
        
        # Control characters should be removed except newlines and tabs
        self.assertEqual(sanitize_string("hello\x01world"), "helloworld")
        self.assertEqual(sanitize_string("hello\nworld"), "hello\nworld")
        self.assertEqual(sanitize_string("hello\tworld"), "hello\tworld")
        
    def test_sanitize_event_data(self):
        """Test event data sanitization."""
        # Basic data should pass through
        data = {
            "type": "test",
            "value": 42,
            "flag": True
        }
        self.assertEqual(sanitize_event_data(data), data)
        
        # Long keys should be removed
        data = {
            "x" * 100: "value",
            "normal_key": "value"
        }
        result = sanitize_event_data(data)
        self.assertNotIn("x" * 100, result)
        self.assertIn("normal_key", result)
        
        # Nested objects should be sanitized
        data = {
            "nested": {
                "deep": {
                    "value": "test\0data"
                }
            }
        }
        result = sanitize_event_data(data)
        self.assertEqual(result["nested"]["deep"]["value"], "testdata")
        
        # Arrays should be limited
        data = {
            "items": list(range(200))
        }
        result = sanitize_event_data(data)
        self.assertEqual(len(result["items"]), 100)
        
        # Max depth should be respected
        deeply_nested = {"level": 1}
        current = deeply_nested
        for i in range(10):
            current["nested"] = {"level": i + 2}
            current = current["nested"]
            
        result = sanitize_event_data(deeply_nested, max_depth=3)
        # Check that deep nesting is cut off
        self.assertIn("level", result)
        self.assertIn("nested", result)
        self.assertIn("level", result["nested"])
        self.assertIn("nested", result["nested"])
        # Beyond depth 3 should be empty
        self.assertEqual(result["nested"]["nested"]["nested"], {})


class TestRateLimiter(unittest.TestCase):
    """Test rate limiting functionality."""
    
    def test_basic_rate_limiting(self):
        """Test basic rate limiting per minute."""
        limiter = ClientRateLimiter(max_events_per_minute=10, max_burst=5)
        client_id = "test_client"
        
        # First 5 events should pass (burst limit)
        for i in range(5):
            self.assertTrue(limiter.check_rate_limit(client_id))
            
        # 6th event should fail (exceeds burst)
        self.assertFalse(limiter.check_rate_limit(client_id))
        
    def test_burst_recovery(self):
        """Test that burst limit recovers after 1 second."""
        limiter = ClientRateLimiter(max_events_per_minute=100, max_burst=5)
        client_id = "test_client"
        
        # Fill burst limit
        for i in range(5):
            self.assertTrue(limiter.check_rate_limit(client_id))
            
        # Should be rate limited
        self.assertFalse(limiter.check_rate_limit(client_id))
        
        # Wait for burst window to pass
        time.sleep(1.1)
        
        # Should be allowed again
        self.assertTrue(limiter.check_rate_limit(client_id))
        
    def test_minute_limit(self):
        """Test minute-based rate limiting."""
        limiter = ClientRateLimiter(max_events_per_minute=10, max_burst=100)
        client_id = "test_client"
        
        # Send 10 events
        for i in range(10):
            self.assertTrue(limiter.check_rate_limit(client_id))
            
        # 11th should fail
        self.assertFalse(limiter.check_rate_limit(client_id))
        
    def test_multiple_clients(self):
        """Test that rate limiting is per-client."""
        limiter = ClientRateLimiter(max_events_per_minute=5, max_burst=3)
        
        # Client 1 fills their limit
        for i in range(3):
            self.assertTrue(limiter.check_rate_limit("client1"))
        self.assertFalse(limiter.check_rate_limit("client1"))
        
        # Client 2 should still be allowed
        for i in range(3):
            self.assertTrue(limiter.check_rate_limit("client2"))
            
    def test_cleanup_old_clients(self):
        """Test cleanup of old client data."""
        limiter = ClientRateLimiter()
        
        # Add some events
        limiter.check_rate_limit("old_client")
        limiter.check_rate_limit("new_client")
        
        # Mock time to make old_client data appear old
        with patch('time.time', return_value=time.time() + 3700):
            limiter.cleanup_old_clients(max_age_seconds=3600)
            
        # Old client should be cleaned up
        self.assertNotIn("old_client", limiter.minute_windows)
        # New client should remain
        self.assertIn("new_client", limiter.minute_windows)


class TestEventValidation(unittest.TestCase):
    """Test event validation logic."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.valid_event = {
            "type": "hand_played",
            "timestamp": time.time(),
            "game_id": "test_game_123",
            "data": {
                "hand_type": "Pair",
                "chips": 100,
                "mult": 2,
                "cards_played": [
                    {"rank": "A", "suit": "Hearts"},
                    {"rank": "A", "suit": "Spades"}
                ]
            }
        }
        
    def test_valid_event(self):
        """Test that valid events pass validation."""
        self.assertTrue(validate_event(self.valid_event))
        
    def test_missing_required_fields(self):
        """Test that events missing required fields fail."""
        # Missing type
        event = self.valid_event.copy()
        del event["type"]
        self.assertFalse(validate_event(event))
        
        # Missing timestamp
        event = self.valid_event.copy()
        del event["timestamp"]
        self.assertFalse(validate_event(event))
        
        # Missing game_id
        event = self.valid_event.copy()
        del event["game_id"]
        self.assertFalse(validate_event(event))
        
        # Missing data
        event = self.valid_event.copy()
        del event["data"]
        self.assertFalse(validate_event(event))
        
    def test_invalid_event_type(self):
        """Test that invalid event types fail."""
        event = self.valid_event.copy()
        event["type"] = "invalid_type"
        self.assertFalse(validate_event(event))
        
    def test_invalid_timestamp(self):
        """Test timestamp validation."""
        # Negative timestamp
        event = self.valid_event.copy()
        event["timestamp"] = -1
        self.assertFalse(validate_event(event))
        
        # Too far in future
        event = self.valid_event.copy()
        event["timestamp"] = time.time() + 7200  # 2 hours in future
        self.assertFalse(validate_event(event))
        
        # Too far in past
        event = self.valid_event.copy()
        event["timestamp"] = time.time() - 7200  # 2 hours in past
        self.assertFalse(validate_event(event))
        
    def test_invalid_game_id(self):
        """Test game ID validation."""
        # Empty game ID
        event = self.valid_event.copy()
        event["game_id"] = ""
        self.assertFalse(validate_event(event))
        
        # Too long game ID
        event = self.valid_event.copy()
        event["game_id"] = "x" * 101
        self.assertFalse(validate_event(event))
        
        # Path traversal attempt
        event = self.valid_event.copy()
        event["game_id"] = "../../../etc/passwd"
        self.assertFalse(validate_event(event))
        
        # Invalid characters
        event = self.valid_event.copy()
        event["game_id"] = "game!@#$%"
        self.assertFalse(validate_event(event))
        
    def test_event_size_limit(self):
        """Test that oversized events are rejected."""
        event = self.valid_event.copy()
        # Add huge data field
        event["data"]["huge_field"] = "x" * MAX_EVENT_SIZE
        self.assertFalse(validate_event(event))
        
    def test_additional_properties_rejected(self):
        """Test that events with extra properties are rejected."""
        event = self.valid_event.copy()
        event["extra_field"] = "should not be here"
        self.assertFalse(validate_event(event))
        
    def test_too_many_properties(self):
        """Test that events with too many properties are rejected."""
        event = self.valid_event.copy()
        # Add many properties to data
        for i in range(60):
            event["data"][f"field_{i}"] = i
        self.assertFalse(validate_event(event))
        
    def test_hand_played_validation(self):
        """Test specific validation for hand_played events."""
        # Valid hand_played event
        event = self.valid_event.copy()
        self.assertTrue(validate_event(event))
        
        # Invalid hand type
        event = self.valid_event.copy()
        event["data"]["hand_type"] = "Invalid Hand"
        self.assertFalse(validate_event(event))
        
        # Invalid card rank
        event = self.valid_event.copy()
        event["data"]["cards_played"][0]["rank"] = "X"
        self.assertFalse(validate_event(event))
        
        # Invalid suit
        event = self.valid_event.copy()
        event["data"]["cards_played"][0]["suit"] = "Invalid"
        self.assertFalse(validate_event(event))
        
        # Too many cards
        event = self.valid_event.copy()
        event["data"]["cards_played"] = [
            {"rank": "A", "suit": "Hearts"} for _ in range(6)
        ]
        self.assertFalse(validate_event(event))
        
        # Negative chips
        event = self.valid_event.copy()
        event["data"]["chips"] = -10
        self.assertFalse(validate_event(event))
        
    def test_shop_entered_validation(self):
        """Test specific validation for shop_entered events."""
        event = {
            "type": "shop_entered",
            "timestamp": time.time(),
            "game_id": "test_game",
            "data": {
                "ante": 1,
                "round": 1,
                "money": 100,
                "shop_items": [
                    {"type": "joker", "cost": 5},
                    {"type": "voucher", "cost": 10}
                ]
            }
        }
        self.assertTrue(validate_event(event))
        
        # Invalid ante
        event["data"]["ante"] = 0
        self.assertFalse(validate_event(event))
        
        # Reset and test negative money
        event["data"]["ante"] = 1
        event["data"]["money"] = -5
        self.assertFalse(validate_event(event))
        
    @patch('jimbot.mcp.utils.validation._rate_limiter')
    def test_rate_limiting_integration(self, mock_limiter):
        """Test that rate limiting is applied during validation."""
        # Mock rate limiter to return False
        mock_limiter.check_rate_limit.return_value = False
        
        # Valid event should fail due to rate limiting
        self.assertFalse(validate_event(self.valid_event, client_id="test_client"))
        mock_limiter.check_rate_limit.assert_called_once_with("test_client")
        
    def test_malformed_json(self):
        """Test handling of non-dict events."""
        # String instead of dict
        self.assertFalse(validate_event("not a dict"))
        
        # List instead of dict
        self.assertFalse(validate_event([1, 2, 3]))
        
        # None
        self.assertFalse(validate_event(None))


class TestGlobalRateLimiter(unittest.TestCase):
    """Test the global rate limiter instance."""
    
    def test_get_rate_limiter(self):
        """Test that get_rate_limiter returns consistent instance."""
        limiter1 = get_rate_limiter()
        limiter2 = get_rate_limiter()
        
        # Should be the same instance
        self.assertIs(limiter1, limiter2)
        
        # Should be a ClientRateLimiter instance
        self.assertIsInstance(limiter1, ClientRateLimiter)


if __name__ == "__main__":
    unittest.main()