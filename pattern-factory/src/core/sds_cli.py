#!/usr/bin/env python3
"""
SameDaySuits Production CLI

Unified command-line interface for the complete production pipeline.

Commands:
    order      - Process a single customer order
    batch      - Process multiple orders from JSON
    queue      - Manage cutter job queue
    templates  - List available templates
    sizes      - Show graded size information
    db         - Database operations (sync orders from Supabase)
    serve      - Start web API server
    test       - Run pipeline test

Examples:
    # Process a single order
    sds order --id ORD-001 --garment tee --chest 102 --waist 88 --hip 100

    # Process batch from JSON
    sds batch orders.json

    # Show queue status
    sds queue status

    # List templates
    sds templates

    # Show size info for a template
    sds sizes --template tee

    # Database sync
    sds db status
    sds db sync
    sds db watch

    # Start web server
    sds serve --port 8000

Author: Claude
Date: 2026-01-30
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Optional
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Add project root to path
# Add project root to path
# production/src/core -> src -> production -> REVERSE-ENGINEER-PDS
project_root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(project_root))
# Also add production/src to path for internal modules
sys.path.insert(0, str(project_root / "production" / "src"))
sys.path.insert(0, str(project_root / "production" / "src" / "nesting"))



def cmd_order(args):
    """Process a single order."""
    from samedaysuits_api import (
        SameDaySuitsAPI,
        Order,
        GarmentType,
        FitType,
        CustomerMeasurements,
    )

    api = SameDaySuitsAPI()

    # Build order
    order = Order(
        order_id=args.id,
        customer_id=args.customer or "CLI-USER",
        garment_type=GarmentType(args.garment),
        fit_type=FitType(args.fit),
        measurements=CustomerMeasurements(
            chest_cm=args.chest,
            waist_cm=args.waist,
            hip_cm=args.hip,
            shoulder_width_cm=args.shoulder,
            inseam_cm=args.inseam,
        ),
    )

    # Process
    result = api.process_order(order)

    # Output
    print("\n" + "=" * 60)
    if result.success:
        print(f"ORDER {result.order_id} - SUCCESS")
        print(f"  PLT file:    {result.plt_file}")
        print(f"  Fabric:      {result.fabric_length_cm:.1f} cm")
        print(f"  Utilization: {result.fabric_utilization:.1f}%")
        print(f"  Time:        {result.processing_time_ms:.0f}ms")
        if result.warnings:
            print(f"  Warnings:")
            for w in result.warnings:
                print(f"    - {w}")
    else:
        print(f"ORDER {result.order_id} - FAILED")
        for error in result.errors:
            print(f"  ERROR: {error}")
    print("=" * 60)

    return 0 if result.success else 1


def cmd_batch(args):
    """Process batch orders from JSON."""
    from samedaysuits_api import (
        SameDaySuitsAPI,
        Order,
        GarmentType,
        FitType,
        CustomerMeasurements,
    )

    api = SameDaySuitsAPI()

    # Load orders from JSON
    with open(args.file) as f:
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

    # Summary
    print("\n" + "=" * 60)
    print("BATCH PROCESSING COMPLETE")
    print("=" * 60)

    successful = sum(1 for r in results if r.success)
    total_fabric = sum(r.fabric_length_cm for r in results if r.success)

    for r in results:
        status = "OK" if r.success else "FAILED"
        print(f"  {r.order_id}: [{status}] {r.fabric_length_cm:.1f}cm")

    print("-" * 60)
    print(f"Success: {successful}/{len(results)}")
    print(f"Total fabric: {total_fabric:.1f} cm")
    print("=" * 60)

    return 0 if successful == len(results) else 1


def cmd_queue(args):
    """Manage cutter queue."""
    from cutter_queue import CutterQueue, JobPriority, JobStatus
    import time

    queue = CutterQueue()

    if args.action == "status":
        status = queue.get_status()
        print("\n" + "=" * 50)
        print("CUTTER QUEUE STATUS")
        print("=" * 50)
        print(f"Total jobs:    {status.total_jobs}")
        print(f"Pending:       {status.pending_jobs}")
        print(f"Cutting:       {status.cutting_jobs}")
        print(f"Complete:      {status.complete_jobs}")
        print(f"Errors:        {status.error_jobs}")
        print(f"Total fabric:  {status.total_fabric_cm:.1f} cm")
        print(f"Est. time:     {status.estimated_time_minutes:.1f} min")
        print("=" * 50)

    elif args.action == "list":
        jobs = queue.list_jobs()
        print("\n" + "=" * 80)
        print(f"{'Job ID':<30} {'Order':<15} {'Status':<10} {'Priority':<8}")
        print("-" * 80)
        for job in jobs:
            print(
                f"{job.job_id:<30} {job.order_id:<15} {job.status.value:<10} {job.priority.name:<8}"
            )
        print("=" * 80)
        print(f"Total: {len(jobs)} jobs")

    elif args.action == "watch":
        print("Starting watch mode (Ctrl+C to stop)...")
        queue.start_watching()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nStopping...")
            queue.stop_watching()

    elif args.action == "process":
        job = queue.get_next_job()
        if job:
            print(f"Processing: {job.job_id}")
            spool_file = queue.copy_to_spool(job.job_id)
            if spool_file:
                queue.mark_cutting(job.job_id)
                queue.mark_complete(job.job_id)
                print(f"Complete: {job.job_id}")
        else:
            print("No jobs in queue")

    return 0


def cmd_templates(args):
    """List available templates."""
    from samedaysuits_api import SameDaySuitsAPI

    api = SameDaySuitsAPI()
    templates = api.list_available_templates()

    print("\n" + "=" * 40)
    print("AVAILABLE TEMPLATES")
    print("=" * 40)
    for garment, available in templates.items():
        status = "OK" if available else "MISSING"
        print(f"  {garment:12} [{status}]")
    print("=" * 40)

    return 0


def cmd_sizes(args):
    """Show graded size information."""
    from graded_size_extractor import extract_graded_info, print_graded_info
    from samedaysuits_api import TEMPLATE_MAPPING, GarmentType

    # Get template path
    garment_type = GarmentType(args.template)
    if garment_type not in TEMPLATE_MAPPING:
        print(f"Unknown template: {args.template}")
        return 1

    template_file = TEMPLATE_MAPPING[garment_type]
    template_path = project_root / "DS-speciale" / "inputs" / "pds" / template_file

    if not template_path.exists():
        print(f"Template not found: {template_path}")
        return 1

    pattern = extract_graded_info(template_path)
    print_graded_info(pattern)

    return 0


def cmd_db(args):
    """Database operations."""
    from database_integration import (
        OrderDatabase,
        OrderSyncService,
        create_test_order,
        SCHEMA_SQL,
    )
    import time

    if args.action == "schema":
        print("\n" + "=" * 60)
        print("SUPABASE SCHEMA SQL")
        print("=" * 60)
        print("Run this in your Supabase SQL editor:\n")
        print(SCHEMA_SQL)
        return 0

    # Initialize database
    try:
        db = OrderDatabase()
    except Exception as e:
        print(f"Error connecting to database: {e}")
        print("\nMake sure Supabase is running and environment variables are set:")
        print("  SUPABASE_URL=http://localhost:54321")
        print("  SUPABASE_KEY=<your-anon-key>")
        return 1

    if args.action == "status":
        print("\n" + "=" * 50)
        print("DATABASE STATUS")
        print("=" * 50)
        print(f"URL:       {db.config.url}")
        print(f"Mode:      {'Local' if db.config.is_local else 'Cloud'}")
        print(f"Connected: {db.is_connected}")

        if db.is_connected:
            pending = db.get_pending_orders(limit=1000)
            print(f"Pending:   {len(pending)} orders")
        print("=" * 50)

    elif args.action == "sync":
        sync = OrderSyncService(db=db)
        stats = sync.run_once()

        print("\n" + "=" * 50)
        print("SYNC COMPLETE")
        print("=" * 50)
        print(f"Processed: {stats['processed']}")
        print(f"Succeeded: {stats['succeeded']}")
        print(f"Failed:    {stats['failed']}")
        print("=" * 50)

    elif args.action == "watch":
        print(f"\nStarting watch mode (interval: {args.interval}s)")
        print("Press Ctrl+C to stop\n")

        sync = OrderSyncService(db=db)

        try:
            sync.run_loop(interval_seconds=args.interval)
        except KeyboardInterrupt:
            print("\nStopping...")
            sync.stop()

    elif args.action == "test-order":
        order_id = create_test_order(db)
        if order_id:
            print(f"\nCreated test order: {order_id}")
            print("Run 'sds db sync' to process it")
        else:
            print("\nFailed to create test order")
            print("Run 'sds db schema' to see the required table SQL")

    return 0


def cmd_serve(args):
    """Start web API server."""
    import uvicorn

    print("\n" + "=" * 60)
    print("SameDaySuits Production API")
    print("=" * 60)
    print(f"Dashboard: http://localhost:{args.port}")
    print(f"API Docs:  http://localhost:{args.port}/docs")
    print("=" * 60 + "\n")

    uvicorn.run(
        "web_api:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )
    return 0


def cmd_test(args):
    """Run pipeline test."""
    print("Running pipeline test...")
    print("=" * 60)

    # Test each major component
    tests_passed = 0
    tests_total = 0

    # Test 1: Template listing
    tests_total += 1
    try:
        from samedaysuits_api import SameDaySuitsAPI

        api = SameDaySuitsAPI()
        templates = api.list_available_templates()
        available = sum(1 for v in templates.values() if v)
        print(f"[PASS] Templates: {available} available")
        tests_passed += 1
    except Exception as e:
        print(f"[FAIL] Templates: {e}")

    # Test 2: Graded sizes
    tests_total += 1
    try:
        from graded_size_extractor import extract_graded_info

        pattern = extract_graded_info(
            project_root / "DS-speciale/inputs/pds/Basic Tee_2D.PDS"
        )
        print(
            f"[PASS] Graded sizes: {len(pattern.available_sizes)} sizes, {len(pattern.pieces)} pieces"
        )
        tests_passed += 1
    except Exception as e:
        print(f"[FAIL] Graded sizes: {e}")

    # Test 3: Pattern scaling
    tests_total += 1
    try:
        from pattern_scaler import (
            calculate_pattern_scale,
            GarmentType as ScalerGarmentType,
        )

        result = calculate_pattern_scale(
            {"chest": 100, "waist": 85, "hip": 100}, ScalerGarmentType.TOP
        )
        print(
            f"[PASS] Pattern scaling: base={result.base_size}, scale_x={result.scale_x:.3f}"
        )
        tests_passed += 1
    except Exception as e:
        print(f"[FAIL] Pattern scaling: {e}")

    # Test 4: Nesting
    tests_total += 1
    try:
        from nesting_engine import nest_bottom_left_fill, Point

        test_pieces = [[Point(0, 0), Point(50, 0), Point(50, 50), Point(0, 50)]]
        result = nest_bottom_left_fill(test_pieces)
        print(f"[PASS] Nesting: {result.message}")
        tests_passed += 1
    except Exception as e:
        print(f"[FAIL] Nesting: {e}")

    # Test 5: Queue
    tests_total += 1
    try:
        from cutter_queue import CutterQueue

        queue = CutterQueue()
        status = queue.get_status()
        print(f"[PASS] Queue: {status.total_jobs} jobs")
        tests_passed += 1
    except Exception as e:
        print(f"[FAIL] Queue: {e}")

    print("=" * 60)
    print(f"Tests: {tests_passed}/{tests_total} passed")

    return 0 if tests_passed == tests_total else 1


def cmd_monitor(args):
    """Handle monitor command."""
    try:
        from production_monitor import get_monitor

        monitor = get_monitor()

        if args.action == "status":
            # Show quick status
            stats = monitor.get_production_stats(24)
            print("=" * 60)
            print("Production Status (Last 24 Hours)")
            print("=" * 60)
            print(
                f"Orders: {stats.orders_total} total ({stats.orders_success} success, {stats.orders_failed} failed)"
            )
            if stats.orders_total > 0:
                success_rate = (stats.orders_success / stats.orders_total) * 100
                print(f"Success Rate: {success_rate:.1f}%")
            print(f"Avg Utilization: {stats.avg_utilization:.1f}%")
            print(f"Fabric Used: {stats.total_fabric_cm / 100:.1f} meters")
            print("=" * 60)

        elif args.action == "dashboard":
            # Show full dashboard
            data = monitor.get_dashboard_data()

            print("=" * 60)
            print("Production Dashboard")
            print("=" * 60)

            # Health
            health = data["health"]
            print(f"\nSystem Health: {'HEALTHY' if health['healthy'] else 'UNHEALTHY'}")
            for name, check in health["checks"].items():
                status = "OK" if check["healthy"] else "FAIL"
                print(f"  [{status}] {name}: {check['message']}")

            # Stats
            stats = data["stats_24h"]
            print(f"\n24-Hour Statistics:")
            print(
                f"  Orders: {stats['orders_total']} total ({stats['orders_success']} success, {stats['orders_failed']} failed)"
            )
            if stats["orders_total"] > 0:
                success_rate = (stats["orders_success"] / stats["orders_total"]) * 100
                print(f"  Success Rate: {success_rate:.1f}%")
            print(f"  Avg Utilization: {stats['avg_utilization']:.1f}%")
            print(f"  Total Fabric: {stats['total_fabric_cm'] / 100:.1f} meters")

            # Queue
            queue = data["queue"]
            print(f"\nQueue Status:")
            print(f"  Pending: {int(queue['pending'])}")
            print(f"  Processing: {int(queue['processing'])}")
            print(f"  Completed: {int(queue['completed'])}")

            # Alerts
            alerts = data["alerts"]
            print(f"\nActive Alerts: {len(alerts)}")
            for alert in alerts:
                print(f"  [{alert['severity']}] {alert['title']}: {alert['message']}")

            # Recent orders
            print(f"\nRecent Orders:")
            for order in data["recent_orders"][-5:]:
                status = "OK" if order["success"] else "FAIL"
                print(
                    f"  {order['order_id']}: {order['garment_type']} [{status}] {order['nesting_utilization']:.1f}%"
                )

            print("\n" + "=" * 60)

        elif args.action == "alerts":
            # Show active alerts
            alerts = monitor.get_active_alerts()
            if not alerts:
                print("No active alerts")
                return 0

            print("=" * 60)
            print("Active Alerts")
            print("=" * 60)
            for alert in alerts:
                print(f"\n[{alert.severity}] {alert.title}")
                print(f"  ID: {alert.id}")
                print(f"  Message: {alert.message}")
                print(
                    f"  Value: {alert.metric_value:.2f} (threshold: {alert.threshold})"
                )
                print(f"  Time: {alert.timestamp}")
                if alert.acknowledged:
                    print(f"  Status: Acknowledged")
            print("\n" + "=" * 60)

        elif args.action == "health":
            # Show health check
            health = monitor.health_check()
            print("=" * 60)
            print("System Health Check")
            print("=" * 60)
            print(f"Overall: {'HEALTHY' if health['healthy'] else 'UNHEALTHY'}")
            print(f"Timestamp: {health['timestamp']}")
            print("\nChecks:")
            for name, check in health["checks"].items():
                status = "OK" if check["healthy"] else "FAIL"
                print(f"  [{status}] {name}: {check['message']}")
            print("=" * 60)

    except ImportError:
        print("Error: Production monitoring system not available")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        return 1

    return 0


def cmd_qc(args):
    """Handle QC command."""
    from pathlib import Path
    import json

    try:
        if args.action == "report":
            if not args.order:
                print("Error: --order required for report action")
                return 1

            # Find QC report file
            orders_dir = Path("DS-speciale/out/orders")
            qc_file = orders_dir / args.order / f"{args.order}_qc_report.json"

            if not qc_file.exists():
                print(f"Error: QC report not found for order {args.order}")
                print(f"Expected: {qc_file}")
                return 1

            # Load and display report
            with open(qc_file) as f:
                report = json.load(f)

            print("=" * 70)
            print(f"QC REPORT - Order {report['order_id']}")
            print(f"Garment Type: {report['garment_type']}")
            print("=" * 70)

            status = "PASSED" if report["passed"] else "FAILED"
            print(f"\nOverall Status: {status}")
            print(f"  Errors:   {report['error_count']}")
            print(f"  Warnings: {report['warning_count']}")
            print(f"  Info:     {report['info_count']}")

            if report["checks"]:
                # Group by level
                errors = [c for c in report["checks"] if c["level"] == "error"]
                warnings = [c for c in report["checks"] if c["level"] == "warning"]
                infos = [c for c in report["checks"] if c["level"] == "info"]

                if errors:
                    print("\n[ERRORS] (Must Fix):")
                    for check in errors:
                        piece_info = (
                            f" [Piece {check['piece_id']}]"
                            if check["piece_id"] is not None
                            else ""
                        )
                        print(
                            f"  * [{check['category']}]{piece_info} {check['message']}"
                        )

                if warnings:
                    print("\n[WARNINGS] (Review Recommended):")
                    for check in warnings:
                        piece_info = (
                            f" [Piece {check['piece_id']}]"
                            if check["piece_id"] is not None
                            else ""
                        )
                        print(
                            f"  * [{check['category']}]{piece_info} {check['message']}"
                        )

                if infos:
                    print("\n[INFO]:")
                    for check in infos:
                        piece_info = (
                            f" [Piece {check['piece_id']}]"
                            if check["piece_id"] is not None
                            else ""
                        )
                        print(
                            f"  * [{check['category']}]{piece_info} {check['message']}"
                        )

            print("\n" + "=" * 70)

        elif args.action == "check":
            # Run QC validation on an order
            print("QC validation runs automatically during order processing.")
            print("Use 'sds qc report --order <ID>' to view results.")

        elif args.action == "list":
            # List orders with QC reports
            orders_dir = Path("DS-speciale/out/orders")
            if not orders_dir.exists():
                print("No orders directory found")
                return 0

            qc_reports = list(orders_dir.glob("*/*_qc_report.json"))

            if not qc_reports:
                print("No QC reports found")
                return 0

            print("=" * 70)
            print("QC REPORTS")
            print("=" * 70)

            for qc_file in sorted(qc_reports):
                try:
                    with open(qc_file) as f:
                        report = json.load(f)

                    status = "PASS" if report["passed"] else "FAIL"
                    errors = report["error_count"]
                    warnings = report["warning_count"]

                    print(
                        f"{report['order_id']:20s} [{status}] {errors}E/{warnings}W - {report['garment_type']}"
                    )
                except:
                    pass

            print("=" * 70)

    except Exception as e:
        print(f"Error: {e}")
        return 1

    return 0


def cmd_scan(args):
    """Handle scan command for TheBlackbox integration."""
    try:
        from theblackbox_integration import TheBlackboxIntegration

        blackbox = TheBlackboxIntegration()

        if args.action == "process":
            if not args.file:
                print("Error: --file required for process action")
                return 1
            if not args.garment:
                print("Error: --garment required for process action")
                return 1

            # Check if file exists
            scan_path = Path(args.file)
            if not scan_path.exists():
                # Try looking in scans directory
                scan_path = Path("sample_scans") / args.file
                if not scan_path.exists():
                    print(f"Error: Scan file not found: {args.file}")
                    return 1

            print(f"Processing scan: {scan_path}")
            print(f"Garment type: {args.garment}")
            print(f"Fit type: {args.fit}")
            print("-" * 60)

            # Process the scan
            order, validation = blackbox.process_scan_file(
                scan_file=str(scan_path),
                garment_type=args.garment,
                fit_type=args.fit,
            )

            if order:
                print(f"\n[OK] Scan processed successfully!")
                print(f"  Order ID: {order['order_id']}")
                print(f"  Customer: {order['customer_id']}")
                print(f"  Measurements:")
                for key, value in order["measurements"].items():
                    if value:
                        print(f"    {key}: {value}cm")
                print(f"  Confidence: {order['confidence']:.0%}")
                print(f"  Quality: {order['scan_quality']}")

                # Save order to file for processing
                orders_dir = Path("DS-speciale/out/orders")
                orders_dir.mkdir(parents=True, exist_ok=True)
                order_file = orders_dir / f"{order['order_id']}_from_scan.json"
                with open(order_file, "w") as f:
                    json.dump(order, f, indent=2)
                print(f"\n  Order saved to: {order_file}")

                # Ask if user wants to process immediately
                print("\n  Process this order now? (y/n): ", end="", flush=True)
                try:
                    response = input().strip().lower()
                    if response in ("y", "yes"):
                        print("\n  Processing order through production pipeline...")
                        # Create Order object and process
                        from samedaysuits_api import (
                            SameDaySuitsAPI,
                            Order,
                            CustomerMeasurements,
                            GarmentType,
                            FitType,
                        )

                        api = SameDaySuitsAPI()

                        # Create order
                        order_obj = Order(
                            order_id=order["order_id"],
                            customer_id=order["customer_id"],
                            garment_type=GarmentType(order["garment_type"]),
                            fit_type=FitType(order["fit_type"]),
                            measurements=CustomerMeasurements(
                                chest_cm=order["measurements"]["chest_cm"],
                                waist_cm=order["measurements"]["waist_cm"],
                                hip_cm=order["measurements"]["hip_cm"],
                                shoulder_width_cm=order["measurements"].get(
                                    "shoulder_width_cm"
                                ),
                                arm_length_cm=order["measurements"].get(
                                    "arm_length_cm"
                                ),
                                inseam_cm=order["measurements"].get("inseam_cm"),
                                neck_cm=order["measurements"].get("neck_cm"),
                                source="theblackbox",
                            ),
                        )

                        result = api.process_order(order_obj)

                        if result.success:
                            print(f"\n  [SUCCESS] Order processed successfully!")
                            print(f"    PLT file: {result.plt_file}")
                            print(f"    Fabric: {result.fabric_length_cm:.1f} cm")
                            print(f"    Utilization: {result.fabric_utilization:.1f}%")
                        else:
                            print(f"\n  [FAILED] Order processing failed:")
                            for error in result.errors:
                                print(f"    - {error}")
                except EOFError:
                    # Non-interactive mode, skip processing
                    pass
                except Exception as e:
                    print(f"\n  Error processing order: {e}")

                return 0
            else:
                print(f"\n[FAILED] Scan validation failed:")
                for error in validation.errors:
                    print(f"  ERROR: {error}")
                for warning in validation.warnings:
                    print(f"  WARNING: {warning}")
                return 1

        elif args.action == "validate":
            if not args.file:
                print("Error: --file required for validate action")
                return 1

            scan_path = Path(args.file)
            if not scan_path.exists():
                scan_path = Path("sample_scans") / args.file
                if not scan_path.exists():
                    print(f"Error: Scan file not found: {args.file}")
                    return 1

            print(f"Validating scan: {scan_path}")
            print("-" * 60)

            scan_data = blackbox.load_scan(str(scan_path))
            if not scan_data:
                print("Error: Failed to load scan file")
                return 1

            validation = blackbox.validate_scan(scan_data)

            print(f"Scan ID: {scan_data.scan_id}")
            print(f"Customer: {scan_data.customer_id}")
            print(f"Quality: {scan_data.quality.value}")
            print(f"Confidence: {scan_data.measurements.confidence:.0%}")
            print(f"\nValidation: {'PASSED' if validation.valid else 'FAILED'}")
            print(f"Quality Score: {validation.quality_score:.0%}")

            if validation.errors:
                print(f"\nErrors ({len(validation.errors)}):")
                for error in validation.errors:
                    print(f"  • {error}")

            if validation.warnings:
                print(f"\nWarnings ({len(validation.warnings)}):")
                for warning in validation.warnings:
                    print(f"  • {warning}")

            return 0 if validation.valid else 1

        elif args.action == "list":
            scans_dir = Path("sample_scans")
            if not scans_dir.exists():
                print("No scans directory found")
                return 0

            scan_files = list(scans_dir.glob("*.json"))

            if not scan_files:
                print("No scan files found")
                return 0

            print("=" * 70)
            print("AVAILABLE SCANS")
            print("=" * 70)

            for scan_file in sorted(scan_files):
                try:
                    scan_data = blackbox.load_scan(str(scan_file))
                    if scan_data:
                        print(f"\n{scan_file.name}")
                        print(f"  ID: {scan_data.scan_id}")
                        print(f"  Customer: {scan_data.customer_id}")
                        print(f"  Chest: {scan_data.measurements.chest_cm}cm")
                        print(f"  Waist: {scan_data.measurements.waist_cm}cm")
                        print(f"  Hip: {scan_data.measurements.hip_cm}cm")
                        print(f"  Quality: {scan_data.quality.value}")
                except:
                    pass

            print("\n" + "=" * 70)
            return 0

        elif args.action == "generate":
            # Generate a sample scan for testing
            customer_id = args.customer or "SAMPLE"
            chest = args.chest or 102.0
            waist = args.waist or 88.0
            hip = args.hip or 100.0

            print("Generating sample scan...")
            print(f"  Customer: {customer_id}")
            print(f"  Chest: {chest}cm")
            print(f"  Waist: {waist}cm")
            print(f"  Hip: {hip}cm")

            scan_file = blackbox.generate_sample_scan(
                customer_id=customer_id,
                chest=chest,
                waist=waist,
                hip=hip,
            )

            print(f"\n[OK] Sample scan created: {scan_file}")
            return 0

    except ImportError as e:
        print(f"Error: TheBlackbox integration not available - {e}")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()
        return 1


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        prog="sds",
        description="SameDaySuits Production CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  sds order --id ORD-001 --garment tee --chest 102 --waist 88 --hip 100
  sds batch orders.json
  sds queue status
  sds templates
  sds sizes --template tee
  sds test
  sds monitor status
  sds monitor dashboard
  sds qc report --order ORD-001
  sds scan process --file scan.json --garment jacket --fit regular
  sds scan validate --file scan.json
  sds scan generate --customer CUST-001 --chest 102 --waist 88 --hip 100
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Order command
    order_parser = subparsers.add_parser("order", help="Process a single order")
    order_parser.add_argument("--id", required=True, help="Order ID")
    order_parser.add_argument("--customer", help="Customer ID")
    order_parser.add_argument(
        "--garment",
        required=True,
        choices=["tee", "jacket", "trousers", "cargo"],
        help="Garment type",
    )
    order_parser.add_argument(
        "--fit",
        choices=["slim", "regular", "classic"],
        default="regular",
        help="Fit type",
    )
    order_parser.add_argument("--chest", type=float, required=True, help="Chest (cm)")
    order_parser.add_argument("--waist", type=float, required=True, help="Waist (cm)")
    order_parser.add_argument("--hip", type=float, required=True, help="Hip (cm)")
    order_parser.add_argument("--shoulder", type=float, help="Shoulder width (cm)")
    order_parser.add_argument("--inseam", type=float, help="Inseam (cm)")
    order_parser.set_defaults(func=cmd_order)

    # Batch command
    batch_parser = subparsers.add_parser("batch", help="Process batch orders")
    batch_parser.add_argument("file", type=Path, help="JSON file with orders")
    batch_parser.set_defaults(func=cmd_batch)

    # Queue command
    queue_parser = subparsers.add_parser("queue", help="Manage cutter queue")
    queue_parser.add_argument(
        "action", choices=["status", "list", "watch", "process"], help="Queue action"
    )
    queue_parser.set_defaults(func=cmd_queue)

    # Templates command
    templates_parser = subparsers.add_parser("templates", help="List templates")
    templates_parser.set_defaults(func=cmd_templates)

    # Sizes command
    sizes_parser = subparsers.add_parser("sizes", help="Show graded sizes")
    sizes_parser.add_argument(
        "--template",
        required=True,
        choices=["tee", "jacket", "trousers", "cargo"],
        help="Template to show",
    )
    sizes_parser.set_defaults(func=cmd_sizes)

    # Test command
    test_parser = subparsers.add_parser("test", help="Run pipeline test")
    test_parser.set_defaults(func=cmd_test)

    # Database command
    db_parser = subparsers.add_parser("db", help="Database operations")
    db_parser.add_argument(
        "action",
        choices=["status", "sync", "watch", "test-order", "schema"],
        help="Database action",
    )
    db_parser.add_argument(
        "--interval",
        type=float,
        default=30.0,
        help="Sync interval in seconds (for watch)",
    )
    db_parser.set_defaults(func=cmd_db)

    # Serve command
    serve_parser = subparsers.add_parser("serve", help="Start web API server")
    serve_parser.add_argument("--host", default="0.0.0.0", help="Host to bind")
    serve_parser.add_argument("--port", type=int, default=8000, help="Port to bind")
    serve_parser.add_argument("--reload", action="store_true", help="Enable hot reload")
    serve_parser.set_defaults(func=cmd_serve)

    # Monitor command
    monitor_parser = subparsers.add_parser("monitor", help="Production monitoring")
    monitor_parser.add_argument(
        "action",
        choices=["status", "dashboard", "alerts", "health"],
        help="Monitoring action",
    )
    monitor_parser.set_defaults(func=cmd_monitor)

    # QC command
    qc_parser = subparsers.add_parser("qc", help="Quality control operations")
    qc_parser.add_argument(
        "action",
        choices=["report", "check", "list"],
        help="QC action",
    )
    qc_parser.add_argument("--order", help="Order ID to check")
    qc_parser.set_defaults(func=cmd_qc)

    # Scan command (TheBlackbox integration)
    scan_parser = subparsers.add_parser(
        "scan", help="Process body scans from TheBlackbox"
    )
    scan_parser.add_argument(
        "action",
        choices=["process", "validate", "list", "generate"],
        help="Scan action",
    )
    scan_parser.add_argument("--file", "-f", help="Scan JSON file to process")
    scan_parser.add_argument(
        "--garment",
        "-g",
        choices=["tee", "jacket", "trousers", "cargo"],
        help="Garment type for order creation",
    )
    scan_parser.add_argument(
        "--fit",
        choices=["slim", "regular", "classic"],
        default="regular",
        help="Fit type",
    )
    scan_parser.add_argument(
        "--customer", "-c", help="Customer ID for sample generation"
    )
    scan_parser.add_argument("--chest", type=float, help="Chest measurement for sample")
    scan_parser.add_argument("--waist", type=float, help="Waist measurement for sample")
    scan_parser.add_argument("--hip", type=float, help="Hip measurement for sample")
    scan_parser.set_defaults(func=cmd_scan)

    # Parse and execute
    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return 0

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
