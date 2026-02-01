#!/usr/bin/env python3
"""
Production Pipeline: PDS/MRK -> HPGL/PLT for 62" Cutter

This is the end-to-end pipeline for SameDaySuits production:
1. Load PDS/MRK file
2. Extract embedded XML with SVG geometry
3. Parse SVG to get actual piece contours
4. Transform coordinates to real-world cm
5. NEST pieces to fit on 62" (157.48 cm) fabric width
6. Generate HPGL/PLT file for plotter/cutter

Author: Claude
Date: 2026-01-30
Updated: 2026-01-30 - Added nesting engine integration
"""

import os
import re
import json
import math
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
import xml.etree.ElementTree as ET

# Import nesting engines (basic and improved)
from nesting_engine import (
    nest_bottom_left_fill,
    Point as NestPoint,
    NestingResult,
    visualize_nesting,
)

# Import improved nesting for better utilization
try:
    from improved_nesting import best_nest

    IMPROVED_NESTING_AVAILABLE = True
except ImportError:
    IMPROVED_NESTING_AVAILABLE = False

# Import master nesting for best-of-all algorithms
try:
    from master_nesting import master_nest

    MASTER_NESTING_AVAILABLE = True
except ImportError:
    MASTER_NESTING_AVAILABLE = False


# Constants
CUTTER_WIDTH_INCHES = 62
CUTTER_WIDTH_CM = CUTTER_WIDTH_INCHES * 2.54  # 157.48 cm
HPGL_UNITS_PER_MM = 40  # Standard HPGL
NESTING_GAP_CM = 0.5  # Gap between pieces


@dataclass
class Point:
    x: float
    y: float


@dataclass
class Contour:
    points: List[Point]
    closed: bool = True
    fill_color: str = ""
    stroke_color: str = ""


@dataclass
class Piece:
    name: str
    unique_id: str
    material: str
    quantity: int
    contours: List[Contour] = field(default_factory=list)
    size_x: float = 0.0
    size_y: float = 0.0


@dataclass
class Pattern:
    name: str
    filename: str
    units: str
    pieces: List[Piece] = field(default_factory=list)


def extract_xml_from_pds(pds_path: str) -> str:
    """Extract embedded XML from PDS binary file."""
    with open(pds_path, "rb") as f:
        data = f.read()

    xml_start = data.find(b"<?xml")
    if xml_start == -1:
        raise ValueError("No XML found in PDS file")

    # Find the closing tag (STYLE or MARKER)
    for end_tag in [b"</STYLE>", b"</MARKER>"]:
        xml_end = data.find(end_tag, xml_start)
        if xml_end != -1:
            xml_content = data[xml_start : xml_end + len(end_tag)].decode(
                "utf-8", errors="replace"
            )
            return xml_content

    raise ValueError("No valid XML closing tag found")


def parse_svg_polygon(points_str: str) -> List[Point]:
    """Parse SVG polygon points attribute."""
    points = []
    parts = points_str.strip().split()
    for part in parts:
        if "," in part:
            x, y = part.split(",")
            points.append(Point(float(x), float(y)))
    return points


def parse_svg_path(d: str) -> List[Point]:
    """Parse SVG path d attribute (simplified - line segments only)."""
    points = []
    d = d.replace(",", " ")
    d = re.sub(r"\s+", " ", d).strip()

    tokens = re.split(r"([MLHVCSQTAZ])", d, flags=re.IGNORECASE)

    current_x, current_y = 0.0, 0.0
    i = 0

    while i < len(tokens):
        token = tokens[i].strip()
        if not token:
            i += 1
            continue

        if token.upper() in "ML":
            cmd = token
            i += 1
            if i >= len(tokens):
                break

            coords_str = tokens[i].strip()
            if coords_str:
                nums = coords_str.split()
                j = 0
                while j + 1 < len(nums):
                    try:
                        x = float(nums[j])
                        y = float(nums[j + 1])

                        if cmd == cmd.lower():  # Relative
                            x += current_x
                            y += current_y

                        points.append(Point(x, y))
                        current_x, current_y = x, y
                        j += 2
                    except ValueError:
                        j += 1
            i += 1
        elif token.upper() == "Z":
            if points and points[0] != points[-1]:
                points.append(Point(points[0].x, points[0].y))
            i += 1
        else:
            i += 1

    return points


def extract_piece_dimensions(
    xml_content: str, base_size: str = "Small"
) -> Dict[str, Dict]:
    """Extract piece dimensions from GEOM_INFO for the base size."""
    root = ET.fromstring(xml_content)

    pieces = {}
    for piece in root.findall(".//PIECE"):
        name = piece.find("NAME")
        if name is not None:
            piece_name = name.text or ""

            # Find the base size info
            for size in piece.findall("SIZE"):
                size_name = size.find("NAME")
                if size_name is not None and size_name.text == base_size:
                    geom = size.find("GEOM_INFO")
                    if geom is not None:
                        pieces[piece_name] = {
                            "size_x": float(geom.get("SIZE_X", 0)),
                            "size_y": float(geom.get("SIZE_Y", 0)),
                            "area": float(geom.get("AREA", 0)),
                            "perimeter": float(geom.get("PERIMETER", 0)),
                        }
                    break

    return pieces


def calculate_total_layout_size(pieces: Dict[str, Dict]) -> Tuple[float, float]:
    """Calculate approximate total layout size from piece dimensions."""
    total_width = sum(p["size_x"] for p in pieces.values())
    max_height = max(p["size_y"] for p in pieces.values()) if pieces else 0

    # This is a rough approximation - pieces would be nested more efficiently
    return total_width, max_height


def extract_svg_geometry(
    xml_content: str, cutting_contours_only: bool = True
) -> Tuple[List[Contour], Dict]:
    """Extract geometry from embedded SVG in XML.

    Args:
        xml_content: The XML string extracted from PDS file
        cutting_contours_only: If True, only extract piece outline polygons (colored fills)
                              and skip background, internal lines, and detail groups.
    """
    contours = []
    metadata = {}

    root = ET.fromstring(xml_content)

    # Colors to skip (background/marker area)
    BACKGROUND_COLORS = {"#C0C0C0", "#c0c0c0", "gray", "grey", "#808080"}

    # Find MARKER/VIEW element with SVG
    for view in root.iter():
        if view.tag == "VIEW":
            factor = float(view.get("FACTOR", "0.1"))
            metadata["view_factor"] = factor

            # Find SVG element
            for svg in view.iter():
                if "svg" in svg.tag.lower() or svg.tag == "svg":
                    # Get viewBox
                    viewbox = svg.get("viewBox", "0 0 1000 1000")
                    vb_parts = viewbox.split()
                    if len(vb_parts) == 4:
                        metadata["viewbox"] = {
                            "min_x": float(vb_parts[0]),
                            "min_y": float(vb_parts[1]),
                            "width": float(vb_parts[2]),
                            "height": float(vb_parts[3]),
                        }

                    # Calculate scale factor
                    metadata["scale_cm_per_unit"] = factor / 100.0

                    # Extract only direct children of SVG (not nested in <g> groups)
                    # This skips internal details like grainlines, notches, text
                    for elem in svg:
                        tag = (
                            elem.tag.lower()
                            if isinstance(elem.tag, str)
                            else str(elem.tag).lower()
                        )
                        # Remove namespace if present
                        if "}" in tag:
                            tag = tag.split("}")[-1]

                        if "polygon" in tag:
                            fill_color = elem.get("fill", "")

                            # Skip background polygons
                            if (
                                cutting_contours_only
                                and fill_color.lower() in BACKGROUND_COLORS
                            ):
                                continue

                            points_str = elem.get("points", "")
                            if points_str:
                                points = parse_svg_polygon(points_str)
                                if points:
                                    contours.append(
                                        Contour(
                                            points=points,
                                            closed=True,
                                            fill_color=fill_color,
                                            stroke_color=elem.get("stroke", ""),
                                        )
                                    )

                        elif "path" in tag and not cutting_contours_only:
                            # Paths are usually internal lines - skip for cutting
                            d = elem.get("d", "")
                            if d:
                                points = parse_svg_path(d)
                                if points:
                                    contours.append(
                                        Contour(
                                            points=points,
                                            closed="z" in d.lower(),
                                            fill_color=elem.get("fill", ""),
                                            stroke_color=elem.get("stroke", ""),
                                        )
                                    )

    return contours, metadata


def transform_to_cm(
    contours: List[Contour],
    metadata: Dict,
    real_width_cm: Optional[float] = None,
    real_height_cm: Optional[float] = None,
) -> List[Contour]:
    """Transform SVG coordinates to real-world cm.

    The embedded SVG is a preview at reduced scale. If real_width_cm and
    real_height_cm are provided (from GEOM_INFO), we use those to calculate
    the correct scale. Otherwise, we use the view factor.
    """
    viewbox = metadata.get("viewbox", {})
    vb_width = viewbox.get("width", 1000)
    vb_height = viewbox.get("height", 1000)

    # Calculate scale factor
    if real_width_cm and real_height_cm:
        # Use actual dimensions if provided
        scale_x = real_width_cm / vb_width
        scale_y = real_height_cm / vb_height
    else:
        # Fall back to view factor
        scale = metadata.get("scale_cm_per_unit", 0.01)
        scale_x = scale_y = scale

    transformed = []
    for contour in contours:
        new_points = []
        for p in contour.points:
            new_points.append(Point(x=p.x * scale_x, y=p.y * scale_y))
        transformed.append(
            Contour(
                points=new_points,
                closed=contour.closed,
                fill_color=contour.fill_color,
                stroke_color=contour.stroke_color,
            )
        )

    return transformed


def nest_contours(
    contours: List[Contour],
    fabric_width: float = CUTTER_WIDTH_CM,
    gap: float = NESTING_GAP_CM,
    use_improved: bool = True,
) -> Tuple[List[Contour], NestingResult]:
    """
    Nest contours to fit within fabric width using bin-packing algorithm.

    Returns transformed contours with new positions and nesting result metadata.

    Args:
        contours: List of contours to nest
        fabric_width: Maximum fabric width (default 62" = 157.48 cm)
        gap: Gap between pieces (default 0.5 cm)
        use_improved: Use improved nesting algorithms (guillotine/skyline) for better utilization
    """
    if not contours:
        return [], NestingResult([], fabric_width, 0, 0, True, "No contours")

    # Convert to nesting engine format
    contour_groups = []
    for c in contours:
        points = [NestPoint(p.x, p.y) for p in c.points]
        contour_groups.append(points)

    # Run nesting - use master nesting (best of all) if available, then improved, then basic
    if use_improved and MASTER_NESTING_AVAILABLE:
        result = master_nest(contour_groups, fabric_width, gap)
    elif use_improved and IMPROVED_NESTING_AVAILABLE:
        result = best_nest(contour_groups, fabric_width, gap)
    else:
        result = nest_bottom_left_fill(contour_groups, fabric_width, gap)

    if not result.success:
        print(f"  WARNING: Nesting failed - {result.message}")
        return contours, result

    # Create nested contours with new positions
    nested_contours = []
    for nested_piece in result.pieces:
        # Find original contour
        original = contours[nested_piece.piece_id]

        # Transform points to nested position
        new_points = []
        for p in nested_piece.transformed_points:
            new_points.append(
                Point(
                    x=p.x + nested_piece.position[0],
                    y=p.y + nested_piece.position[1],
                )
            )

        nested_contours.append(
            Contour(
                points=new_points,
                closed=original.closed,
                fill_color=original.fill_color,
                stroke_color=original.stroke_color,
            )
        )

    return nested_contours, result


def generate_hpgl(
    contours: List[Contour],
    output_path: str,
    fabric_width_cm: float = CUTTER_WIDTH_CM,
    units: str = "cm",
):
    """Generate HPGL/PLT file for plotter/cutter."""

    # Calculate bounds
    all_x = [p.x for c in contours for p in c.points]
    all_y = [p.y for c in contours for p in c.points]

    if not all_x or not all_y:
        print("Warning: No geometry to export")
        return

    min_x, max_x = min(all_x), max(all_x)
    min_y, max_y = min(all_y), max(all_y)

    width = max_x - min_x
    height = max_y - min_y

    print(f"  Pattern bounds: {width:.2f} x {height:.2f} cm")
    print(f"  Fabric width: {fabric_width_cm:.2f} cm")

    if width > fabric_width_cm:
        print(f"  WARNING: Pattern width ({width:.2f} cm) exceeds fabric width!")

    # Convert to HPGL units (40 units per mm)
    def to_hpgl(cm_val):
        return int(cm_val * 10 * HPGL_UNITS_PER_MM)

    with open(output_path, "w") as f:
        # HPGL initialization
        f.write("IN;\n")  # Initialize
        f.write("SP1;\n")  # Select pen 1
        f.write("PU;\n")  # Pen up

        # Draw each contour
        for i, contour in enumerate(contours):
            if not contour.points:
                continue

            # Move to first point
            first = contour.points[0]
            f.write(f"PU{to_hpgl(first.x - min_x)},{to_hpgl(first.y - min_y)};\n")

            # Draw lines to remaining points
            f.write("PD")
            coords = []
            for p in contour.points[1:]:
                coords.append(f"{to_hpgl(p.x - min_x)},{to_hpgl(p.y - min_y)}")
            f.write(",".join(coords) + ";\n")

            # Close if needed
            if contour.closed and contour.points[-1] != contour.points[0]:
                f.write(f"PD{to_hpgl(first.x - min_x)},{to_hpgl(first.y - min_y)};\n")

            f.write("PU;\n")  # Pen up after each contour

        # HPGL end
        f.write("SP0;\n")  # Deselect pen
        f.write("IN;\n")  # Reset

    print(f"  HPGL output: {output_path}")


def process_pds_file(
    pds_path_str: str, output_dir_str: str, enable_nesting: bool = True
):
    """Process a single PDS file and generate cutter-ready output."""
    pds_path = Path(pds_path_str)
    output_dir = Path(output_dir_str)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'=' * 60}")
    print(f"Processing: {pds_path.name}")
    print(f"{'=' * 60}")

    # Extract XML
    print("\n1. Extracting embedded XML...")
    xml_content = extract_xml_from_pds(str(pds_path))
    print(f"   XML size: {len(xml_content)} bytes")

    # Extract piece dimensions from GEOM_INFO
    print("\n2. Extracting piece dimensions...")
    pieces = extract_piece_dimensions(xml_content, "Small")
    if pieces:
        print(f"   Found {len(pieces)} pieces")
        for name, dims in pieces.items():
            print(f"     - {name}: {dims['size_x']:.2f} x {dims['size_y']:.2f} cm")

        total_width, total_height = calculate_total_layout_size(pieces)
        print(f"   Approx total layout: {total_width:.2f} x {total_height:.2f} cm")
    else:
        total_width, total_height = None, None

    # Extract SVG geometry
    print("\n3. Extracting SVG geometry...")
    contours, metadata = extract_svg_geometry(xml_content)
    print(f"   Found {len(contours)} contours")
    print(f"   View factor: {metadata.get('view_factor', 'N/A')}")

    # Transform coordinates using real dimensions if available
    print("\n4. Transforming coordinates to cm...")
    contours_cm = transform_to_cm(contours, metadata, total_width, total_height)

    # Calculate original bounds
    all_x = [p.x for c in contours_cm for p in c.points]
    all_y = [p.y for c in contours_cm for p in c.points]
    original_width = max(all_x) - min(all_x) if all_x else 0
    original_height = max(all_y) - min(all_y) if all_y else 0
    print(f"   Original layout: {original_width:.2f} x {original_height:.2f} cm")

    # Nesting step
    nesting_result = None
    if enable_nesting and original_width > CUTTER_WIDTH_CM:
        print(
            f"\n5. NESTING required (width {original_width:.2f} cm > {CUTTER_WIDTH_CM:.2f} cm fabric)"
        )
        contours_nested, nesting_result = nest_contours(contours_cm)

        if nesting_result.success:
            contours_cm = contours_nested
            print(f"   Nested {len(contours_nested)} pieces")
            print(
                f"   New layout: {nesting_result.fabric_width:.2f} x {nesting_result.fabric_length:.2f} cm"
            )
            print(f"   Utilization: {nesting_result.utilization:.1f}%")

            # Show rotation summary
            rotations = {}
            for p in nesting_result.pieces:
                rot = p.rotation
                rotations[rot] = rotations.get(rot, 0) + 1
            if any(r != 0 for r in rotations.keys()):
                print(f"   Rotations: {rotations}")
        else:
            print(f"   WARNING: Nesting failed - using original layout")
    elif enable_nesting:
        print(
            f"\n5. Nesting not required (width {original_width:.2f} cm <= {CUTTER_WIDTH_CM:.2f} cm)"
        )
    else:
        print(f"\n5. Nesting disabled")

    # Generate HPGL for 62" cutter
    print('\n6. Generating HPGL for 62" cutter...')
    output_plt = output_dir / f"{pds_path.stem}.plt"
    generate_hpgl(contours_cm, str(output_plt))

    # Also save metadata JSON
    output_json = output_dir / f"{pds_path.stem}_metadata.json"
    metadata_out = {
        "source_file": str(pds_path),
        "contour_count": len(contours),
        "pieces": pieces,
        "original_layout_cm": {"width": original_width, "height": original_height},
        "svg_metadata": metadata,
    }

    if nesting_result and nesting_result.success:
        metadata_out["nesting"] = {
            "success": True,
            "fabric_width_cm": nesting_result.fabric_width,
            "fabric_length_cm": nesting_result.fabric_length,
            "utilization_percent": nesting_result.utilization,
            "piece_count": len(nesting_result.pieces),
            "piece_placements": [
                {
                    "id": p.piece_id,
                    "position": list(p.position),
                    "rotation": p.rotation,
                }
                for p in nesting_result.pieces
            ],
        }

    with open(output_json, "w") as f:
        json.dump(metadata_out, f, indent=2)

    print(f"\n   Metadata: {output_json}")

    return {
        "input": str(pds_path),
        "contours": len(contours),
        "output_plt": str(output_plt),
        "output_json": str(output_json),
        "nesting_applied": nesting_result is not None and nesting_result.success,
    }


def main():
    """Main entry point for production pipeline."""
    base_dir = Path(__file__).resolve().parents[3]
    input_dir = base_dir / "DS-speciale" / "inputs" / "pds"
    output_dir = base_dir / "DS-speciale" / "out" / "production_62inch"

    print("=" * 70)
    print('  PRODUCTION PIPELINE: PDS -> HPGL/PLT (62" Cutter)')
    print("=" * 70)
    print(f"\nInput directory: {input_dir}")
    print(f"Output directory: {output_dir}")
    print(f'Cutter width: {CUTTER_WIDTH_CM:.2f} cm ({CUTTER_WIDTH_INCHES}")')

    # Find PDS files
    pds_files = list(input_dir.glob("*.PDS"))
    print(f"\nPDS files found: {len(pds_files)}")

    results = []
    for pds_file in pds_files:
        try:
            result = process_pds_file(str(pds_file), str(output_dir))
            results.append(result)
        except Exception as e:
            print(f"\nERROR processing {pds_file.name}: {e}")
            results.append({"input": str(pds_file), "error": str(e)})

    # Summary
    print("\n" + "=" * 70)
    print("  PIPELINE SUMMARY")
    print("=" * 70)

    success = sum(1 for r in results if "error" not in r)
    print(f"\nTotal files: {len(results)}")
    print(f"Successful: {success}")
    print(f"Failed: {len(results) - success}")

    # Save results
    results_file = output_dir / "pipeline_results.json"
    with open(results_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to: {results_file}")


if __name__ == "__main__":
    main()
