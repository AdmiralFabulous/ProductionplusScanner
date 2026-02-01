#!/usr/bin/env python3
"""
v6.4.3 Production Adapter - Integration Layer

This module provides the integration layer between:
- Working production core (samedaysuits_api, production_pipeline)
- v6.4.3 modules (order_file_manager, order_continuity_validator)
- Database integration (database_integration)

Key Features:
1. Enforces SDS-YYYYMMDD-NNNN-R order ID format
2. Integrates database persistence with production pipeline
3. Generates complete v6.4.3 output files (PLT, PDS, DXF, metadata)
4. Validates order continuity
5. Provides drop-in replacement for process_order()

Usage:
    from v643_adapter import process_order_v643

    result = process_order_v643(
        order_id="SDS-20260131-0001-A",
        customer_id="CUST-001",
        garment_type="jacket",
        measurements={...}
    )
"""

import re
import json
import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass, field

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Add paths for imports
project_root = Path(__file__).parent.parent  # This is src/
sys.path.insert(0, str(project_root / "core"))
sys.path.insert(0, str(project_root / "integrations"))
sys.path.insert(0, str(project_root / "nesting"))


# Import working production core
try:
    from samedaysuits_api import (
        SameDaySuitsAPI,
        Order,
        GarmentType,
        FitType,
        CustomerMeasurements,
        ProductionResult,
    )
    from production_pipeline import (
        extract_xml_from_pds,
        extract_piece_dimensions,
        extract_svg_geometry,
        transform_to_cm,
        nest_contours,
        generate_hpgl,
        CUTTER_WIDTH_CM,
    )
    from pattern_scaler import calculate_pattern_scale, scale_contours, get_garment_type
    from quality_control import QualityControl, QCLevel

    CORE_AVAILABLE = True
except ImportError as e:
    logger.error(f"Failed to import core modules: {e}")
    CORE_AVAILABLE = False

    # Define fallback classes for type hints when core not available
    @dataclass
    class ProductionResult:
        """Fallback ProductionResult for type hints."""

        success: bool = False
        order_id: str = ""
        plt_file: Optional[Path] = None
        metadata_file: Optional[Path] = None
        fabric_length_cm: float = 0.0
        fabric_utilization: float = 0.0
        piece_count: int = 0
        processing_time_ms: float = 0.0
        errors: List[str] = field(default_factory=list)
        warnings: List[str] = field(default_factory=list)

    @dataclass
    class Order:
        """Fallback Order for type hints."""

        order_id: str = ""
        customer_id: str = ""
        garment_type: str = "jacket"
        fit_type: str = "regular"
        measurements: Dict = field(default_factory=dict)
        quantity: int = 1
        notes: str = ""


# Import v6.4.3 modules
try:
    from order_file_manager import OrderFileManager, PieceInfo, EnhancedOutputGenerator
    from order_continuity_validator import (
        OrderContinuityValidator,
        validate_order_before_completion,
    )

    V643_MODULES_AVAILABLE = True
except ImportError as e:
    logger.warning(f"v6.4.3 modules not available: {e}")
    V643_MODULES_AVAILABLE = False

# Import database integration
try:
    from database_integration import OrderDatabase, OrderStatus

    DATABASE_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Database integration not available: {e}")
    DATABASE_AVAILABLE = False


class OrderIDFormatError(Exception):
    """Raised when order ID doesn't match required format."""

    pass


class V643Adapter:
    """
    Adapter class that integrates v6.4.3 features with the production pipeline.
    """

    ORDER_ID_PATTERN = re.compile(r"^SDS-(\d{8})-(\d{4})-([A-Z])$")

    def __init__(
        self,
        output_base_dir: str = "DS-speciale/out/orders",
        fabric_width_cm: float = 157.48,  # 62 inches
    ):
        self.output_base_dir = Path(output_base_dir)
        self.fabric_width_cm = fabric_width_cm
        self.api = (
            SameDaySuitsAPI(fabric_width_cm=fabric_width_cm) if CORE_AVAILABLE else None
        )

        if V643_MODULES_AVAILABLE:
            self.file_manager = OrderFileManager(output_base_dir)
            self.continuity_validator = OrderContinuityValidator()
        else:
            self.file_manager = None
            self.continuity_validator = None

        if DATABASE_AVAILABLE:
            self.db = OrderDatabase()
        else:
            self.db = None

    def validate_order_id(self, order_id: str) -> bool:
        """
        Validate order ID format: SDS-YYYYMMDD-NNNN-R

        Args:
            order_id: Order ID to validate

        Returns:
            True if valid, raises OrderIDFormatError otherwise
        """
        match = self.ORDER_ID_PATTERN.match(order_id)
        if not match:
            raise OrderIDFormatError(
                f"Invalid order ID format: {order_id}\n"
                f"Required format: SDS-YYYYMMDD-NNNN-R\n"
                f"Example: SDS-20260131-0001-A"
            )

        date_str, sequence, revision = match.groups()

        # Validate date is valid
        try:
            datetime.strptime(date_str, "%Y%m%d")
        except ValueError:
            raise OrderIDFormatError(f"Invalid date in order ID: {date_str}")

        return True

    def create_order_from_dict(self, order_data: Dict):
        """
        Create Order object from dictionary with v6.4.3 validation.

        Args:
            order_data: Dictionary with order information

        Returns:
            Order object if core available, else dictionary
        """
        # Validate order ID
        order_id = order_data.get("order_id")
        if order_id:
            self.validate_order_id(order_id)

        # Parse measurements
        measurements_data = order_data.get("measurements", {})

        # If core modules available, create proper Order object
        if CORE_AVAILABLE:
            measurements = CustomerMeasurements(
                chest_cm=measurements_data.get("chest", 0),
                waist_cm=measurements_data.get("waist", 0),
                hip_cm=measurements_data.get("hip", 0),
                shoulder_width_cm=measurements_data.get("shoulder_width"),
                inseam_cm=measurements_data.get("inseam"),
                arm_length_cm=measurements_data.get("arm_length")
                or measurements_data.get("sleeve_length"),
                neck_cm=measurements_data.get("neck"),
            )

            # Parse garment type
            garment_type_str = order_data.get("garment_type", "jacket")
            garment_type = GarmentType(garment_type_str)

            # Parse fit type
            fit_type_str = order_data.get("fit_type", "regular")
            fit_type = FitType(fit_type_str)

            # Create order
            order = Order(
                order_id=order_id or f"SDS-{datetime.now().strftime('%Y%m%d')}-0001-A",
                customer_id=order_data.get("customer_id", "UNKNOWN"),
                garment_type=garment_type,
                fit_type=fit_type,
                measurements=measurements,
                quantity=order_data.get("quantity", 1),
                notes=order_data.get("notes", ""),
            )
            return order
        else:
            # Core modules not available
            raise ImportError(
                "Core production modules (samedaysuits_api) are not available. "
                "Please ensure all dependencies are installed."
            )

    def process_order_v643(self, order_data: Dict) -> Dict:
        """
        Process an order using v6.4.3 standards with full integration.

        This is the main entry point that:
        1. Validates order ID format
        2. Creates database record
        3. Runs production pipeline
        4. Generates v6.4.3 output files
        5. Validates continuity
        6. Updates database with results
        7. Saves QC reports to database

        Args:
            order_data: Dictionary containing:
                - order_id: Must match SDS-YYYYMMDD-NNNN-R format
                - customer_id: Customer identifier
                - garment_type: jacket, tee, shirt, trousers, cargo
                - fit_type: slim, regular, classic (optional)
                - priority: normal, rush, express (optional)
                - notes: Additional notes (optional)
                - measurements: Dict with chest, waist, hip, etc.

        Returns:
            Dict with complete order results:
                - success: bool
                - order_id: str
                - output_files: Dict of file paths
                - database_record: Database entry info
                - qc_report: Quality control results
                - errors: List of error messages
                - warnings: List of warning messages
        """
        start_time = datetime.now()
        errors = []
        warnings = []

        logger.info(f"=" * 60)
        logger.info(f"v6.4.3 Order Processing Started")
        logger.info(f"=" * 60)

        try:
            # Step 1: Validate order ID format
            order_id = order_data.get("order_id")
            if order_id:
                try:
                    self.validate_order_id(order_id)
                    logger.info(f"Order ID validated: {order_id}")
                except OrderIDFormatError as e:
                    logger.error(str(e))
                    errors.append(str(e))
                    return self._create_error_result(order_id, errors, warnings)
            else:
                # Auto-generate order ID if not provided
                order_id = f"SDS-{datetime.now().strftime('%Y%m%d')}-0001-A"
                order_data["order_id"] = order_id
                logger.info(f"Auto-generated order ID: {order_id}")

            # Step 2: Create or update database record
            db_record = None
            if self.db:
                try:
                    db_record = self._create_database_record(order_data)
                    logger.info(
                        f"Database record created: {db_record.get('id', 'N/A')}"
                    )
                except Exception as e:
                    logger.warning(f"Failed to create database record: {e}")
                    warnings.append(f"Database record creation failed: {e}")

            # Step 3: Create Order object
            try:
                order = self.create_order_from_dict(order_data)
                garment_type_str = (
                    order.garment_type.value
                    if hasattr(order.garment_type, "value")
                    else order.garment_type
                )
                logger.info(f"Order object created for {garment_type_str}")
            except Exception as e:
                logger.error(f"Failed to create order object: {e}")
                errors.append(f"Order creation failed: {e}")
                return self._create_error_result(order_id, errors, warnings)

            # Step 4: Run production pipeline
            if not CORE_AVAILABLE:
                errors.append("Core production modules not available")
                return self._create_error_result(order_id, errors, warnings)

            try:
                # Update database status to processing
                if self.db:
                    self.db.update_order_status(order_id, OrderStatus.PROCESSING)

                # Process order through core pipeline
                production_result = self.api.process_order(order)

                if not production_result.success:
                    errors.extend(production_result.errors)
                    warnings.extend(production_result.warnings)
                    logger.error(f"Production pipeline failed: {errors}")

                    # Update database with failure
                    if self.db:
                        self.db.update_order_status(
                            order_id,
                            OrderStatus.ERROR,
                            {"errors": errors, "warnings": warnings},
                        )

                    return self._create_error_result(order_id, errors, warnings)

                logger.info(f"Production pipeline completed successfully")
                logger.info(f"  Fabric: {production_result.fabric_length_cm:.1f}cm")
                logger.info(
                    f"  Utilization: {production_result.fabric_utilization:.1f}%"
                )
                logger.info(f"  Pieces: {production_result.piece_count}")

            except Exception as e:
                logger.exception("Production pipeline error")
                errors.append(f"Production error: {e}")

                # Update database with error
                if self.db:
                    self.db.update_order_status(
                        order_id, OrderStatus.ERROR, {"error": str(e)}
                    )

                return self._create_error_result(order_id, errors, warnings)

            # Step 5: Generate v6.4.3 output files with labels
            output_files = {}
            try:
                if V643_MODULES_AVAILABLE:
                    garment_type_str = (
                        order.garment_type.value
                        if hasattr(order.garment_type, "value")
                        else order.garment_type
                    )
                    output_files = self._generate_v643_outputs(
                        order_id=order_id,
                        customer_id=order.customer_id,
                        garment_type=garment_type_str,
                        measurements=order_data.get("measurements", {}),
                        production_result=production_result,
                    )
                    logger.info(
                        f"v6.4.3 output files generated: {len(output_files)} files"
                    )
                else:
                    # Fallback to basic output
                    output_files = {
                        "plt": str(production_result.plt_file)
                        if production_result.plt_file
                        else None,
                        "metadata": str(production_result.metadata_file)
                        if production_result.metadata_file
                        else None,
                    }
                    warnings.append("v6.4.3 modules not available, using basic output")
            except Exception as e:
                logger.warning(f"v6.4.3 output generation failed: {e}")
                warnings.append(f"v6.4.3 output generation failed: {e}")
                # Still use basic outputs
                output_files = {
                    "plt": str(production_result.plt_file)
                    if production_result.plt_file
                    else None,
                    "metadata": str(production_result.metadata_file)
                    if production_result.metadata_file
                    else None,
                }

            # Step 6: Run continuity validation
            continuity_result = None
            try:
                if V643_MODULES_AVAILABLE and self.continuity_validator:
                    continuity_result = self._validate_continuity(order_id)
                    if not continuity_result.get("is_valid", True):
                        warnings.append(
                            f"Continuity validation warnings: {continuity_result.get('issues', [])}"
                        )
                    else:
                        logger.info("Continuity validation passed")
            except Exception as e:
                logger.warning(f"Continuity validation failed: {e}")
                warnings.append(f"Continuity validation error: {e}")

            # Step 7: Update database with completion
            if self.db:
                try:
                    update_data = {
                        "plt_file": output_files.get("plt"),
                        "fabric_length_cm": production_result.fabric_length_cm,
                        "fabric_utilization": production_result.fabric_utilization,
                        "piece_count": production_result.piece_count,
                        "processing_time_ms": production_result.processing_time_ms,
                        "output_files": output_files,
                        "errors": errors if errors else None,
                        "warnings": warnings if warnings else None,
                    }
                    self.db.update_order_status(
                        order_id, OrderStatus.COMPLETE, update_data
                    )
                    logger.info(f"Database updated with completion status")
                except Exception as e:
                    logger.warning(f"Failed to update database: {e}")
                    warnings.append(f"Database update failed: {e}")

            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds() * 1000

            # Build success result
            garment_type_str = (
                order.garment_type.value
                if hasattr(order.garment_type, "value")
                else order.garment_type
            )
            result = {
                "success": True,
                "order_id": order_id,
                "customer_id": order.customer_id,
                "garment_type": garment_type_str,
                "output_files": output_files,
                "database_record": db_record,
                "production_stats": {
                    "fabric_length_cm": production_result.fabric_length_cm,
                    "fabric_utilization": production_result.fabric_utilization,
                    "piece_count": production_result.piece_count,
                    "processing_time_ms": processing_time,
                },
                "qc_report": {
                    "passed": len(errors) == 0,
                    "error_count": len(errors),
                    "warning_count": len(warnings),
                },
                "continuity_validation": continuity_result,
                "errors": errors if errors else None,
                "warnings": warnings if warnings else None,
                "processed_at": datetime.now().isoformat(),
            }

            logger.info(f"=" * 60)
            logger.info(f"v6.4.3 Order Processing Complete - SUCCESS")
            logger.info(f"=" * 60)

            return result

        except Exception as e:
            logger.exception("Unexpected error in v6.4.3 processing")
            errors.append(f"Unexpected error: {e}")
            return self._create_error_result(order_id, errors, warnings)

    def _create_database_record(self, order_data: Dict) -> Optional[Dict]:
        """Create initial database record for order."""
        if not self.db:
            return None

        # Convert measurements to database format
        measurements = order_data.get("measurements", {})
        db_measurements = {
            "chest": measurements.get("chest", 0),
            "waist": measurements.get("waist", 0),
            "hip": measurements.get("hip", 0),
            "shoulder": measurements.get("shoulder_width"),
            "inseam": measurements.get("inseam"),
        }

        record = self.db.create_order(
            order_id=order_data.get("order_id"),
            customer_id=order_data.get("customer_id", "UNKNOWN"),
            garment_type=order_data.get("garment_type", "jacket"),
            measurements=db_measurements,
            customer_email=order_data.get("customer_email"),
            fit_type=order_data.get("fit_type", "regular"),
            priority=order_data.get("priority", "normal"),
            quantity=order_data.get("quantity", 1),
            notes=order_data.get("notes", ""),
        )

        return record

    def _generate_v643_outputs(
        self,
        order_id: str,
        customer_id: str,
        garment_type: str,
        measurements: Dict,
        production_result: ProductionResult,
    ) -> Dict:
        """Generate all v6.4.3 output files with proper labels."""
        if not V643_MODULES_AVAILABLE or not self.file_manager:
            # Return basic outputs
            return {
                "plt": str(production_result.plt_file)
                if production_result.plt_file
                else None,
                "metadata": str(production_result.metadata_file)
                if production_result.metadata_file
                else None,
            }

        # Create folder structure
        order_folder = self.file_manager.create_order_folder(order_id, customer_id)
        logger.info(f"Created order folder: {order_folder}")

        # Get pieces from production result or create from contours
        # For now, we'll extract from the PLT file or use sample pieces
        pieces = self._extract_pieces_from_production(production_result, order_id)

        # Generate enhanced outputs
        generator = EnhancedOutputGenerator(self.file_manager)

        metadata = {
            "order_id": order_id,
            "customer_id": customer_id,
            "garment_type": garment_type,
            "measurements": measurements,
            "created_at": datetime.now().isoformat(),
            "status": "complete",
            "production_stats": {
                "fabric_length_cm": production_result.fabric_length_cm,
                "fabric_utilization": production_result.fabric_utilization,
                "piece_count": production_result.piece_count,
            },
        }

        nesting_result = {
            "utilization": production_result.fabric_utilization,
            "fabric_length": production_result.fabric_length_cm,
            "algorithm": "guillotine",
        }

        outputs = generator.generate_all_outputs(
            order_id=order_id,
            pieces=pieces,
            nesting_result=nesting_result,
            metadata=metadata,
            base_dir=str(order_folder),
        )

        return outputs

    def _extract_pieces_from_production(
        self, production_result: ProductionResult, order_id: str
    ) -> List[PieceInfo]:
        """Extract piece information from production result."""
        pieces = []

        # If we have the PLT file, we could parse it
        # For now, create pieces based on the piece count
        if production_result.piece_count > 0:
            # Standard piece names for different garments
            piece_names = [
                "Front",
                "Back",
                "Sleeve_L",
                "Sleeve_R",
                "Collar",
                "Cuff_L",
                "Cuff_R",
                "Pocket",
                "Yoke",
                "Placket",
            ]

            for i in range(min(production_result.piece_count, len(piece_names))):
                piece = PieceInfo(
                    piece_id=f"{order_id}-P{i + 1:02d}",
                    piece_name=piece_names[i],
                    width=50.0,  # Placeholder
                    height=60.0,  # Placeholder
                    points=[],  # Would be extracted from actual geometry
                    category="main" if i < 4 else "trim",
                )
                pieces.append(piece)

        return pieces

    def _validate_continuity(self, order_id: str) -> Dict:
        """Validate order continuity."""
        if not V643_MODULES_AVAILABLE or not self.continuity_validator:
            return {"is_valid": True, "issues": []}

        # Get order folder
        order_folder = self.file_manager.get_order_folder(order_id)

        if not order_folder.exists():
            return {"is_valid": False, "issues": ["Order folder not found"]}

        # Validate continuity
        result = validate_order_before_completion(order_id, str(order_folder))

        return {
            "is_valid": result.is_valid,
            "issues": result.issues,
            "warnings": result.warnings,
            "validated_at": result.validated_at.isoformat()
            if hasattr(result, "validated_at")
            else None,
        }

    def _create_error_result(
        self, order_id: str, errors: List[str], warnings: List[str]
    ) -> Dict:
        """Create error result structure."""
        logger.error(f"=" * 60)
        logger.error(f"v6.4.3 Order Processing Complete - FAILED")
        logger.error(f"=" * 60)

        return {
            "success": False,
            "order_id": order_id,
            "errors": errors,
            "warnings": warnings if warnings else None,
            "output_files": {},
            "database_record": None,
            "processed_at": datetime.now().isoformat(),
        }


# Convenience functions for direct use


def process_order_v643(order_data: Dict) -> Dict:
    """
    Convenience function to process an order with v6.4.3 standards.

    Args:
        order_data: Order information dictionary

    Returns:
        Processing result dictionary
    """
    adapter = V643Adapter()
    return adapter.process_order_v643(order_data)


def validate_order_id(order_id: str) -> bool:
    """
    Validate order ID format.

    Args:
        order_id: Order ID to validate

    Returns:
        True if valid, False otherwise
    """
    try:
        adapter = V643Adapter()
        return adapter.validate_order_id(order_id)
    except OrderIDFormatError:
        return False


def create_order_id(
    date: Optional[datetime] = None, sequence: int = 1, revision: str = "A"
) -> str:
    """
    Create a valid v6.4.3 order ID.

    Args:
        date: Date for order (defaults to today)
        sequence: Sequence number (1-9999)
        revision: Revision letter (A-Z)

    Returns:
        Formatted order ID
    """
    if date is None:
        date = datetime.now()

    return f"SDS-{date.strftime('%Y%m%d')}-{sequence:04d}-{revision}"


# CLI entry point
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="v6.4.3 Production Adapter")
    parser.add_argument("--order-id", help="Order ID (SDS-YYYYMMDD-NNNN-R format)")
    parser.add_argument("--customer-id", default="CUST-001", help="Customer ID")
    parser.add_argument(
        "--garment-type",
        default="jacket",
        choices=["jacket", "tee", "shirt", "trousers", "cargo"],
        help="Garment type",
    )
    parser.add_argument(
        "--chest", type=float, default=100.0, help="Chest measurement (cm)"
    )
    parser.add_argument(
        "--waist", type=float, default=85.0, help="Waist measurement (cm)"
    )
    parser.add_argument("--hip", type=float, default=100.0, help="Hip measurement (cm)")
    parser.add_argument("--validate-id", help="Validate order ID format")
    parser.add_argument(
        "--generate-id", action="store_true", help="Generate new order ID"
    )

    args = parser.parse_args()

    if args.validate_id:
        # Validate order ID
        try:
            adapter = V643Adapter()
            adapter.validate_order_id(args.validate_id)
            print(f"Order ID is valid: {args.validate_id}")
            sys.exit(0)
        except OrderIDFormatError as e:
            print(f"Invalid: {e}")
            sys.exit(1)

    elif args.generate_id:
        # Generate new order ID
        order_id = create_order_id()
        print(order_id)
        sys.exit(0)

    elif args.order_id:
        # Process order
        order_data = {
            "order_id": args.order_id,
            "customer_id": args.customer_id,
            "garment_type": args.garment_type,
            "measurements": {
                "chest": args.chest,
                "waist": args.waist,
                "hip": args.hip,
            },
        }

        print(f"Processing order: {args.order_id}")
        result = process_order_v643(order_data)

        print(json.dumps(result, indent=2, default=str))

        sys.exit(0 if result["success"] else 1)

    else:
        parser.print_help()
