#!/usr/bin/env python3
"""
Resilient Cutter Queue System

PROBLEM SOLVED:
1. Queue survives power cuts / crashes via Write-Ahead Log (WAL)
2. All jobs are archived permanently for ad-hoc reprints
3. Single pieces or entire jobs can be reprinted on demand
4. Automatic recovery on startup

ARCHITECTURE:
┌─────────────────────────────────────────────────────────────────┐
│                     CUTTER QUEUE SYSTEM                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐         │
│  │   Redis     │    │    WAL      │    │   Archive   │         │
│  │  (Fast Q)   │◄──►│  (Crash     │◄──►│  (Permanent │         │
│  │             │    │   Safe)     │    │   Storage)  │         │
│  └─────────────┘    └─────────────┘    └─────────────┘         │
│        │                   │                  │                 │
│        ▼                   ▼                  ▼                 │
│  ┌─────────────────────────────────────────────────────┐       │
│  │              Recovery Manager                        │       │
│  │  - Replays WAL on startup                           │       │
│  │  - Rebuilds Redis queue from archive                │       │
│  │  - Marks interrupted jobs for retry                 │       │
│  └─────────────────────────────────────────────────────┘       │
│                                                                 │
│  ┌─────────────────────────────────────────────────────┐       │
│  │              Reprint Manager                         │       │
│  │  - Reprint single piece by piece_id                 │       │
│  │  - Reprint entire job by job_id                     │       │
│  │  - Reprint by order_id (all jobs for order)         │       │
│  │  - Regenerate PLT from archived source data         │       │
│  └─────────────────────────────────────────────────────┘       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

Author: Claude
Date: 2026-02-01
"""

import os
import json
import time
import shutil
import sqlite3
import hashlib
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from contextlib import contextmanager
import threading

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# ============================================================================
# ENUMS & DATA CLASSES
# ============================================================================


class JobStatus(Enum):
    """Job status lifecycle."""

    PENDING = "pending"  # Created, not yet queued
    QUEUED = "queued"  # In queue, waiting
    CUTTING = "cutting"  # Currently being cut
    COMPLETE = "complete"  # Successfully cut
    ERROR = "error"  # Failed
    CANCELLED = "cancelled"  # Manually cancelled
    REPRINTING = "reprinting"  # Reprint in progress


class JobPriority(Enum):
    """Priority levels (lower = higher priority)."""

    RUSH = 1
    HIGH = 2
    NORMAL = 3
    LOW = 4
    REPRINT = 5  # Reprints are lower priority than new work


class WALAction(Enum):
    """Write-Ahead Log action types."""

    JOB_CREATED = "job_created"
    JOB_QUEUED = "job_queued"
    JOB_STARTED = "job_started"
    JOB_COMPLETED = "job_completed"
    JOB_FAILED = "job_failed"
    JOB_CANCELLED = "job_cancelled"
    REPRINT_REQUESTED = "reprint_requested"


@dataclass
class CutterJob:
    """A cutting job with full tracking."""

    job_id: str
    order_id: str
    plt_file: str
    dxf_file: Optional[str] = None  # Source DXF if available
    pds_file: Optional[str] = None  # Source PDS if available
    measurements_json: Optional[str] = None  # Source measurements
    priority: JobPriority = JobPriority.NORMAL
    status: JobStatus = JobStatus.PENDING
    fabric_length_cm: float = 0.0
    fabric_width_cm: float = 157.0  # 62 inches default
    piece_count: int = 0
    pieces: List[Dict] = field(default_factory=list)  # Individual piece info
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    queued_at: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    checksum_sha256: Optional[str] = None
    is_reprint: bool = False
    original_job_id: Optional[str] = None  # If this is a reprint, link to original

    def to_dict(self) -> Dict:
        """Convert to dictionary for storage."""
        return {
            **asdict(self),
            "priority": self.priority.value,
            "status": self.status.value,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "CutterJob":
        """Create from dictionary."""
        data = data.copy()
        data["priority"] = JobPriority(data["priority"])
        data["status"] = JobStatus(data["status"])
        return cls(**data)


@dataclass
class PieceInfo:
    """Information about a single pattern piece."""

    piece_id: str
    job_id: str
    order_id: str
    piece_name: str  # e.g., "JACKET_FRONT_LEFT"
    piece_number: int  # e.g., 1 of 15
    total_pieces: int
    plt_start_byte: int  # Position in PLT file
    plt_end_byte: int
    width_cm: float
    height_cm: float

    def to_dict(self) -> Dict:
        return asdict(self)


# ============================================================================
# WRITE-AHEAD LOG (WAL)
# ============================================================================


class WriteAheadLog:
    """
    Write-Ahead Log for crash recovery.

    Every state change is written to the WAL BEFORE being applied.
    On recovery, we replay the WAL to rebuild state.
    """

    def __init__(self, wal_path: Path):
        self.wal_path = wal_path
        self.wal_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def append(self, action: WALAction, job_id: str, data: Dict) -> int:
        """
        Append entry to WAL.

        Returns:
            Sequence number of the entry
        """
        with self._lock:
            entry = {
                "seq": self._get_next_seq(),
                "timestamp": datetime.now().isoformat(),
                "action": action.value,
                "job_id": job_id,
                "data": data,
            }

            # Atomic append with fsync
            with open(self.wal_path, "a") as f:
                f.write(json.dumps(entry) + "\n")
                f.flush()
                os.fsync(f.fileno())

            return entry["seq"]

    def replay(self) -> List[Dict]:
        """
        Read all entries from WAL for replay.

        Returns:
            List of WAL entries in order
        """
        entries = []

        if not self.wal_path.exists():
            return entries

        with open(self.wal_path, "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        logger.warning(f"Skipping corrupt WAL entry: {line[:50]}...")

        return sorted(entries, key=lambda x: x["seq"])

    def checkpoint(self, last_seq: int):
        """
        Create checkpoint - WAL entries before last_seq can be removed.

        This is called after state has been persisted to archive.
        """
        entries = self.replay()
        remaining = [e for e in entries if e["seq"] > last_seq]

        # Write remaining entries to new WAL
        temp_path = self.wal_path.with_suffix(".tmp")
        with open(temp_path, "w") as f:
            for entry in remaining:
                f.write(json.dumps(entry) + "\n")
            f.flush()
            os.fsync(f.fileno())

        # Atomic replace
        temp_path.replace(self.wal_path)

        logger.info(f"WAL checkpoint: removed {len(entries) - len(remaining)} entries")

    def _get_next_seq(self) -> int:
        """Get next sequence number."""
        entries = self.replay()
        if entries:
            return entries[-1]["seq"] + 1
        return 1


# ============================================================================
# JOB ARCHIVE (Permanent Storage)
# ============================================================================


class JobArchive:
    """
    Permanent archive of all jobs and their files.

    Uses SQLite for metadata + filesystem for PLT files.
    This survives any crash and allows reprints forever.
    """

    def __init__(self, archive_dir: Path):
        self.archive_dir = archive_dir
        self.archive_dir.mkdir(parents=True, exist_ok=True)

        self.db_path = archive_dir / "job_archive.db"
        self.files_dir = archive_dir / "files"
        self.files_dir.mkdir(exist_ok=True)

        self._init_db()

    def _init_db(self):
        """Initialize SQLite database."""
        with self._get_db() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS jobs (
                    job_id TEXT PRIMARY KEY,
                    order_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    priority INTEGER NOT NULL,
                    plt_file TEXT,
                    dxf_file TEXT,
                    pds_file TEXT,
                    measurements_json TEXT,
                    fabric_length_cm REAL,
                    fabric_width_cm REAL,
                    piece_count INTEGER,
                    pieces_json TEXT,
                    created_at TEXT NOT NULL,
                    queued_at TEXT,
                    started_at TEXT,
                    completed_at TEXT,
                    error_message TEXT,
                    retry_count INTEGER DEFAULT 0,
                    checksum_sha256 TEXT,
                    is_reprint INTEGER DEFAULT 0,
                    original_job_id TEXT,
                    archived_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE INDEX IF NOT EXISTS idx_jobs_order_id ON jobs(order_id);
                CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
                CREATE INDEX IF NOT EXISTS idx_jobs_created_at ON jobs(created_at);
                
                CREATE TABLE IF NOT EXISTS pieces (
                    piece_id TEXT PRIMARY KEY,
                    job_id TEXT NOT NULL,
                    order_id TEXT NOT NULL,
                    piece_name TEXT NOT NULL,
                    piece_number INTEGER NOT NULL,
                    total_pieces INTEGER NOT NULL,
                    plt_start_byte INTEGER,
                    plt_end_byte INTEGER,
                    width_cm REAL,
                    height_cm REAL,
                    FOREIGN KEY (job_id) REFERENCES jobs(job_id)
                );
                
                CREATE INDEX IF NOT EXISTS idx_pieces_job_id ON pieces(job_id);
                CREATE INDEX IF NOT EXISTS idx_pieces_order_id ON pieces(order_id);
                
                CREATE TABLE IF NOT EXISTS reprints (
                    reprint_id TEXT PRIMARY KEY,
                    original_job_id TEXT NOT NULL,
                    new_job_id TEXT NOT NULL,
                    reprint_type TEXT NOT NULL,  -- 'full_job', 'single_piece'
                    piece_id TEXT,  -- NULL if full job reprint
                    reason TEXT,
                    requested_by TEXT,
                    requested_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (original_job_id) REFERENCES jobs(job_id),
                    FOREIGN KEY (new_job_id) REFERENCES jobs(job_id)
                );
            """)

    @contextmanager
    def _get_db(self):
        """Get database connection with auto-commit."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def archive_job(self, job: CutterJob) -> bool:
        """
        Archive a job and its files.

        Copies PLT file to archive and stores metadata in SQLite.
        """
        try:
            # Archive PLT file
            archived_plt = None
            if job.plt_file and Path(job.plt_file).exists():
                archived_plt = self._archive_file(job.plt_file, job.job_id, "plt")

            # Archive DXF if available
            archived_dxf = None
            if job.dxf_file and Path(job.dxf_file).exists():
                archived_dxf = self._archive_file(job.dxf_file, job.job_id, "dxf")

            # Archive PDS if available
            archived_pds = None
            if job.pds_file and Path(job.pds_file).exists():
                archived_pds = self._archive_file(job.pds_file, job.job_id, "pds")

            # Store measurements JSON
            archived_measurements = None
            if job.measurements_json:
                measurements_path = self.files_dir / f"{job.job_id}_measurements.json"
                with open(measurements_path, "w") as f:
                    f.write(job.measurements_json)
                archived_measurements = str(measurements_path)

            # Store in database
            with self._get_db() as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO jobs (
                        job_id, order_id, status, priority,
                        plt_file, dxf_file, pds_file, measurements_json,
                        fabric_length_cm, fabric_width_cm, piece_count, pieces_json,
                        created_at, queued_at, started_at, completed_at,
                        error_message, retry_count, checksum_sha256,
                        is_reprint, original_job_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        job.job_id,
                        job.order_id,
                        job.status.value,
                        job.priority.value,
                        archived_plt,
                        archived_dxf,
                        archived_pds,
                        archived_measurements,
                        job.fabric_length_cm,
                        job.fabric_width_cm,
                        job.piece_count,
                        json.dumps(job.pieces),
                        job.created_at,
                        job.queued_at,
                        job.started_at,
                        job.completed_at,
                        job.error_message,
                        job.retry_count,
                        job.checksum_sha256,
                        1 if job.is_reprint else 0,
                        job.original_job_id,
                    ),
                )

                # Archive pieces
                for piece in job.pieces:
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO pieces (
                            piece_id, job_id, order_id, piece_name,
                            piece_number, total_pieces,
                            plt_start_byte, plt_end_byte, width_cm, height_cm
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                        (
                            piece.get("piece_id"),
                            job.job_id,
                            job.order_id,
                            piece.get("piece_name"),
                            piece.get("piece_number"),
                            piece.get("total_pieces"),
                            piece.get("plt_start_byte"),
                            piece.get("plt_end_byte"),
                            piece.get("width_cm"),
                            piece.get("height_cm"),
                        ),
                    )

            logger.info(f"Archived job {job.job_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to archive job {job.job_id}: {e}")
            return False

    def _archive_file(self, src_path: str, job_id: str, ext: str) -> str:
        """Copy file to archive directory."""
        src = Path(src_path)
        dst = self.files_dir / f"{job_id}.{ext}"
        shutil.copy2(src, dst)
        return str(dst)

    def get_job(self, job_id: str) -> Optional[CutterJob]:
        """Retrieve a job from archive."""
        with self._get_db() as conn:
            row = conn.execute(
                "SELECT * FROM jobs WHERE job_id = ?", (job_id,)
            ).fetchone()

            if not row:
                return None

            return self._row_to_job(row)

    def get_jobs_by_order(self, order_id: str) -> List[CutterJob]:
        """Get all jobs for an order."""
        with self._get_db() as conn:
            rows = conn.execute(
                "SELECT * FROM jobs WHERE order_id = ? ORDER BY created_at", (order_id,)
            ).fetchall()

            return [self._row_to_job(row) for row in rows]

    def get_pieces_by_job(self, job_id: str) -> List[PieceInfo]:
        """Get all pieces for a job."""
        with self._get_db() as conn:
            rows = conn.execute(
                "SELECT * FROM pieces WHERE job_id = ? ORDER BY piece_number", (job_id,)
            ).fetchall()

            return [PieceInfo(**dict(row)) for row in rows]

    def get_piece(self, piece_id: str) -> Optional[Tuple[PieceInfo, CutterJob]]:
        """Get a specific piece and its parent job."""
        with self._get_db() as conn:
            row = conn.execute(
                "SELECT * FROM pieces WHERE piece_id = ?", (piece_id,)
            ).fetchone()

            if not row:
                return None

            piece = PieceInfo(**dict(row))
            job = self.get_job(piece.job_id)

            return (piece, job)

    def _row_to_job(self, row: sqlite3.Row) -> CutterJob:
        """Convert database row to CutterJob."""
        data = dict(row)
        data["priority"] = JobPriority(data["priority"])
        data["status"] = JobStatus(data["status"])
        data["pieces"] = json.loads(data["pieces_json"]) if data["pieces_json"] else []
        data["is_reprint"] = bool(data["is_reprint"])
        del data["pieces_json"]
        del data["archived_at"]
        return CutterJob(**data)

    def search_jobs(
        self,
        order_id: Optional[str] = None,
        status: Optional[JobStatus] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 100,
    ) -> List[CutterJob]:
        """Search archived jobs."""
        query = "SELECT * FROM jobs WHERE 1=1"
        params = []

        if order_id:
            query += " AND order_id = ?"
            params.append(order_id)

        if status:
            query += " AND status = ?"
            params.append(status.value)

        if start_date:
            query += " AND created_at >= ?"
            params.append(start_date)

        if end_date:
            query += " AND created_at <= ?"
            params.append(end_date)

        query += f" ORDER BY created_at DESC LIMIT {limit}"

        with self._get_db() as conn:
            rows = conn.execute(query, params).fetchall()
            return [self._row_to_job(row) for row in rows]

    def record_reprint(
        self,
        original_job_id: str,
        new_job_id: str,
        reprint_type: str,
        piece_id: Optional[str] = None,
        reason: str = "",
        requested_by: str = "system",
    ):
        """Record a reprint request."""
        reprint_id = f"REPRINT-{int(time.time() * 1000)}"

        with self._get_db() as conn:
            conn.execute(
                """
                INSERT INTO reprints (
                    reprint_id, original_job_id, new_job_id,
                    reprint_type, piece_id, reason, requested_by
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    reprint_id,
                    original_job_id,
                    new_job_id,
                    reprint_type,
                    piece_id,
                    reason,
                    requested_by,
                ),
            )

        return reprint_id


# ============================================================================
# RESILIENT CUTTER QUEUE
# ============================================================================


class ResilientCutterQueue:
    """
    Crash-safe cutter queue with reprint capability.

    Features:
    - Write-Ahead Log for crash recovery
    - Permanent archive for reprints
    - Single piece or full job reprints
    - Automatic recovery on startup
    """

    def __init__(
        self,
        data_dir: Path,
        spool_dir: Optional[Path] = None,
        cutting_speed_cm_per_min: float = 100.0,
    ):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.spool_dir = spool_dir or self.data_dir / "spool"
        self.spool_dir.mkdir(parents=True, exist_ok=True)

        self.cutting_speed = cutting_speed_cm_per_min

        # Components
        self.wal = WriteAheadLog(self.data_dir / "cutter_queue.wal")
        self.archive = JobArchive(self.data_dir / "archive")

        # In-memory state (rebuilt from WAL/archive on startup)
        self.active_jobs: Dict[str, CutterJob] = {}
        self.queue: List[str] = []  # Job IDs in priority order

        self._lock = threading.Lock()

        # Recover state
        self._recover()

        logger.info(f"ResilientCutterQueue initialized at {self.data_dir}")
        logger.info(
            f"Active jobs: {len(self.active_jobs)}, Queue depth: {len(self.queue)}"
        )

    def _recover(self):
        """
        Recover state from WAL and archive.

        Called on startup to rebuild in-memory state.
        """
        logger.info("Starting recovery...")

        # Replay WAL to get current state
        wal_entries = self.wal.replay()

        recovered_jobs = {}

        for entry in wal_entries:
            job_id = entry["job_id"]
            action = WALAction(entry["action"])
            data = entry["data"]

            if action == WALAction.JOB_CREATED:
                recovered_jobs[job_id] = CutterJob.from_dict(data)

            elif action == WALAction.JOB_QUEUED:
                if job_id in recovered_jobs:
                    recovered_jobs[job_id].status = JobStatus.QUEUED
                    recovered_jobs[job_id].queued_at = data.get("queued_at")

            elif action == WALAction.JOB_STARTED:
                if job_id in recovered_jobs:
                    # Job was cutting when crash happened - mark for retry
                    recovered_jobs[job_id].status = JobStatus.QUEUED
                    recovered_jobs[job_id].retry_count += 1
                    logger.warning(
                        f"Job {job_id} was interrupted during cutting - re-queuing"
                    )

            elif action == WALAction.JOB_COMPLETED:
                if job_id in recovered_jobs:
                    recovered_jobs[job_id].status = JobStatus.COMPLETE
                    recovered_jobs[job_id].completed_at = data.get("completed_at")
                    # Archive completed job
                    self.archive.archive_job(recovered_jobs[job_id])
                    del recovered_jobs[job_id]  # Remove from active

            elif action == WALAction.JOB_FAILED:
                if job_id in recovered_jobs:
                    recovered_jobs[job_id].status = JobStatus.ERROR
                    recovered_jobs[job_id].error_message = data.get("error_message")

            elif action == WALAction.JOB_CANCELLED:
                if job_id in recovered_jobs:
                    recovered_jobs[job_id].status = JobStatus.CANCELLED

        # Set active jobs and rebuild queue
        self.active_jobs = recovered_jobs
        self.queue = [
            job_id
            for job_id, job in sorted(
                recovered_jobs.items(),
                key=lambda x: (x[1].priority.value, x[1].created_at),
            )
            if job.status in [JobStatus.PENDING, JobStatus.QUEUED]
        ]

        logger.info(
            f"Recovery complete: {len(self.active_jobs)} active jobs, {len(self.queue)} queued"
        )

    def add_job(
        self,
        order_id: str,
        plt_file: Path,
        priority: JobPriority = JobPriority.NORMAL,
        dxf_file: Optional[Path] = None,
        pds_file: Optional[Path] = None,
        measurements: Optional[Dict] = None,
        pieces: Optional[List[Dict]] = None,
        fabric_length_cm: float = 0.0,
    ) -> CutterJob:
        """
        Add a new job to the queue.

        Thread-safe and crash-safe.
        """
        with self._lock:
            # Generate job ID
            job_id = f"JOB-{order_id}-{int(time.time() * 1000)}"

            # Calculate checksum
            checksum = self._calculate_checksum(plt_file)

            # Extract piece info if available
            piece_count = len(pieces) if pieces else 0

            # Create job
            job = CutterJob(
                job_id=job_id,
                order_id=order_id,
                plt_file=str(plt_file),
                dxf_file=str(dxf_file) if dxf_file else None,
                pds_file=str(pds_file) if pds_file else None,
                measurements_json=json.dumps(measurements) if measurements else None,
                priority=priority,
                piece_count=piece_count,
                pieces=pieces or [],
                checksum_sha256=checksum,
                fabric_length_cm=fabric_length_cm,
            )

            # WAL: Log intent BEFORE applying
            self.wal.append(WALAction.JOB_CREATED, job_id, job.to_dict())

            # Apply to state
            self.active_jobs[job_id] = job

            # Queue the job
            job.status = JobStatus.QUEUED
            job.queued_at = datetime.now().isoformat()
            self.wal.append(WALAction.JOB_QUEUED, job_id, {"queued_at": job.queued_at})

            # Insert into queue in priority order
            self._insert_into_queue(job_id)

            # Archive immediately (so we can reprint even if crash)
            self.archive.archive_job(job)

            logger.info(f"Added job {job_id} to queue (priority: {priority.name})")

            return job

    def _insert_into_queue(self, job_id: str):
        """Insert job into queue maintaining priority order."""
        job = self.active_jobs[job_id]

        # Find insertion point
        insert_idx = 0
        for i, qid in enumerate(self.queue):
            if qid in self.active_jobs:
                if self.active_jobs[qid].priority.value > job.priority.value:
                    break
            insert_idx = i + 1

        self.queue.insert(insert_idx, job_id)

    def get_next_job(self) -> Optional[CutterJob]:
        """
        Get the next job from the queue.

        Marks it as CUTTING and logs to WAL.
        """
        with self._lock:
            while self.queue:
                job_id = self.queue.pop(0)

                if job_id not in self.active_jobs:
                    continue

                job = self.active_jobs[job_id]

                if job.status != JobStatus.QUEUED:
                    continue

                # Check retry limit
                if job.retry_count >= job.max_retries:
                    self._mark_failed(job_id, "Max retries exceeded")
                    continue

                # Log to WAL BEFORE marking as cutting
                job.status = JobStatus.CUTTING
                job.started_at = datetime.now().isoformat()
                self.wal.append(
                    WALAction.JOB_STARTED, job_id, {"started_at": job.started_at}
                )

                return job

            return None

    def mark_complete(self, job_id: str):
        """Mark a job as successfully completed."""
        with self._lock:
            if job_id not in self.active_jobs:
                return

            job = self.active_jobs[job_id]
            job.status = JobStatus.COMPLETE
            job.completed_at = datetime.now().isoformat()

            # Log to WAL
            self.wal.append(
                WALAction.JOB_COMPLETED, job_id, {"completed_at": job.completed_at}
            )

            # Archive final state
            self.archive.archive_job(job)

            # Remove from active
            del self.active_jobs[job_id]

            logger.info(f"Job {job_id} completed")

    def mark_failed(self, job_id: str, error_message: str):
        """Mark a job as failed."""
        with self._lock:
            self._mark_failed(job_id, error_message)

    def _mark_failed(self, job_id: str, error_message: str):
        """Internal: Mark job as failed (must hold lock)."""
        if job_id not in self.active_jobs:
            return

        job = self.active_jobs[job_id]
        job.status = JobStatus.ERROR
        job.error_message = error_message

        # Log to WAL
        self.wal.append(WALAction.JOB_FAILED, job_id, {"error_message": error_message})

        # Archive
        self.archive.archive_job(job)

        logger.error(f"Job {job_id} failed: {error_message}")

    def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate SHA256 checksum of file."""
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    # ========================================================================
    # REPRINT FUNCTIONALITY
    # ========================================================================

    def reprint_job(
        self,
        job_id: str,
        reason: str = "Manual reprint request",
        requested_by: str = "operator",
        priority: JobPriority = JobPriority.NORMAL,  # Changed from REPRINT to NORMAL
    ) -> Optional[CutterJob]:
        """
        Reprint an entire job.

        Creates a new job copying all data from the original.
        """
        # Get original job from archive
        original = self.archive.get_job(job_id)
        if not original:
            logger.error(f"Cannot reprint: job {job_id} not found in archive")
            return None

        # Check PLT file exists in archive
        if not original.plt_file or not Path(original.plt_file).exists():
            logger.error(f"Cannot reprint: PLT file not found for job {job_id}")
            return None

        with self._lock:
            # Create new job ID
            new_job_id = f"REPRINT-{original.job_id}-{int(time.time() * 1000)}"

            # Create reprint job
            reprint_job = CutterJob(
                job_id=new_job_id,
                order_id=original.order_id,
                plt_file=original.plt_file,
                dxf_file=original.dxf_file,
                pds_file=original.pds_file,
                measurements_json=original.measurements_json,
                priority=priority,
                fabric_length_cm=original.fabric_length_cm,
                fabric_width_cm=original.fabric_width_cm,
                piece_count=original.piece_count,
                pieces=original.pieces,
                checksum_sha256=original.checksum_sha256,
                is_reprint=True,
                original_job_id=job_id,
            )

            # Log to WAL
            self.wal.append(
                WALAction.REPRINT_REQUESTED,
                new_job_id,
                {
                    "original_job_id": job_id,
                    "reason": reason,
                    "requested_by": requested_by,
                },
            )
            self.wal.append(WALAction.JOB_CREATED, new_job_id, reprint_job.to_dict())

            # Add to active and queue
            self.active_jobs[new_job_id] = reprint_job
            reprint_job.status = JobStatus.QUEUED
            reprint_job.queued_at = datetime.now().isoformat()
            self.wal.append(
                WALAction.JOB_QUEUED, new_job_id, {"queued_at": reprint_job.queued_at}
            )
            self._insert_into_queue(new_job_id)

            # Archive
            self.archive.archive_job(reprint_job)

            # Record reprint
            self.archive.record_reprint(
                job_id, new_job_id, "full_job", reason=reason, requested_by=requested_by
            )

            logger.info(f"Created reprint job {new_job_id} from original {job_id}")

            return reprint_job

    def reprint_piece(
        self,
        piece_id: str,
        reason: str = "Single piece reprint",
        requested_by: str = "operator",
        priority: JobPriority = JobPriority.NORMAL,
    ) -> Optional[CutterJob]:
        """
        Reprint a single piece.

        Extracts the piece from the original PLT and creates a mini-job.
        """
        # Get piece and its parent job
        result = self.archive.get_piece(piece_id)
        if not result:
            logger.error(f"Cannot reprint: piece {piece_id} not found in archive")
            return None

        piece, original_job = result

        if not original_job.plt_file or not Path(original_job.plt_file).exists():
            logger.error(f"Cannot reprint piece: PLT file not found")
            return None

        # Extract piece from PLT
        piece_plt_path = self._extract_piece_plt(piece, original_job)
        if not piece_plt_path:
            logger.error(f"Failed to extract piece {piece_id} from PLT")
            return None

        with self._lock:
            # Create new job for single piece
            new_job_id = f"PIECE-REPRINT-{piece_id}-{int(time.time() * 1000)}"

            reprint_job = CutterJob(
                job_id=new_job_id,
                order_id=original_job.order_id,
                plt_file=str(piece_plt_path),
                priority=priority,
                piece_count=1,
                pieces=[piece.to_dict()],
                checksum_sha256=self._calculate_checksum(piece_plt_path),
                is_reprint=True,
                original_job_id=original_job.job_id,
            )

            # Log and queue
            self.wal.append(
                WALAction.REPRINT_REQUESTED,
                new_job_id,
                {
                    "original_job_id": original_job.job_id,
                    "piece_id": piece_id,
                    "reason": reason,
                    "requested_by": requested_by,
                },
            )
            self.wal.append(WALAction.JOB_CREATED, new_job_id, reprint_job.to_dict())

            self.active_jobs[new_job_id] = reprint_job
            reprint_job.status = JobStatus.QUEUED
            reprint_job.queued_at = datetime.now().isoformat()
            self.wal.append(
                WALAction.JOB_QUEUED, new_job_id, {"queued_at": reprint_job.queued_at}
            )
            self._insert_into_queue(new_job_id)

            # Archive
            self.archive.archive_job(reprint_job)
            self.archive.record_reprint(
                original_job.job_id,
                new_job_id,
                "single_piece",
                piece_id=piece_id,
                reason=reason,
                requested_by=requested_by,
            )

            logger.info(f"Created piece reprint job {new_job_id} for piece {piece_id}")

            return reprint_job

    def _extract_piece_plt(self, piece: PieceInfo, job: CutterJob) -> Optional[Path]:
        """
        Extract a single piece from a PLT file.

        HPGL/PLT files are command-based, so we extract the commands
        for the specific piece based on byte offsets.
        """
        try:
            plt_path = Path(job.plt_file)

            # If we have byte offsets, use them
            if piece.plt_start_byte is not None and piece.plt_end_byte is not None:
                with open(plt_path, "rb") as f:
                    f.seek(piece.plt_start_byte)
                    piece_data = f.read(piece.plt_end_byte - piece.plt_start_byte)

                # Add HPGL header and footer
                header = b"IN;SP1;"  # Initialize, select pen 1
                footer = b"SP0;IN;"  # Pen up, reinitialize

                piece_plt = header + piece_data + footer
            else:
                # Fallback: just use the whole file (for reprints before piece tracking)
                with open(plt_path, "rb") as f:
                    piece_plt = f.read()

            # Save extracted piece
            output_path = self.spool_dir / f"piece_{piece.piece_id}.plt"
            with open(output_path, "wb") as f:
                f.write(piece_plt)

            return output_path

        except Exception as e:
            logger.error(f"Error extracting piece: {e}")
            return None

    def reprint_order(
        self,
        order_id: str,
        reason: str = "Order reprint",
        requested_by: str = "operator",
    ) -> List[CutterJob]:
        """
        Reprint all jobs for an order.

        Returns list of created reprint jobs.
        """
        jobs = self.archive.get_jobs_by_order(order_id)

        if not jobs:
            logger.error(f"Cannot reprint: no jobs found for order {order_id}")
            return []

        reprint_jobs = []
        for job in jobs:
            if job.status == JobStatus.COMPLETE:
                reprint = self.reprint_job(
                    job.job_id, reason=reason, requested_by=requested_by
                )
                if reprint:
                    reprint_jobs.append(reprint)

        return reprint_jobs

    # ========================================================================
    # STATUS & QUERIES
    # ========================================================================

    def get_status(self) -> Dict:
        """Get current queue status."""
        with self._lock:
            status_counts = {}
            for status in JobStatus:
                status_counts[status.value] = sum(
                    1 for j in self.active_jobs.values() if j.status == status
                )

            total_fabric = sum(
                j.fabric_length_cm
                for j in self.active_jobs.values()
                if j.status in [JobStatus.PENDING, JobStatus.QUEUED]
            )

            cutting_count = sum(
                1 for j in self.active_jobs.values() if j.status == JobStatus.CUTTING
            )

            return {
                "queue_depth": len(self.queue),
                "active_jobs": len(self.active_jobs),
                "cutting_count": cutting_count,
                "status_breakdown": status_counts,
                "total_fabric_cm": total_fabric,
                "estimated_time_min": total_fabric / self.cutting_speed
                if self.cutting_speed > 0
                else 0,
            }

    def list_queue(self) -> List[CutterJob]:
        """List all jobs in queue order."""
        with self._lock:
            return [
                self.active_jobs[job_id]
                for job_id in self.queue
                if job_id in self.active_jobs
            ]

    def get_job(self, job_id: str) -> Optional[CutterJob]:
        """Get a job by ID (active or archived)."""
        with self._lock:
            if job_id in self.active_jobs:
                return self.active_jobs[job_id]

        return self.archive.get_job(job_id)

    def get_recent_jobs(self, limit: int = 20) -> List[CutterJob]:
        """
        Get recently completed/failed jobs from archive.

        Returns jobs sorted by completion time (most recent first).
        """
        return self.archive.search_jobs(limit=limit)

    def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a queued job (cannot cancel if already cutting).

        Returns True if cancelled successfully.
        """
        with self._lock:
            if job_id not in self.active_jobs:
                logger.warning(f"Cannot cancel: job {job_id} not found")
                return False

            job = self.active_jobs[job_id]

            if job.status == JobStatus.CUTTING:
                logger.warning(f"Cannot cancel: job {job_id} is already cutting")
                return False

            if job.status not in [JobStatus.PENDING, JobStatus.QUEUED]:
                logger.warning(f"Cannot cancel: job {job_id} has status {job.status}")
                return False

            # Remove from queue
            if job_id in self.queue:
                self.queue.remove(job_id)

            # Mark as cancelled
            job.status = JobStatus.CANCELLED
            self.wal.append(WALAction.JOB_CANCELLED, job_id, {})

            # Archive the cancelled job
            self.archive.archive_job(job)

            # Remove from active
            del self.active_jobs[job_id]

            logger.info(f"Job {job_id} cancelled")
            return True

    def retry_job(self, job_id: str) -> Optional[CutterJob]:
        """
        Retry a failed job by re-queuing it.

        Returns the job if retry was successful.
        """
        with self._lock:
            # Check active jobs first
            if job_id in self.active_jobs:
                job = self.active_jobs[job_id]
                if job.status != JobStatus.ERROR:
                    logger.warning(f"Cannot retry: job {job_id} is not failed")
                    return None
            else:
                # Get from archive
                job = self.archive.get_job(job_id)
                if not job:
                    logger.warning(f"Cannot retry: job {job_id} not found")
                    return None
                if job.status != JobStatus.ERROR:
                    logger.warning(f"Cannot retry: job {job_id} is not failed")
                    return None

                # Re-add to active jobs
                self.active_jobs[job_id] = job

            # Check retry limit
            if job.retry_count >= job.max_retries:
                logger.warning(f"Cannot retry: job {job_id} has exceeded max retries")
                return None

            # Reset status and re-queue
            job.status = JobStatus.QUEUED
            job.retry_count += 1
            job.error_message = None
            job.queued_at = datetime.now().isoformat()

            self.wal.append(
                WALAction.JOB_QUEUED,
                job_id,
                {"queued_at": job.queued_at, "retry": True},
            )
            self._insert_into_queue(job_id)

            logger.info(f"Job {job_id} re-queued (retry {job.retry_count})")
            return job

    def checkpoint(self):
        """
        Create WAL checkpoint.

        Call periodically to prevent WAL from growing unbounded.
        """
        # Get last completed job's WAL sequence
        entries = self.wal.replay()
        if not entries:
            return

        # Find last completed action
        last_complete_seq = 0
        for entry in entries:
            if entry["action"] == WALAction.JOB_COMPLETED.value:
                last_complete_seq = entry["seq"]

        if last_complete_seq > 0:
            self.wal.checkpoint(last_complete_seq)


# ============================================================================
# CLI
# ============================================================================


def main():
    """Command-line interface for the resilient cutter queue."""
    import argparse

    parser = argparse.ArgumentParser(description="Resilient Cutter Queue")
    parser.add_argument(
        "command",
        choices=[
            "status",
            "list",
            "add",
            "next",
            "complete",
            "fail",
            "reprint-job",
            "reprint-piece",
            "reprint-order",
            "search",
            "checkpoint",
        ],
    )
    parser.add_argument("--data-dir", default="./cutter_data", help="Data directory")
    parser.add_argument("--job-id", help="Job ID")
    parser.add_argument("--order-id", help="Order ID")
    parser.add_argument("--piece-id", help="Piece ID")
    parser.add_argument("--plt", type=Path, help="PLT file path")
    parser.add_argument(
        "--priority", choices=["rush", "high", "normal", "low"], default="normal"
    )
    parser.add_argument("--reason", default="Manual request", help="Reason for reprint")
    parser.add_argument("--error", help="Error message for fail command")

    args = parser.parse_args()

    queue = ResilientCutterQueue(Path(args.data_dir))

    priority_map = {
        "rush": JobPriority.RUSH,
        "high": JobPriority.HIGH,
        "normal": JobPriority.NORMAL,
        "low": JobPriority.LOW,
    }

    if args.command == "status":
        status = queue.get_status()
        print("\n" + "=" * 60)
        print("CUTTER QUEUE STATUS")
        print("=" * 60)
        print(f"Queue depth:     {status['queue_depth']}")
        print(f"Active jobs:     {status['active_jobs']}")
        print(f"Total fabric:    {status['total_fabric_cm']:.1f} cm")
        print(f"Est. time:       {status['estimated_time_min']:.1f} min")
        print("\nStatus breakdown:")
        for s, count in status["status_breakdown"].items():
            if count > 0:
                print(f"  {s}: {count}")
        print("=" * 60)

    elif args.command == "list":
        jobs = queue.list_queue()
        print(f"\n{'Job ID':<40} {'Order':<15} {'Priority':<10} {'Status':<10}")
        print("-" * 80)
        for job in jobs:
            print(
                f"{job.job_id:<40} {job.order_id:<15} {job.priority.name:<10} {job.status.value:<10}"
            )

    elif args.command == "add":
        if not args.order_id or not args.plt:
            parser.error("--order-id and --plt required for add")
        job = queue.add_job(args.order_id, args.plt, priority_map[args.priority])
        print(f"Added job: {job.job_id}")

    elif args.command == "next":
        job = queue.get_next_job()
        if job:
            print(f"Next job: {job.job_id}")
            print(f"  Order: {job.order_id}")
            print(f"  PLT: {job.plt_file}")
            print(f"  Priority: {job.priority.name}")
        else:
            print("No jobs in queue")

    elif args.command == "complete":
        if not args.job_id:
            parser.error("--job-id required")
        queue.mark_complete(args.job_id)
        print(f"Marked {args.job_id} as complete")

    elif args.command == "fail":
        if not args.job_id or not args.error:
            parser.error("--job-id and --error required")
        queue.mark_failed(args.job_id, args.error)
        print(f"Marked {args.job_id} as failed")

    elif args.command == "reprint-job":
        if not args.job_id:
            parser.error("--job-id required")
        job = queue.reprint_job(args.job_id, reason=args.reason)
        if job:
            print(f"Created reprint job: {job.job_id}")
        else:
            print("Reprint failed - check logs")

    elif args.command == "reprint-piece":
        if not args.piece_id:
            parser.error("--piece-id required")
        job = queue.reprint_piece(args.piece_id, reason=args.reason)
        if job:
            print(f"Created piece reprint job: {job.job_id}")
        else:
            print("Reprint failed - check logs")

    elif args.command == "reprint-order":
        if not args.order_id:
            parser.error("--order-id required")
        jobs = queue.reprint_order(args.order_id, reason=args.reason)
        print(f"Created {len(jobs)} reprint jobs for order {args.order_id}")
        for job in jobs:
            print(f"  {job.job_id}")

    elif args.command == "search":
        jobs = queue.archive.search_jobs(order_id=args.order_id)
        print(f"\nFound {len(jobs)} archived jobs:")
        for job in jobs:
            print(
                f"  {job.job_id} | {job.order_id} | {job.status.value} | {job.created_at}"
            )

    elif args.command == "checkpoint":
        queue.checkpoint()
        print("WAL checkpoint complete")


if __name__ == "__main__":
    main()
