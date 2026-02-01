#!/usr/bin/env python3
"""
User Management Module

Provides user CRUD operations with Supabase storage.
Handles user creation, authentication, and role management.

Usage:
    from security.users import UserService, UserCreate

    service = UserService()
    user = await service.create_user(UserCreate(
        username="operator1",
        password="secure_password",
        role="operator"
    ))

Author: Claude
Date: 2026-01-31
"""

import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field, asdict
from enum import Enum

from pydantic import BaseModel, Field, EmailStr


class UserRole(str, Enum):
    """Available user roles."""

    ADMIN = "admin"
    OPERATOR = "operator"
    QC_TECH = "qc_tech"
    MAINTENANCE = "maintenance"
    READONLY = "readonly"


@dataclass
class User:
    """User data model."""

    id: str
    username: str
    email: Optional[str]
    password_hash: str
    role: str
    is_active: bool = True
    last_login: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses (excludes password_hash)."""
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "role": self.role,
            "is_active": self.is_active,
            "last_login": self.last_login,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class UserCreate(BaseModel):
    """Schema for creating a new user."""

    username: str = Field(..., min_length=3, max_length=50)
    email: Optional[EmailStr] = None
    password: str = Field(..., min_length=8)
    role: UserRole = UserRole.READONLY


class UserUpdate(BaseModel):
    """Schema for updating a user."""

    email: Optional[EmailStr] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None


class UserChangePassword(BaseModel):
    """Schema for changing password."""

    current_password: str
    new_password: str = Field(..., min_length=8)


class UserService:
    """
    Service for managing users in Supabase.

    Falls back to in-memory storage if Supabase is unavailable.
    """

    def __init__(self):
        """Initialize user service."""
        self._client = None
        self._in_memory_users: Dict[str, User] = {}
        self._use_in_memory = False

        self._initialize_client()

    def _initialize_client(self):
        """Initialize Supabase client."""
        try:
            from .config import get_config
            from supabase import create_client

            config = get_config()

            if config.supabase_url and config.supabase_key:
                self._client = create_client(config.supabase_url, config.supabase_key)
            else:
                self._use_in_memory = True
                self._seed_default_users()
        except Exception as e:
            print(f"Warning: Could not connect to Supabase: {e}")
            self._use_in_memory = True
            self._seed_default_users()

    def _seed_default_users(self):
        """Create default users for development."""
        from .auth import hash_password

        default_users = [
            {
                "username": "admin",
                "email": "admin@samedaysuits.com",
                "password": "admin123456",
                "role": UserRole.ADMIN.value,
            },
            {
                "username": "operator",
                "email": "operator@samedaysuits.com",
                "password": "operator123",
                "role": UserRole.OPERATOR.value,
            },
            {
                "username": "qc",
                "email": "qc@samedaysuits.com",
                "password": "qctech12345",
                "role": UserRole.QC_TECH.value,
            },
        ]

        for user_data in default_users:
            user_id = str(uuid.uuid4())
            user = User(
                id=user_id,
                username=user_data["username"],
                email=user_data["email"],
                password_hash=hash_password(user_data["password"]),
                role=user_data["role"],
                is_active=True,
            )
            self._in_memory_users[user.username] = user

        print(f"Seeded {len(default_users)} default users for development")

    async def create_user(self, user_data: UserCreate) -> User:
        """
        Create a new user.

        Args:
            user_data: User creation data

        Returns:
            Created user
        """
        from .auth import hash_password

        user_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()

        user = User(
            id=user_id,
            username=user_data.username,
            email=user_data.email,
            password_hash=hash_password(user_data.password),
            role=user_data.role.value,
            is_active=True,
            created_at=now,
            updated_at=now,
        )

        if self._use_in_memory:
            if user_data.username in self._in_memory_users:
                raise ValueError(f"Username '{user_data.username}' already exists")
            self._in_memory_users[user.username] = user
        else:
            try:
                result = (
                    self._client.table("users")
                    .insert(
                        {
                            "id": user.id,
                            "username": user.username,
                            "email": user.email,
                            "password_hash": user.password_hash,
                            "role": user.role,
                            "is_active": user.is_active,
                            "created_at": user.created_at,
                            "updated_at": user.updated_at,
                        }
                    )
                    .execute()
                )

                if not result.data:
                    raise ValueError("Failed to create user in database")
            except Exception as e:
                if "duplicate" in str(e).lower():
                    raise ValueError(f"Username '{user_data.username}' already exists")
                raise

        return user

    async def get_by_id(self, user_id: str) -> Optional[User]:
        """
        Get user by ID.

        Args:
            user_id: User ID

        Returns:
            User or None
        """
        if self._use_in_memory:
            for user in self._in_memory_users.values():
                if user.id == user_id:
                    return user
            return None

        try:
            result = self._client.table("users").select("*").eq("id", user_id).execute()
            if result.data:
                return self._user_from_dict(result.data[0])
            return None
        except Exception:
            return None

    async def get_by_username(self, username: str) -> Optional[User]:
        """
        Get user by username.

        Args:
            username: Username

        Returns:
            User or None
        """
        if self._use_in_memory:
            return self._in_memory_users.get(username)

        try:
            result = (
                self._client.table("users")
                .select("*")
                .eq("username", username)
                .execute()
            )
            if result.data:
                return self._user_from_dict(result.data[0])
            return None
        except Exception:
            return None

    async def get_by_email(self, email: str) -> Optional[User]:
        """
        Get user by email.

        Args:
            email: Email address

        Returns:
            User or None
        """
        if self._use_in_memory:
            for user in self._in_memory_users.values():
                if user.email == email:
                    return user
            return None

        try:
            result = (
                self._client.table("users").select("*").eq("email", email).execute()
            )
            if result.data:
                return self._user_from_dict(result.data[0])
            return None
        except Exception:
            return None

    async def update_user(self, user_id: str, updates: UserUpdate) -> Optional[User]:
        """
        Update user fields.

        Args:
            user_id: User ID
            updates: Fields to update

        Returns:
            Updated user or None
        """
        user = await self.get_by_id(user_id)
        if not user:
            return None

        update_data = updates.model_dump(exclude_unset=True)
        update_data["updated_at"] = datetime.utcnow().isoformat()

        # Convert role enum to string if present
        if "role" in update_data and update_data["role"]:
            update_data["role"] = update_data["role"].value

        if self._use_in_memory:
            for key, value in update_data.items():
                if hasattr(user, key):
                    setattr(user, key, value)
            return user

        try:
            result = (
                self._client.table("users")
                .update(update_data)
                .eq("id", user_id)
                .execute()
            )
            if result.data:
                return self._user_from_dict(result.data[0])
            return None
        except Exception:
            return None

    async def change_password(
        self, user_id: str, current_password: str, new_password: str
    ) -> bool:
        """
        Change user password.

        Args:
            user_id: User ID
            current_password: Current password for verification
            new_password: New password

        Returns:
            True if successful
        """
        from .auth import hash_password, verify_password

        user = await self.get_by_id(user_id)
        if not user:
            return False

        if not verify_password(current_password, user.password_hash):
            return False

        new_hash = hash_password(new_password)

        if self._use_in_memory:
            user.password_hash = new_hash
            user.updated_at = datetime.utcnow().isoformat()
            return True

        try:
            self._client.table("users").update(
                {"password_hash": new_hash, "updated_at": datetime.utcnow().isoformat()}
            ).eq("id", user_id).execute()
            return True
        except Exception:
            return False

    async def update_last_login(self, user_id: str):
        """
        Update user's last login timestamp.

        Args:
            user_id: User ID
        """
        now = datetime.utcnow().isoformat()

        if self._use_in_memory:
            user = await self.get_by_id(user_id)
            if user:
                user.last_login = now
            return

        try:
            self._client.table("users").update({"last_login": now}).eq(
                "id", user_id
            ).execute()
        except Exception:
            pass

    async def delete_user(self, user_id: str) -> bool:
        """
        Delete a user.

        Args:
            user_id: User ID

        Returns:
            True if deleted
        """
        if self._use_in_memory:
            for username, user in list(self._in_memory_users.items()):
                if user.id == user_id:
                    del self._in_memory_users[username]
                    return True
            return False

        try:
            self._client.table("users").delete().eq("id", user_id).execute()
            return True
        except Exception:
            return False

    async def list_users(
        self,
        role: Optional[str] = None,
        is_active: Optional[bool] = None,
        limit: int = 100,
    ) -> List[User]:
        """
        List users with optional filters.

        Args:
            role: Filter by role
            is_active: Filter by active status
            limit: Maximum users to return

        Returns:
            List of users
        """
        if self._use_in_memory:
            users = list(self._in_memory_users.values())
            if role:
                users = [u for u in users if u.role == role]
            if is_active is not None:
                users = [u for u in users if u.is_active == is_active]
            return users[:limit]

        try:
            query = self._client.table("users").select("*")
            if role:
                query = query.eq("role", role)
            if is_active is not None:
                query = query.eq("is_active", is_active)
            query = query.limit(limit)

            result = query.execute()
            return [self._user_from_dict(u) for u in result.data]
        except Exception:
            return []

    def user_exists(self, user_id: str) -> bool:
        """
        Check if user exists (sync version for token validation).

        Args:
            user_id: User ID

        Returns:
            True if exists
        """
        if self._use_in_memory:
            for user in self._in_memory_users.values():
                if user.id == user_id:
                    return True
            return False

        try:
            result = (
                self._client.table("users").select("id").eq("id", user_id).execute()
            )
            return len(result.data) > 0
        except Exception:
            return False

    def _user_from_dict(self, data: Dict[str, Any]) -> User:
        """Convert database dict to User object."""
        return User(
            id=data["id"],
            username=data["username"],
            email=data.get("email"),
            password_hash=data["password_hash"],
            role=data["role"],
            is_active=data.get("is_active", True),
            last_login=data.get("last_login"),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
        )


# Singleton service instance
_user_service: Optional[UserService] = None


def get_user_service() -> UserService:
    """Get the global user service instance."""
    global _user_service
    if _user_service is None:
        _user_service = UserService()
    return _user_service


# Testing
async def _test_users():
    """Test user service."""
    import os

    os.environ["JWT_SECRET"] = "test-jwt-secret-at-least-32-characters-long"
    os.environ["ENCRYPTION_KEY"] = "test-encryption-key-at-least-32-chars"

    from .config import reset_config

    reset_config()

    service = UserService()

    # Test create user
    user = await service.create_user(
        UserCreate(
            username="testuser",
            email="test@example.com",
            password="testpassword123",
            role=UserRole.OPERATOR,
        )
    )
    assert user.username == "testuser"
    assert user.role == "operator"

    # Test get by username
    found = await service.get_by_username("testuser")
    assert found is not None
    assert found.id == user.id

    # Test update
    updated = await service.update_user(user.id, UserUpdate(role=UserRole.QC_TECH))
    assert updated.role == "qc_tech"

    # Test list
    users = await service.list_users()
    assert len(users) >= 1

    # Test delete
    deleted = await service.delete_user(user.id)
    assert deleted is True

    print("All user service tests passed!")

    reset_config()


if __name__ == "__main__":
    import asyncio

    asyncio.run(_test_users())
