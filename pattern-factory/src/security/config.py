#!/usr/bin/env python3
"""
Secure Configuration Management

Loads configuration from environment variables with validation.
All sensitive values must be provided via environment, not hardcoded.

Usage:
    from security.config import get_config
    config = get_config()
    secret = config.jwt_secret

Author: Claude
Date: 2026-01-31
"""

import os
import secrets
from dataclasses import dataclass
from typing import Optional, List
from functools import lru_cache

from dotenv import load_dotenv

# Load .env file if present
load_dotenv()


@dataclass
class SecureConfig:
    """
    Secure configuration container.

    All sensitive values are loaded from environment variables.
    Provides validation and secure defaults where appropriate.
    """

    # Required fields (no defaults) must come first
    jwt_secret: str
    encryption_key: str
    supabase_url: str
    supabase_key: str

    # Optional fields with defaults
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24
    jwt_refresh_expiration_days: int = 7
    supabase_service_key: Optional[str] = None
    api_key: Optional[str] = None
    allowed_origins: Optional[List[str]] = None
    audit_log_path: str = "logs/audit.log"
    audit_to_database: bool = True
    auth_enabled: bool = True
    encryption_enabled: bool = True
    audit_enabled: bool = True

    def __post_init__(self):
        """Validate configuration after initialization."""
        if self.allowed_origins is None:
            self.allowed_origins = ["http://localhost:3000", "http://localhost:8000"]

        # Validate JWT secret strength
        if len(self.jwt_secret) < 32:
            raise ValueError(
                "JWT_SECRET must be at least 32 characters. "
                'Generate one with: python -c "import secrets; print(secrets.token_hex(32))"'
            )

        # Validate encryption key
        if self.encryption_enabled and len(self.encryption_key) < 32:
            raise ValueError(
                "ENCRYPTION_KEY must be at least 32 characters. "
                'Generate one with: python -c "import secrets; print(secrets.token_hex(32))"'
            )

    @classmethod
    def from_env(cls, require_secrets: bool = True) -> "SecureConfig":
        """
        Load configuration from environment variables.

        Args:
            require_secrets: If True, raise error for missing secrets.
                           If False, generate temporary secrets (dev mode).

        Returns:
            SecureConfig instance
        """
        # Check if we're in development mode
        is_dev = os.getenv("ENVIRONMENT", "development").lower() in (
            "development",
            "dev",
            "local",
        )

        # JWT Secret - required in production
        jwt_secret = os.getenv("JWT_SECRET")
        if not jwt_secret:
            if require_secrets and not is_dev:
                raise ValueError("JWT_SECRET environment variable is required")
            # Generate temporary secret for development
            jwt_secret = secrets.token_hex(32)
            print(
                "WARNING: Using temporary JWT_SECRET. Set JWT_SECRET env var for production."
            )

        # Encryption Key - required in production
        encryption_key = os.getenv("ENCRYPTION_KEY")
        if not encryption_key:
            if require_secrets and not is_dev:
                raise ValueError("ENCRYPTION_KEY environment variable is required")
            encryption_key = secrets.token_hex(32)
            print(
                "WARNING: Using temporary ENCRYPTION_KEY. Set ENCRYPTION_KEY env var for production."
            )

        # Supabase configuration
        supabase_url = os.getenv("SUPABASE_URL", "http://localhost:54321")
        supabase_key = os.getenv("SUPABASE_KEY", os.getenv("SUPABASE_ANON_KEY", ""))

        # For local development without Supabase, use mock key
        if not supabase_key and is_dev:
            supabase_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.mock-dev-key"

        # Parse allowed origins
        allowed_origins_str = os.getenv(
            "ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8000"
        )
        allowed_origins = [origin.strip() for origin in allowed_origins_str.split(",")]

        # Feature flags
        auth_enabled = os.getenv("AUTH_ENABLED", "true").lower() == "true"
        encryption_enabled = os.getenv("ENCRYPTION_ENABLED", "true").lower() == "true"
        audit_enabled = os.getenv("AUDIT_ENABLED", "true").lower() == "true"

        return cls(
            jwt_secret=jwt_secret,
            jwt_algorithm=os.getenv("JWT_ALGORITHM", "HS256"),
            jwt_expiration_hours=int(os.getenv("JWT_EXPIRATION_HOURS", "24")),
            jwt_refresh_expiration_days=int(
                os.getenv("JWT_REFRESH_EXPIRATION_DAYS", "7")
            ),
            encryption_key=encryption_key,
            supabase_url=supabase_url,
            supabase_key=supabase_key,
            supabase_service_key=os.getenv("SUPABASE_SERVICE_KEY"),
            api_key=os.getenv("API_KEY"),
            allowed_origins=allowed_origins,
            audit_log_path=os.getenv("AUDIT_LOG_PATH", "logs/audit.log"),
            audit_to_database=os.getenv("AUDIT_TO_DATABASE", "true").lower() == "true",
            auth_enabled=auth_enabled,
            encryption_enabled=encryption_enabled,
            audit_enabled=audit_enabled,
        )


# Singleton config instance
_config: Optional[SecureConfig] = None


def get_config(require_secrets: bool = False) -> SecureConfig:
    """
    Get the global configuration instance.

    Uses lazy loading and caching for efficiency.

    Args:
        require_secrets: If True, raise error for missing secrets.

    Returns:
        SecureConfig instance
    """
    global _config
    if _config is None:
        _config = SecureConfig.from_env(require_secrets=require_secrets)
    return _config


def reset_config():
    """Reset the cached config (for testing)."""
    global _config
    _config = None


# Utility functions for generating secrets
def generate_secret(length: int = 32) -> str:
    """Generate a cryptographically secure secret."""
    return secrets.token_hex(length)


def print_setup_instructions():
    """Print instructions for setting up security configuration."""
    print("""
╔══════════════════════════════════════════════════════════════════╗
║           SameDaySuits Security Configuration Setup              ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                  ║
║  Generate secure keys by running:                                ║
║                                                                  ║
║    python -c "import secrets; print(secrets.token_hex(32))"      ║
║                                                                  ║
║  Create a .env file with:                                        ║
║                                                                  ║
║    JWT_SECRET=<your-64-char-hex-string>                          ║
║    ENCRYPTION_KEY=<your-64-char-hex-string>                      ║
║    SUPABASE_URL=http://localhost:54321                           ║
║    SUPABASE_KEY=<your-supabase-anon-key>                         ║
║                                                                  ║
║  Optional:                                                       ║
║    API_KEY=<optional-api-key-for-services>                       ║
║    ALLOWED_ORIGINS=https://yourdomain.com                        ║
║    AUTH_ENABLED=true                                             ║
║    ENCRYPTION_ENABLED=true                                       ║
║    AUDIT_ENABLED=true                                            ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
""")


if __name__ == "__main__":
    print_setup_instructions()
    print("\nGenerated secrets:")
    print(f"  JWT_SECRET={generate_secret(32)}")
    print(f"  ENCRYPTION_KEY={generate_secret(32)}")
