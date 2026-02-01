"""
BlackBox to Production Bridge

Bridges BlackBox pipeline output to the Production Redis queue for nesting.

This module provides a clean interface between:
- BlackBox (scanning, measurement, pattern generation)
- Production (nesting, HPGL output, quality control)

The bridge handles:
1. Validating BlackBox output (PDS files, measurements)
2. Packaging data for the queue format
3. Submitting to Redis queue with priority
4. Tracking job status

Usage:
    from integrations.blackbox_bridge import BlackBoxBridge
    from scalability.queue_manager import OrderQueue

    queue = OrderQueue()
    bridge = BlackBoxBridge(queue)

    # Submit from BlackBox pipeline result
    order_id = bridge.submit_from_pipeline(
        pipeline_result=result,
        customer_id="CUST-001",
        garment_type="jacket"
    )

    # Or submit PDS file directly
    order_id = bridge.submit_pds_file(
        pds_file=Path("pattern.pds"),
        measurements={"chest_cm": 102, "waist_cm": 88},
        customer_id="CUST-001"
    )

Author: SameDaySuits
Date: February 2026
"""

import json
import logging
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from enum import Enum

logger = logging.getLogger(__name__)


class BridgeError(Exception):
    """Raised when bridge operation fails."""

    pass


class InputSource(Enum):
    """Source of the order input."""

    BLACKBOX_SCAN = "blackbox_scan"  # Full scan pipeline
    BLACKBOX_PDS = "blackbox_pds"  # PDS file from Optitex
    MANUAL_MEASUREMENTS = "manual"  # Manual measurement input
    LEGACY = "legacy"  # Legacy production system


@dataclass
class BlackBoxOutput:
    """
    Standard output format from BlackBox pipeline.

    This can come from:
    - Full scan pipeline (image -> measurements -> pattern)
    - Optitex automation (measurements -> PDS)
    - Manual measurement entry
    """

    order_id: str
    customer_id: str

    # Measurements (required for records)
    measurements: Dict[str, float]

    # Pattern files (at least one required)
    pds_file: Optional[Path] = None
    dxf_file: Optional[Path] = None
    hpgl_file: Optional[Path] = None

    # Garment info
    garment_type: str = "tee"
    fit_type: str = "regular"
    fabric_type: str = "wool"

    # Quality metrics
    confidence_score: float = 1.0
    processing_time_ms: float = 0.0

    # Source tracking
    source: InputSource = InputSource.BLACKBOX_SCAN
    scan_id: Optional[str] = None

    # Errors/warnings from BlackBox
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class BridgeResult:
    """Result of bridge submission."""

    success: bool
    order_id: str
    queue_position: Optional[int] = None
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class BlackBoxBridge:
    """
    Bridges BlackBox output to Production queue.

    Provides a clean interface for submitting orders from BlackBox
    to the Production nesting/cutting pipeline.
    """

    # Minimum required measurements for processing
    REQUIRED_MEASUREMENTS = ["chest_cm", "waist_cm", "hip_cm"]

    # Supported garment types
    SUPPORTED_GARMENTS = ["tee", "jacket", "trousers", "cargo", "vest", "shirt"]

    def __init__(
        self, queue=None, validate_files: bool = True, sync_mode: bool = False
    ):
        """
        Initialize bridge.

        Args:
            queue: OrderQueue instance (optional, lazy loaded if not provided)
            validate_files: Whether to validate that PDS files exist
            sync_mode: If True, skip queue entirely and operate in sync mode
        """
        self._queue = queue
        self._sync_mode = sync_mode or (
            queue is None and queue is not ...
        )  # Explicit None = sync mode
        self.validate_files = validate_files

        # If queue=None explicitly passed, assume sync mode
        self._explicit_no_queue = queue is None

        logger.info(
            "BlackBox Bridge initialized"
            + (" (sync mode)" if self._explicit_no_queue else "")
        )

    @property
    def queue(self):
        """Lazy-load queue if not provided and not in explicit sync mode."""
        if self._explicit_no_queue:
            # Explicit None was passed - don't try to create queue
            return None

        if self._queue is None:
            try:
                from scalability.queue_manager import OrderQueue

                self._queue = OrderQueue()
                # Check if Redis is actually available
                if not self._queue.is_available:
                    logger.warning("Redis unavailable, falling back to sync mode")
                    return None
            except ImportError:
                logger.warning("Queue manager not available, using sync mode")
                self._queue = None
        return self._queue

    def submit_from_pipeline(
        self,
        pipeline_result: Any,  # PipelineResult from blackbox.pipeline
        customer_id: str,
        garment_type: str = "tee",
        fit_type: str = "regular",
        priority: str = "normal",
        order_id: Optional[str] = None,
    ) -> BridgeResult:
        """
        Submit order from BlackBox pipeline result.

        Args:
            pipeline_result: Result from BlackBoxPipeline.process_image()
            customer_id: Customer identifier
            garment_type: Type of garment
            fit_type: Fit preference (slim, regular, classic)
            priority: Queue priority (rush, normal, low)
            order_id: Optional order ID (auto-generated if not provided)

        Returns:
            BridgeResult with submission status
        """
        # Generate order ID if not provided
        if order_id is None:
            order_id = self._generate_order_id(customer_id)

        # Convert pipeline result to BlackBoxOutput
        blackbox_output = BlackBoxOutput(
            order_id=order_id,
            customer_id=customer_id,
            measurements=pipeline_result.measurements or {},
            dxf_file=pipeline_result.dxf_path,
            hpgl_file=pipeline_result.hpgl_path,
            garment_type=garment_type,
            fit_type=fit_type,
            confidence_score=1.0 if pipeline_result.success else 0.5,
            processing_time_ms=pipeline_result.processing_time_ms,
            source=InputSource.BLACKBOX_SCAN,
            errors=pipeline_result.errors,
        )

        return self._submit_to_queue(blackbox_output, priority)

    def submit_pds_file(
        self,
        pds_file: Path,
        measurements: Dict[str, float],
        customer_id: str,
        garment_type: str = "tee",
        fit_type: str = "regular",
        priority: str = "normal",
        order_id: Optional[str] = None,
    ) -> BridgeResult:
        """
        Submit PDS file directly to production queue.

        Args:
            pds_file: Path to Optitex PDS file
            measurements: Body measurements used to generate the pattern
            customer_id: Customer identifier
            garment_type: Type of garment
            fit_type: Fit preference
            priority: Queue priority
            order_id: Optional order ID

        Returns:
            BridgeResult with submission status
        """
        # Generate order ID if not provided
        if order_id is None:
            order_id = self._generate_order_id(customer_id)

        # Create BlackBoxOutput
        blackbox_output = BlackBoxOutput(
            order_id=order_id,
            customer_id=customer_id,
            measurements=measurements,
            pds_file=Path(pds_file),
            garment_type=garment_type,
            fit_type=fit_type,
            source=InputSource.BLACKBOX_PDS,
        )

        return self._submit_to_queue(blackbox_output, priority)

    def submit_measurements(
        self,
        measurements: Dict[str, float],
        customer_id: str,
        garment_type: str = "tee",
        fit_type: str = "regular",
        priority: str = "normal",
        order_id: Optional[str] = None,
    ) -> BridgeResult:
        """
        Submit measurements only (for legacy production path).

        The production system will generate patterns from templates
        using the provided measurements.

        Args:
            measurements: Body measurements
            customer_id: Customer identifier
            garment_type: Type of garment
            fit_type: Fit preference
            priority: Queue priority
            order_id: Optional order ID

        Returns:
            BridgeResult with submission status
        """
        # Generate order ID if not provided
        if order_id is None:
            order_id = self._generate_order_id(customer_id)

        # Create BlackBoxOutput
        blackbox_output = BlackBoxOutput(
            order_id=order_id,
            customer_id=customer_id,
            measurements=measurements,
            garment_type=garment_type,
            fit_type=fit_type,
            source=InputSource.MANUAL_MEASUREMENTS,
        )

        return self._submit_to_queue(blackbox_output, priority)

    def _submit_to_queue(
        self,
        blackbox_output: BlackBoxOutput,
        priority: str,
    ) -> BridgeResult:
        """
        Internal method to validate and submit to queue.
        """
        errors = []
        warnings = []

        # Validate output
        validation_errors = self._validate_output(blackbox_output)
        if validation_errors:
            errors.extend(validation_errors)

        # Check for warnings from BlackBox
        if blackbox_output.warnings:
            warnings.extend(blackbox_output.warnings)

        # If validation failed, don't submit
        if errors:
            logger.error(f"Validation failed for {blackbox_output.order_id}: {errors}")
            return BridgeResult(
                success=False,
                order_id=blackbox_output.order_id,
                errors=errors,
                warnings=warnings,
            )

        # Convert to queue format
        order_data = self._to_queue_format(blackbox_output)

        # Submit to queue
        try:
            if self.queue is not None:
                # Convert priority string to enum
                from scalability.queue_manager import JobPriority

                priority_enum = JobPriority.from_string(priority)

                self.queue.enqueue(
                    order_id=blackbox_output.order_id,
                    order_data=order_data,
                    priority=priority_enum,
                )

                # Get queue position
                stats = self.queue.get_stats()
                queue_position = stats.total_pending

                logger.info(
                    f"Submitted {blackbox_output.order_id} to queue "
                    f"(priority={priority}, position={queue_position})"
                )

                return BridgeResult(
                    success=True,
                    order_id=blackbox_output.order_id,
                    queue_position=queue_position,
                    warnings=warnings,
                )
            else:
                # Sync mode - queue not available
                logger.warning(
                    f"Queue not available, order {blackbox_output.order_id} "
                    "will need manual processing"
                )
                return BridgeResult(
                    success=True,
                    order_id=blackbox_output.order_id,
                    warnings=["Queue not available - sync mode"],
                )

        except Exception as e:
            logger.error(f"Failed to submit {blackbox_output.order_id}: {e}")
            return BridgeResult(
                success=False,
                order_id=blackbox_output.order_id,
                errors=[f"Queue submission failed: {str(e)}"],
                warnings=warnings,
            )

    def _validate_output(self, output: BlackBoxOutput) -> List[str]:
        """Validate BlackBox output before submission."""
        errors = []

        # Check order ID
        if not output.order_id:
            errors.append("Order ID is required")

        # Check customer ID
        if not output.customer_id:
            errors.append("Customer ID is required")

        # Check garment type
        if output.garment_type not in self.SUPPORTED_GARMENTS:
            errors.append(
                f"Unsupported garment type: {output.garment_type}. "
                f"Supported: {self.SUPPORTED_GARMENTS}"
            )

        # Check measurements
        if not output.measurements:
            errors.append("Measurements are required")
        else:
            # Check for required measurements
            for req in self.REQUIRED_MEASUREMENTS:
                if req not in output.measurements or output.measurements[req] <= 0:
                    errors.append(f"Missing or invalid measurement: {req}")

        # Check file existence (if validate_files enabled)
        if self.validate_files:
            if output.pds_file and not output.pds_file.exists():
                errors.append(f"PDS file not found: {output.pds_file}")
            if output.dxf_file and not output.dxf_file.exists():
                errors.append(f"DXF file not found: {output.dxf_file}")

        # Check confidence score
        if output.confidence_score < 0.5:
            errors.append(
                f"Confidence score too low: {output.confidence_score:.2f} (min: 0.5)"
            )

        return errors

    def _to_queue_format(self, output: BlackBoxOutput) -> Dict[str, Any]:
        """Convert BlackBoxOutput to queue order format."""
        return {
            "order_id": output.order_id,
            "customer_id": output.customer_id,
            "garment_type": output.garment_type,
            "fit_type": output.fit_type,
            "fabric_type": output.fabric_type,
            "source": output.source.value,
            "measurements": output.measurements,
            # File paths as strings
            "pds_file": str(output.pds_file) if output.pds_file else None,
            "dxf_file": str(output.dxf_file) if output.dxf_file else None,
            "hpgl_file": str(output.hpgl_file) if output.hpgl_file else None,
            # Metadata
            "scan_id": output.scan_id,
            "confidence_score": output.confidence_score,
            "blackbox_processing_time_ms": output.processing_time_ms,
            "submitted_at": datetime.utcnow().isoformat(),
        }

    def _generate_order_id(self, customer_id: str) -> str:
        """Generate unique order ID."""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        return f"BB-{customer_id[:8]}-{timestamp}"


# Convenience function for quick submissions
def submit_to_production(
    measurements: Dict[str, float],
    customer_id: str,
    garment_type: str = "tee",
    pds_file: Optional[Path] = None,
    priority: str = "normal",
) -> BridgeResult:
    """
    Convenience function to submit an order to production.

    Args:
        measurements: Body measurements
        customer_id: Customer identifier
        garment_type: Type of garment
        pds_file: Optional PDS file from Optitex
        priority: Queue priority

    Returns:
        BridgeResult with submission status

    Example:
        result = submit_to_production(
            measurements={"chest_cm": 102, "waist_cm": 88, "hip_cm": 100},
            customer_id="CUST-001",
            garment_type="jacket"
        )
        if result.success:
            print(f"Order {result.order_id} submitted")
    """
    bridge = BlackBoxBridge()

    if pds_file:
        return bridge.submit_pds_file(
            pds_file=pds_file,
            measurements=measurements,
            customer_id=customer_id,
            garment_type=garment_type,
            priority=priority,
        )
    else:
        return bridge.submit_measurements(
            measurements=measurements,
            customer_id=customer_id,
            garment_type=garment_type,
            priority=priority,
        )
