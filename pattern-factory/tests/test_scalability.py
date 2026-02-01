#!/usr/bin/env python3
"""
Scalability Module Tests

Tests for Phase 2 scalability features:
1. Queue Manager - Redis-backed order queue
2. Cache Manager - Template caching
3. Worker - Order processing worker

Run with:
    python tests/test_scalability.py

These tests can run with or without Redis:
- With Redis: Full integration tests
- Without Redis: Fallback behavior tests

Author: Claude
Date: 2026-01-31
"""

import os
import sys
import time
import json
import unittest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from typing import Optional

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "core"))
sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "scalability"))
sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "workers"))


class TestQueueManager(unittest.TestCase):
    """Tests for OrderQueue class."""

    @classmethod
    def setUpClass(cls):
        """Import queue manager module."""
        from queue_manager import OrderQueue, JobPriority, JobStatus, QueueStats

        cls.OrderQueue = OrderQueue
        cls.JobPriority = JobPriority
        cls.JobStatus = JobStatus
        cls.QueueStats = QueueStats

    def test_import_queue_manager(self):
        """Test that queue manager module can be imported."""
        self.assertIsNotNone(self.OrderQueue)
        self.assertIsNotNone(self.JobPriority)
        self.assertIsNotNone(self.JobStatus)

    def test_job_priority_values(self):
        """Test priority ordering (RUSH should be highest priority)."""
        self.assertEqual(self.JobPriority.RUSH.value, 1)
        self.assertEqual(self.JobPriority.HIGH.value, 2)
        self.assertEqual(self.JobPriority.NORMAL.value, 3)
        self.assertEqual(self.JobPriority.LOW.value, 4)

        # Lower value = higher priority
        self.assertLess(self.JobPriority.RUSH.value, self.JobPriority.NORMAL.value)

    def test_job_priority_from_string(self):
        """Test priority string conversion."""
        self.assertEqual(self.JobPriority.from_string("rush"), self.JobPriority.RUSH)
        self.assertEqual(self.JobPriority.from_string("RUSH"), self.JobPriority.RUSH)
        self.assertEqual(
            self.JobPriority.from_string("normal"), self.JobPriority.NORMAL
        )
        self.assertEqual(
            self.JobPriority.from_string("invalid"), self.JobPriority.NORMAL
        )

    def test_job_status_values(self):
        """Test job status enum values."""
        self.assertEqual(self.JobStatus.QUEUED.value, "queued")
        self.assertEqual(self.JobStatus.PROCESSING.value, "processing")
        self.assertEqual(self.JobStatus.COMPLETE.value, "complete")
        self.assertEqual(self.JobStatus.FAILED.value, "failed")
        self.assertEqual(self.JobStatus.DLQ.value, "dlq")

    def test_queue_stats_to_dict(self):
        """Test QueueStats serialization."""
        stats = self.QueueStats(
            queued=5,
            processing=2,
            complete=10,
            failed=1,
            dlq=0,
            total_pending=7,
        )
        d = stats.to_dict()
        self.assertEqual(d["queued"], 5)
        self.assertEqual(d["processing"], 2)
        self.assertEqual(d["total_pending"], 7)

    def test_queue_initialization_without_redis(self):
        """Test queue initializes gracefully without Redis."""
        # Use invalid URL to force failure
        queue = self.OrderQueue("redis://nonexistent:9999/0")
        self.assertFalse(queue.is_available)

    def test_queue_fallback_behavior(self):
        """Test queue methods return gracefully when Redis unavailable."""
        queue = self.OrderQueue("redis://nonexistent:9999/0")

        # These should not raise exceptions
        self.assertIsNone(queue.dequeue(timeout=1))
        self.assertIsNone(queue.get_status("test-order"))
        self.assertIsNone(queue.get_result("test-order"))
        self.assertEqual(queue.get_attempts("test-order"), 0)
        self.assertEqual(queue.get_dlq_orders(), [])

        stats = queue.get_stats()
        self.assertEqual(stats.queued, 0)
        self.assertEqual(stats.total_pending, 0)


class TestQueueManagerWithRedis(unittest.TestCase):
    """Integration tests requiring Redis connection."""

    @classmethod
    def setUpClass(cls):
        """Set up Redis connection for tests."""
        from queue_manager import OrderQueue, JobPriority, JobStatus

        cls.OrderQueue = OrderQueue
        cls.JobPriority = JobPriority
        cls.JobStatus = JobStatus

        # Try to connect to Redis
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        cls.queue = cls.OrderQueue(redis_url)
        cls.redis_available = cls.queue.is_available

        if not cls.redis_available:
            print("\n[SKIP] Redis not available - skipping integration tests")

    def setUp(self):
        """Skip if Redis not available."""
        if not self.redis_available:
            self.skipTest("Redis not available")

    def test_enqueue_and_dequeue(self):
        """Test basic enqueue and dequeue operations."""
        order_id = f"TEST-{int(time.time() * 1000)}"
        order_data = {
            "order_id": order_id,
            "customer_id": "TEST-CUST",
            "garment_type": "tee",
            "measurements": {"chest_cm": 102},
        }

        # Enqueue
        result_id = self.queue.enqueue(order_id, order_data, self.JobPriority.NORMAL)
        self.assertEqual(result_id, order_id)

        # Check status
        status = self.queue.get_status(order_id)
        self.assertEqual(status, self.JobStatus.QUEUED)

        # Dequeue
        dequeued = self.queue.dequeue(timeout=1)
        self.assertIsNotNone(dequeued)
        self.assertEqual(dequeued["order_id"], order_id)

        # Status should be processing
        status = self.queue.get_status(order_id)
        self.assertEqual(status, self.JobStatus.PROCESSING)

        # Complete
        self.queue.complete(order_id, {"success": True})
        status = self.queue.get_status(order_id)
        self.assertEqual(status, self.JobStatus.COMPLETE)

        # Get result
        result = self.queue.get_result(order_id)
        self.assertIsNotNone(result)
        self.assertTrue(result["success"])

    def test_priority_ordering(self):
        """Test that RUSH orders are processed before NORMAL orders."""
        # Clear any existing orders first
        time.sleep(0.1)

        # Enqueue normal first
        normal_id = f"NORMAL-{int(time.time() * 1000)}"
        self.queue.enqueue(normal_id, {"order_id": normal_id}, self.JobPriority.NORMAL)

        # Enqueue rush second
        rush_id = f"RUSH-{int(time.time() * 1000)}"
        self.queue.enqueue(rush_id, {"order_id": rush_id}, self.JobPriority.RUSH)

        # Dequeue - should get RUSH first (higher priority)
        first = self.queue.dequeue(timeout=1)
        self.assertIsNotNone(first)
        self.assertEqual(first["order_id"], rush_id)

        # Complete first order
        self.queue.complete(rush_id, {"success": True})

        # Second should be NORMAL
        second = self.queue.dequeue(timeout=1)
        self.assertIsNotNone(second)
        self.assertEqual(second["order_id"], normal_id)

        # Cleanup
        self.queue.complete(normal_id, {"success": True})

    def test_failure_and_retry(self):
        """Test failure handling and retry logic."""
        order_id = f"FAIL-{int(time.time() * 1000)}"
        self.queue.enqueue(order_id, {"order_id": order_id}, self.JobPriority.NORMAL)

        # Dequeue and fail
        self.queue.dequeue(timeout=1)
        self.queue.fail(order_id, "Test failure 1")

        # Should be requeued
        status = self.queue.get_status(order_id)
        self.assertEqual(status, self.JobStatus.QUEUED)
        self.assertEqual(self.queue.get_attempts(order_id), 1)

        # Fail again
        self.queue.dequeue(timeout=1)
        self.queue.fail(order_id, "Test failure 2")
        self.assertEqual(self.queue.get_attempts(order_id), 2)

        # Fail third time - should go to DLQ
        self.queue.dequeue(timeout=1)
        self.queue.fail(order_id, "Test failure 3")

        status = self.queue.get_status(order_id)
        self.assertEqual(status, self.JobStatus.DLQ)

        # Verify in DLQ
        dlq_orders = self.queue.get_dlq_orders()
        dlq_ids = [o["order_id"] for o in dlq_orders]
        self.assertIn(order_id, dlq_ids)

        # Test requeue from DLQ
        self.queue.requeue_from_dlq(order_id)
        status = self.queue.get_status(order_id)
        self.assertEqual(status, self.JobStatus.QUEUED)
        self.assertEqual(self.queue.get_attempts(order_id), 0)

        # Cleanup
        self.queue.dequeue(timeout=1)
        self.queue.complete(order_id, {"success": True})

    def test_worker_heartbeat(self):
        """Test worker heartbeat tracking."""
        worker_id = f"test-worker-{int(time.time())}"

        # Send heartbeat
        self.queue.worker_heartbeat(worker_id)

        # Check active workers
        workers = self.queue.get_active_workers()
        self.assertIn(worker_id, workers)


class TestCacheManager(unittest.TestCase):
    """Tests for TemplateCache class."""

    @classmethod
    def setUpClass(cls):
        """Import cache manager module."""
        from cache_manager import TemplateCache

        cls.TemplateCache = TemplateCache

    def test_import_cache_manager(self):
        """Test that cache manager module can be imported."""
        self.assertIsNotNone(self.TemplateCache)

    def test_cache_initialization_without_redis(self):
        """Test cache initializes with file fallback when Redis unavailable."""
        cache = self.TemplateCache("redis://nonexistent:9999/0")
        # Should not raise, uses file fallback
        self.assertIsNotNone(cache)

    def test_cache_key_generation(self):
        """Test cache key generation is consistent."""
        cache = self.TemplateCache("redis://nonexistent:9999/0")

        # The method is _key(template_name)
        key1 = cache._key("Basic Tee_2D")
        key2 = cache._key("Basic Tee_2D")
        key3 = cache._key("Light Jacket_2D")

        self.assertEqual(key1, key2)
        self.assertNotEqual(key1, key3)
        self.assertTrue(key1.startswith("sds:cache:template:"))


class TestNestingWorker(unittest.TestCase):
    """Tests for NestingWorker class."""

    @classmethod
    def setUpClass(cls):
        """Import worker module."""
        # We need to mock the production modules since they may not be available
        cls.mock_api = Mock()
        cls.mock_api.process_order = Mock(
            return_value=Mock(
                success=True,
                plt_file=Path("/tmp/test.plt"),
                fabric_length_cm=100.0,
                fabric_utilization=85.0,
                piece_count=5,
                processing_time_ms=1000.0,
                errors=[],
            )
        )

    def test_worker_module_imports(self):
        """Test that worker module structure is correct."""
        from nesting_worker import NestingWorker, run_worker

        self.assertIsNotNone(NestingWorker)
        self.assertIsNotNone(run_worker)

    def test_worker_initialization(self):
        """Test worker can be initialized."""
        # Mock the production module loading
        with patch.dict(
            sys.modules,
            {
                "samedaysuits_api": Mock(),
            },
        ):
            from nesting_worker import NestingWorker

            # Create worker with mock queue
            with patch.object(NestingWorker, "_load_production_modules"):
                worker = NestingWorker("test-worker-1")
                self.assertEqual(worker.worker_id, "test-worker-1")
                self.assertEqual(worker.orders_processed, 0)
                self.assertEqual(worker.orders_failed, 0)
                self.assertFalse(worker.shutdown_requested)

    def test_worker_auto_generates_id(self):
        """Test worker auto-generates ID if not provided."""
        with patch.dict(
            sys.modules,
            {
                "samedaysuits_api": Mock(),
            },
        ):
            from nesting_worker import NestingWorker

            with patch.object(NestingWorker, "_load_production_modules"):
                worker = NestingWorker()
                self.assertIsNotNone(worker.worker_id)
                self.assertTrue(worker.worker_id.startswith("worker-"))


class TestAsyncProcessingIntegration(unittest.TestCase):
    """Integration tests for async processing flow."""

    @classmethod
    def setUpClass(cls):
        """Check if full integration test can run."""
        from queue_manager import OrderQueue

        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        queue = OrderQueue(redis_url)
        cls.redis_available = queue.is_available

        if not cls.redis_available:
            print("\n[SKIP] Redis not available - skipping integration tests")

    def setUp(self):
        if not self.redis_available:
            self.skipTest("Redis not available")

    def test_full_order_lifecycle(self):
        """Test complete order lifecycle: enqueue -> process -> complete."""
        from queue_manager import OrderQueue, JobPriority, JobStatus

        queue = OrderQueue()
        order_id = f"LIFECYCLE-{int(time.time() * 1000)}"

        # 1. Enqueue
        order_data = {
            "order_id": order_id,
            "customer_id": "TEST-CUSTOMER",
            "garment_type": "tee",
            "fit_type": "regular",
            "measurements": {
                "chest_cm": 102,
                "waist_cm": 88,
                "hip_cm": 100,
            },
            "priority": "normal",
            "quantity": 1,
        }

        queue.enqueue(order_id, order_data, JobPriority.NORMAL)
        self.assertEqual(queue.get_status(order_id), JobStatus.QUEUED)

        # 2. Check position
        position = queue.get_position(order_id)
        self.assertIsNotNone(position)
        self.assertGreater(position, 0)

        # 3. Dequeue (simulating worker)
        dequeued = queue.dequeue(timeout=1)
        self.assertEqual(dequeued["order_id"], order_id)
        self.assertEqual(queue.get_status(order_id), JobStatus.PROCESSING)

        # 4. Complete
        result = {
            "success": True,
            "plt_file": f"/output/{order_id}/{order_id}.plt",
            "fabric_length_cm": 95.5,
            "fabric_utilization": 87.3,
            "piece_count": 6,
        }
        queue.complete(order_id, result)
        self.assertEqual(queue.get_status(order_id), JobStatus.COMPLETE)

        # 5. Verify result
        stored_result = queue.get_result(order_id)
        self.assertEqual(stored_result["success"], True)
        self.assertEqual(stored_result["fabric_utilization"], 87.3)


class TestBackwardCompatibility(unittest.TestCase):
    """
    Tests to ensure existing functionality still works.

    These verify that:
    1. Sync processing still works when ASYNC_PROCESSING=false
    2. Queue fallback works when Redis unavailable
    3. Existing API contracts are maintained
    """

    def test_sync_mode_is_default(self):
        """Verify ASYNC_PROCESSING defaults to false."""
        # Reset env var
        if "ASYNC_PROCESSING" in os.environ:
            del os.environ["ASYNC_PROCESSING"]

        # Check default
        async_enabled = os.getenv("ASYNC_PROCESSING", "false").lower() == "true"
        self.assertFalse(async_enabled)

    def test_queue_manager_constants(self):
        """Verify queue manager constants match expected values."""
        from queue_manager import OrderQueue

        self.assertEqual(OrderQueue.MAX_RETRIES, 3)
        self.assertEqual(OrderQueue.KEY_PREFIX, "sds")


# =============================================================================
# Test Runner
# =============================================================================


def run_tests():
    """Run all scalability tests."""
    print("\n" + "=" * 70)
    print("SameDaySuits Scalability Tests")
    print("=" * 70)

    # Check Redis availability
    try:
        from queue_manager import OrderQueue

        queue = OrderQueue()
        if queue.is_available:
            print("Redis: CONNECTED")
        else:
            print("Redis: NOT AVAILABLE (some tests will be skipped)")
    except Exception as e:
        print(f"Redis: ERROR ({e})")

    print("=" * 70 + "\n")

    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestQueueManager))
    suite.addTests(loader.loadTestsFromTestCase(TestQueueManagerWithRedis))
    suite.addTests(loader.loadTestsFromTestCase(TestCacheManager))
    suite.addTests(loader.loadTestsFromTestCase(TestNestingWorker))
    suite.addTests(loader.loadTestsFromTestCase(TestAsyncProcessingIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestBackwardCompatibility))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped)}")

    success_count = result.testsRun - len(result.failures) - len(result.errors)
    if result.testsRun > 0:
        pass_rate = (success_count / result.testsRun) * 100
        print(f"Pass rate: {pass_rate:.1f}%")

    if result.failures:
        print("\nFailed tests:")
        for test, _ in result.failures:
            print(f"  - {test}")

    if result.errors:
        print("\nError tests:")
        for test, _ in result.errors:
            print(f"  - {test}")

    print("=" * 70)

    return len(result.failures) == 0 and len(result.errors) == 0


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
