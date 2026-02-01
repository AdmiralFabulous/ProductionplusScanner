"""
EYESON Backend API - Pytest Fixtures

Shared fixtures for unit testing the EYESON BodyScan API.
Provides mocked dependencies, test data, and common utilities.

Reference: SUIT AI Master Operations Manual v6.8
- Section 1.2: 27-State Order Machine
- Section 2.5: Security Layer (JWT Auth)
- Section 13: Database Schema (28 measurement codes)
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import AsyncClient

# Import the FastAPI app
import sys
import os

# Add the backend src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "eyeson", "backend"))

from src.main import app
from src.core.config import Settings, get_settings
from src.api.sessions import SessionStatus, ScanMode, sessions_store
from src.api.measurements import MeasurementValue
from src.api.auth import UserInfo


# =============================================================================
# Test Configuration Fixtures
# =============================================================================

@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
def test_settings() -> Settings:
    """Provide test-specific settings.
    
    Reference: Ops Manual Section 2.5 - Security Layer Configuration
    """
    return Settings(
        environment="test",
        debug=True,
        secret_key="test-secret-key-not-for-production",
        access_token_expire_minutes=30,
        refresh_token_expire_days=7,
        database_url="postgresql+asyncpg://test:test@localhost/test_eyeson",
        redis_url="redis://localhost:6379/15",  # Use DB 15 for tests
        storage_bucket="test-eyeson-scans",
        tts_cache_dir="/tmp/test_tts_cache",
        voice_prompts_dir="/tmp/test_voice_prompts",
    )


@pytest.fixture(scope="function")
def override_settings(test_settings: Settings) -> Generator[None, None, None]:
    """Override FastAPI settings dependency for testing."""
    def get_test_settings():
        return test_settings
    
    app.dependency_overrides[get_settings] = get_test_settings
    yield
    app.dependency_overrides.clear()


# =============================================================================
# HTTP Client Fixtures
# =============================================================================

@pytest.fixture(scope="function")
def client(override_settings) -> TestClient:
    """Provide a synchronous TestClient for API testing."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="function")
async def async_client(override_settings) -> AsyncGenerator[AsyncClient, None]:
    """Provide an asynchronous HTTP client for API testing."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


# =============================================================================
# Authentication Fixtures
# =============================================================================

@pytest.fixture(scope="function")
def mock_jwt_token() -> str:
    """Provide a mock JWT token for authenticated requests.
    
    Reference: Ops Manual Section 2.5.2 - JWT Token Structure
    """
    return "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test.payload.signature"


@pytest.fixture(scope="function")
def mock_refresh_token() -> str:
    """Provide a mock refresh token."""
    return "refresh_token_test_12345"


@pytest.fixture(scope="function")
def mock_expired_token() -> str:
    """Provide a mock expired JWT token."""
    return "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.expired.payload.signature"


@pytest.fixture(scope="function")
def auth_headers(mock_jwt_token: str) -> dict:
    """Provide authorization headers with Bearer token."""
    return {
        "Authorization": f"Bearer {mock_jwt_token}",
        "Content-Type": "application/json"
    }


@pytest.fixture(scope="function")
def mock_user() -> UserInfo:
    """Provide a mock authenticated user."""
    return UserInfo(
        id="user_test_123",
        email="test.user@example.com",
        name="Test User",
        organization="SameDaySuits"
    )


@pytest.fixture(scope="function")
def mock_admin_user() -> UserInfo:
    """Provide a mock admin user."""
    return UserInfo(
        id="admin_456",
        email="admin@example.com",
        name="Admin User",
        organization="SameDaySuits"
    )


# =============================================================================
# Session Fixtures
# =============================================================================

@pytest.fixture(scope="function")
def mock_session_id() -> str:
    """Provide a mock session ID."""
    return str(uuid4())


@pytest.fixture(scope="function")
def mock_session_data(mock_session_id: str) -> dict:
    """Provide complete mock session data.
    
    Reference: Ops Manual Section 1.2 - Session State Flow
    State transitions: INITIATED → CALIBRATING → CAPTURING → PROCESSING → COMPLETED
    """
    now = datetime.utcnow()
    return {
        "session_id": mock_session_id,
        "user_id": "user_test_123",
        "status": SessionStatus.INITIATED,
        "scan_mode": ScanMode.VIDEO,
        "language": "en",
        "device_info": {
            "type": "mobile",
            "os": "iOS 17.0",
            "browser": "Safari",
            "camera_resolution": "1920x1080"
        },
        "websocket_url": f"wss://api.eyeson.io/ws/{mock_session_id}",
        "created_at": now,
        "expires_at": now + timedelta(hours=1),
        "calibration": None,
        "video_url": None,
        "progress_percent": 0,
        "measurements": None,
        "error_message": None,
    }


@pytest.fixture(scope="function")
def mock_calibrated_session(mock_session_data: dict) -> dict:
    """Provide a mock session in CALIBRATING state."""
    mock_session_data["status"] = SessionStatus.CALIBRATING
    mock_session_data["calibration"] = {
        "marker_size_cm": 14.0,
        "scale_factor": 0.035,
        "confidence": 0.95,
        "height_estimate_cm": 175.0
    }
    return mock_session_data


@pytest.fixture(scope="function")
def mock_capturing_session(mock_calibrated_session: dict) -> dict:
    """Provide a mock session in CAPTURING state."""
    mock_calibrated_session["status"] = SessionStatus.CAPTURING
    mock_calibrated_session["video_url"] = f"s3://test-bucket/videos/{mock_calibrated_session['session_id']}.mp4"
    return mock_calibrated_session


@pytest.fixture(scope="function")
def mock_processing_session(mock_capturing_session: dict) -> dict:
    """Provide a mock session in PROCESSING state."""
    mock_capturing_session["status"] = SessionStatus.PROCESSING
    mock_capturing_session["progress_percent"] = 50
    return mock_capturing_session


@pytest.fixture(scope="function")
def mock_completed_session(mock_processing_session: dict) -> dict:
    """Provide a mock session in COMPLETED state."""
    mock_processing_session["status"] = SessionStatus.COMPLETED
    mock_processing_session["progress_percent"] = 100
    mock_processing_session["measurements"] = {"measurement_id": "meas_123"}
    return mock_processing_session


@pytest.fixture(scope="function")
def mock_expired_session(mock_session_data: dict) -> dict:
    """Provide a mock expired session."""
    mock_session_data["status"] = SessionStatus.EXPIRED
    mock_session_data["expires_at"] = datetime.utcnow() - timedelta(minutes=1)
    return mock_session_data


@pytest.fixture(scope="function")
def mock_failed_session(mock_session_data: dict) -> dict:
    """Provide a mock failed session."""
    mock_session_data["status"] = SessionStatus.FAILED
    mock_session_data["error_message"] = "Processing failed: insufficient video quality"
    return mock_session_data


# =============================================================================
# Measurement Fixtures
# =============================================================================

@pytest.fixture(scope="function")
def mock_measurement_id() -> str:
    """Provide a mock measurement ID."""
    return f"meas_{uuid4().hex[:12]}"


@pytest.fixture(scope="function")
def p0_measurements() -> dict:
    """Provide P0 (Critical) measurements with high confidence.
    
    Reference: Ops Manual Section 13 - 28 Measurement Codes
    P0: Critical measurements requiring ±1cm accuracy, confidence ≥ 0.90
    """
    return {
        "chest_girth": MeasurementValue(value=102.5, confidence=0.92, accuracy_grade="P0", unit="cm"),
        "waist_girth": MeasurementValue(value=88.3, confidence=0.91, accuracy_grade="P0", unit="cm"),
        "hip_girth": MeasurementValue(value=98.7, confidence=0.93, accuracy_grade="P0", unit="cm"),
        "shoulder_width": MeasurementValue(value=46.2, confidence=0.94, accuracy_grade="P0", unit="cm"),
        "arm_length": MeasurementValue(value=64.8, confidence=0.90, accuracy_grade="P0", unit="cm"),
        "back_length": MeasurementValue(value=48.5, confidence=0.91, accuracy_grade="P0", unit="cm"),
        "neck_girth": MeasurementValue(value=39.4, confidence=0.95, accuracy_grade="P0", unit="cm"),
    }


@pytest.fixture(scope="function")
def p1_measurements() -> dict:
    """Provide P1 (Important) measurements.
    
    Reference: Ops Manual Section 13 - 28 Measurement Codes
    P1: Important measurements requiring ±2cm accuracy, confidence ≥ 0.85
    """
    return {
        "bicep_girth": MeasurementValue(value=32.1, confidence=0.87, accuracy_grade="P1", unit="cm"),
        "wrist_girth": MeasurementValue(value=17.8, confidence=0.88, accuracy_grade="P1", unit="cm"),
        "inseam": MeasurementValue(value=82.4, confidence=0.86, accuracy_grade="P1", unit="cm"),
        "thigh_girth": MeasurementValue(value=58.3, confidence=0.85, accuracy_grade="P1", unit="cm"),
        "knee_girth": MeasurementValue(value=38.9, confidence=0.85, accuracy_grade="P1", unit="cm"),
        "calf_girth": MeasurementValue(value=37.2, confidence=0.85, accuracy_grade="P1", unit="cm"),
    }


@pytest.fixture(scope="function")
def derived_measurements() -> dict:
    """Provide derived measurements (part of 28 total).
    
    Reference: Ops Manual Section 13 - Derived measurements from base calculations
    """
    return {
        "back_width": MeasurementValue(value=38.5, confidence=0.81, unit="cm"),
        "chest_width": MeasurementValue(value=36.8, confidence=0.80, unit="cm"),
        "scye_depth": MeasurementValue(value=24.3, confidence=0.79, unit="cm"),
        "neck_width": MeasurementValue(value=12.5, confidence=0.88, unit="cm"),
        "half_back": MeasurementValue(value=19.2, confidence=0.82, unit="cm"),
        "crotch_depth": MeasurementValue(value=26.7, confidence=0.78, unit="cm"),
    }


@pytest.fixture(scope="function")
def all_28_measurements(p0_measurements: dict, p1_measurements: dict, derived_measurements: dict) -> dict:
    """Provide all 28 measurements combined.
    
    Reference: Ops Manual Section 13 - Complete Measurement Schema
    Total: 7 P0 + 6 P1 + 15 Derived = 28 measurements
    """
    # Add remaining derived measurements to reach 28 total
    additional_derived = {
        "front_waist_length": MeasurementValue(value=45.2, confidence=0.80, unit="cm"),
        "back_waist_length": MeasurementValue(value=47.8, confidence=0.79, unit="cm"),
        "armscye_girth": MeasurementValue(value=48.5, confidence=0.82, unit="cm"),
        "elbow_girth": MeasurementValue(value=28.4, confidence=0.83, unit="cm"),
        "forearm_girth": MeasurementValue(value=26.8, confidence=0.81, unit="cm"),
        "outseam": MeasurementValue(value=105.2, confidence=0.84, unit="cm"),
        "ankle_girth": MeasurementValue(value=24.5, confidence=0.82, unit="cm"),
        "front_rise": MeasurementValue(value=28.3, confidence=0.77, unit="cm"),
        "back_rise": MeasurementValue(value=35.6, confidence=0.76, unit="cm"),
    }
    
    all_measurements = {}
    all_measurements.update(p0_measurements)
    all_measurements.update(p1_measurements)
    all_measurements.update(derived_measurements)
    all_measurements.update(additional_derived)
    
    return all_measurements


@pytest.fixture(scope="function")
def mock_measurements_response(mock_measurement_id: str, mock_session_id: str, 
                                all_28_measurements: dict) -> dict:
    """Provide complete measurements API response."""
    return {
        "measurement_id": mock_measurement_id,
        "session_id": mock_session_id,
        "user_id": "user_test_123",
        "created_at": datetime.utcnow().isoformat(),
        **all_28_measurements,
        "overall_confidence": 0.88,
        "figure_deviations": [],
        "mesh_url": f"https://storage.eyeson.io/meshes/{mock_measurement_id}.ply"
    }


@pytest.fixture(scope="function")
def measurement_validation_ranges() -> dict:
    """Provide min/max validation ranges for measurements.
    
    Reference: Ops Manual Section 13 - Measurement validation rules
    """
    return {
        "chest_girth": {"min": 80, "max": 140, "unit": "cm"},
        "waist_girth": {"min": 60, "max": 130, "unit": "cm"},
        "hip_girth": {"min": 80, "max": 140, "unit": "cm"},
        "shoulder_width": {"min": 38, "max": 56, "unit": "cm"},
        "arm_length": {"min": 58, "max": 72, "unit": "cm"},
        "back_length": {"min": 38, "max": 52, "unit": "cm"},
        "neck_girth": {"min": 34, "max": 52, "unit": "cm"},
        "bicep_girth": {"min": 26, "max": 50, "unit": "cm"},
        "wrist_girth": {"min": 14, "max": 22, "unit": "cm"},
        "inseam": {"min": 70, "max": 95, "unit": "cm"},
        "thigh_girth": {"min": 40, "max": 80, "unit": "cm"},
        "knee_girth": {"min": 30, "max": 55, "unit": "cm"},
        "calf_girth": {"min": 28, "max": 50, "unit": "cm"},
    }


@pytest.fixture(scope="function")
def pattern_factory_format() -> dict:
    """Provide Pattern Factory expected format for measurements.
    
    Reference: Ops Manual Section 2.4 - Pattern Factory Integration
    """
    return {
        "order_id": "ORD-2026-001",
        "measurements": {
            "jacket": {
                "chest": 102.5,
                "waist": 88.3,
                "hip": 98.7,
                "shoulder": 46.2,
                "sleeve_length": 64.8,
                "back_length": 48.5,
                "neck": 39.4,
                "bicep": 32.1,
                "wrist": 17.8,
            },
            "trousers": {
                "waist": 88.3,
                "hip": 98.7,
                "inseam": 82.4,
                "thigh": 58.3,
                "knee": 38.9,
                "calf": 37.2,
            }
        },
        "confidence": 0.88,
        "source": "EYESON_SCAN",
        "timestamp": datetime.utcnow().isoformat()
    }


# =============================================================================
# Voice/TTS Fixtures
# =============================================================================

@pytest.fixture(scope="function")
def supported_languages() -> list:
    """Provide list of supported TTS languages.
    
    Reference: Ops Manual Section 2.1.10 - Multi-language Support
    """
    return ["en", "es", "fr", "de", "zh", "ar"]


@pytest.fixture(scope="function")
def mock_voice_prompts() -> dict:
    """Provide mock voice prompts for all supported languages."""
    return {
        "en": {
            "welcome": "Welcome to EYESON BodyScan. I'm your AI guide.",
            "calibration": "Place the calibration card on the floor.",
            "capture_start": "Starting scan in 3, 2, 1.",
            "capture_complete": "Scan complete! Processing your measurements.",
        },
        "es": {
            "welcome": "Bienvenido a EYESON BodyScan. Soy tu guía de IA.",
            "calibration": "Coloque la tarjeta de calibración en el suelo.",
            "capture_start": "Comenzando escaneo en 3, 2, 1.",
            "capture_complete": "¡Escaneo completo! Procesando sus mediciones.",
        },
        "fr": {
            "welcome": "Bienvenue sur EYESON BodyScan. Je suis votre guide IA.",
            "calibration": "Placez la carte de calibration au sol.",
            "capture_start": "Démarrage du scan dans 3, 2, 1.",
            "capture_complete": "Scan terminé ! Traitement de vos mesures.",
        },
        "de": {
            "welcome": "Willkommen bei EYESON BodyScan. Ich bin Ihr KI-Guide.",
            "calibration": "Platzieren Sie die Kalibrierungskarte auf dem Boden.",
            "capture_start": "Scan startet in 3, 2, 1.",
            "capture_complete": "Scan abgeschlossen! Verarbeite Ihre Messungen.",
        },
        "zh": {
            "welcome": "欢迎使用 EYESON BodyScan。我是您的 AI 向导。",
            "calibration": "将校准卡放在地板上。",
            "capture_start": "3、2、1 开始扫描。",
            "capture_complete": "扫描完成！正在处理您的测量数据。",
        },
        "ar": {
            "welcome": "مرحبًا بك في EYESON BodyScan. أنا دليلك الذكي.",
            "calibration": "ضع بطاقة المعايرة على الأرض.",
            "capture_start": "بدء المسح في 3، 2، 1.",
            "capture_complete": "اكتمل المسح! جاري معالجة قياساتك.",
        },
    }


@pytest.fixture(scope="function")
def mock_tts_audio_data() -> bytes:
    """Provide mock TTS audio data (WAV format)."""
    # Minimal valid WAV header + some data
    return b'RIFF\x26\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x44\xAC\x00\x00\x88X\x01\x00\x02\x00\x10\x00data\x02\x00\x00\x00\x00\x00'


@pytest.fixture(scope="function")
def mock_tts_service() -> MagicMock:
    """Provide a mock TTS service."""
    mock = MagicMock()
    mock.synthesize = AsyncMock(return_value=b'mock_audio_data')
    mock.synthesize_stream = AsyncMock(return_value=async_generator([b'chunk1', b'chunk2']))
    mock.health_check = AsyncMock(return_value={"status": "healthy", "engine": "Kokoro-82M"})
    mock.get_voices = Mock(return_value={
        "primary": ["af", "am", "bf", "bm"],
        "fallback": ["en_US-lessac-medium"]
    })
    mock.cache = MagicMock()
    mock.cache.clear = Mock(return_value=None)
    return mock


async def async_generator(items):
    """Helper to create async generator from list."""
    for item in items:
        yield item


# =============================================================================
# File Upload Fixtures
# =============================================================================

@pytest.fixture(scope="function")
def mock_video_file() -> tuple:
    """Provide mock video file data."""
    content = b'mock_video_content_mp4' * 1000  # ~22KB mock video
    return ("scan_video.mp4", content, "video/mp4")


@pytest.fixture(scope="function")
def mock_front_image() -> tuple:
    """Provide mock front image data."""
    content = b'mock_jpeg_content' * 100
    return ("front.jpg", content, "image/jpeg")


@pytest.fixture(scope="function")
def mock_side_image() -> tuple:
    """Provide mock side image data."""
    content = b'mock_jpeg_content_side' * 100
    return ("side.jpg", content, "image/jpeg")


@pytest.fixture(scope="function")
def mock_calibration_image() -> tuple:
    """Provide mock calibration marker image."""
    content = b'mock_calibration_marker_jpeg' * 100
    return ("calibration.jpg", content, "image/jpeg")


# =============================================================================
# Cleanup Fixtures
# =============================================================================

@pytest.fixture(scope="function", autouse=True)
def clear_sessions_store() -> Generator[None, None, None]:
    """Clear the in-memory sessions store before each test."""
    sessions_store.clear()
    yield
    sessions_store.clear()


# =============================================================================
# Assertion Helpers
# =============================================================================

def assert_valid_session_response(response_data: dict, expected_status: SessionStatus = None) -> None:
    """Helper to validate session response structure."""
    assert "session_id" in response_data
    assert "status" in response_data
    assert "scan_mode" in response_data
    assert "language" in response_data
    assert "websocket_url" in response_data
    assert "expires_at" in response_data
    assert "created_at" in response_data
    
    if expected_status:
        assert response_data["status"] == expected_status.value


def assert_valid_measurement_response(response_data: dict) -> None:
    """Helper to validate measurement response structure."""
    assert "measurement_id" in response_data
    assert "session_id" in response_data
    assert "created_at" in response_data
    assert "overall_confidence" in response_data
    
    # Check P0 measurements exist
    p0_fields = ["chest_girth", "waist_girth", "hip_girth", "shoulder_width", 
                 "arm_length", "back_length", "neck_girth"]
    for field in p0_fields:
        assert field in response_data, f"Missing P0 measurement: {field}"
        assert "value" in response_data[field]
        assert "confidence" in response_data[field]
        assert "accuracy_grade" in response_data[field]


def assert_valid_tts_response(response_data: dict) -> None:
    """Helper to validate TTS response structure."""
    assert "success" in response_data
    assert "voice_used" in response_data
    assert "cached" in response_data
