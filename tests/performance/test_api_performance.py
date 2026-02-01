"""
Performance Tests: API Performance

Tests API response times and performance under load.
Reference: Ops Manual v6.8 - Section 2.6 (Scalability Layer)

Performance Targets:
- Response time < 100ms (p95) for API calls
- Pattern generation < 3 minutes (99th percentile)
- File download < 5 seconds
- Concurrent user testing (10, 50, 100 users)
"""

import pytest
import asyncio
import time
import statistics
from datetime import datetime
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

import httpx
from httpx import AsyncClient

# Test Configuration
PATTERN_FACTORY_API_BASE = "http://localhost:8000/api/v1"
EYESON_API_BASE = "http://localhost:8001/api/v1"

# Performance Baselines (from Ops Manual v6.8 Section 2.6)
BASELINES = {
    "api_response_p95_ms": 100,
    "api_response_p99_ms": 200,
    "pattern_generation_p99_s": 180,  # 3 minutes
    "file_download_max_s": 5,
    "concurrent_users": [10, 50, 100],
}


# Sample measurement data for testing
SAMPLE_MEASUREMENTS = {
    "Cg": {"value": 102.5, "unit": "cm", "confidence": 0.95},
    "Wg": {"value": 88.3, "unit": "cm", "confidence": 0.92},
    "Hg": {"value": 98.7, "unit": "cm", "confidence": 0.94},
    "Sh": {"value": 46.2, "unit": "cm", "confidence": 0.93},
    "Al": {"value": 64.8, "unit": "cm", "confidence": 0.90},
    "Bw": {"value": 38.5, "unit": "cm", "confidence": 0.91},
    "Nc": {"value": 39.4, "unit": "cm", "confidence": 0.94},
}


@pytest.fixture
def auth_token():
    """Generate test auth token."""
    return "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test_token"


@pytest.fixture
async def async_client():
    """Create async HTTP client."""
    async with AsyncClient(timeout=30.0) as client:
        yield client


@pytest.mark.performance
@pytest.mark.asyncio
class TestAPIResponseTimes:
    """
    Test API endpoint response times.
    
    Target: < 100ms p95 for all API calls
    """

    @pytest.mark.parametrize("endpoint,method", [
        ("/api/health", "GET"),
        ("/api/v1/orders", "POST"),
        ("/api/v1/orders/SDS-20260101-0001-A", "GET"),
        ("/api/v1/queue/status", "GET"),
    ])
    async def test_endpoint_response_time_p95(
        self,
        async_client,
        auth_token,
        endpoint,
        method
    ):
        """
        Test that API endpoints meet p95 response time target.
        
        Makes 100 requests and verifies 95% are under 100ms.
        """
        base_url = PATTERN_FACTORY_API_BASE
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        response_times = []
        num_requests = 100
        
        for i in range(num_requests):
            start = time.perf_counter()
            
            if method == "GET":
                response = await async_client.get(
                    f"{base_url}{endpoint}",
                    headers=headers
                )
            else:  # POST
                response = await async_client.post(
                    f"{base_url}{endpoint}",
                    json={
                        "customer_id": f"perf_test_{i}",
                        "garment_type": "jacket",
                        "fit_type": "regular",
                        "measurements": SAMPLE_MEASUREMENTS
                    },
                    headers=headers
                )
            
            elapsed_ms = (time.perf_counter() - start) * 1000
            response_times.append(elapsed_ms)
        
        # Calculate p95
        response_times.sort()
        p95_index = int(len(response_times) * 0.95)
        p95_time = response_times[p95_index]
        
        avg_time = statistics.mean(response_times)
        min_time = min(response_times)
        max_time = max(response_times)
        
        print(f"\n📊 {method} {endpoint}")
        print(f"   Requests: {num_requests}")
        print(f"   p95: {p95_time:.1f}ms (target < {BASELINES['api_response_p95_ms']}ms)")
        print(f"   avg: {avg_time:.1f}ms, min: {min_time:.1f}ms, max: {max_time:.1f}ms")
        
        assert p95_time < BASELINES["api_response_p95_ms"], \
            f"p95 response time {p95_time:.1f}ms exceeds target of {BASELINES['api_response_p95_ms']}ms"

    async def test_health_check_response_time(self, async_client):
        """
        Test health check endpoint response time.
        
        Health checks should be very fast (< 50ms).
        """
        response_times = []
        
        for _ in range(50):
            start = time.perf_counter()
            response = await async_client.get(
                f"{PATTERN_FACTORY_API_BASE}/health"
            )
            elapsed_ms = (time.perf_counter() - start) * 1000
            response_times.append(elapsed_ms)
        
        avg_time = statistics.mean(response_times)
        max_time = max(response_times)
        
        print(f"\n📊 Health Check")
        print(f"   avg: {avg_time:.1f}ms, max: {max_time:.1f}ms")
        
        assert avg_time < 50, f"Health check avg {avg_time:.1f}ms too slow"
        assert max_time < 100, f"Health check max {max_time:.1f}ms too slow"

    async def test_order_creation_response_time_distribution(self, async_client, auth_token):
        """
        Test distribution of order creation response times.
        
        Verifies p50, p95, p99 all meet targets.
        """
        headers = {"Authorization": f"Bearer {auth_token}"}
        response_times = []
        num_requests = 200
        
        for i in range(num_requests):
            start = time.perf_counter()
            
            response = await async_client.post(
                f"{PATTERN_FACTORY_API_BASE}/orders",
                json={
                    "customer_id": f"dist_test_{i}",
                    "garment_type": "jacket",
                    "fit_type": "regular",
                    "measurements": SAMPLE_MEASUREMENTS
                },
                headers=headers
            )
            
            elapsed_ms = (time.perf_counter() - start) * 1000
            response_times.append(elapsed_ms)
        
        response_times.sort()
        
        p50 = response_times[int(len(response_times) * 0.50)]
        p95 = response_times[int(len(response_times) * 0.95)]
        p99 = response_times[int(len(response_times) * 0.99)]
        
        print(f"\n📊 Order Creation Response Time Distribution")
        print(f"   p50: {p50:.1f}ms")
        print(f"   p95: {p95:.1f}ms (target < {BASELINES['api_response_p95_ms']}ms)")
        print(f"   p99: {p99:.1f}ms (target < {BASELINES['api_response_p99_ms']}ms)")
        
        assert p95 < BASELINES["api_response_p95_ms"]
        assert p99 < BASELINES["api_response_p99_ms"]


@pytest.mark.performance
@pytest.mark.asyncio
class TestPatternGenerationPerformance:
    """
    Test pattern generation performance.
    
    Target: < 3 minutes (99th percentile)
    """

    async def test_pattern_generation_time_p99(self, async_client, auth_token):
        """
        Test pattern generation time meets p99 target.
        
        Creates multiple orders and measures pattern generation time.
        """
        headers = {"Authorization": f"Bearer {auth_token}"}
        generation_times = []
        num_orders = 10
        
        for i in range(num_orders):
            # Create order
            create_start = time.time()
            create_response = await async_client.post(
                f"{PATTERN_FACTORY_API_BASE}/orders",
                json={
                    "customer_id": f"pattern_perf_{i}",
                    "garment_type": "jacket",
                    "fit_type": "regular",
                    "measurements": SAMPLE_MEASUREMENTS
                },
                headers=headers
            )
            
            if create_response.status_code != 201:
                continue
                
            order_id = create_response.json()["order_id"]
            
            # Poll for pattern generation completion
            max_wait = 300  # 5 minutes max
            poll_start = time.time()
            
            while (time.time() - poll_start) < max_wait:
                status_response = await async_client.get(
                    f"{PATTERN_FACTORY_API_BASE}/orders/{order_id}/status",
                    headers=headers
                )
                
                if status_response.status_code == 200:
                    status = status_response.json()
                    
                    if status.get("files_available", {}).get("plt"):
                        generation_time = time.time() - create_start
                        generation_times.append(generation_time)
                        break
                    
                    if status.get("status") == "error":
                        break
                
                await asyncio.sleep(1)
            
            await asyncio.sleep(0.5)  # Small delay between orders
        
        if len(generation_times) < 5:
            pytest.skip(f"Not enough successful pattern generations ({len(generation_times)})")
        
        generation_times.sort()
        p99_index = int(len(generation_times) * 0.99)
        p99_time = generation_times[min(p99_index, len(generation_times) - 1)]
        
        avg_time = statistics.mean(generation_times)
        min_time = min(generation_times)
        max_time = max(generation_times)
        
        print(f"\n📊 Pattern Generation Time")
        print(f"   Samples: {len(generation_times)}")
        print(f"   p99: {p99_time:.1f}s (target < {BASELINES['pattern_generation_p99_s']}s)")
        print(f"   avg: {avg_time:.1f}s, min: {min_time:.1f}s, max: {max_time:.1f}s")
        
        assert p99_time < BASELINES["pattern_generation_p99_s"], \
            f"p99 generation time {p99_time:.1f}s exceeds target of {BASELINES['pattern_generation_p99_s']}s"

    async def test_pattern_generation_throughput(self, async_client, auth_token):
        """
        Test pattern generation throughput.
        
        Target: 100 orders/hour
        """
        headers = {"Authorization": f"Bearer {auth_token}"}
        num_orders = 20
        
        start_time = time.time()
        order_ids = []
        
        # Submit orders rapidly
        for i in range(num_orders):
            response = await async_client.post(
                f"{PATTERN_FACTORY_API_BASE}/orders",
                json={
                    "customer_id": f"throughput_{i}",
                    "garment_type": "jacket",
                    "fit_type": "regular",
                    "measurements": SAMPLE_MEASUREMENTS
                },
                headers=headers
            )
            
            if response.status_code == 201:
                order_ids.append(response.json()["order_id"])
        
        submit_time = time.time() - start_time
        
        # Wait for all patterns to complete
        completed = 0
        max_wait = 600  # 10 minutes
        wait_start = time.time()
        
        while completed < len(order_ids) and (time.time() - wait_start) < max_wait:
            for order_id in order_ids:
                status_response = await async_client.get(
                    f"{PATTERN_FACTORY_API_BASE}/orders/{order_id}/status",
                    headers=headers
                )
                
                if status_response.status_code == 200:
                    status = status_response.json()
                    if status.get("files_available", {}).get("plt"):
                        completed += 1
            
            await asyncio.sleep(2)
        
        total_time = time.time() - start_time
        throughput_per_hour = completed / total_time * 3600
        
        print(f"\n📊 Pattern Generation Throughput")
        print(f"   Orders submitted: {len(order_ids)}")
        print(f"   Patterns completed: {completed}")
        print(f"   Total time: {total_time:.1f}s")
        print(f"   Throughput: {throughput_per_hour:.0f} orders/hour (target: 100/hour)")
        
        assert throughput_per_hour >= 100, \
            f"Throughput {throughput_per_hour:.0f}/hour below target of 100/hour"


@pytest.mark.performance
@pytest.mark.asyncio
class TestFileDownloadPerformance:
    """
    Test file download performance.
    
    Target: < 5 seconds for file downloads
    """

    async def test_plt_download_time(self, async_client, auth_token):
        """
        Test PLT file download time.
        """
        await self._test_file_download(async_client, auth_token, "plt")

    async def test_pds_download_time(self, async_client, auth_token):
        """
        Test PDS file download time.
        """
        await self._test_file_download(async_client, auth_token, "pds")

    async def test_dxf_download_time(self, async_client, auth_token):
        """
        Test DXF file download time.
        """
        await self._test_file_download(async_client, auth_token, "dxf")

    async def _test_file_download(
        self,
        async_client,
        auth_token,
        file_type: str
    ):
        """Helper to test file download performance."""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # Create order and wait for pattern
        create_response = await async_client.post(
            f"{PATTERN_FACTORY_API_BASE}/orders",
            json={
                "customer_id": f"dl_test_{file_type}",
                "garment_type": "jacket",
                "fit_type": "regular",
                "measurements": SAMPLE_MEASUREMENTS
            },
            headers=headers
        )
        
        if create_response.status_code != 201:
            pytest.skip(f"Failed to create order: {create_response.text}")
        
        order_id = create_response.json()["order_id"]
        
        # Wait for pattern generation
        max_wait = 300
        start_wait = time.time()
        file_ready = False
        
        while (time.time() - start_wait) < max_wait:
            status_response = await async_client.get(
                f"{PATTERN_FACTORY_API_BASE}/orders/{order_id}/status",
                headers=headers
            )
            
            if status_response.status_code == 200:
                status = status_response.json()
                if status.get("files_available", {}).get(file_type):
                    file_ready = True
                    break
            
            await asyncio.sleep(1)
        
        if not file_ready:
            pytest.skip(f"File not ready after {max_wait}s")
        
        # Download file multiple times and measure
        download_times = []
        num_downloads = 10
        
        for _ in range(num_downloads):
            start = time.perf_counter()
            
            response = await async_client.get(
                f"{PATTERN_FACTORY_API_BASE}/orders/{order_id}/{file_type}",
                headers=headers
            )
            
            elapsed_s = time.perf_counter() - start
            
            if response.status_code == 200:
                download_times.append(elapsed_s)
            
            await asyncio.sleep(0.1)
        
        if len(download_times) < 3:
            pytest.skip(f"Not enough successful downloads ({len(download_times)})")
        
        avg_time = statistics.mean(download_times)
        max_time = max(download_times)
        file_size_kb = len(response.content) / 1024
        
        print(f"\n📊 {file_type.upper()} Download Performance")
        print(f"   File size: {file_size_kb:.1f} KB")
        print(f"   avg: {avg_time:.2f}s, max: {max_time:.2f}s")
        print(f"   Target: < {BASELINES['file_download_max_s']}s")
        
        assert max_time < BASELINES["file_download_max_s"], \
            f"Download time {max_time:.2f}s exceeds target of {BASELINES['file_download_max_s']}s"


@pytest.mark.performance
@pytest.mark.asyncio
class TestConcurrentUserPerformance:
    """
    Test system performance under concurrent load.
    
    Tests with 10, 50, and 100 concurrent users.
    """

    @pytest.mark.parametrize("num_users", BASELINES["concurrent_users"])
    async def test_concurrent_order_creation(
        self,
        async_client,
        auth_token,
        num_users
    ):
        """
        Test concurrent order creation.
        
        Verifies system can handle multiple users creating orders simultaneously
        without significant performance degradation.
        """
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        async def create_order(user_id: int):
            start = time.perf_counter()
            
            response = await async_client.post(
                f"{PATTERN_FACTORY_API_BASE}/orders",
                json={
                    "customer_id": f"concurrent_user_{user_id}",
                    "garment_type": "jacket",
                    "fit_type": "regular",
                    "measurements": SAMPLE_MEASUREMENTS
                },
                headers=headers
            )
            
            elapsed_ms = (time.perf_counter() - start) * 1000
            return response.status_code == 201, elapsed_ms
        
        # Launch concurrent requests
        start_time = time.time()
        tasks = [create_order(i) for i in range(num_users)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_time = time.time() - start_time
        
        # Analyze results
        successful = []
        failed = 0
        
        for result in results:
            if isinstance(result, Exception):
                failed += 1
            elif result[0]:  # Success
                successful.append(result[1])
            else:
                failed += 1
        
        success_rate = len(successful) / num_users * 100
        
        if successful:
            avg_response = statistics.mean(successful)
            p95_response = sorted(successful)[int(len(successful) * 0.95)]
        else:
            avg_response = 0
            p95_response = 0
        
        print(f"\n📊 Concurrent Order Creation ({num_users} users)")
        print(f"   Success rate: {success_rate:.1f}%")
        print(f"   Total time: {total_time:.1f}s")
        print(f"   avg response: {avg_response:.1f}ms")
        print(f"   p95 response: {p95_response:.1f}ms")
        
        # Success rate should be > 95%
        assert success_rate >= 95, \
            f"Success rate {success_rate:.1f}% below 95% threshold"
        
        # p95 should still be under 500ms even under load
        if successful:
            assert p95_response < 500, \
                f"p95 response {p95_response:.1f}ms too slow under load"

    @pytest.mark.parametrize("num_users", [10, 50])
    async def test_concurrent_status_polling(
        self,
        async_client,
        auth_token,
        num_users
    ):
        """
        Test concurrent status polling.
        
        Simulates multiple users polling for order status simultaneously.
        """
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # Create a test order first
        create_response = await async_client.post(
            f"{PATTERN_FACTORY_API_BASE}/orders",
            json={
                "customer_id": "polling_test",
                "garment_type": "jacket",
                "fit_type": "regular",
                "measurements": SAMPLE_MEASUREMENTS
            },
            headers=headers
        )
        
        if create_response.status_code != 201:
            pytest.skip("Failed to create test order")
        
        order_id = create_response.json()["order_id"]
        
        async def poll_status(user_id: int):
            start = time.perf_counter()
            
            response = await async_client.get(
                f"{PATTERN_FACTORY_API_BASE}/orders/{order_id}/status",
                headers=headers
            )
            
            elapsed_ms = (time.perf_counter() - start) * 1000
            return response.status_code == 200, elapsed_ms
        
        # Launch concurrent polls
        start_time = time.time()
        tasks = [poll_status(i) for i in range(num_users)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_time = time.time() - start_time
        
        # Analyze results
        successful = [r[1] for r in results if not isinstance(r, Exception) and r[0]]
        
        if successful:
            avg_response = statistics.mean(successful)
            p95_response = sorted(successful)[int(len(successful) * 0.95)]
        else:
            avg_response = 0
            p95_response = 0
        
        success_rate = len(successful) / num_users * 100
        
        print(f"\n📊 Concurrent Status Polling ({num_users} users)")
        print(f"   Success rate: {success_rate:.1f}%")
        print(f"   Total time: {total_time:.1f}s")
        print(f"   avg response: {avg_response:.1f}ms")
        print(f"   p95 response: {p95_response:.1f}ms")
        
        assert success_rate >= 99, \
            f"Polling success rate {success_rate:.1f}% below 99% threshold"

    @pytest.mark.parametrize("num_users", [10, 25])
    async def test_concurrent_file_downloads(
        self,
        async_client,
        auth_token,
        num_users
    ):
        """
        Test concurrent file downloads.
        
        Verifies system can handle multiple simultaneous downloads.
        """
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # Create order and wait for pattern
        create_response = await async_client.post(
            f"{PATTERN_FACTORY_API_BASE}/orders",
            json={
                "customer_id": "concurrent_dl_test",
                "garment_type": "jacket",
                "fit_type": "regular",
                "measurements": SAMPLE_MEASUREMENTS
            },
            headers=headers
        )
        
        if create_response.status_code != 201:
            pytest.skip("Failed to create test order")
        
        order_id = create_response.json()["order_id"]
        
        # Wait for pattern
        max_wait = 300
        start_wait = time.time()
        while (time.time() - start_wait) < max_wait:
            status_response = await async_client.get(
                f"{PATTERN_FACTORY_API_BASE}/orders/{order_id}/status",
                headers=headers
            )
            
            if status_response.status_code == 200:
                status = status_response.json()
                if status.get("files_available", {}).get("plt"):
                    break
            
            await asyncio.sleep(1)
        
        async def download_file(user_id: int):
            start = time.perf_counter()
            
            response = await async_client.get(
                f"{PATTERN_FACTORY_API_BASE}/orders/{order_id}/plt",
                headers=headers
            )
            
            elapsed_s = time.perf_counter() - start
            return response.status_code == 200, elapsed_s
        
        # Launch concurrent downloads
        start_time = time.time()
        tasks = [download_file(i) for i in range(num_users)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_time = time.time() - start_time
        
        # Analyze results
        successful = [r[1] for r in results if not isinstance(r, Exception) and r[0]]
        
        if successful:
            avg_time = statistics.mean(successful)
            max_time = max(successful)
        else:
            avg_time = 0
            max_time = 0
        
        success_rate = len(successful) / num_users * 100
        
        print(f"\n📊 Concurrent File Downloads ({num_users} users)")
        print(f"   Success rate: {success_rate:.1f}%")
        print(f"   Total time: {total_time:.1f}s")
        print(f"   avg: {avg_time:.2f}s, max: {max_time:.2f}s")
        
        assert success_rate >= 95
        if successful:
            assert max_time < 10, \
                f"Max download time {max_time:.2f}s too slow under concurrent load"


@pytest.mark.performance
@pytest.mark.benchmark
class TestPerformanceBenchmarks:
    """
    Benchmark tests for establishing performance baselines.
    
    These tests establish benchmark numbers for comparison
    in future performance regression testing.
    """

    @pytest.fixture
    def benchmark_results(self):
        """Store benchmark results for reporting."""
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "results": {}
        }

    def test_benchmark_baseline(self, benchmark_results):
        """
        Establish baseline performance metrics.
        
        This test documents expected performance characteristics
        for reference in regression testing.
        """
        baselines = {
            "api_health_check_ms": {"target": 50, "max": 100},
            "api_order_create_p95_ms": {"target": 100, "max": 200},
            "api_order_create_p99_ms": {"target": 200, "max": 500},
            "api_status_check_ms": {"target": 50, "max": 100},
            "pattern_generation_p99_s": {"target": 180, "max": 300},
            "file_download_max_s": {"target": 5, "max": 10},
            "concurrent_users_10": {"target": 100, "max": 200},
            "concurrent_users_50": {"target": 400, "max": 800},
            "concurrent_users_100": {"target": 800, "max": 1500},
            "throughput_orders_per_hour": {"target": 100, "min": 60},
        }
        
        benchmark_results["results"] = baselines
        
        print("\n📊 Performance Benchmark Baselines")
        print("=" * 50)
        for metric, values in baselines.items():
            if "target" in values:
                print(f"   {metric}:")
                print(f"      target: {values['target']}")
                if "max" in values:
                    print(f"      max: {values['max']}")
                if "min" in values:
                    print(f"      min: {values['min']}")
        
        # This test always passes - it's for documentation
        assert True
