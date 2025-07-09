"""
Input validation utilities for MCP events.

This module provides comprehensive validation for all events received
by the MCP server to prevent malformed or malicious events from being processed.
"""

import json
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from collections import defaultdict, deque
import time
import re

logger = logging.getLogger(__name__)

# Maximum sizes for security
MAX_EVENT_SIZE = 10000  # 10KB per event
MAX_STRING_LENGTH = 1000  # 1KB per string field
MAX_ARRAY_LENGTH = 100  # Maximum array size
MAX_OBJECT_PROPERTIES = 50  # Maximum number of properties in nested objects
MAX_NESTING_DEPTH = 10  # Maximum nesting depth
MAX_KEY_LENGTH = 50  # Maximum key length

# Allowed event types
ALLOWED_EVENT_TYPES = {
    'game_start',
    'game_over',
    'hand_played',
    'shop_entered',
    'shop_exited',
    'card_purchased',
    'card_sold',
    'blind_selected',
    'blind_defeated',
    'joker_triggered',
    'action',
    'state_change',
    'round_start',
    'round_end',
    'ante_change',
    'booster_opened',
    'heartbeat'
}

# Required fields for all events
REQUIRED_FIELDS = {'type', 'timestamp', 'game_id'}

# Field patterns for validation
GAME_ID_PATTERN = re.compile(r'^[a-zA-Z0-9_-]{1,50}$')
CLIENT_ID_PATTERN = re.compile(r'^[a-zA-Z0-9_.-]{1,100}$')

@dataclass
class ValidationError:
    """Represents a validation error."""
    field: str
    message: str
    severity: str = 'error'  # 'error', 'warning'

class EventValidator:
    """Validates MCP events for security and data integrity."""
    
    def __init__(self):
        self.validation_errors = []
        
    def validate_event(self, event: Dict[str, Any]) -> bool:
        """
        Validate an event structure and content.
        
        Args:
            event: Event data dictionary
            
        Returns:
            bool: True if event is valid, False otherwise
        """
        self.validation_errors = []
        
        try:
            # Check event size
            if not self._validate_event_size(event):
                return False
                
            # Check required fields
            if not self._validate_required_fields(event):
                return False
                
            # Check field types and values
            if not self._validate_field_types(event):
                return False
                
            # Check nesting depth
            if not self._validate_nesting_depth(event):
                return False
                
            # Validate specific event types
            if not self._validate_event_type_specific(event):
                return False
                
            # Sanitize data
            self._sanitize_event_data(event)
            
            return True
            
        except Exception as e:
            logger.error(f"Validation error: {e}")
            self.validation_errors.append(
                ValidationError('general', f'Validation exception: {e}')
            )
            return False
    
    def _validate_event_size(self, event: Dict[str, Any]) -> bool:
        """Check if event size is within limits."""
        try:
            event_size = len(json.dumps(event))
            if event_size > MAX_EVENT_SIZE:
                self.validation_errors.append(
                    ValidationError('size', f'Event size {event_size} exceeds maximum {MAX_EVENT_SIZE}')
                )
                return False
            return True
        except (TypeError, ValueError) as e:
            self.validation_errors.append(
                ValidationError('size', f'Cannot measure event size: {e}')
            )
            return False
    
    def _validate_required_fields(self, event: Dict[str, Any]) -> bool:
        """Check if all required fields are present."""
        missing_fields = REQUIRED_FIELDS - event.keys()
        if missing_fields:
            self.validation_errors.append(
                ValidationError('required_fields', f'Missing required fields: {missing_fields}')
            )
            return False
        return True
    
    def _validate_field_types(self, event: Dict[str, Any]) -> bool:
        """Validate field types and values."""
        # Validate event type
        if 'type' in event:
            if not isinstance(event['type'], str):
                self.validation_errors.append(
                    ValidationError('type', 'Event type must be a string')
                )
                return False
            if event['type'] not in ALLOWED_EVENT_TYPES:
                self.validation_errors.append(
                    ValidationError('type', f'Invalid event type: {event["type"]}')
                )
                return False
        
        # Validate timestamp
        if 'timestamp' in event:
            if not isinstance(event['timestamp'], (int, float)):
                self.validation_errors.append(
                    ValidationError('timestamp', 'Timestamp must be a number')
                )
                return False
            if event['timestamp'] < 0:
                self.validation_errors.append(
                    ValidationError('timestamp', 'Timestamp cannot be negative')
                )
                return False
        
        # Validate game_id
        if 'game_id' in event:
            if not isinstance(event['game_id'], str):
                self.validation_errors.append(
                    ValidationError('game_id', 'Game ID must be a string')
                )
                return False
            if not GAME_ID_PATTERN.match(event['game_id']):
                self.validation_errors.append(
                    ValidationError('game_id', 'Game ID contains invalid characters')
                )
                return False
        
        # Validate data field if present
        if 'data' in event:
            if not isinstance(event['data'], dict):
                self.validation_errors.append(
                    ValidationError('data', 'Data field must be an object')
                )
                return False
            if len(event['data']) > MAX_OBJECT_PROPERTIES:
                self.validation_errors.append(
                    ValidationError('data', f'Data object has too many properties: {len(event["data"])}')
                )
                return False
        
        return True
    
    def _validate_nesting_depth(self, obj: Any, current_depth: int = 0) -> bool:
        """Check nesting depth to prevent stack overflow."""
        if current_depth > MAX_NESTING_DEPTH:
            self.validation_errors.append(
                ValidationError('nesting', f'Nesting depth {current_depth} exceeds maximum {MAX_NESTING_DEPTH}')
            )
            return False
        
        if isinstance(obj, dict):
            for key, value in obj.items():
                if len(key) > MAX_KEY_LENGTH:
                    self.validation_errors.append(
                        ValidationError('key_length', f'Key "{key[:20]}..." exceeds maximum length')
                    )
                    return False
                if not self._validate_nesting_depth(value, current_depth + 1):
                    return False
        elif isinstance(obj, list):
            if len(obj) > MAX_ARRAY_LENGTH:
                self.validation_errors.append(
                    ValidationError('array_length', f'Array length {len(obj)} exceeds maximum {MAX_ARRAY_LENGTH}')
                )
                return False
            for item in obj:
                if not self._validate_nesting_depth(item, current_depth + 1):
                    return False
        
        return True
    
    def _validate_event_type_specific(self, event: Dict[str, Any]) -> bool:
        """Validate specific event types with business logic."""
        event_type = event.get('type')
        
        if event_type == 'hand_played':
            return self._validate_hand_played_event(event)
        elif event_type == 'shop_entered':
            return self._validate_shop_event(event)
        elif event_type == 'card_purchased':
            return self._validate_card_event(event)
        elif event_type == 'action':
            return self._validate_action_event(event)
            
        return True
    
    def _validate_hand_played_event(self, event: Dict[str, Any]) -> bool:
        """Validate hand played event structure."""
        data = event.get('data', {})
        
        # Check for required hand data
        if 'hand_type' in data:
            if not isinstance(data['hand_type'], str):
                self.validation_errors.append(
                    ValidationError('hand_type', 'Hand type must be a string')
                )
                return False
        
        if 'cards' in data:
            if not isinstance(data['cards'], list):
                self.validation_errors.append(
                    ValidationError('cards', 'Cards must be an array')
                )
                return False
            if len(data['cards']) > 8:  # Maximum hand size in Balatro
                self.validation_errors.append(
                    ValidationError('cards', f'Too many cards in hand: {len(data["cards"])}')
                )
                return False
        
        return True
    
    def _validate_shop_event(self, event: Dict[str, Any]) -> bool:
        """Validate shop event structure."""
        data = event.get('data', {})
        
        if 'shop_items' in data:
            if not isinstance(data['shop_items'], list):
                self.validation_errors.append(
                    ValidationError('shop_items', 'Shop items must be an array')
                )
                return False
        
        return True
    
    def _validate_card_event(self, event: Dict[str, Any]) -> bool:
        """Validate card-related event structure."""
        data = event.get('data', {})
        
        if 'card_id' in data:
            if not isinstance(data['card_id'], str):
                self.validation_errors.append(
                    ValidationError('card_id', 'Card ID must be a string')
                )
                return False
        
        if 'cost' in data:
            if not isinstance(data['cost'], (int, float)):
                self.validation_errors.append(
                    ValidationError('cost', 'Cost must be a number')
                )
                return False
            if data['cost'] < 0:
                self.validation_errors.append(
                    ValidationError('cost', 'Cost cannot be negative')
                )
                return False
        
        return True
    
    def _validate_action_event(self, event: Dict[str, Any]) -> bool:
        """Validate action event structure."""
        data = event.get('data', {})
        
        if 'action_type' in data:
            if not isinstance(data['action_type'], str):
                self.validation_errors.append(
                    ValidationError('action_type', 'Action type must be a string')
                )
                return False
        
        return True
    
    def _sanitize_event_data(self, event: Dict[str, Any]) -> None:
        """Sanitize event data in place."""
        self._sanitize_object(event)
    
    def _sanitize_object(self, obj: Any) -> Any:
        """Recursively sanitize an object."""
        if isinstance(obj, dict):
            sanitized = {}
            for key, value in obj.items():
                # Sanitize key
                clean_key = self._sanitize_string(key)[:MAX_KEY_LENGTH]
                if clean_key:
                    sanitized[clean_key] = self._sanitize_object(value)
            obj.clear()
            obj.update(sanitized)
        elif isinstance(obj, list):
            for i, item in enumerate(obj[:MAX_ARRAY_LENGTH]):
                obj[i] = self._sanitize_object(item)
            # Trim array if too long
            if len(obj) > MAX_ARRAY_LENGTH:
                obj[:] = obj[:MAX_ARRAY_LENGTH]
        elif isinstance(obj, str):
            return self._sanitize_string(obj)
        elif isinstance(obj, (int, float)):
            # Clamp numeric values to reasonable ranges
            if isinstance(obj, float) and (obj != obj):  # NaN check
                return 0
            return max(-1e9, min(1e9, obj))
        
        return obj
    
    def _sanitize_string(self, s: str) -> str:
        """Sanitize a string value."""
        if not isinstance(s, str):
            return str(s)[:MAX_STRING_LENGTH]
        
        # Remove null bytes and control characters
        sanitized = ''.join(c for c in s if ord(c) >= 32 or c in '\t\n\r')
        
        # Limit length
        return sanitized[:MAX_STRING_LENGTH]
    
    def get_validation_errors(self) -> List[ValidationError]:
        """Get list of validation errors from last validation."""
        return self.validation_errors.copy()


class ClientRateLimiter:
    """Rate limiter for client connections."""
    
    def __init__(self, max_events_per_minute: int = 600):
        """
        Initialize rate limiter.
        
        Args:
            max_events_per_minute: Maximum events allowed per client per minute
        """
        self.max_events_per_minute = max_events_per_minute
        self.client_events = defaultdict(lambda: deque(maxlen=max_events_per_minute))
        self.cleanup_interval = 60  # Clean up old entries every minute
        self.last_cleanup = time.time()
    
    def check_rate_limit(self, client_id: str) -> bool:
        """
        Check if client is within rate limit.
        
        Args:
            client_id: Client identifier
            
        Returns:
            bool: True if within rate limit, False otherwise
        """
        if not isinstance(client_id, str) or not CLIENT_ID_PATTERN.match(client_id):
            logger.warning(f"Invalid client ID format: {client_id}")
            return False
        
        now = time.time()
        
        # Periodic cleanup
        if now - self.last_cleanup > self.cleanup_interval:
            self._cleanup_old_entries()
            self.last_cleanup = now
        
        client_events = self.client_events[client_id]
        
        # Remove events older than 1 minute
        while client_events and client_events[0] < now - 60:
            client_events.popleft()
        
        # Check if client is over rate limit
        if len(client_events) >= self.max_events_per_minute:
            logger.warning(f"Rate limit exceeded for client {client_id}")
            return False
        
        # Add current event
        client_events.append(now)
        return True
    
    def _cleanup_old_entries(self):
        """Clean up old client entries."""
        now = time.time()
        clients_to_remove = []
        
        for client_id, events in self.client_events.items():
            # Remove old events
            while events and events[0] < now - 60:
                events.popleft()
            
            # Remove client if no recent events
            if not events:
                clients_to_remove.append(client_id)
        
        for client_id in clients_to_remove:
            del self.client_events[client_id]
    
    def get_client_count(self) -> int:
        """Get number of active clients."""
        return len(self.client_events)
    
    def get_client_event_count(self, client_id: str) -> int:
        """Get current event count for a client."""
        return len(self.client_events.get(client_id, []))


# Global instances
_validator = EventValidator()
_rate_limiter = ClientRateLimiter()


def validate_event(event: Dict[str, Any]) -> bool:
    """
    Validate an event structure and content.
    
    Args:
        event: Event data dictionary
        
    Returns:
        bool: True if event is valid, False otherwise
    """
    return _validator.validate_event(event)


def check_rate_limit(client_id: str) -> bool:
    """
    Check if client is within rate limit.
    
    Args:
        client_id: Client identifier
        
    Returns:
        bool: True if within rate limit, False otherwise
    """
    return _rate_limiter.check_rate_limit(client_id)


def get_validation_errors() -> List[ValidationError]:
    """Get validation errors from last validation."""
    return _validator.get_validation_errors()


def get_rate_limiter_stats() -> Dict[str, int]:
    """Get rate limiter statistics."""
    return {
        'active_clients': _rate_limiter.get_client_count(),
        'max_events_per_minute': _rate_limiter.max_events_per_minute
    }