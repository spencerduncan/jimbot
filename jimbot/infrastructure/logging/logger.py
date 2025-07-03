"""Logger Module

Structured logging with correlation tracking.
"""

import json
import logging
from datetime import datetime

from .correlation import CorrelationContext


class StructuredLogger(logging.LoggerAdapter):
    """Logger with structured output and correlation tracking"""

    def process(self, msg, kwargs):
        """Add structure to log messages"""
        extra = kwargs.get("extra", {})

        # Add correlation ID if available
        correlation_id = CorrelationContext.get_current()
        if correlation_id:
            extra["correlation_id"] = correlation_id

        # Add timestamp
        extra["timestamp"] = datetime.utcnow().isoformat()

        # Structure the message
        if isinstance(msg, dict):
            extra.update(msg)
            msg = extra.pop("message", "")

        kwargs["extra"] = extra
        return msg, kwargs


def get_logger(name: str) -> StructuredLogger:
    """Get a structured logger instance"""
    base_logger = logging.getLogger(name)
    return StructuredLogger(base_logger, {})


def configure_logging(level: str = "INFO", format_json: bool = True):
    """Configure logging for the application"""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format=(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            if not format_json
            else None
        ),
    )

    if format_json:
        # Configure JSON formatter
        for handler in logging.root.handlers:
            handler.setFormatter(JsonFormatter())


class JsonFormatter(logging.Formatter):
    """Format logs as JSON"""

    def format(self, record):
        log_obj = {
            "timestamp": datetime.utcfromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add extra fields
        for key, value in record.__dict__.items():
            if key not in [
                "name",
                "msg",
                "args",
                "created",
                "filename",
                "funcName",
                "levelname",
                "levelno",
                "lineno",
                "module",
                "msecs",
                "pathname",
                "process",
                "processName",
                "relativeCreated",
                "thread",
                "threadName",
                "getMessage",
            ]:
                log_obj[key] = value

        return json.dumps(log_obj)
