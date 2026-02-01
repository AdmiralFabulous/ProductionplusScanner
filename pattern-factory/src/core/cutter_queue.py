#!/usr/bin/env python3
"""
Cutter Queue Manager: Watch folder and queue management for PLT files

This module provides:
1. Watch folder monitoring for new PLT files
2. Queue management with priority ordering
3. Status tracking for jobs
4. Optional integration with plotter/cutter devices

For production use, this would:
- Copy PLT files to the cutter's spool directory
- Track job status (pending, cutting, complete)
- Handle errors and retries
- Provide status API for UI

Author: Claude
Date: 2026-01-30
"""

import os
import sys
import json
import time
import shutil
import logging
from pathlib import Path
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
import threading
from queue import PriorityQueue

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class JobStatus(Enum):
    """Status of a cutting job."""

    PENDING = "pending"
    QUEUED = "queued"
    CUTTING = "cutting"
    COMPLETE = "complete"
    ERROR = "error"
    CANCELLED = "cancelled"


class JobPriority(Enum):
    """Priority levels for jobs."""

    RUSH = 1  # Same-day rush orders
    HIGH = 2  # Priority customers
    NORMAL = 3  # Standard orders
    LOW = 4  # Batch/bulk orders


@dataclass
class CutterJob:
    """A job in the cutter queue."""

    job_id: str
    order_id: str
    plt_file: Path
    priority: JobPriority = JobPriority.NORMAL
    status: JobStatus = JobStatus.PENDING
    fabric_length_cm: float = 0.0
    piece_count: int = 0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    queued_at: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error_message: Optional[str] = None

    def __lt__(self, other):
        """For priority queue ordering."""
        return self.priority.value < other.priority.value


@dataclass
class QueueStatus:
    """Current status of the cutter queue."""

    total_jobs: int
    pending_jobs: int
    cutting_jobs: int
    complete_jobs: int
    error_jobs: int
    total_fabric_cm: float
    estimated_time_minutes: float


class CutterQueue:
    """
    Manages the queue of jobs for the plotter/cutter.

    Example usage:
        queue = CutterQueue(
            watch_dir=Path("orders"),
            spool_dir=Path("cutter_spool"),
        )

        # Start watching for new PLT files
        queue.start_watching()

        # Or manually add jobs
        job = queue.add_job("ORD-001", Path("orders/ORD-001/ORD-001.plt"))

        # Get queue status
        status = queue.get_status()
        print(f"Jobs pending: {status.pending_jobs}")
    """

    def __init__(
        self,
        watch_dir: Optional[Path] = None,
        spool_dir: Optional[Path] = None,
        cutting_speed_cm_per_min: float = 100.0,  # Approximate cutting speed
    ):
        """
        Initialize the cutter queue.

        Args:
            watch_dir: Directory to watch for new PLT files
            spool_dir: Directory to copy PLT files for the cutter
            cutting_speed_cm_per_min: Estimated cutting speed for time estimates
        """
        project_root = Path(__file__).parent

        self.watch_dir = watch_dir or project_root / "DS-speciale" / "out" / "orders"
        self.spool_dir = (
            spool_dir or project_root / "DS-speciale" / "out" / "cutter_spool"
        )
        self.cutting_speed = cutting_speed_cm_per_min

        self.spool_dir.mkdir(parents=True, exist_ok=True)

        # Job storage
        self.jobs: Dict[str, CutterJob] = {}
        self.queue: PriorityQueue = PriorityQueue()

        # State file for persistence
        self.state_file = self.spool_dir / "queue_state.json"
        self._load_state()

        # Watching
        self._watching = False
        self._watch_thread: Optional[threading.Thread] = None

        logger.info(f"Cutter queue initialized")
        logger.info(f"Watch dir: {self.watch_dir}")
        logger.info(f"Spool dir: {self.spool_dir}")

    def add_job(
        self,
        order_id: str,
        plt_file: Path,
        priority: JobPriority = JobPriority.NORMAL,
        metadata: Optional[Dict] = None,
    ) -> CutterJob:
        """
        Add a job to the queue.

        Args:
            order_id: Order identifier
            plt_file: Path to PLT file
            priority: Job priority
            metadata: Optional metadata from order processing

        Returns:
            Created CutterJob
        """
        job_id = f"JOB-{order_id}-{int(time.time())}"

        # Extract info from metadata if available
        fabric_length = 0.0
        piece_count = 0

        if metadata:
            fabric_length = metadata.get("production", {}).get("fabric_length_cm", 0)
            piece_count = metadata.get("production", {}).get("piece_count", 0)

        job = CutterJob(
            job_id=job_id,
            order_id=order_id,
            plt_file=plt_file,
            priority=priority,
            fabric_length_cm=fabric_length,
            piece_count=piece_count,
        )

        self.jobs[job_id] = job
        self.queue.put((priority.value, job))
        job.status = JobStatus.QUEUED
        job.queued_at = datetime.now().isoformat()

        logger.info(f"Added job {job_id} to queue (priority: {priority.name})")

        self._save_state()

        return job

    def get_next_job(self) -> Optional[CutterJob]:
        """Get the next job from the queue."""
        if self.queue.empty():
            return None

        _, job = self.queue.get()
        return job

    def mark_cutting(self, job_id: str):
        """Mark a job as currently cutting."""
        if job_id in self.jobs:
            job = self.jobs[job_id]
            job.status = JobStatus.CUTTING
            job.started_at = datetime.now().isoformat()
            logger.info(f"Job {job_id} started cutting")
            self._save_state()

    def mark_complete(self, job_id: str):
        """Mark a job as complete."""
        if job_id in self.jobs:
            job = self.jobs[job_id]
            job.status = JobStatus.COMPLETE
            job.completed_at = datetime.now().isoformat()
            logger.info(f"Job {job_id} complete")
            self._save_state()

    def mark_error(self, job_id: str, error_message: str):
        """Mark a job as errored."""
        if job_id in self.jobs:
            job = self.jobs[job_id]
            job.status = JobStatus.ERROR
            job.error_message = error_message
            logger.error(f"Job {job_id} error: {error_message}")
            self._save_state()

    def get_status(self) -> QueueStatus:
        """Get current queue status."""
        pending = sum(1 for j in self.jobs.values() if j.status == JobStatus.PENDING)
        queued = sum(1 for j in self.jobs.values() if j.status == JobStatus.QUEUED)
        cutting = sum(1 for j in self.jobs.values() if j.status == JobStatus.CUTTING)
        complete = sum(1 for j in self.jobs.values() if j.status == JobStatus.COMPLETE)
        errors = sum(1 for j in self.jobs.values() if j.status == JobStatus.ERROR)

        # Calculate total fabric for pending/queued jobs
        total_fabric = sum(
            j.fabric_length_cm
            for j in self.jobs.values()
            if j.status in [JobStatus.PENDING, JobStatus.QUEUED]
        )

        # Estimate time
        estimated_time = (
            total_fabric / self.cutting_speed if self.cutting_speed > 0 else 0
        )

        return QueueStatus(
            total_jobs=len(self.jobs),
            pending_jobs=pending + queued,
            cutting_jobs=cutting,
            complete_jobs=complete,
            error_jobs=errors,
            total_fabric_cm=total_fabric,
            estimated_time_minutes=estimated_time,
        )

    def list_jobs(self, status_filter: Optional[JobStatus] = None) -> List[CutterJob]:
        """List jobs, optionally filtered by status."""
        jobs = list(self.jobs.values())

        if status_filter:
            jobs = [j for j in jobs if j.status == status_filter]

        # Sort by priority, then by creation time
        jobs.sort(key=lambda j: (j.priority.value, j.created_at))

        return jobs

    def copy_to_spool(self, job_id: str) -> Optional[Path]:
        """Copy a job's PLT file to the spool directory."""
        if job_id not in self.jobs:
            return None

        job = self.jobs[job_id]

        if not job.plt_file.exists():
            self.mark_error(job_id, f"PLT file not found: {job.plt_file}")
            return None

        # Copy to spool with job ID prefix
        spool_file = self.spool_dir / f"{job.job_id}.plt"
        shutil.copy(job.plt_file, spool_file)

        logger.info(f"Copied {job.plt_file} to {spool_file}")

        return spool_file

    def send_to_cutter(self, job_id: str) -> bool:
        """Send job to physical cutter"""
        job = self.get_job(job_id)
        if not job or not job.plt_file:
            return False

        try:
            # Get cutter configuration
            cutter_config = self._load_cutter_config()

            # Send file to cutter (example for Graphtec/HPGL cutters)
            if cutter_config.get("type") == "graphtec":
                return self._send_to_graphtec(job, cutter_config)
            elif cutter_config.get("type") == "zund":
                return self._send_to_zund(job, cutter_config)
            else:
                # Generic HPGL
                return self._send_generic_hpgl(job, cutter_config)

        except Exception as e:
            logger.error(f"Failed to send job {job_id} to cutter: {e}")
            return False

    def get_job(self, job_id: str) -> Optional[CutterJob]:
        """Get a job by ID"""
        return self.jobs.get(job_id)

    def _load_cutter_config(self) -> dict:
        """Load cutter configuration"""
        import yaml

        config_path = Path("config/cutter.yaml")
        if config_path.exists():
            with open(config_path, "r") as f:
                return yaml.safe_load(f)
        return {"type": "generic", "port": "COM1"}

    def _send_generic_hpgl(self, job: CutterJob, config: dict) -> bool:
        """Send HPGL file to generic cutter"""
        import serial

        try:
            # Open serial connection
            with serial.Serial(config.get("port", "COM1"), 9600, timeout=10) as ser:
                # Read PLT file
                with open(job.plt_file, "rb") as f:
                    data = f.read()

                # Send to cutter
                ser.write(data)
                return True
        except Exception as e:
            logger.error(f"Serial communication error: {e}")
            return False

    def verify_cut_complete(self, job_id: str) -> bool:
        """Verify that cutting completed successfully"""
        # This would check cutter status sensors
        # For now, assume success after timeout
        return True

    def start_watching(self, interval_seconds: float = 5.0):
        """Start watching the watch directory for new PLT files."""
        if self._watching:
            logger.warning("Already watching")
            return

        self._watching = True
        self._watch_thread = threading.Thread(
            target=self._watch_loop, args=(interval_seconds,), daemon=True
        )
        self._watch_thread.start()

        logger.info(f"Started watching {self.watch_dir}")

    def stop_watching(self):
        """Stop watching."""
        self._watching = False
        if self._watch_thread:
            self._watch_thread.join(timeout=10)
        logger.info("Stopped watching")

    def _watch_loop(self, interval: float):
        """Main watch loop."""
        seen_files = set()

        # Initialize with existing files
        for plt_file in self.watch_dir.rglob("*.plt"):
            seen_files.add(str(plt_file))

        logger.info(f"Watching for new PLT files (ignoring {len(seen_files)} existing)")

        while self._watching:
            try:
                for plt_file in self.watch_dir.rglob("*.plt"):
                    file_str = str(plt_file)

                    if file_str not in seen_files:
                        seen_files.add(file_str)

                        # Extract order ID from path (assumes orders/ORDER_ID/ORDER_ID.plt)
                        order_id = plt_file.stem

                        # Check for metadata
                        metadata_file = plt_file.parent / f"{order_id}_metadata.json"
                        metadata = None
                        if metadata_file.exists():
                            with open(metadata_file) as f:
                                metadata = json.load(f)

                        # Add to queue
                        self.add_job(order_id, plt_file, metadata=metadata)

            except Exception as e:
                logger.error(f"Watch error: {e}")

            time.sleep(interval)

    def _save_state(self):
        """Save queue state to file."""
        state = {
            "jobs": {
                jid: {
                    "job_id": j.job_id,
                    "order_id": j.order_id,
                    "plt_file": str(j.plt_file),
                    "priority": j.priority.value,
                    "status": j.status.value,
                    "fabric_length_cm": j.fabric_length_cm,
                    "piece_count": j.piece_count,
                    "created_at": j.created_at,
                    "queued_at": j.queued_at,
                    "started_at": j.started_at,
                    "completed_at": j.completed_at,
                    "error_message": j.error_message,
                }
                for jid, j in self.jobs.items()
            }
        }

        with open(self.state_file, "w") as f:
            json.dump(state, f, indent=2)

    def _load_state(self):
        """Load queue state from file."""
        if not self.state_file.exists():
            return

        try:
            with open(self.state_file) as f:
                state = json.load(f)

            for jid, jdata in state.get("jobs", {}).items():
                job = CutterJob(
                    job_id=jdata["job_id"],
                    order_id=jdata["order_id"],
                    plt_file=Path(jdata["plt_file"]),
                    priority=JobPriority(jdata["priority"]),
                    status=JobStatus(jdata["status"]),
                    fabric_length_cm=jdata.get("fabric_length_cm", 0),
                    piece_count=jdata.get("piece_count", 0),
                    created_at=jdata.get("created_at", ""),
                    queued_at=jdata.get("queued_at"),
                    started_at=jdata.get("started_at"),
                    completed_at=jdata.get("completed_at"),
                    error_message=jdata.get("error_message"),
                )
                self.jobs[jid] = job

                # Re-queue pending/queued jobs
                if job.status in [JobStatus.PENDING, JobStatus.QUEUED]:
                    self.queue.put((job.priority.value, job))

            logger.info(f"Loaded {len(self.jobs)} jobs from state file")

        except Exception as e:
            logger.error(f"Error loading state: {e}")


def main():
    """CLI for cutter queue management."""
    import argparse

    parser = argparse.ArgumentParser(description="Cutter Queue Manager")
    parser.add_argument(
        "command", choices=["status", "list", "watch", "add", "process"]
    )
    parser.add_argument("--order", help="Order ID for add command")
    parser.add_argument("--plt", type=Path, help="PLT file path for add command")
    parser.add_argument(
        "--priority", choices=["rush", "high", "normal", "low"], default="normal"
    )
    parser.add_argument(
        "--status-filter", choices=["pending", "queued", "cutting", "complete", "error"]
    )

    args = parser.parse_args()

    queue = CutterQueue()

    if args.command == "status":
        status = queue.get_status()
        print("\n" + "=" * 50)
        print("CUTTER QUEUE STATUS")
        print("=" * 50)
        print(f"Total jobs:      {status.total_jobs}")
        print(f"Pending:         {status.pending_jobs}")
        print(f"Cutting:         {status.cutting_jobs}")
        print(f"Complete:        {status.complete_jobs}")
        print(f"Errors:          {status.error_jobs}")
        print(f"Total fabric:    {status.total_fabric_cm:.1f} cm")
        print(f"Est. time:       {status.estimated_time_minutes:.1f} min")
        print("=" * 50)

    elif args.command == "list":
        status_filter = JobStatus(args.status_filter) if args.status_filter else None
        jobs = queue.list_jobs(status_filter)

        print("\n" + "=" * 80)
        print(
            f"{'Job ID':<25} {'Order':<15} {'Status':<10} {'Priority':<10} {'Fabric':<10}"
        )
        print("-" * 80)

        for job in jobs:
            print(
                f"{job.job_id:<25} {job.order_id:<15} {job.status.value:<10} {job.priority.name:<10} {job.fabric_length_cm:.1f} cm"
            )

        print("=" * 80)
        print(f"Total: {len(jobs)} jobs")

    elif args.command == "add":
        if not args.order or not args.plt:
            parser.error("--order and --plt required for add command")

        priority_map = {
            "rush": JobPriority.RUSH,
            "high": JobPriority.HIGH,
            "normal": JobPriority.NORMAL,
            "low": JobPriority.LOW,
        }

        job = queue.add_job(args.order, args.plt, priority_map[args.priority])
        print(f"Added job: {job.job_id}")

    elif args.command == "watch":
        print("Starting watch mode (Ctrl+C to stop)...")
        queue.start_watching()

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nStopping...")
            queue.stop_watching()

    elif args.command == "process":
        # Process next job (simulation)
        job = queue.get_next_job()
        if job:
            print(f"Processing job: {job.job_id}")

            # Copy to spool
            spool_file = queue.copy_to_spool(job.job_id)
            if spool_file:
                print(f"Copied to spool: {spool_file}")
                queue.mark_cutting(job.job_id)

                # Simulate cutting time
                cut_time = job.fabric_length_cm / queue.cutting_speed * 60
                print(f"Simulating cut time: {cut_time:.1f} seconds")
                time.sleep(min(cut_time, 5))  # Cap at 5 seconds for demo

                queue.mark_complete(job.job_id)
                print(f"Job complete: {job.job_id}")
        else:
            print("No jobs in queue")


if __name__ == "__main__":
    main()
