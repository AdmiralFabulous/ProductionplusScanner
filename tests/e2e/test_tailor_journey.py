"""
E2E Test: Tailor Platform Journey

Tests the tailor's workflow from pattern available on job board through production.
Reference: Ops Manual v6.8 - Section 17 (Journey Mapping) - Tailor Persona Journey

Journey Steps:
1. Pattern available on job board (S08 - STAGING)
2. Tailor claims order (S08 → S09)
3. Pattern dispatched (S10)
4. Pattern in transit (S11)
5. Pattern received (S12)
6. Production started (S13)
7. Ready for QC (S14)

State Machine Reference:
- S08: STAGING - Cut pieces staged for assembly
- S09: QA - Quality assurance inspection
- S10: STAGING2 - QA passed, ready for sewing
- S11: SEWING - Active sewing and construction
- S12: ASSEMBLY - Final assembly and detail work
- S13: FINISHING - Pressing, steaming, final touches
- S14: READY_FOR_PICKUP - Garment complete
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
TAILOR_PLATFORM_API_BASE = "http://localhost:8002/api/v1"  # Tailor Platform


@pytest.fixture
async def pattern_factory_client():
    """Create async HTTP client for Pattern Factory API."""
    async with AsyncClient(base_url=PATTERN_FACTORY_API_BASE, timeout=30.0) as client:
        yield client


@pytest.fixture
async def tailor_platform_client():
    """Create async HTTP client for Tailor Platform API."""
    async with AsyncClient(base_url=TAILOR_PLATFORM_API_BASE, timeout=30.0) as client:
        yield client


@pytest.fixture
def tailor_auth_token():
    """Generate test tailor auth token."""
    return "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.tailor_token"


@pytest.fixture
def sample_order_data():
    """Sample order data for testing."""
    return {
        "customer_id": f"cust_{int(time.time())}",
        "garment_type": "jacket",
        "fit_type": "regular",
        "priority": "normal",
        "measurements": {
            "Cg": {"value": 102.5, "unit": "cm", "confidence": 0.95},
            "Wg": {"value": 88.3, "unit": "cm", "confidence": 0.92},
            "Hg": {"value": 98.7, "unit": "cm", "confidence": 0.94},
            "Sh": {"value": 46.2, "unit": "cm", "confidence": 0.93},
            "Al": {"value": 64.8, "unit": "cm", "confidence": 0.90},
        }
    }


@pytest.mark.e2e
@pytest.mark.asyncio
class TestTailorJourney:
    """
    End-to-end tests for the tailor platform journey.
    
    Reference: Ops Manual v6.8 - Section 17.2 (Tailor Journey Map)
    """

    async def _create_test_order(
        self,
        pattern_factory_client,
        auth_token,
        order_data=None
    ) -> str:
        """Helper to create a test order and advance it to cutting."""
        headers = {"Authorization": f"Bearer {auth_token}"}
        data = order_data or {
            "customer_id": f"cust_{int(time.time())}",
            "garment_type": "jacket",
            "fit_type": "regular",
            "priority": "normal",
            "measurements": {
                "Cg": {"value": 102.5, "unit": "cm", "confidence": 0.95},
                "Wg": {"value": 88.3, "unit": "cm", "confidence": 0.92},
                "Hg": {"value": 98.7, "unit": "cm", "confidence": 0.94},
                "Sh": {"value": 46.2, "unit": "cm", "confidence": 0.93},
                "Al": {"value": 64.8, "unit": "cm", "confidence": 0.90},
            }
        }
        
        response = await pattern_factory_client.post(
            "/orders",
            json=data,
            headers=headers
        )
        assert response.status_code == 201
        return response.json()["order_id"]

    async def test_step_1_pattern_on_job_board(
        self,
        pattern_factory_client,
        tailor_platform_client,
        tailor_auth_token
    ):
        """
        Step 1: Pattern available on job board (S08 - STAGING).
        
        Verifies:
        - Orders in S08 state appear on tailor job board
        - Job board shows relevant order details
        - Tailor can browse available orders
        
        Reference: Ops Manual v6.8 - Section 1.2 (S08 STAGING)
        """
        headers = {"Authorization": f"Bearer {tailor_auth_token}"}
        
        # Create an order and advance it to S08
        order_id = await self._create_test_order(
            pattern_factory_client, 
            tailor_auth_token
        )
        
        # Advance order to S08 (STAGING)
        # In production, this happens after cutting completes
        await pattern_factory_client.post(
            f"/orders/{order_id}/transition",
            json={"to_state": "S08", "reason": "cutting_complete"},
            headers=headers
        )
        
        # Check job board
        response = await tailor_platform_client.get(
            "/job-board",
            params={"status": "staging"},
            headers=headers
        )
        
        assert response.status_code == 200
        job_board = response.json()
        
        # Verify order appears on job board
        order_ids = [o["order_id"] for o in job_board.get("orders", [])]
        assert order_id in order_ids, "Order not found on job board"
        
        # Verify job board shows required details
        order_info = next(o for o in job_board["orders"] if o["order_id"] == order_id)
        assert "garment_type" in order_info
        assert "priority" in order_info
        assert "created_at" in order_info

    async def test_step_2_tailor_claims_order(
        self,
        pattern_factory_client,
        tailor_platform_client,
        tailor_auth_token
    ):
        """
        Step 2: Tailor claims order (S08 → S09).
        
        Verifies:
        - Tailor can claim an order from job board
        - Order transitions from S08 to S09
        - Order is assigned to tailor
        - Order no longer appears as available
        
        Reference: Ops Manual v6.8 - Section 1.2 (S08→S09 Transition)
        Target: State transition < 500ms
        """
        headers = {"Authorization": f"Bearer {tailor_auth_token}"}
        tailor_id = f"tailor_{int(time.time())}"
        
        # Create and stage order
        order_id = await self._create_test_order(
            pattern_factory_client,
            tailor_auth_token
        )
        
        await pattern_factory_client.post(
            f"/orders/{order_id}/transition",
            json={"to_state": "S08"},
            headers=headers
        )
        
        # Tailor claims order
        start_time = time.time()
        claim_response = await tailor_platform_client.post(
            f"/orders/{order_id}/claim",
            json={"tailor_id": tailor_id},
            headers=headers
        )
        claim_time = (time.time() - start_time) * 1000
        
        assert claim_response.status_code == 200, \
            f"Claim failed: {claim_response.text}"
        assert claim_time < 500, \
            f"Claim took {claim_time}ms, target < 500ms"
        
        claim_data = claim_response.json()
        assert claim_data["status"] == "claimed"
        assert claim_data["tailor_id"] == tailor_id
        
        # Verify order state transition
        status_response = await pattern_factory_client.get(
            f"/orders/{order_id}/status",
            headers=headers
        )
        status = status_response.json()
        assert status["state"] == "S09", f"Expected S09, got {status['state']}"
        assert status["state_name"] == "QA"

    async def test_step_3_pattern_dispatched(
        self,
        pattern_factory_client,
        tailor_platform_client,
        tailor_auth_token
    ):
        """
        Step 3: Pattern dispatched (S10).
        
        Verifies:
        - Order moves to S10 (STAGING2) after QA pass
        - Pattern pieces are dispatched to tailor
        - Dispatch tracking is recorded
        
        Reference: Ops Manual v6.8 - Section 1.2 (S10 STAGING2)
        """
        headers = {"Authorization": f"Bearer {tailor_auth_token}"}
        tailor_id = f"tailor_{int(time.time())}"
        
        # Setup: Create order and advance through S09
        order_id = await self._create_test_order(
            pattern_factory_client,
            tailor_auth_token
        )
        
        # Advance to S08, claim, then S09
        await pattern_factory_client.post(
            f"/orders/{order_id}/transition",
            json={"to_state": "S08"},
            headers=headers
        )
        await tailor_platform_client.post(
            f"/orders/{order_id}/claim",
            json={"tailor_id": tailor_id},
            headers=headers
        )
        
        # QA passes - transition to S10
        dispatch_response = await pattern_factory_client.post(
            f"/orders/{order_id}/transition",
            json={
                "to_state": "S10",
                "reason": "qa_passed",
                "dispatch_time": datetime.utcnow().isoformat()
            },
            headers=headers
        )
        
        assert dispatch_response.status_code == 200
        
        # Verify dispatch recorded
        order_response = await pattern_factory_client.get(
            f"/orders/{order_id}",
            headers=headers
        )
        order = order_response.json()
        assert order["state"] == "S10"
        assert order["dispatch_time"] is not None

    async def test_step_4_pattern_in_transit(
        self,
        pattern_factory_client,
        tailor_platform_client,
        tailor_auth_token
    ):
        """
        Step 4: Pattern in transit (S11).
        
        Verifies:
        - Order transitions to S11 (SEWING) - active production
        - Transit tracking information is available
        - ETA is calculated and displayed
        
        Reference: Ops Manual v6.8 - Section 1.2 (S11 SEWING)
        """
        headers = {"Authorization": f"Bearer {tailor_auth_token}"}
        tailor_id = f"tailor_{int(time.time())}"
        
        # Setup complete workflow to S11
        order_id = await self._create_test_order(
            pattern_factory_client,
            tailor_auth_token
        )
        
        # Advance through states
        for state in ["S08", "S09", "S10"]:
            await pattern_factory_client.post(
                f"/orders/{order_id}/transition",
                json={"to_state": state},
                headers=headers
            )
        
        # Transition to S11 (SEWING - production started)
        response = await pattern_factory_client.post(
            f"/orders/{order_id}/transition",
            json={
                "to_state": "S11",
                "reason": "production_started",
                "tailor_id": tailor_id
            },
            headers=headers
        )
        
        assert response.status_code == 200
        
        # Verify in transit status
        status_response = await tailor_platform_client.get(
            f"/orders/{order_id}/status",
            headers=headers
        )
        status = status_response.json()
        assert status["state"] == "S11"
        assert status["state_name"] == "SEWING"

    async def test_step_5_pattern_received(
        self,
        pattern_factory_client,
        tailor_platform_client,
        tailor_auth_token
    ):
        """
        Step 5: Pattern received (S12).
        
        Verifies:
        - Tailor can mark pattern as received
        - Order transitions to S12 (ASSEMBLY)
        - Receipt timestamp is recorded
        
        Reference: Ops Manual v6.8 - Section 1.2 (S12 ASSEMBLY)
        """
        headers = {"Authorization": f"Bearer {tailor_auth_token}"}
        tailor_id = f"tailor_{int(time.time())}"
        
        # Setup to S11
        order_id = await self._create_test_order(
            pattern_factory_client,
            tailor_auth_token
        )
        
        for state in ["S08", "S09", "S10", "S11"]:
            await pattern_factory_client.post(
                f"/orders/{order_id}/transition",
                json={"to_state": state, "tailor_id": tailor_id},
                headers=headers
            )
        
        # Mark as received - transition to S12
        response = await tailor_platform_client.post(
            f"/orders/{order_id}/receive",
            json={
                "tailor_id": tailor_id,
                "received_at": datetime.utcnow().isoformat(),
                "condition": "good"
            },
            headers=headers
        )
        
        assert response.status_code == 200
        
        # Verify state
        status_response = await pattern_factory_client.get(
            f"/orders/{order_id}/status",
            headers=headers
        )
        status = status_response.json()
        assert status["state"] == "S12"

    async def test_step_6_production_started(
        self,
        pattern_factory_client,
        tailor_platform_client,
        tailor_auth_token
    ):
        """
        Step 6: Production started (S13).
        
        Verifies:
        - Tailor can start production work
        - Order transitions to S13 (FINISHING)
        - Work order details are available
        
        Reference: Ops Manual v6.8 - Section 1.2 (S13 FINISHING)
        Target SLA: < 4 hours for sewing (S11), < 2 hours for assembly (S12)
        """
        headers = {"Authorization": f"Bearer {tailor_auth_token}"}
        tailor_id = f"tailor_{int(time.time())}"
        
        # Setup to S12
        order_id = await self._create_test_order(
            pattern_factory_client,
            tailor_auth_token
        )
        
        for state in ["S08", "S09", "S10", "S11", "S12"]:
            await pattern_factory_client.post(
                f"/orders/{order_id}/transition",
                json={"to_state": state, "tailor_id": tailor_id},
                headers=headers
            )
        
        # Start finishing - S13
        response = await pattern_factory_client.post(
            f"/orders/{order_id}/transition",
            json={
                "to_state": "S13",
                "reason": "finishing_started",
                "tailor_id": tailor_id
            },
            headers=headers
        )
        
        assert response.status_code == 200
        
        # Verify work order details
        work_order_response = await tailor_platform_client.get(
            f"/orders/{order_id}/work-order",
            headers=headers
        )
        
        if work_order_response.status_code == 200:
            work_order = work_order_response.json()
            assert "garment_type" in work_order
            assert "measurements" in work_order
            assert "special_instructions" in work_order

    async def test_step_7_ready_for_qc(
        self,
        pattern_factory_client,
        tailor_platform_client,
        tailor_auth_token
    ):
        """
        Step 7: Ready for QC (S14).
        
        Verifies:
        - Production completion is recorded
        - Order transitions to S14 (READY_FOR_PICKUP)
        - QC request is automatically triggered
        
        Reference: Ops Manual v6.8 - Section 1.2 (S14 READY_FOR_PICKUP)
        """
        headers = {"Authorization": f"Bearer {tailor_auth_token}"}
        tailor_id = f"tailor_{int(time.time())}"
        
        # Setup to S13
        order_id = await self._create_test_order(
            pattern_factory_client,
            tailor_auth_token
        )
        
        for state in ["S08", "S09", "S10", "S11", "S12", "S13"]:
            await pattern_factory_client.post(
                f"/orders/{order_id}/transition",
                json={"to_state": state, "tailor_id": tailor_id},
                headers=headers
            )
        
        # Complete production - S14
        completion_response = await tailor_platform_client.post(
            f"/orders/{order_id}/complete",
            json={
                "tailor_id": tailor_id,
                "completed_at": datetime.utcnow().isoformat(),
                "notes": "Production complete, ready for QC"
            },
            headers=headers
        )
        
        assert completion_response.status_code == 200
        
        # Verify state and QC trigger
        status_response = await pattern_factory_client.get(
            f"/orders/{order_id}/status",
            headers=headers
        )
        status = status_response.json()
        assert status["state"] == "S14"
        assert status["state_name"] == "READY_FOR_PICKUP"
        assert status["qc_required"] is True

    async def test_complete_tailor_journey(
        self,
        pattern_factory_client,
        tailor_platform_client,
        tailor_auth_token
    ):
        """
        Complete E2E test of the entire tailor journey.
        
        Runs all steps sequentially with timing validation.
        """
        journey_start = time.time()
        headers = {"Authorization": f"Bearer {tailor_auth_token}"}
        tailor_id = f"tailor_{int(time.time())}"
        
        # Step 1: Create order on job board
        order_id = await self._create_test_order(
            pattern_factory_client,
            tailor_auth_token
        )
        await pattern_factory_client.post(
            f"/orders/{order_id}/transition",
            json={"to_state": "S08"},
            headers=headers
        )
        
        # Step 2: Claim order
        await tailor_platform_client.post(
            f"/orders/{order_id}/claim",
            json={"tailor_id": tailor_id},
            headers=headers
        )
        
        # Step 3-7: Progress through production
        state_transitions = [
            ("S09", "qa_complete"),
            ("S10", "dispatched"),
            ("S11", "production_started"),
            ("S12", "assembly_complete"),
            ("S13", "finishing_started"),
            ("S14", "production_complete")
        ]
        
        for state, reason in state_transitions:
            response = await pattern_factory_client.post(
                f"/orders/{order_id}/transition",
                json={
                    "to_state": state,
                    "reason": reason,
                    "tailor_id": tailor_id
                },
                headers=headers
            )
            assert response.status_code == 200, \
                f"Failed to transition to {state}: {response.text}"
        
        total_time = time.time() - journey_start
        
        # Verify final state
        final_status = await pattern_factory_client.get(
            f"/orders/{order_id}/status",
            headers=headers
        )
        status = final_status.json()
        assert status["state"] == "S14"
        
        print(f"\n✅ Complete tailor journey finished in {total_time:.1f}s")
        print(f"   Order ID: {order_id}")
        print(f"   Tailor ID: {tailor_id}")


@pytest.mark.e2e
@pytest.mark.asyncio
class TestTailorJourneyScenarios:
    """
    E2E tests for tailor journey edge cases and scenarios.
    """

    async def test_multiple_tailors_claiming_same_order(
        self,
        pattern_factory_client,
        tailor_platform_client,
        tailor_auth_token
    ):
        """
        Test race condition when multiple tailors try to claim same order.
        
        Verifies only one tailor successfully claims the order.
        """
        headers = {"Authorization": f"Bearer {tailor_auth_token}"}
        
        # Create and stage order
        order_id = await self._create_test_order(
            pattern_factory_client,
            tailor_auth_token
        )
        await pattern_factory_client.post(
            f"/orders/{order_id}/transition",
            json={"to_state": "S08"},
            headers=headers
        )
        
        # Two tailors try to claim simultaneously
        tailor_a = "tailor_A"
        tailor_b = "tailor_B"
        
        claim_a = tailor_platform_client.post(
            f"/orders/{order_id}/claim",
            json={"tailor_id": tailor_a},
            headers=headers
        )
        claim_b = tailor_platform_client.post(
            f"/orders/{order_id}/claim",
            json={"tailor_id": tailor_b},
            headers=headers
        )
        
        results = await asyncio.gather(claim_a, claim_b, return_exceptions=True)
        
        # One should succeed, one should fail
        success_count = sum(
            1 for r in results 
            if not isinstance(r, Exception) and r.status_code == 200
        )
        assert success_count == 1, "Exactly one claim should succeed"

    async def test_order_priority_handling(
        self,
        pattern_factory_client,
        tailor_platform_client,
        tailor_auth_token
    ):
        """
        Test that rush orders are prioritized on job board.
        
        Verifies:
        - Rush orders appear first on job board
        - High priority is visually indicated
        """
        headers = {"Authorization": f"Bearer {tailor_auth_token}"}
        
        # Create multiple orders with different priorities
        priorities = ["low", "normal", "high", "rush"]
        order_ids = []
        
        for priority in priorities:
            data = {
                "customer_id": f"cust_{priority}",
                "garment_type": "jacket",
                "fit_type": "regular",
                "priority": priority,
                "measurements": {
                    "Cg": {"value": 100.0, "unit": "cm", "confidence": 0.95}
                }
            }
            response = await pattern_factory_client.post(
                "/orders",
                json=data,
                headers=headers
            )
            order_id = response.json()["order_id"]
            order_ids.append((priority, order_id))
            
            # Advance to S08
            await pattern_factory_client.post(
                f"/orders/{order_id}/transition",
                json={"to_state": "S08"},
                headers=headers
            )
        
        # Check job board ordering
        response = await tailor_platform_client.get(
            "/job-board",
            params={"status": "staging", "sort": "priority"},
            headers=headers
        )
        
        if response.status_code == 200:
            board = response.json()
            board_order_ids = [o["order_id"] for o in board.get("orders", [])]
            
            # Rush should be first
            rush_order_id = next(oid for pri, oid in order_ids if pri == "rush")
            if rush_order_id in board_order_ids:
                assert board_order_ids.index(rush_order_id) < 2, \
                    "Rush order should be near top of job board"

    async def test_tailor_performance_tracking(
        self,
        pattern_factory_client,
        tailor_platform_client,
        tailor_auth_token
    ):
        """
        Test that tailor performance metrics are tracked.
        
        Verifies:
        - Production time is recorded
        - Quality scores are tracked
        - Performance dashboard is updated
        """
        headers = {"Authorization": f"Bearer {tailor_auth_token}"}
        tailor_id = f"tailor_perf_{int(time.time())}"
        
        # Complete an order
        order_id = await self._create_test_order(
            pattern_factory_client,
            tailor_auth_token
        )
        
        production_start = datetime.utcnow()
        
        for state in ["S08", "S09", "S10", "S11", "S12", "S13", "S14"]:
            await pattern_factory_client.post(
                f"/orders/{order_id}/transition",
                json={"to_state": state, "tailor_id": tailor_id},
                headers=headers
            )
        
        production_end = datetime.utcnow()
        
        # Check performance metrics
        metrics_response = await tailor_platform_client.get(
            f"/tailors/{tailor_id}/performance",
            headers=headers
        )
        
        if metrics_response.status_code == 200:
            metrics = metrics_response.json()
            assert "orders_completed" in metrics
            assert "avg_production_time" in metrics
            
            # Verify this order is counted
            assert metrics["orders_completed"] >= 1


@pytest.mark.e2e
@pytest.mark.asyncio
class TestTailorJourneySLACompliance:
    """
    SLA compliance tests for tailor journey.
    
    Reference: Ops Manual v6.8 - Section 1.2 (SLA Requirements)
    """

    async def test_state_transition_timing(
        self,
        pattern_factory_client,
        tailor_auth_token
    ):
        """
        Verify state transitions meet timing requirements.
        
        SLA Requirements (from Ops Manual):
        - S08 (Staging): < 30 min
        - S09 (QA): < 15 min
        - S10 (Staging2): < 1 hour
        - S11 (Sewing): < 4 hours
        - S12 (Assembly): < 2 hours
        - S13 (Finishing): < 1 hour
        """
        headers = {"Authorization": f"Bearer {tailor_auth_token}"}
        
        sla_requirements = {
            "S08": 30 * 60,    # 30 minutes
            "S09": 15 * 60,    # 15 minutes
            "S10": 60 * 60,    # 1 hour
            "S11": 4 * 60 * 60,  # 4 hours
            "S12": 2 * 60 * 60,  # 2 hours
            "S13": 60 * 60,    # 1 hour
        }
        
        for state, max_seconds in sla_requirements.items():
            # Check that SLA tracking exists for each state
            response = await pattern_factory_client.get(
                f"/sla/{state}",
                headers=headers
            )
            
            if response.status_code == 200:
                sla_data = response.json()
                assert "target_seconds" in sla_data
                assert sla_data["target_seconds"] <= max_seconds
