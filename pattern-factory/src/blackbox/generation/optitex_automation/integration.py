"""
Optitex Automation Integration

Complete integration module connecting the Black Box pipeline to Optitex.

Usage:
    from optitex_automation.integration import OptitexIntegration

    integration = OptitexIntegration()
    result = integration.process_to_optitex(
        measurements={...},
        order_id="ORD-001",
        style_template="suit_template.pds"
    )

Author: AI Agent
Date: January 2026
"""

import sys
from pathlib import Path
from typing import Dict, Optional
from dataclasses import dataclass
import logging

# Import from the same package
from blackbox.generation.optitex_automation.batch_generator import BatchGenerator
from blackbox.generation.optitex_automation.executor import (
    OptitexExecutor,
    ExecutionResult,
)
from blackbox.generation.optitex_automation.result_parser import ResultParser
from blackbox.generation.optitex_automation.config import get_optitex_config

# Get config singleton
config = get_optitex_config()

logger = logging.getLogger(__name__)


@dataclass
class OptitexResult:
    """Result of Optitex automation workflow."""

    success: bool
    script_path: Optional[Path]
    execution_result: Optional[ExecutionResult]
    output_files: Dict[str, Path]
    errors: list


class OptitexIntegration:
    """
    High-level integration between Black Box pipeline and Optitex.

    Orchestrates:
    1. Generate batch scripts from measurements
    2. Execute in Optitex PDS
    3. Parse output files
    """

    def __init__(
        self, style_template_dir: Optional[Path] = None, auto_execute: bool = True
    ):
        """
        Initialize Optitex integration.

        Args:
            style_template_dir: Directory containing .pds style templates
            auto_execute: Whether to automatically execute generated scripts
        """
        self.style_template_dir = style_template_dir or config.input_dir
        self.auto_execute = auto_execute

        # Initialize components
        self.batch_generator = BatchGenerator()
        self.executor = OptitexExecutor()
        self.result_parser = ResultParser()

        logger.info("Optitex integration initialized")

    def process_to_optitex(
        self,
        measurements: Dict[str, float],
        order_id: str,
        style_template: str,
        fabric_width: float = 150.0,
        execute: bool = None,
    ) -> OptitexResult:
        """
        Process measurements through Optitex to generate patterns.

        Args:
            measurements: Pattern parameters from M. Muller translator
            order_id: Unique order identifier
            style_template: Name of style template file (e.g., "suit_v1.pds")
            fabric_width: Fabric width in cm
            execute: Whether to execute (overrides auto_execute)

        Returns:
            OptitexResult with paths to output files
        """
        errors = []

        try:
            # Find style template
            template_path = self.style_template_dir / style_template
            if not template_path.exists():
                # Try common locations
                alt_paths = [
                    Path(r"C:\Optitex\Styles") / style_template,
                    config.input_dir / style_template,
                ]
                for alt in alt_paths:
                    if alt.exists():
                        template_path = alt
                        break
                else:
                    errors.append(f"Style template not found: {style_template}")
                    return OptitexResult(
                        success=False,
                        script_path=None,
                        execution_result=None,
                        output_files={},
                        errors=errors,
                    )

            # Generate workflow script
            logger.info(f"Generating Optitex workflow for {order_id}")

            workflow = self.batch_generator.generate_complete_workflow(
                measurements=measurements,
                style_template=template_path,
                fabric_width=fabric_width,
                order_id=order_id,
            )

            script_path = workflow["workflow_script"]

            # Execute if requested
            should_execute = execute if execute is not None else self.auto_execute

            if should_execute:
                logger.info(f"Executing Optitex script: {script_path}")

                execution_result = self.executor.run_pds_batch(script_path)

                if not execution_result.success:
                    errors.append(
                        f"Optitex execution failed: {execution_result.stderr}"
                    )
                else:
                    logger.info(
                        f"Optitex completed in {execution_result.duration_seconds:.1f}s"
                    )
            else:
                execution_result = None
                logger.info(f"Script generated (not executed): {script_path}")

            # Scan for output files
            output_dir = config.output_dir / order_id
            output_files = {}

            if output_dir.exists():
                for ext in [".dxf", ".plt", ".mrk"]:
                    files = list(output_dir.glob(f"*{ext}"))
                    if files:
                        output_files[ext.lstrip(".")] = files[0]

            return OptitexResult(
                success=len(errors) == 0,
                script_path=script_path,
                execution_result=execution_result,
                output_files=output_files,
                errors=errors,
            )

        except Exception as e:
            errors.append(f"Integration error: {e}")
            logger.exception("Optitex integration failed")

            return OptitexResult(
                success=False,
                script_path=None,
                execution_result=None,
                output_files={},
                errors=errors,
            )

    def get_nesting_metrics(self, order_id: str) -> Optional[Dict]:
        """
        Get nesting efficiency metrics for an order.

        Args:
            order_id: Order identifier

        Returns:
            Dict with nesting metrics or None
        """
        output_dir = config.output_dir / order_id

        if not output_dir.exists():
            return None

        results = self.result_parser.scan_output_directory(output_dir)

        metrics = {
            "nesting_reports": len(results["nesting_reports"]),
            "plot_files": len(results["plot_files"]),
            "marker_files": len(results["marker_files"]),
            "dxf_files": len(results["dxf_files"]),
        }

        if results["nesting_reports"]:
            report = results["nesting_reports"][0]
            metrics["efficiency"] = report.efficiency
            metrics["fabric_length"] = report.fabric_length
            metrics["fabric_width"] = report.fabric_width
            metrics["piece_count"] = report.piece_count

        return metrics


# Convenience function
def measurements_to_optitex(
    measurements: Dict[str, float],
    order_id: str,
    style_template: str = "suit_template.pds",
    fabric_width: float = 150.0,
    execute: bool = True,
) -> OptitexResult:
    """
    Convenience function to process measurements through Optitex.

    Args:
        measurements: Pattern parameters from M. Muller
        order_id: Order identifier
        style_template: Style template filename
        fabric_width: Fabric width in cm
        execute: Whether to execute immediately

    Returns:
        OptitexResult with output file paths
    """
    integration = OptitexIntegration(auto_execute=execute)
    return integration.process_to_optitex(
        measurements=measurements,
        order_id=order_id,
        style_template=style_template,
        fabric_width=fabric_width,
        execute=execute,
    )
