#!/usr/bin/env python3
"""
SameDaySuits Security Module

Provides authentication, authorization, encryption, and audit logging
for the Pattern Factory production system.

Components:
- config: Secure configuration management
- auth: JWT authentication and token management
- users: User management and credential storage
- rbac: Role-based access control
- encryption: Data encryption for sensitive fields
- audit: Structured audit logging

Author: Claude
Date: 2026-01-31
"""

from .config import SecureConfig, get_config
from .auth import (
    create_access_token,
    verify_token,
    get_current_user,
    get_current_user_optional,
    hash_password,
    verify_password,
    OAuth2PasswordRequestFormStrict,
)
from .rbac import (
    ROLES,
    PERMISSIONS,
    require_role,
    require_permission,
    check_permission,
    get_user_permissions,
)
from .encryption import (
    encrypt_data,
    decrypt_data,
    encrypt_measurements,
    decrypt_measurements,
    generate_encryption_key,
)
from .audit import (
    AuditLogger,
    get_audit_logger,
    log_access,
    log_auth_event,
    AuditEventType,
)
from .users import (
    UserService,
    User,
    UserCreate,
    UserUpdate,
    UserRole,
)

__all__ = [
    # Config
    "SecureConfig",
    "get_config",
    # Auth
    "create_access_token",
    "verify_token",
    "get_current_user",
    "get_current_user_optional",
    "hash_password",
    "verify_password",
    "OAuth2PasswordRequestFormStrict",
    # RBAC
    "ROLES",
    "PERMISSIONS",
    "require_role",
    "require_permission",
    "check_permission",
    "get_user_permissions",
    # Encryption
    "encrypt_data",
    "decrypt_data",
    "encrypt_measurements",
    "decrypt_measurements",
    "generate_encryption_key",
    # Audit
    "AuditLogger",
    "get_audit_logger",
    "log_access",
    "log_auth_event",
    "AuditEventType",
    # Users
    "UserService",
    "User",
    "UserCreate",
    "UserUpdate",
    "UserRole",
]

__version__ = "1.0.0"
