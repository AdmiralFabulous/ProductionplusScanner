"""
DXF/HPGL Output Module using ezdxf

Creates pattern pieces in DXF format and converts to HPGL for plotters.

Based on BUILD RECOMMENDATIONS:
- ezdxf (MIT) - PRIMARY for DXF/HPGL output
- Score: 68/70 - Best in class
- Supports full DXF R12-R2010, HPGL/2 conversion

Author: AI Agent
Date: January 2026
"""

import ezdxf
from pathlib import Path
from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass
import logging

# Try to import HPGL converter, but don't fail if not available
try:
    from ezdxf.addons.hpgl2 import to_hpgl2

    HPGL_AVAILABLE = True
except ImportError:
    HPGL_AVAILABLE = False
    to_hpgl2 = None

logger = logging.getLogger(__name__)


class DXFOutputError(Exception):
    """Raised when DXF generation fails."""

    pass


@dataclass
class PatternPiece:
    """Single pattern piece definition."""

    name: str
    points: List[Tuple[float, float]]  # Closed polyline
    notches: List[Tuple[Tuple[float, float], Tuple[float, float]]] = None
    grain_line: Optional[Tuple[Tuple[float, float], Tuple[float, float]]] = None
    label: Optional[str] = None


class DXFGenerator:
    """Generate DXF files from pattern parameters."""

    def __init__(self, dxfversion: str = "R2010"):
        """
        Initialize DXF generator.

        Args:
            dxfversion: DXF version (R12, R2000, R2004, R2007, R2010, R2013, R2018)
        """
        self.dxfversion = dxfversion
        self.doc = None
        self.msp = None
        self._setup_document()

    def _setup_document(self):
        """Setup new DXF document with standard layers."""
        self.doc = ezdxf.new(dxfversion=self.dxfversion)
        self.msp = self.doc.modelspace()

        # Create standard layers
        self.doc.layers.add("CUT", color=7)  # White - cutting line
        self.doc.layers.add("NOTCH", color=1)  # Red - notches
        self.doc.layers.add("GRAIN", color=3)  # Green - grain line
        self.doc.layers.add("TEXT", color=5)  # Blue - labels
        self.doc.layers.add("CONSTRUCTION", color=8)  # Gray - construction lines

        logger.info(f"Created DXF document version {self.dxfversion}")

    def add_pattern_piece(
        self, piece: PatternPiece, offset: Tuple[float, float] = (0, 0)
    ) -> None:
        """
        Add a pattern piece to the DXF.

        Args:
            piece: PatternPiece to add
            offset: (x, y) offset for placement
        """
        # Apply offset to points
        offset_points = [(x + offset[0], y + offset[1]) for x, y in piece.points]

        # Draw main outline
        self.msp.add_lwpolyline(offset_points, close=True, dxfattribs={"layer": "CUT"})

        # Draw notches
        if piece.notches:
            for start, end in piece.notches:
                start_offset = (start[0] + offset[0], start[1] + offset[1])
                end_offset = (end[0] + offset[0], end[1] + offset[1])
                self.msp.add_line(
                    start_offset, end_offset, dxfattribs={"layer": "NOTCH"}
                )

        # Draw grain line
        if piece.grain_line:
            start, end = piece.grain_line
            start_offset = (start[0] + offset[0], start[1] + offset[1])
            end_offset = (end[0] + offset[0], end[1] + offset[1])
            self.msp.add_line(start_offset, end_offset, dxfattribs={"layer": "GRAIN"})

        # Add label
        label = piece.label or piece.name
        bbox = self._calculate_bounding_box(piece.points)
        label_pos = (bbox[0] + offset[0] + 5, bbox[1] + offset[1] - 10)

        self.msp.add_text(
            label, dxfattribs={"layer": "TEXT", "height": 3}
        ).set_placement(label_pos)

        logger.debug(f"Added pattern piece: {piece.name}")

    def add_suit_jacket(
        self, params: Dict[str, float], offset: Tuple[float, float] = (0, 0)
    ) -> None:
        """
        Add suit jacket pieces based on M. Muller parameters.

        Args:
            params: Pattern parameters from M. Muller translator
            offset: (x, y) offset for placement
        """
        # Extract parameters
        half_chest = params.get("HALF_CHEST", 52)
        half_waist = params.get("HALF_WAIST", 46)
        back_length = params.get("BACK_LENGTH_NAPE_TO_WAIST", 44)
        front_width = params.get("FRONT_WIDTH", 27)
        back_width = params.get("BACK_WIDTH", 25)
        scye_depth = params.get("SCYE_DEPTH", 25)

        # Back panel
        back_points = [
            (0, 0),
            (back_width, 0),
            (back_width, back_length - 2),
            (back_width * 0.7, back_length),
            (0, back_length),
            (0, 0),
        ]

        back_notches = [
            (
                (back_width * 0.5, back_length - scye_depth),
                (back_width * 0.5 + 2, back_length - scye_depth),
            ),
        ]

        back_piece = PatternPiece(
            name="Jacket_Back",
            points=back_points,
            notches=back_notches,
            grain_line=((5, 10), (5, back_length - 10)),
            label="JACKET BACK",
        )

        self.add_pattern_piece(back_piece, offset)

        # Front panel
        front_offset = (back_width + 10, 0)
        front_points = [
            (0, 0),
            (front_width, 0),
            (front_width, back_length - 5),
            (front_width - 5, back_length),
            (0, back_length + 2),
            (0, 0),
        ]

        front_piece = PatternPiece(
            name="Jacket_Front",
            points=front_points,
            grain_line=((5, 10), (5, back_length - 10)),
            label="JACKET FRONT",
        )

        self.add_pattern_piece(front_piece, (offset[0] + front_offset[0], offset[1]))

        logger.info(f"Added suit jacket pieces")

    def add_sleeve(
        self, params: Dict[str, float], offset: Tuple[float, float] = (0, 0)
    ) -> None:
        """Add sleeve piece."""
        sleeve_length = params.get("SLEEVE_LENGTH", 64)
        upper_arm = params.get("UPPER_ARM_WIDTH", 18)
        elbow = params.get("ELBOW_WIDTH", 15)
        cuff = params.get("CUFF_WIDTH", 12)

        # Sleeve shape
        sleeve_points = [
            (0, 0),
            (upper_arm, 0),
            (upper_arm - 1, sleeve_length * 0.5),  # Elbow
            (cuff, sleeve_length),
            (0, sleeve_length),
            (-1, sleeve_length * 0.5),  # Elbow inner
            (0, 0),
        ]

        sleeve_piece = PatternPiece(
            name="Sleeve",
            points=sleeve_points,
            grain_line=((upper_arm / 2, 10), (upper_arm / 2, sleeve_length - 10)),
            label="SLEEVE",
        )

        self.add_pattern_piece(sleeve_piece, offset)

    def save_dxf(self, output_path: Path) -> None:
        """
        Save DXF to file.

        Args:
            output_path: Path to save DXF file
        """
        self.doc.saveas(str(output_path))
        logger.info(f"DXF saved to {output_path}")

    def export_to_hpgl(self, output_path: Path) -> None:
        """
        Export to HPGL/2 format for plotters.

        Args:
            output_path: Path to save HPGL file
        """
        if not HPGL_AVAILABLE or to_hpgl2 is None:
            logger.warning("HPGL export not available, saving placeholder")
            output_path.write_text(
                "; HPGL export requires ezdxf hpgl2 addon", encoding="utf-8"
            )
            return

        hpgl_content = to_hpgl2(self.msp)
        output_path.write_text(hpgl_content, encoding="utf-8")
        logger.info(f"HPGL saved to {output_path}")

    def _calculate_bounding_box(
        self, points: List[Tuple[float, float]]
    ) -> Tuple[float, float, float, float]:
        """Calculate bounding box of points."""
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        return (min(xs), min(ys), max(xs), max(ys))

    def get_bounds(self) -> Tuple[float, float, float, float]:
        """Get bounding box of all entities."""
        try:
            # Try old API (ezdxf < 1.2)
            extents = self.msp.query("LINE LWPOLYLINE").get_bbox()
            if extents:
                return (
                    extents.extmin[0],
                    extents.extmin[1],
                    extents.extmax[0],
                    extents.extmax[1],
                )
        except AttributeError:
            # Fallback: calculate manually (ezdxf >= 1.2)
            all_points = []
            for entity in self.msp.query("LINE LWPOLYLINE"):
                if entity.dxftype() == "LINE":
                    all_points.append((entity.dxf.start[0], entity.dxf.start[1]))
                    all_points.append((entity.dxf.end[0], entity.dxf.end[1]))
                elif entity.dxftype() == "LWPOLYLINE":
                    with entity.points() as points:
                        for point in points:
                            all_points.append((point[0], point[1]))

            if all_points:
                xs = [p[0] for p in all_points]
                ys = [p[1] for p in all_points]
                return (min(xs), min(ys), max(xs), max(ys))

        return (0, 0, 0, 0)


def generate_suit_patterns(
    pattern_params: Dict[str, float],
    output_dxf: Path,
    output_hpgl: Optional[Path] = None,
) -> None:
    """
    Convenience function to generate complete suit patterns.

    Args:
        pattern_params: M. Muller pattern parameters
        output_dxf: Output path for DXF file
        output_hpgl: Optional output path for HPGL file
    """
    generator = DXFGenerator()

    # Add jacket pieces
    generator.add_suit_jacket(pattern_params, offset=(0, 0))

    # Add sleeves
    generator.add_sleeve(pattern_params, offset=(100, 0))

    # Save DXF
    generator.save_dxf(output_dxf)

    # Export HPGL if requested
    if output_hpgl:
        generator.export_to_hpgl(output_hpgl)

    logger.info(f"Generated suit patterns: DXF={output_dxf}, HPGL={output_hpgl}")


if __name__ == "__main__":
    # Example usage
    test_params = {
        "HALF_CHEST": 52.0,
        "HALF_WAIST": 46.0,
        "BACK_LENGTH_NAPE_TO_WAIST": 44.0,
        "FRONT_WIDTH": 27.0,
        "BACK_WIDTH": 25.0,
        "SCYE_DEPTH": 25.0,
        "SLEEVE_LENGTH": 64.0,
        "UPPER_ARM_WIDTH": 18.0,
        "ELBOW_WIDTH": 15.0,
        "CUFF_WIDTH": 12.0,
    }

    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)

    generate_suit_patterns(
        test_params,
        output_dxf=output_dir / "suit_pattern.dxf",
        output_hpgl=output_dir / "suit_pattern.plt",
    )

    print("Pattern files generated successfully!")
