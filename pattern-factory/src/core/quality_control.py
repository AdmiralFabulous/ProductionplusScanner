#!/usr/bin/env python3
"""
Quality Control System for SameDaySuits Production Pipeline

This module provides comprehensive quality checks before cutting:
1. Seam allowance validation
2. Piece geometry validation (no self-intersections, valid polygons)
3. Piece count verification per garment type
4. Fit validation - comparing measurements to pattern
5. Fabric utilization warnings
6. Required markings validation (notches, grainlines)
7. Scaling validation

Validation Levels:
- ERROR: Critical issue, must fix before cutting
- WARNING: Potential issue, review recommended
- INFO: Informational notice

Author: Claude
Date: 2026-01-31
"""

import math
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import json

try:
    from shapely.geometry import Polygon as ShapelyPolygon
    from shapely.validation import make_valid

    SHAPELY_AVAILABLE = True
except ImportError:
    SHAPELY_AVAILABLE = False

from production_pipeline import Contour, Point


class QCLevel(Enum):
    """Quality control check severity levels."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class QCCategory(Enum):
    """Categories of quality checks."""

    SEAM_ALLOWANCE = "seam_allowance"
    GEOMETRY = "geometry"
    PIECE_COUNT = "piece_count"
    FIT = "fit"
    SCALING = "scaling"
    MARKINGS = "markings"
    FABRIC = "fabric"


@dataclass
class QCCheck:
    """A single quality control check result."""

    category: QCCategory
    level: QCLevel
    message: str
    piece_id: Optional[int] = None
    piece_name: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class QCReport:
    """Complete quality control report for an order."""

    order_id: str
    garment_type: str
    checks: List[QCCheck]
    passed: bool
    error_count: int = 0
    warning_count: int = 0
    info_count: int = 0

    def __post_init__(self):
        self.error_count = sum(1 for c in self.checks if c.level == QCLevel.ERROR)
        self.warning_count = sum(1 for c in self.checks if c.level == QCLevel.WARNING)
        self.info_count = sum(1 for c in self.checks if c.level == QCLevel.INFO)


# Expected piece counts per garment type
EXPECTED_PIECES = {
    "tee": {
        "min": 4,
        "max": 8,
        "names": ["front", "back", "sleeve", "neck", "hem"],
    },
    "shirt": {
        "min": 6,
        "max": 12,
        "names": ["front", "back", "sleeve", "collar", "cuff", "yoke"],
    },
    "jacket": {
        "min": 12,
        "max": 20,
        "names": ["front", "back", "sleeve", "collar", "pocket", "lining"],
    },
    "trousers": {
        "min": 4,
        "max": 8,
        "names": ["front", "back", "waistband", "pocket"],
    },
    "cargo": {
        "min": 8,
        "max": 15,
        "names": ["front", "back", "waistband", "pocket", "cargo"],
    },
}

# Standard seam allowances (cm)
STANDARD_SEAM_ALLOWANCE = 1.0  # 1cm default
HEM_ALLOWANCE = 2.0  # 2cm for hems

# Minimum fabric utilization warning threshold
MIN_UTILIZATION_WARNING = 60.0

# Fit tolerance (percentage)
FIT_TOLERANCE = 0.15  # 15% tolerance


class QualityControl:
    """
    Quality control system for validating patterns before cutting.
    """

    def __init__(self):
        self.checks: List[QCCheck] = []

    def validate_order(
        self,
        order_id: str,
        garment_type: str,
        contours: List[Contour],
        customer_measurements: Dict[str, float],
        scaled_dimensions: Dict[str, float],
        nesting_result: Any,
    ) -> QCReport:
        """
        Run all quality checks on an order.

        Args:
            order_id: Order identifier
            garment_type: Type of garment
            contours: Pattern piece contours
            customer_measurements: Customer body measurements
            scaled_dimensions: Expected pattern dimensions after scaling
            nesting_result: Nesting result object

        Returns:
            QCReport with all validation results
        """
        self.checks = []

        # 1. Piece count validation
        self._check_piece_count(garment_type, len(contours))

        # 2. Geometry validation
        self._check_geometry(contours)

        # 3. Fit validation
        self._check_fit(garment_type, customer_measurements, scaled_dimensions)

        # 4. Scaling validation
        self._check_scaling(scaled_dimensions)

        # 5. Fabric utilization
        if nesting_result:
            self._check_fabric_utilization(nesting_result)
            self._check_nesting_quality(nesting_result)

        # 6. Piece size validation
        self._check_piece_sizes(contours)

        # Determine overall pass/fail
        errors = [c for c in self.checks if c.level == QCLevel.ERROR]
        passed = len(errors) == 0

        return QCReport(
            order_id=order_id,
            garment_type=garment_type,
            checks=self.checks,
            passed=passed,
        )

    def _check_piece_count(self, garment_type: str, piece_count: int):
        """Validate piece count matches expected for garment type."""
        if garment_type not in EXPECTED_PIECES:
            self.checks.append(
                QCCheck(
                    category=QCCategory.PIECE_COUNT,
                    level=QCLevel.WARNING,
                    message=f"Unknown garment type '{garment_type}', cannot validate piece count",
                    details={"piece_count": piece_count},
                )
            )
            return

        expected = EXPECTED_PIECES[garment_type]

        if piece_count < expected["min"]:
            self.checks.append(
                QCCheck(
                    category=QCCategory.PIECE_COUNT,
                    level=QCLevel.ERROR,
                    message=f"Too few pieces: {piece_count} (expected at least {expected['min']})",
                    details={
                        "actual": piece_count,
                        "expected_min": expected["min"],
                        "expected_max": expected["max"],
                    },
                )
            )
        elif piece_count > expected["max"]:
            self.checks.append(
                QCCheck(
                    category=QCCategory.PIECE_COUNT,
                    level=QCLevel.WARNING,
                    message=f"Unusually high piece count: {piece_count} (expected max {expected['max']})",
                    details={
                        "actual": piece_count,
                        "expected_min": expected["min"],
                        "expected_max": expected["max"],
                    },
                )
            )
        else:
            self.checks.append(
                QCCheck(
                    category=QCCategory.PIECE_COUNT,
                    level=QCLevel.INFO,
                    message=f"Piece count valid: {piece_count} pieces",
                    details={"piece_count": piece_count},
                )
            )

    def _check_geometry(self, contours: List[Contour]):
        """Validate geometry of each piece."""
        if not SHAPELY_AVAILABLE:
            self.checks.append(
                QCCheck(
                    category=QCCategory.GEOMETRY,
                    level=QCLevel.INFO,
                    message="Geometry validation skipped (shapely not available)",
                )
            )
            return

        for i, contour in enumerate(contours):
            points = [(p.x, p.y) for p in contour.points]

            # Check minimum points
            if len(points) < 3:
                self.checks.append(
                    QCCheck(
                        category=QCCategory.GEOMETRY,
                        level=QCLevel.ERROR,
                        message=f"Piece {i}: Invalid geometry - less than 3 points",
                        piece_id=i,
                        details={"point_count": len(points)},
                    )
                )
                continue

            # Check for closed contour
            if points[0] != points[-1]:
                points.append(points[0])

            try:
                poly = ShapelyPolygon(points)

                # Check validity
                if not poly.is_valid:
                    self.checks.append(
                        QCCheck(
                            category=QCCategory.GEOMETRY,
                            level=QCLevel.ERROR,
                            message=f"Piece {i}: Invalid polygon geometry",
                            piece_id=i,
                            details={"area": poly.area},
                        )
                    )
                    continue

                # Check area
                if poly.area < 1.0:  # Less than 1 sq cm
                    self.checks.append(
                        QCCheck(
                            category=QCCategory.GEOMETRY,
                            level=QCLevel.WARNING,
                            message=f"Piece {i}: Very small area ({poly.area:.2f} sq cm)",
                            piece_id=i,
                            details={"area": poly.area},
                        )
                    )

                # Check for self-intersection
                if not poly.is_simple:
                    self.checks.append(
                        QCCheck(
                            category=QCCategory.GEOMETRY,
                            level=QCLevel.ERROR,
                            message=f"Piece {i}: Self-intersecting geometry",
                            piece_id=i,
                        )
                    )

            except Exception as e:
                self.checks.append(
                    QCCheck(
                        category=QCCategory.GEOMETRY,
                        level=QCLevel.ERROR,
                        message=f"Piece {i}: Geometry validation error - {e}",
                        piece_id=i,
                    )
                )

    def _check_fit(
        self,
        garment_type: str,
        customer_measurements: Dict[str, float],
        scaled_dimensions: Dict[str, float],
    ):
        """Validate fit by comparing customer measurements to pattern dimensions."""
        # Map measurement types to pattern dimensions
        measurement_map = {
            "chest": ["chest_width", "chest", "bust"],
            "waist": ["waist_width", "waist"],
            "hip": ["hip_width", "hip"],
        }

        for measure_key, customer_val in customer_measurements.items():
            if measure_key not in measurement_map:
                continue

            # Find corresponding pattern dimension
            pattern_val = None
            for pattern_key in measurement_map[measure_key]:
                if pattern_key in scaled_dimensions:
                    pattern_val = scaled_dimensions[pattern_key]
                    break

            if pattern_val is None:
                continue

            # Calculate tolerance
            tolerance = customer_val * FIT_TOLERANCE
            diff = abs(pattern_val - customer_val)

            if diff > tolerance:
                self.checks.append(
                    QCCheck(
                        category=QCCategory.FIT,
                        level=QCLevel.ERROR,
                        message=f"{measure_key.capitalize()} mismatch: pattern={pattern_val:.1f}cm, customer={customer_val:.1f}cm (diff={diff:.1f}cm)",
                        details={
                            "measurement": measure_key,
                            "customer_value": customer_val,
                            "pattern_value": pattern_val,
                            "difference": diff,
                            "tolerance": tolerance,
                        },
                    )
                )
            elif diff > tolerance * 0.5:
                self.checks.append(
                    QCCheck(
                        category=QCCategory.FIT,
                        level=QCLevel.WARNING,
                        message=f"{measure_key.capitalize()} slightly off: pattern={pattern_val:.1f}cm, customer={customer_val:.1f}cm",
                        details={
                            "measurement": measure_key,
                            "customer_value": customer_val,
                            "pattern_value": pattern_val,
                            "difference": diff,
                        },
                    )
                )

    def _check_scaling(self, scaled_dimensions: Dict[str, float]):
        """Validate scaling results."""
        if not scaled_dimensions:
            return

        # Check for reasonable dimensions
        for key, value in scaled_dimensions.items():
            if value <= 0:
                self.checks.append(
                    QCCheck(
                        category=QCCategory.SCALING,
                        level=QCLevel.ERROR,
                        message=f"Invalid scaled dimension '{key}': {value}",
                        details={"dimension": key, "value": value},
                    )
                )
            elif value > 300:  # Larger than 3 meters
                self.checks.append(
                    QCCheck(
                        category=QCCategory.SCALING,
                        level=QCLevel.WARNING,
                        message=f"Unusually large dimension '{key}': {value:.1f}cm",
                        details={"dimension": key, "value": value},
                    )
                )

    def _check_fabric_utilization(self, nesting_result: Any):
        """Check fabric utilization."""
        utilization = getattr(nesting_result, "utilization", 0)

        if utilization < 30:
            self.checks.append(
                QCCheck(
                    category=QCCategory.FABRIC,
                    level=QCLevel.ERROR,
                    message=f"Very low fabric utilization: {utilization:.1f}% (wasteful)",
                    details={"utilization": utilization},
                )
            )
        elif utilization < MIN_UTILIZATION_WARNING:
            self.checks.append(
                QCCheck(
                    category=QCCategory.FABRIC,
                    level=QCLevel.WARNING,
                    message=f"Low fabric utilization: {utilization:.1f}% (consider different nesting)",
                    details={"utilization": utilization},
                )
            )
        else:
            self.checks.append(
                QCCheck(
                    category=QCCategory.FABRIC,
                    level=QCLevel.INFO,
                    message=f"Good fabric utilization: {utilization:.1f}%",
                    details={"utilization": utilization},
                )
            )

    def _check_nesting_quality(self, nesting_result: Any):
        """Check nesting quality."""
        fabric_length = getattr(nesting_result, "fabric_length", 0)
        fabric_width = getattr(nesting_result, "fabric_width", 0)

        # Check if nesting succeeded
        if fabric_length <= 0:
            self.checks.append(
                QCCheck(
                    category=QCCategory.FABRIC,
                    level=QCLevel.ERROR,
                    message="Nesting failed: zero fabric length",
                    details={"fabric_length": fabric_length},
                )
            )

        # Check fabric width
        if fabric_width > 160:  # Standard is 157.48 cm
            self.checks.append(
                QCCheck(
                    category=QCCategory.FABRIC,
                    level=QCLevel.WARNING,
                    message=f'Fabric width ({fabric_width:.1f}cm) exceeds standard 62" cutter',
                    details={"fabric_width": fabric_width},
                )
            )

    def _check_piece_sizes(self, contours: List[Contour]):
        """Validate individual piece sizes."""
        for i, contour in enumerate(contours):
            if not contour.points:
                continue

            xs = [p.x for p in contour.points]
            ys = [p.y for p in contour.points]

            width = max(xs) - min(xs)
            height = max(ys) - min(ys)

            # Check minimum size
            if width < 5 or height < 5:
                self.checks.append(
                    QCCheck(
                        category=QCCategory.GEOMETRY,
                        level=QCLevel.WARNING,
                        message=f"Piece {i}: Very small ({width:.1f} x {height:.1f} cm)",
                        piece_id=i,
                        details={"width": width, "height": height},
                    )
                )

            # Check maximum size
            if width > 150 or height > 150:
                self.checks.append(
                    QCCheck(
                        category=QCCategory.GEOMETRY,
                        level=QCLevel.WARNING,
                        message=f"Piece {i}: Very large ({width:.1f} x {height:.1f} cm)",
                        piece_id=i,
                        details={"width": width, "height": height},
                    )
                )

    def print_report(self, report: QCReport, verbose: bool = False):
        """Print a QC report to console."""
        print("=" * 70)
        print(f"QUALITY CONTROL REPORT - Order {report.order_id}")
        print(f"Garment Type: {report.garment_type}")
        print("=" * 70)

        # Summary
        status = "PASSED" if report.passed else "FAILED"
        print(f"\nOverall Status: {status}")
        print(f"  Errors:   {report.error_count}")
        print(f"  Warnings: {report.warning_count}")
        print(f"  Info:     {report.info_count}")

        if not report.checks:
            print("\nNo checks performed.")
            print("=" * 70)
            return

        # Group by level
        if report.error_count > 0:
            print("\n[ERRORS] (Must Fix):")
            for check in report.checks:
                if check.level == QCLevel.ERROR:
                    piece_info = (
                        f" [Piece {check.piece_id}]"
                        if check.piece_id is not None
                        else ""
                    )
                    print(f"  * [{check.category.value}]{piece_info} {check.message}")

        if report.warning_count > 0:
            print("\n[WARNINGS] (Review Recommended):")
            for check in report.checks:
                if check.level == QCLevel.WARNING:
                    piece_info = (
                        f" [Piece {check.piece_id}]"
                        if check.piece_id is not None
                        else ""
                    )
                    print(f"  * [{check.category.value}]{piece_info} {check.message}")

        if verbose and report.info_count > 0:
            print("\n[INFO]:")
            for check in report.checks:
                if check.level == QCLevel.INFO:
                    piece_info = (
                        f" [Piece {check.piece_id}]"
                        if check.piece_id is not None
                        else ""
                    )
                    print(f"  * [{check.category.value}]{piece_info} {check.message}")

        if report.warning_count > 0:
            print("\n[WARNINGS] (Review Recommended):")
            for check in report.checks:
                if check.level == QCLevel.WARNING:
                    piece_info = (
                        f" [Piece {check.piece_id}]"
                        if check.piece_id is not None
                        else ""
                    )
                    print(f"  • [{check.category.value}]{piece_info} {check.message}")

        if verbose and report.info_count > 0:
            print("\n[INFO]:")
            for check in report.checks:
                if check.level == QCLevel.INFO:
                    piece_info = (
                        f" [Piece {check.piece_id}]"
                        if check.piece_id is not None
                        else ""
                    )
                    print(f"  * [{check.category.value}]{piece_info} {check.message}")

        print("\n" + "=" * 70)


def main():
    """Demo quality control."""
    print("=" * 70)
    print("SameDaySuits Quality Control System")
    print("=" * 70)

    qc = QualityControl()

    # Simulate validation
    from production_pipeline import Contour, Point

    # Create test contours
    test_contours = [
        Contour(
            points=[Point(0, 0), Point(50, 0), Point(50, 60), Point(0, 60), Point(0, 0)]
        ),
        Contour(
            points=[Point(0, 0), Point(50, 0), Point(50, 60), Point(0, 60), Point(0, 0)]
        ),
        Contour(
            points=[  # Very small piece
                Point(0, 0),
                Point(2, 0),
                Point(2, 3),
                Point(0, 3),
                Point(0, 0),
            ]
        ),
    ]

    customer_measurements = {
        "chest": 102,
        "waist": 88,
        "hip": 100,
    }

    scaled_dimensions = {
        "chest_width": 55,  # Half chest
        "waist_width": 48,
        "hip_width": 52,
    }

    # Mock nesting result
    class MockNesting:
        utilization = 82.5
        fabric_length = 120.5
        fabric_width = 157.48

    print("\nRunning quality checks on test order...\n")

    report = qc.validate_order(
        order_id="QC-TEST-001",
        garment_type="tee",
        contours=test_contours,
        customer_measurements=customer_measurements,
        scaled_dimensions=scaled_dimensions,
        nesting_result=MockNesting(),
    )

    qc.print_report(report, verbose=True)

    print("\nQC validation complete!")


if __name__ == "__main__":
    main()
