#!/usr/bin/env python3
"""
Jindex Cutter Worker - TCP Socket Interface for Jindex UPC Inkjet Cutter

Pulls jobs from the ResilientCutterQueue and sends PLT files via raw TCP
to the Jindex cutter at the configured IP address on port 9100.

Features:
- Raw TCP socket communication (no print spooler)
- Connection retry with exponential backoff
- Job status updates to resilient queue
- Worker health monitoring
- Graceful shutdown support

Configuration:
    Environment variables:
    - JINDEX_IP: Cutter IP address (default: 192.168.1.100)
    - JINDEX_PORT: Cutter port (default: 9100)
    - CUTTER_DATA_DIR: Data directory for queue (default: ./cutter_data)

Usage:
    # Run directly
    python -m src.workers.jindex_cutter

    # With custom cutter IP
    JINDEX_IP=192.168.1.50 python -m src.workers.jindex_cutter

Author: Claude
Date: 2026-02-01
"""

import os
import sys
import socket
import signal
import logging
import time
import traceback
from pathlib import Path
from typing import Optional
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "core"))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - [%(levelname)s] - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("jindex-cutter")


class JindexCutter:
    """
    Low-level TCP interface to Jindex UPC Inkjet Cutter.

    The Jindex cutter accepts raw HPGL/PLT data on TCP port 9100.
    This class handles connection management and data transmission.
    """

    # Default timeouts
    CONNECT_TIMEOUT = 10  # seconds
    SEND_TIMEOUT = 300  # 5 minutes for large files

    # Retry configuration
    MAX_RETRIES = 3
    INITIAL_BACKOFF = 2  # seconds

    def __init__(self, ip: str, port: int = 9100):
        """
        Initialize cutter connection parameters.

        Args:
            ip: IP address of the Jindex cutter
            port: TCP port (default 9100)
        """
        self.ip = ip
        self.port = port
        self._socket: Optional[socket.socket] = None

    def connect(self) -> bool:
        """
        Establish TCP connection to cutter.

        Returns:
            True if connected successfully
        """
        try:
            if self._socket:
                self.disconnect()

            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._socket.settimeout(self.CONNECT_TIMEOUT)
            self._socket.connect((self.ip, self.port))

            logger.info(f"Connected to Jindex cutter at {self.ip}:{self.port}")
            return True

        except socket.timeout:
            logger.error(f"Connection timeout to {self.ip}:{self.port}")
            return False
        except socket.error as e:
            logger.error(f"Socket error connecting to {self.ip}:{self.port}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error connecting: {e}")
            return False

    def disconnect(self):
        """Close connection to cutter."""
        if self._socket:
            try:
                self._socket.close()
            except Exception:
                pass
            self._socket = None

    def is_connected(self) -> bool:
        """Check if currently connected."""
        return self._socket is not None

    def send_plt(self, plt_path: Path) -> bool:
        """
        Send PLT file to cutter.

        Args:
            plt_path: Path to PLT file

        Returns:
            True if sent successfully
        """
        if not plt_path.exists():
            logger.error(f"PLT file not found: {plt_path}")
            return False

        file_size = plt_path.stat().st_size
        logger.info(f"Sending {plt_path.name} ({file_size:,} bytes) to cutter...")

        # Retry loop with exponential backoff
        backoff = self.INITIAL_BACKOFF

        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                # Ensure connected
                if not self.is_connected():
                    if not self.connect():
                        raise ConnectionError("Failed to connect to cutter")

                # Set send timeout
                self._socket.settimeout(self.SEND_TIMEOUT)

                # Send file in chunks
                bytes_sent = 0
                chunk_size = 8192  # 8KB chunks

                with open(plt_path, "rb") as f:
                    while True:
                        chunk = f.read(chunk_size)
                        if not chunk:
                            break
                        self._socket.sendall(chunk)
                        bytes_sent += len(chunk)

                # Log success
                logger.info(f"Sent {bytes_sent:,} bytes to cutter successfully")
                return True

            except socket.timeout:
                logger.error(f"Send timeout (attempt {attempt}/{self.MAX_RETRIES})")
                self.disconnect()

            except socket.error as e:
                logger.error(f"Socket error during send (attempt {attempt}): {e}")
                self.disconnect()

            except Exception as e:
                logger.error(f"Unexpected error during send (attempt {attempt}): {e}")
                self.disconnect()

            # Backoff before retry
            if attempt < self.MAX_RETRIES:
                logger.info(f"Retrying in {backoff}s...")
                time.sleep(backoff)
                backoff *= 2

        logger.error(
            f"Failed to send {plt_path.name} after {self.MAX_RETRIES} attempts"
        )
        return False

    def test_connection(self) -> bool:
        """
        Test connection to cutter.

        Returns:
            True if cutter is reachable
        """
        try:
            if self.connect():
                self.disconnect()
                return True
            return False
        except Exception:
            return False


class CutterWorker:
    """
    Main cutter worker that processes jobs from the resilient queue.

    Features:
    - Pulls jobs from ResilientCutterQueue
    - Sends PLT to Jindex cutter via TCP
    - Updates job status (complete/failed)
    - Health monitoring via heartbeat
    - Graceful shutdown support
    """

    def __init__(
        self,
        cutter_ip: str,
        cutter_port: int = 9100,
        data_dir: Optional[Path] = None,
        worker_id: Optional[str] = None,
    ):
        """
        Initialize cutter worker.

        Args:
            cutter_ip: IP address of Jindex cutter
            cutter_port: TCP port (default 9100)
            data_dir: Directory for queue data
            worker_id: Unique worker identifier
        """
        self.cutter = JindexCutter(cutter_ip, cutter_port)
        self.data_dir = data_dir or Path("./cutter_data")
        self.worker_id = worker_id or f"cutter-worker-{os.getpid()}"

        self.shutdown_requested = False
        self.current_job_id = None
        self.jobs_completed = 0
        self.jobs_failed = 0
        self.start_time = None

        # Import queue lazily to avoid circular imports
        self._queue = None

    def _get_queue(self):
        """Get or create the resilient cutter queue."""
        if self._queue is None:
            from core.resilient_cutter_queue import ResilientCutterQueue

            self._queue = ResilientCutterQueue(self.data_dir)
        return self._queue

    def _setup_signal_handlers(self):
        """Setup graceful shutdown handlers."""
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        signal.signal(signal.SIGINT, self._handle_shutdown)

    def _handle_shutdown(self, signum, frame):
        """Handle shutdown signal gracefully."""
        logger.info(f"Received shutdown signal ({signum}), finishing current job...")
        self.shutdown_requested = True

    def _write_heartbeat(self):
        """Write heartbeat file for health monitoring."""
        try:
            heartbeat_path = Path("/tmp/cutter_worker_heartbeat")
            heartbeat_path.write_text(
                f"{self.worker_id}|{datetime.utcnow().isoformat()}|"
                f"completed={self.jobs_completed}|failed={self.jobs_failed}|"
                f"current_job={self.current_job_id or 'idle'}"
            )
        except Exception:
            pass  # Non-fatal

    def run(self):
        """
        Main worker loop.

        Continuously pulls jobs from queue and sends to cutter.
        """
        self._setup_signal_handlers()
        self.start_time = datetime.utcnow()
        queue = self._get_queue()

        logger.info(f"Cutter worker {self.worker_id} starting...")
        logger.info(f"Jindex cutter: {self.cutter.ip}:{self.cutter.port}")
        logger.info(f"Data directory: {self.data_dir}")

        # Test cutter connection on startup
        if not self.cutter.test_connection():
            logger.warning(
                f"Cannot reach cutter at {self.cutter.ip}:{self.cutter.port} - "
                "will retry when processing jobs"
            )
        else:
            logger.info("Cutter connection test successful")

        # Main loop
        poll_interval = 2  # seconds between queue checks

        while not self.shutdown_requested:
            try:
                self._write_heartbeat()

                # Get next job from queue
                job = queue.get_next_job()

                if job is None:
                    # No jobs available
                    time.sleep(poll_interval)
                    continue

                # Process the job
                self.current_job_id = job.job_id
                self._process_job(job, queue)
                self.current_job_id = None

            except KeyboardInterrupt:
                logger.info("Keyboard interrupt received")
                self.shutdown_requested = True
            except Exception as e:
                logger.error(f"Worker loop error: {e}")
                traceback.print_exc()
                time.sleep(5)

        # Cleanup
        self.cutter.disconnect()
        self._log_stats()
        logger.info(f"Cutter worker {self.worker_id} shutdown complete")

    def _process_job(self, job, queue):
        """
        Process a single cutting job.

        Args:
            job: CutterJob from queue
            queue: ResilientCutterQueue instance
        """
        logger.info(f"Processing job {job.job_id} (order: {job.order_id})")
        logger.info(f"  PLT file: {job.plt_file}")
        logger.info(f"  Priority: {job.priority.name}")
        logger.info(f"  Pieces: {job.piece_count}")

        plt_path = Path(job.plt_file)

        if not plt_path.exists():
            error_msg = f"PLT file not found: {plt_path}"
            logger.error(error_msg)
            queue.mark_failed(job.job_id, error_msg)
            self.jobs_failed += 1
            return

        # Send to cutter
        start_time = time.time()
        success = self.cutter.send_plt(plt_path)
        elapsed = time.time() - start_time

        if success:
            queue.mark_complete(job.job_id)
            self.jobs_completed += 1
            logger.info(f"Job {job.job_id} completed successfully ({elapsed:.1f}s)")
        else:
            error_msg = (
                f"Failed to send to cutter after {JindexCutter.MAX_RETRIES} attempts"
            )
            queue.mark_failed(job.job_id, error_msg)
            self.jobs_failed += 1
            logger.error(f"Job {job.job_id} failed: {error_msg}")

    def _log_stats(self):
        """Log worker statistics."""
        if self.start_time:
            uptime = (datetime.utcnow() - self.start_time).total_seconds()
            rate = self.jobs_completed / (uptime / 3600) if uptime > 0 else 0

            logger.info(
                f"Cutter worker {self.worker_id} stats: "
                f"completed={self.jobs_completed}, "
                f"failed={self.jobs_failed}, "
                f"uptime={uptime:.0f}s, "
                f"rate={rate:.1f}/hour"
            )


def run_cutter_worker():
    """
    Entry point for running the cutter worker.

    Configuration via environment variables:
    - JINDEX_IP: Cutter IP address
    - JINDEX_PORT: Cutter port
    - CUTTER_DATA_DIR: Data directory
    - CUTTER_WORKER_ID: Worker identifier
    """
    cutter_ip = os.getenv("JINDEX_IP", "192.168.1.100")
    cutter_port = int(os.getenv("JINDEX_PORT", "9100"))
    data_dir = Path(os.getenv("CUTTER_DATA_DIR", "./cutter_data"))
    worker_id = os.getenv("CUTTER_WORKER_ID")

    worker = CutterWorker(
        cutter_ip=cutter_ip,
        cutter_port=cutter_port,
        data_dir=data_dir,
        worker_id=worker_id,
    )
    worker.run()


if __name__ == "__main__":
    run_cutter_worker()
