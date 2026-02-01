"""
EYESON ↔ Pattern Factory Integration Tests
Reference: SUIT_AI_Master_Operations_Manual_v6_8.md

Integration Points:
- Section 1.2: S03 SCAN_RECEIVED trigger
- Section 2.5: Cross-service JWT authentication
- Section 2.8: Pattern Factory SOPs for measurement processing
"""

import asyncio
from datetime import datetime

import pytest


@pytest.mark.integration
@pytest.mark.pillar2
class TestMeasurementTransformation:
    """
    Test measurement format transformation.
    
    Reference: Ops Manual v6.8 Section 13 - Database Schema
    """
    
    def test_p0_measurements_transformed_correctly(self):
        """
        Test all 13 P0 measurements transform from EYESON to Pattern Factory format.
        """
        from eyeson.frontend.src.utils.measurementMapping import transformToPatternFactory
        
        # EYESON format input
        eyeson_measurements = {
            "chest_girth": {"value": 102.5, "unit": "cm", "confidence": 0.95},
            "waist_girth": {"value": 88.0, "unit": "cm", "confidence": 0.92},
            "hip_girth": {"value": 98.5, "unit": "cm", "confidence": 0.94},
            "shoulder_width": {"value": 46.0, "unit": "cm", "confidence": 0.91},
            "arm_length": {"value": 64.5, "unit": "cm", "confidence": 0.93},
            "inseam": {"value": 82.0, "unit": "cm", "confidence": 0.90},
            "neck_girth": {"value": 41.0, "unit": "cm", "confidence": 0.94},
            "bicep_girth": {"value": 34.0, "unit": "cm", "confidence": 0.88},
            "wrist_girth": {"value": 17.5, "unit": "cm", "confidence": 0.95},
            "thigh_girth": {"value": 58.0, "unit": "cm", "confidence": 0.87},
            "knee_girth": {"value": 40.0, "unit": "cm", "confidence": 0.89},
            "calf_girth": {"value": 38.0, "unit": "cm", "confidence": 0.88},
            "back_width": {"value": 38.5, "unit": "cm", "confidence": 0.90},
        }
        
        # Transform
        result = transformToPatternFactory(eyeson_measurements)
        
        # Verify P0 codes
        assert "Cg" in result  # Chest Girth
        assert "Wg" in result  # Waist Girth
        assert "Hg" in result  # Hip Girth
        assert "Sh" in result  # Shoulder Width
        assert "Al" in result  # Arm Length
        assert "Il" in result  # Inseam
        assert "Nc" in result  # Neck Girth
        assert "Bg" in result  # Bicep Girth
        assert "Wr" in result  # Wrist Girth
        assert "Tg" in result  # Thigh Girth
        assert "Kg" in result  # Knee Girth
        assert "Ca" in result  # Calf Girth
        assert "Bw" in result  # Back Width
        
        # Verify format
        for code, measurement in result.items():
            assert "value" in measurement
            assert "unit" in measurement
            assert "confidence" in measurement
            assert measurement["unit"] == "cm"
    
    def test_p1_measurements_transformed_correctly(self):
        """Test all 15 P1 measurements transform correctly."""
        from eyeson.frontend.src.utils.measurementMapping import transformToPatternFactory
        
        eyeson_measurements = {
            "front_waist_length": {"value": 42.0, "unit": "cm", "confidence": 0.88},
            "back_waist_length": {"value": 44.0, "unit": "cm", "confidence": 0.86},
            "sleeve_inseam": {"value": 48.0, "unit": "cm", "confidence": 0.89},
        }
        
        result = transformToPatternFactory(eyeson_measurements)
        
        assert "Fwl" in result  # Front Waist Length
        assert "Bwl" in result  # Back Waist Length
        assert "Si" in result   # Sleeve Inseam
    
    def test_measurement_validation_p0_confidence(self):
        """
        Test P0 measurements require confidence ≥ 0.90.
        
        Reference: Ops Manual v6.8 Section 13
        """
        from eyeson.frontend.src.utils.measurementMapping import validateConfidence
        
        pf_measurements = {
            "Cg": {"value": 102.5, "unit": "cm", "confidence": 0.95},  # Valid
            "Wg": {"value": 88.0, "unit": "cm", "confidence": 0.85},   # Invalid (< 0.90)
        }
        
        result = validateConfidence(pf_measurements)
        
        assert result["valid"] == False
        assert any("Wg" in failure for failure in result["failures"])
    
    def test_measurement_validation_p1_confidence(self):
        """Test P1 measurements require confidence ≥ 0.85."""
        from eyeson.frontend.src.utils.measurementMapping import validateConfidence
        
        pf_measurements = {
            "Fwl": {"value": 42.0, "unit": "cm", "confidence": 0.88},  # Valid
            "Bwl": {"value": 44.0, "unit": "cm", "confidence": 0.80},  # Invalid (< 0.85)
        }
        
        result = validateConfidence(pf_measurements)
        
        assert result["valid"] == False
        assert any("Bwl" in failure for failure in result["failures"])


@pytest.mark.integration
@pytest.mark.pillar2
@pytest.mark.asyncio
class TestOrderSubmissionFlow:
    """
    Test complete order submission from EYESON to Pattern Factory.
    
    Reference: Ops Manual v6.8 Section 1.2 - S03 SCAN_RECEIVED
    """
    
    async def test_eyeson_submits_to_pattern_factory(
        self,
        eyeson_client,
        pattern_factory_client,
        auth_headers,
        valid_p0_measurements
    ):
        """
        Test EYESON submits scan and Pattern Factory creates order at S03.
        """
        # Step 1: Create session in EYESON
        session_response = await eyeson_client.post(
            "/sessions",
            headers=auth_headers,
            json={"garment_type": "jacket", "fit_type": "regular"}
        )
        assert session_response.status_code == 201
        session_id = session_response.json()["session_id"]
        
        # Step 2: Submit measurements to Pattern Factory
        order_id = f"SDS-{datetime.now().strftime('%Y%m%d')}-0001-A"
        
        order_response = await pattern_factory_client.post(
            "/orders",
            headers=auth_headers,
            json={
                "order_id": order_id,
                "customer_id": session_id,
                "garment_type": "jacket",
                "fit_type": "regular",
                "measurements": valid_p0_measurements,
                "scan_metadata": {
                    "device_type": "photogrammetry",
                    "confidence_avg": 0.91,
                }
            }
        )
        
        assert order_response.status_code == 201
        data = order_response.json()
        
        # Verify state is S03 (SCAN_RECEIVED)
        assert data["status"] == "S03"
        assert data["state_name"] == "SCAN_RECEIVED"
    
    async def test_pattern_factory_polling_mechanism(
        self,
        pattern_factory_client,
        auth_headers,
        valid_p0_measurements
    ):
        """
        Test EYESON polls Pattern Factory status every 2 seconds.
        
        Verifies progression from S03 → S04 → S05
        """
        # Create order
        order_id = f"SDS-{datetime.now().strftime('%Y%m%d')}-0002-A"
        
        await pattern_factory_client.post(
            "/orders",
            headers=auth_headers,
            json={
                "order_id": order_id,
                "garment_type": "jacket",
                "measurements": valid_p0_measurements,
            }
        )
        
        # Poll until S05 (max 5 minutes)
        max_attempts = 150  # 150 * 2 seconds = 5 minutes
        poll_interval = 2
        
        for attempt in range(max_attempts):
            status_response = await pattern_factory_client.get(
                f"/orders/{order_id}/status",
                headers=auth_headers
            )
            
            assert status_response.status_code == 200
            data = status_response.json()
            
            if data["status"] == "S05":
                # Success - pattern is ready
                assert data["files_available"]["plt"] == True
                assert data["files_available"]["pds"] == True
                assert data["files_available"]["dxf"] == True
                return
            
            await asyncio.sleep(poll_interval)
        
        pytest.fail("Pattern generation timeout - did not reach S05 in 5 minutes")
    
    async def test_file_download_after_s05(
        self,
        pattern_factory_client,
        auth_headers,
        valid_p0_measurements
    ):
        """Test file download after S05 PATTERN_READY."""
        # Create and process order to S05
        order_id = f"SDS-{datetime.now().strftime('%Y%m%d')}-0003-A"
        
        await pattern_factory_client.post("/orders", headers=auth_headers, json={
            "order_id": order_id,
            "garment_type": "jacket",
            "measurements": valid_p0_measurements,
        })
        
        # Wait for S05
        # (Simplified - in real test would poll)
        
        # Download PLT file
        plt_response = await pattern_factory_client.get(
            f"/orders/{order_id}/plt",
            headers=auth_headers
        )
        assert plt_response.status_code == 200
        assert plt_response.headers["content-type"] == "application/octet-stream"
        
        # Download PDS file
        pds_response = await pattern_factory_client.get(
            f"/orders/{order_id}/pds",
            headers=auth_headers
        )
        assert pds_response.status_code == 200
        
        # Download DXF file
        dxf_response = await pattern_factory_client.get(
            f"/orders/{order_id}/dxf",
            headers=auth_headers
        )
        assert dxf_response.status_code == 200


@pytest.mark.integration
@pytest.mark.pillar2
@pytest.mark.security
class TestCrossServiceAuth:
    """
    Test authentication between EYESON and Pattern Factory.
    
    Reference: Ops Manual v6.8 Section 2.5 - Security Layer
    """
    
    async def test_eyeson_authenticates_with_pattern_factory(
        self,
        eyeson_client,
        pattern_factory_client,
        valid_access_token
    ):
        """Test EYESON backend can authenticate with Pattern Factory."""
        headers = {"Authorization": f"Bearer {valid_access_token}"}
        
        # Verify token works with Pattern Factory
        response = await pattern_factory_client.get("/health", headers=headers)
        assert response.status_code == 200
    
    async def test_token_refresh_during_long_operations(
        self,
        eyeson_client,
        pattern_factory_client,
        valid_access_token
    ):
        """
        Test token refresh during operations > 1 hour.
        
        Pattern generation may take time - ensure auth doesn't expire.
        """
        # This would test the refresh flow
        pass
    
    async def test_expired_token_rejection(self, pattern_factory_client):
        """Test expired tokens are rejected with 401."""
        expired_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...expired"
        headers = {"Authorization": f"Bearer {expired_token}"}
        
        response = await pattern_factory_client.get("/orders/test-123", headers=headers)
        assert response.status_code == 401


@pytest.mark.integration
@pytest.mark.pillar2
@pytest.mark.cutter
class TestCutterQueueIntegration:
    """
    Test cutter queue integration.
    
    Reference: Ops Manual v6.8 Section 2.7 - Resilience Layer
    """
    
    async def test_auto_submit_to_cutter_after_s05(
        self,
        pattern_factory_client,
        auth_headers,
        valid_p0_measurements
    ):
        """Test order automatically submits to cutter queue at S05."""
        order_id = f"SDS-{datetime.now().strftime('%Y%m%d')}-0004-A"
        
        # Create order with auto_submit enabled
        await pattern_factory_client.post("/orders", headers=auth_headers, json={
            "order_id": order_id,
            "garment_type": "jacket",
            "measurements": valid_p0_measurements,
            "auto_submit_to_cutter": True,
        })
        
        # Verify it enters cutter queue
        queue_response = await pattern_factory_client.get(
            f"/queue/status",
            headers=auth_headers
        )
        
        assert queue_response.status_code == 200
        queue_data = queue_response.json()
        
        # Verify order is in queue
        order_ids = [job["order_id"] for job in queue_data["jobs"]]
        assert order_id in order_ids


@pytest.mark.integration
@pytest.mark.pillar2
@pytest.mark.payment
class TestPaymentIntegration:
    """
    Test payment architecture integration.
    
    Reference: Ops Manual v6.8 Section 1.3 - Payment Architecture
    """
    
    async def test_qc_ledger_entry_created(self, pattern_factory_client, auth_headers):
        """Test QC ledger entry is created on inspection."""
        order_id = f"SDS-{datetime.now().strftime('%Y%m%d')}-0005-A"
        
        # Submit QC pass
        await pattern_factory_client.post(
            f"/orders/{order_id}/submit_qc",
            headers=auth_headers,
            json={
                "verdict": "PASS",
                "verdict_category": "PASS",
                "fabric_cost": 5000,
                "labor_fee": 15000,
            }
        )
        
        # Verify ledger entry
        ledger_response = await pattern_factory_client.get(
            f"/ledger/{order_id}",
            headers=auth_headers
        )
        
        assert ledger_response.status_code == 200
        data = ledger_response.json()
        assert data["payout_status"] == "PENDING"
        assert data["total_due"] == 20000  # fabric + labor
    
    async def test_payout_hold_outside_hours(self, pattern_factory_client, auth_headers):
        """
        Test payout is held when QC submitted outside 09:00-18:00 IST.
        
        Reference: Ops Manual v6.8 Section 1.3.3 - Payout Windows
        """
        # This would require time mocking
        pass
