"""
POC-02: MediaPipe Pose Extraction Module
Extract 33 body landmarks from images using MediaPipe Pose.

Based on BUILD RECOMMENDATIONS:
- MediaPipe + ArUco (Apache 2.0) - RECOMMENDED for measurement extraction
- 33 body landmarks for measurement calculations

Author: AI Agent
Date: January 2026
"""

import cv2
import mediapipe as mp
import numpy as np
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

# MediaPipe API compatibility layer
try:
    # Try legacy API (MediaPipe < 0.10.0)
    _mp_pose = mp.solutions.pose
    _mp_drawing = mp.solutions.drawing_utils
    MEDIAPIPE_LEGACY_API = True
    logger.debug("Using legacy MediaPipe API")
except AttributeError:
    # New API structure (MediaPipe >= 0.10.0)
    MEDIAPIPE_LEGACY_API = False
    _mp_pose = None
    _mp_drawing = None
    logger.warning(
        "MediaPipe legacy API not available. "
        "Pose extraction will use fallback methods. "
        "Consider using SAM 3D Body for full functionality."
    )


class PoseExtractionError(Exception):
    """Raised when pose extraction fails."""

    pass


@dataclass
class Landmark:
    """Body landmark with 3D coordinates."""

    name: str
    index: int
    x: float  # Normalized 0-1
    y: float  # Normalized 0-1
    z: float  # Normalized 0-1 (relative to hip)
    visibility: float  # Confidence 0-1

    def distance_to(self, other: "Landmark") -> float:
        """Calculate Euclidean distance to another landmark."""
        return np.sqrt(
            (self.x - other.x) ** 2 + (self.y - other.y) ** 2 + (self.z - other.z) ** 2
        )


# MediaPipe pose landmark names
LANDMARK_NAMES = [
    "nose",
    "left_eye_inner",
    "left_eye",
    "left_eye_outer",
    "right_eye_inner",
    "right_eye",
    "right_eye_outer",
    "left_ear",
    "right_ear",
    "mouth_left",
    "mouth_right",
    "left_shoulder",
    "right_shoulder",
    "left_elbow",
    "right_elbow",
    "left_wrist",
    "right_wrist",
    "left_pinky",
    "right_pinky",
    "left_index",
    "right_index",
    "left_thumb",
    "right_thumb",
    "left_hip",
    "right_hip",
    "left_knee",
    "right_knee",
    "left_ankle",
    "right_ankle",
    "left_heel",
    "right_heel",
    "left_foot_index",
    "right_foot_index",
]


class PoseExtractor:
    """Extract body measurements from images using MediaPipe Pose."""

    def __init__(
        self,
        static_image_mode: bool = True,
        model_complexity: int = 2,
        min_detection_confidence: float = 0.5,
    ):
        """
        Initialize PoseExtractor.

        Args:
            static_image_mode: True for images, False for video
            model_complexity: 0 (fast), 1 (medium), 2 (accurate)
            min_detection_confidence: Minimum confidence threshold

        Raises:
            PoseExtractionError: If MediaPipe is not available
        """
        if not MEDIAPIPE_LEGACY_API:
            raise PoseExtractionError(
                "MediaPipe legacy API not available. "
                "Please install: pip install mediapipe==0.10.3 "
                "Or use SAM 3D Body pipeline for better accuracy."
            )

        self.mp_pose = _mp_pose
        self.pose = self.mp_pose.Pose(
            static_image_mode=static_image_mode,
            model_complexity=model_complexity,
            min_detection_confidence=min_detection_confidence,
        )
        self.mp_drawing = _mp_drawing

    def extract_landmarks(self, image: np.ndarray) -> List[Landmark]:
        """
        Extract 33 body landmarks from image.

        Args:
            image: Input image as numpy array (BGR format)

        Returns:
            List of 33 Landmark objects

        Raises:
            PoseExtractionError: If no pose detected
        """
        if image is None or image.size == 0:
            raise PoseExtractionError("Invalid image provided")

        # Convert BGR to RGB
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        # Process image
        results = self.pose.process(image_rgb)

        if not results.pose_landmarks:
            raise PoseExtractionError("No pose detected in image")

        landmarks = []
        for idx, lm in enumerate(results.pose_landmarks.landmark):
            landmarks.append(
                Landmark(
                    name=LANDMARK_NAMES[idx],
                    index=idx,
                    x=lm.x,
                    y=lm.y,
                    z=lm.z,
                    visibility=lm.visibility,
                )
            )

        logger.info(f"Extracted {len(landmarks)} landmarks")
        return landmarks

    def extract_landmarks_from_file(self, image_path: Path) -> List[Landmark]:
        """Extract landmarks from image file."""
        image = cv2.imread(str(image_path))
        if image is None:
            raise PoseExtractionError(f"Could not load image: {image_path}")
        return self.extract_landmarks(image)

    def get_landmark(self, landmarks: List[Landmark], name: str) -> Landmark:
        """Get landmark by name."""
        for lm in landmarks:
            if lm.name == name:
                return lm
        raise PoseExtractionError(f"Landmark '{name}' not found")

    def calculate_measurements(
        self,
        landmarks: List[Landmark],
        scale_factor_cm_per_pixel: Optional[float] = None,
        image_height: Optional[int] = None,
    ) -> Dict[str, float]:
        """
        Calculate basic body measurements from landmarks.

        Args:
            landmarks: List of extracted landmarks
            scale_factor_cm_per_pixel: Optional scale factor from ArUco calibration
            image_height: Image height in pixels (needed for scale conversion)

        Returns:
            Dictionary of measurements
        """
        measurements = {}

        try:
            left_shoulder = self.get_landmark(landmarks, "left_shoulder")
            right_shoulder = self.get_landmark(landmarks, "right_shoulder")
            left_hip = self.get_landmark(landmarks, "left_hip")
            right_hip = self.get_landmark(landmarks, "right_hip")
            left_elbow = self.get_landmark(landmarks, "left_elbow")
            left_wrist = self.get_landmark(landmarks, "left_wrist")
            left_knee = self.get_landmark(landmarks, "left_knee")
            left_ankle = self.get_landmark(landmarks, "left_ankle")

            # Calculate distances (normalized 0-1)
            shoulder_width_norm = left_shoulder.distance_to(right_shoulder)
            hip_width_norm = left_hip.distance_to(right_hip)
            torso_length_norm = left_shoulder.distance_to(left_hip)
            upper_arm_norm = left_shoulder.distance_to(left_elbow)
            forearm_norm = left_elbow.distance_to(left_wrist)
            arm_length_norm = left_shoulder.distance_to(left_wrist)
            leg_length_norm = left_hip.distance_to(left_knee) + left_knee.distance_to(
                left_ankle
            )

            measurements["shoulder_width_norm"] = shoulder_width_norm
            measurements["hip_width_norm"] = hip_width_norm
            measurements["torso_length_norm"] = torso_length_norm
            measurements["upper_arm_length_norm"] = upper_arm_norm
            measurements["forearm_length_norm"] = forearm_norm
            measurements["arm_length_norm"] = arm_length_norm
            measurements["leg_length_norm"] = leg_length_norm

            # Convert to cm if scale factor provided
            if scale_factor_cm_per_pixel and image_height:
                # MediaPipe uses normalized coordinates, convert to pixels first
                pixel_scale = image_height  # Height in pixels

                measurements["shoulder_width_cm"] = (
                    shoulder_width_norm * pixel_scale * scale_factor_cm_per_pixel
                )
                measurements["hip_width_cm"] = (
                    hip_width_norm * pixel_scale * scale_factor_cm_per_pixel
                )
                measurements["torso_length_cm"] = (
                    torso_length_norm * pixel_scale * scale_factor_cm_per_pixel
                )
                measurements["upper_arm_length_cm"] = (
                    upper_arm_norm * pixel_scale * scale_factor_cm_per_pixel
                )
                measurements["forearm_length_cm"] = (
                    forearm_norm * pixel_scale * scale_factor_cm_per_pixel
                )
                measurements["arm_length_cm"] = (
                    arm_length_norm * pixel_scale * scale_factor_cm_per_pixel
                )
                measurements["leg_length_cm"] = (
                    leg_length_norm * pixel_scale * scale_factor_cm_per_pixel
                )

            logger.info(f"Calculated {len(measurements)} measurements")

        except PoseExtractionError as e:
            logger.warning(f"Could not calculate some measurements: {e}")

        return measurements

    def draw_pose_debug(
        self,
        image: np.ndarray,
        landmarks: List[Landmark],
        measurements: Optional[Dict[str, float]] = None,
    ) -> np.ndarray:
        """
        Draw debug visualization of detected pose.

        Args:
            image: Original image
            landmarks: Extracted landmarks
            measurements: Optional measurements to display

        Returns:
            Image with debug overlay
        """
        debug_image = image.copy()
        h, w = image.shape[:2]

        # Draw landmarks
        for lm in landmarks:
            x, y = int(lm.x * w), int(lm.y * h)
            cv2.circle(debug_image, (x, y), 3, (0, 255, 0), -1)
            cv2.putText(
                debug_image,
                str(lm.index),
                (x + 5, y - 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.3,
                (255, 0, 0),
                1,
            )

        # Draw skeleton
        connections = [
            ("left_shoulder", "right_shoulder"),
            ("left_shoulder", "left_elbow"),
            ("right_shoulder", "right_elbow"),
            ("left_elbow", "left_wrist"),
            ("right_elbow", "right_wrist"),
            ("left_shoulder", "left_hip"),
            ("right_shoulder", "right_hip"),
            ("left_hip", "right_hip"),
            ("left_hip", "left_knee"),
            ("right_hip", "right_knee"),
            ("left_knee", "left_ankle"),
            ("right_knee", "right_ankle"),
        ]

        for start_name, end_name in connections:
            try:
                start_lm = self.get_landmark(landmarks, start_name)
                end_lm = self.get_landmark(landmarks, end_name)
                start_pt = (int(start_lm.x * w), int(start_lm.y * h))
                end_pt = (int(end_lm.x * w), int(end_lm.y * h))
                cv2.line(debug_image, start_pt, end_pt, (0, 255, 255), 2)
            except PoseExtractionError:
                pass

        # Display measurements
        if measurements:
            y_offset = 30
            for key, value in list(measurements.items())[:5]:  # Show first 5
                text = f"{key}: {value:.3f}"
                cv2.putText(
                    debug_image,
                    text,
                    (10, y_offset),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (255, 255, 255),
                    1,
                )
                y_offset += 20

        return debug_image


def extract_measurements_from_file(
    image_path: Path,
    scale_factor_cm_per_pixel: Optional[float] = None,
    save_debug: bool = False,
    debug_output_path: Optional[Path] = None,
) -> Tuple[List[Landmark], Dict[str, float]]:
    """
    Convenience function to extract measurements from image file.

    Args:
        image_path: Path to image file
        scale_factor_cm_per_pixel: Optional scale factor from ArUco calibration
        save_debug: Whether to save debug visualization
        debug_output_path: Path for debug image

    Returns:
        Tuple of (landmarks, measurements)
    """
    extractor = PoseExtractor()

    image = cv2.imread(str(image_path))
    if image is None:
        raise PoseExtractionError(f"Could not load image: {image_path}")

    landmarks = extractor.extract_landmarks(image)
    measurements = extractor.calculate_measurements(
        landmarks,
        scale_factor_cm_per_pixel=scale_factor_cm_per_pixel,
        image_height=image.shape[0],
    )

    if save_debug:
        debug_image = extractor.draw_pose_debug(image, landmarks, measurements)
        if debug_output_path:
            cv2.imwrite(str(debug_output_path), debug_image)
        else:
            debug_path = (
                image_path.parent / f"{image_path.stem}_pose_debug{image_path.suffix}"
            )
            cv2.imwrite(str(debug_path), debug_image)

    return landmarks, measurements


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="MediaPipe pose extraction")
    parser.add_argument("image", type=Path, help="Input image file")
    parser.add_argument(
        "--scale", type=float, help="Scale factor from ArUco (cm/pixel)"
    )
    parser.add_argument("--debug", action="store_true", help="Save debug visualization")

    args = parser.parse_args()

    try:
        landmarks, measurements = extract_measurements_from_file(
            args.image, scale_factor_cm_per_pixel=args.scale, save_debug=args.debug
        )

        print(f"\nExtracted {len(landmarks)} landmarks")
        print("\nKey Landmarks:")
        for lm in landmarks[11:17]:  # Shoulders, elbows, wrists
            print(
                f"  {lm.name}: ({lm.x:.3f}, {lm.y:.3f}, {lm.z:.3f}) vis={lm.visibility:.2f}"
            )

        print("\nMeasurements:")
        for key, value in measurements.items():
            print(f"  {key}: {value:.3f}")

    except PoseExtractionError as e:
        print(f"Error: {e}")
        exit(1)
