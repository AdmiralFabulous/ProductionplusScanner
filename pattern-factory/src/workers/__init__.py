#!/usr/bin/env python3
"""
SameDaySuits Workers Module

Provides scalable background workers for order processing:
- NestingWorker: Processes orders from Redis queue
- Supports horizontal scaling via Docker Compose replicas

Usage:
    # Run worker directly
    python -m src.workers.nesting_worker

    # Scale with Docker Compose
    docker-compose up -d --scale nesting-worker=3

Author: Claude
Date: 2026-01-31
"""

from .nesting_worker import NestingWorker, run_worker

__all__ = [
    "NestingWorker",
    "run_worker",
]
