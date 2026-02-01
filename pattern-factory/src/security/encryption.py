#!/usr/bin/env python3
"""
Data Encryption Module

Provides AES-256 encryption for sensitive data like customer measurements.
Uses Fernet symmetric encryption (AES-128-CBC with HMAC-SHA256).

Usage:
    from security.encryption import encrypt_measurements, decrypt_measurements

    # Encrypt before storing
    encrypted = encrypt_measurements({"chest_cm": 102, "waist_cm": 88})

    # Decrypt when reading
    measurements = decrypt_measurements(encrypted)

Author: Claude
Date: 2026-01-31
"""

import os
import base64
import json
import hashlib
from typing import Dict, Any, Optional, Union
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# Sensitive fields that should be encrypted
SENSITIVE_FIELDS = [
    "chest_cm",
    "waist_cm",
    "hip_cm",
    "shoulder_width_cm",
    "arm_length_cm",
    "inseam_cm",
    "neck_cm",
    "thigh_cm",
    "height_cm",
    "weight_kg",
    "customer_email",
    "customer_phone",
    "customer_address",
]


class EncryptionError(Exception):
    """Raised when encryption/decryption fails."""

    pass


def _get_encryption_key() -> bytes:
    """
    Get the encryption key from environment or config.

    Returns:
        32-byte key suitable for Fernet
    """
    from .config import get_config

    config = get_config()
    key_str = config.encryption_key

    # Derive a proper Fernet key from the config key
    # Using PBKDF2 to ensure consistent key derivation
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b"samedaysuits-encryption-salt",  # Static salt for deterministic key
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(key_str.encode()))
    return key


def _get_cipher() -> Fernet:
    """Get the Fernet cipher instance."""
    return Fernet(_get_encryption_key())


def generate_encryption_key() -> str:
    """
    Generate a new encryption key.

    Returns:
        Base64-encoded 32-byte key
    """
    return Fernet.generate_key().decode()


def encrypt_data(data: str) -> str:
    """
    Encrypt a string value.

    Args:
        data: Plain text string to encrypt

    Returns:
        Base64-encoded encrypted string
    """
    try:
        cipher = _get_cipher()
        encrypted = cipher.encrypt(data.encode())
        return encrypted.decode()
    except Exception as e:
        raise EncryptionError(f"Encryption failed: {str(e)}")


def decrypt_data(encrypted: str) -> str:
    """
    Decrypt an encrypted string.

    Args:
        encrypted: Base64-encoded encrypted string

    Returns:
        Decrypted plain text string
    """
    try:
        cipher = _get_cipher()
        decrypted = cipher.decrypt(encrypted.encode())
        return decrypted.decode()
    except InvalidToken:
        raise EncryptionError("Decryption failed: Invalid token or wrong key")
    except Exception as e:
        raise EncryptionError(f"Decryption failed: {str(e)}")


def encrypt_value(value: Any) -> str:
    """
    Encrypt any JSON-serializable value.

    Args:
        value: Any JSON-serializable value

    Returns:
        Encrypted string
    """
    json_str = json.dumps(value)
    return encrypt_data(json_str)


def decrypt_value(encrypted: str) -> Any:
    """
    Decrypt to original JSON value.

    Args:
        encrypted: Encrypted string

    Returns:
        Original value
    """
    json_str = decrypt_data(encrypted)
    return json.loads(json_str)


def encrypt_measurements(
    measurements: Dict[str, Any], encrypt_all: bool = False
) -> Dict[str, Any]:
    """
    Encrypt sensitive measurement fields.

    Args:
        measurements: Dict containing measurement data
        encrypt_all: If True, encrypt all fields. If False, only sensitive fields.

    Returns:
        Dict with encrypted values and metadata
    """
    from .config import get_config

    config = get_config()
    if not config.encryption_enabled:
        return measurements

    encrypted = {}
    encrypted_fields = []

    for key, value in measurements.items():
        if encrypt_all or key in SENSITIVE_FIELDS:
            if value is not None:
                encrypted[key] = encrypt_value(value)
                encrypted_fields.append(key)
            else:
                encrypted[key] = None
        else:
            encrypted[key] = value

    # Add metadata about encryption
    encrypted["_encrypted"] = True
    encrypted["_encrypted_fields"] = encrypted_fields

    return encrypted


def decrypt_measurements(encrypted_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Decrypt measurement fields.

    Args:
        encrypted_data: Dict with encrypted values

    Returns:
        Dict with decrypted values
    """
    from .config import get_config

    config = get_config()

    # Check if data is encrypted
    if not encrypted_data.get("_encrypted", False):
        return encrypted_data

    if not config.encryption_enabled:
        # Remove metadata and return as-is
        result = {k: v for k, v in encrypted_data.items() if not k.startswith("_")}
        return result

    encrypted_fields = encrypted_data.get("_encrypted_fields", [])
    decrypted = {}

    for key, value in encrypted_data.items():
        # Skip metadata fields
        if key.startswith("_"):
            continue

        if key in encrypted_fields and value is not None:
            try:
                decrypted[key] = decrypt_value(value)
            except EncryptionError:
                # If decryption fails, include original value with warning
                decrypted[key] = value
                decrypted[f"_{key}_decrypt_error"] = True
        else:
            decrypted[key] = value

    return decrypted


def encrypt_field(value: Any, field_name: str = "") -> Optional[str]:
    """
    Encrypt a single field value.

    Args:
        value: Value to encrypt
        field_name: Optional field name for context

    Returns:
        Encrypted string or None if value is None
    """
    if value is None:
        return None
    return encrypt_value(value)


def decrypt_field(encrypted: Optional[str], field_name: str = "") -> Any:
    """
    Decrypt a single field value.

    Args:
        encrypted: Encrypted string
        field_name: Optional field name for context

    Returns:
        Decrypted value or None
    """
    if encrypted is None:
        return None
    return decrypt_value(encrypted)


def hash_data(data: str) -> str:
    """
    Create a one-way hash of data (for comparison without decryption).

    Args:
        data: String to hash

    Returns:
        SHA-256 hash as hex string
    """
    return hashlib.sha256(data.encode()).hexdigest()


def is_encrypted(data: Dict[str, Any]) -> bool:
    """
    Check if a dict contains encrypted data.

    Args:
        data: Dict to check

    Returns:
        True if data appears to be encrypted
    """
    return data.get("_encrypted", False) is True


# Testing function
def _test_encryption():
    """Test encryption/decryption round-trip."""
    # Set up test environment
    os.environ["ENCRYPTION_KEY"] = "test-key-at-least-32-characters-long"
    os.environ["JWT_SECRET"] = "test-jwt-secret-at-least-32-chars"

    from .config import reset_config

    reset_config()

    # Test string encryption
    original = "sensitive data"
    encrypted = encrypt_data(original)
    decrypted = decrypt_data(encrypted)
    assert decrypted == original, "String encryption failed"

    # Test value encryption
    value = {"chest_cm": 102.5, "waist_cm": 88}
    encrypted_val = encrypt_value(value)
    decrypted_val = decrypt_value(encrypted_val)
    assert decrypted_val == value, "Value encryption failed"

    # Test measurements encryption
    measurements = {
        "chest_cm": 102,
        "waist_cm": 88,
        "hip_cm": 100,
        "source": "scanner",  # Non-sensitive
    }
    encrypted_meas = encrypt_measurements(measurements)
    assert encrypted_meas["_encrypted"] is True
    assert "chest_cm" in encrypted_meas["_encrypted_fields"]
    assert encrypted_meas["source"] == "scanner"  # Not encrypted

    decrypted_meas = decrypt_measurements(encrypted_meas)
    assert decrypted_meas["chest_cm"] == 102
    assert decrypted_meas["source"] == "scanner"

    print("All encryption tests passed!")

    # Clean up
    reset_config()


if __name__ == "__main__":
    _test_encryption()
