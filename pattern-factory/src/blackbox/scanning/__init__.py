"""
BlackBox Scanning Module

Contains body measurement extraction from images:
- ArUco marker calibration for scale detection
- MediaPipe pose extraction (33 landmarks)
- SAM 3D Body extraction (high accuracy)

Requires: pip install .[scanning]
"""

import logging

logger = logging.getLogger(__name__)

# Check dependencies
_OPENCV_AVAILABLE = False
_MEDIAPIPE_AVAILABLE = False

try:
    import cv2

    _OPENCV_AVAILABLE = True
except ImportError:
    logger.warning("OpenCV not available. Install with: pip install opencv-python")

try:
    import mediapipe

    _MEDIAPIPE_AVAILABLE = True
except ImportError:
    logger.warning("MediaPipe not available. Install with: pip install mediapipe")


# Conditional exports
__all__ = []

if _OPENCV_AVAILABLE:
    from blackbox.scanning.aruco_calibration import (
        detect_aruco_marker,
        generate_aruco_marker,
        calibrate_from_file,
        pixels_to_cm,
        cm_to_pixels,
        ArucoCalibrationError,
    )

    __all__.extend(
        [
            "detect_aruco_marker",
            "generate_aruco_marker",
            "calibrate_from_file",
            "pixels_to_cm",
            "cm_to_pixels",
            "ArucoCalibrationError",
        ]
    )

if _OPENCV_AVAILABLE and _MEDIAPIPE_AVAILABLE:
    from blackbox.scanning.pose_extraction import (
        PoseExtractor,
        PoseExtractionError,
        Landmark,
        LANDMARK_NAMES,
        extract_measurements_from_file,
    )

    __all__.extend(
        [
            "PoseExtractor",
            "PoseExtractionError",
            "Landmark",
            "LANDMARK_NAMES",
            "extract_measurements_from_file",
        ]
    )

# SAM 3D Body has additional dependencies
try:
    from blackbox.scanning.sam3d_extractor import (
        SAM3DBodyExtractor,
        SAM3DBodyError,
        BodyMesh,
        BodyMeasurements3D,
        extract_measurements_sam3d,
    )

    __all__.extend(
        [
            "SAM3DBodyExtractor",
            "SAM3DBodyError",
            "BodyMesh",
            "BodyMeasurements3D",
            "extract_measurements_sam3d",
        ]
    )
except ImportError as e:
    logger.debug(f"SAM 3D Body not available: {e}")
