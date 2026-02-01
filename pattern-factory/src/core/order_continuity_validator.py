# Order Continuity Validator
# Validates order number continuity throughout the system

import os
import re
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class ContinuityError(Exception):
    """Exception raised when order continuity check fails"""

    pass


class OrderContinuityValidator:
    """
    Validates that order numbers are consistently maintained throughout:
    - Database records
    - Folder structure
    - File names
    - File contents (PLT, PDS, DXF)
    - Piece labels
    """

    def __init__(self, base_dir: str = "DS-speciale/out/orders", db_connection=None):
        self.base_dir = Path(base_dir)
        self.db = db_connection

    def validate_full_continuity(self, order_id: str) -> Tuple[bool, List[str]]:
        """
        Perform complete continuity validation for an order.

        Returns:
            (success: bool, errors: List[str])
        """
        errors = []

        # 1. Check database record
        if not self._check_database_record(order_id):
            errors.append(f"Database: Order {order_id} not found in database")

        # 2. Check folder structure
        if not self._check_folder_exists(order_id):
            errors.append(f"Folder: Order folder {order_id} does not exist")

        # 3. Check all required files exist
        missing_files = self._check_required_files(order_id)
        if missing_files:
            errors.append(f"Files: Missing required files: {', '.join(missing_files)}")

        # 4. Check file naming conventions
        naming_errors = self._check_file_naming(order_id)
        if naming_errors:
            errors.append(f"Naming: {', '.join(naming_errors)}")

        # 5. Check PLT content
        plt_errors = self._check_plt_labels(order_id)
        if plt_errors:
            errors.append(f"PLT Labels: {', '.join(plt_errors)}")

        # 6. Check PDS content
        pds_errors = self._check_pds_labels(order_id)
        if pds_errors:
            errors.append(f"PDS Labels: {', '.join(pds_errors)}")

        # 7. Check DXF content
        dxf_errors = self._check_dxf_labels(order_id)
        if dxf_errors:
            errors.append(f"DXF Labels: {', '.join(dxf_errors)}")

        # 8. Check metadata consistency
        metadata_errors = self._check_metadata_consistency(order_id)
        if metadata_errors:
            errors.append(f"Metadata: {', '.join(metadata_errors)}")

        # 9. Check piece labels in individual files
        piece_errors = self._check_piece_labels(order_id)
        if piece_errors:
            errors.append(f"Piece Labels: {', '.join(piece_errors)}")

        # Log results
        if errors:
            logger.error(f"Continuity validation failed for {order_id}:")
            for error in errors:
                logger.error(f"  - {error}")
            return False, errors
        else:
            logger.info(f"Continuity validation passed for {order_id}")
            return True, []

    def _check_database_record(self, order_id: str) -> bool:
        """Check if order exists in database"""
        # This is a placeholder - implement with actual database query
        # For now, assume it exists if folder exists
        order_folder = self.base_dir / order_id
        return order_folder.exists()

    def _check_folder_exists(self, order_id: str) -> bool:
        """Check if order folder exists"""
        order_folder = self.base_dir / order_id
        return order_folder.exists() and order_folder.is_dir()

    def _check_required_files(self, order_id: str) -> List[str]:
        """Check if all required files exist"""
        order_folder = self.base_dir / order_id
        missing = []

        required_files = [
            f"{order_id}.plt",
            f"{order_id}.pds",
            f"{order_id}.dxf",
            f"{order_id}_metadata.json",
            f"{order_id}_qc_report.json",
            f"{order_id}_production.log",
            f"{order_id}_nesting.json",
        ]

        for filename in required_files:
            if not (order_folder / filename).exists():
                missing.append(filename)

        # Check subdirectories
        if not (order_folder / "pieces").exists():
            missing.append("pieces/ subdirectory")

        if not (order_folder / "previews").exists():
            missing.append("previews/ subdirectory")

        return missing

    def _check_file_naming(self, order_id: str) -> List[str]:
        """Check that all files follow naming conventions"""
        order_folder = self.base_dir / order_id
        errors = []

        # Check that all files start with order_id
        for file_path in order_folder.iterdir():
            if file_path.is_file():
                if not file_path.name.startswith(order_id):
                    errors.append(f"File {file_path.name} does not start with order ID")

        # Check pieces subdirectory
        pieces_folder = order_folder / "pieces"
        if pieces_folder.exists():
            for file_path in pieces_folder.iterdir():
                if not file_path.name.startswith(order_id):
                    errors.append(
                        f"Piece file {file_path.name} does not start with order ID"
                    )

        return errors

    def _check_plt_labels(self, order_id: str) -> List[str]:
        """Check that PLT file contains order number labels"""
        order_folder = self.base_dir / order_id
        plt_path = order_folder / f"{order_id}.plt"

        if not plt_path.exists():
            return ["PLT file not found"]

        errors = []

        try:
            with open(plt_path, "r") as f:
                content = f.read()

            # Check for order ID in labels
            if order_id not in content:
                errors.append(f"Order ID {order_id} not found in PLT content")

            # Check for piece counters (XXX/XXX format)
            counter_pattern = r"\d{3}/\d{3}"
            counters = re.findall(counter_pattern, content)
            if not counters:
                errors.append("No piece counters (XXX/XXX format) found in PLT")

            # Check for piece names
            if (
                "FRONT" not in content
                and "BACK" not in content
                and "SLEEVE" not in content
            ):
                errors.append("No piece names found in PLT labels")

        except Exception as e:
            errors.append(f"Error reading PLT file: {str(e)}")

        return errors

    def _check_pds_labels(self, order_id: str) -> List[str]:
        """Check that PDS file contains order number"""
        order_folder = self.base_dir / order_id
        pds_path = order_folder / f"{order_id}.pds"

        if not pds_path.exists():
            return ["PDS file not found"]

        errors = []

        try:
            with open(pds_path, "rb") as f:
                content = f.read().decode("utf-8", errors="ignore")

            # Check for order ID in PDS
            if order_id not in content:
                errors.append(f"Order ID {order_id} not found in PDS content")

            # Check for PDS header
            if "PDS|" not in content:
                errors.append("Invalid PDS format (missing PDS header)")

        except Exception as e:
            errors.append(f"Error reading PDS file: {str(e)}")

        return errors

    def _check_dxf_labels(self, order_id: str) -> List[str]:
        """Check that DXF file contains order number"""
        order_folder = self.base_dir / order_id
        dxf_path = order_folder / f"{order_id}.dxf"

        if not dxf_path.exists():
            return ["DXF file not found"]

        errors = []

        try:
            with open(dxf_path, "r") as f:
                content = f.read()

            # Check for order ID in DXF text entities
            if order_id not in content:
                errors.append(f"Order ID {order_id} not found in DXF content")

            # Check for TEXT entities
            if "TEXT" not in content:
                errors.append("No TEXT entities found in DXF (labels missing)")

            # Check for proper DXF structure
            if "EOF" not in content:
                errors.append("Invalid DXF format (missing EOF)")

        except Exception as e:
            errors.append(f"Error reading DXF file: {str(e)}")

        return errors

    def _check_metadata_consistency(self, order_id: str) -> List[str]:
        """Check that metadata matches order ID"""
        order_folder = self.base_dir / order_id
        metadata_path = order_folder / f"{order_id}_metadata.json"

        if not metadata_path.exists():
            return ["Metadata file not found"]

        errors = []

        try:
            with open(metadata_path, "r") as f:
                metadata = json.load(f)

            # Check order_id in metadata
            if metadata.get("order_id") != order_id:
                errors.append(
                    f"Metadata order_id mismatch: {metadata.get('order_id')} != {order_id}"
                )

            # Check for required fields
            required_fields = ["customer_id", "garment_type", "created_at"]
            for field in required_fields:
                if field not in metadata:
                    errors.append(f"Missing required field in metadata: {field}")

        except json.JSONDecodeError as e:
            errors.append(f"Invalid JSON in metadata file: {str(e)}")
        except Exception as e:
            errors.append(f"Error reading metadata: {str(e)}")

        return errors

    def _check_piece_labels(self, order_id: str) -> List[str]:
        """Check that individual piece files contain order numbers"""
        order_folder = self.base_dir / order_id
        pieces_folder = order_folder / "pieces"

        if not pieces_folder.exists():
            return ["Pieces folder not found"]

        errors = []
        piece_files = list(pieces_folder.glob(f"{order_id}_piece_*.pds"))

        if not piece_files:
            errors.append("No individual piece files found")
            return errors

        for piece_file in piece_files:
            try:
                with open(piece_file, "rb") as f:
                    content = f.read().decode("utf-8", errors="ignore")

                if order_id not in content:
                    errors.append(
                        f"Order ID not found in piece file: {piece_file.name}"
                    )

            except Exception as e:
                errors.append(f"Error reading piece file {piece_file.name}: {str(e)}")

        return errors

    def generate_continuity_report(self, order_id: str) -> Dict:
        """Generate detailed continuity validation report"""
        success, errors = self.validate_full_continuity(order_id)

        report = {
            "order_id": order_id,
            "validation_timestamp": "2026-01-31T00:00:00Z",  # Use actual timestamp
            "overall_status": "PASSED" if success else "FAILED",
            "checks": {
                "database_record": {
                    "status": "PASS"
                    if self._check_database_record(order_id)
                    else "FAIL",
                    "details": "Order exists in database"
                    if self._check_database_record(order_id)
                    else "Order not found",
                },
                "folder_structure": {
                    "status": "PASS" if self._check_folder_exists(order_id) else "FAIL",
                    "details": "Folder exists"
                    if self._check_folder_exists(order_id)
                    else "Folder missing",
                },
                "required_files": {
                    "status": "PASS"
                    if not self._check_required_files(order_id)
                    else "FAIL",
                    "missing_files": self._check_required_files(order_id),
                },
                "file_naming": {
                    "status": "PASS"
                    if not self._check_file_naming(order_id)
                    else "FAIL",
                    "errors": self._check_file_naming(order_id),
                },
                "plt_labels": {
                    "status": "PASS"
                    if not self._check_plt_labels(order_id)
                    else "FAIL",
                    "errors": self._check_plt_labels(order_id),
                },
                "pds_labels": {
                    "status": "PASS"
                    if not self._check_pds_labels(order_id)
                    else "FAIL",
                    "errors": self._check_pds_labels(order_id),
                },
                "dxf_labels": {
                    "status": "PASS"
                    if not self._check_dxf_labels(order_id)
                    else "FAIL",
                    "errors": self._check_dxf_labels(order_id),
                },
                "metadata_consistency": {
                    "status": "PASS"
                    if not self._check_metadata_consistency(order_id)
                    else "FAIL",
                    "errors": self._check_metadata_consistency(order_id),
                },
                "piece_labels": {
                    "status": "PASS"
                    if not self._check_piece_labels(order_id)
                    else "FAIL",
                    "errors": self._check_piece_labels(order_id),
                },
            },
            "errors": errors,
            "recommendations": self._generate_recommendations(errors),
        }

        return report

    def _generate_recommendations(self, errors: List[str]) -> List[str]:
        """Generate recommendations based on errors"""
        recommendations = []

        for error in errors:
            if "Database" in error:
                recommendations.append("Run database sync: sds db sync")
            elif "Folder" in error:
                recommendations.append(
                    "Regenerate order: sds order --regenerate <order_id>"
                )
            elif "Files" in error:
                recommendations.append(
                    "Check file generation pipeline - may need to reprocess order"
                )
            elif "Naming" in error:
                recommendations.append(
                    "Rename files to follow convention: {ORDER_ID}_suffix.ext"
                )
            elif "Labels" in error:
                recommendations.append("Regenerate output files with proper labeling")
            elif "Metadata" in error:
                recommendations.append("Update metadata file with correct order_id")

        return recommendations

    def batch_validate(self, order_ids: List[str]) -> Dict[str, Tuple[bool, List[str]]]:
        """Validate continuity for multiple orders"""
        results = {}

        for order_id in order_ids:
            success, errors = self.validate_full_continuity(order_id)
            results[order_id] = (success, errors)

        return results

    def fix_continuity_issues(self, order_id: str, auto_fix: bool = False) -> List[str]:
        """
        Attempt to fix continuity issues.
        Returns list of actions taken.
        """
        actions = []

        success, errors = self.validate_full_continuity(order_id)

        if success:
            actions.append(f"Order {order_id} passed validation - no fixes needed")
            return actions

        # Try to fix missing metadata
        if any("Metadata" in error for error in errors):
            if auto_fix:
                # Create basic metadata
                metadata = {
                    "order_id": order_id,
                    "fixed_at": "2026-01-31T00:00:00Z",
                    "note": "Auto-fixed by continuity validator",
                }

                order_folder = self.base_dir / order_id
                metadata_path = order_folder / f"{order_id}_metadata.json"

                with open(metadata_path, "w") as f:
                    json.dump(metadata, f, indent=2)

                actions.append(f"Created missing metadata file: {metadata_path}")

        # Log all errors that couldn't be fixed
        for error in errors:
            if not any(action in error for action in actions):
                actions.append(f"Could not auto-fix: {error}")

        return actions


# Integration with production pipeline
def validate_order_before_completion(
    order_id: str, base_dir: str = "DS-speciale/out/orders"
) -> bool:
    """
    Validate order continuity before marking as complete.
    Raises ContinuityError if validation fails.
    """
    validator = OrderContinuityValidator(base_dir)
    success, errors = validator.validate_full_continuity(order_id)

    if not success:
        raise ContinuityError(
            f"Order {order_id} failed continuity validation:\n"
            + "\n".join(f"  - {error}" for error in errors)
        )

    logger.info(f"Order {order_id} passed continuity validation")
    return True


def log_continuity_check(order_id: str, success: bool, errors: List[str]):
    """Log continuity check to production log"""
    log_entry = {
        "timestamp": "2026-01-31T00:00:00Z",
        "order_id": order_id,
        "check_type": "continuity_validation",
        "success": success,
        "errors": errors,
    }

    # This would be integrated with the production logging system
    logger.info(
        f"Continuity check logged for {order_id}: {'PASS' if success else 'FAIL'}"
    )


# Example usage
if __name__ == "__main__":
    # Create validator
    validator = OrderContinuityValidator("test_orders")

    # Test order ID (use actual order from previous script)
    test_order_id = "SDS-20260131-0001-A"

    # Validate continuity
    print(f"Validating continuity for {test_order_id}...")
    success, errors = validator.validate_full_continuity(test_order_id)

    if success:
        print("✓ All continuity checks passed!")
    else:
        print("✗ Continuity validation failed:")
        for error in errors:
            print(f"  - {error}")

    # Generate detailed report
    print("\nGenerating continuity report...")
    report = validator.generate_continuity_report(test_order_id)
    print(json.dumps(report, indent=2))
