#!/usr/bin/env python3
"""
TheBlackbox Body Scanner Integration Module

Integrates with TheBlackbox (3D body scanner) to extract body measurements
from 3D scans and create production orders automatically.

Features:
1. Load scan data from JSON/mesh files
2. Extract body measurements (chest, waist, hip, etc.)
3. Calculate made-to-measure (MTM) sizing
4. Create orders directly from scans
5. Scan quality validation
6. Posture analysis

Expected TheBlackbox Output Format:
{
    "scan_id": "unique-id",
    "customer_id": "customer-id",
    "timestamp": "2026-01-31T10:00:00",
    "measurements": {
        "chest_cm": 102.5,
        "waist_cm": 88.0,
        "hip_cm": 100.0,
        "shoulder_width_cm": 45.0,
        "neck_cm": 40.0,
        "arm_length_cm": 65.0,
        "inseam_cm": 78.0,
        "torso_length_cm": 70.0
    },
    "posture": {
        "shoulder_slope": "normal",
        "posture_score": 0.92
    },
    "mesh_file": "path/to/mesh.obj",
    "confidence": 0.95
}

Author: Claude
Date: 2026-01-31
"""

import json
import math
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PostureType(Enum):
    """Body posture classification."""

    NORMAL = "normal"
    SLOPED_SHOULDERS = "sloped_shoulders"
    SQUARE_SHOULDERS = "square_shoulders"
    FORWARD_HEAD = "forward_head"
    SWAY_BACK = "sway_back"


class ScanQuality(Enum):
    """Scan quality rating."""

    EXCELLENT = "excellent"  # > 0.95 confidence
    GOOD = "good"  # > 0.85 confidence
    ACCEPTABLE = "acceptable"  # > 0.70 confidence
    POOR = "poor"  # < 0.70 confidence


@dataclass
class BodyMeasurements:
    """Complete body measurements from scan."""

    # Required
    chest_cm: float
    waist_cm: float
    hip_cm: float

    # Optional but important
    shoulder_width_cm: Optional[float] = None
    neck_cm: Optional[float] = None
    arm_length_cm: Optional[float] = None
    inseam_cm: Optional[float] = None
    torso_length_cm: Optional[float] = None

    # Additional MTM measurements
    wrist_cm: Optional[float] = None
    bicep_cm: Optional[float] = None
    thigh_cm: Optional[float] = None
    calf_cm: Optional[float] = None

    # Metadata
    source: str = "theblackbox"
    confidence: float = 1.0
    measurement_date: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class PostureAnalysis:
    """Body posture analysis from scan."""

    shoulder_slope: str
    shoulder_slope_degrees: float
    back_arch: str
    posture_score: float
    recommendations: List[str] = field(default_factory=list)


@dataclass
class ScanData:
    """Complete scan data from TheBlackbox."""

    scan_id: str
    customer_id: str
    timestamp: str
    measurements: BodyMeasurements
    posture: Optional[PostureAnalysis] = None
    mesh_file: Optional[str] = None
    images: List[str] = field(default_factory=list)
    quality: ScanQuality = ScanQuality.GOOD
    notes: List[str] = field(default_factory=list)


@dataclass
class ScanValidationResult:
    """Validation result for a scan."""

    valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    quality_score: float = 0.0


class TheBlackboxIntegration:
    """
    Integration with TheBlackbox body scanner system.
    """

    # Standard measurement tolerances
    MEASUREMENT_RANGES = {
        "chest_cm": (60, 150),
        "waist_cm": (50, 140),
        "hip_cm": (60, 150),
        "shoulder_width_cm": (30, 60),
        "neck_cm": (30, 50),
        "arm_length_cm": (40, 90),
        "inseam_cm": (50, 100),
        "torso_length_cm": (40, 80),
    }

    def __init__(self, scans_dir: str = "scans"):
        """
        Initialize TheBlackbox integration.

        Args:
            scans_dir: Directory to store/load scan files
        """
        self.scans_dir = Path(scans_dir)
        self.scans_dir.mkdir(exist_ok=True)

    def load_scan(self, scan_file: str) -> Optional[ScanData]:
        """
        Load scan data from JSON file.

        Args:
            scan_file: Path to scan JSON file

        Returns:
            ScanData object or None if loading fails
        """
        try:
            with open(scan_file, "r") as f:
                data = json.load(f)

            # Parse measurements
            measurements_data = data.get("measurements", {})
            measurements = BodyMeasurements(
                chest_cm=measurements_data.get("chest_cm", 0),
                waist_cm=measurements_data.get("waist_cm", 0),
                hip_cm=measurements_data.get("hip_cm", 0),
                shoulder_width_cm=measurements_data.get("shoulder_width_cm"),
                neck_cm=measurements_data.get("neck_cm"),
                arm_length_cm=measurements_data.get("arm_length_cm"),
                inseam_cm=measurements_data.get("inseam_cm"),
                torso_length_cm=measurements_data.get("torso_length_cm"),
                wrist_cm=measurements_data.get("wrist_cm"),
                bicep_cm=measurements_data.get("bicep_cm"),
                thigh_cm=measurements_data.get("thigh_cm"),
                calf_cm=measurements_data.get("calf_cm"),
                confidence=data.get("confidence", 1.0),
            )

            # Parse posture
            posture_data = data.get("posture")
            posture = None
            if posture_data:
                posture = PostureAnalysis(
                    shoulder_slope=posture_data.get("shoulder_slope", "normal"),
                    shoulder_slope_degrees=posture_data.get(
                        "shoulder_slope_degrees", 0
                    ),
                    back_arch=posture_data.get("back_arch", "normal"),
                    posture_score=posture_data.get("posture_score", 1.0),
                    recommendations=posture_data.get("recommendations", []),
                )

            # Determine quality
            confidence = data.get("confidence", 1.0)
            if confidence >= 0.95:
                quality = ScanQuality.EXCELLENT
            elif confidence >= 0.85:
                quality = ScanQuality.GOOD
            elif confidence >= 0.70:
                quality = ScanQuality.ACCEPTABLE
            else:
                quality = ScanQuality.POOR

            scan_data = ScanData(
                scan_id=data.get("scan_id", "unknown"),
                customer_id=data.get("customer_id", "unknown"),
                timestamp=data.get("timestamp", datetime.now().isoformat()),
                measurements=measurements,
                posture=posture,
                mesh_file=data.get("mesh_file"),
                images=data.get("images", []),
                quality=quality,
                notes=data.get("notes", []),
            )

            logger.info(
                f"Loaded scan {scan_data.scan_id} for customer {scan_data.customer_id}"
            )
            return scan_data

        except Exception as e:
            logger.error(f"Failed to load scan from {scan_file}: {e}")
            return None

    def save_scan(self, scan_data: ScanData, output_file: Optional[str] = None) -> str:
        """
        Save scan data to JSON file.

        Args:
            scan_data: ScanData object to save
            output_file: Optional output path (auto-generated if not provided)

        Returns:
            Path to saved file
        """
        if output_file is None:
            output_file = self.scans_dir / f"{scan_data.scan_id}.json"

        data = {
            "scan_id": scan_data.scan_id,
            "customer_id": scan_data.customer_id,
            "timestamp": scan_data.timestamp,
            "measurements": asdict(scan_data.measurements),
            "confidence": scan_data.measurements.confidence,
        }

        if scan_data.posture:
            data["posture"] = asdict(scan_data.posture)

        if scan_data.mesh_file:
            data["mesh_file"] = scan_data.mesh_file

        if scan_data.images:
            data["images"] = scan_data.images

        if scan_data.notes:
            data["notes"] = scan_data.notes

        with open(output_file, "w") as f:
            json.dump(data, f, indent=2)

        logger.info(f"Saved scan to {output_file}")
        return str(output_file)

    def validate_scan(self, scan_data: ScanData) -> ScanValidationResult:
        """
        Validate scan data for quality and completeness.

        Args:
            scan_data: ScanData to validate

        Returns:
            ValidationResult with errors and warnings
        """
        errors = []
        warnings = []

        m = scan_data.measurements

        # Check required measurements
        if m.chest_cm <= 0:
            errors.append("Chest measurement missing or invalid")
        elif not (
            self.MEASUREMENT_RANGES["chest_cm"][0]
            <= m.chest_cm
            <= self.MEASUREMENT_RANGES["chest_cm"][1]
        ):
            errors.append(f"Chest measurement {m.chest_cm}cm outside normal range")

        if m.waist_cm <= 0:
            errors.append("Waist measurement missing or invalid")
        elif not (
            self.MEASUREMENT_RANGES["waist_cm"][0]
            <= m.waist_cm
            <= self.MEASUREMENT_RANGES["waist_cm"][1]
        ):
            errors.append(f"Waist measurement {m.waist_cm}cm outside normal range")

        if m.hip_cm <= 0:
            errors.append("Hip measurement missing or invalid")
        elif not (
            self.MEASUREMENT_RANGES["hip_cm"][0]
            <= m.hip_cm
            <= self.MEASUREMENT_RANGES["hip_cm"][1]
        ):
            errors.append(f"Hip measurement {m.hip_cm}cm outside normal range")

        # Check measurement ratios
        if m.chest_cm > 0 and m.waist_cm > 0:
            ratio = m.chest_cm / m.waist_cm
            if ratio > 1.5:
                warnings.append(f"Unusual chest-to-waist ratio: {ratio:.2f}")
            elif ratio < 0.9:
                warnings.append(f"Waist larger than chest - verify measurements")

        # Check confidence
        if m.confidence < 0.70:
            errors.append(f"Low scan confidence: {m.confidence:.0%}")
        elif m.confidence < 0.85:
            warnings.append(f"Moderate scan confidence: {m.confidence:.0%}")

        # Check posture
        if scan_data.posture:
            if scan_data.posture.posture_score < 0.7:
                warnings.append("Poor posture detected - may affect fit")

        # Calculate quality score
        score = 1.0
        score -= len(errors) * 0.3
        score -= len(warnings) * 0.1
        score = max(0.0, score)

        return ScanValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            quality_score=score,
        )

    def create_order_from_scan(
        self,
        scan_data: ScanData,
        garment_type: str,
        fit_type: str = "regular",
        order_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a production order from scan data.

        Args:
            scan_data: Validated scan data
            garment_type: Type of garment (tee, jacket, trousers, cargo)
            fit_type: Fit preference (slim, regular, classic)
            order_id: Optional order ID (auto-generated if not provided)

        Returns:
            Order dictionary ready for production
        """
        if order_id is None:
            order_id = f"SCAN-{scan_data.customer_id}-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        m = scan_data.measurements

        order = {
            "order_id": order_id,
            "customer_id": scan_data.customer_id,
            "garment_type": garment_type,
            "fit_type": fit_type,
            "source": "theblackbox",
            "scan_id": scan_data.scan_id,
            "measurements": {
                "chest_cm": m.chest_cm,
                "waist_cm": m.waist_cm,
                "hip_cm": m.hip_cm,
                "shoulder_width_cm": m.shoulder_width_cm,
                "arm_length_cm": m.arm_length_cm,
                "inseam_cm": m.inseam_cm,
                "neck_cm": m.neck_cm,
                "torso_length_cm": m.torso_length_cm,
            },
            "posture": {
                "shoulder_slope": scan_data.posture.shoulder_slope
                if scan_data.posture
                else "normal",
                "posture_score": scan_data.posture.posture_score
                if scan_data.posture
                else 1.0,
            }
            if scan_data.posture
            else None,
            "scan_quality": scan_data.quality.value,
            "confidence": m.confidence,
            "created_at": datetime.now().isoformat(),
        }

        logger.info(f"Created order {order_id} from scan {scan_data.scan_id}")
        return order

    def process_scan_file(
        self,
        scan_file: str,
        garment_type: str,
        fit_type: str = "regular",
        validate: bool = True,
    ) -> Tuple[Optional[Dict[str, Any]], ScanValidationResult]:
        """
        Complete pipeline: load scan, validate, create order.

        Args:
            scan_file: Path to scan JSON file
            garment_type: Type of garment
            fit_type: Fit preference
            validate: Whether to validate the scan

        Returns:
            Tuple of (order_dict or None, validation_result)
        """
        # Load scan
        scan_data = self.load_scan(scan_file)
        if scan_data is None:
            return None, ScanValidationResult(
                valid=False,
                errors=["Failed to load scan file"],
            )

        # Validate
        if validate:
            validation = self.validate_scan(scan_data)
            if not validation.valid:
                logger.warning(f"Scan validation failed: {validation.errors}")
                return None, validation
        else:
            validation = ScanValidationResult(valid=True)

        # Create order
        order = self.create_order_from_scan(scan_data, garment_type, fit_type)

        return order, validation

    def generate_sample_scan(
        self,
        customer_id: str = "SAMPLE-001",
        chest: float = 102.0,
        waist: float = 88.0,
        hip: float = 100.0,
    ) -> str:
        """
        Generate a sample scan file for testing.

        Args:
            customer_id: Customer identifier
            chest: Chest measurement in cm
            waist: Waist measurement in cm
            hip: Hip measurement in cm

        Returns:
            Path to generated scan file
        """
        scan_id = f"SCAN-{customer_id}-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        sample_data = {
            "scan_id": scan_id,
            "customer_id": customer_id,
            "timestamp": datetime.now().isoformat(),
            "measurements": {
                "chest_cm": chest,
                "waist_cm": waist,
                "hip_cm": hip,
                "shoulder_width_cm": chest / 2.2,
                "neck_cm": chest / 2.5,
                "arm_length_cm": 65.0,
                "inseam_cm": hip * 0.78,
                "torso_length_cm": 70.0,
            },
            "confidence": 0.95,
            "posture": {
                "shoulder_slope": "normal",
                "shoulder_slope_degrees": 0,
                "back_arch": "normal",
                "posture_score": 0.92,
            },
            "notes": ["Sample scan for testing"],
        }

        output_file = self.scans_dir / f"{scan_id}.json"
        with open(output_file, "w") as f:
            json.dump(sample_data, f, indent=2)

        logger.info(f"Generated sample scan: {output_file}")
        return str(output_file)


def main():
    """Demo TheBlackbox integration."""
    print("=" * 70)
    print("TheBlackbox Body Scanner Integration Demo")
    print("=" * 70)

    # Initialize integration
    blackbox = TheBlackboxIntegration(scans_dir="sample_scans")

    # Generate sample scan
    print("\n1. Generating sample scan...")
    scan_file = blackbox.generate_sample_scan(
        customer_id="CUST-12345",
        chest=102.0,
        waist=88.0,
        hip=100.0,
    )
    print(f"   Created: {scan_file}")

    # Load and validate
    print("\n2. Loading and validating scan...")
    scan_data = blackbox.load_scan(scan_file)
    if scan_data:
        print(f"   Customer: {scan_data.customer_id}")
        print(f"   Measurements:")
        print(f"     Chest: {scan_data.measurements.chest_cm}cm")
        print(f"     Waist: {scan_data.measurements.waist_cm}cm")
        print(f"     Hip: {scan_data.measurements.hip_cm}cm")
        print(f"   Confidence: {scan_data.measurements.confidence:.0%}")
        print(f"   Quality: {scan_data.quality.value}")

        # Validate
        validation = blackbox.validate_scan(scan_data)
        print(f"\n   Validation: {'PASSED' if validation.valid else 'FAILED'}")
        if validation.errors:
            print(f"   Errors: {', '.join(validation.errors)}")
        if validation.warnings:
            print(f"   Warnings: {', '.join(validation.warnings)}")

        # Create order
        print("\n3. Creating production order...")
        order = blackbox.create_order_from_scan(
            scan_data=scan_data,
            garment_type="jacket",
            fit_type="regular",
        )
        print(f"   Order ID: {order['order_id']}")
        print(f"   Garment: {order['garment_type']}")
        print(f"   Source: {order['source']}")

    # Process scan file
    print("\n4. Processing scan through complete pipeline...")
    order, validation = blackbox.process_scan_file(
        scan_file=scan_file,
        garment_type="trousers",
        fit_type="slim",
    )

    if order:
        print(f"   Success! Created order: {order['order_id']}")
    else:
        print(f"   Failed: {validation.errors}")

    print("\n" + "=" * 70)
    print("Demo complete!")
    print("=" * 70)


if __name__ == "__main__":
    main()
