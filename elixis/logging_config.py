"""Structured logging configuration for Elixis.

Provides JSON logging for production observability.
"""

import json
import logging
import logging.handlers
import os
import sys
from datetime import datetime, timezone
from typing import Optional
import threading


# Log format configuration
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
LOG_FORMAT = os.environ.get("LOG_FORMAT", "json")  # "json" or "text"
MAX_LOG_SIZE = 10 * 1024 * 1024  # 10MB
MAX_LOG_BACKUPS = 5


class JSONFormatter(logging.Formatter):
    """JSON log formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields
        for key, value in record.__dict__.items():
            if key not in (
                "name", "msg", "args", "levelname", "levelno", "pathname",
                "filename", "module", "exc_info", "exc_text", "stack_info",
                "lineno", "funcName", "created", "msecs", "relativeCreated",
                "thread", "threadName", "processName", "process", "getMessage",
            ):
                log_data[key] = value

        return json.dumps(log_data, default=str)


class TextFormatter(logging.Formatter):
    """Human-readable text formatter for development."""

    def __init__(self):
        super().__init__(
            fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )


def get_logger(name: str) -> logging.Logger:
    """Get a configured logger.

    Args:
        name: Logger name

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.propagate = False

    # Avoid reconfiguring if already set up
    if logger.handlers:
        if not any(isinstance(filter_, RequestContextFilter) for filter_ in logger.filters):
            logger.addFilter(RequestContextFilter())
        return logger

    logger.setLevel(getattr(logging, LOG_LEVEL))
    logger.addFilter(RequestContextFilter())

    # Console handler
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.DEBUG)
    console.addFilter(RequestContextFilter())

    if LOG_FORMAT == "json":
        console.setFormatter(JSONFormatter())
    else:
        console.setFormatter(TextFormatter())

    logger.addHandler(console)

    # File handler (rotating)
    try:
        log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".elixis", "logs")
        os.makedirs(log_dir, exist_ok=True)

        file_handler = logging.handlers.RotatingFileHandler(
            os.path.join(log_dir, "elixis.log"),
            maxBytes=MAX_LOG_SIZE,
            backupCount=MAX_LOG_BACKUPS,
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(JSONFormatter())
        file_handler.addFilter(RequestContextFilter())
        logger.addHandler(file_handler)
    except OSError as exc:
        logger.warning("File logging unavailable; continuing with console logging only: %s", exc)

    return logger


# Request context for correlation IDs
_request_context = threading.local()


def set_request_id(request_id: str):
    """Set current request correlation ID."""
    _request_context.request_id = request_id


def get_request_id() -> Optional[str]:
    """Get current request correlation ID."""
    return getattr(_request_context, "request_id", None)


def clear_request_id():
    """Clear current request correlation ID."""
    _request_context.request_id = None


class RequestContextFilter(logging.Filter):
    """Filter that adds request context to log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id()
        record.service = "elixis"
        return True


def configure_root_logger():
    """Configure the root logger with all handlers."""
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, LOG_LEVEL))

    # Clear existing handlers
    root_logger.handlers = []

    # Add context filter
    context_filter = RequestContextFilter()
    root_logger.addFilter(context_filter)

    # Console handler
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.DEBUG)
    console.addFilter(context_filter)

    if LOG_FORMAT == "json":
        console.setFormatter(JSONFormatter())
    else:
        console.setFormatter(TextFormatter())

    root_logger.addHandler(console)

    # File handler
    try:
        log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".elixis", "logs")
        os.makedirs(log_dir, exist_ok=True)

        file_handler = logging.handlers.RotatingFileHandler(
            os.path.join(log_dir, "elixis.log"),
            maxBytes=MAX_LOG_SIZE,
            backupCount=MAX_LOG_BACKUPS,
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(JSONFormatter())
        file_handler.addFilter(context_filter)
        root_logger.addHandler(file_handler)
    except OSError as exc:
        root_logger.warning("File logging unavailable; continuing with console logging only: %s", exc)


# Structured log event helpers
# NOTE: Pipeline and request logging is handled by elixis/traces.py
# which writes to both JSONL files and the structured logger.
