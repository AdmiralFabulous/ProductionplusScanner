"""
Observability Module - Phase 3

Provides:
- Structured JSON logging (structlog)
- Prometheus metrics export
- Backup management

Usage:
    from observability import configure_logging, get_logger, get_metrics

    configure_logging()
    logger = get_logger(__name__)
    logger.info("Processing order", order_id="SDS-123")

Author: Claude
Date: 2026-02-01
"""

from .logging_config import configure_logging, get_logger
from .metrics import (
    get_metrics,
    update_queue_metrics,
    record_order_complete,
    record_order_failed,
    ORDERS_TOTAL,
    PROCESSING_TIME,
    QUEUE_LENGTH,
    ACTIVE_WORKERS,
    DLQ_SIZE,
)

__all__ = [
    "configure_logging",
    "get_logger",
    "get_metrics",
    "update_queue_metrics",
    "record_order_complete",
    "record_order_failed",
    "ORDERS_TOTAL",
    "PROCESSING_TIME",
    "QUEUE_LENGTH",
    "ACTIVE_WORKERS",
    "DLQ_SIZE",
]
