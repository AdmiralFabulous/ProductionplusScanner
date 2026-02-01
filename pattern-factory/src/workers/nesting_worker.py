#!/usr/bin/env python3
"""
Nesting Worker - Scalable Order Processing Worker

Long-running process that:
1. Polls Redis queue for new orders
2. Processes orders through the production pipeline
3. Handles failures with retry logic
4. Reports health via heartbeat

Features:
- Graceful shutdown on SIGTERM (Docker-friendly)
- Automatic retry with exponential backoff
- Dead-letter queue after 3 failures
- Worker identification for debugging

Usage:
    # Run directly
    python -m src.workers.nesting_worker

    # With custom worker ID
    WORKER_ID=worker-1 python -m src.workers.nesting_worker

    # Scale with Docker Compose
    docker-compose up -d --scale nesting-worker=3

Author: Claude
Date: 2026-01-31
"""

import os
import sys
import signal
import logging
import time
import traceback
from uuid import uuid4
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "core"))

from scalability.queue_manager import OrderQueue, JobStatus, JobPriority

# Import cutter queue for auto-submission
try:
    from core.resilient_cutter_queue import ResilientCutterQueue, CutterPriority

    CUTTER_QUEUE_AVAILABLE = True
except ImportError:
    CUTTER_QUEUE_AVAILABLE = False

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - [%(levelname)s] - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("nesting-worker")


class NestingWorker:
    """
    Order processing worker with queue integration.

    Handles:
    - Dequeuing orders from Redis
    - Processing through production pipeline
    - Auto-submitting to cutter queue
    - Reporting success/failure
    - Graceful shutdown
    """

    def __init__(self, worker_id: str = None):
        """
        Initialize the worker.

        Args:
            worker_id: Optional identifier for this worker instance
        """
        self.worker_id = worker_id or f"worker-{uuid4().hex[:8]}"
        self.shutdown_requested = False
        self.orders_processed = 0
        self.orders_failed = 0
        self.current_order_id = None
        self.start_time = None

        # Initialize queue connection
        self.queue = OrderQueue()

        # Initialize cutter queue if available
        self.cutter_queue = None
        if CUTTER_QUEUE_AVAILABLE:
            try:
                self.cutter_queue = ResilientCutterQueue()
                logger.info("Cutter queue initialized - auto-submit enabled")
            except Exception as e:
                logger.warning(f"Cutter queue unavailable: {e}")

        # Load production modules
        self._load_production_modules()

    def _load_production_modules(self):
        """Load production pipeline modules."""
        try:
            from samedaysuits_api import (
                SameDaySuitsAPI,
                Order,
                GarmentType,
                FitType,
                CustomerMeasurements,
            )

            self._api = SameDaySuitsAPI()
            self._Order = Order
            self._GarmentType = GarmentType
            self._FitType = FitType
            self._CustomerMeasurements = CustomerMeasurements
            logger.info("Production modules loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load production modules: {e}")
            raise

    def _setup_signal_handlers(self):
        """Setup graceful shutdown handlers."""
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        signal.signal(signal.SIGINT, self._handle_shutdown)

    def _handle_shutdown(self, signum, frame):
        """Handle shutdown signal gracefully."""
        logger.info(f"Received shutdown signal ({signum}), finishing current order...")
        self.shutdown_requested = True

    def run(self):
        """
        Main worker loop.

        Continuously polls the queue and processes orders until shutdown.
        """
        self._setup_signal_handlers()
        self.start_time = datetime.utcnow()

        logger.info(f"Worker {self.worker_id} starting...")
        logger.info(f"Redis available: {self.queue.is_available}")

        if not self.queue.is_available:
            logger.error("Redis not available - worker cannot start")
            return

        while not self.shutdown_requested:
            try:
                # Send heartbeat
                self.queue.worker_heartbeat(self.worker_id)

                # Try to get an order
                order_data = self.queue.dequeue(timeout=5)

                if order_data is None:
                    # No orders available, wait briefly
                    continue

                # Process the order
                self._process_order(order_data)

            except KeyboardInterrupt:
                logger.info("Keyboard interrupt received")
                self.shutdown_requested = True
            except Exception as e:
                logger.error(f"Worker loop error: {e}")
                traceback.print_exc()
                time.sleep(5)  # Backoff on unexpected errors

        # Shutdown complete
        self._log_stats()
        logger.info(f"Worker {self.worker_id} shutdown complete")

    def _process_order(self, order_data: Dict[str, Any]):
        """
        Process a single order through the production pipeline.

        Args:
            order_data: Order data from queue
        """
        order_id = order_data.get("order_id", "unknown")
        self.current_order_id = order_id
        start_time = time.time()

        logger.info(f"Processing order {order_id}")
        logger.debug(f"Order data: {order_data}")

        try:
            # Convert dict to Order object
            order = self._create_order_object(order_data)

            # Process through pipeline
            logger.info(f"Starting pipeline for {order_id}...")
            result = self._api.process_order(order)

            processing_time = time.time() - start_time

            if result.success:
                # Mark complete
                self.queue.complete(
                    order_id,
                    {
                        "success": True,
                        "plt_file": str(result.plt_file) if result.plt_file else None,
                        "fabric_length_cm": result.fabric_length_cm,
                        "fabric_utilization": result.fabric_utilization,
                        "piece_count": result.piece_count,
                        "processing_time_ms": result.processing_time_ms,
                        "worker_id": self.worker_id,
                        "completed_at": datetime.utcnow().isoformat(),
                    },
                )

                # Auto-submit to cutter queue if available
                if self.cutter_queue and result.plt_file:
                    self._submit_to_cutter(order_id, result.plt_file, order_data)

                self.orders_processed += 1
                logger.info(
                    f"Order {order_id} completed: "
                    f"{result.fabric_utilization:.1f}% utilization, "
                    f"{result.piece_count} pieces, "
                    f"{processing_time:.1f}s"
                )
            else:
                # Processing failed
                error_msg = (
                    "; ".join(result.errors) if result.errors else "Unknown error"
                )
                self._handle_failure(order_id, error_msg)

        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e)}"
            logger.error(f"Order {order_id} exception: {error_msg}")
            traceback.print_exc()
            self._handle_failure(order_id, error_msg)
        finally:
            self.current_order_id = None

    def _create_order_object(self, order_data: Dict[str, Any]):
        """Convert order dict to Order object."""
        # Handle nested measurements
        measurements = order_data.get("measurements", {})
        if isinstance(measurements, dict):
            measurements_obj = self._CustomerMeasurements(
                chest_cm=measurements.get("chest_cm", 100),
                waist_cm=measurements.get("waist_cm", 85),
                hip_cm=measurements.get("hip_cm", 100),
                shoulder_width_cm=measurements.get("shoulder_width_cm"),
                arm_length_cm=measurements.get("arm_length_cm"),
                inseam_cm=measurements.get("inseam_cm"),
                source=measurements.get("source", "queue"),
            )
        else:
            measurements_obj = measurements

        # Parse garment type
        garment_str = order_data.get("garment_type", "tee")
        try:
            garment_type = self._GarmentType(garment_str)
        except ValueError:
            garment_type = self._GarmentType.TEE

        # Parse fit type
        fit_str = order_data.get("fit_type", "regular")
        try:
            fit_type = self._FitType(fit_str)
        except ValueError:
            fit_type = self._FitType.REGULAR

        return self._Order(
            order_id=order_data.get("order_id"),
            customer_id=order_data.get("customer_id", "worker-queue"),
            garment_type=garment_type,
            fit_type=fit_type,
            measurements=measurements_obj,
            quantity=order_data.get("quantity", 1),
            notes=order_data.get("notes", ""),
        )

    def _submit_to_cutter(
        self, order_id: str, plt_file: Path, order_data: Dict[str, Any]
    ):
        """
        Submit completed PLT file to cutter queue.

        Args:
            order_id: Order identifier
            plt_file: Path to PLT file
            order_data: Original order data (for priority hints)
        """
        try:
            # Determine priority based on order data
            priority_str = order_data.get("priority", "normal").lower()
            if CUTTER_QUEUE_AVAILABLE:
                from core.resilient_cutter_queue import CutterPriority

                priority_map = {
                    "rush": CutterPriority.RUSH,
                    "high": CutterPriority.HIGH,
                    "normal": CutterPriority.NORMAL,
                    "low": CutterPriority.LOW,
                }
                priority = priority_map.get(priority_str, CutterPriority.NORMAL)
            else:
                priority = None

            # Submit to cutter queue
            job_id = self.cutter_queue.add_job(
                order_id=order_id,
                plt_file=str(plt_file),
                priority=priority,
            )

            logger.info(f"Order {order_id} submitted to cutter queue: job_id={job_id}")

        except Exception as e:
            # Log but don't fail the order - cutter queue is optional
            logger.warning(f"Failed to submit {order_id} to cutter queue: {e}")

    def _handle_failure(self, order_id: str, error: str):
        """Handle order processing failure."""
        self.orders_failed += 1
        self.queue.fail(order_id, error)

    def _log_stats(self):
        """Log worker statistics."""
        if self.start_time:
            uptime = (datetime.utcnow() - self.start_time).total_seconds()
            rate = self.orders_processed / (uptime / 3600) if uptime > 0 else 0

            logger.info(
                f"Worker {self.worker_id} stats: "
                f"processed={self.orders_processed}, "
                f"failed={self.orders_failed}, "
                f"uptime={uptime:.0f}s, "
                f"rate={rate:.1f}/hour"
            )


def run_worker(worker_id: Optional[str] = None):
    """
    Entry point for running a worker.

    Args:
        worker_id: Optional worker identifier
    """
    worker = NestingWorker(worker_id)
    worker.run()


# Main entry point
if __name__ == "__main__":
    run_worker()
