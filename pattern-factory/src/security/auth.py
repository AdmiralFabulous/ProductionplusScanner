#!/usr/bin/env python3
"""
JWT Authentication Module

Provides JWT token creation, verification, and user authentication.
Integrates with FastAPI's dependency injection system.

Usage:
    from security.auth import get_current_user, create_access_token

    # In FastAPI endpoint
    @app.get("/protected")
    async def protected_route(user: dict = Depends(get_current_user)):
        return {"user": user["username"]}

Author: Claude
Date: 2026-01-31
"""

import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
import hashlib

# Try to use passlib with bcrypt, fall back to hashlib if not available
try:
    from passlib.context import CryptContext

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    USE_BCRYPT = True
except Exception:
    pwd_context = None
    USE_BCRYPT = False

# OAuth2 scheme for token extraction
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


class Token(BaseModel):
    """JWT Token response model."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: Dict[str, Any]


class TokenData(BaseModel):
    """Data extracted from JWT token."""

    username: Optional[str] = None
    user_id: Optional[str] = None
    role: Optional[str] = None
    exp: Optional[datetime] = None


class OAuth2PasswordRequestFormStrict(OAuth2PasswordRequestForm):
    """Strict password form that validates required fields."""

    pass


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt or SHA-256 fallback.

    Args:
        password: Plain text password

    Returns:
        Hashed password string
    """
    if USE_BCRYPT and pwd_context:
        try:
            return pwd_context.hash(password)
        except Exception:
            pass

    # Fallback to SHA-256 with salt
    import secrets

    salt = secrets.token_hex(16)
    hash_val = hashlib.sha256((salt + password).encode()).hexdigest()
    return f"sha256${salt}${hash_val}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.

    Args:
        plain_password: Plain text password to verify
        hashed_password: Stored hash to compare against

    Returns:
        True if password matches
    """
    # Check if it's a bcrypt hash
    if hashed_password.startswith("$2"):
        if USE_BCRYPT and pwd_context:
            try:
                return pwd_context.verify(plain_password, hashed_password)
            except Exception:
                return False
        return False

    # Check if it's our SHA-256 format
    if hashed_password.startswith("sha256$"):
        parts = hashed_password.split("$")
        if len(parts) == 3:
            salt = parts[1]
            stored_hash = parts[2]
            computed_hash = hashlib.sha256((salt + plain_password).encode()).hexdigest()
            return computed_hash == stored_hash

    return False


def create_access_token(
    data: Dict[str, Any], expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT access token.

    Args:
        data: Payload data to encode in token
        expires_delta: Optional custom expiration time

    Returns:
        Encoded JWT token string
    """
    from .config import get_config

    config = get_config()

    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=config.jwt_expiration_hours)

    to_encode.update({"exp": expire, "iat": datetime.utcnow(), "type": "access"})

    encoded_jwt = jwt.encode(
        to_encode, config.jwt_secret, algorithm=config.jwt_algorithm
    )

    return encoded_jwt


def create_refresh_token(data: Dict[str, Any]) -> str:
    """
    Create a JWT refresh token with longer expiration.

    Args:
        data: Payload data to encode

    Returns:
        Encoded refresh token
    """
    from .config import get_config

    config = get_config()

    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=config.jwt_refresh_expiration_days)

    to_encode.update({"exp": expire, "iat": datetime.utcnow(), "type": "refresh"})

    return jwt.encode(to_encode, config.jwt_secret, algorithm=config.jwt_algorithm)


def verify_token(token: str) -> Dict[str, Any]:
    """
    Verify and decode a JWT token.

    Args:
        token: JWT token string

    Returns:
        Decoded token payload

    Raises:
        HTTPException: If token is invalid or expired
    """
    from .config import get_config

    config = get_config()

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            token, config.jwt_secret, algorithms=[config.jwt_algorithm]
        )

        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception

        return payload

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
) -> Dict[str, Any]:
    """
    FastAPI dependency to get the current authenticated user.

    Args:
        token: JWT token from Authorization header

    Returns:
        User data from token payload

    Raises:
        HTTPException: If not authenticated
    """
    from .config import get_config

    config = get_config()

    # Check if auth is disabled (development mode)
    if not config.auth_enabled:
        return {
            "sub": "dev-user",
            "username": "dev-user",
            "user_id": "dev-user-id",
            "role": "admin",
            "auth_disabled": True,
        }

    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = verify_token(token)

    # Optionally verify user still exists in database
    # This adds latency but ensures revoked users can't access
    # from .users import UserService
    # user_service = UserService()
    # if not user_service.user_exists(payload.get("user_id")):
    #     raise HTTPException(status_code=401, detail="User no longer exists")

    return payload


async def get_current_user_optional(
    token: Optional[str] = Depends(oauth2_scheme),
) -> Optional[Dict[str, Any]]:
    """
    FastAPI dependency for optional authentication.

    Returns None if no valid token provided, instead of raising exception.
    Useful for endpoints that work differently for authenticated users.

    Args:
        token: JWT token from Authorization header

    Returns:
        User data or None
    """
    from .config import get_config

    config = get_config()

    if not config.auth_enabled:
        return {
            "sub": "dev-user",
            "username": "dev-user",
            "role": "admin",
            "auth_disabled": True,
        }

    if token is None:
        return None

    try:
        return verify_token(token)
    except HTTPException:
        return None


def get_token_from_request(request: Request) -> Optional[str]:
    """
    Extract JWT token from request headers or cookies.

    Args:
        request: FastAPI Request object

    Returns:
        Token string or None
    """
    # Try Authorization header first
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header[7:]

    # Try cookie
    token = request.cookies.get("access_token")
    if token:
        return token

    # Try query parameter (for WebSocket)
    token = request.query_params.get("token")
    if token:
        return token

    return None


async def authenticate_user(username: str, password: str) -> Optional[Dict[str, Any]]:
    """
    Authenticate a user with username and password.

    Args:
        username: User's username
        password: Plain text password

    Returns:
        User data if authentication successful, None otherwise
    """
    from .users import UserService

    user_service = UserService()
    user = await user_service.get_by_username(username)

    if not user:
        return None

    if not verify_password(password, user.password_hash):
        return None

    if not user.is_active:
        return None

    return {
        "user_id": str(user.id),
        "username": user.username,
        "email": user.email,
        "role": user.role,
    }


def verify_api_key(api_key: str) -> bool:
    """
    Verify an API key for service-to-service authentication.

    Args:
        api_key: API key to verify

    Returns:
        True if valid
    """
    from .config import get_config

    config = get_config()

    if not config.api_key:
        return False

    return api_key == config.api_key


async def get_current_user_or_api_key(
    token: Optional[str] = Depends(oauth2_scheme), x_api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Allow authentication via either JWT or API key.

    Args:
        token: JWT token
        x_api_key: API key from X-API-Key header

    Returns:
        User data or service identity
    """
    from .config import get_config

    config = get_config()

    if not config.auth_enabled:
        return {"sub": "dev-user", "role": "admin", "auth_disabled": True}

    # Try JWT first
    if token:
        try:
            return verify_token(token)
        except HTTPException:
            pass

    # Try API key
    if x_api_key and verify_api_key(x_api_key):
        return {
            "sub": "api-service",
            "username": "api-service",
            "role": "service",
            "auth_type": "api_key",
        }

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )


# Testing function
def _test_auth():
    """Test authentication functions."""
    import os

    # Set up test environment
    os.environ["JWT_SECRET"] = "test-jwt-secret-at-least-32-characters-long"
    os.environ["ENCRYPTION_KEY"] = "test-encryption-key-at-least-32-chars"

    from .config import reset_config

    reset_config()

    # Test password hashing
    password = "testpassword123"
    hashed = hash_password(password)
    assert verify_password(password, hashed), "Password verification failed"
    assert not verify_password("wrongpassword", hashed), "Wrong password accepted"

    # Test token creation and verification
    token_data = {"sub": "testuser", "user_id": "123", "role": "operator"}
    token = create_access_token(token_data)

    payload = verify_token(token)
    assert payload["sub"] == "testuser"
    assert payload["user_id"] == "123"
    assert payload["role"] == "operator"

    print("All auth tests passed!")

    reset_config()


if __name__ == "__main__":
    _test_auth()
