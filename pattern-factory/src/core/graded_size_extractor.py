#!/usr/bin/env python3
"""
Graded Size Extractor: Extract size-specific dimensions from PDS files

PDS files contain graded sizes (XS-4XL) with GEOM_INFO for each piece/size.
This module extracts that information and provides scale factors to transform
from one size to another.

The actual SVG geometry in the MARKER section is rendered at a specific size
(usually the base size or all sizes overlaid). We use the GEOM_INFO dimensions
to calculate accurate scaling between sizes.

Author: Claude
Date: 2026-01-30
"""

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class SizeInfo:
    """Information about a specific size."""

    name: str
    size_x: float  # Width in cm
    size_y: float  # Height in cm
    area: float  # Area in sq cm
    perimeter: float  # Perimeter in cm


@dataclass
class PieceInfo:
    """Information about a pattern piece across all sizes."""

    name: str
    unique_id: str
    material: str
    sizes: Dict[str, SizeInfo]  # size_name -> SizeInfo


@dataclass
class GradedPattern:
    """Complete graded pattern information."""

    filename: str
    available_sizes: List[str]
    base_size: str
    pieces: Dict[str, PieceInfo]  # piece_name -> PieceInfo


def extract_graded_info(pds_path: Path) -> GradedPattern:
    """
    Extract graded size information from a PDS file.

    Args:
        pds_path: Path to PDS file

    Returns:
        GradedPattern with all size information
    """
    from production_pipeline import extract_xml_from_pds

    xml_content = extract_xml_from_pds(str(pds_path))
    root = ET.fromstring(xml_content)

    # Get available sizes
    sizes_elem = root.find(".//SIZES")
    num_sizes = (
        int(sizes_elem.text) if sizes_elem is not None and sizes_elem.text else 0
    )

    # Get size names from SIZES_TABLE
    available_sizes = []
    sizes_table = root.find(".//SIZES_TABLE")
    if sizes_table is not None:
        for size_elem in sizes_table.findall("SIZE"):
            name_elem = size_elem.find("NAME")
            if name_elem is not None and name_elem.text:
                available_sizes.append(name_elem.text)

    # Get base size
    base_size_elem = root.find(".//SIZES_TABLE/BASE_SIZE/NAME")
    base_size = (
        base_size_elem.text
        if base_size_elem is not None and base_size_elem.text
        else "Small"
    )

    # Extract piece information
    pieces = {}

    for piece_elem in root.findall("PIECE"):
        name_elem = piece_elem.find("NAME")
        if name_elem is None or not name_elem.text:
            continue

        piece_name = name_elem.text
        unique_id = ""
        material = ""

        # Get piece attributes
        uid_elem = piece_elem.find("UNIQUE_ID")
        if uid_elem is not None and uid_elem.text:
            unique_id = uid_elem.text

        mat_elem = piece_elem.find("MATERIAL")
        if mat_elem is not None and mat_elem.text:
            material = mat_elem.text

        # Extract size-specific info
        sizes_dict = {}

        for size_elem in piece_elem.findall("SIZE"):
            size_name_elem = size_elem.find("NAME")
            if size_name_elem is None or not size_name_elem.text:
                continue

            size_name = size_name_elem.text
            geom = size_elem.find("GEOM_INFO")

            if geom is not None:
                sizes_dict[size_name] = SizeInfo(
                    name=size_name,
                    size_x=float(geom.get("SIZE_X", 0)),
                    size_y=float(geom.get("SIZE_Y", 0)),
                    area=float(geom.get("AREA", 0)),
                    perimeter=float(geom.get("PERIMETER", 0)),
                )

        pieces[piece_name] = PieceInfo(
            name=piece_name,
            unique_id=unique_id,
            material=material,
            sizes=sizes_dict,
        )

    return GradedPattern(
        filename=pds_path.name,
        available_sizes=available_sizes,
        base_size=base_size,
        pieces=pieces,
    )


def get_size_scale_factors(
    pattern: GradedPattern,
    from_size: str,
    to_size: str,
) -> Dict[str, Tuple[float, float]]:
    """
    Calculate per-piece scale factors to transform from one size to another.

    Args:
        pattern: GradedPattern info
        from_size: Source size name
        to_size: Target size name

    Returns:
        Dict mapping piece_name -> (scale_x, scale_y)
    """
    scale_factors = {}

    for piece_name, piece_info in pattern.pieces.items():
        from_info = piece_info.sizes.get(from_size)
        to_info = piece_info.sizes.get(to_size)

        if from_info and to_info:
            scale_x = to_info.size_x / from_info.size_x if from_info.size_x > 0 else 1.0
            scale_y = to_info.size_y / from_info.size_y if from_info.size_y > 0 else 1.0
            scale_factors[piece_name] = (scale_x, scale_y)
        else:
            scale_factors[piece_name] = (1.0, 1.0)

    return scale_factors


def find_best_size(
    pattern: GradedPattern,
    customer_chest_cm: float,
    garment_type: str = "top",
) -> str:
    """
    Find the best matching size based on customer measurements.

    This uses a simple chest-to-pattern-width mapping.
    For a top, we assume the pattern width roughly corresponds to
    half the chest measurement (since patterns are usually half-body).

    Args:
        pattern: GradedPattern info
        customer_chest_cm: Customer chest circumference in cm
        garment_type: "top" or "bottom"

    Returns:
        Best matching size name
    """
    # For tops, main body piece width ≈ chest/4 (quarter of circumference)
    # Add ease (typically 4-8cm for regular fit)
    target_width = customer_chest_cm / 4 + 2  # cm, with some ease

    # Find a representative piece (Front, Back, or largest)
    rep_piece = None
    for name in ["Front", "Back", "P1", "Body"]:
        if name in pattern.pieces:
            rep_piece = pattern.pieces[name]
            break

    if rep_piece is None and pattern.pieces:
        rep_piece = list(pattern.pieces.values())[0]

    if rep_piece is None:
        return pattern.base_size

    # Find closest size
    best_size = pattern.base_size
    best_diff = float("inf")

    for size_name, size_info in rep_piece.sizes.items():
        diff = abs(size_info.size_x - target_width)
        if diff < best_diff:
            best_diff = diff
            best_size = size_name

    return best_size


def print_graded_info(pattern: GradedPattern):
    """Print graded pattern information in a readable format."""
    print(f"\n{'=' * 60}")
    print(f"Pattern: {pattern.filename}")
    print(f"{'=' * 60}")
    print(f"Available sizes: {', '.join(pattern.available_sizes)}")
    print(f"Base size: {pattern.base_size}")
    print(f"Pieces: {len(pattern.pieces)}")

    for piece_name, piece_info in pattern.pieces.items():
        print(f"\n  {piece_name}:")
        for size_name in pattern.available_sizes:
            if size_name in piece_info.sizes:
                s = piece_info.sizes[size_name]
                print(f"    {size_name:8}: {s.size_x:6.2f} x {s.size_y:6.2f} cm")


def main():
    """Test graded size extraction."""
    from pathlib import Path

    project_root = Path(__file__).parent
    pds_files = list((project_root / "DS-speciale" / "inputs" / "pds").glob("*.PDS"))

    for pds_path in pds_files[:2]:  # First 2 files
        pattern = extract_graded_info(pds_path)
        print_graded_info(pattern)

        # Test size selection
        print(f"\n  Size selection tests:")
        for chest in [88, 100, 112, 125]:
            best = find_best_size(pattern, chest)
            print(f"    Chest {chest}cm -> {best}")

        # Test scale factors
        print(f"\n  Scale factors (Small -> XL):")
        scales = get_size_scale_factors(pattern, "Small", "XL")
        for piece, (sx, sy) in list(scales.items())[:3]:
            print(f"    {piece}: X={sx:.3f}, Y={sy:.3f}")


if __name__ == "__main__":
    main()
