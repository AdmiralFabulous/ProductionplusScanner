"""
EYESON Session Management Unit Tests
Reference: SUIT_AI_Master_Operations_Manual_v6_8.md

Sections Referenced:
- 1.2: Order State Machine - Session states mapping to S03
- 17.2: Customer Journey - Scan flow
- 2.5: Security Layer - Session authentication
"""

import uuid
from datetime import datetime, timedelta

import pytest
from fastapi import HTTPException


@pytest.mark.unit
@pytest.mark.pillar2
class TestSessionCreation:
    """Test session creation endpoints."""
    
    def test_create_session_success(self, eyeson_client, auth_headers):
        """
        Test POST /sessions creates new session.
        
        Reference: Ops Manual v6.8 Section 17.2 - Customer Journey
        Step 1: Customer initiates scan session
        """
        response = eyeson_client.post(
            "/sessions",
            headers=auth_headers,
            json={
                "customer_id": "cust_test_123",
                "garment_type": "jacket",
                "fit_type": "regular",
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert "session_id" in data
        assert data["status"] == "INITIATED"
        assert data["garment_type"] == "jacket"
        assert data["fit_type"] == "regular"
    
    def test_create_session_invalid_garment_type(self, eyeson_client, auth_headers):
        """Test validation of garment_type field."""
        response = eyeson_client.post(
            "/sessions",
            headers=auth_headers,
            json={
                "customer_id": "cust_test_123",
                "garment_type": "invalid_type",
                "fit_type": "regular",
            }
        )
        
        assert response.status_code == 422
        assert "garment_type" in response.json()["detail"][0]["loc"]
    
    def test_create_session_invalid_fit_type(self, eyeson_client, auth_headers):
        """Test validation of fit_type field."""
        response = eyeson_client.post(
            "/sessions",
            headers=auth_headers,
            json={
                "customer_id": "cust_test_123",
                "garment_type": "jacket",
                "fit_type": "invalid_fit",
            }
        )
        
        assert response.status_code == 422


@pytest.mark.unit
@pytest.mark.pillar2
class TestSessionCalibration:
    """Test calibration endpoints."""
    
    def test_calibration_success(self, eyeson_client, auth_headers, valid_session_data):
        """
        Test POST /sessions/{id}/calibrate.
        
        Reference: Ops Manual v6.8 Section 17.2 - Customer Journey
        Step 2: ArUco marker calibration
        """
        session_id = valid_session_data["session_id"]
        
        response = eyeson_client.post(
            f"/sessions/{session_id}/calibrate",
            headers=auth_headers,
            json={
                "marker_image": "base64_encoded_image_data",
                "marker_type": "aruco",
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "CALIBRATING"
        assert "scale_factor" in data
        assert data["marker_detected"] == True
    
    def test_calibration_no_marker_detected(self, eyeson_client, auth_headers, valid_session_data):
        """Test calibration when no marker detected."""
        session_id = valid_session_data["session_id"]
        
        response = eyeson_client.post(
            f"/sessions/{session_id}/calibrate",
            headers=auth_headers,
            json={
                "marker_image": "invalid_image",
                "marker_type": "aruco",
            }
        )
        
        assert response.status_code == 400
        assert "marker" in response.json()["detail"].lower()


@pytest.mark.unit
@pytest.mark.pillar2
class TestSessionUpload:
    """Test video upload endpoints."""
    
    def test_upload_success(self, eyeson_client, auth_headers, valid_session_data):
        """
        Test POST /sessions/{id}/upload.
        
        Reference: Ops Manual v6.8 Section 17.2 - Customer Journey
        Step 3: 90-second video upload
        """
        session_id = valid_session_data["session_id"]
        
        response = eyeson_client.post(
            f"/sessions/{session_id}/upload",
            headers=auth_headers,
            json={
                "video_data": "base64_encoded_video",
                "duration_seconds": 90,
                "format": "mp4",
            }
        )
        
        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "PROCESSING"
        assert "processing_id" in data
    
    def test_upload_invalid_duration(self, eyeson_client, auth_headers, valid_session_data):
        """Test upload validation for video duration."""
        session_id = valid_session_data["session_id"]
        
        response = eyeson_client.post(
            f"/sessions/{session_id}/upload",
            headers=auth_headers,
            json={
                "video_data": "base64_encoded_video",
                "duration_seconds": 10,  # Too short
                "format": "mp4",
            }
        )
        
        assert response.status_code == 422


@pytest.mark.unit
@pytest.mark.pillar2
@pytest.mark.state_machine
class TestSessionStateTransitions:
    """
    Test session state machine.
    
    Reference: Ops Manual v6.8 Section 1.2 - Order State Machine
    EYESON Session states map to S03 SCAN_RECEIVED
    """
    
    def test_state_initiated_to_calibrating(self, eyeson_client, auth_headers):
        """Test INITIATED → CALIBRATING transition."""
        # Create session
        response = eyeson_client.post("/sessions", headers=auth_headers, json={
            "garment_type": "jacket",
            "fit_type": "regular",
        })
        session_id = response.json()["session_id"]
        
        # Verify initial state
        response = eyeson_client.get(f"/sessions/{session_id}", headers=auth_headers)
        assert response.json()["status"] == "INITIATED"
        
        # Trigger calibration
        eyeson_client.post(
            f"/sessions/{session_id}/calibrate",
            headers=auth_headers,
            json={"marker_image": "test", "marker_type": "aruco"}
        )
        
        # Verify state transition
        response = eyeson_client.get(f"/sessions/{session_id}", headers=auth_headers)
        assert response.json()["status"] == "CALIBRATING"
    
    def test_state_calibrating_to_capturing(self, eyeson_client, auth_headers):
        """Test CALIBRATING → CAPTURING transition."""
        # Setup: Create and calibrate session
        response = eyeson_client.post("/sessions", headers=auth_headers, json={
            "garment_type": "jacket",
            "fit_type": "regular",
        })
        session_id = response.json()["session_id"]
        eyeson_client.post(
            f"/sessions/{session_id}/calibrate",
            headers=auth_headers,
            json={"marker_image": "test", "marker_type": "aruco"}
        )
        
        # Trigger capture start
        eyeson_client.post(
            f"/sessions/{session_id}/start_capture",
            headers=auth_headers
        )
        
        # Verify state
        response = eyeson_client.get(f"/sessions/{session_id}", headers=auth_headers)
        assert response.json()["status"] == "CAPTURING"
    
    def test_state_capturing_to_processing(self, eyeson_client, auth_headers):
        """Test CAPTURING → PROCESSING transition."""
        # Setup through capturing state
        response = eyeson_client.post("/sessions", headers=auth_headers, json={
            "garment_type": "jacket",
        })
        session_id = response.json()["session_id"]
        
        # Upload video triggers processing
        eyeson_client.post(
            f"/sessions/{session_id}/upload",
            headers=auth_headers,
            json={"video_data": "test", "duration_seconds": 90}
        )
        
        # Verify state
        response = eyeson_client.get(f"/sessions/{session_id}", headers=auth_headers)
        assert response.json()["status"] == "PROCESSING"
    
    def test_state_processing_to_completed(self, eyeson_client, auth_headers):
        """Test PROCESSING → COMPLETED transition."""
        # This would require async processing to complete
        # Mock the processing completion
        pass
    
    def test_invalid_state_transition(self, eyeson_client, auth_headers):
        """Test that invalid state transitions are rejected."""
        # Create new session
        response = eyeson_client.post("/sessions", headers=auth_headers, json={
            "garment_type": "jacket",
        })
        session_id = response.json()["session_id"]
        
        # Try to upload without calibration (invalid transition)
        response = eyeson_client.post(
            f"/sessions/{session_id}/upload",
            headers=auth_headers,
            json={"video_data": "test", "duration_seconds": 90}
        )
        
        assert response.status_code == 409  # Conflict - invalid state transition


@pytest.mark.unit
@pytest.mark.security
class TestSessionAuth:
    """
    Test session authentication.
    
    Reference: Ops Manual v6.8 Section 2.5 - Security Layer
    """
    
    def test_session_without_auth(self, eyeson_client):
        """Test that endpoints require authentication."""
        response = eyeson_client.post("/sessions", json={
            "garment_type": "jacket",
        })
        
        assert response.status_code == 401
    
    def test_session_with_expired_token(self, eyeson_client, expired_access_token):
        """Test expired token handling."""
        headers = {"Authorization": f"Bearer {expired_access_token}"}
        
        response = eyeson_client.post("/sessions", headers=headers, json={
            "garment_type": "jacket",
        })
        
        assert response.status_code == 401
        assert "expired" in response.json()["detail"].lower()
    
    def test_session_invalid_session_id(self, eyeson_client, auth_headers):
        """Test handling of invalid session ID."""
        response = eyeson_client.get(
            f"/sessions/{uuid.uuid4()}",
            headers=auth_headers
        )
        
        assert response.status_code == 404
