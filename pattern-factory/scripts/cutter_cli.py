#!/usr/bin/env python3
"""
Cutter Queue CLI - Command Line Interface for Resilient Cutter Queue

Simple CLI wrapper for queue management operations including:
- Viewing queue status
- Requesting job reprints
- Searching archived jobs
- Testing cutter connection

Usage:
    python scripts/cutter_cli.py status
    python scripts/cutter_cli.py reprint-job --job-id JOB-xxx
    python scripts/cutter_cli.py search --order-id ORD-001
    python scripts/cutter_cli.py test-cutter --ip 192.168.1.100

Author: Claude
Date: 2026-02-01
"""

import os
import sys
import argparse
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "core"))

from core.resilient_cutter_queue import (
    ResilientCutterQueue,
    JobPriority,
    JobStatus,
)


def format_time(iso_str: str) -> str:
    """Format ISO timestamp for display."""
    if not iso_str:
        return "-"
    try:
        dt = datetime.fromisoformat(iso_str)
        return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return iso_str[:16]


def cmd_status(args):
    """Show queue status."""
    queue = ResilientCutterQueue(Path(args.data_dir))
    status = queue.get_status()

    print()
    print("=" * 60)
    print("  JINDEX CUTTER QUEUE STATUS")
    print("=" * 60)
    print(f"  Queue depth:        {status['queue_depth']:>8}")
    print(f"  Active jobs:        {status['active_jobs']:>8}")
    print(f"  Total fabric:       {status['total_fabric_cm']:>8.1f} cm")
    print(f"  Estimated time:     {status['estimated_time_min']:>8.1f} min")
    print()
    print("  Status breakdown:")
    for s, count in status["status_breakdown"].items():
        if count > 0:
            print(f"    {s:<15} {count:>5}")
    print("=" * 60)
    print()


def cmd_list(args):
    """List jobs in queue."""
    queue = ResilientCutterQueue(Path(args.data_dir))
    jobs = queue.list_queue()

    if not jobs:
        print("\nQueue is empty.\n")
        return

    print()
    print(f"{'Job ID':<45} {'Order':<15} {'Pri':<8} {'Status':<10}")
    print("-" * 80)
    for job in jobs:
        reprint_marker = "[R]" if job.is_reprint else "   "
        print(
            f"{reprint_marker}{job.job_id:<42} {job.order_id:<15} "
            f"{job.priority.name:<8} {job.status.value:<10}"
        )
    print()


def cmd_reprint_job(args):
    """Reprint a job."""
    if not args.job_id:
        print("Error: --job-id required")
        sys.exit(1)

    queue = ResilientCutterQueue(Path(args.data_dir))

    # Map priority string to enum
    priority_map = {
        "rush": JobPriority.RUSH,
        "high": JobPriority.HIGH,
        "normal": JobPriority.NORMAL,
        "low": JobPriority.LOW,
    }
    priority = priority_map.get(args.priority, JobPriority.NORMAL)

    job = queue.reprint_job(
        args.job_id,
        reason=args.reason,
        requested_by=args.requested_by,
        priority=priority,
    )

    if job:
        print(f"\nReprint job created: {job.job_id}")
        print(f"  Original job: {args.job_id}")
        print(f"  Priority: {priority.name}")
        print(f"  Reason: {args.reason}")
        print()
    else:
        print(f"\nError: Could not create reprint for job {args.job_id}")
        print("Check that the job exists in the archive and has a valid PLT file.")
        sys.exit(1)


def cmd_reprint_order(args):
    """Reprint all jobs for an order."""
    if not args.order_id:
        print("Error: --order-id required")
        sys.exit(1)

    queue = ResilientCutterQueue(Path(args.data_dir))

    jobs = queue.reprint_order(
        args.order_id,
        reason=args.reason,
        requested_by=args.requested_by,
    )

    if jobs:
        print(f"\nCreated {len(jobs)} reprint jobs for order {args.order_id}:")
        for job in jobs:
            print(f"  {job.job_id}")
        print()
    else:
        print(f"\nNo completed jobs found for order {args.order_id}")
        sys.exit(1)


def cmd_search(args):
    """Search archived jobs."""
    queue = ResilientCutterQueue(Path(args.data_dir))

    # Parse status if provided
    status = None
    if args.status:
        try:
            status = JobStatus(args.status)
        except ValueError:
            print(f"Invalid status: {args.status}")
            print(f"Valid values: {[s.value for s in JobStatus]}")
            sys.exit(1)

    jobs = queue.archive.search_jobs(
        order_id=args.order_id,
        status=status,
        start_date=args.start_date,
        end_date=args.end_date,
        limit=args.limit,
    )

    if not jobs:
        print("\nNo jobs found matching criteria.\n")
        return

    print(f"\nFound {len(jobs)} jobs:")
    print()
    print(f"{'Job ID':<45} {'Order':<15} {'Status':<10} {'Created':<16}")
    print("-" * 90)
    for job in jobs:
        reprint_marker = "[R]" if job.is_reprint else "   "
        print(
            f"{reprint_marker}{job.job_id:<42} {job.order_id:<15} "
            f"{job.status.value:<10} {format_time(job.created_at):<16}"
        )
    print()


def cmd_job_info(args):
    """Show detailed job information."""
    if not args.job_id:
        print("Error: --job-id required")
        sys.exit(1)

    queue = ResilientCutterQueue(Path(args.data_dir))
    job = queue.get_job(args.job_id)

    if not job:
        print(f"\nJob {args.job_id} not found.\n")
        sys.exit(1)

    print()
    print("=" * 60)
    print(f"  JOB: {job.job_id}")
    print("=" * 60)
    print(f"  Order ID:       {job.order_id}")
    print(f"  Status:         {job.status.value}")
    print(f"  Priority:       {job.priority.name}")
    print(f"  Is Reprint:     {'Yes' if job.is_reprint else 'No'}")
    if job.original_job_id:
        print(f"  Original Job:   {job.original_job_id}")
    print(f"  Piece Count:    {job.piece_count}")
    print(f"  Fabric Length:  {job.fabric_length_cm:.1f} cm")
    print(f"  PLT File:       {job.plt_file}")
    print()
    print(f"  Created:        {format_time(job.created_at)}")
    print(f"  Queued:         {format_time(job.queued_at)}")
    print(f"  Started:        {format_time(job.started_at)}")
    print(f"  Completed:      {format_time(job.completed_at)}")
    if job.error_message:
        print(f"  Error:          {job.error_message}")
    print(f"  Retry Count:    {job.retry_count}/{job.max_retries}")
    print(
        f"  Checksum:       {job.checksum_sha256[:16]}..."
        if job.checksum_sha256
        else "  Checksum:       -"
    )
    print("=" * 60)
    print()


def cmd_test_cutter(args):
    """Test connection to Jindex cutter."""
    from workers.jindex_cutter import JindexCutter

    ip = args.ip or os.getenv("JINDEX_IP", "192.168.1.100")
    port = args.port or int(os.getenv("JINDEX_PORT", "9100"))

    print(f"\nTesting connection to Jindex cutter at {ip}:{port}...")

    cutter = JindexCutter(ip, port)

    if cutter.test_connection():
        print(f"SUCCESS: Cutter is reachable at {ip}:{port}")
    else:
        print(f"FAILED: Cannot connect to cutter at {ip}:{port}")
        print("Check that:")
        print("  - The cutter is powered on")
        print("  - The IP address is correct")
        print("  - Network connectivity exists")
        sys.exit(1)
    print()


def cmd_checkpoint(args):
    """Create WAL checkpoint to clean up old entries."""
    queue = ResilientCutterQueue(Path(args.data_dir))
    queue.checkpoint()
    print("\nWAL checkpoint complete.\n")


def main():
    parser = argparse.ArgumentParser(
        description="Jindex Cutter Queue CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s status                           Show queue status
  %(prog)s list                             List queued jobs
  %(prog)s info --job-id JOB-xxx            Show job details
  %(prog)s reprint-job --job-id JOB-xxx     Reprint a job
  %(prog)s reprint-order --order-id ORD-001 Reprint all jobs for order
  %(prog)s search --order-id ORD-001        Search archived jobs
  %(prog)s test-cutter --ip 192.168.1.100   Test cutter connection
        """,
    )

    parser.add_argument(
        "--data-dir",
        default=os.getenv("CUTTER_DATA_DIR", "./cutter_data"),
        help="Data directory for queue (default: ./cutter_data)",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # status
    subparsers.add_parser("status", help="Show queue status")

    # list
    subparsers.add_parser("list", help="List jobs in queue")

    # info
    info_parser = subparsers.add_parser("info", help="Show job details")
    info_parser.add_argument("--job-id", required=True, help="Job ID")

    # reprint-job
    reprint_parser = subparsers.add_parser("reprint-job", help="Reprint a job")
    reprint_parser.add_argument("--job-id", required=True, help="Job ID to reprint")
    reprint_parser.add_argument(
        "--priority",
        choices=["rush", "high", "normal", "low"],
        default="normal",
        help="Priority for reprint (default: normal)",
    )
    reprint_parser.add_argument(
        "--reason", default="Manual reprint request", help="Reason for reprint"
    )
    reprint_parser.add_argument(
        "--requested-by", default="operator", help="Who requested the reprint"
    )

    # reprint-order
    reprint_order_parser = subparsers.add_parser(
        "reprint-order", help="Reprint all jobs for order"
    )
    reprint_order_parser.add_argument("--order-id", required=True, help="Order ID")
    reprint_order_parser.add_argument(
        "--reason", default="Order reprint request", help="Reason for reprint"
    )
    reprint_order_parser.add_argument(
        "--requested-by", default="operator", help="Who requested the reprint"
    )

    # search
    search_parser = subparsers.add_parser("search", help="Search archived jobs")
    search_parser.add_argument("--order-id", help="Filter by order ID")
    search_parser.add_argument(
        "--status", choices=[s.value for s in JobStatus], help="Filter by status"
    )
    search_parser.add_argument("--start-date", help="Start date (ISO format)")
    search_parser.add_argument("--end-date", help="End date (ISO format)")
    search_parser.add_argument(
        "--limit", type=int, default=50, help="Max results (default: 50)"
    )

    # test-cutter
    test_parser = subparsers.add_parser("test-cutter", help="Test cutter connection")
    test_parser.add_argument("--ip", help="Cutter IP address")
    test_parser.add_argument("--port", type=int, help="Cutter port")

    # checkpoint
    subparsers.add_parser("checkpoint", help="Create WAL checkpoint")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Dispatch to command handler
    commands = {
        "status": cmd_status,
        "list": cmd_list,
        "info": cmd_job_info,
        "reprint-job": cmd_reprint_job,
        "reprint-order": cmd_reprint_order,
        "search": cmd_search,
        "test-cutter": cmd_test_cutter,
        "checkpoint": cmd_checkpoint,
    }

    handler = commands.get(args.command)
    if handler:
        handler(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
