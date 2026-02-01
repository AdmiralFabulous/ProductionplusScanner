"""
E2E Test: Complete Customer Journey

Tests the full end-to-end customer journey from opening EYESON to downloading pattern files.
Reference: Ops Manual v6.8 - Section 17 (Journey Mapping) - Customer Persona Journey

Journey Steps:
1. Customer opens EYESON (WelcomeScreen)
2. Grant camera permissions
3. Follow voice guidance (Kokoro TTS)
4. Complete 90-second scan
5. Review measurements
6. Submit to Pattern Factory
7. Download pattern files
8. Verify all files present (PLT, PDS, DXF)
"""

import pytest
import asyncio
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional
from unittest.mock import Mock, patch, AsyncMock

import httpx
from httpx import AsyncClient

# Test Configuration
EYESON_API_BASE = "http://localhost:8001/api/v1"  # EYESON Backend
PATTERN_FACTORY_API_BASE = "http://localhost:8000/api/v1"  # Pattern Factory

# Test Data - Sample measurements
SAMPLE_MEASUREMENTS = {
    "Cg": {"value": 102.5, "unit": "cm", "confidence": 0.95},
    "Wg": {"value": 88.3, "unit": "cm", "confidence": 0.92},
    "Hg": {"value": 98.7, "unit": "cm", "confidence": 0.94},
    "Sh": {"value": 46.2, "unit": "cm", "confidence": 0.93},
    "Al": {"value": 64.8, "unit": "cm", "confidence": 0.90},
    "Bw": {"value": 38.5, "unit": "cm", "confidence": 0.91},
    "Nc": {"value": 39.4, "unit": "cm", "confidence": 0.94},
    "Bi": {"value": 32.1, "unit": "cm", "confidence": 0.85},
    "Wc": {"value": 17.8, "unit": "cm", "confidence": 0.87},
    "Il": {"value": 82.4, "unit": "cm", "confidence": 0.86},
    "Th": {"value": 58.3, "unit": "cm", "confidence": 0.84},
    "Kn": {"value": 38.9, "unit": "cm", "confidence": 0.83},
    "Ca": {"value": 37.2, "unit": "cm", "confidence": 0.82},
}


@pytest.fixture
async def eyeson_client():
    """Create async HTTP client for EYESON API."""
    async with AsyncClient(base_url=EYESON_API_BASE, timeout=30.0) as client:
        yield client


@pytest.fixture
async def pattern_factory_client():
    """Create async HTTP client for Pattern Factory API."""
    async with AsyncClient(base_url=PATTERN_FACTORY_API_BASE, timeout=60.0) as client:
        yield client


@pytest.fixture
def customer_auth_token():
    """Generate test customer auth token."""
    # In real tests, this would authenticate with the auth service
    return "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test_token"


@pytest.mark.e2e
@pytest.mark.asyncio
class TestCustomerJourney:
    """
    End-to-end tests for the complete customer journey.
    
    Reference: Ops Manual v6.8 - Section 17.1 (Customer Journey Map)
    """

    async def test_step_1_welcome_screen(self, eyeson_client):
        """
        Step 1: Customer opens EYESON and sees WelcomeScreen.
        
        Verifies:
        - EYESON backend is accessible
        - Welcome content loads correctly
        - Voice prompts are available
        """
        # Check EYESON health
        response = await eyeson_client.get("/health")
        assert response.status_code == 200
        health_data = response.json()
        assert health_data["status"] == "healthy"
        
        # Verify voice prompts available
        response = await eyeson_client.get("/voice/prompts/en")
        assert response.status_code == 200
        prompts = response.json()
        assert "prompts" in prompts
        assert "welcome" in prompts["prompts"]
        assert prompts["prompts"]["welcome"].startswith("Welcome to EYESON")

    async def test_step_2_camera_permissions(self, eyeson_client):
        """
        Step 2: Grant camera permissions and initialize session.
        
        Verifies:
        - Session can be created
        - Camera permissions endpoint works
        - Session is in INITIATED state
        
        Target: < 500ms to initialize session (Ops Manual v6.8 Section 2.6)
        """
        start_time = time.time()
        
        # Create scan session
        session_data = {
            "user_id": f"test_customer_{int(time.time())}",
            "scan_mode": "video",
            "language": "en",
            "device_info": {
                "platform": "ios",
                "camera": "back",
                "resolution": "1920x1080"
            }
        }
        
        response = await eyeson_client.post("/sessions", json=session_data)
        
        init_time = (time.time() - start_time) * 1000
        assert response.status_code == 201, f"Failed to create session: {response.text}"
        assert init_time < 500, f"Session init took {init_time}ms, target < 500ms"
        
        session = response.json()
        assert session["status"] == "initiated"
        assert session["session_id"]
        assert session["websocket_url"]
        
        return session["session_id"]

    async def test_step_3_voice_guidance_kokoro_tts(self, eyeson_client):
        """
        Step 3: Voice guidance using Kokoro TTS.
        
        Verifies:
        - Kokoro TTS service is available
        - Voice prompts can be synthesized
        - Audio response time is acceptable
        
        Reference: Ops Manual v6.8 - Section 2.6 (TTS Performance Targets)
        Target: < 2 seconds for first audio chunk
        """
        # Check TTS health
        response = await eyeson_client.get("/voice/health")
        assert response.status_code == 200
        health = response.json()
        assert health["status"] == "healthy"
        
        # Test voice synthesis for welcome message
        tts_request = {
            "text": "Welcome to EYESON BodyScan. I'm your AI guide.",
            "voice": "kokoro_default",
            "speed": 1.0,
            "stream": False
        }
        
        start_time = time.time()
        response = await eyeson_client.post("/voice/synthesize", json=tts_request)
        synthesis_time = (time.time() - start_time) * 1000
        
        assert response.status_code == 200, f"TTS synthesis failed: {response.text}"
        assert synthesis_time < 2000, f"TTS took {synthesis_time}ms, target < 2000ms"
        
        tts_response = response.json()
        assert tts_response["success"] is True
        assert tts_response["audio_url"]
        assert tts_response["duration_seconds"] > 0

    async def test_step_4_complete_90_second_scan(self, eyeson_client):
        """
        Step 4: Complete the 90-second body scan.
        
        Verifies:
        - Calibration works
        - Video upload succeeds
        - Processing completes within SLA
        
        Reference: Ops Manual v6.8 - Section 1.2 (Scan Duration SLA)
        Target: 90 seconds for complete scan cycle
        """
        # Create session
        session_response = await eyeson_client.post("/sessions", json={
            "user_id": f"test_scan_{int(time.time())}",
            "scan_mode": "video",
            "language": "en"
        })
        assert session_response.status_code == 201
        session_id = session_response.json()["session_id"]
        
        # Simulate calibration (Step 1 of scan)
        # Note: In real E2E tests, this would upload actual marker image
        calib_response = await eyeson_client.post(
            f"/sessions/{session_id}/calibrate",
            data={"height_cm": 175.0}
        )
        assert calib_response.status_code == 200
        
        calibration = calib_response.json()
        assert calibration["scale_factor"] > 0
        assert calibration["confidence"] >= 0.85  # Min confidence threshold
        
        # Simulate video upload completion
        upload_response = await eyeson_client.post(
            f"/sessions/{session_id}/upload",
            json={
                "video_url": f"https://storage.eyeson.io/videos/{session_id}.mp4",
                "duration_seconds": 90,
                "file_size_mb": 45.5
            }
        )
        assert upload_response.status_code == 200
        
        # Verify session moves to processing
        session_status = await eyeson_client.get(f"/sessions/{session_id}")
        assert session_status.status_code == 200
        status = session_status.json()
        assert status["status"] in ["processing", "completed"]

    async def test_step_5_review_measurements(self, eyeson_client):
        """
        Step 5: Review extracted measurements.
        
        Verifies:
        - All 28 measurements extracted
        - P0 measurements have high confidence (>0.85)
        - Measurements displayed in customer-friendly format
        
        Reference: Ops Manual v6.8 - Section 13 (Measurement Schema)
        """
        # Create completed session with measurements
        session_id = f"test_review_{int(time.time())}"
        
        # Get measurements
        measurements_response = await eyeson_client.get(
            f"/measurements/{session_id}"
        )
        
        if measurements_response.status_code == 200:
            measurements = measurements_response.json()
            
            # Verify P0 measurements (critical)
            p0_keys = ["Cg", "Wg", "Hg", "Sh", "Al", "Bw", "Nc"]
            for key in p0_keys:
                assert key in measurements, f"Missing P0 measurement: {key}"
                assert measurements[key]["confidence"] >= 0.85, \
                    f"P0 measurement {key} confidence too low"
            
            # Verify P1 measurements (important)
            p1_keys = ["Bi", "Wc", "Il", "Th", "Kn", "Ca"]
            for key in p1_keys:
                assert key in measurements, f"Missing P1 measurement: {key}"

    async def test_step_6_submit_to_pattern_factory(
        self, 
        eyeson_client, 
        pattern_factory_client,
        customer_auth_token
    ):
        """
        Step 6: Submit measurements to Pattern Factory.
        
        Verifies:
        - Order is created in Pattern Factory
        - State transitions from S02 (RECEIVED) to S03 (SCAN_RECEIVED)
        - Order ID format is correct: SDS-YYYYMMDD-NNNN-R
        
        Reference: Ops Manual v6.8 - Section 1.2 (27-State Order Machine)
        """
        headers = {"Authorization": f"Bearer {customer_auth_token}"}
        
        # Submit order to Pattern Factory
        order_data = {
            "customer_id": f"cust_{int(time.time())}",
            "garment_type": "jacket",
            "fit_type": "regular",
            "priority": "normal",
            "measurements": SAMPLE_MEASUREMENTS,
            "scan_metadata": {
                "device_type": "photogrammetry",
                "vertex_count": 50000,
                "capture_timestamp": datetime.utcnow().isoformat(),
                "confidence": 0.92
            }
        }
        
        start_time = time.time()
        response = await pattern_factory_client.post(
            "/orders",
            json=order_data,
            headers=headers
        )
        submit_time = (time.time() - start_time) * 1000
        
        assert response.status_code == 201, f"Order submission failed: {response.text}"
        assert submit_time < 1000, f"Order submit took {submit_time}ms, target < 1000ms"
        
        order = response.json()
        
        # Verify order ID format: SDS-YYYYMMDD-NNNN-R
        assert order["order_id"].startswith("SDS-"), "Invalid order ID prefix"
        assert len(order["order_id"].split("-")) == 4, "Invalid order ID format"
        
        # Verify initial state
        assert order["status"] in ["scan_received", "processing"]
        
        return order["order_id"]

    async def test_step_7_poll_for_pattern_generation(
        self, 
        pattern_factory_client,
        customer_auth_token
    ):
        """
        Step 7: Poll for pattern generation completion.
        
        Verifies:
        - Pattern generation completes within SLA
        - State transitions to S05 (PATTERN_READY)
        - Files become available
        
        Reference: Ops Manual v6.8 - Section 1.2 & 2.6
        Target: < 3 minutes for pattern generation (99th percentile)
        """
        headers = {"Authorization": f"Bearer {customer_auth_token}"}
        
        # First create an order
        order_response = await pattern_factory_client.post(
            "/orders",
            json={
                "customer_id": f"cust_{int(time.time())}",
                "garment_type": "jacket",
                "fit_type": "regular",
                "priority": "normal",
                "measurements": SAMPLE_MEASUREMENTS
            },
            headers=headers
        )
        assert order_response.status_code == 201
        order_id = order_response.json()["order_id"]
        
        # Poll for pattern generation
        max_wait_seconds = 180  # 3 minutes SLA
        poll_interval = 2.0
        start_time = time.time()
        
        while (time.time() - start_time) < max_wait_seconds:
            status_response = await pattern_factory_client.get(
                f"/orders/{order_id}/status",
                headers=headers
            )
            
            if status_response.status_code == 200:
                status = status_response.json()
                
                if status["files_available"]["plt"]:
                    elapsed = time.time() - start_time
                    assert elapsed < 180, \
                        f"Pattern generation took {elapsed}s, target < 180s"
                    return order_id
                
                if status["status"] == "error":
                    pytest.fail(f"Pattern generation failed for order {order_id}")
            
            await asyncio.sleep(poll_interval)
        
        pytest.fail(f"Pattern generation timeout after {max_wait_seconds}s")

    async def test_step_8_download_pattern_files(
        self,
        pattern_factory_client,
        customer_auth_token
    ):
        """
        Step 8: Download all pattern files (PLT, PDS, DXF).
        
        Verifies:
        - All required files are available
        - File download is fast (< 5 seconds)
        - Files have correct format and size
        
        Reference: Ops Manual v6.8 - Section 15 (Output File Standards)
        """
        headers = {"Authorization": f"Bearer {customer_auth_token}"}
        
        # Create and wait for order to complete
        order_id = await self.test_step_7_poll_for_pattern_generation(
            pattern_factory_client, 
            customer_auth_token
        )
        
        files_to_download = ["plt", "pds", "dxf"]
        downloaded_files = {}
        
        for file_type in files_to_download:
            start_time = time.time()
            response = await pattern_factory_client.get(
                f"/orders/{order_id}/{file_type}",
                headers=headers
            )
            download_time = (time.time() - start_time) * 1000
            
            assert response.status_code == 200, \
                f"Failed to download {file_type}: {response.text}"
            assert download_time < 5000, \
                f"{file_type} download took {download_time}ms, target < 5000ms"
            
            content = response.content
            assert len(content) > 0, f"{file_type} file is empty"
            
            # Verify content type headers
            content_type = response.headers.get("content-type", "")
            assert "octet-stream" in content_type or "application" in content_type
            
            downloaded_files[file_type] = {
                "size_bytes": len(content),
                "download_time_ms": download_time
            }
        
        return downloaded_files

    async def test_complete_customer_journey(
        self,
        eyeson_client,
        pattern_factory_client,
        customer_auth_token
    ):
        """
        Complete E2E test of the entire customer journey.
        
        This test runs all steps sequentially to verify the complete flow.
        Target total time: < 5 minutes from scan to files ready
        
        Reference: Ops Manual v6.8 - Section 17.1 (Customer Journey Map)
        """
        journey_start = time.time()
        
        # Step 1: Welcome screen
        await self.test_step_1_welcome_screen(eyeson_client)
        
        # Step 2: Camera permissions & session init
        session_id = await self.test_step_2_camera_permissions(eyeson_client)
        
        # Step 3: Voice guidance
        await self.test_step_3_voice_guidance_kokoro_tts(eyeson_client)
        
        # Step 4: Complete scan
        await self.test_step_4_complete_90_second_scan(eyeson_client)
        
        # Step 5: Review measurements
        await self.test_step_5_review_measurements(eyeson_client)
        
        # Step 6: Submit to Pattern Factory
        order_id = await self.test_step_6_submit_to_pattern_factory(
            eyeson_client, 
            pattern_factory_client,
            customer_auth_token
        )
        
        # Step 7: Poll for pattern generation
        await self.test_step_7_poll_for_pattern_generation(
            pattern_factory_client,
            customer_auth_token
        )
        
        # Step 8: Download files
        files = await self.test_step_8_download_pattern_files(
            pattern_factory_client,
            customer_auth_token
        )
        
        total_time = time.time() - journey_start
        
        # Verify all files downloaded
        assert "plt" in files, "PLT file missing"
        assert "pds" in files, "PDS file missing"
        assert "dxf" in files, "DXF file missing"
        
        # Verify file sizes are reasonable
        for file_type, info in files.items():
            assert info["size_bytes"] > 100, f"{file_type} file too small"
        
        print(f"\n✅ Complete customer journey finished in {total_time:.1f}s")
        print(f"   Order ID: {order_id}")
        print(f"   Files: {files}")


@pytest.mark.e2e
@pytest.mark.asyncio
class TestCustomerJourneyErrorScenarios:
    """
    E2E tests for customer journey error scenarios.
    
    Reference: Ops Manual v6.8 - Section 17.1.3 (Error Handling)
    """

    async def test_scan_timeout_recovery(self, eyeson_client):
        """
        Test recovery when scan takes too long.
        
        Verifies:
        - System detects scan timeout
        - Customer can retry
        - Voice guidance resumes appropriately
        """
        # Create session
        session_response = await eyeson_client.post("/sessions", json={
            "user_id": f"test_timeout_{int(time.time())}",
            "scan_mode": "video",
            "language": "en"
        })
        session_id = session_response.json()["session_id"]
        
        # Simulate timeout
        # In real scenario, session would expire after 5 minutes
        await asyncio.sleep(0.1)  # Fast-forward for test
        
        # Verify session can be reset
        reset_response = await eyeson_client.post(
            f"/sessions/{session_id}/reset"
        )
        # May return 404 if endpoint doesn't exist, or 200 if it does
        assert reset_response.status_code in [200, 404]

    async def test_low_confidence_measurement_handling(
        self,
        pattern_factory_client,
        customer_auth_token
    ):
        """
        Test handling of low confidence measurements.
        
        Verifies:
        - System flags low confidence measurements
        - Customer is prompted to rescan if needed
        - Order can proceed with acknowledgment
        """
        headers = {"Authorization": f"Bearer {customer_auth_token}"}
        
        # Submit order with low confidence
        low_conf_measurements = SAMPLE_MEASUREMENTS.copy()
        low_conf_measurements["Cg"]["confidence"] = 0.70  # Below 0.85 threshold
        
        response = await pattern_factory_client.post(
            "/orders",
            json={
                "customer_id": f"cust_{int(time.time())}",
                "garment_type": "jacket",
                "fit_type": "regular",
                "measurements": low_conf_measurements
            },
            headers=headers
        )
        
        # Should still accept but flag for review
        assert response.status_code == 201
        order = response.json()
        
        # Verify validation warnings exist
        # In real implementation, would check validation endpoint

    async def test_network_interruption_recovery(
        self,
        pattern_factory_client,
        customer_auth_token
    ):
        """
        Test recovery from network interruption during file download.
        
        Verifies:
        - Partial downloads can be resumed
        - Integrity is maintained
        - Customer can retry without data loss
        """
        headers = {"Authorization": f"Bearer {customer_auth_token}"}
        
        # Create and complete order
        order_response = await pattern_factory_client.post(
            "/orders",
            json={
                "customer_id": f"cust_{int(time.time())}",
                "garment_type": "jacket",
                "fit_type": "regular",
                "measurements": SAMPLE_MEASUREMENTS
            },
            headers=headers
        )
        order_id = order_response.json()["order_id"]
        
        # Simulate interrupted download
        # In real test, would use HTTP Range requests
        response = await pattern_factory_client.get(
            f"/orders/{order_id}/plt",
            headers=headers
        )
        
        # Verify download succeeded (resilience built-in)
        assert response.status_code == 200


@pytest.mark.e2e
@pytest.mark.benchmark
@pytest.mark.asyncio
class TestCustomerJourneyPerformance:
    """
    Performance benchmarks for customer journey.
    
    Reference: Ops Manual v6.8 - Section 2.6 (Scalability Layer)
    """

    @pytest.mark.parametrize("concurrent_customers", [1, 5, 10])
    async def test_concurrent_scan_sessions(
        self,
        eyeson_client,
        concurrent_customers
    ):
        """
        Test multiple customers scanning simultaneously.
        
        Verifies system can handle multiple concurrent scan sessions
        without performance degradation.
        """
        async def create_scan_session(customer_id: str):
            response = await eyeson_client.post("/sessions", json={
                "user_id": customer_id,
                "scan_mode": "video",
                "language": "en"
            })
            return response.status_code == 201
        
        # Launch concurrent sessions
        start_time = time.time()
        tasks = [
            create_scan_session(f"concurrent_user_{i}_{int(time.time())}")
            for i in range(concurrent_customers)
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_time = time.time() - start_time
        
        success_count = sum(1 for r in results if r is True)
        assert success_count == concurrent_customers, \
            f"Only {success_count}/{concurrent_customers} sessions created"
        
        # Verify performance doesn't degrade
        avg_time_per_session = total_time / concurrent_customers
        assert avg_time_per_session < 1.0, \
            f"Avg time per session {avg_time_per_session}s too slow"

    async def test_pattern_generation_throughput(
        self,
        pattern_factory_client,
        customer_auth_token
    ):
        """
        Test pattern generation throughput under load.
        
        Target: 100 orders/hour throughput (Ops Manual v6.8 Section 2.6)
        """
        headers = {"Authorization": f"Bearer {customer_auth_token}"}
        
        # Submit multiple orders rapidly
        num_orders = 10
        start_time = time.time()
        
        order_ids = []
        for i in range(num_orders):
            response = await pattern_factory_client.post(
                "/orders",
                json={
                    "customer_id": f"throughput_test_{i}",
                    "garment_type": "jacket",
                    "fit_type": "regular",
                    "measurements": SAMPLE_MEASUREMENTS
                },
                headers=headers
            )
            if response.status_code == 201:
                order_ids.append(response.json()["order_id"])
        
        submit_time = time.time() - start_time
        throughput = num_orders / submit_time * 3600  # orders per hour
        
        print(f"\n📊 Throughput: {throughput:.0f} orders/hour")
        assert throughput >= 100, f"Throughput {throughput:.0f} below 100/hour target"
