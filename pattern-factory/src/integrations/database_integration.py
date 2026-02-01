#!/usr/bin/env python3
"""
SameDaySuits Database Integration - Supabase

Integrates with Supabase (local or cloud) for:
1. Pulling new orders from website
2. Storing production status
3. Tracking order lifecycle

Supports:
- Local Supabase (development)
- Cloud Supabase (production)

Database Schema:
----------------
CREATE TABLE orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id TEXT UNIQUE NOT NULL,
    customer_id TEXT NOT NULL,
    customer_email TEXT,
    garment_type TEXT NOT NULL,
    fit_type TEXT DEFAULT 'regular',
    priority TEXT DEFAULT 'normal',
    quantity INTEGER DEFAULT 1,
    notes TEXT,

    -- Measurements (stored as JSONB for flexibility)
    measurements JSONB NOT NULL,

    -- Production status
    status TEXT DEFAULT 'pending',  -- pending, processing, queued, cutting, complete, shipped, error

    -- Production results
    plt_file TEXT,
    fabric_length_cm FLOAT,
    fabric_utilization FLOAT,
    piece_count INTEGER,
    processing_time_ms FLOAT,
    job_id TEXT,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    processed_at TIMESTAMPTZ,
    shipped_at TIMESTAMPTZ,

    -- Errors/warnings
    errors JSONB,
    warnings JSONB
);

-- Index for polling new orders
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_orders_created ON orders(created_at);

Author: Claude
Date: 2026-01-30
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum

# Supabase client
from supabase import create_client, Client

# Import our production modules
from samedaysuits_api import (
    SameDaySuitsAPI,
    Order,
    GarmentType,
    FitType,
    CustomerMeasurements,
    ProductionResult,
)
from cutter_queue import CutterQueue, JobPriority

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class OrderStatus(Enum):
    """Order status in database."""

    PENDING = "pending"  # New order, not yet processed
    PROCESSING = "processing"  # Being processed by pipeline
    QUEUED = "queued"  # In cutter queue
    CUTTING = "cutting"  # Being cut
    COMPLETE = "complete"  # Cut complete, ready for sewing
    SHIPPED = "shipped"  # Sent to customer
    ERROR = "error"  # Processing failed


@dataclass
class DatabaseConfig:
    """Supabase configuration."""

    url: str
    key: str
    is_local: bool = True

    @classmethod
    def from_env(cls) -> "DatabaseConfig":
        """Load config from environment variables."""
        url = os.getenv("SUPABASE_URL", "http://localhost:54321")
        key = os.getenv("SUPABASE_KEY", "")
        is_local = "localhost" in url or "127.0.0.1" in url

        if not key:
            # For local dev, use the default anon key
            if is_local:
                key = os.getenv(
                    "SUPABASE_ANON_KEY",
                    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6ImFub24iLCJleHAiOjE5ODM4MTI5OTZ9.CRXP1A7WOeoJeXxjNni43kdQwgnWNReilDMblYTn_I0",
                )
            else:
                raise ValueError("SUPABASE_KEY environment variable required for cloud")

        return cls(url=url, key=key, is_local=is_local)


class OrderDatabase:
    """
    Database integration for SameDaySuits orders.

    Example usage:
        # Initialize
        db = OrderDatabase()

        # Poll for new orders
        new_orders = db.get_pending_orders()

        # Process and update
        for order_data in new_orders:
            result = api.process_order(order)
            db.update_order_status(order_data['id'], OrderStatus.COMPLETE, result)
    """

    def __init__(self, config: Optional[DatabaseConfig] = None):
        """
        Initialize database connection.

        Args:
            config: Supabase configuration. If None, loads from environment.
        """
        self.config = config or DatabaseConfig.from_env()

        try:
            self.client: Client = create_client(self.config.url, self.config.key)
            logger.info(f"Connected to Supabase at {self.config.url}")
            logger.info(f"Mode: {'Local' if self.config.is_local else 'Cloud'}")
        except Exception as e:
            logger.error(f"Failed to connect to Supabase: {e}")
            self.client = None

    @property
    def is_connected(self) -> bool:
        """Check if database is connected."""
        return self.client is not None

    def get_pending_orders(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get orders with status 'pending' (ready for processing).

        Args:
            limit: Maximum number of orders to return

        Returns:
            List of order dictionaries
        """
        if not self.is_connected:
            logger.warning("Database not connected")
            return []

        try:
            response = (
                self.client.table("orders")
                .select("*")
                .eq("status", OrderStatus.PENDING.value)
                .order("created_at")
                .limit(limit)
                .execute()
            )

            logger.info(f"Found {len(response.data)} pending orders")
            return response.data

        except Exception as e:
            logger.error(f"Error fetching pending orders: {e}")
            return []

    def get_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific order by order_id."""
        if not self.is_connected:
            return None

        try:
            response = (
                self.client.table("orders")
                .select("*")
                .eq("order_id", order_id)
                .single()
                .execute()
            )

            return response.data

        except Exception as e:
            logger.error(f"Error fetching order {order_id}: {e}")
            return None

    def update_order_status(
        self,
        order_id: str,
        status: OrderStatus,
        production_result: Optional[Union[ProductionResult, Dict]] = None,
        job_id: Optional[str] = None,
    ) -> bool:
        """
        Update order status and production results.

        Args:
            order_id: Order ID to update
            status: New status
            production_result: Results from production pipeline
            job_id: Cutter queue job ID

        Returns:
            True if update succeeded
        """
        if not self.is_connected:
            return False

        try:
            update_data = {
                "status": status.value,
            }

            if production_result:
                # Handle both ProductionResult objects and dicts
                if isinstance(production_result, dict):
                    # It's a dict - access fields directly
                    update_data.update(
                        {
                            "plt_file": production_result.get("plt_file"),
                            "fabric_length_cm": production_result.get(
                                "fabric_length_cm"
                            ),
                            "fabric_utilization": production_result.get(
                                "fabric_utilization"
                            ),
                            "piece_count": production_result.get("piece_count"),
                            "processing_time_ms": production_result.get(
                                "processing_time_ms"
                            ),
                            "errors": production_result.get("errors"),
                            "warnings": production_result.get("warnings"),
                            "processed_at": datetime.now().isoformat(),
                        }
                    )
                else:
                    # It's a ProductionResult object - access attributes
                    update_data.update(
                        {
                            "plt_file": str(production_result.plt_file)
                            if production_result.plt_file
                            else None,
                            "fabric_length_cm": production_result.fabric_length_cm,
                            "fabric_utilization": production_result.fabric_utilization,
                            "piece_count": production_result.piece_count,
                            "processing_time_ms": production_result.processing_time_ms,
                            "errors": production_result.errors
                            if production_result.errors
                            else None,
                            "warnings": production_result.warnings
                            if production_result.warnings
                            else None,
                            "processed_at": datetime.now().isoformat(),
                        }
                    )

            if job_id:
                update_data["job_id"] = job_id

            response = (
                self.client.table("orders")
                .update(update_data)
                .eq("order_id", order_id)
                .execute()
            )

            logger.info(f"Updated order {order_id} to status: {status.value}")
            return True

        except Exception as e:
            logger.error(f"Error updating order {order_id}: {e}")
            return False

    def create_order(self, order_data: Dict[str, Any]) -> Optional[str]:
        """
        Create a new order in the database.

        Args:
            order_data: Order data dictionary

        Returns:
            Created order ID or None if failed
        """
        if not self.is_connected:
            return None

        try:
            response = self.client.table("orders").insert(order_data).execute()

            if response.data:
                order_id = response.data[0].get("order_id")
                logger.info(f"Created order: {order_id}")
                return order_id
            return None

        except Exception as e:
            logger.error(f"Error creating order: {e}")
            return None

    def save_qc_report(self, order_id: str, qc_report: dict) -> bool:
        """Save QC report to database"""
        try:
            data = {
                "order_id": order_id,
                "passed": qc_report.get("status") == "PASSED",
                "error_count": len(qc_report.get("errors", [])),
                "warning_count": len(qc_report.get("warnings", [])),
                "checks": json.dumps(qc_report.get("checks", {})),
                "overall_score": qc_report.get("overall_score", "Unknown"),
            }

            result = self.client.table("qc_reports").insert(data).execute()
            return len(result.data) > 0
        except Exception as e:
            logger.error(f"Failed to save QC report: {e}")
            return False

    def convert_db_order_to_api_order(self, db_order: Dict[str, Any]) -> Order:
        """
        Convert database order record to API Order object.

        Args:
            db_order: Order dictionary from database

        Returns:
            Order object for API
        """
        measurements = db_order.get("measurements", {})

        return Order(
            order_id=db_order["order_id"],
            customer_id=db_order.get("customer_id", "unknown"),
            garment_type=GarmentType(db_order["garment_type"]),
            fit_type=FitType(db_order.get("fit_type", "regular")),
            measurements=CustomerMeasurements(
                chest_cm=measurements.get("chest_cm", measurements.get("chest", 100)),
                waist_cm=measurements.get("waist_cm", measurements.get("waist", 85)),
                hip_cm=measurements.get("hip_cm", measurements.get("hip", 100)),
                shoulder_width_cm=measurements.get("shoulder_width_cm"),
                arm_length_cm=measurements.get("arm_length_cm"),
                inseam_cm=measurements.get("inseam_cm"),
                source=measurements.get("source", "database"),
            ),
            quantity=db_order.get("quantity", 1),
            notes=db_order.get("notes", ""),
        )


class OrderSyncService:
    """
    Service that polls database for new orders and processes them.

    This is the main integration point between the website database
    and the production pipeline.

    Example usage:
        sync = OrderSyncService()
        sync.run_once()  # Process all pending orders

        # Or run continuously
        sync.run_loop(interval_seconds=30)
    """

    def __init__(
        self,
        db: Optional[OrderDatabase] = None,
        api: Optional[SameDaySuitsAPI] = None,
        queue: Optional[CutterQueue] = None,
    ):
        """
        Initialize the sync service.

        Args:
            db: Database connection
            api: Production API
            queue: Cutter queue
        """
        self.db = db or OrderDatabase()
        self.api = api or SameDaySuitsAPI()
        self.queue = queue or CutterQueue()

        self._running = False

    def process_order(self, db_order: Dict[str, Any]) -> bool:
        """
        Process a single order from the database.

        Args:
            db_order: Order record from database

        Returns:
            True if processing succeeded
        """
        order_id = db_order.get("order_id")
        logger.info(f"Processing order: {order_id}")

        try:
            # Mark as processing
            self.db.update_order_status(order_id, OrderStatus.PROCESSING)

            # Convert to API order
            order = self.db.convert_db_order_to_api_order(db_order)

            # Process through pipeline
            result = self.api.process_order(order)

            if result.success:
                # Add to cutter queue
                priority_str = db_order.get("priority", "normal")
                priority_map = {
                    "rush": JobPriority.RUSH,
                    "high": JobPriority.HIGH,
                    "normal": JobPriority.NORMAL,
                    "low": JobPriority.LOW,
                }
                priority = priority_map.get(priority_str, JobPriority.NORMAL)

                # Load metadata for queue
                metadata = None
                if result.metadata_file and result.metadata_file.exists():
                    with open(result.metadata_file) as f:
                        metadata = json.load(f)

                job = self.queue.add_job(
                    order_id,
                    result.plt_file,
                    priority=priority,
                    metadata=metadata,
                )

                # Update database with success
                self.db.update_order_status(
                    order_id,
                    OrderStatus.QUEUED,
                    production_result=result,
                    job_id=job.job_id,
                )

                logger.info(f"Order {order_id} queued as job {job.job_id}")
                return True

            else:
                # Update database with failure
                self.db.update_order_status(
                    order_id,
                    OrderStatus.ERROR,
                    production_result=result,
                )

                logger.error(f"Order {order_id} failed: {result.errors}")
                return False

        except Exception as e:
            logger.exception(f"Error processing order {order_id}")

            # Create a failure result
            failure_result = ProductionResult(
                success=False,
                order_id=order_id,
                plt_file=None,
                metadata_file=None,
                fabric_length_cm=0,
                fabric_utilization=0,
                piece_count=0,
                processing_time_ms=0,
                errors=[str(e)],
                warnings=[],
            )

            self.db.update_order_status(
                order_id,
                OrderStatus.ERROR,
                production_result=failure_result,
            )

            return False

    def run_once(self) -> Dict[str, int]:
        """
        Process all pending orders once.

        Returns:
            Dictionary with counts: processed, succeeded, failed
        """
        logger.info("Running order sync...")

        # Get pending orders
        pending_orders = self.db.get_pending_orders()

        stats = {
            "processed": 0,
            "succeeded": 0,
            "failed": 0,
        }

        for db_order in pending_orders:
            stats["processed"] += 1

            if self.process_order(db_order):
                stats["succeeded"] += 1
            else:
                stats["failed"] += 1

        logger.info(
            f"Sync complete: {stats['processed']} processed, "
            f"{stats['succeeded']} succeeded, {stats['failed']} failed"
        )

        return stats

    def run_loop(self, interval_seconds: float = 30.0):
        """
        Run continuously, polling for new orders.

        Args:
            interval_seconds: Seconds between polls
        """
        import time

        self._running = True
        logger.info(f"Starting order sync loop (interval: {interval_seconds}s)")

        while self._running:
            try:
                self.run_once()
            except Exception as e:
                logger.error(f"Error in sync loop: {e}")

            time.sleep(interval_seconds)

    def stop(self):
        """Stop the sync loop."""
        self._running = False
        logger.info("Stopping order sync loop")

    def retry_failed_order(self, order_id: str) -> bool:
        """Retry a failed order with exponential backoff"""
        import time

        try:
            order = self.db.get_order(order_id)
            if not order:
                return False

            # Check retry count
            retry_count = order.get("retry_count", 0)
            if retry_count >= 3:
                logger.error(f"Order {order_id} exceeded max retries")
                return False

            # Calculate backoff delay
            delay = min(2**retry_count, 300)  # Max 5 minutes
            logger.info(
                f"Retrying order {order_id} in {delay}s (attempt {retry_count + 1})"
            )

            # Update retry count
            self.db.client.table("orders").update(
                {
                    "retry_count": retry_count + 1,
                    "next_retry_at": (
                        datetime.now() + timedelta(seconds=delay)
                    ).isoformat(),
                }
            ).eq("order_id", order_id).execute()

            # Schedule retry
            time.sleep(delay)
            return self.process_order(order)

        except Exception as e:
            logger.error(f"Failed to retry order {order_id}: {e}")
            return False


def create_test_order(db: OrderDatabase) -> Optional[str]:
    """Create a test order in the database."""
    import uuid

    order_data = {
        "order_id": f"TEST-{uuid.uuid4().hex[:8].upper()}",
        "customer_id": "CUST-TEST",
        "customer_email": "test@example.com",
        "garment_type": "tee",
        "fit_type": "regular",
        "priority": "normal",
        "quantity": 1,
        "notes": "Test order from database integration",
        "measurements": {
            "chest_cm": 102,
            "waist_cm": 88,
            "hip_cm": 100,
            "source": "test",
        },
        "status": "pending",
    }

    return db.create_order(order_data)


# SQL for creating the orders table (run in Supabase SQL editor)
SCHEMA_SQL = """
-- Orders table for SameDaySuits
CREATE TABLE IF NOT EXISTS orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id TEXT UNIQUE NOT NULL,
    customer_id TEXT NOT NULL,
    customer_email TEXT,
    garment_type TEXT NOT NULL,
    fit_type TEXT DEFAULT 'regular',
    priority TEXT DEFAULT 'normal',
    quantity INTEGER DEFAULT 1,
    notes TEXT,
    
    -- Measurements (stored as JSONB for flexibility)
    measurements JSONB NOT NULL,
    
    -- Production status
    status TEXT DEFAULT 'pending',
    
    -- Production results
    plt_file TEXT,
    fabric_length_cm FLOAT,
    fabric_utilization FLOAT,
    piece_count INTEGER,
    processing_time_ms FLOAT,
    job_id TEXT,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    processed_at TIMESTAMPTZ,
    shipped_at TIMESTAMPTZ,
    
    -- Errors/warnings
    errors JSONB,
    warnings JSONB
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_orders_created ON orders(created_at);
CREATE INDEX IF NOT EXISTS idx_orders_customer ON orders(customer_id);

-- QC Reports table
CREATE TABLE IF NOT EXISTS qc_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id TEXT REFERENCES orders(order_id),
    passed BOOLEAN NOT NULL,
    error_count INTEGER DEFAULT 0,
    warning_count INTEGER DEFAULT 0,
    checks JSONB,
    overall_score TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Cutter Jobs table
CREATE TABLE IF NOT EXISTS cutter_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id TEXT UNIQUE NOT NULL,
    order_id TEXT REFERENCES orders(order_id),
    status TEXT DEFAULT 'pending',
    priority INTEGER DEFAULT 3,
    plt_file TEXT,
    fabric_length_cm FLOAT,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Fabric Inventory table
CREATE TABLE IF NOT EXISTS fabric_inventory (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    roll_id TEXT UNIQUE NOT NULL,
    fabric_type TEXT,
    length_remaining_cm FLOAT,
    width_cm FLOAT DEFAULT 157.48,
    location TEXT,
    status TEXT DEFAULT 'active',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Order Audit Log
CREATE TABLE IF NOT EXISTS order_audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id TEXT REFERENCES orders(order_id),
    action TEXT NOT NULL,
    old_status TEXT,
    new_status TEXT,
    performed_by TEXT,
    details JSONB,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Enable RLS (Row Level Security) for production
ALTER TABLE orders ENABLE ROW LEVEL SECURITY;

-- Policy: Allow all operations for authenticated users (adjust for production)
CREATE POLICY "Allow all for authenticated" ON orders
    FOR ALL
    USING (true)
    WITH CHECK (true);
"""


def main():
    """CLI for database integration."""
    import argparse
    import time

    parser = argparse.ArgumentParser(
        description="SameDaySuits Database Integration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Check connection
  python database_integration.py status
  
  # Process pending orders once
  python database_integration.py sync
  
  # Run continuous sync loop
  python database_integration.py watch --interval 30
  
  # Create test order
  python database_integration.py test-order
  
  # Show schema SQL
  python database_integration.py schema

Environment Variables:
  SUPABASE_URL - Supabase URL (default: http://localhost:54321)
  SUPABASE_KEY - Supabase API key (required for cloud)
        """,
    )

    parser.add_argument(
        "command",
        choices=["status", "sync", "watch", "test-order", "schema", "pending"],
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=30.0,
        help="Sync interval in seconds (for watch command)",
    )

    args = parser.parse_args()

    if args.command == "schema":
        print("\n" + "=" * 60)
        print("SUPABASE SCHEMA SQL")
        print("=" * 60)
        print("Run this in your Supabase SQL editor:\n")
        print(SCHEMA_SQL)
        return

    # Initialize database
    try:
        db = OrderDatabase()
    except Exception as e:
        print(f"Error connecting to database: {e}")
        print("\nMake sure Supabase is running and environment variables are set:")
        print("  SUPABASE_URL=http://localhost:54321")
        print("  SUPABASE_KEY=<your-anon-key>")
        return

    if args.command == "status":
        print("\n" + "=" * 50)
        print("DATABASE STATUS")
        print("=" * 50)
        print(f"URL:       {db.config.url}")
        print(f"Mode:      {'Local' if db.config.is_local else 'Cloud'}")
        print(f"Connected: {db.is_connected}")

        if db.is_connected:
            pending = db.get_pending_orders(limit=1000)
            print(f"Pending:   {len(pending)} orders")
        print("=" * 50)

    elif args.command == "pending":
        pending = db.get_pending_orders()
        print("\n" + "=" * 80)
        print(f"{'Order ID':<20} {'Garment':<12} {'Priority':<10} {'Created':<20}")
        print("-" * 80)

        for order in pending:
            created = order.get("created_at", "")[:19]
            print(
                f"{order['order_id']:<20} "
                f"{order['garment_type']:<12} "
                f"{order.get('priority', 'normal'):<10} "
                f"{created:<20}"
            )

        print("=" * 80)
        print(f"Total: {len(pending)} pending orders")

    elif args.command == "sync":
        sync = OrderSyncService(db=db)
        stats = sync.run_once()

        print("\n" + "=" * 50)
        print("SYNC COMPLETE")
        print("=" * 50)
        print(f"Processed: {stats['processed']}")
        print(f"Succeeded: {stats['succeeded']}")
        print(f"Failed:    {stats['failed']}")
        print("=" * 50)

    elif args.command == "watch":
        print(f"\nStarting watch mode (interval: {args.interval}s)")
        print("Press Ctrl+C to stop\n")

        sync = OrderSyncService(db=db)

        try:
            sync.run_loop(interval_seconds=args.interval)
        except KeyboardInterrupt:
            print("\nStopping...")
            sync.stop()

    elif args.command == "test-order":
        order_id = create_test_order(db)
        if order_id:
            print(f"\nCreated test order: {order_id}")
            print("Run 'python database_integration.py sync' to process it")
        else:
            print("\nFailed to create test order")
            print("Make sure the 'orders' table exists in your database")
            print("Run 'python database_integration.py schema' to see the SQL")


if __name__ == "__main__":
    main()
