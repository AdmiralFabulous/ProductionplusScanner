"""
Optitex Batch Script Generator

Generates Optitex batch scripts (.bat/.txt) from measurements and parameters.

Author: AI Agent
Date: January 2026
"""

from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
import uuid

from .config import config


@dataclass
class PatternJob:
    """Single pattern processing job."""

    style_file: Path
    sizes: List[str]
    quantities: Dict[str, int]
    fabric_width: float
    output_format: str = "PLT"


@dataclass
class NestingJob:
    """Single nesting job."""

    marker_file: Path
    fabric_width: float
    max_length: float
    algorithm: str = "standard"
    time_limit: int = 300
    efficiency_target: float = 85.0


class BatchGenerator:
    """Generate Optitex batch scripts."""

    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = output_dir or config.scripts_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _generate_script_id(self) -> str:
        """Generate unique script identifier."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        short_uuid = str(uuid.uuid4())[:8]
        return f"{timestamp}_{short_uuid}"

    def generate_pattern_from_measurements(
        self,
        measurements: Dict[str, float],
        style_template: Path,
        output_path: Path,
        order_id: str = "",
    ) -> Path:
        """
        Generate batch script to create pattern from body measurements.

        Args:
            measurements: Dict of pattern parameters from M. Muller
            style_template: Path to Optitex style template (.pds)
            output_path: Path for output files
            order_id: Order identifier

        Returns:
            Path to generated script file
        """
        script_id = self._generate_script_id()
        script_path = self.output_dir / f"pattern_{order_id}_{script_id}.bat"

        # Generate measurement parameter file for BTF
        params_file = self.output_dir / f"params_{order_id}_{script_id}.txt"
        param_lines = [f"{k}={v}" for k, v in measurements.items()]
        params_file.write_text("\n".join(param_lines), encoding="utf-8")

        lines = [
            f"@REM Generated: {datetime.now().isoformat()}",
            f"@REM Order: {order_id}",
            f"@REM Custom pattern from measurements",
            f"@UNIT {config.default_unit}",
            f"@OPEN /FILE={style_template}",
            f"@PARAMS /FILE={params_file}",
            f"@EXPORT /FORMAT=DXF /FILE={output_path.with_suffix('.dxf')}",
            f"@PLOT /FILE={output_path.with_suffix('.plt')} /OPT=PLT",
            "@!",
        ]

        script_path.write_text("\n".join(lines), encoding="utf-8")
        return script_path

    def generate_nesting_script(self, job: NestingJob, output_path: Path) -> Path:
        """
        Generate batch script for marker nesting.

        Args:
            job: NestingJob parameters
            output_path: Path for output files

        Returns:
            Path to generated script file
        """
        script_id = self._generate_script_id()
        script_path = self.output_dir / f"nest_{script_id}.bat"

        alg_code = config.NEST_ALGORITHMS.get(job.algorithm, 2)

        lines = [
            f"@REM Generated: {datetime.now().isoformat()}",
            f"@REM Marker: {job.marker_file.name}",
            f"@UNIT {config.default_unit}",
            f"@MARKER /FILE={job.marker_file}",
            f"@WIDTH /VALUE={job.fabric_width}",
            f"@LENGTH /VALUE={job.max_length}",
            f"@NEST /ALG={alg_code} /TIME={job.time_limit} /EFF={job.efficiency_target}",
            f"@SAVE /FILE={output_path} /FORMAT=MRK",
            f"@PLOT /FILE={output_path.with_suffix('.plt')} /OPT=PLT",
            "@!",
        ]

        script_path.write_text("\n".join(lines), encoding="utf-8")
        return script_path

    def generate_complete_workflow(
        self,
        measurements: Dict[str, float],
        style_template: Path,
        fabric_width: float,
        order_id: str,
    ) -> Dict[str, Path]:
        """
        Generate complete workflow: pattern → nesting → output.

        Args:
            measurements: Pattern parameters
            style_template: Style template path
            fabric_width: Fabric width in cm
            order_id: Order identifier

        Returns:
            Dict with paths to generated scripts
        """
        script_id = self._generate_script_id()

        # Paths
        pattern_output = config.output_dir / order_id / f"{order_id}_pattern"
        marker_output = config.output_dir / order_id / f"{order_id}_marker"

        # Generate measurement params file
        params_file = self.output_dir / f"params_{order_id}_{script_id}.txt"
        param_lines = [f"{k}={v}" for k, v in measurements.items()]
        params_file.write_text("\n".join(param_lines), encoding="utf-8")

        # Combined script
        script_path = self.output_dir / f"workflow_{order_id}_{script_id}.bat"

        lines = [
            f"@REM Generated: {datetime.now().isoformat()}",
            f"@REM Order: {order_id}",
            f"@REM Complete workflow: Pattern → Nesting → Output",
            f"",
            f"@REM === STEP 1: Generate Pattern ===",
            f"@UNIT {config.default_unit}",
            f"@OPEN /FILE={style_template}",
            f"@PARAMS /FILE={params_file}",
            f"@EXPORT /FORMAT=DXF /FILE={pattern_output}.dxf",
            f"",
            f"@REM === STEP 2: Nest Pattern ===",
            f"@MARKER /FILE={pattern_output}.mrk",
            f"@WIDTH /VALUE={fabric_width}",
            f"@NEST /ALG=3 /TIME={config.default_nest_time} /EFF={config.default_efficiency_target}",
            f"@SAVE /FILE={marker_output}.mrk /FORMAT=MRK",
            f"@PLOT /FILE={marker_output}.plt /OPT=PLT",
            f"",
            f"@!",
        ]

        script_path.write_text("\n".join(lines), encoding="utf-8")

        return {
            "workflow_script": script_path,
            "params_file": params_file,
            "pattern_output": pattern_output,
            "marker_output": marker_output,
        }
