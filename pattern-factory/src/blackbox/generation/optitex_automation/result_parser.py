"""
Optitex Result Parser

Parses Optitex output files (PLT, MRK, reports) for results and metrics.

Author: AI Agent
Date: January 2026
"""

import re
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class NestingResult:
    """Parsed nesting result metrics."""

    marker_file: Path
    efficiency: float
    fabric_length: float
    fabric_width: float
    piece_count: int
    utilization_area: float
    waste_area: float
    nesting_time: float
    algorithm_used: str


@dataclass
class PlotResult:
    """Parsed plot file info."""

    plot_file: Path
    file_size: int
    piece_count: int
    bounding_box: tuple  # (width, height)


class ResultParser:
    """Parse Optitex output files."""

    def parse_nesting_report(self, report_path: Path) -> Optional[NestingResult]:
        """
        Parse nesting efficiency report.

        Optitex generates XML or TXT reports with nesting metrics.
        """
        if not report_path.exists():
            return None

        suffix = report_path.suffix.lower()

        if suffix == ".xml":
            return self._parse_xml_report(report_path)
        elif suffix in (".txt", ".rpt"):
            return self._parse_txt_report(report_path)

        return None

    def _parse_xml_report(self, path: Path) -> Optional[NestingResult]:
        """Parse XML format nesting report."""
        try:
            import xml.etree.ElementTree as ET

            tree = ET.parse(path)
            root = tree.getroot()

            # Extract metrics (structure depends on Optitex version)
            efficiency = float(root.findtext(".//Efficiency", "0"))
            length = float(root.findtext(".//MarkerLength", "0"))
            width = float(root.findtext(".//FabricWidth", "0"))
            pieces = int(root.findtext(".//PieceCount", "0"))

            return NestingResult(
                marker_file=path,
                efficiency=efficiency,
                fabric_length=length,
                fabric_width=width,
                piece_count=pieces,
                utilization_area=length * width * (efficiency / 100),
                waste_area=length * width * (1 - efficiency / 100),
                nesting_time=float(root.findtext(".//NestingTime", "0")),
                algorithm_used=root.findtext(".//Algorithm", "unknown"),
            )
        except Exception:
            return None

    def _parse_txt_report(self, path: Path) -> Optional[NestingResult]:
        """Parse text format nesting report."""
        try:
            content = path.read_text(encoding="utf-8")

            # Regex patterns for common report formats
            efficiency_match = re.search(r"Efficiency[:\s]+(\d+\.?\d*)%?", content)
            length_match = re.search(r"Length[:\s]+(\d+\.?\d*)", content)
            width_match = re.search(r"Width[:\s]+(\d+\.?\d*)", content)
            pieces_match = re.search(r"Pieces?[:\s]+(\d+)", content)

            efficiency = float(efficiency_match.group(1)) if efficiency_match else 0
            length = float(length_match.group(1)) if length_match else 0
            width = float(width_match.group(1)) if width_match else 0
            pieces = int(pieces_match.group(1)) if pieces_match else 0

            return NestingResult(
                marker_file=path,
                efficiency=efficiency,
                fabric_length=length,
                fabric_width=width,
                piece_count=pieces,
                utilization_area=length * width * (efficiency / 100),
                waste_area=length * width * (1 - efficiency / 100),
                nesting_time=0,
                algorithm_used="unknown",
            )
        except Exception:
            return None

    def parse_plt_file(self, plt_path: Path) -> Optional[PlotResult]:
        """
        Parse PLT (HPGL) file for basic metrics.

        PLT files are HPGL commands - we can extract bounding box
        and piece count from PU/PD commands.
        """
        if not plt_path.exists():
            return None

        try:
            content = plt_path.read_text(encoding="utf-8", errors="ignore")

            # Find all coordinates in PU (pen up) and PD (pen down) commands
            coords = re.findall(r"P[UD](\d+),(\d+)", content)

            if not coords:
                return None

            x_coords = [int(c[0]) for c in coords]
            y_coords = [int(c[1]) for c in coords]

            # Bounding box in plotter units (typically 0.025mm per unit)
            min_x, max_x = min(x_coords), max(x_coords)
            min_y, max_y = min(y_coords), max(y_coords)

            # Convert to mm (assuming standard HPGL units)
            width_mm = (max_x - min_x) * 0.025
            height_mm = (max_y - min_y) * 0.025

            # Count PU commands as rough piece estimate
            pen_ups = content.count("PU")

            return PlotResult(
                plot_file=plt_path,
                file_size=plt_path.stat().st_size,
                piece_count=pen_ups // 2,  # Rough estimate
                bounding_box=(width_mm, height_mm),
            )
        except Exception:
            return None

    def scan_output_directory(self, output_dir: Path) -> Dict[str, List]:
        """
        Scan output directory for all result files.

        Returns dict with categorized results.
        """
        results = {
            "nesting_reports": [],
            "plot_files": [],
            "marker_files": [],
            "dxf_files": [],
            "errors": [],
        }

        if not output_dir.exists():
            return results

        for file_path in output_dir.rglob("*"):
            if file_path.is_dir():
                continue

            suffix = file_path.suffix.lower()

            if (
                suffix in (".xml", ".rpt", ".txt")
                and "report" in file_path.stem.lower()
            ):
                report = self.parse_nesting_report(file_path)
                if report:
                    results["nesting_reports"].append(report)

            elif suffix == ".plt":
                plot = self.parse_plt_file(file_path)
                if plot:
                    results["plot_files"].append(plot)

            elif suffix == ".mrk":
                results["marker_files"].append(file_path)

            elif suffix == ".dxf":
                results["dxf_files"].append(file_path)

        return results
