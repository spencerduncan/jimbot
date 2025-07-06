"""
Event validation module for MCP server.

Provides comprehensive validation for incoming events to prevent malformed
or malicious data from being processed.
"""

import time
from collections import defaultdict, deque
from typing import Any, Dict, Optional

import jsonschema
from jsonschema import ValidationError

# Maximum allowed event size in bytes (10KB)
MAX_EVENT_SIZE = 10 * 1024

# Event type schema definitions
EVENT_SCHEMA = {
    "type": "object",
    "required": ["type", "timestamp", "game_id", "data"],
    "properties": {
        "type": {
            "type": "string",
            "enum": [
                "game_start",
                "hand_played",
                "shop_entered",
                "card_purchased",
                "game_over",
                "action",
                "state_update",
                "joker_activated",
                "round_complete",
                "ante_complete"
            ]
        },
        "timestamp": {
            "type": "number",
            "minimum": 0,
            "maximum": 2147483647  # Max 32-bit timestamp
        },
        "game_id": {
            "type": "string",
            "minLength": 1,
            "maxLength": 100,
            "pattern": "^[a-zA-Z0-9_-]+$"  # Alphanumeric with underscores and hyphens
        },
        "data": {
            "type": "object",
            "maxProperties": 50  # Prevent huge objects
        }
    },
    "additionalProperties": False,
    "maxProperties": 10  # Limit total fields
}

# Specific validation schemas for different event types
HAND_PLAYED_SCHEMA = {
    "type": "object",
    "required": ["hand_type", "chips", "mult", "cards_played"],
    "properties": {
        "hand_type": {
            "type": "string",
            "enum": [
                "High Card", "Pair", "Two Pair", "Three of a Kind",
                "Straight", "Flush", "Full House", "Four of a Kind",
                "Straight Flush", "Flush House", "Flush Five", "Five of a Kind"
            ]
        },
        "chips": {"type": "number", "minimum": 0, "maximum": 1e9},
        "mult": {"type": "number", "minimum": 0, "maximum": 1e6},
        "cards_played": {
            "type": "array",
            "minItems": 1,
            "maxItems": 5,
            "items": {
                "type": "object",
                "required": ["rank", "suit"],
                "properties": {
                    "rank": {"type": "string", "pattern": "^[A2-9TJQK]$"},
                    "suit": {"type": "string", "enum": ["Hearts", "Diamonds", "Clubs", "Spades", "Wild"]}
                }
            }
        }
    },
    "additionalProperties": True  # Allow additional game state data
}

SHOP_ENTERED_SCHEMA = {
    "type": "object",
    "required": ["ante", "round", "money"],
    "properties": {
        "ante": {"type": "integer", "minimum": 1, "maximum": 100},
        "round": {"type": "integer", "minimum": 1, "maximum": 10},
        "money": {"type": "number", "minimum": 0, "maximum": 1e6},
        "shop_items": {
            "type": "array",
            "maxItems": 10,
            "items": {
                "type": "object",
                "required": ["type", "cost"],
                "properties": {
                    "type": {"type": "string", "maxLength": 50},
                    "cost": {"type": "number", "minimum": 0, "maximum": 1e4}
                }
            }
        }
    },
    "additionalProperties": True
}


class ClientRateLimiter:
    """Rate limiter to prevent event spam from individual clients."""
    
    def __init__(self, max_events_per_minute: int = 600, max_burst: int = 30):
        """
        Initialize rate limiter.
        
        Args:
            max_events_per_minute: Maximum events allowed per minute per client
            max_burst: Maximum events allowed in a short burst (1 second)
        """
        self.max_events_per_minute = max_events_per_minute
        self.max_burst = max_burst
        self.minute_windows = defaultdict(lambda: deque(maxlen=max_events_per_minute))
        self.burst_windows = defaultdict(lambda: deque(maxlen=max_burst))
        
    def check_rate_limit(self, client_id: str) -> bool:
        """
        Check if client is within rate limits.
        
        Args:
            client_id: Unique client identifier
            
        Returns:
            True if within limits, False if rate limited
        """
        now = time.time()
        
        # Check burst limit (events in last second)
        burst_events = self.burst_windows[client_id]
        while burst_events and burst_events[0] < now - 1:
            burst_events.popleft()
            
        if len(burst_events) >= self.max_burst:
            return False
            
        # Check minute limit
        minute_events = self.minute_windows[client_id]
        while minute_events and minute_events[0] < now - 60:
            minute_events.popleft()
            
        if len(minute_events) >= self.max_events_per_minute:
            return False
            
        # Record event
        burst_events.append(now)
        minute_events.append(now)
        return True
        
    def cleanup_old_clients(self, max_age_seconds: int = 3600):
        """Remove rate limit data for clients that haven't sent events recently."""
        cutoff = time.time() - max_age_seconds
        
        # Clean minute windows
        old_clients = []
        for client_id, events in self.minute_windows.items():
            if not events or events[-1] < cutoff:
                old_clients.append(client_id)
        
        for client_id in old_clients:
            del self.minute_windows[client_id]
            if client_id in self.burst_windows:
                del self.burst_windows[client_id]


# Global rate limiter instance
_rate_limiter = ClientRateLimiter()


def sanitize_string(value: str, max_length: int = 1000) -> str:
    """
    Sanitize string values to prevent injection attacks.
    
    Args:
        value: String to sanitize
        max_length: Maximum allowed length
        
    Returns:
        Sanitized string
    """
    if not isinstance(value, str):
        return str(value)[:max_length]
        
    # Remove null bytes and control characters
    sanitized = value.replace('\0', '')
    
    # Remove other control characters except newlines and tabs
    sanitized = ''.join(char for char in sanitized 
                       if char == '\n' or char == '\t' or ord(char) >= 32)
    
    # Limit length
    return sanitized[:max_length]


def sanitize_event_data(data: Dict[str, Any], max_depth: int = 5) -> Dict[str, Any]:
    """
    Recursively sanitize event data.
    
    Args:
        data: Event data to sanitize
        max_depth: Maximum nesting depth
        
    Returns:
        Sanitized event data
    """
    if max_depth <= 0:
        return {}
        
    sanitized = {}
    
    for key, value in data.items():
        # Limit key length
        if len(key) > 50:
            continue
            
        # Sanitize based on type
        if isinstance(value, str):
            sanitized[key] = sanitize_string(value)
        elif isinstance(value, (int, float)):
            # Ensure reasonable numeric ranges
            sanitized[key] = max(-1e9, min(1e9, value))
        elif isinstance(value, bool):
            sanitized[key] = value
        elif isinstance(value, dict):
            # Recursively sanitize nested objects
            sanitized[key] = sanitize_event_data(value, max_depth - 1)
        elif isinstance(value, list):
            # Limit array size and sanitize elements
            sanitized[key] = [
                sanitize_event_data(item, max_depth - 1) if isinstance(item, dict)
                else sanitize_string(item) if isinstance(item, str)
                else item
                for item in value[:100]  # Max 100 elements
            ]
        # Ignore other types (functions, classes, etc.)
            
    return sanitized


def validate_event(event: Dict[str, Any], client_id: Optional[str] = None) -> bool:
    """
    Validate incoming event structure and data.
    
    Args:
        event: Event dictionary to validate
        client_id: Optional client identifier for rate limiting
        
    Returns:
        True if event is valid, False otherwise
    """
    try:
        # Size check
        event_str = str(event)
        if len(event_str) > MAX_EVENT_SIZE:
            return False
            
        # Rate limiting check
        if client_id and not _rate_limiter.check_rate_limit(client_id):
            return False
            
        # Basic schema validation
        jsonschema.validate(event, EVENT_SCHEMA)
        
        # Type-specific validation
        event_type = event.get("type")
        event_data = event.get("data", {})
        
        if event_type == "hand_played":
            jsonschema.validate(event_data, HAND_PLAYED_SCHEMA)
        elif event_type == "shop_entered":
            jsonschema.validate(event_data, SHOP_ENTERED_SCHEMA)
        
        # Additional business logic validation
        
        # Timestamp should be recent (within last hour)
        current_time = time.time()
        if abs(event["timestamp"] - current_time) > 3600:
            return False
            
        # Game ID should not contain path traversal attempts
        game_id = event.get("game_id", "")
        if ".." in game_id or "/" in game_id or "\\" in game_id:
            return False
            
        return True
        
    except (ValidationError, KeyError, TypeError, ValueError):
        return False


def get_rate_limiter() -> ClientRateLimiter:
    """Get the global rate limiter instance."""
    return _rate_limiter