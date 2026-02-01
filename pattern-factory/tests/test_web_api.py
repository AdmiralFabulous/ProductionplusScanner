#!/usr/bin/env python3
"""
Test script for the SameDaySuits Web API

This script tests all API endpoints without needing to run the server separately.
It uses FastAPI's TestClient for synchronous testing.

Run with: python test_web_api.py
"""

import json
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))


def test_api():
    """Test all API endpoints."""
    from fastapi.testclient import TestClient
    from web_api import app

    client = TestClient(app)

    print("\n" + "=" * 60)
    print("SAMEDAYSUITS WEB API TESTS")
    print("=" * 60)

    tests_passed = 0
    tests_total = 0

    # Test 1: Health check
    tests_total += 1
    print("\n[Test 1] Health Check...")
    response = client.get("/health")
    if response.status_code == 200 and response.json().get("status") == "healthy":
        print("  PASS: Health endpoint returns healthy")
        tests_passed += 1
    else:
        print(f"  FAIL: {response.status_code} - {response.text}")

    # Test 2: Dashboard HTML
    tests_total += 1
    print("\n[Test 2] Dashboard HTML...")
    response = client.get("/")
    if response.status_code == 200 and "SameDaySuits" in response.text:
        print("  PASS: Dashboard HTML loads correctly")
        tests_passed += 1
    else:
        print(f"  FAIL: {response.status_code}")

    # Test 3: List templates
    tests_total += 1
    print("\n[Test 3] List Templates...")
    response = client.get("/templates")
    if response.status_code == 200:
        templates = response.json()
        available = [t for t in templates if t["available"]]
        print(f"  PASS: {len(available)} templates available")
        for t in templates:
            status = "OK" if t["available"] else "MISSING"
            print(f"    - {t['garment_type']}: [{status}]")
        tests_passed += 1
    else:
        print(f"  FAIL: {response.status_code} - {response.text}")

    # Test 4: Queue status
    tests_total += 1
    print("\n[Test 4] Queue Status...")
    response = client.get("/queue/status")
    if response.status_code == 200:
        status = response.json()
        print(f"  PASS: Queue status retrieved")
        print(f"    - Total jobs: {status['total_jobs']}")
        print(f"    - Pending: {status['pending_jobs']}")
        print(f"    - Complete: {status['complete_jobs']}")
        tests_passed += 1
    else:
        print(f"  FAIL: {response.status_code} - {response.text}")

    # Test 5: List jobs
    tests_total += 1
    print("\n[Test 5] List Jobs...")
    response = client.get("/queue/jobs")
    if response.status_code == 200:
        jobs = response.json()
        print(f"  PASS: {len(jobs)} jobs in queue")
        tests_passed += 1
    else:
        print(f"  FAIL: {response.status_code} - {response.text}")

    # Test 6: Submit an order
    tests_total += 1
    print("\n[Test 6] Submit Order...")
    order_data = {
        "order_id": "TEST-API-001",
        "customer_id": "CUST-TEST",
        "garment_type": "tee",
        "fit_type": "regular",
        "priority": "normal",
        "measurements": {"chest_cm": 102, "waist_cm": 88, "hip_cm": 100},
    }
    response = client.post("/orders", json=order_data)
    if response.status_code == 200:
        result = response.json()
        if result["success"]:
            print(f"  PASS: Order submitted successfully")
            print(f"    - Order ID: {result['order_id']}")
            print(f"    - Fabric: {result['fabric_length_cm']:.1f} cm")
            print(f"    - Utilization: {result['fabric_utilization']:.1f}%")
            print(f"    - Job ID: {result['job_id']}")
            tests_passed += 1
        else:
            print(f"  FAIL: Order failed - {result['errors']}")
    else:
        print(f"  FAIL: {response.status_code} - {response.text}")

    # Test 7: Get order details
    tests_total += 1
    print("\n[Test 7] Get Order Details...")
    response = client.get("/orders/TEST-API-001")
    if response.status_code == 200:
        order = response.json()
        print(f"  PASS: Order details retrieved")
        print(f"    - Template: {order.get('production', {}).get('template', 'N/A')}")
        tests_passed += 1
    else:
        print(f"  FAIL: {response.status_code} - {response.text}")

    # Test 8: Submit order for different garment
    tests_total += 1
    print("\n[Test 8] Submit Jacket Order...")
    order_data = {
        "order_id": "TEST-API-002",
        "customer_id": "CUST-TEST",
        "garment_type": "jacket",
        "fit_type": "regular",
        "priority": "rush",
        "measurements": {"chest_cm": 108, "waist_cm": 92, "hip_cm": 104},
    }
    response = client.post("/orders", json=order_data)
    if response.status_code == 200:
        result = response.json()
        if result["success"]:
            print(f"  PASS: Jacket order submitted")
            print(f"    - Fabric: {result['fabric_length_cm']:.1f} cm")
            print(f"    - Utilization: {result['fabric_utilization']:.1f}%")
            tests_passed += 1
        else:
            print(f"  FAIL: {result['errors']}")
    else:
        print(f"  FAIL: {response.status_code}")

    # Test 9: Invalid garment type
    tests_total += 1
    print("\n[Test 9] Invalid Garment Type (should fail)...")
    order_data = {
        "order_id": "TEST-API-003",
        "customer_id": "CUST-TEST",
        "garment_type": "invalid_type",
        "measurements": {"chest_cm": 100, "waist_cm": 85, "hip_cm": 100},
    }
    response = client.post("/orders", json=order_data)
    if response.status_code == 400 or (
        response.status_code == 200 and not response.json().get("success")
    ):
        print(f"  PASS: Invalid garment type correctly rejected")
        tests_passed += 1
    else:
        print(f"  FAIL: Should have rejected invalid garment type")

    # Test 10: Queue status after orders
    tests_total += 1
    print("\n[Test 10] Queue Status After Orders...")
    response = client.get("/queue/status")
    if response.status_code == 200:
        status = response.json()
        print(f"  PASS: Queue updated")
        print(f"    - Total jobs: {status['total_jobs']}")
        print(f"    - Pending: {status['pending_jobs']}")
        print(f"    - Est. time: {status['estimated_time_minutes']:.1f} min")
        tests_passed += 1
    else:
        print(f"  FAIL: {response.status_code}")

    # Summary
    print("\n" + "=" * 60)
    print(f"TESTS: {tests_passed}/{tests_total} PASSED")
    print("=" * 60)

    if tests_passed == tests_total:
        print("\nAll tests passed! The Web API is working correctly.")
    else:
        print(f"\n{tests_total - tests_passed} test(s) failed.")

    return tests_passed == tests_total


def test_websocket():
    """Test WebSocket connection."""
    print("\n" + "=" * 60)
    print("WEBSOCKET TEST")
    print("=" * 60)

    from fastapi.testclient import TestClient
    from web_api import app

    client = TestClient(app)

    try:
        with client.websocket_connect("/ws") as websocket:
            # Should receive initial status
            data = websocket.receive_json()
            print(f"Received initial status: {data['event']}")

            if data["event"] == "status_update":
                print("  PASS: WebSocket connected and received status")
                return True
    except Exception as e:
        print(f"  FAIL: WebSocket error - {e}")
        return False


if __name__ == "__main__":
    # Run tests
    api_ok = test_api()
    ws_ok = test_websocket()

    print("\n" + "=" * 60)
    print("FINAL RESULT")
    print("=" * 60)
    print(f"API Tests:       {'PASS' if api_ok else 'FAIL'}")
    print(f"WebSocket Tests: {'PASS' if ws_ok else 'FAIL'}")
    print("=" * 60)

    sys.exit(0 if (api_ok and ws_ok) else 1)
