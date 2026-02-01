"""
Centralized Structured Logging Configuration

Provides JSON-formatted logs for easy parsing by log aggregators (ELK, Loki, etc.).
Supports both structured (production) and console (development) output.

Usage:
    from observability.logging_config import configure_logging, get_logger

    # Call once at startup
    configure_logging(json_format=True, level="INFO")

    # Get logger in any module
    logger = get_logger(__name__)
    logger.info("Processing order", order_id="SDS-123", status="started")

Author: Claude
Date: 2026-02-01
"""

import logging
import sys
import os
from typing import Optional

# Try to import structlog, fall back to standard logging if not available
try:
    import structlog

    STRUCTLOG_AVAILABLE = True
except ImportError:
    STRUCTLOG_AVAILABLE = False


def configure_logging(json_format: Optional[bool] = None, level: str = "INFO"):
    """
    Configure structured logging for all modules.

    Call once at application startup (web_api.py, nesting_worker.py).

    Args:
        json_format: Use JSON output. Default: True in production, False in dev
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    # Auto-detect format based on environment
    if json_format is None:
        env = os.getenv("ENVIRONMENT", "development")
        json_format = env not in ("development", "dev", "local")

    log_level = getattr(logging, level.upper(), logging.INFO)

    if STRUCTLOG_AVAILABLE:
        _configure_structlog(json_format, log_level)
    else:
        _configure_stdlib_logging(log_level)


def _configure_structlog(json_format: bool, log_level: int):
    """Configure structlog with processors."""
    import structlog

    # Common processors
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    # Add format-specific processor
    if json_format:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer(colors=True))

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Also configure stdlib logging for compatibility with third-party libs
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stdout,
    )


def _configure_stdlib_logging(log_level: int):
    """Fallback to standard library logging."""
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stdout,
    )


def get_logger(name: str):
    """
    Get a structured logger with context support.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Structured logger (structlog) or standard logger (fallback)

    Usage:
        logger = get_logger(__name__)
        logger.info("Processing order", order_id="SDS-123", status="started")

        # With context binding
        log = logger.bind(order_id="SDS-123")
        log.info("Step 1 complete")
        log.info("Step 2 complete")  # order_id included automatically
    """
    if STRUCTLOG_AVAILABLE:
        import structlog

        return structlog.get_logger(name)
    else:
        return logging.getLogger(name)


def bind_context(**kwargs):
    """
    Bind context variables to all subsequent log calls in this thread/task.

    Usage:
        bind_context(order_id="SDS-123", worker_id="worker-1")
        logger.info("Processing")  # Includes order_id and worker_id
    """
    if STRUCTLOG_AVAILABLE:
        import structlog

        structlog.contextvars.bind_contextvars(**kwargs)


def clear_context():
    """Clear all bound context variables."""
    if STRUCTLOG_AVAILABLE:
        import structlog

        structlog.contextvars.clear_contextvars()
