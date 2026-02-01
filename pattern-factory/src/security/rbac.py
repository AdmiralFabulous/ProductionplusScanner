#!/usr/bin/env python3
"""
Role-Based Access Control (RBAC) Module

Defines roles, permissions, and provides decorators/dependencies
for enforcing access control in FastAPI endpoints.

Roles (from SOP):
- admin: Full system access
- operator: Order processing, queue management
- qc_tech: Quality control, approvals
- maintenance: System maintenance, health monitoring
- readonly: View-only access

Usage:
    from security.rbac import require_role, require_permission

    @app.post("/orders")
    async def create_order(user: dict = Depends(require_role(["operator", "admin"]))):
        ...

Author: Claude
Date: 2026-01-31
"""

from typing import List, Set, Optional, Dict, Any, Callable
from functools import wraps

from fastapi import Depends, HTTPException, status


# Permission definitions
PERMISSIONS = {
    # Order operations
    "orders:create": "Create new orders",
    "orders:read": "View orders",
    "orders:update": "Update orders",
    "orders:delete": "Delete orders",
    "orders:download": "Download order files",
    # Queue operations
    "queue:read": "View queue status",
    "queue:manage": "Process and manage queue jobs",
    # QC operations
    "qc:review": "Review QC reports",
    "qc:approve": "Approve/reject orders",
    "qc:override": "Override QC warnings",
    # System operations
    "system:health": "View system health",
    "system:metrics": "View metrics and analytics",
    "system:config": "Modify system configuration",
    "system:maintenance": "Perform maintenance tasks",
    # User management
    "users:read": "View users",
    "users:create": "Create users",
    "users:update": "Update users",
    "users:delete": "Delete users",
    # Alerts
    "alerts:read": "View alerts",
    "alerts:manage": "Acknowledge/resolve alerts",
}

# Role to permissions mapping
ROLES: Dict[str, Set[str]] = {
    "admin": {
        # Admin has all permissions
        "orders:create",
        "orders:read",
        "orders:update",
        "orders:delete",
        "orders:download",
        "queue:read",
        "queue:manage",
        "qc:review",
        "qc:approve",
        "qc:override",
        "system:health",
        "system:metrics",
        "system:config",
        "system:maintenance",
        "users:read",
        "users:create",
        "users:update",
        "users:delete",
        "alerts:read",
        "alerts:manage",
    },
    "operator": {
        "orders:create",
        "orders:read",
        "orders:update",
        "orders:download",
        "queue:read",
        "queue:manage",
        "system:health",
        "alerts:read",
    },
    "qc_tech": {
        "orders:read",
        "orders:download",
        "queue:read",
        "qc:review",
        "qc:approve",
        "qc:override",
        "system:health",
        "system:metrics",
        "alerts:read",
        "alerts:manage",
    },
    "maintenance": {
        "orders:read",
        "queue:read",
        "system:health",
        "system:metrics",
        "system:maintenance",
        "alerts:read",
        "alerts:manage",
    },
    "readonly": {
        "orders:read",
        "queue:read",
        "system:health",
        "alerts:read",
    },
    "service": {
        # Service accounts (API key auth) have limited permissions
        "orders:create",
        "orders:read",
        "orders:update",
        "queue:read",
        "queue:manage",
        "system:health",
    },
}


def get_user_permissions(role: str) -> Set[str]:
    """
    Get all permissions for a role.

    Args:
        role: Role name

    Returns:
        Set of permission strings
    """
    return ROLES.get(role, set())


def check_permission(user: Dict[str, Any], permission: str) -> bool:
    """
    Check if a user has a specific permission.

    Args:
        user: User data dict with 'role' key
        permission: Permission to check

    Returns:
        True if user has permission
    """
    role = user.get("role", "readonly")
    permissions = get_user_permissions(role)
    return permission in permissions


def check_any_permission(user: Dict[str, Any], permissions: List[str]) -> bool:
    """
    Check if user has any of the specified permissions.

    Args:
        user: User data dict
        permissions: List of permissions (user needs at least one)

    Returns:
        True if user has at least one permission
    """
    role = user.get("role", "readonly")
    user_permissions = get_user_permissions(role)
    return bool(user_permissions & set(permissions))


def check_all_permissions(user: Dict[str, Any], permissions: List[str]) -> bool:
    """
    Check if user has all specified permissions.

    Args:
        user: User data dict
        permissions: List of permissions (user needs all)

    Returns:
        True if user has all permissions
    """
    role = user.get("role", "readonly")
    user_permissions = get_user_permissions(role)
    return set(permissions).issubset(user_permissions)


def require_role(allowed_roles: List[str]):
    """
    FastAPI dependency that requires specific roles.

    Usage:
        @app.post("/orders", dependencies=[Depends(require_role(["operator", "admin"]))])
        async def create_order(...):

    Or with user injection:
        @app.post("/orders")
        async def create_order(user: dict = Depends(require_role(["operator", "admin"]))):

    Args:
        allowed_roles: List of roles that can access the endpoint

    Returns:
        Dependency function
    """
    from .auth import get_current_user

    async def _check_role(
        user: Dict[str, Any] = Depends(get_current_user),
    ) -> Dict[str, Any]:
        # Auth disabled in dev mode
        if user.get("auth_disabled"):
            return user

        user_role = user.get("role", "readonly")

        if user_role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role: {' or '.join(allowed_roles)}, your role: {user_role}",
            )

        return user

    return _check_role


def require_permission(permission: str):
    """
    FastAPI dependency that requires a specific permission.

    Usage:
        @app.post("/orders")
        async def create_order(user: dict = Depends(require_permission("orders:create"))):

    Args:
        permission: Required permission string

    Returns:
        Dependency function
    """
    from .auth import get_current_user

    async def _check_permission(
        user: Dict[str, Any] = Depends(get_current_user),
    ) -> Dict[str, Any]:
        # Auth disabled in dev mode
        if user.get("auth_disabled"):
            return user

        if not check_permission(user, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required permission: {permission}",
            )

        return user

    return _check_permission


def require_any_permission(permissions: List[str]):
    """
    FastAPI dependency requiring any of the specified permissions.

    Args:
        permissions: List of permissions (user needs at least one)

    Returns:
        Dependency function
    """
    from .auth import get_current_user

    async def _check_permissions(
        user: Dict[str, Any] = Depends(get_current_user),
    ) -> Dict[str, Any]:
        if user.get("auth_disabled"):
            return user

        if not check_any_permission(user, permissions):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required one of: {', '.join(permissions)}",
            )

        return user

    return _check_permissions


def require_all_permissions(permissions: List[str]):
    """
    FastAPI dependency requiring all specified permissions.

    Args:
        permissions: List of permissions (user needs all)

    Returns:
        Dependency function
    """
    from .auth import get_current_user

    async def _check_permissions(
        user: Dict[str, Any] = Depends(get_current_user),
    ) -> Dict[str, Any]:
        if user.get("auth_disabled"):
            return user

        if not check_all_permissions(user, permissions):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required all: {', '.join(permissions)}",
            )

        return user

    return _check_permissions


class RBACMiddleware:
    """
    RBAC middleware for route-level permission checking.

    Can be used to define permissions at the route decorator level.
    """

    def __init__(self, app):
        self.app = app
        self.route_permissions: Dict[str, List[str]] = {}

    def register_route_permission(self, path: str, method: str, permissions: List[str]):
        """Register required permissions for a route."""
        key = f"{method.upper()}:{path}"
        self.route_permissions[key] = permissions

    async def __call__(self, scope, receive, send):
        # For now, just pass through - actual checking done via dependencies
        await self.app(scope, receive, send)


def permission_required(permission: str):
    """
    Decorator for functions that require a permission.

    Useful for non-FastAPI functions where you want permission checking.

    Usage:
        @permission_required("orders:create")
        def create_order(user: dict, order_data: dict):
            ...

    Args:
        permission: Required permission

    Returns:
        Decorator function
    """

    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, user: Dict[str, Any] = None, **kwargs):
            if user is None:
                raise ValueError("User argument required for permission check")

            if not check_permission(user, permission):
                raise PermissionError(f"Permission denied: {permission}")

            return func(*args, user=user, **kwargs)

        return wrapper

    return decorator


# Convenience functions for common role checks
def is_admin(user: Dict[str, Any]) -> bool:
    """Check if user is admin."""
    return user.get("role") == "admin"


def is_operator(user: Dict[str, Any]) -> bool:
    """Check if user is operator."""
    return user.get("role") == "operator"


def is_qc_tech(user: Dict[str, Any]) -> bool:
    """Check if user is QC tech."""
    return user.get("role") == "qc_tech"


def can_process_orders(user: Dict[str, Any]) -> bool:
    """Check if user can process orders."""
    return check_permission(user, "orders:create")


def can_manage_queue(user: Dict[str, Any]) -> bool:
    """Check if user can manage the cutter queue."""
    return check_permission(user, "queue:manage")


def can_approve_qc(user: Dict[str, Any]) -> bool:
    """Check if user can approve/reject QC."""
    return check_permission(user, "qc:approve")


# Testing
def _test_rbac():
    """Test RBAC functions."""
    # Test admin permissions
    admin_user = {"username": "admin", "role": "admin"}
    assert check_permission(admin_user, "orders:create")
    assert check_permission(admin_user, "users:delete")
    assert check_permission(admin_user, "system:config")
    assert is_admin(admin_user)

    # Test operator permissions
    operator_user = {"username": "op1", "role": "operator"}
    assert check_permission(operator_user, "orders:create")
    assert check_permission(operator_user, "queue:manage")
    assert not check_permission(operator_user, "users:delete")
    assert not check_permission(operator_user, "system:config")
    assert is_operator(operator_user)

    # Test QC tech permissions
    qc_user = {"username": "qc1", "role": "qc_tech"}
    assert check_permission(qc_user, "qc:approve")
    assert check_permission(qc_user, "qc:override")
    assert not check_permission(qc_user, "orders:create")
    assert is_qc_tech(qc_user)

    # Test readonly permissions
    readonly_user = {"username": "viewer", "role": "readonly"}
    assert check_permission(readonly_user, "orders:read")
    assert check_permission(readonly_user, "queue:read")
    assert not check_permission(readonly_user, "orders:create")
    assert not check_permission(readonly_user, "queue:manage")

    # Test any/all permission checks
    assert check_any_permission(operator_user, ["orders:create", "system:config"])
    assert not check_any_permission(readonly_user, ["orders:create", "system:config"])
    assert check_all_permissions(admin_user, ["orders:create", "users:delete"])
    assert not check_all_permissions(operator_user, ["orders:create", "users:delete"])

    print("All RBAC tests passed!")


if __name__ == "__main__":
    _test_rbac()
