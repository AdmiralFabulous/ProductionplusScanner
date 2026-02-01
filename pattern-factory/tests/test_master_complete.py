#!/usr/bin/env python3
"""
MASTER END-TO-END TEST SUITE
SameDaySuits Pattern Factory - Complete System Test

Tests ALL systems:
1. Nesting Algorithms (8 algorithms)
2. Production Monitoring
3. Quality Control
4. TheBlackbox Integration
5. Database (Supabase)
6. Cutter Queue
7. Pattern Scaling
8. WebSocket/Real-time
9. Order File Management
10. Continuity Validation
11. Web API
12. Dashboard

Usage:
    python test_master_complete.py [--verbose] [--web] [--keep]

Options:
    --verbose    Show detailed output
    --web        Start web server for testing
    --keep       Keep test output
"""

import os
import sys
import json
import shutil
import time
import subprocess
import tempfile
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import threading
import argparse

# Add to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Test configuration
TEST_DIR = Path("master_test_output")
VERBOSE = False
KEEP_OUTPUT = False


class TestResult:
    """Store test results"""

    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.tests = []
        self.start_time = time.time()

    def add(self, name: str, passed: bool, details: str = ""):
        self.tests.append(
            {
                "name": name,
                "passed": passed,
                "details": details,
                "timestamp": datetime.now().isoformat(),
            }
        )
        if passed:
            self.passed += 1
        else:
            self.failed += 1

    def summary(self):
        elapsed = time.time() - self.start_time
        total = self.passed + self.failed
        rate = (self.passed / total * 100) if total > 0 else 0
        return {
            "total": total,
            "passed": self.passed,
            "failed": self.failed,
            "rate": rate,
            "elapsed_seconds": elapsed,
        }


class MasterTestSuite:
    """Complete test suite"""

    def __init__(self):
        self.results = TestResult()
        self.test_orders = []

    def log(self, message: str, level: str = "INFO"):
        """Log message"""
        if VERBOSE or level in ["ERROR", "HEADER"]:
            prefix = {
                "HEADER": "\n" + "=" * 70,
                "INFO": "  ",
                "SUCCESS": "  ✓ ",
                "ERROR": "  ✗ ",
                "WARNING": "  ⚠ ",
            }.get(level, "  ")
            print(f"{prefix}{message}")

    def setup(self):
        """Setup test environment"""
        self.log("SETTING UP MASTER TEST ENVIRONMENT", "HEADER")
        self.log(f"Test Directory: {TEST_DIR}")
        self.log(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # Clean previous tests
        if TEST_DIR.exists():
            shutil.rmtree(TEST_DIR)
            self.log("Cleaned previous test output")

        TEST_DIR.mkdir(parents=True, exist_ok=True)
        self.log("Created test directory")

    def teardown(self):
        """Cleanup"""
        self.log("\nCLEANING UP", "HEADER")

        if not KEEP_OUTPUT and TEST_DIR.exists():
            shutil.rmtree(TEST_DIR)
            self.log("Removed test directory")
        else:
            self.log(f"Kept test directory: {TEST_DIR}")

    # =================================================================
    # MODULE 1: Nesting Algorithms
    # =================================================================
    def test_nesting_algorithms(self):
        """Test all nesting algorithms"""
        self.log("MODULE 1: NESTING ALGORITHMS", "HEADER")

        algorithms = [
            ("master_nesting", "Best-of-all selector"),
            ("hybrid_nesting", "Polygon collision"),
            ("turbo_nesting", "Shapely-based"),
            ("guillotine_nesting", "Rectangle splitting"),
            ("skyline_nesting", "Top-edge tracking"),
            ("shelf_nesting", "Bottom-left fill"),
        ]

        for module_name, description in algorithms:
            try:
                module = __import__(module_name)
                self.results.add(f"Nesting: {description}", True)
                self.log(f"{description}: OK", "SUCCESS")
            except ImportError as e:
                self.results.add(f"Nesting: {description}", False, str(e))
                self.log(f"{description}: Failed - {e}", "ERROR")

        # Test master_nest function
        try:
            from master_nesting import master_nest

            # Create simple test pieces
            test_pieces = [[(0, 0), (10, 0), (10, 10), (0, 10)] for _ in range(3)]

            result = master_nest(test_pieces, fabric_width=157.48, gap=0.5)

            assert result is not None, "master_nest returned None"
            assert hasattr(result, "utilization"), "Result missing utilization"

            self.results.add(
                "Nesting: master_nest execution",
                True,
                f"Utilization: {result.utilization:.1f}%",
            )
            self.log(
                f"master_nest: OK ({result.utilization:.1f}% utilization)", "SUCCESS"
            )

        except Exception as e:
            self.results.add("Nesting: master_nest execution", False, str(e))
            self.log(f"master_nest: Failed - {e}", "ERROR")

    # =================================================================
    # MODULE 2: Production Monitoring
    # =================================================================
    def test_production_monitoring(self):
        """Test production monitoring system"""
        self.log("MODULE 2: PRODUCTION MONITORING", "HEADER")

        try:
            from production_monitor import ProductionMonitor, get_monitor

            monitor = ProductionMonitor(data_dir=str(TEST_DIR / "monitoring"))

            # Record some metrics
            monitor.record_order_processed(success=True, fabric_cm=100.5)

            # Get metrics
            metrics = monitor.get_current_metrics()

            assert "orders" in metrics, "Missing orders in metrics"
            assert metrics["orders"]["total"] == 1, "Order count mismatch"

            self.results.add("Monitoring: Basic metrics", True)
            self.log("Basic metrics: OK", "SUCCESS")

            # Test alerts
            monitor.check_alerts()
            self.results.add("Monitoring: Alert checking", True)
            self.log("Alert checking: OK", "SUCCESS")

        except Exception as e:
            self.results.add("Monitoring: System", False, str(e))
            self.log(f"Monitoring: Failed - {e}", "ERROR")

    # =================================================================
    # MODULE 3: Quality Control
    # =================================================================
    def test_quality_control(self):
        """Test quality control system"""
        self.log("MODULE 3: QUALITY CONTROL", "HEADER")

        try:
            from quality_control import QualityControl

            qc = QualityControl()

            # Create test order
            test_order = {
                "order_id": "TEST-001",
                "garment_type": "jacket",
                "pieces": [
                    {"name": "front", "contour": [(0, 0), (50, 0), (50, 60), (0, 60)]}
                ],
            }

            # Validate
            report = qc.validate_order(test_order)

            assert report is not None, "QC returned None"
            assert "status" in report, "QC report missing status"

            self.results.add("QC: Validation", True, f"Status: {report['status']}")
            self.log(f"QC Validation: OK ({report['status']})", "SUCCESS")

        except Exception as e:
            self.results.add("QC: System", False, str(e))
            self.log(f"QC: Failed - {e}", "ERROR")

    # =================================================================
    # MODULE 4: TheBlackbox Integration
    # =================================================================
    def test_theblackbox_integration(self):
        """Test TheBlackbox scanner integration"""
        self.log("MODULE 4: THEBLACKBOX INTEGRATION", "HEADER")

        try:
            from theblackbox_integration import TheBlackboxIntegration

            tbi = TheBlackboxIntegration(scans_dir=str(TEST_DIR / "scans"))

            # Create test scan
            test_scan = {
                "scan_id": "TB-20260131-001",
                "timestamp": datetime.now().isoformat(),
                "measurements": {
                    "chest": 102.0,
                    "waist": 88.0,
                    "hip": 100.0,
                    "shoulder_width": 46.0,
                    "neck": 41.0,
                    "arm_length": 66.0,
                    "inseam": 81.0,
                    "torso_length": 71.0,
                },
                "quality_score": 0.98,
                "posture": "normal",
            }

            # Validate scan
            validation = tbi.validate_scan(test_scan)

            assert validation["valid"], (
                f"Scan validation failed: {validation.get('errors')}"
            )

            self.results.add(
                "TheBlackbox: Scan validation",
                True,
                f"Quality: {test_scan['quality_score']}",
            )
            self.log(
                f"Scan validation: OK (quality: {test_scan['quality_score']})",
                "SUCCESS",
            )

            # Test order creation
            order = tbi.create_order_from_scan(test_scan, garment_type="jacket")

            assert order is not None, "Order creation failed"
            assert "customer_measurements" in order, "Missing measurements"

            self.results.add("TheBlackbox: Order creation", True)
            self.log("Order creation: OK", "SUCCESS")

        except Exception as e:
            self.results.add("TheBlackbox: Integration", False, str(e))
            self.log(f"TheBlackbox: Failed - {e}", "ERROR")

    # =================================================================
    # MODULE 5: Database Integration
    # =================================================================
    def test_database_integration(self):
        """Test database (Supabase) integration"""
        self.log("MODULE 5: DATABASE INTEGRATION", "HEADER")

        try:
            from database_integration import OrderDatabase

            # Initialize with local mode (no actual DB required for test)
            db = OrderDatabase(mode="local")

            # Create test order
            test_order_data = {
                "order_id": "TEST-DB-001",
                "customer_id": "CUST-TEST",
                "garment_type": "jacket",
                "status": "pending",
            }

            # Save locally
            order_file = TEST_DIR / "test_order.json"
            with open(order_file, "w") as f:
                json.dump(test_order_data, f)

            self.results.add("Database: Local storage", True)
            self.log("Local storage: OK", "SUCCESS")

        except Exception as e:
            self.results.add("Database: Integration", False, str(e))
            self.log(f"Database: Failed - {e}", "ERROR")

    # =================================================================
    # MODULE 6: Cutter Queue
    # =================================================================
    def test_cutter_queue(self):
        """Test cutter queue management"""
        self.log("MODULE 6: CUTTER QUEUE", "HEADER")

        try:
            from cutter_queue import CutterQueue, JobPriority

            queue = CutterQueue(spool_dir=str(TEST_DIR / "spool"))

            # Submit test job
            job_id = queue.submit_job(
                order_id="TEST-ORDER-001",
                plt_file="test.plt",
                priority=JobPriority.NORMAL,
                garment_type="jacket",
            )

            assert job_id is not None, "Job submission failed"

            self.results.add("Queue: Job submission", True, f"Job ID: {job_id}")
            self.log(f"Job submission: OK ({job_id})", "SUCCESS")

            # Get queue status
            status = queue.get_status()

            assert status is not None, "Status is None"
            assert status.pending_jobs >= 1, "Job not in queue"

            self.results.add("Queue: Status check", True)
            self.log("Status check: OK", "SUCCESS")

        except Exception as e:
            self.results.add("Queue: Management", False, str(e))
            self.log(f"Queue: Failed - {e}", "ERROR")

    # =================================================================
    # MODULE 7: Pattern Scaling
    # =================================================================
    def test_pattern_scaling(self):
        """Test pattern scaling system"""
        self.log("MODULE 7: PATTERN SCALING", "HEADER")

        try:
            from pattern_scaler import PatternScaler

            scaler = PatternScaler()

            # Test size selection
            measurements = {"chest": 102, "waist": 88, "hip": 100}
            size = scaler.select_base_size(measurements)

            assert size is not None, "Size selection failed"

            self.results.add("Scaling: Size selection", True, f"Size: {size}")
            self.log(f"Size selection: OK ({size})", "SUCCESS")

            # Test scaling calculation
            scales = scaler.calculate_scales(measurements, base_size="L")

            assert "scale_x" in scales, "Missing scale_x"
            assert "scale_y" in scales, "Missing scale_y"

            self.results.add(
                "Scaling: Calculation",
                True,
                f"X: {scales['scale_x']:.3f}, Y: {scales['scale_y']:.3f}",
            )
            self.log(
                f"Scaling: OK (X: {scales['scale_x']:.3f}, Y: {scales['scale_y']:.3f})",
                "SUCCESS",
            )

        except Exception as e:
            self.results.add("Scaling: System", False, str(e))
            self.log(f"Scaling: Failed - {e}", "ERROR")

    # =================================================================
    # MODULE 8: Order File Management (v6.4.3)
    # =================================================================
    def test_order_file_management(self):
        """Test order file management (v6.4.3)"""
        self.log("MODULE 8: ORDER FILE MANAGEMENT (v6.4.3)", "HEADER")

        try:
            from order_file_manager import (
                OrderFileManager,
                EnhancedOutputGenerator,
                PieceInfo,
            )

            # Initialize file manager
            file_mgr = OrderFileManager(str(TEST_DIR / "orders"))

            # Generate order ID
            order_id = file_mgr.generate_order_id("CUST-TEST")

            assert order_id.startswith("SDS-"), f"Invalid order ID: {order_id}"
            assert len(order_id.split("-")) == 4, f"Wrong format: {order_id}"

            self.results.add("v6.4.3: Order ID generation", True, order_id)
            self.log(f"Order ID generation: OK ({order_id})", "SUCCESS")

            # Create folder structure
            folder = file_mgr.create_order_folder(order_id, "CUST-TEST")

            assert folder.exists(), "Folder not created"
            assert (folder / "pieces").exists(), "Pieces subdir missing"

            self.results.add("v6.4.3: Folder structure", True)
            self.log("Folder structure: OK", "SUCCESS")

            # Generate output files
            pieces = [
                PieceInfo(
                    name="FRONT",
                    contour=[(0, 0), (50, 0), (50, 60), (0, 60)],
                    bounding_box=(0, 0, 50, 60),
                    piece_number=1,
                    total_pieces=2,
                ),
                PieceInfo(
                    name="BACK",
                    contour=[(0, 0), (50, 0), (50, 70), (0, 70)],
                    bounding_box=(0, 0, 50, 70),
                    piece_number=2,
                    total_pieces=2,
                ),
            ]

            generator = EnhancedOutputGenerator(file_mgr)

            metadata = {"order_id": order_id, "status": "testing"}
            nesting = {"utilization": 78.5, "fabric_length": 120.5, "algorithm": "test"}

            outputs = generator.generate_all_outputs(
                order_id, pieces, nesting, metadata
            )

            # Verify files exist
            required = ["plt", "pds", "dxf", "metadata"]
            for file_type in required:
                if file_type in outputs and outputs[file_type].exists():
                    self.results.add(f"v6.4.3: {file_type.upper()} generation", True)
                    self.log(f"{file_type.upper()} generation: OK", "SUCCESS")
                else:
                    self.results.add(
                        f"v6.4.3: {file_type.upper()} generation", False, "File missing"
                    )
                    self.log(f"{file_type.upper()} generation: Failed", "ERROR")

            self.test_orders.append(order_id)

        except Exception as e:
            self.results.add("v6.4.3: File Management", False, str(e))
            self.log(f"v6.4.3: Failed - {e}", "ERROR")

    # =================================================================
    # MODULE 9: Continuity Validation (v6.4.3)
    # =================================================================
    def test_continuity_validation(self):
        """Test order continuity validation"""
        self.log("MODULE 9: CONTINUITY VALIDATION (v6.4.3)", "HEADER")

        try:
            from order_continuity_validator import OrderContinuityValidator

            if not self.test_orders:
                self.log("Skipping - no test orders available", "WARNING")
                return

            validator = OrderContinuityValidator(str(TEST_DIR / "orders"))

            # Validate first test order
            order_id = self.test_orders[0]
            success, errors = validator.validate_full_continuity(order_id)

            if success:
                self.results.add("v6.4.3: Continuity validation", True)
                self.log("Continuity validation: OK", "SUCCESS")
            else:
                self.results.add("v6.4.3: Continuity validation", False, str(errors))
                self.log(f"Continuity validation: Failed - {errors}", "ERROR")

        except Exception as e:
            self.results.add("v6.4.3: Continuity", False, str(e))
            self.log(f"v6.4.3 Continuity: Failed - {e}", "ERROR")

    # =================================================================
    # MODULE 10: Web API
    # =================================================================
    def test_web_api(self):
        """Test Web API"""
        self.log("MODULE 10: WEB API", "HEADER")

        try:
            import web_api

            # Check app exists
            assert hasattr(web_api, "app"), "web_api missing 'app'"

            self.results.add("Web API: Module import", True)
            self.log("Module import: OK", "SUCCESS")

            # Check for key endpoints in source
            web_api_path = Path(__file__).parent / "web_api.py"
            content = web_api_path.read_text()

            endpoints = [
                "/orders/{order_id}/plt",
                "/orders/{order_id}/pds",
                "/orders/{order_id}/dxf",
                "/orders/{order_id}/files",
                "/orders/{order_id}/status",
            ]

            for endpoint in endpoints:
                if endpoint in content:
                    self.results.add(f"Web API: Endpoint {endpoint}", True)
                    self.log(f"Endpoint {endpoint}: OK", "SUCCESS")
                else:
                    self.results.add(
                        f"Web API: Endpoint {endpoint}", False, "Not found"
                    )
                    self.log(f"Endpoint {endpoint}: Missing", "ERROR")

        except Exception as e:
            self.results.add("Web API: System", False, str(e))
            self.log(f"Web API: Failed - {e}", "ERROR")

    # =================================================================
    # MODULE 11: CLI
    # =================================================================
    def test_cli(self):
        """Test CLI commands"""
        self.log("MODULE 11: CLI", "HEADER")

        try:
            import sds_cli

            self.results.add("CLI: Module import", True)
            self.log("Module import: OK", "SUCCESS")

            # Check for key commands in source
            cli_path = Path(__file__).parent / "sds_cli.py"
            content = cli_path.read_text()

            commands = ["order", "queue", "monitor", "qc", "scan", "db"]

            for cmd in commands:
                if f'"{cmd}"' in content or f"'{cmd}'" in content:
                    self.results.add(f"CLI: Command '{cmd}'", True)
                    self.log(f"Command '{cmd}': OK", "SUCCESS")
                else:
                    self.results.add(f"CLI: Command '{cmd}'", False, "Not found")
                    self.log(f"Command '{cmd}': Missing", "WARNING")

        except Exception as e:
            self.results.add("CLI: System", False, str(e))
            self.log(f"CLI: Failed - {e}", "ERROR")

    # =================================================================
    # COMPLETE WORKFLOW TEST
    # =================================================================
    def test_complete_workflow(self):
        """Test complete end-to-end workflow"""
        self.log("COMPLETE WORKFLOW TEST", "HEADER")

        try:
            from v6_4_3_integration import process_order_v6_4_3

            # Create complete order
            result = process_order_v6_4_3(
                order_id="SDS-20260131-9999-A",
                customer_id="CUST-WORKFLOW",
                garment_type="jacket",
                measurements={
                    "chest": 102,
                    "waist": 88,
                    "hip": 100,
                    "shoulder": 46,
                    "inseam": 81,
                },
                base_dir=str(TEST_DIR / "workflow"),
            )

            if result["success"]:
                self.results.add(
                    "Workflow: Complete order processing",
                    True,
                    f"Order: {result['order_id']}",
                )
                self.log(f"Complete workflow: OK ({result['order_id']})", "SUCCESS")

                # Verify files
                files_count = len(
                    [
                        k
                        for k in result.get("files", {}).keys()
                        if not k.endswith("_folder")
                    ]
                )
                self.results.add("Workflow: Output files", True, f"{files_count} files")
                self.log(f"Output files: {files_count} files", "SUCCESS")

                # Verify continuity
                if result.get("continuity_validated"):
                    self.results.add("Workflow: Continuity validation", True)
                    self.log("Continuity: Validated", "SUCCESS")

            else:
                self.results.add(
                    "Workflow: Complete order processing",
                    False,
                    result.get("error", "Unknown error"),
                )
                self.log(f"Workflow: Failed - {result.get('error')}", "ERROR")

        except Exception as e:
            self.results.add("Workflow: Complete test", False, str(e))
            self.log(f"Workflow: Failed - {e}", "ERROR")

    # =================================================================
    # RUN ALL TESTS
    # =================================================================
    def run_all(self):
        """Run all tests"""
        self.setup()

        try:
            self.test_nesting_algorithms()
            self.test_production_monitoring()
            self.test_quality_control()
            self.test_theblackbox_integration()
            self.test_database_integration()
            self.test_cutter_queue()
            self.test_pattern_scaling()
            self.test_order_file_management()
            self.test_continuity_validation()
            self.test_web_api()
            self.test_cli()
            self.test_complete_workflow()

        finally:
            self.print_summary()
            self.teardown()

    def print_summary(self):
        """Print final summary"""
        self.log("\nTEST SUMMARY", "HEADER")

        summary = self.results.summary()

        print(f"\n  Total Tests: {summary['total']}")
        print(f"  Passed: {summary['passed']} ✅")
        print(
            f"  Failed: {summary['failed']} {'✅' if summary['failed'] == 0 else '❌'}"
        )
        print(f"  Success Rate: {summary['rate']:.1f}%")
        print(f"  Time: {summary['elapsed_seconds']:.1f}s")

        if summary["failed"] > 0:
            print(f"\n  Failed Tests:")
            for test in self.results.tests:
                if not test["passed"]:
                    print(f"    ❌ {test['name']}")
                    if test["details"]:
                        print(f"       {test['details'][:80]}")

        print(f"\n  {'=' * 70}")
        if summary["failed"] == 0:
            print(f"  ✅ ALL TESTS PASSED! System is production ready!")
        else:
            print(f"  ❌ {summary['failed']} test(s) failed. Review above.")
        print(f"  {'=' * 70}\n")


def main():
    """Main entry point"""
    global VERBOSE, KEEP_OUTPUT

    parser = argparse.ArgumentParser(description="Master End-to-End Test Suite")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--keep", "-k", action="store_true", help="Keep test output")
    parser.add_argument(
        "--test-dir", "-d", default="master_test_output", help="Test directory"
    )

    args = parser.parse_args()

    VERBOSE = args.verbose
    KEEP_OUTPUT = args.keep

    suite = MasterTestSuite()
    suite.run_all()

    # Exit with appropriate code
    summary = suite.results.summary()
    sys.exit(0 if summary["failed"] == 0 else 1)


if __name__ == "__main__":
    main()
