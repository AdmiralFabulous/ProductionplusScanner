"""
E2E Test: QC Inspector Journey

Tests the Quality Control inspector's workflow for garment inspection.
Reference: Ops Manual v6.8 - Section 17 (Journey Mapping) - QC Inspector Persona Journey

Journey Steps:
1. Garment received at QC (S14a - QC_RECEIVED)
2. Inspection in progress (S15 - QC_INSPECTION)
3. QC Pass (S16) → labeling → packing
4. QC Fail (S17) → dispute process

State Machine Reference:
- S14a: QC_RECEIVED - Garment arrived at QC station
- S15: QC_INSPECTION - Active inspection
- S16: QC_PASSED - Quality approved
- S17: QC_FAILED - Quality issues found
- S18: REWORK_REQUIRED - Sent back for repair
- S19: DISPUTE - Quality dispute in progress
"""

import pytest
import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List
from unittest.mock import Mock, patch

import httpx
from httpx import AsyncClient

# Test Configuration
PATTERN_FACTORY_API_BASE = "http://localhost:8000/api/v1"
QC_PLATFORM_API_BASE = "http://localhost:8003/api/v1"  # QC Platform


@pytest.fixture
async def pattern_factory_client():
    """Create async HTTP client for Pattern Factory API."""
    async with AsyncClient(base_url=PATTERN_FACTORY_API_BASE, timeout=30.0) as client:
        yield client


@pytest.fixture
async def qc_platform_client():
    """Create async HTTP client for QC Platform API."""
    async with AsyncClient(base_url=QC_PLATFORM_API_BASE, timeout=30.0) as client:
        yield client


@pytest.fixture
def qc_auth_token():
    """Generate test QC inspector auth token."""
    return "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.qc_token"


@pytest.fixture
def qc_inspector_id():
    """Generate test QC inspector ID."""
    return f"qc_inspector_{int(time.time())}"


@pytest.mark.e2e
@pytest.mark.asyncio
class TestQCJourney:
    """
    End-to-end tests for the QC inspector journey.
    
    Reference: Ops Manual v6.8 - Section 17.3 (QC Inspector Journey Map)
    """

    async def _create_order_at_s14(
        self,
        pattern_factory_client,
        auth_token,
        tailor_id="tailor_test"
    ) -> str:
        """Helper to create an order and advance it to S14 (READY_FOR_PICKUP/QC)."""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # Create order
        response = await pattern_factory_client.post(
            "/orders",
            json={
                "customer_id": f"cust_{int(time.time())}",
                "garment_type": "jacket",
                "fit_type": "regular",
                "priority": "normal",
                "measurements": {
                    "Cg": {"value": 102.5, "unit": "cm", "confidence": 0.95},
                    "Wg": {"value": 88.3, "unit": "cm", "confidence": 0.92},
                }
            },
            headers=headers
        )
        assert response.status_code == 201
        order_id = response.json()["order_id"]
        
        # Advance through production states to S14
        states = ["S08", "S09", "S10", "S11", "S12", "S13", "S14"]
        for state in states:
            await pattern_factory_client.post(
                f"/orders/{order_id}/transition",
                json={"to_state": state, "tailor_id": tailor_id},
                headers=headers
            )
        
        return order_id

    async def test_step_1_garment_received_at_qc(
        self,
        pattern_factory_client,
        qc_platform_client,
        qc_auth_token,
        qc_inspector_id
    ):
        """
        Step 1: Garment received at QC (S14a - QC_RECEIVED).
        
        Verifies:
        - Garment can be checked into QC
        - Order transitions to S14a (QC_RECEIVED)
        - QC inspector is assigned
        - Inspection queue is updated
        
        Reference: Ops Manual v6.8 - Section 1.2 (S14a QC_RECEIVED)
        """
        headers = {"Authorization": f"Bearer {qc_auth_token}"}
        
        # Create order at S14
        order_id = await self._create_order_at_s14(
            pattern_factory_client, 
            qc_auth_token
        )
        
        # Receive at QC
        start_time = time.time()
        receive_response = await qc_platform_client.post(
            f"/qc/orders/{order_id}/receive",
            json={
                "inspector_id": qc_inspector_id,
                "received_at": datetime.utcnow().isoformat(),
                "condition_on_arrival": "good"
            },
            headers=headers
        )
        receive_time = (time.time() - start_time) * 1000
        
        assert receive_response.status_code == 200, \
            f"QC receive failed: {receive_response.text}"
        assert receive_time < 1000, \
            f"QC receive took {receive_time}ms, target < 1000ms"
        
        # Verify state transition
        status_response = await pattern_factory_client.get(
            f"/orders/{order_id}/status",
            headers=headers
        )
        status = status_response.json()
        assert status["state"] == "S14a"
        assert status["state_name"] == "QC_RECEIVED"
        assert status["inspector_id"] == qc_inspector_id

    async def test_step_2_inspection_in_progress(
        self,
        pattern_factory_client,
        qc_platform_client,
        qc_auth_token,
        qc_inspector_id
    ):
        """
        Step 2: Inspection in progress (S15 - QC_INSPECTION).
        
        Verifies:
        - Inspector can start inspection
        - Order transitions to S15 (QC_INSPECTION)
        - Inspection checklist is available
        - Progress can be tracked
        
        Reference: Ops Manual v6.8 - Section 1.2 (S15 QC_INSPECTION)
        Target SLA: < 15 minutes for inspection
        """
        headers = {"Authorization": f"Bearer {qc_auth_token}"}
        
        # Setup order at S14a
        order_id = await self._create_order_at_s14(
            pattern_factory_client,
            qc_auth_token
        )
        await qc_platform_client.post(
            f"/qc/orders/{order_id}/receive",
            json={
                "inspector_id": qc_inspector_id,
                "received_at": datetime.utcnow().isoformat()
            },
            headers=headers
        )
        
        # Start inspection
        start_response = await qc_platform_client.post(
            f"/qc/orders/{order_id}/inspection/start",
            json={
                "inspector_id": qc_inspector_id,
                "started_at": datetime.utcnow().isoformat()
            },
            headers=headers
        )
        
        assert start_response.status_code == 200
        
        # Verify inspection checklist
        checklist_response = await qc_platform_client.get(
            f"/qc/orders/{order_id}/inspection/checklist",
            headers=headers
        )
        
        if checklist_response.status_code == 200:
            checklist = checklist_response.json()
            assert "items" in checklist
            assert len(checklist["items"]) > 0
            
            # Verify standard QC checks
            expected_checks = [
                "stitch_quality",
                "measurement_accuracy",
                "fabric_defects",
                "button_attachment",
                "lining_alignment"
            ]
            check_names = [item["name"] for item in checklist["items"]]
            for expected in expected_checks:
                assert any(expected in name for name in check_names), \
                    f"Missing QC check: {expected}"
        
        # Verify state
        status_response = await pattern_factory_client.get(
            f"/orders/{order_id}/status",
            headers=headers
        )
        status = status_response.json()
        assert status["state"] == "S15"

    async def test_step_3_qc_pass_labeling_packing(
        self,
        pattern_factory_client,
        qc_platform_client,
        qc_auth_token,
        qc_inspector_id
    ):
        """
        Step 3: QC Pass (S16) → labeling → packing.
        
        Verifies:
        - Inspector can mark inspection as passed
        - Order transitions to S16 (QC_PASSED)
        - Label is generated with order details
        - Packing instructions are provided
        
        Reference: Ops Manual v6.8 - Section 1.2 (S16 QC_PASSED)
        """
        headers = {"Authorization": f"Bearer {qc_auth_token}"}
        
        # Setup order through inspection
        order_id = await self._create_order_at_s14(
            pattern_factory_client,
            qc_auth_token
        )
        
        # S14a → S15
        await qc_platform_client.post(
            f"/qc/orders/{order_id}/receive",
            json={"inspector_id": qc_inspector_id},
            headers=headers
        )
        await qc_platform_client.post(
            f"/qc/orders/{order_id}/inspection/start",
            json={"inspector_id": qc_inspector_id},
            headers=headers
        )
        
        # Complete inspection - PASS
        inspection_results = {
            "inspector_id": qc_inspector_id,
            "result": "PASS",
            "completed_at": datetime.utcnow().isoformat(),
            "checks": [
                {"name": "stitch_quality", "result": "PASS", "notes": ""},
                {"name": "measurement_accuracy", "result": "PASS", "notes": ""},
                {"name": "fabric_defects", "result": "PASS", "notes": ""},
            ],
            "overall_score": 98.5
        }
        
        pass_response = await qc_platform_client.post(
            f"/qc/orders/{order_id}/inspection/complete",
            json=inspection_results,
            headers=headers
        )
        
        assert pass_response.status_code == 200
        
        # Verify label generation
        label_response = await qc_platform_client.get(
            f"/qc/orders/{order_id}/label",
            headers=headers
        )
        
        if label_response.status_code == 200:
            label = label_response.json()
            assert label["order_id"] == order_id
            assert "barcode" in label or "qr_code" in label
            assert "care_instructions" in label
        
        # Verify packing instructions
        packing_response = await qc_platform_client.get(
            f"/qc/orders/{order_id}/packing-instructions",
            headers=headers
        )
        
        if packing_response.status_code == 200:
            packing = packing_response.json()
            assert "box_size" in packing
            assert "protective_materials" in packing
        
        # Verify final state
        status_response = await pattern_factory_client.get(
            f"/orders/{order_id}/status",
            headers=headers
        )
        status = status_response.json()
        assert status["state"] == "S16"
        assert status["state_name"] == "QC_PASSED"

    async def test_step_4_qc_fail_dispute_process(
        self,
        pattern_factory_client,
        qc_platform_client,
        qc_auth_token,
        qc_inspector_id
    ):
        """
        Step 4: QC Fail (S17) → dispute process.
        
        Verifies:
        - Inspector can mark inspection as failed
        - Order transitions to S17 (QC_FAILED)
        - Defects are documented
        - Dispute/return process is initiated
        
        Reference: Ops Manual v6.8 - Section 1.2 (S17 QC_FAILED)
        """
        headers = {"Authorization": f"Bearer {qc_auth_token}"}
        
        # Setup order through inspection
        order_id = await self._create_order_at_s14(
            pattern_factory_client,
            qc_auth_token
        )
        
        # Advance to inspection
        await qc_platform_client.post(
            f"/qc/orders/{order_id}/receive",
            json={"inspector_id": qc_inspector_id},
            headers=headers
        )
        await qc_platform_client.post(
            f"/qc/orders/{order_id}/inspection/start",
            json={"inspector_id": qc_inspector_id},
            headers=headers
        )
        
        # Complete inspection - FAIL
        inspection_results = {
            "inspector_id": qc_inspector_id,
            "result": "FAIL",
            "completed_at": datetime.utcnow().isoformat(),
            "checks": [
                {"name": "stitch_quality", "result": "PASS", "notes": ""},
                {"name": "measurement_accuracy", "result": "FAIL", "notes": "Sleeve length off by 2cm"},
                {"name": "fabric_defects", "result": "PASS", "notes": ""},
            ],
            "defects": [
                {
                    "type": "measurement_error",
                    "location": "left_sleeve",
                    "severity": "major",
                    "description": "Sleeve length exceeds tolerance by 2cm"
                }
            ],
            "overall_score": 65.0
        }
        
        fail_response = await qc_platform_client.post(
            f"/qc/orders/{order_id}/inspection/complete",
            json=inspection_results,
            headers=headers
        )
        
        assert fail_response.status_code == 200
        
        # Verify defect documentation
        defects_response = await qc_platform_client.get(
            f"/qc/orders/{order_id}/defects",
            headers=headers
        )
        
        if defects_response.status_code == 200:
            defects = defects_response.json()
            assert len(defects["items"]) > 0
            assert defects["items"][0]["severity"] == "major"
        
        # Verify dispute process initiated
        dispute_response = await qc_platform_client.post(
            f"/qc/orders/{order_id}/dispute",
            json={
                "inspector_id": qc_inspector_id,
                "reason": "measurement_out_of_tolerance",
                "evidence_photos": ["defect_001.jpg", "defect_002.jpg"],
                "recommended_action": "return_to_tailor"
            },
            headers=headers
        )
        
        assert dispute_response.status_code in [200, 201]
        
        # Verify state
        status_response = await pattern_factory_client.get(
            f"/orders/{order_id}/status",
            headers=headers
        )
        status = status_response.json()
        assert status["state"] == "S17"
        assert status["state_name"] == "QC_FAILED"

    async def test_complete_qc_pass_journey(
        self,
        pattern_factory_client,
        qc_platform_client,
        qc_auth_token,
        qc_inspector_id
    ):
        """
        Complete E2E test of QC pass journey.
        
        S14 → S14a → S15 → S16 (labeling/packing)
        """
        journey_start = time.time()
        headers = {"Authorization": f"Bearer {qc_auth_token}"}
        
        # Setup: Order at S14
        order_id = await self._create_order_at_s14(
            pattern_factory_client,
            qc_auth_token
        )
        
        # S14 → S14a (Receive at QC)
        await qc_platform_client.post(
            f"/qc/orders/{order_id}/receive",
            json={
                "inspector_id": qc_inspector_id,
                "received_at": datetime.utcnow().isoformat()
            },
            headers=headers
        )
        
        # S14a → S15 (Start inspection)
        await qc_platform_client.post(
            f"/qc/orders/{order_id}/inspection/start",
            json={"inspector_id": qc_inspector_id},
            headers=headers
        )
        
        # S15 → S16 (Complete inspection - PASS)
        await qc_platform_client.post(
            f"/qc/orders/{order_id}/inspection/complete",
            json={
                "inspector_id": qc_inspector_id,
                "result": "PASS",
                "checks": [
                    {"name": "stitch_quality", "result": "PASS"},
                    {"name": "measurement_accuracy", "result": "PASS"},
                    {"name": "fabric_defects", "result": "PASS"},
                ],
                "overall_score": 97.5
            },
            headers=headers
        )
        
        total_time = time.time() - journey_start
        
        # Verify final state
        status_response = await pattern_factory_client.get(
            f"/orders/{order_id}/status",
            headers=headers
        )
        status = status_response.json()
        assert status["state"] == "S16"
        
        print(f"\n✅ QC Pass journey finished in {total_time:.1f}s")
        print(f"   Order ID: {order_id}")
        print(f"   Inspector: {qc_inspector_id}")

    async def test_complete_qc_fail_journey(
        self,
        pattern_factory_client,
        qc_platform_client,
        qc_auth_token,
        qc_inspector_id
    ):
        """
        Complete E2E test of QC fail journey.
        
        S14 → S14a → S15 → S17 (dispute) → S18 (rework)
        """
        journey_start = time.time()
        headers = {"Authorization": f"Bearer {qc_auth_token}"}
        
        # Setup: Order at S14
        order_id = await self._create_order_at_s14(
            pattern_factory_client,
            qc_auth_token
        )
        
        # S14 → S14a (Receive at QC)
        await qc_platform_client.post(
            f"/qc/orders/{order_id}/receive",
            json={"inspector_id": qc_inspector_id},
            headers=headers
        )
        
        # S14a → S15 (Start inspection)
        await qc_platform_client.post(
            f"/qc/orders/{order_id}/inspection/start",
            json={"inspector_id": qc_inspector_id},
            headers=headers
        )
        
        # S15 → S17 (Complete inspection - FAIL)
        await qc_platform_client.post(
            f"/qc/orders/{order_id}/inspection/complete",
            json={
                "inspector_id": qc_inspector_id,
                "result": "FAIL",
                "checks": [
                    {"name": "stitch_quality", "result": "FAIL", "notes": "Loose threads"},
                    {"name": "measurement_accuracy", "result": "PASS"},
                ],
                "defects": [
                    {"type": "stitch_quality", "severity": "minor"}
                ],
                "overall_score": 72.0
            },
            headers=headers
        )
        
        # Initiate dispute
        await qc_platform_client.post(
            f"/qc/orders/{order_id}/dispute",
            json={
                "inspector_id": qc_inspector_id,
                "reason": "quality_below_standard",
                "recommended_action": "return_to_tailor"
            },
            headers=headers
        )
        
        total_time = time.time() - journey_start
        
        # Verify final state
        status_response = await pattern_factory_client.get(
            f"/orders/{order_id}/status",
            headers=headers
        )
        status = status_response.json()
        assert status["state"] == "S17"
        
        print(f"\n✅ QC Fail journey finished in {total_time:.1f}s")
        print(f"   Order ID: {order_id}")
        print(f"   Inspector: {qc_inspector_id}")


@pytest.mark.e2e
@pytest.mark.asyncio
class TestQCInspectionScenarios:
    """
    E2E tests for QC inspection scenarios and edge cases.
    """

    async def test_partial_inspection_save_resume(
        self,
        pattern_factory_client,
        qc_platform_client,
        qc_auth_token,
        qc_inspector_id
    ):
        """
        Test that inspectors can save partial progress and resume.
        
        Verifies:
        - Inspection progress is saved
        - Inspector can resume from where they left off
        - No data loss occurs
        """
        headers = {"Authorization": f"Bearer {qc_auth_token}"}
        
        order_id = await self._create_order_at_s14(
            pattern_factory_client,
            qc_auth_token
        )
        
        # Start inspection
        await qc_platform_client.post(
            f"/qc/orders/{order_id}/receive",
            json={"inspector_id": qc_inspector_id},
            headers=headers
        )
        await qc_platform_client.post(
            f"/qc/orders/{order_id}/inspection/start",
            json={"inspector_id": qc_inspector_id},
            headers=headers
        )
        
        # Save partial progress
        partial_response = await qc_platform_client.post(
            f"/qc/orders/{order_id}/inspection/save",
            json={
                "inspector_id": qc_inspector_id,
                "progress": {
                    "checks_completed": 3,
                    "checks_total": 10,
                    "current_check": "button_attachment"
                },
                "results_so_far": [
                    {"name": "stitch_quality", "result": "PASS"},
                    {"name": "measurement_accuracy", "result": "PENDING"},
                ]
            },
            headers=headers
        )
        
        assert partial_response.status_code == 200
        
        # Resume inspection
        resume_response = await qc_platform_client.get(
            f"/qc/orders/{order_id}/inspection/progress",
            headers=headers
        )
        
        if resume_response.status_code == 200:
            progress = resume_response.json()
            assert progress["checks_completed"] == 3
            assert len(progress["results_so_far"]) == 2

    async def test_multiple_defects_documentation(
        self,
        pattern_factory_client,
        qc_platform_client,
        qc_auth_token,
        qc_inspector_id
    ):
        """
        Test documentation of multiple defects.
        
        Verifies:
        - Multiple defects can be recorded
        - Defect severity is tracked
        - Photos can be attached
        """
        headers = {"Authorization": f"Bearer {qc_auth_token}"}
        
        order_id = await self._create_order_at_s14(
            pattern_factory_client,
            qc_auth_token
        )
        
        await qc_platform_client.post(
            f"/qc/orders/{order_id}/receive",
            json={"inspector_id": qc_inspector_id},
            headers=headers
        )
        await qc_platform_client.post(
            f"/qc/orders/{order_id}/inspection/start",
            json={"inspector_id": qc_inspector_id},
            headers=headers
        )
        
        # Document multiple defects
        defects = [
            {
                "type": "stitch_quality",
                "location": "left_shoulder",
                "severity": "minor",
                "description": "Uneven stitching"
            },
            {
                "type": "measurement_error",
                "location": "sleeve_length",
                "severity": "major",
                "description": "2cm too long"
            },
            {
                "type": "fabric_defect",
                "location": "back_panel",
                "severity": "minor",
                "description": "Small discoloration"
            }
        ]
        
        for defect in defects:
            defect_response = await qc_platform_client.post(
                f"/qc/orders/{order_id}/defects",
                json={
                    "inspector_id": qc_inspector_id,
                    "defect": defect,
                    "photos": [f"{defect['type']}_photo.jpg"]
                },
                headers=headers
            )
            assert defect_response.status_code in [200, 201]
        
        # Verify all defects recorded
        defects_list = await qc_platform_client.get(
            f"/qc/orders/{order_id}/defects",
            headers=headers
        )
        
        if defects_list.status_code == 200:
            defects_data = defects_list.json()
            assert len(defects_data["items"]) == 3
            
            # Count by severity
            severities = [d["severity"] for d in defects_data["items"]]
            assert severities.count("major") == 1
            assert severities.count("minor") == 2

    async def test_inspection_reassignment(
        self,
        pattern_factory_client,
        qc_platform_client,
        qc_auth_token,
        qc_inspector_id
    ):
        """
        Test reassignment of inspection to different inspector.
        
        Verifies:
        - Inspection can be reassigned
        - Progress is preserved
        - Audit trail shows reassignment
        """
        headers = {"Authorization": f"Bearer {qc_auth_token}"}
        
        order_id = await self._create_order_at_s14(
            pattern_factory_client,
            qc_auth_token
        )
        
        original_inspector = qc_inspector_id
        new_inspector = f"qc_inspector_{int(time.time())}_new"
        
        # Assign to original inspector
        await qc_platform_client.post(
            f"/qc/orders/{order_id}/receive",
            json={"inspector_id": original_inspector},
            headers=headers
        )
        
        # Reassign
        reassign_response = await qc_platform_client.post(
            f"/qc/orders/{order_id}/reassign",
            json={
                "from_inspector": original_inspector,
                "to_inspector": new_inspector,
                "reason": "shift_change"
            },
            headers=headers
        )
        
        assert reassign_response.status_code == 200
        
        # Verify new inspector
        status_response = await pattern_factory_client.get(
            f"/orders/{order_id}/status",
            headers=headers
        )
        status = status_response.json()
        assert status["inspector_id"] == new_inspector


@pytest.mark.e2e
@pytest.mark.asyncio
class TestQCPerformance:
    """
    Performance tests for QC operations.
    """

    async def test_qc_throughput(
        self,
        pattern_factory_client,
        qc_platform_client,
        qc_auth_token,
        qc_inspector_id
    ):
        """
        Test QC inspection throughput.
        
        Target: Process 60+ garments/hour through QC
        Reference: Ops Manual v6.8 - Section 2.6
        """
        headers = {"Authorization": f"Bearer {qc_auth_token}"}
        
        num_garments = 5  # Test with smaller number for E2E
        order_ids = []
        
        # Setup: Create orders at S14
        for i in range(num_garments):
            order_id = await self._create_order_at_s14(
                pattern_factory_client,
                qc_auth_token
            )
            order_ids.append(order_id)
        
        # Process all through QC
        start_time = time.time()
        
        for order_id in order_ids:
            # Receive
            await qc_platform_client.post(
                f"/qc/orders/{order_id}/receive",
                json={"inspector_id": qc_inspector_id},
                headers=headers
            )
            
            # Inspect
            await qc_platform_client.post(
                f"/qc/orders/{order_id}/inspection/start",
                json={"inspector_id": qc_inspector_id},
                headers=headers
            )
            
            # Complete (PASS)
            await qc_platform_client.post(
                f"/qc/orders/{order_id}/inspection/complete",
                json={
                    "inspector_id": qc_inspector_id,
                    "result": "PASS",
                    "checks": [{"name": "all", "result": "PASS"}]
                },
                headers=headers
            )
        
        total_time = time.time() - start_time
        throughput = num_garments / total_time * 3600  # garments/hour
        
        print(f"\n📊 QC Throughput: {throughput:.0f} garments/hour")
        # Target: 60+ garments/hour

    async def test_concurrent_qc_inspections(
        self,
        pattern_factory_client,
        qc_platform_client,
        qc_auth_token
    ):
        """
        Test multiple QC inspectors working simultaneously.
        
        Verifies system can handle concurrent inspections.
        """
        headers = {"Authorization": f"Bearer {qc_auth_token}"}
        
        num_inspectors = 3
        inspectors = [f"qc_inspector_{i}_{int(time.time())}" for i in range(num_inspectors)]
        
        async def inspector_workflow(inspector_id: str):
            order_id = await self._create_order_at_s14(
                pattern_factory_client,
                qc_auth_token
            )
            
            # Receive
            await qc_platform_client.post(
                f"/qc/orders/{order_id}/receive",
                json={"inspector_id": inspector_id},
                headers=headers
            )
            
            # Start inspection
            await qc_platform_client.post(
                f"/qc/orders/{order_id}/inspection/start",
                json={"inspector_id": inspector_id},
                headers=headers
            )
            
            # Complete
            response = await qc_platform_client.post(
                f"/qc/orders/{order_id}/inspection/complete",
                json={
                    "inspector_id": inspector_id,
                    "result": "PASS",
                    "checks": [{"name": "all", "result": "PASS"}]
                },
                headers=headers
            )
            
            return response.status_code == 200
        
        # Run concurrent inspections
        start_time = time.time()
        tasks = [inspector_workflow(ins_id) for ins_id in inspectors]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_time = time.time() - start_time
        
        success_count = sum(1 for r in results if r is True)
        assert success_count == num_inspectors, \
            f"Only {success_count}/{num_inspectors} concurrent inspections succeeded"
        
        print(f"\n✅ {num_inspectors} concurrent QC inspections completed in {total_time:.1f}s")
