#!/usr/bin/env python3
"""
SameDaySuits Production API

Unified API for the complete production pipeline:
1. Receive customer order (measurements or body scan)
2. Select appropriate pattern template
3. Apply measurements to pattern (via BTF or direct scaling)
4. Nest pieces for 62" cutter
5. Generate HPGL/PLT file
6. Queue for cutting

This bridges:
- TheBlackbox Experiment (measurement extraction)
- REVERSE-ENGINEER-PDS (pattern processing & nesting)

Author: Claude
Date: 2026-01-30
"""

import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
import logging

# v6.4.3 Order ID format: SDS-YYYYMMDD-NNNN-R
ORDER_ID_PATTERN = re.compile(r"^SDS-(\d{8})-(\d{4})-([A-Z])$")

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Add paths
project_root = Path(
    __file__
).parent.parent.parent.parent  # Go up to REVERSE-ENGINEER-PDS
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "production" / "src" / "core"))

# Import our production pipeline
from production_pipeline import (
    extract_xml_from_pds,
    extract_piece_dimensions,
    extract_svg_geometry,
    transform_to_cm,
    nest_contours,
    generate_hpgl,
    CUTTER_WIDTH_CM,
)

# Import pattern scaler
from pattern_scaler import (
    calculate_pattern_scale,
    scale_contours,
    get_garment_type,
    GarmentType as ScalerGarmentType,
)

# Import production monitoring
try:
    from production_monitor import get_monitor

    MONITORING_AVAILABLE = True
except ImportError:
    MONITORING_AVAILABLE = False

# Import quality control
try:
    from quality_control import QualityControl, QCLevel

    QC_AVAILABLE = True
except ImportError:
    QC_AVAILABLE = False


class GarmentType(Enum):
    """Available garment types."""

    TEE = "tee"
    SHIRT = "shirt"
    JACKET = "jacket"
    TROUSERS = "trousers"
    CARGO = "cargo"


class FitType(Enum):
    """Fit preferences."""

    SLIM = "slim"
    REGULAR = "regular"
    CLASSIC = "classic"


@dataclass
class CustomerMeasurements:
    """Customer body measurements."""

    # Required
    chest_cm: float
    waist_cm: float
    hip_cm: float

    # Optional but recommended
    shoulder_width_cm: Optional[float] = None
    arm_length_cm: Optional[float] = None
    inseam_cm: Optional[float] = None
    neck_cm: Optional[float] = None
    torso_length_cm: Optional[float] = None

    # Metadata
    source: str = "manual"  # manual, mediapipe, sam3d
    confidence: float = 1.0


@dataclass
class Order:
    """Customer order."""

    order_id: str
    customer_id: str
    garment_type: GarmentType
    fit_type: FitType
    measurements: CustomerMeasurements
    quantity: int = 1
    notes: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class ProductionResult:
    """Result of production pipeline."""

    success: bool
    order_id: str
    plt_file: Optional[Path]
    metadata_file: Optional[Path]
    fabric_length_cm: float
    fabric_utilization: float
    piece_count: int
    processing_time_ms: float
    errors: List[str]
    warnings: List[str]


# Template mapping: garment type -> PDS file
TEMPLATE_MAPPING = {
    GarmentType.TEE: "Basic Tee_2D.PDS",
    GarmentType.JACKET: "Light  Jacket_2D.PDS",
    GarmentType.TROUSERS: "Skinny Trousers_2D.PDS",
    GarmentType.CARGO: "Skinny Cargo_2D.PDS",
}


class SameDaySuitsAPI:
    """
    Main API for SameDaySuits production pipeline.

    Example usage:
        api = SameDaySuitsAPI()

        order = Order(
            order_id="ORD-001",
            customer_id="CUST-123",
            garment_type=GarmentType.TEE,
            fit_type=FitType.REGULAR,
            measurements=CustomerMeasurements(
                chest_cm=102,
                waist_cm=88,
                hip_cm=100,
            )
        )

        result = api.process_order(order)

        if result.success:
            print(f"PLT file: {result.plt_file}")
            print(f"Fabric needed: {result.fabric_length_cm} cm")
    """

    def __init__(
        self,
        templates_dir: Optional[Path] = None,
        output_dir: Optional[Path] = None,
        fabric_width_cm: float = CUTTER_WIDTH_CM,
    ):
        """
        Initialize the API.

        Args:
            templates_dir: Directory containing PDS template files
            output_dir: Directory for output files
            fabric_width_cm: Fabric width for nesting (default: 62" = 157.48 cm)
        """
        self.templates_dir = (
            templates_dir or project_root / "DS-speciale" / "inputs" / "pds"
        )
        self.output_dir = output_dir or project_root / "DS-speciale" / "out" / "orders"
        self.fabric_width_cm = fabric_width_cm

        self.output_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"SameDaySuits API initialized")
        logger.info(f"Templates: {self.templates_dir}")
        logger.info(f"Output: {self.output_dir}")

    def _validate_order_id_format(self, order_id: str) -> bool:
        """Validate v6.4.3 order ID format: SDS-YYYYMMDD-NNNN-R."""
        match = ORDER_ID_PATTERN.match(order_id)
        if not match:
            return False

        date_str = match.group(1)
        try:
            datetime.strptime(date_str, "%Y%m%d")
            return True
        except ValueError:
            return False
        logger.info(f"Fabric width: {self.fabric_width_cm} cm")

    def list_available_templates(self) -> Dict[str, bool]:
        """List available templates and their existence status."""
        result = {}
        for garment_type, filename in TEMPLATE_MAPPING.items():
            template_path = self.templates_dir / filename
            result[garment_type.value] = template_path.exists()
        return result

    def get_template_path(self, garment_type: GarmentType) -> Path:
        """Get path to template PDS file."""
        if garment_type not in TEMPLATE_MAPPING:
            raise ValueError(f"Unknown garment type: {garment_type}")

        filename = TEMPLATE_MAPPING[garment_type]
        template_path = self.templates_dir / filename

        if not template_path.exists():
            raise FileNotFoundError(f"Template not found: {template_path}")

        return template_path

    def process_order(self, order: Order) -> ProductionResult:
        """
        Process a customer order through the production pipeline.

        Steps:
        1. Validate order
        2. Load template PDS file
        3. Extract geometry
        4. Apply measurements (future: scale pattern)
        5. Nest pieces for fabric width
        6. Generate HPGL/PLT
        7. Save outputs
        """
        import time

        start_time = time.time()

        errors = []
        warnings = []

        try:
            logger.info(f"Processing order: {order.order_id}")

            # Step 1: Validate order
            validation_errors = self._validate_order(order)
            if validation_errors:
                errors.extend(validation_errors)
                return self._create_failure_result(order, errors, start_time)

            # Update database status to PROCESSING
            try:
                from database_integration import OrderDatabase, OrderStatus

                db = OrderDatabase()
                db.update_order_status(order.order_id, OrderStatus.PROCESSING)
                logger.info(f"Order {order.order_id} status updated to PROCESSING")
            except Exception as db_error:
                logger.warning(f"Failed to update PROCESSING status: {db_error}")

            # Step 2: Get template
            try:
                template_path = self.get_template_path(order.garment_type)
                logger.info(f"Using template: {template_path.name}")
            except FileNotFoundError as e:
                errors.append(str(e))
                return self._create_failure_result(order, errors, start_time)

            # Step 3: Extract geometry
            logger.info("Extracting pattern geometry...")
            xml_content = extract_xml_from_pds(str(template_path))

            pieces = extract_piece_dimensions(xml_content, "Small")
            total_width = sum(p["size_x"] for p in pieces.values())
            total_height = max(p["size_y"] for p in pieces.values()) if pieces else 0

            contours, metadata = extract_svg_geometry(
                xml_content, cutting_contours_only=True
            )
            logger.info(f"Found {len(contours)} cutting contours, {len(pieces)} pieces")

            # Step 4: Transform to real-world cm
            contours_cm = transform_to_cm(contours, metadata, total_width, total_height)

            # Step 4b: Apply customer measurements to scale pattern
            logger.info("Calculating pattern scale from measurements...")

            # Convert measurements to scaler format
            customer_measurements = {
                "chest": order.measurements.chest_cm,
                "waist": order.measurements.waist_cm,
                "hip": order.measurements.hip_cm,
            }
            if order.measurements.shoulder_width_cm:
                customer_measurements["shoulder"] = order.measurements.shoulder_width_cm
            if order.measurements.inseam_cm:
                customer_measurements["inseam"] = order.measurements.inseam_cm

            # Get garment type for scaler
            scaler_garment_type = get_garment_type(order.garment_type.value)

            # Calculate scale factors
            scale_result = calculate_pattern_scale(
                customer_measurements, scaler_garment_type
            )

            logger.info(
                f"Base size: {scale_result.base_size}, Scale: X={scale_result.scale_x:.3f}, Y={scale_result.scale_y:.3f}"
            )

            # Apply scaling if significantly different from 1.0
            scaling_applied = False
            if (
                abs(scale_result.scale_x - 1.0) > 0.01
                or abs(scale_result.scale_y - 1.0) > 0.01
            ):
                logger.info("Applying pattern scaling...")
                contours_cm = scale_contours(
                    contours_cm, scale_result.scale_x, scale_result.scale_y
                )
                scaling_applied = True
            else:
                logger.info("No significant scaling needed")

            # Add scaling notes to warnings
            for note in scale_result.notes:
                warnings.append(note)

            # Step 5: Nest pieces
            logger.info("Nesting pieces...")
            nested_contours, nesting_result = nest_contours(
                contours_cm, fabric_width=self.fabric_width_cm
            )

            if not nesting_result.success:
                errors.append(f"Nesting failed: {nesting_result.message}")
                return self._create_failure_result(order, errors, start_time)

            logger.info(
                f"Nested to {nesting_result.fabric_width:.1f} x {nesting_result.fabric_length:.1f} cm"
            )
            logger.info(f"Utilization: {nesting_result.utilization:.1f}%")

            # Step 5b: Quality Control Validation
            if QC_AVAILABLE:
                logger.info("Running quality control checks...")
                qc = QualityControl()

                # Prepare customer measurements
                customer_measurements = {
                    "chest": order.measurements.chest_cm,
                    "waist": order.measurements.waist_cm,
                    "hip": order.measurements.hip_cm,
                }

                # Prepare scaled dimensions (approximate from scale result)
                scaled_dimensions = {
                    "chest_width": order.measurements.chest_cm / 2,  # Half chest
                    "waist_width": order.measurements.waist_cm / 2,
                    "hip_width": order.measurements.hip_cm / 2,
                }

                qc_report = qc.validate_order(
                    order_id=order.order_id,
                    garment_type=order.garment_type.value,
                    contours=nested_contours,
                    customer_measurements=customer_measurements,
                    scaled_dimensions=scaled_dimensions,
                    nesting_result=nesting_result,
                )

                # Log QC results
                if not qc_report.passed:
                    logger.warning(
                        f"QC check failed: {qc_report.error_count} errors, {qc_report.warning_count} warnings"
                    )
                    # Add QC warnings to order warnings
                    for check in qc_report.checks:
                        if check.level == QCLevel.WARNING:
                            warnings.append(f"QC: {check.message}")
                        elif check.level == QCLevel.ERROR:
                            errors.append(f"QC Error: {check.message}")

                    # Save QC report
                    order_output_dir = self.output_dir / order.order_id
                    order_output_dir.mkdir(parents=True, exist_ok=True)
                    qc_file = order_output_dir / f"{order.order_id}_qc_report.json"
                    qc_check_dicts = []
                    for check in qc_report.checks:
                        qc_check_dicts.append(
                            {
                                "category": check.category.value,
                                "level": check.level.value,
                                "message": check.message,
                                "piece_id": check.piece_id,
                                "piece_name": check.piece_name,
                                "details": check.details,
                            }
                        )
                    qc_report_data = {
                        "order_id": qc_report.order_id,
                        "garment_type": qc_report.garment_type,
                        "passed": qc_report.passed,
                        "error_count": qc_report.error_count,
                        "warning_count": qc_report.warning_count,
                        "info_count": qc_report.info_count,
                        "checks": qc_check_dicts,
                    }
                    with open(qc_file, "w") as f:
                        json.dump(qc_report_data, f, indent=2)

                    # Don't fail the order for QC warnings, but log them
                    if qc_report.error_count > 0:
                        logger.error(
                            "QC validation found critical errors - review recommended before cutting"
                        )
                else:
                    logger.info("QC validation passed")

            # Step 6: Generate HPGL
            order_output_dir = self.output_dir / order.order_id
            order_output_dir.mkdir(parents=True, exist_ok=True)

            plt_file = order_output_dir / f"{order.order_id}.plt"
            metadata_file = order_output_dir / f"{order.order_id}_metadata.json"

            logger.info(f"Generating HPGL: {plt_file}")
            generate_hpgl(nested_contours, str(plt_file), self.fabric_width_cm)

            # Step 7: Save metadata
            order_metadata = {
                "order": asdict(order),
                "production": {
                    "template": template_path.name,
                    "piece_count": len(contours),
                    "fabric_width_cm": self.fabric_width_cm,
                    "fabric_length_cm": nesting_result.fabric_length,
                    "utilization_percent": nesting_result.utilization,
                    "nesting_applied": True,
                    "scaling": {
                        "applied": scaling_applied,
                        "base_size": scale_result.base_size,
                        "scale_x": scale_result.scale_x,
                        "scale_y": scale_result.scale_y,
                        "size_match_quality": scale_result.size_match_quality,
                    },
                },
                "files": {
                    "plt": str(plt_file),
                },
                "processed_at": datetime.now().isoformat(),
            }

            # Convert enum values for JSON
            order_metadata["order"]["garment_type"] = order.garment_type.value
            order_metadata["order"]["fit_type"] = order.fit_type.value

            with open(metadata_file, "w") as f:
                json.dump(order_metadata, f, indent=2)

            processing_time = (time.time() - start_time) * 1000

            logger.info(f"Order {order.order_id} completed in {processing_time:.0f}ms")

            # Create result first so we can use it for database update
            result = ProductionResult(
                success=True,
                order_id=order.order_id,
                plt_file=plt_file,
                metadata_file=metadata_file,
                fabric_length_cm=nesting_result.fabric_length,
                fabric_utilization=nesting_result.utilization,
                piece_count=len(contours),
                processing_time_ms=processing_time,
                errors=errors,
                warnings=warnings,
            )

            # Record metrics
            if MONITORING_AVAILABLE:
                monitor = get_monitor()
                monitor.record_order_processed(
                    order_id=order.order_id,
                    garment_type=order.garment_type.value,
                    success=True,
                    processing_time=processing_time / 1000,  # Convert to seconds
                    utilization=nesting_result.utilization,
                    fabric_length=nesting_result.fabric_length,
                    piece_count=len(contours),
                )

            # Save to database with production details
            try:
                from database_integration import OrderDatabase, OrderStatus

                db = OrderDatabase()
                # Pass production data as dict to avoid circular import type issues
                db.update_order_status(
                    order.order_id,
                    OrderStatus.COMPLETE,
                    production_result={
                        "plt_file": str(result.plt_file) if result.plt_file else None,
                        "metadata_file": str(result.metadata_file)
                        if result.metadata_file
                        else None,
                        "fabric_length_cm": result.fabric_length_cm,
                        "fabric_utilization": result.fabric_utilization,
                        "piece_count": result.piece_count,
                        "processing_time_ms": result.processing_time_ms,
                        "errors": result.errors if result.errors else None,
                        "warnings": result.warnings if result.warnings else None,
                    },
                )
                logger.info(
                    f"Order {order.order_id} status updated to COMPLETE in database"
                )
            except Exception as db_error:
                logger.warning(f"Failed to update database: {db_error}")

            return result

        except Exception as e:
            logger.exception(f"Error processing order {order.order_id}")
            errors.append(f"Processing error: {e}")

            # Update database status to ERROR
            try:
                from database_integration import OrderDatabase, OrderStatus

                db = OrderDatabase()
                db.update_order_status(order.order_id, OrderStatus.ERROR)
                logger.info(f"Order {order.order_id} status updated to ERROR")
            except Exception as db_error:
                logger.warning(f"Failed to update ERROR status: {db_error}")

            return self._create_failure_result(order, errors, start_time)

    def _validate_order(self, order: Order) -> List[str]:
        """Validate order data including v6.4.3 order ID format."""
        errors = []

        if not order.order_id:
            errors.append("Order ID is required")
        else:
            # Validate v6.4.3 order ID format: SDS-YYYYMMDD-NNNN-R
            if not self._validate_order_id_format(order.order_id):
                errors.append(
                    f"Invalid order ID format: {order.order_id}. "
                    f"Required format: SDS-YYYYMMDD-NNNN-R (e.g., SDS-20260131-0001-A)"
                )

        if not order.customer_id:
            errors.append("Customer ID is required")

        m = order.measurements
        if m.chest_cm <= 0 or m.chest_cm > 200:
            errors.append(f"Invalid chest measurement: {m.chest_cm}")

        if m.waist_cm <= 0 or m.waist_cm > 200:
            errors.append(f"Invalid waist measurement: {m.waist_cm}")

        if m.hip_cm <= 0 or m.hip_cm > 200:
            errors.append(f"Invalid hip measurement: {m.hip_cm}")

        return errors

    def _create_failure_result(
        self, order: Order, errors: List[str], start_time: float
    ) -> ProductionResult:
        """Create a failure result and record metrics."""
        import time

        processing_time = (time.time() - start_time) * 1000

        # Record failure metrics
        if MONITORING_AVAILABLE:
            monitor = get_monitor()
            monitor.record_order_processed(
                order_id=order.order_id,
                garment_type=order.garment_type.value,
                success=False,
                processing_time=processing_time / 1000,
                utilization=0,
                fabric_length=0,
                piece_count=0,
                error="; ".join(errors),
            )

        return ProductionResult(
            success=False,
            order_id=order.order_id,
            plt_file=None,
            metadata_file=None,
            fabric_length_cm=0,
            fabric_utilization=0,
            piece_count=0,
            processing_time_ms=processing_time,
            errors=errors,
            warnings=[],
        )

    def batch_process(self, orders: List[Order]) -> List[ProductionResult]:
        """Process multiple orders in batch."""
        results = []

        logger.info(f"Batch processing {len(orders)} orders")

        for i, order in enumerate(orders, 1):
            logger.info(f"Processing {i}/{len(orders)}: {order.order_id}")
            result = self.process_order(order)
            results.append(result)

            if result.success:
                logger.info(f"  OK - {result.fabric_length_cm:.1f}cm fabric")
            else:
                logger.error(f"  FAILED - {result.errors}")

        # Summary
        successful = sum(1 for r in results if r.success)
        total_fabric = sum(r.fabric_length_cm for r in results if r.success)

        logger.info(f"\nBatch complete: {successful}/{len(orders)} successful")
        logger.info(f"Total fabric needed: {total_fabric:.1f} cm")

        return results


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="SameDaySuits Production API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process a single order
  python samedaysuits_api.py --order ORD-001 --garment tee --chest 102 --waist 88 --hip 100
  
  # List available templates
  python samedaysuits_api.py --list-templates
  
  # Process from JSON file
  python samedaysuits_api.py --json orders.json
        """,
    )

    parser.add_argument("--order", help="Order ID")
    parser.add_argument("--customer", default="WALK-IN", help="Customer ID")
    parser.add_argument(
        "--garment", choices=["tee", "jacket", "trousers", "cargo"], help="Garment type"
    )
    parser.add_argument(
        "--fit",
        choices=["slim", "regular", "classic"],
        default="regular",
        help="Fit type",
    )
    parser.add_argument("--chest", type=float, help="Chest measurement (cm)")
    parser.add_argument("--waist", type=float, help="Waist measurement (cm)")
    parser.add_argument("--hip", type=float, help="Hip measurement (cm)")
    parser.add_argument("--json", type=Path, help="Process orders from JSON file")
    parser.add_argument(
        "--list-templates", action="store_true", help="List available templates"
    )
    parser.add_argument("--output", type=Path, help="Output directory")

    args = parser.parse_args()

    # Initialize API
    api = SameDaySuitsAPI(output_dir=args.output)

    if args.list_templates:
        print("\nAvailable Templates:")
        print("-" * 40)
        for garment, available in api.list_available_templates().items():
            status = "OK" if available else "MISSING"
            print(f"  {garment:12} [{status}]")
        return

    if args.json:
        # Process from JSON file
        with open(args.json) as f:
            orders_data = json.load(f)

        orders = []
        for od in orders_data:
            orders.append(
                Order(
                    order_id=od["order_id"],
                    customer_id=od.get("customer_id", "BATCH"),
                    garment_type=GarmentType(od["garment_type"]),
                    fit_type=FitType(od.get("fit_type", "regular")),
                    measurements=CustomerMeasurements(
                        chest_cm=od["measurements"]["chest"],
                        waist_cm=od["measurements"]["waist"],
                        hip_cm=od["measurements"]["hip"],
                    ),
                )
            )

        results = api.batch_process(orders)

        # Print summary
        print("\n" + "=" * 60)
        print("BATCH PROCESSING COMPLETE")
        print("=" * 60)
        for r in results:
            status = "OK" if r.success else "FAILED"
            print(f"  {r.order_id}: [{status}] {r.fabric_length_cm:.1f}cm fabric")

    elif args.order and args.garment:
        # Single order from command line
        if not all([args.chest, args.waist, args.hip]):
            parser.error("--chest, --waist, and --hip are required for single orders")

        order = Order(
            order_id=args.order,
            customer_id=args.customer,
            garment_type=GarmentType(args.garment),
            fit_type=FitType(args.fit),
            measurements=CustomerMeasurements(
                chest_cm=args.chest,
                waist_cm=args.waist,
                hip_cm=args.hip,
            ),
        )

        result = api.process_order(order)

        print("\n" + "=" * 60)
        if result.success:
            print(f"ORDER {result.order_id} - SUCCESS")
            print(f"  PLT file: {result.plt_file}")
            print(f"  Fabric needed: {result.fabric_length_cm:.1f} cm")
            print(f"  Utilization: {result.fabric_utilization:.1f}%")
            print(f"  Processing time: {result.processing_time_ms:.0f}ms")
        else:
            print(f"ORDER {result.order_id} - FAILED")
            for error in result.errors:
                print(f"  ERROR: {error}")
        print("=" * 60)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
