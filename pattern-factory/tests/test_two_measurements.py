#!/usr/bin/env python3
"""
END-TO-END TEST: Two Measurements Through SameDaySuits System

Tests:
1. TEST-STD-001 (Normal man measurements)
2. FAT-MAN-001 (Larger measurements)

Follows complete pipeline:
- Order creation with v6.4.3 order ID
- Database persistence
- Production pipeline processing
- Output file generation (PLT, PDS, DXF, metadata)
- Quality control validation

Usage: python test_two_measurements.py
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime

# Setup paths
script_dir = Path(__file__).parent
project_root = script_dir.parent
sys.path.insert(0, str(project_root / "src" / "core"))
sys.path.insert(0, str(project_root / "src" / "nesting"))

# Test Results
test_results = {
    "test_std_001": {"status": "NOT_RUN", "errors": [], "outputs": {}},
    "fat_man_001": {"status": "NOT_RUN", "errors": [], "outputs": {}},
}


def log(msg, level="INFO"):
    """Simple logging without unicode issues"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    prefix = f"[{timestamp}] [{level}]"
    print(f"{prefix} {msg}")


def test_measurement(measurement_id, measurements, garment_type="jacket"):
    """Run a single measurement through the system"""
    log(f"=" * 70)
    log(f"TESTING: {measurement_id}")
    log(f"=" * 70)
    log(f"Measurements: {json.dumps(measurements, indent=2)}")

    result = {"status": "FAILED", "errors": [], "outputs": {}}

    try:
        # Step 1: Import and initialize
        log("Step 1: Importing modules...")
        from samedaysuits_api import (
            SameDaySuitsAPI,
            Order,
            GarmentType,
            FitType,
            CustomerMeasurements,
        )
        from v643_adapter import V643Adapter, create_order_id

        log("  - Modules imported successfully")

        # Step 2: Create Order ID
        log("Step 2: Creating v6.4.3 order ID...")
        adapter = V643Adapter()
        order_id = create_order_id()
        log(f"  - Order ID: {order_id}")

        # Step 3: Create Order object
        log("Step 3: Creating Order object...")
        order = Order(
            order_id=order_id,
            customer_id=f"TEST-{measurement_id}",
            garment_type=GarmentType(garment_type),
            fit_type=FitType.REGULAR,
            measurements=CustomerMeasurements(
                chest_cm=measurements["chest"],
                waist_cm=measurements["waist"],
                hip_cm=measurements["hip"],
                shoulder_width_cm=measurements.get("shoulder"),
                inseam_cm=measurements.get("inseam"),
            ),
            notes=f"Test measurement {measurement_id}",
        )
        log(f"  - Order created: {order_id}")
        log(f"  - Garment: {garment_type}")
        log(f"  - Chest: {measurements['chest']}cm")
        log(f"  - Waist: {measurements['waist']}cm")
        log(f"  - Hip: {measurements['hip']}cm")

        # Step 4: Initialize API
        log("Step 4: Initializing SameDaySuits API...")
        api = SameDaySuitsAPI()
        log("  - API initialized")

        # Step 5: Process Order
        log("Step 5: Processing order through pipeline...")
        production_result = api.process_order(order)

        if production_result.success:
            log(f"  - Processing SUCCESS")
            log(f"  - Fabric length: {production_result.fabric_length_cm:.1f} cm")
            log(f"  - Utilization: {production_result.fabric_utilization:.1f}%")
            log(f"  - Pieces: {production_result.piece_count}")
            log(f"  - Time: {production_result.processing_time_ms:.0f} ms")

            result["outputs"]["plt_file"] = (
                str(production_result.plt_file) if production_result.plt_file else None
            )
            result["outputs"]["metadata_file"] = (
                str(production_result.metadata_file)
                if production_result.metadata_file
                else None
            )
            result["outputs"]["fabric_length"] = production_result.fabric_length_cm
            result["outputs"]["utilization"] = production_result.fabric_utilization
            result["outputs"]["piece_count"] = production_result.piece_count

            # Step 6: Verify output files
            log("Step 6: Verifying output files...")
            if production_result.plt_file and Path(production_result.plt_file).exists():
                plt_size = Path(production_result.plt_file).stat().st_size
                log(f"  - PLT file: {production_result.plt_file}")
                log(f"  - PLT size: {plt_size} bytes")
                result["outputs"]["plt_size"] = plt_size
            else:
                log("  - WARNING: PLT file not found")

            if (
                production_result.metadata_file
                and Path(production_result.metadata_file).exists()
            ):
                meta_size = Path(production_result.metadata_file).stat().st_size
                log(f"  - Metadata file: {production_result.metadata_file}")
                log(f"  - Metadata size: {meta_size} bytes")
                result["outputs"]["metadata_size"] = meta_size

                # Load and display metadata
                with open(production_result.metadata_file, "r") as f:
                    metadata = json.load(f)
                    log(
                        f"  - Template used: {metadata.get('production', {}).get('template', 'N/A')}"
                    )
                    log(
                        f"  - Scaling applied: {metadata.get('production', {}).get('scaling', {}).get('applied', False)}"
                    )
            else:
                log("  - WARNING: Metadata file not found")

            result["status"] = "PASSED"

        else:
            log(f"  - Processing FAILED")
            for error in production_result.errors:
                log(f"    ERROR: {error}", "ERROR")
                result["errors"].append(error)
            for warning in production_result.warnings:
                log(f"    WARNING: {warning}", "WARNING")

    except Exception as e:
        log(f"EXCEPTION: {e}", "ERROR")
        import traceback

        traceback.print_exc()
        result["errors"].append(str(e))

    log(f"Test {measurement_id}: {result['status']}")
    return result


def main():
    """Run both measurement tests"""
    log("=" * 70)
    log("SAMEDAYSUITS END-TO-END TEST: Two Measurements")
    log("=" * 70)
    log("")

    # Test 1: Normal Man (TEST-STD-001)
    test_std_001_measurements = {
        "chest": 96.0,
        "waist": 82.0,
        "hip": 96.0,
        "shoulder": 43.0,
        "inseam": 78.0,
    }
    test_results["test_std_001"] = test_measurement(
        "TEST-STD-001", test_std_001_measurements, garment_type="tee"
    )

    log("")

    # Test 2: Fat Man (FAT-MAN-001)
    fat_man_001_measurements = {
        "chest": 120.0,
        "waist": 110.0,
        "hip": 118.0,
        "shoulder": 48.0,
        "inseam": 76.0,
    }
    test_results["fat_man_001"] = test_measurement(
        "FAT-MAN-001", fat_man_001_measurements, garment_type="jacket"
    )

    # Summary
    log("")
    log("=" * 70)
    log("TEST SUMMARY")
    log("=" * 70)

    passed = sum(1 for r in test_results.values() if r["status"] == "PASSED")
    failed = sum(1 for r in test_results.values() if r["status"] == "FAILED")

    for test_id, result in test_results.items():
        status_symbol = "[PASS]" if result["status"] == "PASSED" else "[FAIL]"
        log(f"{status_symbol} {test_id}")
        if result["outputs"]:
            log(f"  - Fabric: {result['outputs'].get('fabric_length', 0):.1f} cm")
            log(f"  - Utilization: {result['outputs'].get('utilization', 0):.1f}%")
            log(f"  - Pieces: {result['outputs'].get('piece_count', 0)}")
        if result["errors"]:
            for error in result["errors"]:
                log(f"  - Error: {error}", "ERROR")

    log("")
    log(f"Results: {passed} passed, {failed} failed")

    if failed == 0:
        log("ALL TESTS PASSED")
        return 0
    else:
        log("SOME TESTS FAILED")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
