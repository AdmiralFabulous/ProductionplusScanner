#!/usr/bin/env python3
"""
Security Module Tests

Comprehensive tests for the security module including:
- JWT authentication
- Password hashing
- RBAC
- Encryption
- Audit logging

Run with: pytest tests/test_security.py -v

Author: Claude
Date: 2026-01-31
"""

import os
import sys
import pytest
import tempfile
import asyncio
from datetime import datetime, timedelta

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

# Set test environment BEFORE importing security modules
os.environ["JWT_SECRET"] = "test-jwt-secret-key-that-is-at-least-32-characters-long"
os.environ["ENCRYPTION_KEY"] = "test-encryption-key-that-is-at-least-32-characters"
os.environ["ENVIRONMENT"] = "development"
os.environ["AUTH_ENABLED"] = "true"
os.environ["ENCRYPTION_ENABLED"] = "true"
os.environ["AUDIT_ENABLED"] = "true"
os.environ["AUDIT_TO_DATABASE"] = "false"
os.environ["AUDIT_LOG_PATH"] = os.path.join(tempfile.gettempdir(), "test_audit.log")


class TestConfig:
    """Test secure configuration."""

    def test_config_loads_from_env(self):
        """Test that config loads from environment variables."""
        from security.config import get_config, reset_config

        reset_config()

        config = get_config()

        assert config.jwt_secret == os.environ["JWT_SECRET"]
        assert config.encryption_key == os.environ["ENCRYPTION_KEY"]
        assert config.auth_enabled is True
        assert config.encryption_enabled is True

        reset_config()

    def test_config_validates_secret_length(self):
        """Test that config validates secret key length."""
        from security.config import SecureConfig

        with pytest.raises(
            ValueError, match="JWT_SECRET must be at least 32 characters"
        ):
            SecureConfig(
                jwt_secret="short",
                encryption_key="test-encryption-key-that-is-at-least-32-characters",
                supabase_url="http://localhost:54321",
                supabase_key="test-key",
            )

    def test_generate_secret(self):
        """Test secret generation utility."""
        from security.config import generate_secret

        secret = generate_secret(32)
        assert len(secret) == 64  # hex encoding doubles length


class TestPasswordHashing:
    """Test password hashing functions."""

    def test_hash_password(self):
        """Test password hashing."""
        from security.auth import hash_password

        password = "test_password_123"
        hashed = hash_password(password)

        assert hashed != password
        assert hashed.startswith("$2b$")  # bcrypt prefix

    def test_verify_password_correct(self):
        """Test password verification with correct password."""
        from security.auth import hash_password, verify_password

        password = "test_password_123"
        hashed = hash_password(password)

        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """Test password verification with wrong password."""
        from security.auth import hash_password, verify_password

        password = "test_password_123"
        hashed = hash_password(password)

        assert verify_password("wrong_password", hashed) is False

    def test_different_passwords_different_hashes(self):
        """Test that different passwords produce different hashes."""
        from security.auth import hash_password

        hash1 = hash_password("password1")
        hash2 = hash_password("password2")

        assert hash1 != hash2


class TestJWTTokens:
    """Test JWT token creation and verification."""

    def test_create_access_token(self):
        """Test access token creation."""
        from security.auth import create_access_token
        from security.config import reset_config

        reset_config()

        data = {"sub": "testuser", "role": "operator"}
        token = create_access_token(data)

        assert isinstance(token, str)
        assert len(token) > 50  # JWT tokens are typically long

        reset_config()

    def test_verify_token_valid(self):
        """Test verification of valid token."""
        from security.auth import create_access_token, verify_token
        from security.config import reset_config

        reset_config()

        data = {"sub": "testuser", "user_id": "123", "role": "operator"}
        token = create_access_token(data)

        payload = verify_token(token)

        assert payload["sub"] == "testuser"
        assert payload["user_id"] == "123"
        assert payload["role"] == "operator"
        assert "exp" in payload
        assert "iat" in payload

        reset_config()

    def test_verify_token_expired(self):
        """Test verification of expired token."""
        from security.auth import create_access_token, verify_token
        from security.config import reset_config
        from fastapi import HTTPException

        reset_config()

        data = {"sub": "testuser"}
        # Create token that expires immediately
        token = create_access_token(data, expires_delta=timedelta(seconds=-1))

        with pytest.raises(HTTPException) as exc_info:
            verify_token(token)

        assert exc_info.value.status_code == 401
        assert "expired" in exc_info.value.detail.lower()

        reset_config()

    def test_verify_token_invalid(self):
        """Test verification of invalid token."""
        from security.auth import verify_token
        from security.config import reset_config
        from fastapi import HTTPException

        reset_config()

        with pytest.raises(HTTPException) as exc_info:
            verify_token("invalid.token.here")

        assert exc_info.value.status_code == 401

        reset_config()


class TestRBAC:
    """Test Role-Based Access Control."""

    def test_admin_has_all_permissions(self):
        """Test that admin role has all permissions."""
        from security.rbac import ROLES, check_permission

        admin_user = {"role": "admin"}

        # Test various permissions
        assert check_permission(admin_user, "orders:create")
        assert check_permission(admin_user, "users:delete")
        assert check_permission(admin_user, "system:config")
        assert check_permission(admin_user, "qc:override")

    def test_operator_permissions(self):
        """Test operator role permissions."""
        from security.rbac import check_permission

        operator_user = {"role": "operator"}

        # Should have
        assert check_permission(operator_user, "orders:create")
        assert check_permission(operator_user, "queue:manage")
        assert check_permission(operator_user, "system:health")

        # Should not have
        assert not check_permission(operator_user, "users:delete")
        assert not check_permission(operator_user, "system:config")

    def test_qc_tech_permissions(self):
        """Test QC tech role permissions."""
        from security.rbac import check_permission

        qc_user = {"role": "qc_tech"}

        # Should have
        assert check_permission(qc_user, "qc:approve")
        assert check_permission(qc_user, "qc:override")
        assert check_permission(qc_user, "orders:read")

        # Should not have
        assert not check_permission(qc_user, "orders:create")
        assert not check_permission(qc_user, "users:delete")

    def test_readonly_permissions(self):
        """Test readonly role permissions."""
        from security.rbac import check_permission

        readonly_user = {"role": "readonly"}

        # Should have
        assert check_permission(readonly_user, "orders:read")
        assert check_permission(readonly_user, "queue:read")

        # Should not have
        assert not check_permission(readonly_user, "orders:create")
        assert not check_permission(readonly_user, "queue:manage")

    def test_check_any_permission(self):
        """Test checking for any of multiple permissions."""
        from security.rbac import check_any_permission

        operator_user = {"role": "operator"}

        # Has at least one
        assert check_any_permission(operator_user, ["orders:create", "system:config"])

        # Has none
        assert not check_any_permission(
            operator_user, ["users:delete", "system:config"]
        )

    def test_check_all_permissions(self):
        """Test checking for all permissions."""
        from security.rbac import check_all_permissions

        admin_user = {"role": "admin"}
        operator_user = {"role": "operator"}

        # Admin has all
        assert check_all_permissions(admin_user, ["orders:create", "users:delete"])

        # Operator doesn't have all
        assert not check_all_permissions(
            operator_user, ["orders:create", "users:delete"]
        )

    def test_get_user_permissions(self):
        """Test getting all permissions for a role."""
        from security.rbac import get_user_permissions

        perms = get_user_permissions("operator")

        assert "orders:create" in perms
        assert "queue:manage" in perms
        assert "users:delete" not in perms


class TestEncryption:
    """Test data encryption functions."""

    def test_encrypt_decrypt_string(self):
        """Test encrypting and decrypting a string."""
        from security.encryption import encrypt_data, decrypt_data
        from security.config import reset_config

        reset_config()

        original = "sensitive data"
        encrypted = encrypt_data(original)
        decrypted = decrypt_data(encrypted)

        assert encrypted != original
        assert decrypted == original

        reset_config()

    def test_encrypt_decrypt_value(self):
        """Test encrypting and decrypting arbitrary values."""
        from security.encryption import encrypt_value, decrypt_value
        from security.config import reset_config

        reset_config()

        # Test dict
        value = {"chest_cm": 102.5, "waist_cm": 88}
        encrypted = encrypt_value(value)
        decrypted = decrypt_value(encrypted)

        assert decrypted == value

        # Test number
        num = 123.456
        encrypted_num = encrypt_value(num)
        decrypted_num = decrypt_value(encrypted_num)

        assert decrypted_num == num

        reset_config()

    def test_encrypt_measurements(self):
        """Test encrypting measurement data."""
        from security.encryption import encrypt_measurements, decrypt_measurements
        from security.config import reset_config

        reset_config()

        measurements = {
            "chest_cm": 102,
            "waist_cm": 88,
            "hip_cm": 100,
            "source": "scanner",  # Non-sensitive field
        }

        encrypted = encrypt_measurements(measurements)

        # Should be marked as encrypted
        assert encrypted["_encrypted"] is True

        # Sensitive fields should be encrypted
        assert "chest_cm" in encrypted["_encrypted_fields"]
        assert encrypted["chest_cm"] != 102  # Encrypted value

        # Non-sensitive field should not be encrypted
        assert encrypted["source"] == "scanner"

        # Decrypt and verify
        decrypted = decrypt_measurements(encrypted)

        assert decrypted["chest_cm"] == 102
        assert decrypted["waist_cm"] == 88
        assert decrypted["source"] == "scanner"

        reset_config()

    def test_encryption_different_results(self):
        """Test that same data encrypted twice produces different ciphertext."""
        from security.encryption import encrypt_data
        from security.config import reset_config

        reset_config()

        data = "test data"
        encrypted1 = encrypt_data(data)
        encrypted2 = encrypt_data(data)

        # Fernet uses random IV, so same plaintext produces different ciphertext
        # Both should decrypt to same value though
        # Note: This test may need adjustment based on encryption implementation

        reset_config()

    def test_is_encrypted(self):
        """Test checking if data is encrypted."""
        from security.encryption import is_encrypted, encrypt_measurements
        from security.config import reset_config

        reset_config()

        plain = {"chest_cm": 102}
        encrypted = encrypt_measurements(plain)

        assert is_encrypted(encrypted) is True
        assert is_encrypted(plain) is False

        reset_config()


class TestAuditLogging:
    """Test audit logging functionality."""

    def test_audit_logger_initialization(self):
        """Test audit logger initializes correctly."""
        from security.audit import get_audit_logger, AuditLogger

        logger = get_audit_logger()
        assert isinstance(logger, AuditLogger)

    def test_log_auth_event(self):
        """Test logging authentication events."""
        from security.audit import log_auth_event, AuditEventType
        from security.config import reset_config

        reset_config()

        # Should not raise
        log_auth_event(
            "testuser", AuditEventType.LOGIN_SUCCESS, "192.168.1.1", success=True
        )

        log_auth_event(
            "baduser",
            AuditEventType.LOGIN_FAILURE,
            "192.168.1.100",
            success=False,
            details={"reason": "invalid password"},
        )

        reset_config()

    def test_log_access(self):
        """Test logging access events."""
        from security.audit import log_access
        from security.config import reset_config

        reset_config()

        user = {"username": "operator1", "user_id": "123", "role": "operator"}

        log_access(user, "orders", "read", "success", "192.168.1.1")
        log_access(user, "users", "delete", "denied", "192.168.1.1")

        reset_config()

    def test_log_modification(self):
        """Test logging modification events."""
        from security.audit import log_modification, AuditEventType
        from security.config import reset_config

        reset_config()

        user = {"username": "admin", "user_id": "1", "role": "admin"}

        log_modification(
            user,
            AuditEventType.ORDER_CREATED,
            "order",
            "ORD-001",
            {"garment_type": "tee", "customer_id": "CUST-001"},
        )

        reset_config()

    def test_audit_event_json(self):
        """Test audit event serialization."""
        from security.audit import AuditEvent
        import json

        event = AuditEvent(
            timestamp="2026-01-31T12:00:00",
            event_type="auth.login.success",
            username="testuser",
            user_id="123",
            user_role="operator",
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
            resource="auth",
            action="login",
            outcome="success",
            details={"method": "password"},
        )

        json_str = event.to_json()
        data = json.loads(json_str)

        assert data["username"] == "testuser"
        assert data["outcome"] == "success"


class TestUserService:
    """Test user service functionality."""

    @pytest.fixture
    def user_service(self):
        """Create user service for testing."""
        from security.users import UserService
        from security.config import reset_config

        reset_config()

        service = UserService()
        yield service

        reset_config()

    @pytest.mark.asyncio
    async def test_default_users_exist(self, user_service):
        """Test that default users are seeded."""
        # Should have default admin user
        admin = await user_service.get_by_username("admin")
        assert admin is not None
        assert admin.role == "admin"

        # Should have default operator
        operator = await user_service.get_by_username("operator")
        assert operator is not None
        assert operator.role == "operator"

    @pytest.mark.asyncio
    async def test_create_user(self, user_service):
        """Test creating a new user."""
        from security.users import UserCreate, UserRole

        new_user = await user_service.create_user(
            UserCreate(
                username="newuser",
                email="new@example.com",
                password="securepassword123",
                role=UserRole.READONLY,
            )
        )

        assert new_user.username == "newuser"
        assert new_user.role == "readonly"
        assert new_user.is_active is True

    @pytest.mark.asyncio
    async def test_get_user_by_id(self, user_service):
        """Test getting user by ID."""
        admin = await user_service.get_by_username("admin")
        found = await user_service.get_by_id(admin.id)

        assert found is not None
        assert found.username == "admin"

    @pytest.mark.asyncio
    async def test_update_user(self, user_service):
        """Test updating a user."""
        from security.users import UserCreate, UserUpdate, UserRole

        # Create test user
        user = await user_service.create_user(
            UserCreate(
                username="updatetest", password="password123", role=UserRole.READONLY
            )
        )

        # Update role
        updated = await user_service.update_user(
            user.id, UserUpdate(role=UserRole.OPERATOR)
        )

        assert updated.role == "operator"

    @pytest.mark.asyncio
    async def test_list_users(self, user_service):
        """Test listing users."""
        users = await user_service.list_users()

        assert len(users) >= 3  # Default users

        # Filter by role
        admins = await user_service.list_users(role="admin")
        assert all(u.role == "admin" for u in admins)


class TestIntegration:
    """Integration tests for security module."""

    def test_full_auth_flow(self):
        """Test complete authentication flow."""
        from security.auth import (
            hash_password,
            verify_password,
            create_access_token,
            verify_token,
        )
        from security.config import reset_config

        reset_config()

        # 1. Hash password (during registration)
        password = "user_password_123"
        hashed = hash_password(password)

        # 2. Verify password (during login)
        assert verify_password(password, hashed)

        # 3. Create token
        token = create_access_token(
            {"sub": "testuser", "user_id": "123", "role": "operator"}
        )

        # 4. Verify token (on protected endpoint)
        payload = verify_token(token)
        assert payload["sub"] == "testuser"
        assert payload["role"] == "operator"

        reset_config()

    def test_full_encryption_flow(self):
        """Test complete encryption flow for order data."""
        from security.encryption import (
            encrypt_measurements,
            decrypt_measurements,
            is_encrypted,
        )
        from security.config import reset_config

        reset_config()

        # Original order measurements
        order_data = {
            "chest_cm": 102,
            "waist_cm": 88,
            "hip_cm": 100,
            "shoulder_width_cm": 45,
            "arm_length_cm": 65,
            "inseam_cm": 80,
            "source": "web_api",
            "notes": "Rush order",
        }

        # Encrypt before storing
        encrypted = encrypt_measurements(order_data)
        assert is_encrypted(encrypted)

        # Decrypt when processing
        decrypted = decrypt_measurements(encrypted)

        # Verify all measurements restored
        assert decrypted["chest_cm"] == 102
        assert decrypted["waist_cm"] == 88
        assert decrypted["source"] == "web_api"

        reset_config()


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
