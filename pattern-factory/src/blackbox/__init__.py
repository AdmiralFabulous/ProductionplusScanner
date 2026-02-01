"""
BlackBox Module - Body Measurement Extraction & Pattern Generation

This module contains the complete scan-to-pattern pipeline:
1. Scanning - ArUco calibration, MediaPipe pose, SAM 3D Body
2. Translation - M. Muller pattern mathematics
3. Generation - DXF/HPGL output, Optitex automation

Usage:
    # Full pipeline (requires scanning dependencies)
    from blackbox.pipeline import BlackBoxPipeline

    # Translation only (no external deps)
    from blackbox.translation import MullerTranslator

    # Optitex automation (Windows + Optitex required)
    from blackbox.generation.optitex_automation import OptitexAutomationWorkflow

Installation:
    pip install .[scanning]   # Add scanning capabilities (opencv, mediapipe)
    pip install .[patterns]   # Add pattern generation (ezdxf)
    pip install .[all]        # Everything

Author: SameDaySuits
Date: February 2026
"""

import logging

logger = logging.getLogger(__name__)

# Version info
__version__ = "1.0.0"
__author__ = "SameDaySuits"

# Check for optional dependencies and provide graceful degradation
_SCANNING_AVAILABLE = False
_PATTERNS_AVAILABLE = False

try:
    import cv2
    import mediapipe

    _SCANNING_AVAILABLE = True
except ImportError:
    logger.debug(
        "Scanning dependencies not available. Install with: pip install .[scanning]"
    )

try:
    import ezdxf

    _PATTERNS_AVAILABLE = True
except ImportError:
    logger.debug(
        "Pattern generation dependencies not available. Install with: pip install .[patterns]"
    )


def scanning_available() -> bool:
    """Check if scanning modules are available."""
    return _SCANNING_AVAILABLE


def patterns_available() -> bool:
    """Check if pattern generation modules are available."""
    return _PATTERNS_AVAILABLE


# Always available imports (no external deps)
from blackbox.translation.muller_translator import (
    MullerTranslator,
    MullerTranslationError,
    BodyMeasurements,
    PatternParameters,
    FitType,
    FabricType,
    calculate_pattern_params,
)

# Conditional imports for scanning
if _SCANNING_AVAILABLE:
    try:
        from blackbox.scanning.aruco_calibration import (
            detect_aruco_marker,
            ArucoCalibrationError,
            pixels_to_cm,
            generate_aruco_marker,
        )
        from blackbox.scanning.pose_extraction import (
            PoseExtractor,
            PoseExtractionError,
            Landmark,
            extract_measurements_from_file,
        )
    except ImportError as e:
        logger.warning(f"Could not import scanning modules: {e}")

# Conditional imports for patterns
if _PATTERNS_AVAILABLE:
    try:
        from blackbox.generation.dxf_generator import (
            DXFGenerator,
            generate_suit_patterns,
        )
    except ImportError as e:
        logger.warning(f"Could not import pattern generation modules: {e}")

# Export list
__all__ = [
    # Version
    "__version__",
    # Availability checks
    "scanning_available",
    "patterns_available",
    # Translation (always available)
    "MullerTranslator",
    "MullerTranslationError",
    "BodyMeasurements",
    "PatternParameters",
    "FitType",
    "FabricType",
    "calculate_pattern_params",
]

# Add scanning exports if available
if _SCANNING_AVAILABLE:
    __all__.extend(
        [
            "detect_aruco_marker",
            "ArucoCalibrationError",
            "pixels_to_cm",
            "generate_aruco_marker",
            "PoseExtractor",
            "PoseExtractionError",
            "Landmark",
            "extract_measurements_from_file",
        ]
    )

# Add pattern exports if available
if _PATTERNS_AVAILABLE:
    __all__.extend(
        [
            "DXFGenerator",
            "generate_suit_patterns",
        ]
    )
