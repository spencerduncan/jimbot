"""Correlation Context Module

Tracks correlation IDs across async operations.
"""

import contextvars
import uuid
from typing import Optional


# Context variable for correlation ID
_correlation_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    'correlation_id', default=None
)


class CorrelationContext:
    """Manages correlation IDs for request tracking"""
    
    @staticmethod
    def set_current(correlation_id: Optional[str] = None) -> str:
        """Set correlation ID for current context"""
        if correlation_id is None:
            correlation_id = str(uuid.uuid4())
        _correlation_id.set(correlation_id)
        return correlation_id
        
    @staticmethod
    def get_current() -> Optional[str]:
        """Get current correlation ID"""
        return _correlation_id.get()
        
    @staticmethod
    def clear():
        """Clear current correlation ID"""
        _correlation_id.set(None)