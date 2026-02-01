"""
PRODUCTION-SCANNER Test Configuration
Reference: SUIT_AI_Master_Operations_Manual_v6_8.md

Sections Referenced:
- 1.2: 27-State Order Machine (test state fixtures)
- 2.5: Security Layer (auth fixtures)
- 2.6: Scalability Layer (performance baselines)
- 13: Database Schema (test data structures)
"""

import asyncio
import os
import uuid
from datetime import datetime, timedelta
from typing import AsyncGenerator, Dict, Generator, List

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import AsyncClient

# Test Database Configuration
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql://samedaysuits:test@localhost:5432/samedaysuits_test"
)

# Test Redis Configuration
TEST_REDIS_URL = os.getenv(
    "TEST_REDIS_URL",
    "redis://localhost:6379/15"  # Use DB 15 for tests
)

# JWT Test Secrets
TEST_JWT_SECRET = "test-jwt-secret-minimum-32-characters-long"
TEST_JWT_REFRESH_SECRET = "test-refresh-secret-different-from-jwt"


# =============================================================================
# DATABASE FIXTURES
# =============================================================================

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def test_db() -> AsyncGenerator:
    """
    Create a test database connection.
    
    Reference: Ops Manual v6.8 Section 13 - Database Schema
    """
    # Setup: Create test tables
    # TODO: Initialize test database with schema
    
    yield TEST_DATABASE_URL
    
    # Teardown: Clean up test data
    # TODO: Truncate test tables


@pytest_asyncio.fixture(scope="function")
async def test_redis() -> AsyncGenerator:
    """
    Create a test Redis connection.
    
    Reference: Ops Manual v6.8 Section 2.6 - Scalability Layer (Caching)
    """
    import redis.asyncio as redis
    
    client = redis.from_url(TEST_REDIS_URL, decode_responses=True)
    
    # Clear test database before each test
    await client.flushdb()
    
    yield client
    
    # Cleanup
    await client.flushdb()
    await client.close()


# =============================================================================
# AUTHENTICATION FIXTURES
# =============================================================================

@pytest.fixture
def jwt_test_settings() -> Dict:
    """
    JWT test configuration.
    
    Reference: Ops Manual v6.8 Section 2.5 - Security Layer
    """
    return {
        "secret_key": TEST_JWT_SECRET,
        "refresh_secret_key": TEST_JWT_REFRESH_SECRET,
        "algorithm": "HS256",
        "access_token_expire_minutes": 60,  # 1 hour as per spec
        "refresh_token_expire_days": 7,
    }


@pytest.fixture
def test_user() -> Dict:
    """Test user fixture with standard permissions."""
    return {
        "id": str(uuid.uuid4()),
        "email": "test@example.com",
        "permissions": ["orders:read", "orders:write", "sessions:read"],
        "is_active": True,
    }


@pytest.fixture
def valid_access_token(test_user, jwt_test_settings) -> str:
    """Generate a valid JWT access token for testing."""
    from jose import jwt
    
    now = datetime.utcnow()
    payload = {
        "sub": test_user["email"],
        "exp": now + timedelta(minutes=jwt_test_settings["access_token_expire_minutes"]),
        "iat": now,
        "iss": "test-pattern-factory",
        "scope": test_user["permissions"],
        "jti": str(uuid.uuid4()),
    }
    
    return jwt.encode(
        payload,
        jwt_test_settings["secret_key"],
        algorithm=jwt_test_settings["algorithm"]
    )


@pytest.fixture
def expired_access_token(test_user, jwt_test_settings) -> str:
    """Generate an expired JWT access token for testing."""
    from jose import jwt
    
    now = datetime.utcnow()
    payload = {
        "sub": test_user["email"],
        "exp": now - timedelta(minutes=5),  # Expired 5 minutes ago
        "iat": now - timedelta(hours=1),
        "iss": "test-pattern-factory",
        "scope": test_user["permissions"],
        "jti": str(uuid.uuid4()),
    }
    
    return jwt.encode(
        payload,
        jwt_test_settings["secret_key"],
        algorithm=jwt_test_settings["algorithm"]
    )


@pytest.fixture
def auth_headers(valid_access_token) -> Dict[str, str]:
    """Return authorization headers with valid token."""
    return {
        "Authorization": f"Bearer {valid_access_token}",
        "Content-Type": "application/json",
    }


# =============================================================================
# MEASUREMENT FIXTURES
# =============================================================================

@pytest.fixture
def valid_p0_measurements() -> Dict:
    """
    Valid P0 (Primary) measurements with high confidence.
    
    Reference: Ops Manual v6.8 Section 13 - Database Schema
    P0 Tolerance: ±0.5-1cm, Confidence ≥ 0.90
    """
    return {
        "Cg": {"value": 102.5, "unit": "cm", "confidence": 0.95},  # Chest Girth
        "Wg": {"value": 88.0, "unit": "cm", "confidence": 0.92},   # Waist Girth
        "Hg": {"value": 98.5, "unit": "cm", "confidence": 0.94},   # Hip Girth
        "Sh": {"value": 46.0, "unit": "cm", "confidence": 0.91},   # Shoulder Width
        "Al": {"value": 64.5, "unit": "cm", "confidence": 0.93},   # Arm Length
        "Il": {"value": 82.0, "unit": "cm", "confidence": 0.90},   # Inseam
        "Nc": {"value": 41.0, "unit": "cm", "confidence": 0.94},   # Neck Girth
        "Bg": {"value": 34.0, "unit": "cm", "confidence": 0.88},   # Bicep Girth
        "Wr": {"value": 17.5, "unit": "cm", "confidence": 0.95},   # Wrist Girth
        "Tg": {"value": 58.0, "unit": "cm", "confidence": 0.87},   # Thigh Girth
        "Kg": {"value": 40.0, "unit": "cm", "confidence": 0.89},   # Knee Girth
        "Ca": {"value": 38.0, "unit": "cm", "confidence": 0.88},   # Calf Girth
        "Bw": {"value": 38.5, "unit": "cm", "confidence": 0.90},   # Back Width
    }


@pytest.fixture
def valid_p1_measurements() -> Dict:
    """
    Valid P1 (Secondary) measurements.
    
    Reference: Ops Manual v6.8 Section 13 - Database Schema
    P1 Tolerance: ±1-2cm, Confidence ≥ 0.85
    """
    return {
        "Fwl": {"value": 42.0, "unit": "cm", "confidence": 0.88},  # Front Waist Length
        "Bwl": {"value": 44.0, "unit": "cm", "confidence": 0.86},  # Back Waist Length
        "Fsw": {"value": 38.0, "unit": "cm", "confidence": 0.87},  # Front Shoulder Width
        "Si": {"value": 48.0, "unit": "cm", "confidence": 0.89},   # Sleeve Inseam
        "Cd": {"value": 28.0, "unit": "cm", "confidence": 0.90},   # Crotch Depth
        "Os": {"value": 102.0, "unit": "cm", "confidence": 0.85},  # Outseam
    }


@pytest.fixture
def invalid_low_confidence_measurements() -> Dict:
    """Measurements with confidence below threshold for error testing."""
    return {
        "Cg": {"value": 102.5, "unit": "cm", "confidence": 0.75},  # Below P0 threshold (0.90)
        "Wg": {"value": 88.0, "unit": "cm", "confidence": 0.80},   # Below P0 threshold
    }


@pytest.fixture
def valid_eyeson_measurements() -> Dict:
    """EYESON format measurements for transformation testing."""
    return {
        "chest_girth": {"value": 102.5, "unit": "cm", "confidence": 0.95},
        "waist_girth": {"value": 88.0, "unit": "cm", "confidence": 0.92},
        "hip_girth": {"value": 98.5, "unit": "cm", "confidence": 0.94},
        "shoulder_width": {"value": 46.0, "unit": "cm", "confidence": 0.91},
        "arm_length": {"value": 64.5, "unit": "cm", "confidence": 0.93},
        "inseam": {"value": 82.0, "unit": "cm", "confidence": 0.90},
    }


# =============================================================================
# ORDER STATE FIXTURES
# =============================================================================

@pytest.fixture
def order_state_transitions() -> List[Dict]:
    """
    Valid order state transitions.
    
    Reference: Ops Manual v6.8 Section 1.2 - 27-State Order Machine
    """
    return [
        {"from": "S01", "to": "S02", "trigger": "payment_received"},
        {"from": "S02", "to": "S03", "trigger": "scan_received"},
        {"from": "S03", "to": "S04", "trigger": "processing_started"},
        {"from": "S04", "to": "S05", "trigger": "pattern_ready"},
        {"from": "S05", "to": "S06", "trigger": "submitted_to_cutter"},
        {"from": "S06", "to": "S07", "trigger": "pattern_cut"},
        {"from": "S07", "to": "S08", "trigger": "available_for_tailors"},
        {"from": "S08", "to": "S09", "trigger": "claimed_by_tailor"},
        {"from": "S09", "to": "S10", "trigger": "courier_booked"},
        {"from": "S10", "to": "S11", "trigger": "dispatched"},
        {"from": "S11", "to": "S12", "trigger": "received_by_tailor"},
        {"from": "S12", "to": "S13", "trigger": "production_started"},
        {"from": "S13", "to": "S14", "trigger": "production_complete"},
    ]


@pytest.fixture
def valid_order_request(valid_p0_measurements) -> Dict:
    """Valid order creation request."""
    return {
        "order_id": f"SDS-{datetime.now().strftime('%Y%m%d')}-0001-A",
        "customer_id": "cust_test_12345",
        "garment_type": "jacket",
        "fit_type": "regular",
        "measurements": valid_p0_measurements,
        "priority": "normal",
    }


@pytest.fixture
def valid_session_data() -> Dict:
    """Valid EYESON session data."""
    return {
        "session_id": str(uuid.uuid4()),
        "customer_id": "cust_test_12345",
        "garment_type": "jacket",
        "status": "COMPLETED",
        "created_at": datetime.utcnow().isoformat(),
        "completed_at": datetime.utcnow().isoformat(),
    }


# =============================================================================
# API CLIENT FIXTURES
# =============================================================================

@pytest_asyncio.fixture
async def pattern_factory_client() -> AsyncGenerator[AsyncClient, None]:
    """
    Async HTTP client for Pattern Factory API testing.
    
    Reference: Ops Manual v6.8 Section 2.8 - Pattern Factory SOPs
    """
    # TODO: Import actual FastAPI app
    # from pattern_factory.src.api.web_api import app
    # async with AsyncClient(app=app, base_url="http://test") as client:
    #     yield client
    
    async with AsyncClient(base_url="http://localhost:8000") as client:
        yield client


@pytest_asyncio.fixture
async def eyeson_client() -> AsyncGenerator[AsyncClient, None]:
    """
    Async HTTP client for EYESON Backend API testing.
    """
    async with AsyncClient(base_url="http://localhost:8001") as client:
        yield client


# =============================================================================
# PERFORMANCE BASELINE FIXTURES
# =============================================================================

@pytest.fixture
def performance_baselines() -> Dict:
    """
    Performance baseline metrics.
    
    Reference: Ops Manual v6.8 Section 2.6 - Scalability Layer
    """
    return {
        "api_response_time_ms": {
            "p50": 50,
            "p95": 100,
            "p99": 200,
        },
        "pattern_generation_time_seconds": {
            "target": 180,  # 3 minutes
            "max": 300,     # 5 minutes
        },
        "file_download_time_seconds": {
            "target": 3,
            "max": 5,
        },
        "concurrent_users": {
            "normal": 10,
            "peak": 50,
            "stress": 100,
        },
        "throughput": {
            "orders_per_hour": 100,
            "patterns_per_hour": 60,
        },
    }


# =============================================================================
# MOCK FIXTURES
# =============================================================================

@pytest.fixture
def mock_cutter_socket(mocker):
    """Mock TCP socket for Jindex cutter testing."""
    mock_socket = mocker.patch("socket.socket")
    mock_instance = mock_socket.return_value
    mock_instance.connect.return_value = None
    mock_instance.send.return_value = 100
    mock_instance.recv.return_value = b"OK\r\n"
    mock_instance.close.return_value = None
    return mock_instance


@pytest.fixture
def mock_stripe_api(mocker):
    """Mock Stripe API for payment testing."""
    return mocker.patch("stripe.Transfer.create")


@pytest.fixture
def mock_kokoro_tts(mocker):
    """Mock Kokoro TTS service."""
    return mocker.patch("eyeson.backend.src.services.tts_service.KokoroTTS.synthesize")


# =============================================================================
# PYTEST CONFIGURATION
# =============================================================================

def pytest_configure(config):
    """Configure custom pytest markers."""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "e2e: End-to-end tests")
    config.addinivalue_line("markers", "performance: Performance tests")
    config.addinivalue_line("markers", "slow: Slow tests")
    config.addinivalue_line("markers", "state_machine: 27-State Order Machine tests")
    config.addinivalue_line("markers", "security: Security and auth tests")
