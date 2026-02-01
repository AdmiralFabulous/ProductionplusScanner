#!/usr/bin/env python3
"""
Audit Logging Module

Provides structured audit logging for security-relevant events.
Logs to both file and optionally to database for compliance.

Event types:
- AUTH: Authentication events (login, logout, token refresh)
- ACCESS: Resource access events
- MODIFY: Data modification events
- ADMIN: Administrative actions
- SECURITY: Security-related events (failed logins, permission denied)

Usage:
    from security.audit import log_access, log_auth_event

    # Log authentication
    log_auth_event("user123", AuditEventType.LOGIN_SUCCESS, "192.168.1.1")

    # Log resource access
    log_access(user, "orders:read", "order-123", "success")

Author: Claude
Date: 2026-01-31
"""

import json
import logging
import os
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict
import threading


class AuditEventType(str, Enum):
    """Types of audit events."""

    # Authentication
    LOGIN_SUCCESS = "auth.login.success"
    LOGIN_FAILURE = "auth.login.failure"
    LOGOUT = "auth.logout"
    TOKEN_REFRESH = "auth.token.refresh"
    TOKEN_INVALID = "auth.token.invalid"

    # Access
    ACCESS_GRANTED = "access.granted"
    ACCESS_DENIED = "access.denied"
    RESOURCE_READ = "resource.read"
    RESOURCE_DOWNLOAD = "resource.download"

    # Modifications
    ORDER_CREATED = "order.created"
    ORDER_UPDATED = "order.updated"
    ORDER_DELETED = "order.deleted"
    USER_CREATED = "user.created"
    USER_UPDATED = "user.updated"
    USER_DELETED = "user.deleted"

    # Queue
    JOB_QUEUED = "queue.job.queued"
    JOB_STARTED = "queue.job.started"
    JOB_COMPLETED = "queue.job.completed"
    JOB_FAILED = "queue.job.failed"

    # Admin
    CONFIG_CHANGED = "admin.config.changed"
    SYSTEM_MAINTENANCE = "admin.system.maintenance"

    # Security
    PERMISSION_DENIED = "security.permission.denied"
    SUSPICIOUS_ACTIVITY = "security.suspicious"
    RATE_LIMITED = "security.rate.limited"


@dataclass
class AuditEvent:
    """Structured audit event."""

    timestamp: str
    event_type: str
    username: Optional[str]
    user_id: Optional[str]
    user_role: Optional[str]
    ip_address: Optional[str]
    user_agent: Optional[str]
    resource: Optional[str]
    action: Optional[str]
    outcome: str  # success, failure, error
    details: Dict[str, Any]
    request_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict())


class AuditLogger:
    """
    Centralized audit logging service.

    Logs to:
    1. Structured JSON file (always)
    2. Supabase audit_logs table (optional)
    3. Standard logging (for integration with log aggregators)
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        """Singleton pattern for global audit logger."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize audit logger."""
        if self._initialized:
            return

        self._initialized = True
        self._log_file = None
        self._db_client = None
        self._use_database = False

        self._setup_logging()

    def _setup_logging(self):
        """Set up logging handlers."""
        try:
            from .config import get_config

            config = get_config()

            # Ensure log directory exists
            log_path = Path(config.audit_log_path)
            log_path.parent.mkdir(parents=True, exist_ok=True)

            # Set up file handler for audit log
            self._log_file = log_path

            # Set up database logging if enabled
            if config.audit_to_database:
                try:
                    from supabase import create_client

                    if config.supabase_url and config.supabase_key:
                        self._db_client = create_client(
                            config.supabase_url, config.supabase_key
                        )
                        self._use_database = True
                except Exception as e:
                    print(f"Warning: Could not set up audit database logging: {e}")

            # Standard Python logger for integration
            self._logger = logging.getLogger("audit")
            self._logger.setLevel(logging.INFO)

            # Add file handler if not already added
            if not self._logger.handlers:
                handler = logging.FileHandler(self._log_file)
                handler.setFormatter(logging.Formatter("%(message)s"))
                self._logger.addHandler(handler)

        except Exception as e:
            print(f"Warning: Audit logging setup error: {e}")
            self._logger = logging.getLogger("audit")

    def log(self, event: AuditEvent):
        """
        Log an audit event.

        Args:
            event: AuditEvent to log
        """
        # Write to JSON file
        try:
            self._logger.info(event.to_json())
        except Exception as e:
            print(f"Audit log file error: {e}")

        # Write to database if enabled
        if self._use_database and self._db_client:
            try:
                self._db_client.table("audit_logs").insert(event.to_dict()).execute()
            except Exception as e:
                # Don't fail on database errors
                print(f"Audit database error: {e}")

    def log_auth(
        self,
        event_type: AuditEventType,
        username: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        success: bool = True,
        details: Optional[Dict[str, Any]] = None,
    ):
        """
        Log an authentication event.

        Args:
            event_type: Type of auth event
            username: Username attempting auth
            ip_address: Client IP address
            user_agent: Client user agent
            success: Whether auth succeeded
            details: Additional details
        """
        event = AuditEvent(
            timestamp=datetime.utcnow().isoformat(),
            event_type=event_type.value,
            username=username,
            user_id=None,
            user_role=None,
            ip_address=ip_address,
            user_agent=user_agent,
            resource="auth",
            action=event_type.value.split(".")[-1],
            outcome="success" if success else "failure",
            details=details or {},
        )
        self.log(event)

    def log_access(
        self,
        user: Dict[str, Any],
        resource: str,
        action: str,
        outcome: str,
        ip_address: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """
        Log a resource access event.

        Args:
            user: User dict with username, user_id, role
            resource: Resource being accessed
            action: Action performed
            outcome: Result (success, denied, error)
            ip_address: Client IP
            details: Additional context
        """
        event = AuditEvent(
            timestamp=datetime.utcnow().isoformat(),
            event_type=AuditEventType.ACCESS_GRANTED.value
            if outcome == "success"
            else AuditEventType.ACCESS_DENIED.value,
            username=user.get("username") or user.get("sub"),
            user_id=user.get("user_id"),
            user_role=user.get("role"),
            ip_address=ip_address,
            user_agent=None,
            resource=resource,
            action=action,
            outcome=outcome,
            details=details or {},
        )
        self.log(event)

    def log_modification(
        self,
        user: Dict[str, Any],
        event_type: AuditEventType,
        resource_type: str,
        resource_id: str,
        changes: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
    ):
        """
        Log a data modification event.

        Args:
            user: User performing modification
            event_type: Type of modification
            resource_type: Type of resource (order, user, etc.)
            resource_id: ID of modified resource
            changes: What was changed
            ip_address: Client IP
        """
        event = AuditEvent(
            timestamp=datetime.utcnow().isoformat(),
            event_type=event_type.value,
            username=user.get("username") or user.get("sub"),
            user_id=user.get("user_id"),
            user_role=user.get("role"),
            ip_address=ip_address,
            user_agent=None,
            resource=f"{resource_type}:{resource_id}",
            action=event_type.value.split(".")[-1],
            outcome="success",
            details={"changes": changes} if changes else {},
        )
        self.log(event)

    def log_security(
        self,
        event_type: AuditEventType,
        description: str,
        ip_address: Optional[str] = None,
        username: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """
        Log a security event.

        Args:
            event_type: Type of security event
            description: Human-readable description
            ip_address: Source IP
            username: Associated username if known
            details: Additional context
        """
        event = AuditEvent(
            timestamp=datetime.utcnow().isoformat(),
            event_type=event_type.value,
            username=username,
            user_id=None,
            user_role=None,
            ip_address=ip_address,
            user_agent=None,
            resource="security",
            action=event_type.value.split(".")[-1],
            outcome="alert",
            details={"description": description, **(details or {})},
        )
        self.log(event)

    def get_recent_events(
        self,
        limit: int = 100,
        event_type: Optional[str] = None,
        username: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get recent audit events from database.

        Args:
            limit: Max events to return
            event_type: Filter by event type
            username: Filter by username

        Returns:
            List of audit events
        """
        if not self._use_database or not self._db_client:
            return []

        try:
            query = self._db_client.table("audit_logs").select("*")

            if event_type:
                query = query.eq("event_type", event_type)
            if username:
                query = query.eq("username", username)

            query = query.order("timestamp", desc=True).limit(limit)
            result = query.execute()

            return result.data if result.data else []
        except Exception:
            return []


# Global audit logger instance
_audit_logger: Optional[AuditLogger] = None


def get_audit_logger() -> AuditLogger:
    """Get the global audit logger instance."""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger


# Convenience functions
def log_access(
    user: Dict[str, Any],
    resource: str,
    action: str,
    outcome: str,
    ip_address: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
):
    """Log a resource access event."""
    logger = get_audit_logger()
    logger.log_access(user, resource, action, outcome, ip_address, details)


def log_auth_event(
    username: str,
    event_type: AuditEventType,
    ip_address: Optional[str] = None,
    success: bool = True,
    details: Optional[Dict[str, Any]] = None,
):
    """Log an authentication event."""
    logger = get_audit_logger()
    logger.log_auth(event_type, username, ip_address, success=success, details=details)


def log_modification(
    user: Dict[str, Any],
    event_type: AuditEventType,
    resource_type: str,
    resource_id: str,
    changes: Optional[Dict[str, Any]] = None,
):
    """Log a modification event."""
    logger = get_audit_logger()
    logger.log_modification(user, event_type, resource_type, resource_id, changes)


def log_security_event(
    event_type: AuditEventType,
    description: str,
    ip_address: Optional[str] = None,
    username: Optional[str] = None,
):
    """Log a security event."""
    logger = get_audit_logger()
    logger.log_security(event_type, description, ip_address, username)


# Testing
def _test_audit():
    """Test audit logging."""
    import os
    import tempfile

    os.environ["JWT_SECRET"] = "test-jwt-secret-at-least-32-characters-long"
    os.environ["ENCRYPTION_KEY"] = "test-encryption-key-at-least-32-chars"
    os.environ["AUDIT_LOG_PATH"] = os.path.join(tempfile.gettempdir(), "test_audit.log")
    os.environ["AUDIT_TO_DATABASE"] = "false"

    from .config import reset_config

    reset_config()

    global _audit_logger
    _audit_logger = None

    logger = get_audit_logger()

    # Test auth logging
    logger.log_auth(
        AuditEventType.LOGIN_SUCCESS, "testuser", "192.168.1.1", success=True
    )

    # Test access logging
    user = {"username": "testuser", "user_id": "123", "role": "operator"}
    logger.log_access(user, "orders", "read", "success", "192.168.1.1")

    # Test modification logging
    logger.log_modification(
        user, AuditEventType.ORDER_CREATED, "order", "ORD-001", {"garment_type": "tee"}
    )

    # Test security logging
    logger.log_security(
        AuditEventType.PERMISSION_DENIED,
        "User attempted to access admin function",
        "192.168.1.1",
        "testuser",
    )

    # Verify log file was created
    log_path = os.environ["AUDIT_LOG_PATH"]
    assert os.path.exists(log_path), f"Audit log not created at {log_path}"

    with open(log_path) as f:
        lines = f.readlines()
        assert len(lines) >= 4, "Expected at least 4 log entries"

    print("All audit tests passed!")

    # Cleanup
    os.remove(log_path)
    reset_config()


if __name__ == "__main__":
    _test_audit()
