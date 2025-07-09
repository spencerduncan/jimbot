"""
Test cases for MCP input validation functionality.

These tests ensure that the MCP server properly validates and sanitizes
all incoming events to prevent security vulnerabilities.
"""

import pytest
import time
from unittest.mock import patch

from jimbot.mcp.utils.validation import (
    validate_event,
    check_rate_limit,
    get_validation_errors,
    EventValidator,
    ClientRateLimiter,
    ValidationError,
    MAX_EVENT_SIZE,
    MAX_STRING_LENGTH,
    MAX_ARRAY_LENGTH,
    MAX_OBJECT_PROPERTIES,
    MAX_NESTING_DEPTH,
    ALLOWED_EVENT_TYPES,
    REQUIRED_FIELDS
)


class TestEventValidator:
    """Test cases for EventValidator class."""

    def setup_method(self):
        """Setup test fixtures."""
        self.validator = EventValidator()

    def test_valid_event(self):
        """Test validation of a valid event."""
        event = {
            "type": "hand_played",
            "timestamp": 1609459200.0,
            "game_id": "test_game_123",
            "data": {
                "hand_type": "pair",
                "cards": ["AH", "AS"]
            }
        }
        
        assert self.validator.validate_event(event) is True
        assert len(self.validator.get_validation_errors()) == 0

    def test_missing_required_fields(self):
        """Test validation with missing required fields."""
        event = {
            "type": "hand_played",
            "timestamp": 1609459200.0
            # Missing game_id
        }
        
        assert self.validator.validate_event(event) is False
        errors = self.validator.get_validation_errors()
        assert len(errors) == 1
        assert errors[0].field == "required_fields"
        assert "game_id" in errors[0].message

    def test_invalid_event_type(self):
        """Test validation with invalid event type."""
        event = {
            "type": "invalid_type",
            "timestamp": 1609459200.0,
            "game_id": "test_game_123"
        }
        
        assert self.validator.validate_event(event) is False
        errors = self.validator.get_validation_errors()
        assert any("Invalid event type" in error.message for error in errors)

    def test_oversized_event(self):
        """Test validation with oversized event."""
        # Create a large event
        large_data = "x" * (MAX_EVENT_SIZE + 1)
        event = {
            "type": "hand_played",
            "timestamp": 1609459200.0,
            "game_id": "test_game_123",
            "data": {"large_field": large_data}
        }
        
        assert self.validator.validate_event(event) is False
        errors = self.validator.get_validation_errors()
        assert any("exceeds maximum" in error.message for error in errors)

    def test_security_scenarios(self):
        """Test various security attack scenarios."""
        # Test deeply nested object
        nested_obj = {}
        current = nested_obj
        for i in range(MAX_NESTING_DEPTH + 2):
            current["level"] = {}
            current = current["level"]
        
        event = {
            "type": "hand_played",
            "timestamp": 1609459200.0,
            "game_id": "test_game_123",
            "data": nested_obj
        }
        
        assert self.validator.validate_event(event) is False


class TestClientRateLimiter:
    """Test cases for ClientRateLimiter class."""

    def setup_method(self):
        """Setup test fixtures."""
        self.rate_limiter = ClientRateLimiter(max_events_per_minute=10)

    def test_rate_limit_within_bounds(self):
        """Test rate limiting within allowed bounds."""
        client_id = "test_client_1"
        
        # Should allow up to max_events_per_minute
        for i in range(10):
            assert self.rate_limiter.check_rate_limit(client_id) is True
        
        # Should deny further requests
        assert self.rate_limiter.check_rate_limit(client_id) is False

    def test_rate_limit_multiple_clients(self):
        """Test rate limiting with multiple clients."""
        client1 = "test_client_1"
        client2 = "test_client_2"
        
        # Both clients should be allowed independently
        for i in range(5):
            assert self.rate_limiter.check_rate_limit(client1) is True
            assert self.rate_limiter.check_rate_limit(client2) is True


class TestGlobalFunctions:
    """Test cases for global validation functions."""

    def test_validate_event_function(self):
        """Test global validate_event function."""
        valid_event = {
            "type": "hand_played",
            "timestamp": 1609459200.0,
            "game_id": "test_game_123"
        }
        
        assert validate_event(valid_event) is True
        
        invalid_event = {
            "type": "invalid_type",
            "timestamp": 1609459200.0,
            "game_id": "test_game_123"
        }
        
        assert validate_event(invalid_event) is False

    def test_check_rate_limit_function(self):
        """Test global check_rate_limit function."""
        client_id = "test_client_1"
        
        # Should allow initial requests
        assert check_rate_limit(client_id) is True


if __name__ == "__main__":
    # Run basic tests without pytest
    print("Running basic validation tests...")
    
    # Test valid event
    valid_event = {
        "type": "hand_played",
        "timestamp": 1609459200.0,
        "game_id": "test_game_123"
    }
    print(f"Valid event test: {validate_event(valid_event)}")
    
    # Test invalid event
    invalid_event = {
        "type": "invalid_type",
        "timestamp": 1609459200.0,
        "game_id": "test_game_123"
    }
    print(f"Invalid event test: {validate_event(invalid_event)}")
    
    # Test rate limiting
    client_id = "test_client"
    print(f"Rate limit test: {check_rate_limit(client_id)}")
    
    print("Basic tests completed successfully!")