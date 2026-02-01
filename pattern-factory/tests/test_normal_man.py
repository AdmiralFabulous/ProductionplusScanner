#!/usr/bin/env python3
"""
End-to-End Test: Normal Man → Production File
"""

import sys

sys.path.insert(0, ".")

from theblackbox_integration import TheBlackboxIntegration
from samedaysuits_api import (
    SameDaySuitsAPI,
    Order,
    CustomerMeasurements,
    GarmentType,
    FitType,
)
from datetime import datetime
import json

print("=" * 70)
print("END-TO-END WORKFLOW: Normal Man to Production File")
print("=" * 70)

# Step 1: Load and validate scan
print("\n[Step 1] Loading body scan data...")
blackbox = TheBlackboxIntegration()
scan_file = "scans/SCAN-NORMAL-MAN-20260131014740.json"
scan_data = blackbox.load_scan(scan_file)

print(f"  Customer: {scan_data.customer_id}")
print(f"  Measurements:")
print(f"    Chest: {scan_data.measurements.chest_cm}cm")
print(f"    Waist: {scan_data.measurements.waist_cm}cm")
print(f"    Hip: {scan_data.measurements.hip_cm}cm")
print(f"    Shoulder: {scan_data.measurements.shoulder_width_cm}cm")
print(f"    Arm: {scan_data.measurements.arm_length_cm}cm")
print(f"    Inseam: {scan_data.measurements.inseam_cm}cm")
print(f"  Confidence: {scan_data.measurements.confidence:.0%}")

# Step 2: Validate scan
print("\n[Step 2] Validating scan quality...")
validation = blackbox.validate_scan(scan_data)
status = "PASSED" if validation.valid else "FAILED"
print(f"  Status: {status}")
print(f"  Quality Score: {validation.quality_score:.0%}")

# Step 3: Create production order
print("\n[Step 3] Creating production order...")
garment_type = "jacket"
fit_type = "regular"

order = blackbox.create_order_from_scan(
    scan_data=scan_data,
    garment_type=garment_type,
    fit_type=fit_type,
)

print(f"  Order ID: {order['order_id']}")
print(f"  Garment: {order['garment_type'].upper()}")
print(f"  Fit: {order['fit_type']}")
print(f"  Source: {order['source']}")

# Step 4: Process through production pipeline
print("\n[Step 4] Processing through production pipeline...")
print("  This may take 30-60 seconds...")

api = SameDaySuitsAPI()

order_obj = Order(
    order_id=order["order_id"],
    customer_id=order["customer_id"],
    garment_type=GarmentType(order["garment_type"]),
    fit_type=FitType(order["fit_type"]),
    measurements=CustomerMeasurements(
        chest_cm=order["measurements"]["chest_cm"],
        waist_cm=order["measurements"]["waist_cm"],
        hip_cm=order["measurements"]["hip_cm"],
        shoulder_width_cm=order["measurements"].get("shoulder_width_cm"),
        arm_length_cm=order["measurements"].get("arm_length_cm"),
        inseam_cm=order["measurements"].get("inseam_cm"),
        neck_cm=order["measurements"].get("neck_cm"),
        source="theblackbox",
    ),
)

result = api.process_order(order_obj)

if result.success:
    print(f"\n  [SUCCESS] Production complete!")
    print(f"    PLT File: {result.plt_file}")
    print(f"    Fabric Length: {result.fabric_length_cm:.1f} cm")
    print(f"    Fabric Utilization: {result.fabric_utilization:.1f}%")
    print(f"    Piece Count: {result.piece_count}")
    print(f"    Processing Time: {result.processing_time_ms / 1000:.1f}s")

    # Save result info
    output_info = {
        "order_id": result.order_id,
        "plt_file": str(result.plt_file),
        "metadata_file": str(result.metadata_file),
        "fabric_length_cm": result.fabric_length_cm,
        "fabric_utilization": result.fabric_utilization,
        "piece_count": result.piece_count,
        "warnings": result.warnings,
    }

    with open("NORMAL_MAN_RESULT.json", "w") as f:
        json.dump(output_info, f, indent=2)

    print(f"\n  Result saved to: NORMAL_MAN_RESULT.json")
else:
    print(f"\n  [FAILED] {result.errors}")

print("\n" + "=" * 70)
