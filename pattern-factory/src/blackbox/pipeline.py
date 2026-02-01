"""
Black Box Pipeline - Main Integration Module

Orchestrates the complete scan-to-pattern pipeline:
1. ArUco calibration (scale detection)
2. MediaPipe pose extraction (33 landmarks)
3. M. Muller translation (pattern parameters)
4. DXF/HPGL generation (pattern output)

Based on BUILD RECOMMENDATIONS:
- HYBRID architecture (Apache 2.0 + Commercial)
- 6-8 week timeline to production
- Primary stack for SameDaySuits

Author: AI Agent
Date: January 2026
"""

import sys
from pathlib import Path
from typing import Dict, Optional, Tuple, List
from dataclasses import dataclass
import logging

# Setup logging
logger = logging.getLogger(__name__)

# Check for optional dependencies
_SCANNING_AVAILABLE = False
_PATTERNS_AVAILABLE = False

try:
    import cv2
    import mediapipe

    _SCANNING_AVAILABLE = True
except ImportError:
    logger.debug("Scanning dependencies not available")

try:
    import ezdxf

    _PATTERNS_AVAILABLE = True
except ImportError:
    logger.debug("Pattern generation dependencies not available")

# Import translation module (always available - no external deps)
from blackbox.translation.muller_translator import (
    MullerTranslator,
    MullerTranslationError,
    BodyMeasurements,
    FitType,
    FabricType,
    calculate_pattern_params,
)

# Conditional imports for scanning
if _SCANNING_AVAILABLE:
    from blackbox.scanning.aruco_calibration import (
        detect_aruco_marker,
        ArucoCalibrationError,
        pixels_to_cm,
    )
    from blackbox.scanning.pose_extraction import (
        PoseExtractor,
        PoseExtractionError,
        Landmark,
    )
else:
    # Placeholders for when scanning not available
    detect_aruco_marker = None
    ArucoCalibrationError = Exception
    pixels_to_cm = None
    PoseExtractor = None
    PoseExtractionError = Exception
    Landmark = None

# Conditional imports for pattern generation
if _PATTERNS_AVAILABLE:
    from blackbox.generation.dxf_generator import (
        DXFGenerator,
        generate_suit_patterns,
    )
else:
    DXFGenerator = None
    generate_suit_patterns = None


class PipelineError(Exception):
    """Raised when pipeline execution fails."""

    pass


@dataclass
class PipelineResult:
    """Result of pipeline execution."""

    success: bool
    measurements: Optional[Dict[str, float]]
    pattern_params: Optional[Dict[str, float]]
    dxf_path: Optional[Path]
    hpgl_path: Optional[Path]
    errors: List[str]
    processing_time_ms: float


class BlackBoxPipeline:
    """
    Complete scan-to-pattern pipeline for bespoke suits.

    Implements the HYBRID architecture from BUILD RECOMMENDATIONS:
    - Open source measurement (ArUco + MediaPipe)
    - Proprietary translation (M. Muller)
    - DXF/HPGL output (ezdxf)

    Note: Requires scanning dependencies for full functionality.
    Install with: pip install .[scanning]
    """

    def __init__(
        self,
        fit_type: FitType = FitType.REGULAR,
        fabric_type: FabricType = FabricType.WOOL,
        debug: bool = False,
    ):
        """
        Initialize pipeline.

        Args:
            fit_type: Slim, Regular, or Classic fit
            fabric_type: Fabric type for adjustments
            debug: Enable debug output

        Raises:
            PipelineError: If scanning dependencies not available
        """
        if not _SCANNING_AVAILABLE:
            raise PipelineError(
                "Scanning dependencies not available. "
                "Install with: pip install .[scanning]"
            )

        self.fit_type = fit_type
        self.fabric_type = fabric_type
        self.debug = debug
        self.scanning_available = _SCANNING_AVAILABLE
        self.patterns_available = _PATTERNS_AVAILABLE

        # Initialize components
        self.pose_extractor = PoseExtractor()
        self.muller_translator = MullerTranslator(fit_type, fabric_type)

        logger.info(f"Pipeline initialized: {fit_type.value} fit, {fabric_type.value}")
        if not _PATTERNS_AVAILABLE:
            logger.warning(
                "Pattern generation not available - install with pip install .[patterns]"
            )

    def process_image(
        self,
        image_path: Path,
        aruco_marker_id: int = 0,
        aruco_size_cm: float = 5.0,
        output_dir: Optional[Path] = None,
    ) -> PipelineResult:
        """
        Process single image through complete pipeline.

        Args:
            image_path: Path to input image
            aruco_marker_id: Expected ArUco marker ID
            aruco_size_cm: Physical size of ArUco marker
            output_dir: Directory for output files

        Returns:
            PipelineResult with measurements, patterns, and output paths
        """
        import time
        import cv2

        start_time = time.time()
        errors = []

        try:
            # Load image
            image = cv2.imread(str(image_path))
            if image is None:
                raise PipelineError(f"Could not load image: {image_path}")

            logger.info(f"Processing image: {image_path}")

            # Step 1: ArUco calibration
            logger.info("Step 1: ArUco calibration...")
            try:
                scale_factor, corners = detect_aruco_marker(
                    image, marker_id=aruco_marker_id, physical_size_cm=aruco_size_cm
                )
                logger.info(f"Scale factor: {scale_factor:.6f} cm/px")
            except ArucoCalibrationError as e:
                errors.append(f"ArUco calibration failed: {e}")
                scale_factor = None
                if self.debug:
                    logger.warning("Proceeding without scale calibration")

            # Step 2: MediaPipe pose extraction
            logger.info("Step 2: Pose extraction...")
            try:
                landmarks = self.pose_extractor.extract_landmarks(image)
                measurements = self.pose_extractor.calculate_measurements(
                    landmarks,
                    scale_factor_cm_per_pixel=scale_factor,
                    image_height=image.shape[0],
                )
                logger.info(f"Extracted {len(measurements)} measurements")
            except PoseExtractionError as e:
                errors.append(f"Pose extraction failed: {e}")
                raise PipelineError("Cannot proceed without pose detection")

            # Step 3: M. Muller translation
            logger.info("Step 3: M. Muller translation...")
            try:
                # Convert measurements to body measurements format
                body_measurements = self._landmarks_to_body_measurements(
                    landmarks, measurements, scale_factor, image.shape[0]
                )

                pattern_params = self.muller_translator.translate_measurements(
                    body_measurements
                )
                pattern_dict = self.muller_translator.export_to_dict(pattern_params)
                logger.info("Pattern parameters calculated")
            except MullerTranslationError as e:
                errors.append(f"Translation failed: {e}")
                raise PipelineError("Cannot proceed without pattern parameters")

            # Step 4: DXF/HPGL generation
            logger.info("Step 4: Pattern generation...")
            dxf_path = None
            hpgl_path = None

            if output_dir:
                output_dir = Path(output_dir)
                output_dir.mkdir(parents=True, exist_ok=True)

                dxf_path = output_dir / f"{image_path.stem}_pattern.dxf"
                hpgl_path = output_dir / f"{image_path.stem}_pattern.plt"

                try:
                    generate_suit_patterns(pattern_dict, dxf_path, hpgl_path)
                    logger.info(f"Patterns saved: DXF={dxf_path}, HPGL={hpgl_path}")
                except Exception as e:
                    errors.append(f"Pattern generation failed: {e}")

            # Calculate processing time
            processing_time = (time.time() - start_time) * 1000

            return PipelineResult(
                success=len(errors) == 0,
                measurements=measurements,
                pattern_params=pattern_dict,
                dxf_path=dxf_path,
                hpgl_path=hpgl_path,
                errors=errors,
                processing_time_ms=processing_time,
            )

        except Exception as e:
            processing_time = (time.time() - start_time) * 1000
            errors.append(f"Pipeline error: {e}")

            return PipelineResult(
                success=False,
                measurements=None,
                pattern_params=None,
                dxf_path=None,
                hpgl_path=None,
                errors=errors,
                processing_time_ms=processing_time,
            )

    def _landmarks_to_body_measurements(
        self,
        landmarks: List[Landmark],
        measurements: Dict[str, float],
        scale_factor: Optional[float],
        image_height: int,
    ) -> BodyMeasurements:
        """Convert landmarks and measurements to BodyMeasurements."""
        # Extract key measurements from pose extraction
        chest_girth = measurements.get("chest_girth_cm")
        waist_girth = measurements.get("waist_girth_cm")

        # If circumference measurements not available, estimate from widths
        if chest_girth is None and "shoulder_width_cm" in measurements:
            # Estimate chest from shoulder width (approximation)
            shoulder_width = measurements["shoulder_width_cm"]
            chest_girth = shoulder_width * 2.2  # Rough approximation

        if waist_girth is None and "torso_length_cm" in measurements:
            # Estimate from other measurements if available
            waist_girth = chest_girth * 0.85 if chest_girth else 90

        # Get other measurements
        hip_girth = (
            measurements.get("hip_width_cm", 0) * 2.2
            if "hip_width_cm" in measurements
            else None
        )

        return BodyMeasurements(
            chest=chest_girth,
            waist=waist_girth,
            hip=hip_girth,
            shoulder_width=measurements.get("shoulder_width_cm"),
            arm_length=measurements.get("arm_length_cm"),
            back_length=measurements.get("torso_length_cm"),
            bicep=measurements.get("bicep_cm"),
            source="mediapipe",
        )

    def batch_process(
        self, image_paths: List[Path], output_dir: Path, aruco_marker_id: int = 0
    ) -> List[PipelineResult]:
        """
        Process multiple images in batch.

        Args:
            image_paths: List of image paths to process
            output_dir: Directory for all outputs
            aruco_marker_id: Expected ArUco marker ID

        Returns:
            List of PipelineResult objects
        """
        results = []
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Batch processing {len(image_paths)} images...")

        for i, image_path in enumerate(image_paths, 1):
            logger.info(f"Processing {i}/{len(image_paths)}: {image_path.name}")

            result = self.process_image(
                image_path,
                aruco_marker_id=aruco_marker_id,
                output_dir=output_dir / image_path.stem,
            )

            results.append(result)

            if result.success:
                logger.info(f"  ✓ Success in {result.processing_time_ms:.0f}ms")
            else:
                logger.error(f"  ✗ Failed: {result.errors}")

        # Summary
        successful = sum(1 for r in results if r.success)
        logger.info(f"\nBatch complete: {successful}/{len(image_paths)} successful")

        return results


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Black Box Pipeline - Scan to Pattern")
    parser.add_argument("image", type=Path, help="Input image file")
    parser.add_argument(
        "--output", "-o", type=Path, default=Path("output"), help="Output directory"
    )
    parser.add_argument(
        "--fit",
        choices=["slim", "regular", "classic"],
        default="regular",
        help="Fit type",
    )
    parser.add_argument(
        "--fabric",
        choices=["wool", "cotton", "linen", "silk", "synthetic"],
        default="wool",
        help="Fabric type",
    )
    parser.add_argument("--marker-id", type=int, default=0, help="ArUco marker ID")
    parser.add_argument(
        "--marker-size", type=float, default=5.0, help="ArUco marker size in cm"
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug output")

    args = parser.parse_args()

    # Create pipeline
    pipeline = BlackBoxPipeline(
        fit_type=FitType(args.fit),
        fabric_type=FabricType(args.fabric),
        debug=args.debug,
    )

    # Process image
    result = pipeline.process_image(
        args.image,
        aruco_marker_id=args.marker_id,
        aruco_size_cm=args.marker_size,
        output_dir=args.output,
    )

    # Print results
    print("\n" + "=" * 60)
    if result.success:
        print("✓ PIPELINE SUCCESSFUL")
        print(f"Processing time: {result.processing_time_ms:.0f}ms")
        print(f"\nMeasurements:")
        for key, value in list(result.measurements.items())[:5]:
            print(f"  {key}: {value:.2f}")
        print(f"\nPattern params:")
        for key, value in list(result.pattern_params.items())[:5]:
            print(f"  {key}: {value}")
        print(f"\nOutput files:")
        print(f"  DXF: {result.dxf_path}")
        print(f"  HPGL: {result.hpgl_path}")
    else:
        print("✗ PIPELINE FAILED")
        print("Errors:")
        for error in result.errors:
            print(f"  - {error}")
    print("=" * 60)


if __name__ == "__main__":
    main()
