"""
Pattern Factory 27-State Order Machine Tests
Reference: SUIT_AI_Master_Operations_Manual_v6_8.md Section 1.2

Complete test coverage for all 27 order states and transitions.
"""

import uuid
from datetime import datetime, timedelta

import pytest


@pytest.mark.unit
@pytest.mark.pillar2
@pytest.mark.state_machine
class TestOrderStateTransitions:
    """
    Test all 27 state transitions.
    
    Reference: Ops Manual v6.8 Section 1.2 - Complete State Reference Table
    """
    
    # Phase 1: Initial Order Processing
    
    def test_s01_draft_to_s02_paid(self, pattern_factory_client, auth_headers):
        """S01 DRAFT → S02 PAID: Payment captured."""
        order_id = f"SDS-{datetime.now().strftime('%Y%m%d')}-0001-A"
        
        # Create draft order
        response = pattern_factory_client.post(
            "/orders",
            headers=auth_headers,
            json={
                "order_id": order_id,
                "status": "S01",
                "customer_id": "cust_123",
            }
        )
        assert response.status_code == 201
        
        # Process payment
        response = pattern_factory_client.post(
            f"/orders/{order_id}/payment",
            headers=auth_headers,
            json={"payment_method": "stripe", "amount": 50000}
        )
        
        assert response.status_code == 200
        assert response.json()["status"] == "S02"
        assert response.json()["state_name"] == "PAID"
    
    def test_s02_paid_to_s03_scan_received(self, pattern_factory_client, auth_headers, valid_p0_measurements):
        """
        S02 PAID → S03 SCAN_RECEIVED: Body scan uploaded.
        
        This is triggered by EYESON POST /orders.
        Reference: Ops Manual v6.8 Section 1.2
        """
        order_id = f"SDS-{datetime.now().strftime('%Y%m%d')}-0002-A"
        
        # Create order with scan data (simulates EYESON submission)
        response = pattern_factory_client.post(
            "/orders",
            headers=auth_headers,
            json={
                "order_id": order_id,
                "customer_id": "cust_123",
                "garment_type": "jacket",
                "fit_type": "regular",
                "measurements": valid_p0_measurements,
                "status": "S02",
            }
        )
        
        assert response.status_code == 201
        assert response.json()["status"] == "S03"
        assert response.json()["state_name"] == "SCAN_RECEIVED"
    
    def test_s03_to_s04_processing(self, pattern_factory_client, auth_headers):
        """S03 SCAN_RECEIVED → S04 PROCESSING: Translation Matrix + Optitex."""
        order_id = self._create_order_in_state(pattern_factory_client, auth_headers, "S03")
        
        # Start processing
        response = pattern_factory_client.post(
            f"/orders/{order_id}/process",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        assert response.json()["status"] == "S04"
        assert response.json()["state_name"] == "PROCESSING"
    
    def test_s04_to_s05_pattern_ready(self, pattern_factory_client, auth_headers):
        """
        S04 PROCESSING → S05 PATTERN_READY: PLT file generated.
        
        This is the state EYESON polls for.
        """
        order_id = self._create_order_in_state(pattern_factory_client, auth_headers, "S04")
        
        # Complete processing
        response = pattern_factory_client.post(
            f"/orders/{order_id}/complete_processing",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "S05"
        assert data["state_name"] == "PATTERN_READY"
        assert data["files_available"]["plt"] == True
        assert data["files_available"]["pds"] == True
        assert data["files_available"]["dxf"] == True
    
    # Phase 2: Cutting
    
    def test_s05_to_s06_cutting(self, pattern_factory_client, auth_headers):
        """S05 PATTERN_READY → S06 CUTTING: On plotter queue at HQ."""
        order_id = self._create_order_in_state(pattern_factory_client, auth_headers, "S05")
        
        # Submit to cutter queue
        response = pattern_factory_client.post(
            f"/orders/{order_id}/submit_to_cutter",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "S06"
        assert data["state_name"] == "CUTTING"
        assert "queue_position" in data
    
    def test_s06_to_s07_pattern_cut(self, pattern_factory_client, auth_headers):
        """S06 CUTTING → S07 PATTERN_CUT: Templates cut, ready for dispatch."""
        order_id = self._create_order_in_state(pattern_factory_client, auth_headers, "S06")
        
        # Simulate cutter completion
        response = pattern_factory_client.post(
            f"/orders/{order_id}/cutter_complete",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "S07"
        assert data["state_name"] == "PATTERN_CUT"
    
    # Phase 3: Tailor Assignment
    
    def test_s07_to_s08_available_for_tailors(self, pattern_factory_client, auth_headers):
        """S07 PATTERN_CUT → S08 AVAILABLE_FOR_TAILORS: On job board."""
        order_id = self._create_order_in_state(pattern_factory_client, auth_headers, "S07")
        
        response = pattern_factory_client.post(
            f"/orders/{order_id}/publish_to_job_board",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "S08"
        assert data["state_name"] == "AVAILABLE_FOR_TAILORS"
    
    def test_s08_to_s09_claimed(self, pattern_factory_client, auth_headers):
        """S08 AVAILABLE_FOR_TAILORS → S09 CLAIMED: Assigned to tailor(s)."""
        order_id = self._create_order_in_state(pattern_factory_client, auth_headers, "S08")
        
        response = pattern_factory_client.post(
            f"/orders/{order_id}/claim",
            headers=auth_headers,
            json={"tailor_id": "tailor_001"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "S09"
        assert data["state_name"] == "CLAIMED"
        assert data["assigned_tailor_id"] == "tailor_001"
    
    def test_s09_to_s10_dispatching(self, pattern_factory_client, auth_headers):
        """S09 CLAIMED → S10 DISPATCHING: Courier booked."""
        order_id = self._create_order_in_state(pattern_factory_client, auth_headers, "S09")
        
        response = pattern_factory_client.post(
            f"/orders/{order_id}/book_courier",
            headers=auth_headers,
            json={"courier_id": "courier_001"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "S10"
        assert data["state_name"] == "DISPATCHING"
    
    def test_s10_to_s11_in_transit(self, pattern_factory_client, auth_headers):
        """S10 DISPATCHING → S11 IN_TRANSIT_TO_TAILOR: Pattern tube with courier."""
        order_id = self._create_order_in_state(pattern_factory_client, auth_headers, "S10")
        
        response = pattern_factory_client.post(
            f"/orders/{order_id}/dispatch",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "S11"
        assert data["state_name"] == "IN_TRANSIT_TO_TAILOR"
    
    def test_s11_to_s12_with_tailor(self, pattern_factory_client, auth_headers):
        """S11 IN_TRANSIT → S12 WITH_TAILOR: Templates received."""
        order_id = self._create_order_in_state(pattern_factory_client, auth_headers, "S11")
        
        response = pattern_factory_client.post(
            f"/orders/{order_id}/receive_by_tailor",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "S12"
        assert data["state_name"] == "WITH_TAILOR"
    
    def test_s12_to_s13_in_production(self, pattern_factory_client, auth_headers):
        """S12 WITH_TAILOR → S13 IN_PRODUCTION: Fabric cut, sewing underway."""
        order_id = self._create_order_in_state(pattern_factory_client, auth_headers, "S12")
        
        response = pattern_factory_client.post(
            f"/orders/{order_id}/start_production",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "S13"
        assert data["state_name"] == "IN_PRODUCTION"
    
    def test_s13_to_s14_ready_for_qc(self, pattern_factory_client, auth_headers):
        """S13 IN_PRODUCTION → S14 READY_FOR_QC: Tailor marked complete."""
        order_id = self._create_order_in_state(pattern_factory_client, auth_headers, "S13")
        
        response = pattern_factory_client.post(
            f"/orders/{order_id}/complete_production",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "S14"
        assert data["state_name"] == "READY_FOR_QC"
    
    # Phase 4: QC Pass Flow
    
    def test_s14_to_s15_qc_in_progress(self, pattern_factory_client, auth_headers):
        """S14 READY_FOR_QC → S15 QC_IN_PROGRESS: Inspector working."""
        order_id = self._create_order_in_state(pattern_factory_client, auth_headers, "S14")
        
        response = pattern_factory_client.post(
            f"/orders/{order_id}/start_qc",
            headers=auth_headers,
            json={"inspector_id": "qc_001"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "S15"
        assert data["state_name"] == "QC_IN_PROGRESS"
    
    def test_s15_to_s16_qc_pass(self, pattern_factory_client, auth_headers):
        """S15 QC_IN_PROGRESS → S16 QC_PASS: Approved."""
        order_id = self._create_order_in_state(pattern_factory_client, auth_headers, "S15")
        
        response = pattern_factory_client.post(
            f"/orders/{order_id}/submit_qc",
            headers=auth_headers,
            json={"verdict": "PASS", "inspector_id": "qc_001"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "S16"
        assert data["state_name"] == "QC_PASS"
    
    def test_s16_to_s16a_awaiting_labeling(self, pattern_factory_client, auth_headers):
        """S16 QC_PASS → S16a AWAITING_LABELING."""
        order_id = self._create_order_in_state(pattern_factory_client, auth_headers, "S16")
        
        response = pattern_factory_client.post(
            f"/orders/{order_id}/move_to_labeling",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "S16a"
        assert data["state_name"] == "AWAITING_LABELING"
    
    def test_s16a_to_s16b_labeling_complete(self, pattern_factory_client, auth_headers):
        """S16a AWAITING_LABELING → S16b LABELING_COMPLETE."""
        order_id = self._create_order_in_state(pattern_factory_client, auth_headers, "S16a")
        
        response = pattern_factory_client.post(
            f"/orders/{order_id}/complete_labeling",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "S16b"
        assert data["state_name"] == "LABELING_COMPLETE"
    
    def test_s16b_to_s16c_packed(self, pattern_factory_client, auth_headers):
        """S16b LABELING_COMPLETE → S16c PACKED."""
        order_id = self._create_order_in_state(pattern_factory_client, auth_headers, "S16b")
        
        response = pattern_factory_client.post(
            f"/orders/{order_id}/pack",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "S16c"
        assert data["state_name"] == "PACKED"
    
    # Phase 4b: QC Fail Flow
    
    def test_s15_to_s17_qc_fail(self, pattern_factory_client, auth_headers):
        """S15 QC_IN_PROGRESS → S17 QC_FAIL: Failed, enters dispute window."""
        order_id = self._create_order_in_state(pattern_factory_client, auth_headers, "S15")
        
        response = pattern_factory_client.post(
            f"/orders/{order_id}/submit_qc",
            headers=auth_headers,
            json={
                "verdict": "FAIL",
                "verdict_category": "CRITICAL_FAIL",
                "inspector_id": "qc_001"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "S17"
        assert data["state_name"] == "QC_FAIL"
    
    def test_s17_to_s17a_pending_dispute(self, pattern_factory_client, auth_headers):
        """S17 QC_FAIL → S17a QC_FAIL_PENDING_DISPUTE: Within 24hr window."""
        order_id = self._create_order_in_state(pattern_factory_client, auth_headers, "S17")
        
        # After QC fail, enters 24hr dispute window
        response = pattern_factory_client.get(
            f"/orders/{order_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "S17a"
        assert data["state_name"] == "QC_FAIL_PENDING_DISPUTE"
        assert "dispute_deadline" in data
    
    def test_s17a_to_s17b_disputed(self, pattern_factory_client, auth_headers):
        """S17a → S17b DISPUTED_AWAITING_REINSPECTION."""
        order_id = self._create_order_in_state(pattern_factory_client, auth_headers, "S17a")
        
        response = pattern_factory_client.post(
            f"/orders/{order_id}/dispute",
            headers=auth_headers,
            json={"tailor_id": "tailor_001", "reason": "Fault is minor, not critical"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "S17b"
        assert data["state_name"] == "DISPUTED_AWAITING_REINSPECTION"
    
    def test_s17b_to_s17d_total_fail(self, pattern_factory_client, auth_headers):
        """S17b → S17d TOTAL_FAIL: Failed twice, no payout."""
        order_id = self._create_order_in_state(pattern_factory_client, auth_headers, "S17b")
        
        # Reinspection confirms fail
        response = pattern_factory_client.post(
            f"/orders/{order_id}/reinspect",
            headers=auth_headers,
            json={"verdict": "CONFIRM_FAIL", "inspector_id": "qc_002"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "S17d"
        assert data["state_name"] == "TOTAL_FAIL"
        assert data["payout_eligible"] == False
    
    def test_s17b_to_s17e_dispute_upheld(self, pattern_factory_client, auth_headers):
        """S17b → S17e DISPUTE_UPHELD: Reinspection passed."""
        order_id = self._create_order_in_state(pattern_factory_client, auth_headers, "S17b")
        
        # Reinspection overturns original verdict
        response = pattern_factory_client.post(
            f"/orders/{order_id}/reinspect",
            headers=auth_headers,
            json={"verdict": "PASS", "inspector_id": "qc_002"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "S17e"
        assert data["state_name"] == "DISPUTE_UPHELD"
    
    # Phase 5: Fulfillment
    
    def test_s16c_to_s18_returning_to_hq(self, pattern_factory_client, auth_headers):
        """S16c PACKED → S18 RETURNING_TO_HQ: Suit in transit."""
        order_id = self._create_order_in_state(pattern_factory_client, auth_headers, "S16c")
        
        response = pattern_factory_client.post(
            f"/orders/{order_id}/return_to_hq",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "S18"
        assert data["state_name"] == "RETURNING_TO_HQ"
    
    def test_s18_to_s19_at_hq(self, pattern_factory_client, auth_headers):
        """S18 RETURNING_TO_HQ → S19 AT_HQ: Ready for packaging."""
        order_id = self._create_order_in_state(pattern_factory_client, auth_headers, "S18")
        
        response = pattern_factory_client.post(
            f"/orders/{order_id}/receive_at_hq",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "S19"
        assert data["state_name"] == "AT_HQ"
    
    def test_s19_to_s20_shipped(self, pattern_factory_client, auth_headers):
        """S19 AT_HQ → S20 SHIPPED: To customer."""
        order_id = self._create_order_in_state(pattern_factory_client, auth_headers, "S19")
        
        response = pattern_factory_client.post(
            f"/orders/{order_id}/ship",
            headers=auth_headers,
            json={"carrier": "fedex", "tracking_number": "1234567890"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "S20"
        assert data["state_name"] == "SHIPPED"
    
    def test_s20_to_s21_delivered(self, pattern_factory_client, auth_headers):
        """S20 SHIPPED → S21 DELIVERED: Customer received."""
        order_id = self._create_order_in_state(pattern_factory_client, auth_headers, "S20")
        
        response = pattern_factory_client.post(
            f"/orders/{order_id}/deliver",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "S21"
        assert data["state_name"] == "DELIVERED"
    
    def test_s21_to_s22_complete(self, pattern_factory_client, auth_headers):
        """S21 DELIVERED → S22 COMPLETE: Order closed."""
        order_id = self._create_order_in_state(pattern_factory_client, auth_headers, "S21")
        
        response = pattern_factory_client.post(
            f"/orders/{order_id}/close",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "S22"
        assert data["state_name"] == "COMPLETE"
        assert data["is_terminal"] == True
    
    # Helper methods
    
    def _create_order_in_state(self, client, headers, state: str) -> str:
        """Helper to create order in a specific state."""
        order_id = f"SDS-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:4].upper()}-A"
        
        # This would typically use a test factory or database seed
        # For now, create through API
        response = client.post(
            "/orders/test/create_in_state",
            headers=headers,
            json={
                "order_id": order_id,
                "state": state,
                "customer_id": "cust_test",
            }
        )
        
        assert response.status_code == 201
        return order_id


@pytest.mark.unit
@pytest.mark.pillar2
@pytest.mark.state_machine
class TestOrderStateSLA:
    """
    Test SLA timing requirements per state.
    
    Reference: Ops Manual v6.8 Section 1.2 - State Timings
    """
    
    def test_s04_processing_sla(self, pattern_factory_client, auth_headers):
        """S04 PROCESSING: Max 5 minutes, Target 3 minutes."""
        # Verify SLA configuration
        response = pattern_factory_client.get(
            "/config/sla",
            headers=auth_headers
        )
        
        data = response.json()
        assert data["S04"]["max_minutes"] == 5
        assert data["S04"]["target_minutes"] == 3
    
    def test_s06_cutting_sla(self, pattern_factory_client, auth_headers):
        """S06 CUTTING: Max 30 minutes."""
        response = pattern_factory_client.get("/config/sla", headers=auth_headers)
        data = response.json()
        assert data["S06"]["max_minutes"] == 30
    
    def test_s11_transit_sla(self, pattern_factory_client, auth_headers):
        """S11 IN_TRANSIT: Max 4 hours (local)."""
        response = pattern_factory_client.get("/config/sla", headers=auth_headers)
        data = response.json()
        assert data["S11"]["max_hours"] == 4
    
    def test_s13_production_sla(self, pattern_factory_client, auth_headers):
        """S13 IN_PRODUCTION: Max 8 hours."""
        response = pattern_factory_client.get("/config/sla", headers=auth_headers)
        data = response.json()
        assert data["S13"]["max_hours"] == 8
