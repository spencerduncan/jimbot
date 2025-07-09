#!/usr/bin/env python3
"""
Smoke test for MCP security validation implementation.

This script runs basic tests to verify the security fixes are working correctly.
"""

import sys
import os
import logging

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Disable logging for cleaner test output
logging.getLogger().setLevel(logging.CRITICAL)

def test_validation_imports():
    """Test that validation modules can be imported."""
    try:
        from jimbot.mcp.utils.validation import validate_event, check_rate_limit
        from jimbot.mcp.utils.monitoring import MetricsCollector
        print("✓ All validation and monitoring modules import successfully")
        return True
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False

def test_server_imports():
    """Test that server can be imported and instantiated."""
    try:
        from jimbot.mcp.server import MCPServer
        server = MCPServer()
        print(f"✓ Server instantiated successfully with secure default host: {server.host}")
        return True
    except ImportError as e:
        print(f"✗ Server import error: {e}")
        return False

def test_validation_functionality():
    """Test basic validation functionality."""
    try:
        from jimbot.mcp.utils.validation import validate_event, get_validation_errors
        
        # Test valid event
        valid_event = {
            "type": "hand_played",
            "timestamp": 1609459200.0,
            "game_id": "test_game_123",
            "data": {"hand_type": "pair", "cards": ["AH", "AS"]}
        }
        
        if not validate_event(valid_event):
            print("✗ Valid event failed validation")
            return False
        
        # Test invalid event
        invalid_event = {
            "type": "invalid_event_type",
            "timestamp": 1609459200.0,
            "game_id": "test_game_123"
        }
        
        if validate_event(invalid_event):
            print("✗ Invalid event passed validation")
            return False
        
        errors = get_validation_errors()
        if len(errors) == 0:
            print("✗ No validation errors recorded for invalid event")
            return False
        
        print("✓ Event validation working correctly")
        return True
        
    except Exception as e:
        print(f"✗ Validation test error: {e}")
        return False

def test_rate_limiting():
    """Test rate limiting functionality."""
    try:
        from jimbot.mcp.utils.validation import ClientRateLimiter
        
        # Test with small rate limit for testing
        rate_limiter = ClientRateLimiter(max_events_per_minute=3)
        client_id = "test_client_123"
        
        # Should allow initial requests
        for i in range(3):
            if not rate_limiter.check_rate_limit(client_id):
                print(f"✗ Rate limiter rejected request {i} unexpectedly")
                return False
        
        # Should reject further requests
        if rate_limiter.check_rate_limit(client_id):
            print("✗ Rate limiter allowed request beyond limit")
            return False
        
        print("✓ Rate limiting working correctly")
        return True
        
    except Exception as e:
        print(f"✗ Rate limiting test error: {e}")
        return False

def test_monitoring():
    """Test monitoring functionality."""
    try:
        from jimbot.mcp.utils.monitoring import MetricsCollector
        
        metrics = MetricsCollector()
        
        # Test counter
        metrics.increment("test_counter", 5)
        if metrics.get_counter("test_counter") != 5.0:
            print("✗ Counter not working correctly")
            return False
        
        # Test gauge
        metrics.gauge("test_gauge", 42.5)
        if metrics.get_gauge("test_gauge") != 42.5:
            print("✗ Gauge not working correctly")
            return False
        
        # Test security event
        metrics.security_event("test_event", "test_client", {"test": "data"})
        events = metrics.get_security_events()
        if len(events) != 1:
            print("✗ Security event not recorded")
            return False
        
        print("✓ Monitoring functionality working correctly")
        return True
        
    except Exception as e:
        print(f"✗ Monitoring test error: {e}")
        return False

def test_security_defaults():
    """Test that security defaults are properly set."""
    try:
        from jimbot.mcp.server import MCPServer
        
        # Test default host is localhost
        server = MCPServer()
        if server.host != "127.0.0.1":
            print(f"✗ Default host is not secure: {server.host}")
            return False
        
        print("✓ Security defaults are correctly configured")
        return True
        
    except Exception as e:
        print(f"✗ Security defaults test error: {e}")
        return False

def main():
    """Run all smoke tests."""
    print("MCP Security Validation Smoke Test")
    print("=" * 40)
    
    tests = [
        test_validation_imports,
        test_server_imports,
        test_validation_functionality,
        test_rate_limiting,
        test_monitoring,
        test_security_defaults
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("=" * 40)
    print(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All tests passed! MCP security validation is working correctly.")
        return 0
    else:
        print("❌ Some tests failed. Check the output above for details.")
        return 1

if __name__ == "__main__":
    sys.exit(main())