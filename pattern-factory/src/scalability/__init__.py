#!/usr/bin/env python3
"""
SameDaySuits Scalability Module

Provides distributed processing capabilities for the Pattern Factory:
- Redis-backed order queue with priority support
- Template caching for reduced I/O
- Dead-letter queue for failed orders
- Graceful fallback to synchronous processing

Components:
- queue_manager: Distributed order queue with Redis
- cache_manager: Template and result caching

Author: Claude
Date: 2026-01-31
"""

from .queue_manager import (
    OrderQueue,
    QueueStats,
    JobStatus,
    JobPriority,
    OrderData,
)
from .cache_manager import (
    TemplateCache,
    get_template_cache,
)

__all__ = [
    # Queue
    "OrderQueue",
    "QueueStats",
    "JobStatus",
    "JobPriority",
    "OrderData",
    # Cache
    "TemplateCache",
    "get_template_cache",
]

__version__ = "1.0.0"
