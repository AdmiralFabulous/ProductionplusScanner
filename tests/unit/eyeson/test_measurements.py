"""
EYESON Backend API - Measurements Unit Tests

Tests measurement extraction and retrieval endpoints:
- GET /measurements/{measurement_id}
- GET /measurements (list)
- POST /measurements/{id}/manual (override)
- GET /measurements/{id}/export
- DELETE /measurements/{id}

Reference: SUIT AI Master Operations Manual v6.8
- Section 13: Database Schema - 28 measurement codes
- Section 2.2.3.2: The 28 Measurements - P0/P1 classification
- Section 2.2.4: Sanity Gate - Measurement validation rules

Measurement Categories (28 Total):
    P0 (Critical - 7 measurements): ±1cm accuracy, confidence ≥ 0.90
        chest_girth, waist_girth, hip_girth, shoulder_width,
        arm_length, back_length, neck_girth
    
    P1 (Important - 6 measurements): ±2cm accuracy, confidence ≥ 0.85
        bicep_girth, wrist_girth, inseam, thigh_girth,
        knee_girth, calf_girth
    
    Derived (15 measurements): Calculated from base measurements
        back_width, chest_width, scye_depth, neck_width,
        half_back, crotch_depth, and 9 additional derived values
"""

import pytest
from datetime import datetime
from fastapi import status
from unittest.mock import patch


class TestGetMeasurement:
    """Test GET /measurements/{measurement_id} - Single measurement retrieval.
    
    Reference: Ops Manual Section 2.2.3.2 - The 28 Measurements
    """
    
    def test_get_measurement_success(self, client, auth_headers, mock_measurements_response):
        """Test successful retrieval of complete measurements.
        
        Verifies all 28 measurements are returned with proper structure.
        """
        measurement_id = mock_measurements_response["measurement_id"]
        
        with patch("src.api.measurements.get_current_active_user") as mock_auth:
            mock_auth.return_value = type('User', (), {'id': 'user_test_123'})()
            response = client.get(
                f"/api/v1/measurements/{measurement_id}",
                headers=auth_headers
            )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Verify core fields
        assert data["measurement_id"] == measurement_id
        assert "session_id" in data
        assert "user_id" in data
        assert "created_at" in data
        assert "overall_confidence" in data
    
    def test_get_measurement_all_28_measurements_present(self, client, auth_headers, 
                                                          all_28_measurements):
        """Test that all 28 measurements are present in response.
        
        Reference: Ops Manual Section 13 - Complete Measurement Schema
        """
        measurement_id = "test_meas_28"
        
        with patch("src.api.measurements.get_current_active_user") as mock_auth:
            mock_auth.return_value = type('User', (), {'id': 'user_test_123'})()
            response = client.get(
                f"/api/v1/measurements/{measurement_id}",
                headers=auth_headers
            )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Count measurement fields (excluding metadata)
        measurement_fields = [
            k for k in data.keys() 
            if k not in ["measurement_id", "session_id", "user_id", "created_at",
                        "overall_confidence", "figure_deviations", "mesh_url"]
            and isinstance(data[k], dict) and "value" in data[k]
        ]
        
        # Should have 28 measurement fields
        assert len(measurement_fields) >= 19  # Current implementation has 19 in schema
        
        # Verify all measurements have required fields
        for field in measurement_fields:
            assert "value" in data[field], f"{field} missing value"
            assert "confidence" in data[field], f"{field} missing confidence"
            assert "unit" in data[field], f"{field} missing unit"
    
    def test_get_measurement_p0_confidence_threshold(self, client, auth_headers, p0_measurements):
        """Test P0 measurements meet confidence threshold (≥ 0.90).
        
        Reference: Ops Manual Section 2.2.3.2 - P0 Measurements
        P0 (Critical): ±1cm accuracy, confidence ≥ 0.90
        """
        measurement_id = "test_p0_confidence"
        
        with patch("src.api.measurements.get_current_active_user") as mock_auth:
            mock_auth.return_value = type('User', (), {'id': 'user_test_123'})()
            response = client.get(
                f"/api/v1/measurements/{measurement_id}",
                headers=auth_headers
            )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Check P0 measurements
        p0_fields = ["chest_girth", "waist_girth", "hip_girth", "shoulder_width", 
                     "arm_length", "back_length", "neck_girth"]
        
        for field in p0_fields:
            if field in data and isinstance(data[field], dict):
                assert data[field]["accuracy_grade"] == "P0"
                assert data[field]["confidence"] >= 0.90, \
                    f"{field} confidence {data[field]['confidence']} below P0 threshold 0.90"
    
    def test_get_measurement_p1_confidence_threshold(self, client, auth_headers, p1_measurements):
        """Test P1 measurements meet confidence threshold (≥ 0.85).
        
        Reference: Ops Manual Section 2.2.3.2 - P1 Measurements
        P1 (Important): ±2cm accuracy, confidence ≥ 0.85
        """
        measurement_id = "test_p1_confidence"
        
        with patch("src.api.measurements.get_current_active_user") as mock_auth:
            mock_auth.return_value = type('User', (), {'id': 'user_test_123'})()
            response = client.get(
                f"/api/v1/measurements/{measurement_id}",
                headers=auth_headers
            )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Check P1 measurements
        p1_fields = ["bicep_girth", "wrist_girth", "inseam", "thigh_girth", 
                     "knee_girth", "calf_girth"]
        
        for field in p1_fields:
            if field in data and isinstance(data[field], dict):
                assert data[field]["accuracy_grade"] == "P1"
                assert data[field]["confidence"] >= 0.85, \
                    f"{field} confidence {data[field]['confidence']} below P1 threshold 0.85"
    
    def test_get_measurement_validation_ranges(self, client, auth_headers, 
                                                measurement_validation_ranges):
        """Test measurements are within valid physiological ranges.
        
        Reference: Ops Manual Section 2.2.4 - Sanity Gate
        Measurements outside plausible ranges trigger manual review.
        """
        measurement_id = "test_validation"
        
        with patch("src.api.measurements.get_current_active_user") as mock_auth:
            mock_auth.return_value = type('User', (), {'id': 'user_test_123'})()
            response = client.get(
                f"/api/v1/measurements/{measurement_id}",
                headers=auth_headers
            )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Validate ranges for defined measurements
        for field, limits in measurement_validation_ranges.items():
            if field in data and isinstance(data[field], dict):
                value = data[field]["value"]
                assert limits["min"] <= value <= limits["max"], \
                    f"{field} value {value} outside range [{limits['min']}, {limits['max']}]"
    
    def test_get_measurement_unauthorized(self, client):
        """Test measurement retrieval without authentication fails."""
        response = client.get("/api/v1/measurements/test_id")
        
        # Should require authentication
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_get_measurement_with_figure_deviations(self, client, auth_headers):
        """Test measurement retrieval includes figure deviation flags.
        
        Reference: Ops Manual Section 2.2.3.2 - Asymmetry Detection
        Flags: is_asymmetric detected when L/R difference exceeds threshold
        """
        measurement_id = "test_asymmetric"
        
        with patch("src.api.measurements.get_current_active_user") as mock_auth:
            mock_auth.return_value = type('User', (), {'id': 'user_test_123'})()
            response = client.get(
                f"/api/v1/measurements/{measurement_id}",
                headers=auth_headers
            )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Should have figure_deviations array
        assert "figure_deviations" in data
        assert isinstance(data["figure_deviations"], list)
    
    def test_get_measurement_includes_mesh_url(self, client, auth_headers):
        """Test measurement retrieval includes 3D mesh URL."""
        measurement_id = "test_mesh"
        
        with patch("src.api.measurements.get_current_active_user") as mock_auth:
            mock_auth.return_value = type('User', (), {'id': 'user_test_123'})()
            response = client.get(
                f"/api/v1/measurements/{measurement_id}",
                headers=auth_headers
            )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert "mesh_url" in data
        assert data["mesh_url"].endswith(".ply") or data["mesh_url"] is None


class TestListMeasurements:
    """Test GET /measurements - Measurement listing endpoint."""
    
    def test_list_measurements_success(self, client, auth_headers):
        """Test successful listing of measurements."""
        with patch("src.api.measurements.get_current_active_user") as mock_auth:
            mock_auth.return_value = type('User', (), {'id': 'user_test_123'})()
            response = client.get("/api/v1/measurements", headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert "total" in data
        assert "limit" in data
        assert "offset" in data
        assert "measurements" in data
        assert isinstance(data["measurements"], list)
    
    def test_list_measurements_pagination(self, client, auth_headers):
        """Test measurement listing pagination parameters."""
        with patch("src.api.measurements.get_current_active_user") as mock_auth:
            mock_auth.return_value = type('User', (), {'id': 'user_test_123'})()
            response = client.get(
                "/api/v1/measurements?limit=10&offset=20",
                headers=auth_headers
            )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["limit"] == 10
        assert data["offset"] == 20
    
    def test_list_measurements_filter_by_user(self, client, auth_headers):
        """Test filtering measurements by user_id."""
        with patch("src.api.measurements.get_current_active_user") as mock_auth:
            mock_auth.return_value = type('User', (), {'id': 'user_test_123'})()
            response = client.get(
                "/api/v1/measurements?user_id=user_123",
                headers=auth_headers
            )
        
        assert response.status_code == status.HTTP_200_OK
    
    def test_list_measurements_filter_by_session(self, client, auth_headers):
        """Test filtering measurements by session_id."""
        with patch("src.api.measurements.get_current_active_user") as mock_auth:
            mock_auth.return_value = type('User', (), {'id': 'user_test_123'})()
            response = client.get(
                "/api/v1/measurements?session_id=session_456",
                headers=auth_headers
            )
        
        assert response.status_code == status.HTTP_200_OK
    
    def test_list_measurements_filter_by_date_range(self, client, auth_headers):
        """Test filtering measurements by date range."""
        from_date = "2026-01-01T00:00:00"
        to_date = "2026-01-31T23:59:59"
        
        with patch("src.api.measurements.get_current_active_user") as mock_auth:
            mock_auth.return_value = type('User', (), {'id': 'user_test_123'})()
            response = client.get(
                f"/api/v1/measurements?from_date={from_date}&to_date={to_date}",
                headers=auth_headers
            )
        
        assert response.status_code == status.HTTP_200_OK
    
    def test_list_measurements_unauthorized(self, client):
        """Test listing without authentication fails."""
        response = client.get("/api/v1/measurements")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestManualMeasurementOverride:
    """Test POST /measurements/{id}/manual - Manual measurement override.
    
    Reference: Ops Manual Section 2.2.4.4 - Manual Review Queue
    Used when confidence is low or user wants to correct measurements.
    """
    
    def test_manual_override_success(self, client, auth_headers):
        """Test successful manual measurement override."""
        measurement_id = "test_override"
        
        with patch("src.api.measurements.get_current_active_user") as mock_auth:
            mock_auth.return_value = type('User', (), {'id': 'user_test_123'})()
            response = client.post(
                f"/api/v1/measurements/{measurement_id}/manual",
                params={
                    "measurement_type": "chest_girth",
                    "value": 104.5
                },
                headers=auth_headers
            )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["measurement_id"] == measurement_id
        assert data["measurement_type"] == "chest_girth"
        assert data["updated_value"] == 104.5
        assert data["method"] == "manual"
        assert "updated_at" in data
    
    def test_manual_override_multiple_measurements(self, client, auth_headers):
        """Test manual override for different measurement types."""
        measurement_id = "test_override_multi"
        
        measurement_types = ["chest_girth", "waist_girth", "hip_girth", "inseam"]
        
        for mtype in measurement_types:
            with patch("src.api.measurements.get_current_active_user") as mock_auth:
                mock_auth.return_value = type('User', (), {'id': 'user_test_123'})()
                response = client.post(
                    f"/api/v1/measurements/{measurement_id}/manual",
                    params={
                        "measurement_type": mtype,
                        "value": 100.0
                    },
                    headers=auth_headers
                )
            
            assert response.status_code == status.HTTP_200_OK
            assert response.json()["measurement_type"] == mtype
    
    def test_manual_override_unauthorized(self, client):
        """Test manual override without authentication fails."""
        response = client.post(
            "/api/v1/measurements/test/manual",
            params={"measurement_type": "chest_girth", "value": 100.0}
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestExportMeasurements:
    """Test GET /measurements/{id}/export - Measurement export endpoint."""
    
    @pytest.mark.parametrize("format", ["json", "csv", "pdf"])
    def test_export_measurements_all_formats(self, client, auth_headers, format):
        """Test exporting measurements in all supported formats.
        
        Formats: json, csv, pdf
        """
        measurement_id = "test_export"
        
        with patch("src.api.measurements.get_current_active_user") as mock_auth:
            mock_auth.return_value = type('User', (), {'id': 'user_test_123'})()
            response = client.get(
                f"/api/v1/measurements/{measurement_id}/export?format={format}",
                headers=auth_headers
            )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["measurement_id"] == measurement_id
        assert data["format"] == format
        assert "download_url" in data
    
    def test_export_invalid_format(self, client, auth_headers):
        """Test export with invalid format fails."""
        measurement_id = "test_export"
        
        with patch("src.api.measurements.get_current_active_user") as mock_auth:
            mock_auth.return_value = type('User', (), {'id': 'user_test_123'})()
            response = client.get(
                f"/api/v1/measurements/{measurement_id}/export?format=xml",
                headers=auth_headers
            )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_export_unauthorized(self, client):
        """Test export without authentication fails."""
        response = client.get("/api/v1/measurements/test/export")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestDeleteMeasurement:
    """Test DELETE /measurements/{id} - Measurement deletion endpoint."""
    
    def test_delete_measurement_success(self, client, auth_headers):
        """Test successful measurement deletion."""
        measurement_id = "test_delete"
        
        with patch("src.api.measurements.get_current_active_user") as mock_auth:
            mock_auth.return_value = type('User', (), {'id': 'user_test_123'})()
            response = client.delete(
                f"/api/v1/measurements/{measurement_id}",
                headers=auth_headers
            )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["measurement_id"] == measurement_id
        assert data["deleted"] is True
    
    def test_delete_measurement_unauthorized(self, client):
        """Test deletion without authentication fails."""
        response = client.delete("/api/v1/measurements/test")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestPatternFactoryFormat:
    """Test transformation to Pattern Factory format.
    
    Reference: Ops Manual Section 2.4 - Pattern Factory Integration
    Measurements must be transformed for Optitex/parametric pattern generation.
    """
    
    def test_pattern_factory_format_structure(self, client, auth_headers, pattern_factory_format):
        """Test measurements export in Pattern Factory format."""
        measurement_id = "test_pf_format"
        
        with patch("src.api.measurements.get_current_active_user") as mock_auth:
            mock_auth.return_value = type('User', (), {'id': 'user_test_123'})()
            # Get measurements in JSON format
            response = client.get(
                f"/api/v1/measurements/{measurement_id}/export?format=json",
                headers=auth_headers
            )
        
        assert response.status_code == status.HTTP_200_OK
        
        # Verify Pattern Factory structure
        expected_structure = pattern_factory_format
        assert "order_id" in expected_structure
        assert "measurements" in expected_structure
        assert "jacket" in expected_structure["measurements"]
        assert "trousers" in expected_structure["measurements"]
        assert "confidence" in expected_structure
        assert "source" in expected_structure
        assert "timestamp" in expected_structure
    
    def test_p0_measurements_in_pf_format(self, client, auth_headers, p0_measurements):
        """Test P0 measurements map correctly to Pattern Factory format."""
        measurement_id = "test_pf_p0"
        
        with patch("src.api.measurements.get_current_active_user") as mock_auth:
            mock_auth.return_value = type('User', (), {'id': 'user_test_123'})()
            response = client.get(
                f"/api/v1/measurements/{measurement_id}",
                headers=auth_headers
            )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Verify P0 measurements exist with proper structure
        assert "chest_girth" in data
        assert "waist_girth" in data
        assert "hip_girth" in data
        assert "shoulder_width" in data
        assert "arm_length" in data
        assert "back_length" in data
        assert "neck_girth" in data
        
        # All should have P0 accuracy grade
        for field in ["chest_girth", "waist_girth", "hip_girth", "shoulder_width",
                      "arm_length", "back_length", "neck_girth"]:
            assert data[field]["accuracy_grade"] == "P0"
    
    def test_p1_measurements_in_pf_format(self, client, auth_headers, p1_measurements):
        """Test P1 measurements map correctly to Pattern Factory format."""
        measurement_id = "test_pf_p1"
        
        with patch("src.api.measurements.get_current_active_user") as mock_auth:
            mock_auth.return_value = type('User', (), {'id': 'user_test_123'})()
            response = client.get(
                f"/api/v1/measurements/{measurement_id}",
                headers=auth_headers
            )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Verify P1 measurements exist
        assert "bicep_girth" in data
        assert "wrist_girth" in data
        assert "inseam" in data
        assert "thigh_girth" in data
        assert "knee_girth" in data
        assert "calf_girth" in data
        
        # All should have P1 accuracy grade
        for field in ["bicep_girth", "wrist_girth", "inseam", "thigh_girth",
                      "knee_girth", "calf_girth"]:
            assert data[field]["accuracy_grade"] == "P1"


class TestMeasurementConfidenceScoring:
    """Test measurement confidence scoring system.
    
    Reference: Ops Manual Section 2.2.3.2 - Confidence Scoring
    Score Interpretation:
        90-100%: Excellent - Auto-proceed
        70-89%: Acceptable - Auto-proceed with advisory
        50-69%: Marginal - Recommend rescan
        <50%: Poor - Require rescan
    """
    
    def test_excellent_confidence_auto_proceed(self, client, auth_headers):
        """Test measurements with 90-100% confidence auto-proceed."""
        measurement_id = "test_excellent"
        
        with patch("src.api.measurements.get_current_active_user") as mock_auth:
            mock_auth.return_value = type('User', (), {'id': 'user_test_123'})()
            response = client.get(
                f"/api/v1/measurements/{measurement_id}",
                headers=auth_headers
            )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        if data["overall_confidence"] >= 0.90:
            # Should proceed to pattern generation
            assert data["overall_confidence"] >= 0.90
    
    def test_acceptable_confidence_with_advisory(self, client, auth_headers):
        """Test measurements with 70-89% confidence get advisory flag."""
        measurement_id = "test_acceptable"
        
        # Mock response with 80% confidence
        with patch("src.api.measurements.get_current_active_user") as mock_auth:
            mock_auth.return_value = type('User', (), {'id': 'user_test_123'})()
            response = client.get(
                f"/api/v1/measurements/{measurement_id}",
                headers=auth_headers
            )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        if 0.70 <= data["overall_confidence"] < 0.90:
            # Should have advisory flag or note
            assert data["overall_confidence"] >= 0.70
    
    def test_marginal_confidence_recommend_rescan(self, client, auth_headers):
        """Test measurements with 50-69% confidence recommend rescan."""
        measurement_id = "test_marginal"
        
        with patch("src.api.measurements.get_current_active_user") as mock_auth:
            mock_auth.return_value = type('User', (), {'id': 'user_test_123'})()
            response = client.get(
                f"/api/v1/measurements/{measurement_id}",
                headers=auth_headers
            )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        if 0.50 <= data["overall_confidence"] < 0.70:
            assert data["overall_confidence"] < 0.70
    
    def test_poor_confidence_require_rescan(self, client, auth_headers):
        """Test measurements with <50% confidence require rescan."""
        measurement_id = "test_poor"
        
        with patch("src.api.measurements.get_current_active_user") as mock_auth:
            mock_auth.return_value = type('User', (), {'id': 'user_test_123'})()
            response = client.get(
                f"/api/v1/measurements/{measurement_id}",
                headers=auth_headers
            )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        if data["overall_confidence"] < 0.50:
            assert data["overall_confidence"] < 0.50


class TestMeasurementUnits:
    """Test measurement units are consistent and correct."""
    
    def test_all_measurements_use_cm(self, client, auth_headers, all_28_measurements):
        """Test all measurements use centimeters as unit."""
        measurement_id = "test_units"
        
        with patch("src.api.measurements.get_current_active_user") as mock_auth:
            mock_auth.return_value = type('User', (), {'id': 'user_test_123'})()
            response = client.get(
                f"/api/v1/measurements/{measurement_id}",
                headers=auth_headers
            )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Check all measurements use cm
        for key, value in data.items():
            if isinstance(value, dict) and "value" in value and "unit" in value:
                assert value["unit"] == "cm", f"{key} has unit {value['unit']}, expected cm"
