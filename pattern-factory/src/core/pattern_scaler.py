#!/usr/bin/env python3
"""
Pattern Scaler: Scale patterns based on customer measurements

This module handles:
1. Size selection based on measurements
2. Scale factor calculation
3. Geometry transformation for custom fit

The PDS templates contain graded sizes (XS-4XL). We can:
- Select the closest base size
- Scale from base size to exact measurements
- Interpolate between sizes for best fit

Author: Claude
Date: 2026-01-30
"""

import math
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum


class GarmentType(Enum):
    """Garment types with different measurement priorities."""

    TOP = "top"  # Tee, shirt, jacket - chest is primary
    BOTTOM = "bottom"  # Trousers, pants - waist/hip is primary
    DRESS = "dress"  # Full length - multiple measurements


@dataclass
class SizeChart:
    """Standard size chart for a garment type."""

    garment_type: GarmentType
    sizes: Dict[str, Dict[str, float]]  # size_name -> {measurement: value}


# Standard size charts (body measurements in cm)
# These are typical ready-to-wear sizes
SIZE_CHARTS = {
    GarmentType.TOP: SizeChart(
        garment_type=GarmentType.TOP,
        sizes={
            "XS": {"chest": 86, "waist": 71, "hip": 89, "shoulder": 42},
            "Small": {"chest": 91, "waist": 76, "hip": 94, "shoulder": 44},
            "Medium": {"chest": 97, "waist": 81, "hip": 99, "shoulder": 46},
            "Large": {"chest": 102, "waist": 86, "hip": 104, "shoulder": 48},
            "XL": {"chest": 107, "waist": 91, "hip": 109, "shoulder": 50},
            "2XL": {"chest": 112, "waist": 97, "hip": 114, "shoulder": 52},
            "3XL": {"chest": 119, "waist": 104, "hip": 119, "shoulder": 54},
            "4XL": {"chest": 127, "waist": 112, "hip": 127, "shoulder": 56},
        },
    ),
    GarmentType.BOTTOM: SizeChart(
        garment_type=GarmentType.BOTTOM,
        sizes={
            "XS": {"waist": 71, "hip": 89, "inseam": 76, "thigh": 54},
            "Small": {"waist": 76, "hip": 94, "inseam": 79, "thigh": 56},
            "Medium": {"waist": 81, "hip": 99, "inseam": 81, "thigh": 58},
            "Large": {"waist": 86, "hip": 104, "inseam": 81, "thigh": 60},
            "XL": {"waist": 91, "hip": 109, "inseam": 81, "thigh": 62},
            "2XL": {"waist": 97, "hip": 114, "inseam": 81, "thigh": 64},
            "3XL": {"waist": 104, "hip": 119, "inseam": 81, "thigh": 66},
            "4XL": {"waist": 112, "hip": 127, "inseam": 81, "thigh": 68},
        },
    ),
}


@dataclass
class ScaleResult:
    """Result of size selection and scaling calculation."""

    base_size: str
    scale_x: float  # Horizontal scale factor (width)
    scale_y: float  # Vertical scale factor (height/length)
    size_match_quality: float  # 0-1, how well the size matches
    interpolated: bool  # True if interpolated between sizes
    notes: List[str]


def find_best_size(
    measurements: Dict[str, float],
    garment_type: GarmentType,
    primary_measurement: str = "chest",
) -> Tuple[str, float]:
    """
    Find the best matching standard size.

    Args:
        measurements: Customer measurements {name: value_cm}
        garment_type: Type of garment
        primary_measurement: Primary measurement to match (chest, waist, etc.)

    Returns:
        (size_name, match_quality)
    """
    chart = SIZE_CHARTS.get(garment_type)
    if not chart:
        return "Medium", 0.5  # Default fallback

    customer_value = measurements.get(primary_measurement)
    if not customer_value:
        return "Medium", 0.5

    best_size = "Medium"
    best_diff = float("inf")

    for size_name, size_measurements in chart.sizes.items():
        size_value = size_measurements.get(primary_measurement)
        if size_value:
            diff = abs(customer_value - size_value)
            if diff < best_diff:
                best_diff = diff
                best_size = size_name

    # Calculate match quality (1.0 = exact, 0.0 = very far)
    # Assume ±10cm is the acceptable range
    match_quality = max(0, 1 - (best_diff / 10))

    return best_size, match_quality


def calculate_scale_factors(
    customer_measurements: Dict[str, float],
    base_size_measurements: Dict[str, float],
    garment_type: GarmentType,
) -> Tuple[float, float]:
    """
    Calculate scale factors to transform from base size to customer size.

    For tops: chest controls width, torso_length controls height
    For bottoms: hip controls width, inseam controls height

    Returns:
        (scale_x, scale_y)
    """
    if garment_type == GarmentType.TOP:
        # Width from chest
        base_chest = base_size_measurements.get("chest", 97)
        customer_chest = customer_measurements.get("chest", base_chest)
        scale_x = customer_chest / base_chest

        # Height from torso length (if available) or slight proportional
        base_shoulder = base_size_measurements.get("shoulder", 46)
        customer_shoulder = customer_measurements.get("shoulder", base_shoulder)
        scale_y = customer_shoulder / base_shoulder if customer_shoulder else 1.0

    elif garment_type == GarmentType.BOTTOM:
        # Width from hip
        base_hip = base_size_measurements.get("hip", 99)
        customer_hip = customer_measurements.get("hip", base_hip)
        scale_x = customer_hip / base_hip

        # Height from inseam
        base_inseam = base_size_measurements.get("inseam", 81)
        customer_inseam = customer_measurements.get("inseam", base_inseam)
        scale_y = customer_inseam / base_inseam if customer_inseam else 1.0

    else:
        scale_x = scale_y = 1.0

    return scale_x, scale_y


def calculate_pattern_scale(
    customer_measurements: Dict[str, float],
    garment_type: GarmentType,
    base_size: Optional[str] = None,
) -> ScaleResult:
    """
    Calculate how to scale a pattern for a customer.

    Args:
        customer_measurements: Customer body measurements in cm
            - chest: Chest circumference
            - waist: Waist circumference
            - hip: Hip circumference
            - shoulder: Shoulder width (optional)
            - inseam: Inside leg length (optional)
        garment_type: Type of garment (TOP, BOTTOM)
        base_size: Force a specific base size (optional)

    Returns:
        ScaleResult with base size and scale factors
    """
    notes = []

    # Determine primary measurement based on garment type
    if garment_type == GarmentType.TOP:
        primary = "chest"
    else:
        primary = "hip"

    # Find best base size
    if base_size:
        selected_size = base_size
        match_quality = 0.8  # Assume reasonable if manually selected
    else:
        selected_size, match_quality = find_best_size(
            customer_measurements, garment_type, primary
        )

    notes.append(f"Selected base size: {selected_size} (match: {match_quality:.0%})")

    # Get base size measurements
    chart = SIZE_CHARTS.get(garment_type)
    if chart and selected_size in chart.sizes:
        base_measurements = chart.sizes[selected_size]
    else:
        # Fallback to Medium
        base_measurements = SIZE_CHARTS[GarmentType.TOP].sizes["Medium"]
        notes.append("Warning: Using fallback Medium size measurements")

    # Calculate scale factors
    scale_x, scale_y = calculate_scale_factors(
        customer_measurements, base_measurements, garment_type
    )

    # Clamp to reasonable range (0.8x to 1.3x)
    original_scale_x, original_scale_y = scale_x, scale_y
    scale_x = max(0.8, min(1.3, scale_x))
    scale_y = max(0.8, min(1.3, scale_y))

    if scale_x != original_scale_x:
        notes.append(f"Scale X clamped from {original_scale_x:.2f} to {scale_x:.2f}")
    if scale_y != original_scale_y:
        notes.append(f"Scale Y clamped from {original_scale_y:.2f} to {scale_y:.2f}")

    return ScaleResult(
        base_size=selected_size,
        scale_x=scale_x,
        scale_y=scale_y,
        size_match_quality=match_quality,
        interpolated=False,
        notes=notes,
    )


def scale_points(
    points: List[Tuple[float, float]],
    scale_x: float,
    scale_y: float,
    center: Optional[Tuple[float, float]] = None,
) -> List[Tuple[float, float]]:
    """
    Scale a list of points around a center point.

    Args:
        points: List of (x, y) coordinates
        scale_x: Horizontal scale factor
        scale_y: Vertical scale factor
        center: Center point for scaling (uses centroid if None)

    Returns:
        Scaled points
    """
    if not points:
        return []

    # Calculate centroid if center not provided
    if center is None:
        cx = sum(p[0] for p in points) / len(points)
        cy = sum(p[1] for p in points) / len(points)
    else:
        cx, cy = center

    # Scale around center
    scaled = []
    for x, y in points:
        new_x = cx + (x - cx) * scale_x
        new_y = cy + (y - cy) * scale_y
        scaled.append((new_x, new_y))

    return scaled


def scale_contours(
    contours,  # List of Contour objects
    scale_x: float,
    scale_y: float,
):
    """
    Scale a list of Contour objects.

    This modifies contours in place and returns them.
    """
    from production_pipeline import Contour, Point

    scaled_contours = []

    for contour in contours:
        # Extract points as tuples
        points = [(p.x, p.y) for p in contour.points]

        # Scale
        scaled_points = scale_points(points, scale_x, scale_y)

        # Create new contour with scaled points
        new_points = [Point(x=x, y=y) for x, y in scaled_points]
        scaled_contours.append(
            Contour(
                points=new_points,
                closed=contour.closed,
                fill_color=contour.fill_color,
                stroke_color=contour.stroke_color,
            )
        )

    return scaled_contours


# Mapping from API garment types to scaler garment types
GARMENT_TYPE_MAP = {
    "tee": GarmentType.TOP,
    "shirt": GarmentType.TOP,
    "jacket": GarmentType.TOP,
    "trousers": GarmentType.BOTTOM,
    "cargo": GarmentType.BOTTOM,
    "pants": GarmentType.BOTTOM,
}


def get_garment_type(garment_name: str) -> GarmentType:
    """Get garment type from name."""
    return GARMENT_TYPE_MAP.get(garment_name.lower(), GarmentType.TOP)


if __name__ == "__main__":
    # Test scaling calculations
    print("Pattern Scaler Test")
    print("=" * 60)

    # Test customer measurements
    customer = {
        "chest": 108,  # Larger than XL
        "waist": 92,
        "hip": 105,
        "shoulder": 49,
    }

    print(f"\nCustomer measurements:")
    for k, v in customer.items():
        print(f"  {k}: {v} cm")

    # Calculate scale for a top
    result = calculate_pattern_scale(customer, GarmentType.TOP)

    print(f"\nScale Result:")
    print(f"  Base size: {result.base_size}")
    print(f"  Scale X: {result.scale_x:.3f}")
    print(f"  Scale Y: {result.scale_y:.3f}")
    print(f"  Match quality: {result.size_match_quality:.0%}")
    print(f"\nNotes:")
    for note in result.notes:
        print(f"  - {note}")

    # Test point scaling
    print(f"\nPoint scaling test:")
    test_points = [(0, 0), (100, 0), (100, 50), (0, 50)]
    scaled = scale_points(test_points, result.scale_x, result.scale_y)
    print(f"  Original: {test_points}")
    print(f"  Scaled:   {[(round(x, 1), round(y, 1)) for x, y in scaled]}")
