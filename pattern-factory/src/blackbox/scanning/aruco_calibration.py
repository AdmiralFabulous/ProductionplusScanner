"""
POC-01: ArUco Calibration Module
ArUco marker detection for scale calibration in body measurement extraction.

Based on BUILD RECOMMENDATIONS:
- MediaPipe + ArUco (Apache 2.0) - RECOMMENDED for measurement extraction
- 2-3cm accuracy for MVP, mobile-first approach

Author: AI Agent
Date: January 2026
"""

import cv2
import cv2.aruco as aruco
import numpy as np
from pathlib import Path
from typing import Tuple, Optional, List
import logging

logger = logging.getLogger(__name__)


class ArucoCalibrationError(Exception):
    """Raised when ArUco calibration fails."""

    pass


def detect_aruco_marker(
    image: np.ndarray,
    marker_id: int = 0,
    marker_dict: int = aruco.DICT_4X4_50,
    physical_size_cm: float = 5.0,
) -> Tuple[float, np.ndarray]:
    """
    Detect ArUco marker and calculate scale factor (cm per pixel).

    Args:
        image: Input image as numpy array (BGR format)
        marker_id: Expected ArUco marker ID (default: 0)
        marker_dict: ArUco dictionary type (default: DICT_4X4_50)
        physical_size_cm: Known physical size of marker in cm (default: 5.0cm)

    Returns:
        Tuple of (scale_factor_cm_per_pixel, marker_corners)

    Raises:
        ArucoCalibrationError: If no marker detected or wrong marker ID

    Example:
        >>> import cv2
        >>> image = cv2.imread("person_with_marker.jpg")
        >>> scale, corners = detect_aruco_marker(image, physical_size_cm=5.0)
        >>> print(f"Scale: {scale:.6f} cm/pixel")
    """
    if image is None or image.size == 0:
        raise ArucoCalibrationError("Invalid image provided")

    # Convert to grayscale for detection
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Setup ArUco detector
    dictionary = aruco.getPredefinedDictionary(marker_dict)
    parameters = aruco.DetectorParameters()
    detector = aruco.ArucoDetector(dictionary, parameters)

    # Detect markers
    corners, ids, rejected = detector.detectMarkers(gray)

    if ids is None or len(ids) == 0:
        raise ArucoCalibrationError("No ArUco marker detected in image")

    # Find the specific marker ID
    marker_idx = None
    for i, detected_id in enumerate(ids):
        if detected_id[0] == marker_id:
            marker_idx = i
            break

    if marker_idx is None:
        detected_ids = [id[0] for id in ids]
        raise ArucoCalibrationError(
            f"Marker ID {marker_id} not found. Detected IDs: {detected_ids}"
        )

    # Get marker corners
    marker_corners = corners[marker_idx][0]

    # Calculate pixel width (average of all 4 sides)
    side_lengths = [
        np.linalg.norm(marker_corners[0] - marker_corners[1]),
        np.linalg.norm(marker_corners[1] - marker_corners[2]),
        np.linalg.norm(marker_corners[2] - marker_corners[3]),
        np.linalg.norm(marker_corners[3] - marker_corners[0]),
    ]
    avg_pixel_width = np.mean(side_lengths)

    # Calculate scale factor
    scale_factor = physical_size_cm / avg_pixel_width

    logger.info(f"Detected marker ID: {marker_id}")
    logger.info(f"Pixel width: {avg_pixel_width:.2f} px")
    logger.info(f"Scale factor: {scale_factor:.6f} cm/px")

    return scale_factor, marker_corners


def generate_aruco_marker(
    marker_id: int = 0,
    marker_dict: int = aruco.DICT_4X4_50,
    size_pixels: int = 200,
    output_path: Optional[Path] = None,
) -> np.ndarray:
    """
    Generate an ArUco marker image for printing.

    Args:
        marker_id: Marker ID to generate (default: 0)
        marker_dict: ArUco dictionary type (default: DICT_4X4_50)
        size_pixels: Size of marker in pixels (default: 200)
        output_path: Optional path to save marker image

    Returns:
        Marker image as numpy array

    Example:
        >>> marker = generate_aruco_marker(marker_id=0, size_pixels=200)
        >>> cv2.imwrite("aruco_marker.png", marker)
        >>> print("Print at exactly 5cm x 5cm for calibration")
    """
    dictionary = aruco.getPredefinedDictionary(marker_dict)
    marker_image = aruco.generateImageMarker(dictionary, marker_id, size_pixels)

    if output_path:
        cv2.imwrite(str(output_path), marker_image)
        logger.info(f"Marker saved to {output_path}")
        logger.info(f"Print at exactly 5cm x 5cm for calibration")

    return marker_image


def pixels_to_cm(pixel_distance: float, scale_factor: float) -> float:
    """
    Convert pixel distance to centimeters using scale factor.

    Args:
        pixel_distance: Distance in pixels
        scale_factor: Scale factor from ArUco calibration (cm/pixel)

    Returns:
        Distance in centimeters
    """
    return pixel_distance * scale_factor


def cm_to_pixels(cm_distance: float, scale_factor: float) -> float:
    """
    Convert centimeters to pixels using scale factor.

    Args:
        cm_distance: Distance in centimeters
        scale_factor: Scale factor from ArUco calibration (cm/pixel)

    Returns:
        Distance in pixels
    """
    return cm_distance / scale_factor


def draw_aruco_debug(
    image: np.ndarray, corners: np.ndarray, scale_factor: float, marker_id: int = 0
) -> np.ndarray:
    """
    Draw debug visualization of detected ArUco marker.

    Args:
        image: Original image
        corners: Marker corners from detect_aruco_marker
        scale_factor: Calculated scale factor
        marker_id: Marker ID

    Returns:
        Image with debug overlay
    """
    debug_image = image.copy()

    # Draw marker outline
    corners_int = corners.astype(np.int32)
    cv2.polylines(debug_image, [corners_int], True, (0, 255, 0), 2)

    # Draw corner points
    for i, corner in enumerate(corners):
        cv2.circle(debug_image, tuple(corner.astype(int)), 5, (0, 0, 255), -1)
        cv2.putText(
            debug_image,
            str(i),
            tuple((corner + 10).astype(int)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (255, 0, 0),
            2,
        )

    # Add scale info
    cv2.putText(
        debug_image,
        f"ID: {marker_id} | Scale: {scale_factor:.4f} cm/px",
        (10, 30),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (0, 255, 0),
        2,
    )

    return debug_image


def calibrate_from_file(
    image_path: Path,
    marker_id: int = 0,
    physical_size_cm: float = 5.0,
    save_debug: bool = False,
    debug_output_path: Optional[Path] = None,
) -> Tuple[float, np.ndarray]:
    """
    Calibrate from image file with optional debug output.

    Args:
        image_path: Path to image file
        marker_id: Expected marker ID
        physical_size_cm: Physical marker size
        save_debug: Whether to save debug visualization
        debug_output_path: Path for debug image (optional)

    Returns:
        Tuple of (scale_factor, marker_corners)
    """
    image = cv2.imread(str(image_path))
    if image is None:
        raise ArucoCalibrationError(f"Could not load image: {image_path}")

    scale_factor, corners = detect_aruco_marker(
        image, marker_id=marker_id, physical_size_cm=physical_size_cm
    )

    if save_debug:
        debug_image = draw_aruco_debug(image, corners, scale_factor, marker_id)
        if debug_output_path:
            cv2.imwrite(str(debug_output_path), debug_image)
            logger.info(f"Debug image saved to {debug_output_path}")
        else:
            debug_path = (
                image_path.parent / f"{image_path.stem}_debug{image_path.suffix}"
            )
            cv2.imwrite(str(debug_path), debug_image)
            logger.info(f"Debug image saved to {debug_path}")

    return scale_factor, corners


if __name__ == "__main__":
    # Example usage
    import argparse

    parser = argparse.ArgumentParser(description="ArUco calibration tool")
    parser.add_argument(
        "--generate", action="store_true", help="Generate calibration marker"
    )
    parser.add_argument("--detect", type=Path, help="Detect marker in image file")
    parser.add_argument("--marker-id", type=int, default=0, help="Marker ID")
    parser.add_argument("--size", type=float, default=5.0, help="Physical size in cm")
    parser.add_argument("--debug", action="store_true", help="Save debug visualization")

    args = parser.parse_args()

    if args.generate:
        marker = generate_aruco_marker(
            marker_id=args.marker_id,
            output_path=Path(f"aruco_marker_{args.marker_id}.png"),
        )
        print(f"Generated ArUco marker ID {args.marker_id}")
        print(f"Print at exactly {args.size}cm x {args.size}cm")

    elif args.detect:
        try:
            scale, corners = calibrate_from_file(
                args.detect,
                marker_id=args.marker_id,
                physical_size_cm=args.size,
                save_debug=args.debug,
            )
            print(f"\nCalibration successful!")
            print(f"Scale factor: {scale:.6f} cm/pixel")
            print(f"Marker corners shape: {corners.shape}")
        except ArucoCalibrationError as e:
            print(f"Calibration failed: {e}")
            exit(1)

    else:
        parser.print_help()
