#!/usr/bin/env python3
"""
Hybrid Nesting Engine - Combines Best Strategies for Maximum Utilization

This module combines multiple nesting strategies:
1. Run all existing algorithms (shelf, guillotine, skyline, turbo)
2. Use polygon sliding to find tighter placements
3. Local optimization to compact the nest
4. Multiple orderings and rotations

The key to reaching 98% is:
1. Try MANY different orderings (not just size-based)
2. Use true polygon collision for placement
3. "Slide" pieces toward origin to find tighter positions
4. Local search to improve individual placements

Author: Claude
Date: 2026-01-31
"""

import math
import random
import time
from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass, field
from copy import deepcopy
import itertools

try:
    from shapely.geometry import Polygon as ShapelyPolygon, box as shapely_box
    from shapely.affinity import translate, rotate
    from shapely.validation import make_valid
    from shapely import STRtree

    SHAPELY_AVAILABLE = True
except ImportError:
    SHAPELY_AVAILABLE = False

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
        if hasattr(poly, "geoms"):
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
    """A pattern piece."""

    id: int
    original_points: List[Point]
    shapely_poly: ShapelyPolygon
    area: float = 0
    rotations: Dict[int, Tuple[ShapelyPolygon, float, float]] = field(
        default_factory=dict
    )

    def __post_init__(self):
        self.area = self.shapely_poly.area
        for angle in ROTATION_ANGLES:
            if angle == 0:
                rotated = self.shapely_poly
            else:
                rotated = rotate(self.shapely_poly, angle, origin="centroid")
            bounds = rotated.bounds
            rotated = translate(rotated, -bounds[0], -bounds[1])
            width = rotated.bounds[2]
            height = rotated.bounds[3]
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


class HybridNester:
    """
    Hybrid nesting that combines multiple strategies.
    """

    def __init__(
        self,
        fabric_width: float = CUTTER_WIDTH_CM,
        gap: float = GAP_CM,
    ):
        self.fabric_width = fabric_width
        self.gap = gap

    def slide_to_bottom_left(
        self,
        piece_poly: ShapelyPolygon,
        piece_w: float,
        piece_h: float,
        start_x: float,
        start_y: float,
        other_polys: List[ShapelyPolygon],
        step: float = 0.5,
    ) -> Tuple[float, float]:
        """
        Slide a piece toward bottom-left until collision.

        This is key for tight packing - instead of just finding the first
        valid position, we slide pieces as close as possible.
        """
        x, y = start_x, start_y

        # Build spatial index
        if other_polys:
            tree = STRtree([p.buffer(self.gap / 2) for p in other_polys])
            buffered = [p.buffer(self.gap / 2) for p in other_polys]
        else:
            return (0, 0)

        # Slide down (decrease Y)
        while y > 0:
            test_poly = translate(piece_poly, x, y - step)
            test_buffered = test_poly.buffer(-0.02)

            # Check bounds
            if test_poly.bounds[1] < 0:
                break

            # Check collision
            collision = False
            for idx in tree.query(test_poly):
                if test_buffered.intersects(buffered[idx]):
                    collision = True
                    break

            if collision:
                break
            y -= step

        # Slide left (decrease X)
        while x > 0:
            test_poly = translate(piece_poly, x - step, y)
            test_buffered = test_poly.buffer(-0.02)

            # Check bounds
            if test_poly.bounds[0] < 0:
                break

            # Check collision
            collision = False
            for idx in tree.query(test_poly):
                if test_buffered.intersects(buffered[idx]):
                    collision = True
                    break

            if collision:
                break
            x -= step

        # Final slide down after sliding left
        while y > 0:
            test_poly = translate(piece_poly, x, y - step)
            test_buffered = test_poly.buffer(-0.02)

            if test_poly.bounds[1] < 0:
                break

            collision = False
            for idx in tree.query(test_poly):
                if test_buffered.intersects(buffered[idx]):
                    collision = True
                    break

            if collision:
                break
            y -= step

        return (max(0, x), max(0, y))

    def find_position_with_sliding(
        self,
        piece: Piece,
        rotation: int,
        placements: List[Placement],
        scan_step: float = 5.0,
    ) -> Optional[Tuple[float, float]]:
        """
        Find position by scanning and sliding.

        1. Scan a grid of potential positions
        2. For each valid position, slide toward origin
        3. Return the best (lowest Y, then lowest X)
        """
        poly, w, h = piece.rotations[rotation]

        if not placements:
            return (0, 0)

        placed_polys = [p.polygon for p in placements]
        max_y = max(p.y + p.height for p in placements)

        best_pos = None
        best_score = float("inf")  # lower is better: y * 1000 + x

        # Scan positions
        x_positions = list(range(0, int(self.fabric_width - w + 1), int(scan_step)))
        y_positions = list(range(0, int(max_y + h + scan_step), int(scan_step)))

        # Also add positions adjacent to placed pieces
        for p in placements:
            x_positions.append(int(p.x + p.width + self.gap))
            y_positions.append(int(p.y + p.height + self.gap))

        x_positions = sorted(
            set(x for x in x_positions if 0 <= x <= self.fabric_width - w)
        )
        y_positions = sorted(set(y for y in y_positions if y >= 0))

        # Build spatial index
        tree = STRtree([p.buffer(self.gap / 2) for p in placed_polys])
        buffered = [p.buffer(self.gap / 2) for p in placed_polys]

        for start_y in y_positions:
            if start_y * 1000 >= best_score:
                continue  # Can't improve

            for start_x in x_positions:
                if start_y * 1000 + start_x >= best_score:
                    continue

                test_poly = translate(poly, start_x, start_y)
                test_buffered = test_poly.buffer(-0.02)

                # Quick collision check
                collision = False
                for idx in tree.query(test_poly):
                    if test_buffered.intersects(buffered[idx]):
                        collision = True
                        break

                if collision:
                    continue

                # Valid position found - slide to optimize
                slid_x, slid_y = self.slide_to_bottom_left(
                    poly, w, h, start_x, start_y, placed_polys, step=1.0
                )

                score = slid_y * 1000 + slid_x
                if score < best_score:
                    best_score = score
                    best_pos = (slid_x, slid_y)

        return best_pos

    def nest_with_order(
        self,
        pieces: List[Piece],
        order: List[int],
        rotations: List[int],
    ) -> Tuple[List[Placement], float]:
        """Nest pieces in given order with given rotations."""
        placements: List[Placement] = []
        max_y = 0

        for idx, piece_idx in enumerate(order):
            piece = pieces[piece_idx]
            rotation = rotations[idx]

            poly, w, h = piece.rotations[rotation]

            # Skip if too wide, try other rotations
            if w > self.fabric_width:
                for rot in ROTATION_ANGLES:
                    p, w2, h2 = piece.rotations[rot]
                    if w2 <= self.fabric_width:
                        poly, w, h = p, w2, h2
                        rotation = rot
                        break
                else:
                    continue

            # Find position with sliding
            pos = self.find_position_with_sliding(piece, rotation, placements)

            if pos is None:
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

    def compact_layout(
        self,
        placements: List[Placement],
        pieces: List[Piece],
        iterations: int = 3,
    ) -> Tuple[List[Placement], float]:
        """
        Local optimization: try to slide each piece closer to origin.
        """
        improved = True
        iter_count = 0

        while improved and iter_count < iterations:
            improved = False
            iter_count += 1

            for i, placement in enumerate(placements):
                # Get all other placements
                others = [p.polygon for j, p in enumerate(placements) if j != i]

                piece = pieces[placement.piece_id]
                poly, w, h = piece.rotations[placement.rotation]

                # Try to slide this piece
                new_x, new_y = self.slide_to_bottom_left(
                    poly, w, h, placement.x, placement.y, others, step=0.5
                )

                if new_y < placement.y - 0.5 or new_x < placement.x - 0.5:
                    # Improved!
                    placements[i] = Placement(
                        piece_id=placement.piece_id,
                        x=new_x,
                        y=new_y,
                        rotation=placement.rotation,
                        polygon=translate(poly, new_x, new_y),
                        width=w,
                        height=h,
                    )
                    improved = True

        max_y = max(p.y + p.height for p in placements) if placements else 0
        return placements, max_y

    def calculate_utilization(
        self, placements: List[Placement], pieces: List[Piece], fabric_length: float
    ) -> float:
        if fabric_length <= 0:
            return 0
        total_area = sum(pieces[p.piece_id].area for p in placements)
        fabric_area = self.fabric_width * fabric_length
        return (total_area / fabric_area) * 100

    def optimize(
        self,
        pieces: List[Piece],
        timeout_seconds: float = 45,
    ) -> Tuple[List[Placement], float, float]:
        """
        Try many orderings and pick the best.
        """
        n = len(pieces)
        if n == 0:
            return [], 0, 0

        start_time = time.time()

        best_placements = []
        best_length = float("inf")
        best_util = 0

        # Heuristic orderings to try
        orderings = [
            # By area (decreasing)
            sorted(range(n), key=lambda i: -pieces[i].area),
            # By area (increasing)
            sorted(range(n), key=lambda i: pieces[i].area),
            # By height (decreasing)
            sorted(range(n), key=lambda i: -pieces[i].rotations[0][2]),
            # By width (decreasing)
            sorted(range(n), key=lambda i: -pieces[i].rotations[0][1]),
            # By perimeter
            sorted(
                range(n),
                key=lambda i: -(pieces[i].rotations[0][1] + pieces[i].rotations[0][2]),
            ),
        ]

        # Rotation strategies
        rotation_strategies = [
            [0] * n,  # All 0
            [90] * n,  # All 90
            [
                0 if pieces[i].rotations[0][1] >= pieces[i].rotations[0][2] else 90
                for i in range(n)
            ],  # Prefer wide
            [
                90 if pieces[i].rotations[0][1] >= pieces[i].rotations[0][2] else 0
                for i in range(n)
            ],  # Prefer tall
        ]

        # Try heuristic combinations
        for order in orderings:
            for rots in rotation_strategies:
                if time.time() - start_time > timeout_seconds / 2:
                    break

                placements, length = self.nest_with_order(pieces, order, rots)
                placements, length = self.compact_layout(placements, pieces)
                util = self.calculate_utilization(placements, pieces, length)

                if util > best_util:
                    best_util = util
                    best_placements = placements
                    best_length = length

                    if best_util >= 98:
                        return best_placements, best_length, best_util

        # Random search for remaining time
        while time.time() - start_time < timeout_seconds:
            order = list(range(n))
            random.shuffle(order)
            rots = [random.choice(ROTATION_ANGLES) for _ in range(n)]

            placements, length = self.nest_with_order(pieces, order, rots)
            util = self.calculate_utilization(placements, pieces, length)

            # Only compact if promising
            if util > best_util * 0.9:
                placements, length = self.compact_layout(placements, pieces)
                util = self.calculate_utilization(placements, pieces, length)

            if util > best_util:
                best_util = util
                best_placements = placements
                best_length = length

        return best_placements, best_length, best_util

    def nest(self, contour_groups: List[List[Point]]) -> NestingResult:
        """Main nesting function."""
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
            except:
                continue

        if not pieces:
            return NestingResult([], self.fabric_width, 0, 0, False, "No valid pieces")

        # Run optimization
        placements, fabric_length, utilization = self.optimize(
            pieces, timeout_seconds=45
        )

        # Convert to NestingResult
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
            message=f"Hybrid nested {len(nested_pieces)} pieces at {utilization:.1f}%",
        )


def hybrid_nest(
    contour_groups: List[List[Point]],
    fabric_width: float = CUTTER_WIDTH_CM,
    gap: float = GAP_CM,
) -> NestingResult:
    """Main entry point."""
    nester = HybridNester(fabric_width, gap)
    return nester.nest(contour_groups)


def best_of_all(
    contour_groups: List[List[Point]],
    fabric_width: float = CUTTER_WIDTH_CM,
    gap: float = GAP_CM,
) -> NestingResult:
    """
    Run ALL nesting algorithms and return the best result.

    This is the recommended function for production use.
    """
    from nesting_engine import nest_bottom_left_fill
    from improved_nesting import guillotine_nest, skyline_nest

    results = {}

    # Fast algorithms first
    try:
        results["shelf"] = nest_bottom_left_fill(contour_groups, fabric_width, gap)
    except:
        pass

    try:
        results["guillotine"] = guillotine_nest(contour_groups, fabric_width, gap)
    except:
        pass

    try:
        results["skyline"] = skyline_nest(contour_groups, fabric_width, gap)
    except:
        pass

    # Hybrid (slower but usually better)
    try:
        results["hybrid"] = hybrid_nest(contour_groups, fabric_width, gap)
    except:
        pass

    if not results:
        return NestingResult([], fabric_width, 0, 0, False, "All algorithms failed")

    # Return best
    best_name = max(
        results.keys(),
        key=lambda k: results[k].utilization if results[k].success else 0,
    )
    best = results[best_name]

    return NestingResult(
        pieces=best.pieces,
        fabric_width=best.fabric_width,
        fabric_length=best.fabric_length,
        utilization=best.utilization,
        success=best.success,
        message=f"Best ({best_name}): {best.utilization:.1f}%",
    )


def main():
    """Test hybrid nesting."""
    import argparse
    from pathlib import Path
    from production_pipeline import (
        extract_xml_from_pds,
        extract_piece_dimensions,
        extract_svg_geometry,
        transform_to_cm,
    )

    parser = argparse.ArgumentParser(description="Hybrid nesting engine")
    parser.add_argument("pds_file", nargs="?", help="PDS file")
    parser.add_argument("--compare", action="store_true", help="Compare algorithms")
    parser.add_argument("--all", action="store_true", help="Test all PDS files")
    parser.add_argument("--best", action="store_true", help="Run best_of_all")

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

        # Calculate theoretical minimum
        total_area = sum(
            abs(
                sum(
                    contour_groups[i][j].x
                    * contour_groups[i][(j + 1) % len(contour_groups[i])].y
                    - contour_groups[i][(j + 1) % len(contour_groups[i])].x
                    * contour_groups[i][j].y
                    for j in range(len(contour_groups[i]))
                )
                / 2
            )
            for i in range(len(contour_groups))
        )
        theoretical_min = total_area / CUTTER_WIDTH_CM

        print(f"Pieces: {len(contour_groups)}")
        print(f"Fabric width: {CUTTER_WIDTH_CM} cm")
        print(f"Total piece area: {total_area:.1f} sq cm")
        print(f"Theoretical min length: {theoretical_min:.1f} cm (100% util)")

        if args.compare:
            from nesting_engine import nest_bottom_left_fill
            from improved_nesting import guillotine_nest, skyline_nest

            print(
                f"\n{'Algorithm':<15} {'Utilization':<12} {'Length':<12} {'vs Theory':<12} {'Time'}"
            )
            print("-" * 70)

            algorithms = [
                (
                    "shelf",
                    lambda: nest_bottom_left_fill(contour_groups, CUTTER_WIDTH_CM),
                ),
                (
                    "guillotine",
                    lambda: guillotine_nest(contour_groups, CUTTER_WIDTH_CM),
                ),
                ("skyline", lambda: skyline_nest(contour_groups, CUTTER_WIDTH_CM)),
                ("hybrid", lambda: hybrid_nest(contour_groups, CUTTER_WIDTH_CM)),
            ]

            for name, func in algorithms:
                t0 = time.time()
                try:
                    result = func()
                    elapsed = time.time() - t0
                    vs_theory = (
                        (theoretical_min / result.fabric_length * 100)
                        if result.fabric_length > 0
                        else 0
                    )
                    print(
                        f"{name:<15} {result.utilization:>9.1f}%  {result.fabric_length:>9.1f} cm  {vs_theory:>9.1f}%  {elapsed:>6.1f}s"
                    )
                except Exception as e:
                    print(f"{name:<15} FAILED: {str(e)[:30]}")

            print("-" * 70)

        elif args.best:
            print("\nRunning best_of_all...")
            t0 = time.time()
            result = best_of_all(contour_groups)
            elapsed = time.time() - t0

            print(f"\n{result.message}")
            print(f"Fabric length: {result.fabric_length:.1f} cm")
            print(f"Time: {elapsed:.1f} seconds")
        else:
            print("\nRunning hybrid nesting...")
            t0 = time.time()
            result = hybrid_nest(contour_groups)
            elapsed = time.time() - t0

            print(f"\n{result.message}")
            print(f"Fabric length: {result.fabric_length:.1f} cm")
            print(f"Time: {elapsed:.1f} seconds")


if __name__ == "__main__":
    main()
