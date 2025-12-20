"""
Logging configuration for MAPIT AI.

Provides structured logging with consistent formatting, multiple output handlers,
and request correlation IDs for tracing.
"""

import logging
import logging.handlers
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional
import threading

# Thread-local storage for request correlation IDs
_local = threading.local()


def get_correlation_id() -> str:
    """Get the current correlation ID or generate a new one."""
    if not hasattr(_local, 'correlation_id'):
        _local.correlation_id = str(uuid.uuid4())[:8]
    return _local.correlation_id


def set_correlation_id(correlation_id: Optional[str] = None) -> str:
    """Set a correlation ID for the current thread."""
    _local.correlation_id = correlation_id or str(uuid.uuid4())[:8]
    return _local.correlation_id


def clear_correlation_id():
    """Clear the correlation ID for the current thread."""
    if hasattr(_local, 'correlation_id'):
        delattr(_local, 'correlation_id')


class CorrelationIdFilter(logging.Filter):
    """Add correlation ID to log records."""

    def filter(self, record):
        record.correlation_id = get_correlation_id()
        return True


class StructuredFormatter(logging.Formatter):
    """Structured log formatter for production-ready logging."""

    def __init__(self, include_extras: bool = True):
        self.include_extras = include_extras
        super().__init__()

    def format(self, record):
        # Base log format
        timestamp = datetime.utcnow().isoformat() + 'Z'
        correlation_id = getattr(record, 'correlation_id', 'N/A')

        # Build log message
        base_message = (
            f"{timestamp} | {record.levelname:8} | "
            f"{correlation_id} | {record.name} | {record.getMessage()}"
        )

        # Add exception info if present
        if record.exc_info:
            base_message += f"\n{self.formatException(record.exc_info)}"

        return base_message


def setup_logging(
    log_level: str = "INFO",
    log_dir: str = "./log",
    log_file: str = "mapit.log",
    console_output: bool = True,
    max_bytes: int = 10 * 1024 * 1024,  # 10 MB
    backup_count: int = 5
) -> logging.Logger:
    """
    Configure structured logging for MAPIT AI.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Directory for log files
        log_file: Name of the log file
        console_output: Whether to output to console
        max_bytes: Maximum size of log file before rotation
        backup_count: Number of backup files to keep

    Returns:
        The root logger configured for MAPIT
    """
    # Create log directory
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    # Get root logger for MAPIT
    root_logger = logging.getLogger('mapit')
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Clear any existing handlers
    root_logger.handlers.clear()

    # Create formatter
    formatter = StructuredFormatter()

    # Add correlation ID filter
    correlation_filter = CorrelationIdFilter()

    # File handler with rotation
    file_handler = logging.handlers.RotatingFileHandler(
        log_path / log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    file_handler.addFilter(correlation_filter)
    root_logger.addHandler(file_handler)

    # Console handler
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        console_handler.addFilter(correlation_filter)
        root_logger.addHandler(console_handler)

    # Also configure the root Python logger
    logging.getLogger().setLevel(logging.WARNING)

    root_logger.info("MAPIT logging initialized", extra={
        'log_level': log_level,
        'log_file': str(log_path / log_file)
    })

    return root_logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger for a specific module.

    Args:
        name: Name of the module (typically __name__)

    Returns:
        Logger instance for the module

    Example:
        logger = get_logger(__name__)
        logger.info("Processing query", extra={'query_length': len(query)})
    """
    # Create child logger under mapit namespace
    if name.startswith('mapit.'):
        return logging.getLogger(name)
    return logging.getLogger(f'mapit.{name}')


class LogContext:
    """
    Context manager for logging with timing.

    Example:
        with LogContext(logger, "Processing query"):
            result = process_query(query)
    """

    def __init__(self, logger: logging.Logger, operation: str, level: int = logging.INFO):
        self.logger = logger
        self.operation = operation
        self.level = level
        self.start_time = None

    def __enter__(self):
        self.start_time = datetime.utcnow()
        self.logger.log(self.level, f"Starting: {self.operation}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration_ms = (datetime.utcnow() - self.start_time).total_seconds() * 1000

        if exc_type is None:
            self.logger.log(
                self.level,
                f"Completed: {self.operation} in {duration_ms:.2f}ms"
            )
        else:
            self.logger.error(
                f"Failed: {self.operation} after {duration_ms:.2f}ms - {exc_val}",
                exc_info=True
            )

        return False  # Don't suppress exceptions
