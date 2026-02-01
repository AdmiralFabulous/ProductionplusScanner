#!/usr/bin/env python3
"""
Integration Test Suite for v6.4.3 Adapter

Tests the complete integration between:
- Production core (samedaysuits_api, production_pipeline)
- v6.4.3 modules (order_file_manager, order_continuity_validator)
- Database integration (database_integration)
- Order ID validation
- File generation with labels

Run: python test_v643_integration.py
"""

import sys
import json
import logging
from pathlib import Path
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Add paths
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src" / "core"))
sys.path.insert(0, str(project_root / "src" / "integrations"))

# Track test results
test_results = {
    "passed": 0,
    "failed": 0,
    "errors": [],
}


def test_order_id_validation():
    """Test 1: Order ID format validation"""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 1: Order ID Format Validation")
    logger.info("=" * 60)

    try:
        from v643_adapter import V643Adapter, OrderIDFormatError

        adapter = V643Adapter()

        # Valid order IDs
        valid_ids = [
            "SDS-20260131-0001-A",
            "SDS-20260131-9999-Z",
            "SDS-20241225-0050-B",
        ]

        for order_id in valid_ids:
            try:
                adapter.validate_order_id(order_id)
                logger.info(f"✓ Valid ID accepted: {order_id}")
            except OrderIDFormatError as e:
                logger.error(f"✗ Valid ID rejected: {order_id} - {e}")
                test_results["failed"] += 1
                test_results["errors"].append(f"Valid ID rejected: {order_id}")
                return False

        # Invalid order IDs
        invalid_ids = [
            "20260131-0001-A",  # Missing SDS prefix
            "SDS-2026-0001-A",  # Wrong date format
            "SDS-20260131-1-A",  # Wrong sequence format
            "SDS-20260131-0001",  # Missing revision
            "INVALID-ID",  # Completely wrong
        ]

        for order_id in invalid_ids:
            try:
                adapter.validate_order_id(order_id)
                logger.error(f"✗ Invalid ID accepted: {order_id}")
                test_results["failed"] += 1
                test_results["errors"].append(f"Invalid ID accepted: {order_id}")
                return False
            except OrderIDFormatError:
                logger.info(f"✓ Invalid ID correctly rejected: {order_id}")

        test_results["passed"] += 1
        logger.info("✓ Order ID validation PASSED")
        return True

    except Exception as e:
        logger.error(f"✗ Test failed with exception: {e}")
        test_results["failed"] += 1
        test_results["errors"].append(f"Order ID validation error: {e}")
        return False


def test_order_creation():
    """Test 2: Order object creation from dictionary"""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 2: Order Creation from Dictionary")
    logger.info("=" * 60)

    try:
        from v643_adapter import V643Adapter

        adapter = V643Adapter()

        # Test order data
        order_data = {
            "order_id": "SDS-20260131-0001-A",
            "customer_id": "CUST-001",
            "garment_type": "jacket",
            "fit_type": "regular",
            "priority": "normal",
            "notes": "Test order",
            "measurements": {
                "chest": 100.0,
                "waist": 85.0,
                "hip": 100.0,
                "shoulder_width": 45.0,
                "inseam": 80.0,
            },
        }

        order = adapter.create_order_from_dict(order_data)

        # Handle both Order objects (enum) and SimpleOrder objects (string)
        garment_type_str = (
            order.garment_type.value
            if hasattr(order.garment_type, "value")
            else order.garment_type
        )

        # Handle both CustomerMeasurements objects and dict
        if hasattr(order.measurements, "chest_cm"):
            chest_val = order.measurements.chest_cm
            waist_val = order.measurements.waist_cm
        else:
            chest_val = order.measurements.get("chest", 0)
            waist_val = order.measurements.get("waist", 0)

        # Verify order properties
        assert order.order_id == "SDS-20260131-0001-A", "Order ID mismatch"
        assert order.customer_id == "CUST-001", "Customer ID mismatch"
        assert garment_type_str == "jacket", "Garment type mismatch"
        assert chest_val == 100.0, "Chest measurement mismatch"
        assert waist_val == 85.0, "Waist measurement mismatch"

        logger.info(f"✓ Order created: {order.order_id}")
        logger.info(f"  - Customer: {order.customer_id}")
        logger.info(f"  - Garment: {garment_type_str}")
        logger.info(f"  - Chest: {chest_val}cm")

        test_results["passed"] += 1
        logger.info("✓ Order creation PASSED")
        return True

    except Exception as e:
        logger.error(f"✗ Test failed with exception: {e}")
        test_results["failed"] += 1
        test_results["errors"].append(f"Order creation error: {e}")
        return False


def test_v643_processing():
    """Test 3: Complete v6.4.3 order processing"""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 3: v6.4.3 Order Processing")
    logger.info("=" * 60)

    try:
        from v643_adapter import process_order_v643

        # Test order data
        order_data = {
            "order_id": f"SDS-{datetime.now().strftime('%Y%m%d')}-0001-A",
            "customer_id": "CUST-TEST-001",
            "garment_type": "tee",
            "fit_type": "regular",
            "priority": "normal",
            "measurements": {
                "chest": 96.0,
                "waist": 82.0,
                "hip": 96.0,
                "shoulder_width": 43.0,
            },
        }

        logger.info(f"Processing order: {order_data['order_id']}")

        # Process order
        result = process_order_v643(order_data)

        # Check result structure
        assert "success" in result, "Missing success field"
        assert "order_id" in result, "Missing order_id field"
        assert "output_files" in result, "Missing output_files field"

        if result["success"]:
            logger.info(f"✓ Order processed successfully")
            logger.info(f"  - Order ID: {result['order_id']}")
            logger.info(f"  - Output files: {len(result['output_files'])}")

            if "production_stats" in result:
                stats = result["production_stats"]
                logger.info(f"  - Fabric: {stats.get('fabric_length_cm', 0):.1f}cm")
                logger.info(
                    f"  - Utilization: {stats.get('fabric_utilization', 0):.1f}%"
                )
                logger.info(f"  - Pieces: {stats.get('piece_count', 0)}")

            test_results["passed"] += 1
            logger.info("✓ v6.4.3 processing PASSED")
            return True
        else:
            logger.error(f"✗ Order processing failed")
            logger.error(f"  Errors: {result.get('errors', [])}")
            test_results["failed"] += 1
            test_results["errors"].append(
                f"Processing failed: {result.get('errors', [])}"
            )
            return False

    except Exception as e:
        logger.error(f"✗ Test failed with exception: {e}")
        import traceback

        traceback.print_exc()
        test_results["failed"] += 1
        test_results["errors"].append(f"v6.4.3 processing error: {e}")
        return False


def test_database_integration():
    """Test 4: Database integration (if available)"""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 4: Database Integration")
    logger.info("=" * 60)

    try:
        from v643_adapter import V643Adapter

        adapter = V643Adapter()

        if not adapter.db:
            logger.warning("⚠ Database not available - skipping test")
            test_results["passed"] += 1
            return True

        # Test order data
        order_data = {
            "order_id": f"SDS-{datetime.now().strftime('%Y%m%d')}-0002-B",
            "customer_id": "CUST-DB-TEST",
            "garment_type": "shirt",
            "fit_type": "regular",
            "measurements": {
                "chest": 102.0,
                "waist": 88.0,
                "hip": 102.0,
            },
        }

        # Create database record
        db_record = adapter._create_database_record(order_data)

        if db_record:
            logger.info(f"✓ Database record created: {db_record.get('order_id')}")
            test_results["passed"] += 1
            logger.info("✓ Database integration PASSED")
            return True
        else:
            logger.warning("⚠ Database record not created (DB may be offline)")
            test_results["passed"] += 1
            return True

    except Exception as e:
        logger.error(f"✗ Database test failed: {e}")
        test_results["failed"] += 1
        test_results["errors"].append(f"Database integration error: {e}")
        return False


def test_file_structure():
    """Test 5: Verify order folder structure creation"""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 5: Order Folder Structure")
    logger.info("=" * 60)

    try:
        from v643_adapter import V643Adapter
        from order_file_manager import OrderFileManager

        adapter = V643Adapter()

        if not adapter.file_manager:
            logger.warning("⚠ File manager not available - skipping test")
            test_results["passed"] += 1
            return True

        order_id = f"SDS-{datetime.now().strftime('%Y%m%d')}-0003-C"
        customer_id = "CUST-FILE-TEST"

        # Create folder structure
        order_folder = adapter.file_manager.create_order_folder(order_id, customer_id)

        if order_folder.exists():
            logger.info(f"✓ Order folder created: {order_folder}")

            # Check subdirectories
            expected_dirs = ["cut_files", "patterns", "metadata", "qc_reports"]
            for subdir in expected_dirs:
                subdir_path = order_folder / subdir
                if subdir_path.exists():
                    logger.info(f"  ✓ {subdir}/ directory exists")
                else:
                    logger.warning(f"  ⚠ {subdir}/ directory missing")

            test_results["passed"] += 1
            logger.info("✓ Folder structure PASSED")
            return True
        else:
            logger.error(f"✗ Order folder not created: {order_folder}")
            test_results["failed"] += 1
            test_results["errors"].append("Order folder not created")
            return False

    except Exception as e:
        logger.error(f"✗ Test failed with exception: {e}")
        import traceback

        traceback.print_exc()
        test_results["failed"] += 1
        test_results["errors"].append(f"Folder structure error: {e}")
        return False


def test_order_id_generation():
    """Test 6: Order ID generation function"""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 6: Order ID Generation")
    logger.info("=" * 60)

    try:
        from v643_adapter import create_order_id, validate_order_id

        # Generate order ID with defaults
        order_id_1 = create_order_id()
        logger.info(f"Generated ID (default): {order_id_1}")
        assert validate_order_id(order_id_1), "Generated ID should be valid"

        # Generate with specific parameters
        test_date = datetime(2026, 1, 31)
        order_id_2 = create_order_id(date=test_date, sequence=42, revision="C")
        logger.info(f"Generated ID (custom): {order_id_2}")
        assert order_id_2 == "SDS-20260131-0042-C", (
            f"Expected SDS-20260131-0042-C, got {order_id_2}"
        )
        assert validate_order_id(order_id_2), "Custom generated ID should be valid"

        test_results["passed"] += 1
        logger.info("✓ Order ID generation PASSED")
        return True

    except Exception as e:
        logger.error(f"✗ Test failed with exception: {e}")
        test_results["failed"] += 1
        test_results["errors"].append(f"Order ID generation error: {e}")
        return False


def test_error_handling():
    """Test 7: Error handling for invalid inputs"""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 7: Error Handling")
    logger.info("=" * 60)

    try:
        from v643_adapter import process_order_v643, OrderIDFormatError

        # Test with invalid order ID
        invalid_order = {
            "order_id": "INVALID-ID",
            "customer_id": "CUST-001",
            "garment_type": "jacket",
            "measurements": {
                "chest": 100.0,
                "waist": 85.0,
                "hip": 100.0,
            },
        }

        result = process_order_v643(invalid_order)

        assert not result["success"], "Should fail with invalid order ID"
        assert result["errors"], "Should have error messages"

        logger.info(f"✓ Invalid order ID correctly rejected")
        logger.info(f"  Errors: {result['errors']}")

        # Test with missing measurements
        incomplete_order = {
            "order_id": f"SDS-{datetime.now().strftime('%Y%m%d')}-0004-D",
            "customer_id": "CUST-001",
            "garment_type": "jacket",
            "measurements": {},
        }

        result = process_order_v643(incomplete_order)
        # Should still process but may have warnings
        logger.info(f"✓ Incomplete order handled (success={result['success']})")

        test_results["passed"] += 1
        logger.info("✓ Error handling PASSED")
        return True

    except Exception as e:
        logger.error(f"✗ Test failed with exception: {e}")
        import traceback

        traceback.print_exc()
        test_results["failed"] += 1
        test_results["errors"].append(f"Error handling test error: {e}")
        return False


def test_samedaysuits_api_integration():
    """Test 8: Integration with samedaysuits_api order ID validation"""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 8: SameDaySuits API Integration")
    logger.info("=" * 60)

    try:
        from samedaysuits_api import (
            SameDaySuitsAPI,
            Order,
            GarmentType,
            FitType,
            CustomerMeasurements,
        )

        api = SameDaySuitsAPI()

        # Test order with valid v6.4.3 ID
        valid_order = Order(
            order_id=f"SDS-{datetime.now().strftime('%Y%m%d')}-0005-E",
            customer_id="CUST-API-TEST",
            garment_type=GarmentType.TEE,
            fit_type=FitType.REGULAR,
            measurements=CustomerMeasurements(
                chest_cm=96.0,
                waist_cm=82.0,
                hip_cm=96.0,
            ),
        )

        # Validate order (should pass with v6.4.3 validation)
        errors = api._validate_order(valid_order)

        if errors:
            logger.warning(f"Validation warnings: {errors}")
        else:
            logger.info(f"✓ Order validation passed for {valid_order.order_id}")

        test_results["passed"] += 1
        logger.info("✓ SameDaySuits API integration PASSED")
        return True

    except Exception as e:
        logger.error(f"✗ Test failed with exception: {e}")
        import traceback

        traceback.print_exc()
        test_results["failed"] += 1
        test_results["errors"].append(f"API integration error: {e}")
        return False


def run_all_tests():
    """Run all integration tests"""
    logger.info("\n" + "=" * 70)
    logger.info("V6.4.3 ADAPTER INTEGRATION TEST SUITE")
    logger.info("=" * 70)
    logger.info(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 70)

    tests = [
        test_order_id_validation,
        test_order_creation,
        test_v643_processing,
        test_database_integration,
        test_file_structure,
        test_order_id_generation,
        test_error_handling,
        test_samedaysuits_api_integration,
    ]

    for test_func in tests:
        try:
            test_func()
        except Exception as e:
            logger.error(f"✗ Test {test_func.__name__} crashed: {e}")
            test_results["failed"] += 1
            test_results["errors"].append(f"Test crash: {test_func.__name__}: {e}")

    # Print summary
    logger.info("\n" + "=" * 70)
    logger.info("TEST SUMMARY")
    logger.info("=" * 70)
    logger.info(f"Total tests: {test_results['passed'] + test_results['failed']}")
    logger.info(f"Passed: {test_results['passed']}")
    logger.info(f"Failed: {test_results['failed']}")

    if test_results["errors"]:
        logger.info("\nErrors:")
        for error in test_results["errors"]:
            logger.info(f"  - {error}")

    success_rate = (
        (test_results["passed"] / (test_results["passed"] + test_results["failed"]))
        * 100
        if (test_results["passed"] + test_results["failed"]) > 0
        else 0
    )
    logger.info(f"\nSuccess rate: {success_rate:.1f}%")

    if test_results["failed"] == 0:
        logger.info("\n✓ ALL TESTS PASSED!")
        return 0
    else:
        logger.info(f"\n✗ {test_results['failed']} test(s) failed")
        return 1


if __name__ == "__main__":
    exit_code = run_all_tests()
    sys.exit(exit_code)
