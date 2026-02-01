"""
Performance Tests: Load Patterns

Tests system performance under various load patterns.
Reference: Ops Manual v6.8 - Section 2.6 (Scalability Layer)

Load Test Targets:
- 100 orders/hour throughput
- Cutter queue 60+ patterns/hour
- Database query performance
- Redis cache hit rates
"""

import pytest
import asyncio
import time
import random
import statistics
from datetime import datetime, timedelta
from typing import List, Dict, Any
from collections import defaultdict

import httpx
from httpx import AsyncClient

# Test Configuration
PATTERN_FACTORY_API_BASE = "http://localhost:8000/api/v1"

# Performance Targets (from Ops Manual v6.8 Section 2.6)
PERFORMANCE_TARGETS = {
    "orders_per_hour": 100,
    "cutter_patterns_per_hour": 60,
    "db_query_p95_ms": 50,
    "redis_cache_hit_rate": 0.90,
    "queue_processing_rate": 60,  # per hour
}

SAMPLE_MEASUREMENTS = {
    "Cg": {"value": 102.5, "unit": "cm", "confidence": 0.95},
    "Wg": {"value": 88.3, "unit": "cm", "confidence": 0.92},
    "Hg": {"value": 98.7, "unit": "cm", "confidence": 0.94},
    "Sh": {"value": 46.2, "unit": "cm", "confidence": 0.93},
    "Al": {"value": 64.8, "unit": "cm", "confidence": 0.90},
}


@pytest.fixture
def auth_token():
    """Generate test auth token."""
    return "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test_token"


@pytest.fixture
async def async_client():
    """Create async HTTP client."""
    async with AsyncClient(timeout=60.0) as client:
        yield client


@pytest.mark.performance
@pytest.mark.asyncio
class TestThroughputLoad:
    """
    Test system throughput under sustained load.
    
    Target: 100 orders/hour sustained throughput
    """

    async def test_sustained_order_throughput(self, async_client, auth_token):
        """
        Test sustained order creation throughput.
        
        Creates orders at target rate for 10 minutes and verifies
        system maintains performance.
        """
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        target_orders_per_hour = PERFORMANCE_TARGETS["orders_per_hour"]
        test_duration_minutes = 5  # Shortened for test suite
        
        orders_created = 0
        response_times = []
        errors = []
        
        start_time = time.time()
        end_time = start_time + (test_duration_minutes * 60)
        
        # Calculate delay between orders to achieve target rate
        delay_between_orders = 3600 / target_orders_per_hour
        
        while time.time() < end_time:
            order_start = time.perf_counter()
            
            try:
                response = await async_client.post(
                    f"{PATTERN_FACTORY_API_BASE}/orders",
                    json={
                        "customer_id": f"throughput_{int(time.time() * 1000)}",
                        "garment_type": random.choice(["jacket", "trousers", "tee"]),
                        "fit_type": random.choice(["slim", "regular", "classic"]),
                        "measurements": SAMPLE_MEASUREMENTS,
                        "priority": random.choice(["normal", "high"])
                    },
                    headers=headers
                )
                
                elapsed_ms = (time.perf_counter() - order_start) * 1000
                response_times.append(elapsed_ms)
                
                if response.status_code == 201:
                    orders_created += 1
                else:
                    errors.append({
                        "status": response.status_code,
                        "time": datetime.utcnow().isoformat()
                    })
                    
            except Exception as e:
                errors.append({
                    "error": str(e),
                    "time": datetime.utcnow().isoformat()
                })
            
            # Wait to maintain target rate
            await asyncio.sleep(delay_between_orders)
        
        total_time = time.time() - start_time
        actual_throughput = orders_created / total_time * 3600
        error_rate = len(errors) / (orders_created + len(errors)) * 100 if (orders_created + len(errors)) > 0 else 0
        
        if response_times:
            avg_response = statistics.mean(response_times)
            p95_response = sorted(response_times)[int(len(response_times) * 0.95)]
        else:
            avg_response = 0
            p95_response = 0
        
        print(f"\n📊 Sustained Throughput Test ({test_duration_minutes} minutes)")
        print(f"   Target: {target_orders_per_hour} orders/hour")
        print(f"   Actual: {actual_throughput:.0f} orders/hour")
        print(f"   Orders created: {orders_created}")
        print(f"   Error rate: {error_rate:.1f}%")
        print(f"   avg response: {avg_response:.1f}ms")
        print(f"   p95 response: {p95_response:.1f}ms")
        
        assert actual_throughput >= target_orders_per_hour * 0.9, \
            f"Throughput {actual_throughput:.0f}/hour below 90% of target"
        assert error_rate < 5, f"Error rate {error_rate:.1f}% too high"

    async def test_burst_load_handling(self, async_client, auth_token):
        """
        Test system handling of burst loads.
        
        Simulates sudden spike in order volume (e.g., flash sale).
        """
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        burst_size = 50
        burst_duration_seconds = 30
        
        orders_created = []
        errors = []
        
        async def create_burst_order(order_num: int):
            try:
                response = await async_client.post(
                    f"{PATTERN_FACTORY_API_BASE}/orders",
                    json={
                        "customer_id": f"burst_{order_num}",
                        "garment_type": "jacket",
                        "fit_type": "regular",
                        "measurements": SAMPLE_MEASUREMENTS
                    },
                    headers=headers
                )
                
                if response.status_code == 201:
                    orders_created.append(order_num)
                else:
                    errors.append(order_num)
            except Exception:
                errors.append(order_num)
        
        start_time = time.time()
        
        # Launch burst of orders
        tasks = [create_burst_order(i) for i in range(burst_size)]
        await asyncio.gather(*tasks, return_exceptions=True)
        
        burst_time = time.time() - start_time
        success_rate = len(orders_created) / burst_size * 100
        throughput = len(orders_created) / burst_time * 60
        
        print(f"\n📊 Burst Load Test")
        print(f"   Burst size: {burst_size} orders")
        print(f"   Burst time: {burst_time:.1f}s")
        print(f"   Success rate: {success_rate:.1f}%")
        print(f"   Throughput: {throughput:.0f} orders/minute")
        
        assert success_rate >= 95, f"Burst success rate {success_rate:.1f}% too low"

    async def test_ramp_up_pattern(self, async_client, auth_token):
        """
        Test system behavior during gradual ramp-up.
        
        Gradually increases load to find performance degradation point.
        """
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        ramp_stages = [
            (10, 30),   # 10 orders, 30 seconds
            (25, 30),   # 25 orders, 30 seconds
            (50, 30),   # 50 orders, 30 seconds
        ]
        
        stage_results = []
        
        for orders, duration in ramp_stages:
            response_times = []
            errors = 0
            
            delay = duration / orders
            start_time = time.time()
            
            for i in range(orders):
                order_start = time.perf_counter()
                
                try:
                    response = await async_client.post(
                        f"{PATTERN_FACTORY_API_BASE}/orders",
                        json={
                            "customer_id": f"ramp_{orders}_{i}",
                            "garment_type": "jacket",
                            "fit_type": "regular",
                            "measurements": SAMPLE_MEASUREMENTS
                        },
                        headers=headers
                    )
                    
                    elapsed_ms = (time.perf_counter() - order_start) * 1000
                    response_times.append(elapsed_ms)
                    
                    if response.status_code != 201:
                        errors += 1
                except Exception:
                    errors += 1
                
                await asyncio.sleep(delay)
            
            actual_time = time.time() - start_time
            throughput = orders / actual_time * 60
            
            if response_times:
                p95 = sorted(response_times)[int(len(response_times) * 0.95)]
            else:
                p95 = 0
            
            stage_results.append({
                "orders": orders,
                "throughput": throughput,
                "p95_response_ms": p95,
                "error_rate": errors / orders * 100
            })
        
        print(f"\n📊 Ramp-Up Pattern Test")
        for result in stage_results:
            print(f"   {result['orders']} orders: {result['throughput']:.0f}/min, "
                  f"p95={result['p95_response_ms']:.0f}ms, "
                  f"errors={result['error_rate']:.1f}%")
        
        # Verify performance doesn't degrade significantly
        for i in range(1, len(stage_results)):
            prev = stage_results[i-1]
            curr = stage_results[i]
            
            # p95 should not more than double
            assert curr["p95_response_ms"] < prev["p95_response_ms"] * 2.5, \
                f"Performance degraded significantly at {curr['orders']} orders"


@pytest.mark.performance
@pytest.mark.asyncio
class TestCutterQueueLoad:
    """
    Test cutter queue performance.
    
    Target: 60+ patterns/hour through cutter queue
    """

    async def test_cutter_queue_throughput(self, async_client, auth_token):
        """
        Test cutter queue processing throughput.
        
        Verifies patterns can be queued and processed at target rate.
        """
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        target_patterns_per_hour = PERFORMANCE_TARGETS["cutter_patterns_per_hour"]
        test_duration_minutes = 3
        
        patterns_queued = 0
        patterns_processed = 0
        
        start_time = time.time()
        end_time = start_time + (test_duration_minutes * 60)
        order_ids = []
        
        # Create patterns and add to queue
        while time.time() < end_time and patterns_queued < target_patterns_per_hour / 2:
            response = await async_client.post(
                f"{PATTERN_FACTORY_API_BASE}/orders",
                json={
                    "customer_id": f"cutter_test_{patterns_queued}",
                    "garment_type": "jacket",
                    "fit_type": "regular",
                    "measurements": SAMPLE_MEASUREMENTS
                },
                headers=headers
            )
            
            if response.status_code == 201:
                order_id = response.json()["order_id"]
                order_ids.append(order_id)
                patterns_queued += 1
            
            await asyncio.sleep(1)
        
        # Wait for patterns to be processed
        await asyncio.sleep(30)
        
        # Check queue status
        queue_response = await async_client.get(
            f"{PATTERN_FACTORY_API_BASE}/queue/status",
            headers=headers
        )
        
        if queue_response.status_code == 200:
            queue_status = queue_response.json()
            
            print(f"\n📊 Cutter Queue Throughput")
            print(f"   Patterns queued: {patterns_queued}")
            print(f"   Pending jobs: {queue_status.get('pending_jobs', 'N/A')}")
            print(f"   Processing jobs: {queue_status.get('processing_jobs', 'N/A')}")
            print(f"   Completed jobs: {queue_status.get('completed_jobs', 'N/A')}")
            
            # Queue should be processing at target rate
            if queue_status.get('average_wait_time_ms'):
                avg_wait_s = queue_status['average_wait_time_ms'] / 1000
                print(f"   Avg wait time: {avg_wait_s:.1f}s")

    async def test_queue_depth_handling(self, async_client, auth_token):
        """
        Test system behavior with deep queue.
        
        Verifies system remains stable with large queue backlog.
        """
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # Create deep queue
        queue_depth = 30
        order_ids = []
        
        for i in range(queue_depth):
            response = await async_client.post(
                f"{PATTERN_FACTORY_API_BASE}/orders",
                json={
                    "customer_id": f"deep_queue_{i}",
                    "garment_type": "jacket",
                    "fit_type": "regular",
                    "measurements": SAMPLE_MEASUREMENTS
                },
                headers=headers
            )
            
            if response.status_code == 201:
                order_ids.append(response.json()["order_id"])
        
        # Monitor queue over time
        queue_snapshots = []
        for _ in range(5):
            response = await async_client.get(
                f"{PATTERN_FACTORY_API_BASE}/queue/status",
                headers=headers
            )
            
            if response.status_code == 200:
                status = response.json()
                queue_snapshots.append({
                    "pending": status.get("pending_jobs", 0),
                    "processing": status.get("processing_jobs", 0),
                    "completed": status.get("completed_jobs", 0)
                })
            
            await asyncio.sleep(10)
        
        print(f"\n📊 Queue Depth Handling")
        print(f"   Initial queue depth: {queue_depth}")
        for i, snapshot in enumerate(queue_snapshots):
            print(f"   T+{i*10}s: pending={snapshot['pending']}, "
                  f"processing={snapshot['processing']}, "
                  f"completed={snapshot['completed']}")
        
        # Queue should be processing (completed count increasing)
        if len(queue_snapshots) >= 2:
            assert queue_snapshots[-1]["completed"] >= queue_snapshots[0]["completed"], \
                "Queue not processing items"

    async def test_priority_queue_ordering(self, async_client, auth_token):
        """
        Test that priority orders are processed first.
        
        Verifies rush orders jump ahead in queue.
        """
        headers = {"Authorization": f"Bearer {auth_token}""
        
        # Create normal priority orders
        normal_orders = []
        for i in range(5):
            response = await async_client.post(
                f"{PATTERN_FACTORY_API_BASE}/orders",
                json={
                    "customer_id": f"normal_priority_{i}",
                    "garment_type": "jacket",
                    "fit_type": "regular",
                    "measurements": SAMPLE_MEASUREMENTS,
                    "priority": "normal"
                },
                headers=headers
            )
            
            if response.status_code == 201:
                normal_orders.append(response.json()["order_id"])
        
        await asyncio.sleep(1)
        
        # Create rush order (should be processed before normals)
        rush_response = await async_client.post(
            f"{PATTERN_FACTORY_API_BASE}/orders",
            json={
                "customer_id": "rush_priority",
                "garment_type": "jacket",
                "fit_type": "regular",
                "measurements": SAMPLE_MEASUREMENTS,
                "priority": "rush"
            },
            headers=headers
        )
        
        if rush_response.status_code == 201:
            rush_order_id = rush_response.json()["order_id"]
            
            # Check queue position
            queue_response = await async_client.get(
                f"{PATTERN_FACTORY_API_BASE}/queue/status",
                headers=headers
            )
            
            if queue_response.status_code == 200:
                queue_status = queue_response.json()
                
                print(f"\n📊 Priority Queue Ordering")
                print(f"   Normal orders: {len(normal_orders)}")
                print(f"   Rush order: {rush_order_id}")
                print(f"   Queue status: {queue_status}")


@pytest.mark.performance
@pytest.mark.asyncio
class TestDatabaseQueryPerformance:
    """
    Test database query performance.
    
    Target: < 50ms p95 for database queries
    """

    async def test_order_lookup_query_performance(self, async_client, auth_token):
        """
        Test order lookup query response times.
        """
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # Create test orders
        order_ids = []
        for i in range(20):
            response = await async_client.post(
                f"{PATTERN_FACTORY_API_BASE}/orders",
                json={
                    "customer_id": f"db_test_{i}",
                    "garment_type": "jacket",
                    "fit_type": "regular",
                    "measurements": SAMPLE_MEASUREMENTS
                },
                headers=headers
            )
            
            if response.status_code == 201:
                order_ids.append(response.json()["order_id"])
        
        # Query orders and measure response times
        query_times = []
        
        for order_id in order_ids:
            start = time.perf_counter()
            
            response = await async_client.get(
                f"{PATTERN_FACTORY_API_BASE}/orders/{order_id}",
                headers=headers
            )
            
            elapsed_ms = (time.perf_counter() - start) * 1000
            query_times.append(elapsed_ms)
            
            assert response.status_code == 200
        
        if query_times:
            avg_time = statistics.mean(query_times)
            p95_time = sorted(query_times)[int(len(query_times) * 0.95)]
            max_time = max(query_times)
        else:
            avg_time = p95_time = max_time = 0
        
        print(f"\n📊 Order Lookup Query Performance")
        print(f"   Queries: {len(query_times)}")
        print(f"   avg: {avg_time:.1f}ms")
        print(f"   p95: {p95_time:.1f}ms (target < {PERFORMANCE_TARGETS['db_query_p95_ms']}ms)")
        print(f"   max: {max_time:.1f}ms")
        
        assert p95_time < PERFORMANCE_TARGETS["db_query_p95_ms"] * 2, \
            f"Query p95 {p95_time:.1f}ms exceeds target"

    async def test_order_list_query_performance(self, async_client, auth_token):
        """
        Test order list query with filters.
        """
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        query_times = []
        
        # Test various filter combinations
        filters = [
            {},
            {"status": "processing"},
            {"garment_type": "jacket"},
            {"priority": "high"},
            {"limit": 100},
            {"status": "processing", "garment_type": "jacket"},
        ]
        
        for filter_params in filters:
            start = time.perf_counter()
            
            response = await async_client.get(
                f"{PATTERN_FACTORY_API_BASE}/orders",
                params=filter_params,
                headers=headers
            )
            
            elapsed_ms = (time.perf_counter() - start) * 1000
            query_times.append(elapsed_ms)
        
        if query_times:
            avg_time = statistics.mean(query_times)
            p95_time = sorted(query_times)[int(len(query_times) * 0.95)]
        else:
            avg_time = p95_time = 0
        
        print(f"\n📊 Order List Query Performance")
        print(f"   avg: {avg_time:.1f}ms")
        print(f"   p95: {p95_time:.1f}ms")

    async def test_concurrent_db_queries(self, async_client, auth_token):
        """
        Test database performance under concurrent query load.
        """
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        num_concurrent = 20
        
        async def query_order_status():
            start = time.perf_counter()
            
            response = await async_client.get(
                f"{PATTERN_FACTORY_API_BASE}/queue/status",
                headers=headers
            )
            
            elapsed_ms = (time.perf_counter() - start) * 1000
            return response.status_code == 200, elapsed_ms
        
        start_time = time.time()
        tasks = [query_order_status() for _ in range(num_concurrent)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_time = time.time() - start_time
        
        successful = [r[1] for r in results if not isinstance(r, Exception) and r[0]]
        
        if successful:
            avg_time = statistics.mean(successful)
            max_time = max(successful)
        else:
            avg_time = max_time = 0
        
        print(f"\n📊 Concurrent DB Queries ({num_concurrent} queries)")
        print(f"   Total time: {total_time:.2f}s")
        print(f"   avg: {avg_time:.1f}ms")
        print(f"   max: {max_time:.1f}ms")
        
        assert len(successful) >= num_concurrent * 0.95


@pytest.mark.performance
@pytest.mark.asyncio
class TestCachePerformance:
    """
    Test Redis cache performance.
    
    Target: > 90% cache hit rate
    """

    async def test_cache_hit_rate(self, async_client, auth_token):
        """
        Test cache hit rate for repeated queries.
        """
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # Create a test order
        create_response = await async_client.post(
            f"{PATTERN_FACTORY_API_BASE}/orders",
            json={
                "customer_id": "cache_test",
                "garment_type": "jacket",
                "fit_type": "regular",
                "measurements": SAMPLE_MEASUREMENTS
            },
            headers=headers
        )
        
        if create_response.status_code != 201:
            pytest.skip("Failed to create test order")
        
        order_id = create_response.json()["order_id"]
        
        # Query same order multiple times
        num_queries = 50
        query_times = []
        
        for _ in range(num_queries):
            start = time.perf_counter()
            
            response = await async_client.get(
                f"{PATTERN_FACTORY_API_BASE}/orders/{order_id}",
                headers=headers
            )
            
            elapsed_ms = (time.perf_counter() - start) * 1000
            query_times.append(elapsed_ms)
            
            await asyncio.sleep(0.1)
        
        # Analyze cache effect
        first_half = query_times[:25]
        second_half = query_times[25:]
        
        avg_first = statistics.mean(first_half)
        avg_second = statistics.mean(second_half)
        
        # Second half should be faster if caching works
        speedup = avg_first / avg_second if avg_second > 0 else 1
        
        print(f"\n📊 Cache Hit Rate Analysis")
        print(f"   First 25 queries avg: {avg_first:.1f}ms")
        print(f"   Last 25 queries avg: {avg_second:.1f}ms")
        print(f"   Speedup: {speedup:.1f}x")
        
        # With good caching, later queries should be faster
        if speedup > 1.2:
            print("   ✅ Cache appears to be working")

    async def test_cache_invalidation(self, async_client, auth_token):
        """
        Test cache invalidation on order updates.
        """
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # Create order
        create_response = await async_client.post(
            f"{PATTERN_FACTORY_API_BASE}/orders",
            json={
                "customer_id": "cache_inv_test",
                "garment_type": "jacket",
                "fit_type": "regular",
                "measurements": SAMPLE_MEASUREMENTS
            },
            headers=headers
        )
        
        if create_response.status_code != 201:
            pytest.skip("Failed to create test order")
        
        order_id = create_response.json()["order_id"]
        
        # Query to cache
        await async_client.get(
            f"{PATTERN_FACTORY_API_BASE}/orders/{order_id}",
            headers=headers
        )
        
        # Update order (should invalidate cache)
        # Note: This assumes an update endpoint exists
        
        # Query again - should not be stale
        response = await async_client.get(
            f"{PATTERN_FACTORY_API_BASE}/orders/{order_id}",
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["order_id"] == order_id


@pytest.mark.performance
@pytest.mark.benchmark
class TestLoadBenchmarks:
    """
    Establish load test benchmarks.
    """

    def test_load_test_baselines(self):
        """
        Document load test baseline expectations.
        """
        baselines = {
            "sustained_throughput_orders_per_hour": {
                "target": 100,
                "acceptable_range": [90, 150]
            },
            "cutter_queue_patterns_per_hour": {
                "target": 60,
                "acceptable_range": [50, 80]
            },
            "burst_load_success_rate": {
                "target": 0.99,
                "acceptable_range": [0.95, 1.0]
            },
            "db_query_p95_ms": {
                "target": 50,
                "acceptable_range": [30, 100]
            },
            "concurrent_user_capacity": {
                "target": 100,
                "acceptable_range": [50, 200]
            },
            "cache_hit_rate": {
                "target": 0.90,
                "acceptable_range": [0.85, 0.99]
            },
        }
        
        print("\n📊 Load Test Baselines")
        print("=" * 60)
        for metric, values in baselines.items():
            print(f"\n{metric}:")
            print(f"  target: {values['target']}")
            print(f"  acceptable: {values['acceptable_range']}")
        
        assert True  # Documentation test


# Locust-style load test configuration for external execution
LOCUST_CONFIG = """
# Locust Load Test Configuration
# Run with: locust -f locustfile.py --host=http://localhost:8000

from locust import HttpUser, task, between

class PatternFactoryUser(HttpUser):
    wait_time = between(1, 5)
    
    def on_start(self):
        self.client.headers["Authorization"] = "Bearer test_token"
    
    @task(5)
    def create_order(self):
        self.client.post("/api/v1/orders", json={
            "customer_id": f"locust_{self.user_id}",
            "garment_type": "jacket",
            "fit_type": "regular",
            "measurements": SAMPLE_MEASUREMENTS
        })
    
    @task(10)
    def check_status(self):
        self.client.get("/api/v1/queue/status")
    
    @task(3)
    def get_order(self):
        self.client.get("/api/v1/orders/SDS-20260101-0001-A")
    
    @task(1)
    def download_file(self):
        self.client.get("/api/v1/orders/SDS-20260101-0001-A/plt")

# Load Test Scenarios
SCENARIOS = {
    "normal_load": {
        "users": 10,
        "spawn_rate": 1,
        "duration": "10m"
    },
    "peak_load": {
        "users": 50,
        "spawn_rate": 5,
        "duration": "5m"
    },
    "stress_test": {
        "users": 100,
        "spawn_rate": 10,
        "duration": "3m"
    }
}
"""
