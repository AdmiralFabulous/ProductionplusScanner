#!/usr/bin/env python3
"""
Nesting Engine: Bin-packing algorithm for pattern pieces on fabric

This module optimizes the layout of pattern pieces on 62" (157.48 cm) fabric
to minimize waste and ensure all pieces fit within the cutter width.

Algorithm: Bottom-Left Fill with Rotation
1. Calculate bounding box for each piece
2. Sort pieces by height (largest first)
3. Place each piece at lowest available Y position, as far left as possible
4. Try 0, 90, 180, 270 degree rotations to find best fit

Author: Claude
Date: 2026-01-30
"""

import math
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
from copy import deepcopy


# Constants
CUTTER_WIDTH_CM = 157.48  # 62 inches
GAP_CM = 0.5  # Gap between pieces for cutting


@dataclass
class Point:
    x: float
    y: float


@dataclass
class BoundingBox:
    min_x: float
    min_y: float
    max_x: float
    max_y: float

    @property
    def width(self) -> float:
        return self.max_x - self.min_x

    @property
    def height(self) -> float:
        return self.max_y - self.min_y

    @property
    def area(self) -> float:
        return self.width * self.height


@dataclass
class NestedPiece:
    """A piece after nesting with position and rotation."""

    piece_id: int
    original_points: List[Point]
    transformed_points: List[Point]
    bbox: BoundingBox
    position: Tuple[float, float]  # (x, y) offset
    rotation: int  # 0, 90, 180, 270 degrees

    @property
    def final_bbox(self) -> BoundingBox:
        """Get bounding box after positioning."""
        return BoundingBox(
            min_x=self.bbox.min_x + self.position[0],
            min_y=self.bbox.min_y + self.position[1],
            max_x=self.bbox.max_x + self.position[0],
            max_y=self.bbox.max_y + self.position[1],
        )


@dataclass
class NestingResult:
    """Result of nesting operation."""

    pieces: List[NestedPiece]
    fabric_width: float
    fabric_length: float
    utilization: float  # Percentage of fabric used
    success: bool
    message: str


def calculate_bbox(points: List[Point]) -> BoundingBox:
    """Calculate bounding box for a set of points."""
    if not points:
        return BoundingBox(0, 0, 0, 0)

    xs = [p.x for p in points]
    ys = [p.y for p in points]

    return BoundingBox(
        min_x=min(xs),
        min_y=min(ys),
        max_x=max(xs),
        max_y=max(ys),
    )


def rotate_points(
    points: List[Point], degrees: int, center: Tuple[float, float] = None
) -> List[Point]:
    """Rotate points around center (or their centroid if not specified)."""
    if not points:
        return []

    # Calculate center if not provided
    if center is None:
        cx = sum(p.x for p in points) / len(points)
        cy = sum(p.y for p in points) / len(points)
    else:
        cx, cy = center

    # Convert to radians
    rad = math.radians(degrees)
    cos_a = math.cos(rad)
    sin_a = math.sin(rad)

    rotated = []
    for p in points:
        # Translate to origin
        dx = p.x - cx
        dy = p.y - cy

        # Rotate
        new_x = dx * cos_a - dy * sin_a
        new_y = dx * sin_a + dy * cos_a

        # Translate back
        rotated.append(Point(new_x + cx, new_y + cy))

    return rotated


def normalize_to_origin(points: List[Point]) -> List[Point]:
    """Move points so bounding box starts at (0, 0)."""
    if not points:
        return []

    bbox = calculate_bbox(points)
    return [Point(p.x - bbox.min_x, p.y - bbox.min_y) for p in points]


def check_overlap(box1: BoundingBox, box2: BoundingBox, gap: float = GAP_CM) -> bool:
    """Check if two bounding boxes overlap (with gap)."""
    return not (
        box1.max_x + gap <= box2.min_x
        or box2.max_x + gap <= box1.min_x
        or box1.max_y + gap <= box2.min_y
        or box2.max_y + gap <= box1.min_y
    )


def find_best_rotation(
    points: List[Point], fabric_width: float, rotations: List[int] = [0, 90, 180, 270]
) -> Tuple[List[Point], int, BoundingBox]:
    """Find rotation that best fits within fabric width.

    Always returns normalized points (bounding box starting at origin).
    """
    # Start with normalized 0-degree rotation as default
    normalized_0 = normalize_to_origin(points)
    best_points = normalized_0
    best_rotation = 0
    best_bbox = calculate_bbox(normalized_0)

    for rotation in rotations:
        if rotation == 0:
            rotated = normalized_0  # Already computed
        else:
            rotated = rotate_points(points, rotation)
            rotated = normalize_to_origin(rotated)
        bbox = calculate_bbox(rotated)

        # Prefer rotation where width fits within fabric
        if bbox.width <= fabric_width:
            # If both fit, prefer smaller width (more efficient)
            if best_bbox.width > fabric_width or bbox.width < best_bbox.width:
                best_points = rotated
                best_rotation = rotation
                best_bbox = bbox

    return best_points, best_rotation, best_bbox


class Shelf:
    """A horizontal shelf for shelf-based bin packing."""

    def __init__(self, y: float, height: float, width: float):
        self.y = y  # Bottom Y position
        self.height = height
        self.width = width
        self.items: List[Tuple[float, float, float]] = []  # (x, width, piece_id)
        self.next_x = 0.0

    def can_fit(
        self, item_width: float, item_height: float, gap: float = GAP_CM
    ) -> bool:
        """Check if item can fit on this shelf."""
        return (
            item_height <= self.height + gap and self.next_x + item_width <= self.width
        )

    def add_item(self, item_width: float, piece_id: int, gap: float = GAP_CM) -> float:
        """Add item to shelf, returns X position."""
        x = self.next_x
        self.items.append((x, item_width, piece_id))
        self.next_x = x + item_width + gap
        return x


def nest_bottom_left_fill(
    contour_groups: List[List[Point]],
    fabric_width: float = CUTTER_WIDTH_CM,
    gap: float = GAP_CM,
    allow_rotation: bool = True,
) -> NestingResult:
    """
    Nest pattern pieces using bottom-left fill algorithm.

    This algorithm:
    1. Sorts pieces by height (decreasing)
    2. Places each piece at the lowest Y position possible
    3. Within that Y level, places as far left as possible
    4. Tries rotations to optimize fit
    """
    if not contour_groups:
        return NestingResult(
            pieces=[],
            fabric_width=fabric_width,
            fabric_length=0,
            utilization=0,
            success=True,
            message="No pieces to nest",
        )

    # Prepare pieces with best rotation
    prepared_pieces = []
    for i, points in enumerate(contour_groups):
        if not points:
            continue

        if allow_rotation:
            rotated_points, rotation, bbox = find_best_rotation(points, fabric_width)
        else:
            rotated_points = normalize_to_origin(points)
            rotation = 0
            bbox = calculate_bbox(rotated_points)

        prepared_pieces.append(
            {
                "id": i,
                "original": points,
                "points": rotated_points,
                "rotation": rotation,
                "bbox": bbox,
            }
        )

    # Check if any piece is wider than fabric
    oversized = [p for p in prepared_pieces if p["bbox"].width > fabric_width]
    if oversized:
        # Try rotating oversized pieces
        for piece in oversized:
            if piece["bbox"].height <= fabric_width:
                # Rotate 90 degrees
                rotated = rotate_points(piece["original"], 90)
                rotated = normalize_to_origin(rotated)
                piece["points"] = rotated
                piece["rotation"] = 90
                piece["bbox"] = calculate_bbox(rotated)

        # Re-check
        still_oversized = [p for p in prepared_pieces if p["bbox"].width > fabric_width]
        if still_oversized:
            return NestingResult(
                pieces=[],
                fabric_width=fabric_width,
                fabric_length=0,
                utilization=0,
                success=False,
                message=f"Pieces too large for fabric: {[p['id'] for p in still_oversized]}",
            )

    # Sort by height (largest first) for better packing
    prepared_pieces.sort(key=lambda p: p["bbox"].height, reverse=True)

    # Shelf-based packing
    shelves: List[Shelf] = []
    placed_pieces: List[NestedPiece] = []

    for piece in prepared_pieces:
        bbox = piece["bbox"]
        placed = False

        # Try to fit on existing shelf
        for shelf in shelves:
            if shelf.can_fit(bbox.width, bbox.height, gap):
                x = shelf.add_item(bbox.width, piece["id"], gap)
                y = shelf.y

                placed_pieces.append(
                    NestedPiece(
                        piece_id=piece["id"],
                        original_points=piece["original"],
                        transformed_points=piece["points"],
                        bbox=bbox,
                        position=(x, y),
                        rotation=piece["rotation"],
                    )
                )
                placed = True
                break

        if not placed:
            # Create new shelf
            if shelves:
                new_y = max(s.y + s.height for s in shelves) + gap
            else:
                new_y = 0

            shelf = Shelf(new_y, bbox.height, fabric_width)
            x = shelf.add_item(bbox.width, piece["id"], gap)
            shelves.append(shelf)

            placed_pieces.append(
                NestedPiece(
                    piece_id=piece["id"],
                    original_points=piece["original"],
                    transformed_points=piece["points"],
                    bbox=bbox,
                    position=(x, new_y),
                    rotation=piece["rotation"],
                )
            )

    # Calculate total fabric length needed
    if shelves:
        fabric_length = max(s.y + s.height for s in shelves)
    else:
        fabric_length = 0

    # Calculate utilization
    total_piece_area = sum(p.bbox.area for p in placed_pieces)
    fabric_area = fabric_width * fabric_length if fabric_length > 0 else 1
    utilization = (total_piece_area / fabric_area) * 100

    return NestingResult(
        pieces=placed_pieces,
        fabric_width=fabric_width,
        fabric_length=fabric_length,
        utilization=utilization,
        success=True,
        message=f"Nested {len(placed_pieces)} pieces in {fabric_length:.2f} cm",
    )


def get_nested_contours(
    contours,  # List of Contour objects from production_pipeline
    fabric_width: float = CUTTER_WIDTH_CM,
    gap: float = GAP_CM,
):
    """
    High-level function to nest contours from production_pipeline.

    Takes Contour objects and returns transformed points ready for HPGL.
    """
    # Extract point lists from contours
    contour_groups = []
    for c in contours:
        points = [Point(p.x, p.y) for p in c.points]
        contour_groups.append(points)

    # Nest
    result = nest_bottom_left_fill(contour_groups, fabric_width, gap)

    if not result.success:
        print(f"  WARNING: Nesting failed - {result.message}")
        return None, result

    # Transform contours to their nested positions
    nested_contours = []
    for nested_piece in result.pieces:
        transformed_points = []
        for p in nested_piece.transformed_points:
            transformed_points.append(
                Point(
                    x=p.x + nested_piece.position[0],
                    y=p.y + nested_piece.position[1],
                )
            )
        nested_contours.append(transformed_points)

    return nested_contours, result


def visualize_nesting(result: NestingResult, output_path: str = None):
    """Generate simple ASCII visualization of nesting result."""
    if not result.success or not result.pieces:
        print("Cannot visualize: nesting failed or no pieces")
        return

    # Scale to fit in terminal
    scale = 80 / result.fabric_width
    height_chars = int(result.fabric_length * scale) + 1
    width_chars = 80

    # Create grid
    grid = [[" " for _ in range(width_chars)] for _ in range(height_chars)]

    # Draw pieces
    for i, piece in enumerate(result.pieces):
        bbox = piece.final_bbox
        x1 = int(bbox.min_x * scale)
        y1 = int(bbox.min_y * scale)
        x2 = int(bbox.max_x * scale)
        y2 = int(bbox.max_y * scale)

        char = chr(ord("A") + (i % 26))

        for y in range(max(0, y1), min(height_chars, y2 + 1)):
            for x in range(max(0, x1), min(width_chars, x2 + 1)):
                if y == y1 or y == y2 or x == x1 or x == x2:
                    grid[y][x] = char

    # Print
    print(f"\nNesting Visualization (scale: {scale:.2f})")
    print("=" * width_chars)
    for row in grid:
        print("".join(row))
    print("=" * width_chars)
    print(f"Fabric: {result.fabric_width:.1f} x {result.fabric_length:.1f} cm")
    print(f"Utilization: {result.utilization:.1f}%")


if __name__ == "__main__":
    # Test with sample data
    print("Testing Nesting Engine")
    print("=" * 60)

    # Create sample pieces (rectangles for testing)
    test_pieces = [
        [Point(0, 0), Point(50, 0), Point(50, 80), Point(0, 80)],  # Large piece
        [Point(0, 0), Point(40, 0), Point(40, 60), Point(0, 60)],  # Medium piece
        [Point(0, 0), Point(30, 0), Point(30, 40), Point(0, 40)],  # Small piece
        [Point(0, 0), Point(60, 0), Point(60, 30), Point(0, 30)],  # Wide piece
        [Point(0, 0), Point(25, 0), Point(25, 70), Point(0, 70)],  # Tall piece
    ]

    result = nest_bottom_left_fill(test_pieces, fabric_width=CUTTER_WIDTH_CM)

    print(f"\nResult: {result.message}")
    print(f"Fabric needed: {result.fabric_width:.1f} x {result.fabric_length:.1f} cm")
    print(f"Utilization: {result.utilization:.1f}%")

    print("\nPiece placements:")
    for piece in result.pieces:
        print(
            f"  Piece {piece.piece_id}: position={piece.position}, rotation={piece.rotation}deg"
        )

    visualize_nesting(result)
