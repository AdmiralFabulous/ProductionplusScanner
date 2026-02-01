"""
Complete Optitex Automation Workflow

Fully automated pattern generation from measurements to PLT output.
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import logging
import time
import subprocess

# Import from the same package
from blackbox.generation.optitex_automation.config import get_optitex_config
from blackbox.generation.optitex_automation.template_config import (
    get_template,
    list_templates,
)
from blackbox.generation.optitex_automation.btf_generator import (
    generate_btf_parameters,
    BTFResult,
)
from blackbox.generation.optitex_automation.executor import (
    OptitexExecutor,
    ExecutionResult,
)
from blackbox.generation.optitex_automation.result_parser import ResultParser

# Get config singleton
config = get_optitex_config()

logger = logging.getLogger(__name__)


@dataclass
class AutomationResult:
    """Result of complete automation workflow."""

    success: bool
    order_id: str
    template_name: str
    dxf_file: Optional[Path]
    plt_file: Optional[Path]
    mrk_file: Optional[Path]
    processing_time_seconds: float
    errors: List[str]
    warnings: List[str]
    validation_passed: bool


class OptitexAutomationWorkflow:
    """
    Complete automated workflow for pattern generation.

    Steps:
    1. Validate inputs
    2. Generate BTF parameters (all 3 formats)
    3. Create batch script
    4. Execute in Optitex
    5. Validate outputs
    6. Return results
    """

    def __init__(
        self,
        pds_exe: Optional[Path] = None,
        marker_exe: Optional[Path] = None,
        max_retries: int = 3,
    ):
        """
        Initialize automation workflow.

        Args:
            pds_exe: Path to PDS.exe (uses config default if not specified)
            marker_exe: Path to Marker.exe
            max_retries: Maximum retry attempts on failure
        """
        self.pds_exe = pds_exe or config.pds_exe
        self.marker_exe = marker_exe or config.marker_exe
        self.max_retries = max_retries

        self.executor = OptitexExecutor(
            pds_exe=self.pds_exe, marker_exe=self.marker_exe
        )
        self.result_parser = ResultParser()

        logger.info(f"Automation workflow initialized")
        logger.info(f"PDS: {self.pds_exe}")
        logger.info(f"Marker: {self.marker_exe}")

    def process_order(
        self,
        measurements: Dict[str, float],
        template_name: str,
        order_id: str,
        fabric_width: Optional[float] = None,
        execute: bool = True,
    ) -> AutomationResult:
        """
        Process a complete order from measurements to pattern files.

        Args:
            measurements: Body measurements from scan
            template_name: Template to use (basic_tee, woven_shirt, skinny_trousers)
            order_id: Unique order identifier
            fabric_width: Fabric width in cm (uses template default if not specified)
            execute: If True, actually run Optitex. If False, only generate scripts.

        Returns:
            AutomationResult with file paths and status
        """
        start_time = time.time()
        errors = []
        warnings = []

        try:
            # Step 1: Validate inputs
            logger.info(f"Step 1/6: Validating inputs for order {order_id}")
            template = get_template(template_name)
            output_dir = config.output_dir / order_id
            output_dir.mkdir(parents=True, exist_ok=True)

            if not template.pds_file.exists():
                errors.append(f"Template file not found: {template.pds_file}")
                return self._create_failure_result(
                    order_id, template_name, errors, start_time
                )

            # Use template default fabric width if not specified
            fabric_width = fabric_width or template.default_fabric_width

            # Step 2: Generate BTF parameters (all 3 formats)
            logger.info(f"Step 2/6: Generating BTF parameters")
            btf_result = generate_btf_parameters(
                measurements=measurements,
                template_name=template_name,
                order_id=order_id,
                output_dir=output_dir / "params",
            )

            if btf_result.validation_errors:
                warnings.extend(btf_result.validation_errors)
                logger.warning(
                    f"Measurement validation issues: {btf_result.validation_errors}"
                )

            # Step 3: Create batch script (using Format C - direct commands)
            logger.info(f"Step 3/6: Creating batch script")
            script_path = self._create_batch_script(
                template=template,
                order_id=order_id,
                output_dir=output_dir,
                btf_commands=btf_result.format_c_commands,
                fabric_width=fabric_width,
            )

            if not execute:
                # Stop here if only generating scripts
                processing_time = time.time() - start_time
                return AutomationResult(
                    success=True,
                    order_id=order_id,
                    template_name=template_name,
                    dxf_file=None,
                    plt_file=None,
                    mrk_file=None,
                    processing_time_seconds=processing_time,
                    errors=errors,
                    warnings=warnings,
                    validation_passed=len(btf_result.validation_errors) == 0,
                )

            # Step 4: Execute in Optitex
            logger.info(f"Step 4/6: Executing Optitex batch script")
            execution_result = self._execute_with_retry(script_path)

            if not execution_result.success:
                errors.append(f"Optitex execution failed: {execution_result.stderr}")
                return self._create_failure_result(
                    order_id, template_name, errors, start_time
                )

            # Step 5: Validate outputs
            logger.info(f"Step 5/6: Validating outputs")
            dxf_file = output_dir / f"{order_id}_pattern.dxf"
            plt_file = output_dir / f"{order_id}_pattern.plt"
            mrk_file = output_dir / f"{order_id}_marker.mrk"

            validation_passed = self._validate_outputs(
                dxf_file=dxf_file, plt_file=plt_file, mrk_file=mrk_file
            )

            if not validation_passed:
                errors.append("Output validation failed - files may be incomplete")

            # Step 6: Parse results
            logger.info(f"Step 6/6: Parsing results")
            nesting_metrics = self.result_parser.parse_nesting_report(mrk_file)
            if nesting_metrics:
                logger.info(f"Nesting efficiency: {nesting_metrics.efficiency}%")

            processing_time = time.time() - start_time

            return AutomationResult(
                success=len(errors) == 0,
                order_id=order_id,
                template_name=template_name,
                dxf_file=dxf_file if dxf_file.exists() else None,
                plt_file=plt_file if plt_file.exists() else None,
                mrk_file=mrk_file if mrk_file.exists() else None,
                processing_time_seconds=processing_time,
                errors=errors,
                warnings=warnings,
                validation_passed=validation_passed,
            )

        except Exception as e:
            logger.exception(f"Automation workflow failed for order {order_id}")
            errors.append(f"Workflow error: {e}")
            return self._create_failure_result(
                order_id, template_name, errors, start_time
            )

    def _create_batch_script(
        self,
        template,
        order_id: str,
        output_dir: Path,
        btf_commands: List[str],
        fabric_width: float,
    ) -> Path:
        """Create Optitex batch script."""
        script_path = config.scripts_dir / f"workflow_{order_id}.bat"

        lines = [
            f"@REM Auto-generated workflow for Order: {order_id}",
            f"@REM Template: {template.name}",
            f"@REM Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "@UNIT /CM",
            f"@OPEN /FILE={template.pds_file.absolute()}",
            "",
            "@REM Apply BTF measurements",
        ]

        # Add BTF commands (Format C)
        lines.extend(btf_commands)

        # Add export and nesting commands
        lines.extend(
            [
                "",
                "@REM Validate pattern",
                "@VALIDATE /STRICT=YES",
                "",
                "@REM Export pattern",
                f"@EXPORT /FORMAT=DXF /FILE={output_dir / f'{order_id}_pattern.dxf'}",
                f"@SAVE /FILE={output_dir / f'{order_id}_pattern.pds'}",
                "",
                "@REM Create marker and nest",
                f"@MARKER /FILE={output_dir / f'{order_id}_pattern.mrk'}",
                f"@WIDTH /VALUE={fabric_width}",
                f"@NEST /ALG={template.nesting_algorithm} /TIME=300 /EFF=85",
                f"@SAVE /FILE={output_dir / f'{order_id}_marker.mrk'} /FORMAT=MRK",
                f"@PLOT /FILE={output_dir / f'{order_id}_pattern.plt'} /OPT=PLT",
                "",
                "@!",
            ]
        )

        script_path.write_text("\n".join(lines), encoding="utf-8")
        logger.info(f"Created batch script: {script_path}")

        return script_path

    def _execute_with_retry(self, script_path: Path) -> ExecutionResult:
        """Execute batch script with retry logic."""
        for attempt in range(1, self.max_retries + 1):
            logger.info(f"Execution attempt {attempt}/{self.max_retries}")

            result = self.executor.run_pds_batch(script_path)

            if result.success:
                logger.info(f"Execution successful on attempt {attempt}")
                return result

            # Check for specific errors
            if "License" in result.stderr:
                logger.error("Optitex license error - cannot retry")
                break
            elif "Template" in result.stderr:
                logger.error("Template error - cannot retry")
                break

            if attempt < self.max_retries:
                wait_time = 5 * attempt  # Exponential backoff
                logger.warning(
                    f"Attempt {attempt} failed, waiting {wait_time}s before retry"
                )
                time.sleep(wait_time)

        return result

    def _validate_outputs(self, dxf_file: Path, plt_file: Path, mrk_file: Path) -> bool:
        """Validate that output files were created and are valid."""
        all_valid = True

        for file_path in [dxf_file, plt_file, mrk_file]:
            if not file_path.exists():
                logger.error(f"Output file missing: {file_path}")
                all_valid = False
            elif file_path.stat().st_size == 0:
                logger.error(f"Output file is empty: {file_path}")
                all_valid = False
            elif file_path.stat().st_size < 100:  # Suspiciously small
                logger.warning(
                    f"Output file is very small: {file_path} ({file_path.stat().st_size} bytes)"
                )

        # Additional validation for DXF
        if dxf_file.exists():
            try:
                import ezdxf

                doc = ezdxf.readfile(str(dxf_file))
                if len(doc.modelspace()) == 0:
                    logger.error(f"DXF file has no entities: {dxf_file}")
                    all_valid = False
            except Exception as e:
                logger.error(f"DXF validation failed: {e}")
                all_valid = False

        return all_valid

    def _create_failure_result(
        self, order_id: str, template_name: str, errors: List[str], start_time: float
    ) -> AutomationResult:
        """Create failure result."""
        processing_time = time.time() - start_time
        return AutomationResult(
            success=False,
            order_id=order_id,
            template_name=template_name,
            dxf_file=None,
            plt_file=None,
            mrk_file=None,
            processing_time_seconds=processing_time,
            errors=errors,
            warnings=[],
            validation_passed=False,
        )

    def batch_process(
        self,
        orders: List[
            Tuple[Dict[str, float], str, str]
        ],  # (measurements, template, order_id)
        fabric_width: Optional[float] = None,
    ) -> List[AutomationResult]:
        """
        Process multiple orders in batch.

        Args:
            orders: List of (measurements, template_name, order_id) tuples
            fabric_width: Optional fabric width override

        Returns:
            List of AutomationResult objects
        """
        results = []

        logger.info(f"Starting batch processing of {len(orders)} orders")

        for i, (measurements, template_name, order_id) in enumerate(orders, 1):
            logger.info(f"Processing order {i}/{len(orders)}: {order_id}")

            result = self.process_order(
                measurements=measurements,
                template_name=template_name,
                order_id=order_id,
                fabric_width=fabric_width,
            )

            results.append(result)

            if result.success:
                logger.info(f"✓ Order {order_id} completed successfully")
            else:
                logger.error(f"✗ Order {order_id} failed: {result.errors}")

        # Summary
        successful = sum(1 for r in results if r.success)
        logger.info(f"Batch complete: {successful}/{len(orders)} orders successful")

        return results


# Convenience function
def automate_pattern_generation(
    measurements: Dict[str, float],
    template_name: str,
    order_id: str,
    fabric_width: Optional[float] = None,
    execute: bool = True,
) -> AutomationResult:
    """
    Convenience function for one-off pattern generation.

    Example:
        result = automate_pattern_generation(
            measurements={"chest_girth": 102, "waist_girth": 88, ...},
            template_name="basic_tee",
            order_id="ORD-001"
        )

        if result.success:
            print(f"DXF: {result.dxf_file}")
            print(f"PLT: {result.plt_file}")
    """
    workflow = OptitexAutomationWorkflow()
    return workflow.process_order(
        measurements=measurements,
        template_name=template_name,
        order_id=order_id,
        fabric_width=fabric_width,
        execute=execute,
    )
