#!/usr/bin/env python3
"""
Turbo Nesting Engine - Fast + High Utilization

This module achieves high utilization with reasonable speed by:
1. Using Shapely for TRUE polygon collision detection (not bounding box)
2. Fast heightmap-based placement finding
3. Multi-pass optimization with different orderings
4. Intelligent piece rotation selection

Key insight: The bottleneck in NFP-based nesting is NFP computation.
Instead, we use direct polygon intersection tests which are fast with Shapely.

Author: Claude
Date: 2026-01-31
"""

import math
import random
import time
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass, field
from copy import deepcopy

try:
    from shapely.geometry import Polygon as ShapelyPolygon, box as shapely_box
    from shapely.affinity import translate, rotate
    from shapely.validation import make_valid
    from shapely.prepared import prep
    from shapely import STRtree

    SHAPELY_AVAILABLE = True
except ImportError:
    SHAPELY_AVAILABLE = False
    print("WARNING: shapely not available. Install with: pip install shapely")

from nesting_engine import (
    Point,
    BoundingBox,
    NestedPiece,
    NestingResult,
    calculate_bbox,
    normalize_to_origin,
    GAP_CM,
    CUTTER_WIDTH_CM,
)

# Constants
ROTATION_ANGLES = [0, 90, 180, 270]


def points_to_shapely(points: List[Point]) -> ShapelyPolygon:
    """Convert Point list to Shapely polygon."""
    coords = [(p.x, p.y) for p in points]
    if len(coords) < 3:
        return ShapelyPolygon()
    if coords[0] != coords[-1]:
        coords.append(coords[0])
    poly = ShapelyPolygon(coords)
    if not poly.is_valid:
        poly = make_valid(poly)
        if hasattr(poly, "geoms"):  # MultiPolygon
            poly = max(poly.geoms, key=lambda p: p.area)
    return poly


def shapely_to_points(poly: ShapelyPolygon) -> List[Point]:
    """Convert Shapely polygon to Point list."""
    if poly.is_empty:
        return []
    coords = list(poly.exterior.coords)
    return [Point(x, y) for x, y in coords[:-1]]


@dataclass
class Piece:
    """A pattern piece with pre-computed rotations."""

    id: int
    original_points: List[Point]
    shapely_poly: ShapelyPolygon
    area: float = 0
    rotations: Dict[int, Tuple[ShapelyPolygon, float, float]] = field(
        default_factory=dict
    )

    def __post_init__(self):
        self.area = self.shapely_poly.area
        # Pre-compute rotations with dimensions
        for angle in ROTATION_ANGLES:
            if angle == 0:
                rotated = self.shapely_poly
            else:
                rotated = rotate(self.shapely_poly, angle, origin="centroid")
            # Normalize to origin
            bounds = rotated.bounds
            rotated = translate(rotated, -bounds[0], -bounds[1])
            width = rotated.bounds[2] - rotated.bounds[0]
            height = rotated.bounds[3] - rotated.bounds[1]
            self.rotations[angle] = (rotated, width, height)


@dataclass
class Placement:
    """A placed piece."""

    piece_id: int
    x: float
    y: float
    rotation: int
    polygon: ShapelyPolygon
    width: float
    height: float


class TurboNester:
    """
    High-performance nesting using true polygon operations.
    """

    def __init__(
        self,
        fabric_width: float = CUTTER_WIDTH_CM,
        gap: float = GAP_CM,
    ):
        self.fabric_width = fabric_width
        self.gap = gap

    def _find_position_heightmap(
        self,
        piece_poly: ShapelyPolygon,
        piece_w: float,
        piece_h: float,
        placements: List[Placement],
        step: float = 2.0,  # Grid resolution in cm
    ) -> Optional[Tuple[float, float]]:
        """
        Find bottom-left position using heightmap approach.

        Scans from left-to-right, bottom-to-top to find first valid position.
        Uses true polygon collision, not bounding box.
        """
        if not placements:
            return (0, 0)

        # Determine search bounds
        max_y = max(p.y + p.height for p in placements) + piece_h + self.gap

        # Build spatial index for fast collision detection
        placed_polys = [p.polygon.buffer(self.gap / 2) for p in placements]
        tree = STRtree(placed_polys)

        # Scan positions
        best_pos = None
        best_y = float("inf")

        # First try positions along the right edge of each placed piece
        x_candidates = [0]
        for p in placements:
            x_right = p.x + p.width + self.gap
            if x_right + piece_w <= self.fabric_width:
                x_candidates.append(x_right)

        # Also add some grid positions
        for x in range(0, int(self.fabric_width - piece_w), int(step * 5)):
            x_candidates.append(float(x))

        x_candidates = sorted(set(x_candidates))

        for x in x_candidates:
            if x < 0 or x + piece_w > self.fabric_width:
                continue

            # Find the minimum Y at this X by checking what we'd collide with
            min_y = 0

            # Quick check: find max Y of any piece that overlaps our X range
            for p in placements:
                if not (p.x + p.width + self.gap <= x or x + piece_w + self.gap <= p.x):
                    # X ranges overlap, so we need to go above this piece
                    min_y = max(min_y, p.y + p.height + self.gap)

            # Now scan upward from min_y to find valid position
            for y in [min_y] + [min_y + i * step for i in range(1, 100)]:
                if y >= best_y:
                    break

                test_poly = translate(piece_poly, x, y)
                test_buffered = test_poly.buffer(
                    -0.05
                )  # Tiny negative buffer for numerical stability

                # Check collision with spatial index
                possible_hits = tree.query(test_poly)
                collision = False
                for idx in possible_hits:
                    if test_buffered.intersects(placed_polys[idx]):
                        collision = True
                        break

                if not collision:
                    if y < best_y:
                        best_y = y
                        best_pos = (x, y)
                    break

        return best_pos

    def nest_greedy(
        self,
        pieces: List[Piece],
        order: List[int] = None,
        rotations: List[int] = None,
    ) -> Tuple[List[Placement], float]:
        """
        Greedy bottom-left fill with true polygon collision.
        """
        if order is None:
            order = list(range(len(pieces)))
        if rotations is None:
            rotations = [0] * len(pieces)

        placements: List[Placement] = []
        max_y = 0

        for idx, piece_idx in enumerate(order):
            piece = pieces[piece_idx]
            rotation = rotations[idx]

            # Get rotated polygon
            poly, w, h = piece.rotations[rotation]

            # Skip if too wide
            if w > self.fabric_width:
                # Try other rotations
                for rot in ROTATION_ANGLES:
                    poly_r, w_r, h_r = piece.rotations[rot]
                    if w_r <= self.fabric_width:
                        poly, w, h = poly_r, w_r, h_r
                        rotation = rot
                        break
                else:
                    continue  # Can't fit this piece

            # Find position
            pos = self._find_position_heightmap(poly, w, h, placements)

            if pos is None:
                # Force placement at bottom
                pos = (0, max_y + self.gap)

            x, y = pos
            placed_poly = translate(poly, x, y)

            placements.append(
                Placement(
                    piece_id=piece.id,
                    x=x,
                    y=y,
                    rotation=rotation,
                    polygon=placed_poly,
                    width=w,
                    height=h,
                )
            )

            max_y = max(max_y, y + h)

        return placements, max_y

    def calculate_utilization(
        self, placements: List[Placement], pieces: List[Piece], fabric_length: float
    ) -> float:
        """Calculate utilization percentage."""
        if fabric_length <= 0:
            return 0
        total_area = sum(pieces[p.piece_id].area for p in placements)
        fabric_area = self.fabric_width * fabric_length
        return (total_area / fabric_area) * 100

    def optimize_multi_pass(
        self,
        pieces: List[Piece],
        n_iterations: int = 50,
        timeout_seconds: float = 30,
    ) -> Tuple[List[Placement], float, float]:
        """
        Multi-pass optimization trying different orderings and rotations.
        """
        n = len(pieces)
        if n == 0:
            return [], 0, 0

        start_time = time.time()

        best_placements = []
        best_length = float("inf")
        best_util = 0

        # Strategy 1: Area descending (largest first)
        order = sorted(range(n), key=lambda i: -pieces[i].area)
        for rots in self._generate_rotation_combos(n, 4):
            placements, length = self.nest_greedy(pieces, order, rots)
            util = self.calculate_utilization(placements, pieces, length)
            if util > best_util:
                best_util = util
                best_placements = placements
                best_length = length
            if time.time() - start_time > timeout_seconds / 3:
                break

        # Strategy 2: Height descending
        order = sorted(range(n), key=lambda i: -pieces[i].rotations[0][2])
        for rots in self._generate_rotation_combos(n, 4):
            placements, length = self.nest_greedy(pieces, order, rots)
            util = self.calculate_utilization(placements, pieces, length)
            if util > best_util:
                best_util = util
                best_placements = placements
                best_length = length
            if time.time() - start_time > timeout_seconds * 2 / 3:
                break

        # Strategy 3: Width descending
        order = sorted(range(n), key=lambda i: -pieces[i].rotations[0][1])
        for rots in self._generate_rotation_combos(n, 4):
            placements, length = self.nest_greedy(pieces, order, rots)
            util = self.calculate_utilization(placements, pieces, length)
            if util > best_util:
                best_util = util
                best_placements = placements
                best_length = length
            if time.time() - start_time > timeout_seconds:
                break

        # Strategy 4: Random permutations
        while time.time() - start_time < timeout_seconds:
            order = list(range(n))
            random.shuffle(order)
            rots = [random.choice(ROTATION_ANGLES) for _ in range(n)]

            placements, length = self.nest_greedy(pieces, order, rots)
            util = self.calculate_utilization(placements, pieces, length)

            if util > best_util:
                best_util = util
                best_placements = placements
                best_length = length

        return best_placements, best_length, best_util

    def _generate_rotation_combos(self, n: int, max_combos: int) -> List[List[int]]:
        """Generate rotation combinations to try."""
        combos = []
        # All 0s
        combos.append([0] * n)
        # All 90s
        combos.append([90] * n)
        # Alternate
        combos.append([0 if i % 2 == 0 else 90 for i in range(n)])
        # Random
        for _ in range(max(0, max_combos - 3)):
            combos.append([random.choice([0, 90]) for _ in range(n)])
        return combos[:max_combos]

    def nest(self, contour_groups: List[List[Point]]) -> NestingResult:
        """
        Main nesting function.
        """
        if not SHAPELY_AVAILABLE:
            raise RuntimeError("Shapely required")

        if not contour_groups:
            return NestingResult([], self.fabric_width, 0, 0, True, "No pieces")

        # Convert to Piece objects
        pieces = []
        for i, points in enumerate(contour_groups):
            if len(points) < 3:
                continue
            try:
                poly = points_to_shapely(points)
                if poly.is_empty or poly.area < 1:
                    continue
                bounds = poly.bounds
                poly = translate(poly, -bounds[0], -bounds[1])
                pieces.append(Piece(id=i, original_points=points, shapely_poly=poly))
            except Exception as e:
                continue

        if not pieces:
            return NestingResult([], self.fabric_width, 0, 0, False, "No valid pieces")

        # Run optimization
        placements, fabric_length, utilization = self.optimize_multi_pass(
            pieces, timeout_seconds=30
        )

        # Convert to NestingResult format
        nested_pieces = []
        for placement in placements:
            orig_piece = next((p for p in pieces if p.id == placement.piece_id), None)
            if orig_piece is None:
                continue

            transformed = shapely_to_points(placement.polygon)
            bounds = placement.polygon.bounds
            bbox = BoundingBox(bounds[0], bounds[1], bounds[2], bounds[3])

            nested_pieces.append(
                NestedPiece(
                    piece_id=placement.piece_id,
                    original_points=orig_piece.original_points,
                    transformed_points=transformed,
                    bbox=bbox,
                    position=(placement.x, placement.y),
                    rotation=placement.rotation,
                )
            )

        return NestingResult(
            pieces=nested_pieces,
            fabric_width=self.fabric_width,
            fabric_length=fabric_length,
            utilization=utilization,
            success=True,
            message=f"Turbo nested {len(nested_pieces)} pieces at {utilization:.1f}%",
        )


def turbo_nest(
    contour_groups: List[List[Point]],
    fabric_width: float = CUTTER_WIDTH_CM,
    gap: float = GAP_CM,
) -> NestingResult:
    """Main entry point."""
    nester = TurboNester(fabric_width, gap)
    return nester.nest(contour_groups)


def main():
    """Test turbo nesting."""
    import argparse
    from pathlib import Path
    from production_pipeline import (
        extract_xml_from_pds,
        extract_piece_dimensions,
        extract_svg_geometry,
        transform_to_cm,
    )

    parser = argparse.ArgumentParser(description="Turbo nesting engine")
    parser.add_argument("pds_file", nargs="?", help="PDS file to test")
    parser.add_argument("--compare", action="store_true", help="Compare algorithms")
    parser.add_argument("--all", action="store_true", help="Test all PDS files")

    args = parser.parse_args()

    if args.all:
        pds_files = [
            "DS-speciale/inputs/pds/Basic Tee_2D.PDS",
            "DS-speciale/inputs/pds/Light  Jacket_2D.PDS",
            "DS-speciale/inputs/pds/Skinny Trousers_2D.PDS",
            "DS-speciale/inputs/pds/Skinny Cargo_2D.PDS",
        ]
    elif args.pds_file:
        pds_files = [args.pds_file]
    else:
        pds_files = ["DS-speciale/inputs/pds/Basic Tee_2D.PDS"]

    for pds_path in pds_files:
        if not Path(pds_path).exists():
            print(f"File not found: {pds_path}")
            continue

        print(f"\n{'=' * 70}")
        print(f"Pattern: {Path(pds_path).stem}")
        print("=" * 70)

        xml_content = extract_xml_from_pds(pds_path)
        pieces = extract_piece_dimensions(xml_content, "Small")
        total_width = sum(p["size_x"] for p in pieces.values())
        total_height = max(p["size_y"] for p in pieces.values()) if pieces else 0

        contours, metadata = extract_svg_geometry(
            xml_content, cutting_contours_only=True
        )
        contours_cm = transform_to_cm(contours, metadata, total_width, total_height)

        contour_groups = [[Point(p.x, p.y) for p in c.points] for c in contours_cm]

        print(f"Pieces: {len(contour_groups)}")
        print(f"Fabric width: {CUTTER_WIDTH_CM} cm")

        if args.compare:
            from nesting_engine import nest_bottom_left_fill
            from improved_nesting import guillotine_nest, skyline_nest

            print(
                f"\n{'Algorithm':<15} {'Utilization':<12} {'Length':<12} {'Time':<10}"
            )
            print("-" * 60)

            # Shelf
            t0 = time.time()
            try:
                result = nest_bottom_left_fill(contour_groups, CUTTER_WIDTH_CM)
                print(
                    f"{'shelf':<15} {result.utilization:>9.1f}%  {result.fabric_length:>9.1f} cm {time.time() - t0:>7.2f}s"
                )
            except Exception as e:
                print(f"{'shelf':<15} FAILED: {e}")

            # Guillotine
            t0 = time.time()
            try:
                result = guillotine_nest(contour_groups, CUTTER_WIDTH_CM)
                print(
                    f"{'guillotine':<15} {result.utilization:>9.1f}%  {result.fabric_length:>9.1f} cm {time.time() - t0:>7.2f}s"
                )
            except Exception as e:
                print(f"{'guillotine':<15} FAILED: {e}")

            # Skyline
            t0 = time.time()
            try:
                result = skyline_nest(contour_groups, CUTTER_WIDTH_CM)
                print(
                    f"{'skyline':<15} {result.utilization:>9.1f}%  {result.fabric_length:>9.1f} cm {time.time() - t0:>7.2f}s"
                )
            except Exception as e:
                print(f"{'skyline':<15} FAILED: {e}")

            # Turbo
            t0 = time.time()
            try:
                result = turbo_nest(contour_groups, CUTTER_WIDTH_CM)
                print(
                    f"{'turbo':<15} {result.utilization:>9.1f}%  {result.fabric_length:>9.1f} cm {time.time() - t0:>7.2f}s"
                )
            except Exception as e:
                print(f"{'turbo':<15} FAILED: {e}")

            print("-" * 60)
        else:
            print("\nRunning turbo nesting...")
            t0 = time.time()
            result = turbo_nest(contour_groups)
            elapsed = time.time() - t0

            print(f"\nResult: {result.message}")
            print(f"Fabric length: {result.fabric_length:.1f} cm")
            print(f"Utilization: {result.utilization:.1f}%")
            print(f"Time: {elapsed:.1f} seconds")


if __name__ == "__main__":
    main()
