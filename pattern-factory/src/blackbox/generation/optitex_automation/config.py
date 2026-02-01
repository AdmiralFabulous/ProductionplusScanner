"""
Optitex Configuration Module

Environment-based configuration for Optitex automation.
Follows the same pattern as security/config.py.

Environment Variables:
    OPTITEX_ENABLED: Enable/disable Optitex integration (default: false)
    OPTITEX_PDS_EXE: Path to PDS.exe
    OPTITEX_MARKER_EXE: Path to Marker.exe
    OPTITEX_TEMPLATES_DIR: Directory for PDS templates
    OPTITEX_OUTPUT_DIR: Directory for generated files
    OPTITEX_SCRIPTS_DIR: Directory for batch scripts
    OPTITEX_TIMEOUT: Execution timeout in seconds

Author: SameDaySuits
Date: February 2026
"""

import os
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class OptitexConfig:
    """Optitex configuration from environment variables."""

    # Enable/disable Optitex integration
    enabled: bool = field(
        default_factory=lambda: os.getenv("OPTITEX_ENABLED", "false").lower() == "true"
    )

    # Paths to Optitex executables (Windows only)
    pds_exe: Path = field(
        default_factory=lambda: Path(
            os.getenv("OPTITEX_PDS_EXE", "C:/Program Files/Optitex/PDS.exe")
        )
    )
    marker_exe: Path = field(
        default_factory=lambda: Path(
            os.getenv("OPTITEX_MARKER_EXE", "C:/Program Files/Optitex/Marker.exe")
        )
    )

    # Working directories
    templates_dir: Path = field(
        default_factory=lambda: Path(
            os.getenv("OPTITEX_TEMPLATES_DIR", "./templates/optitex")
        )
    )
    output_dir: Path = field(
        default_factory=lambda: Path(
            os.getenv("OPTITEX_OUTPUT_DIR", "./output/optitex")
        )
    )
    scripts_dir: Path = field(
        default_factory=lambda: Path(
            os.getenv("OPTITEX_SCRIPTS_DIR", "./scripts/optitex")
        )
    )

    # Execution settings
    timeout_seconds: int = field(
        default_factory=lambda: int(os.getenv("OPTITEX_TIMEOUT", "300"))
    )
    max_retries: int = field(
        default_factory=lambda: int(os.getenv("OPTITEX_MAX_RETRIES", "3"))
    )

    # Default units for measurements (CM or INCH)
    default_unit: str = field(
        default_factory=lambda: os.getenv("OPTITEX_DEFAULT_UNIT", "CM")
    )

    def __post_init__(self):
        """Validate and log configuration."""
        if self.enabled:
            logger.info("Optitex integration enabled")
            logger.info(f"  PDS.exe: {self.pds_exe}")
            logger.info(f"  Marker.exe: {self.marker_exe}")
            logger.info(f"  Templates: {self.templates_dir}")
            logger.info(f"  Output: {self.output_dir}")
            logger.info(f"  Timeout: {self.timeout_seconds}s")

            # Check if executables exist
            if not self.pds_exe.exists():
                logger.warning(f"PDS.exe not found at: {self.pds_exe}")
            if not self.marker_exe.exists():
                logger.warning(f"Marker.exe not found at: {self.marker_exe}")
        else:
            logger.debug("Optitex integration disabled")

    def is_available(self) -> bool:
        """Check if Optitex is available and configured."""
        if not self.enabled:
            return False
        return self.pds_exe.exists() and self.marker_exe.exists()

    def ensure_directories(self) -> None:
        """Create working directories if they don't exist."""
        self.templates_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.scripts_dir.mkdir(parents=True, exist_ok=True)

    def get_template_path(self, template_name: str) -> Path:
        """Get full path to a template file."""
        # Check with .pds extension
        pds_path = self.templates_dir / f"{template_name}.pds"
        if pds_path.exists():
            return pds_path

        # Check without extension (might already have it)
        direct_path = self.templates_dir / template_name
        if direct_path.exists():
            return direct_path

        return pds_path  # Return expected path even if not found

    def get_output_path(self, order_id: str, extension: str = "pds") -> Path:
        """Get output path for an order."""
        order_dir = self.output_dir / order_id
        order_dir.mkdir(parents=True, exist_ok=True)
        return order_dir / f"{order_id}.{extension}"


# Singleton instance
_config: Optional[OptitexConfig] = None


def get_optitex_config() -> OptitexConfig:
    """
    Get the Optitex configuration singleton.

    Returns:
        OptitexConfig instance
    """
    global _config
    if _config is None:
        _config = OptitexConfig()
    return _config


def reset_config() -> None:
    """Reset configuration (useful for testing)."""
    global _config
    _config = None


# Legacy alias for backwards compatibility with existing code
# Note: This creates a module-level config instance that can be imported
class _ConfigProxy:
    """Proxy class to allow lazy loading of config."""

    def __getattr__(self, name):
        return getattr(get_optitex_config(), name)


config = _ConfigProxy()


# For direct module attribute access (backwards compatibility)
def __getattr__(name):
    """Allow accessing config attributes directly from module."""
    if name in (
        "pds_exe",
        "marker_exe",
        "templates_dir",
        "output_dir",
        "scripts_dir",
        "timeout_seconds",
        "enabled",
    ):
        return getattr(get_optitex_config(), name)
    raise AttributeError(f"module 'config' has no attribute '{name}'")
