#!/usr/bin/env python3
"""
Tests for Resilient Cutter Queue System

Tests cover:
- Job creation and queuing
- Priority ordering
- Job completion and failure handling
- Recovery after simulated crash
- Reprint functionality
- Archive operations

Author: Claude
Date: 2026-02-01
"""

import os
import sys
import json
import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "core"))

from core.resilient_cutter_queue import (
    ResilientCutterQueue,
    JobPriority,
    JobStatus,
    CutterJob,
    WriteAheadLog,
    JobArchive,
    WALAction,
)


class TestWriteAheadLog:
    """Tests for WriteAheadLog component."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests."""
        d = tempfile.mkdtemp()
        yield Path(d)
        shutil.rmtree(d, ignore_errors=True)

    def test_append_and_replay(self, temp_dir):
        """Test appending entries and replaying them."""
        wal = WriteAheadLog(temp_dir / "test.wal")

        # Append some entries
        seq1 = wal.append(WALAction.JOB_CREATED, "job-1", {"order_id": "ord-1"})
        seq2 = wal.append(WALAction.JOB_QUEUED, "job-1", {"queued_at": "2026-01-01"})
        seq3 = wal.append(
            WALAction.JOB_COMPLETED, "job-1", {"completed_at": "2026-01-01"}
        )

        # Sequences should be increasing
        assert seq1 == 1
        assert seq2 == 2
        assert seq3 == 3

        # Replay should return all entries in order
        entries = wal.replay()
        assert len(entries) == 3
        assert entries[0]["action"] == WALAction.JOB_CREATED.value
        assert entries[1]["action"] == WALAction.JOB_QUEUED.value
        assert entries[2]["action"] == WALAction.JOB_COMPLETED.value

    def test_checkpoint(self, temp_dir):
        """Test WAL checkpoint removes old entries."""
        wal = WriteAheadLog(temp_dir / "test.wal")

        # Add 5 entries
        for i in range(5):
            wal.append(WALAction.JOB_CREATED, f"job-{i}", {"i": i})

        # Checkpoint after seq 3
        wal.checkpoint(3)

        # Only entries 4 and 5 should remain
        entries = wal.replay()
        assert len(entries) == 2
        assert entries[0]["job_id"] == "job-3"
        assert entries[1]["job_id"] == "job-4"


class TestJobArchive:
    """Tests for JobArchive component."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests."""
        d = tempfile.mkdtemp()
        yield Path(d)
        shutil.rmtree(d, ignore_errors=True)

    @pytest.fixture
    def sample_plt(self, temp_dir):
        """Create a sample PLT file."""
        plt_path = temp_dir / "sample.plt"
        plt_path.write_text("IN;SP1;PU0,0;PD100,100;SP0;")
        return plt_path

    def test_archive_and_retrieve_job(self, temp_dir, sample_plt):
        """Test archiving and retrieving a job."""
        archive = JobArchive(temp_dir / "archive")

        job = CutterJob(
            job_id="JOB-001",
            order_id="ORD-001",
            plt_file=str(sample_plt),
            priority=JobPriority.NORMAL,
            piece_count=5,
            fabric_length_cm=150.0,
        )

        # Archive the job
        result = archive.archive_job(job)
        assert result is True

        # Retrieve the job
        retrieved = archive.get_job("JOB-001")
        assert retrieved is not None
        assert retrieved.job_id == "JOB-001"
        assert retrieved.order_id == "ORD-001"
        assert retrieved.priority == JobPriority.NORMAL
        assert retrieved.piece_count == 5

    def test_search_jobs(self, temp_dir, sample_plt):
        """Test searching archived jobs."""
        archive = JobArchive(temp_dir / "archive")

        # Archive multiple jobs
        for i in range(3):
            job = CutterJob(
                job_id=f"JOB-{i:03d}",
                order_id=f"ORD-{i % 2:03d}",  # 2 different orders
                plt_file=str(sample_plt),
                status=JobStatus.COMPLETE if i < 2 else JobStatus.ERROR,
            )
            archive.archive_job(job)

        # Search by order
        jobs = archive.search_jobs(order_id="ORD-000")
        assert len(jobs) == 2

        # Search by status
        jobs = archive.search_jobs(status=JobStatus.ERROR)
        assert len(jobs) == 1


class TestResilientCutterQueue:
    """Tests for main ResilientCutterQueue."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests."""
        d = tempfile.mkdtemp()
        yield Path(d)
        shutil.rmtree(d, ignore_errors=True)

    @pytest.fixture
    def sample_plt(self, temp_dir):
        """Create a sample PLT file."""
        plt_path = temp_dir / "sample.plt"
        plt_path.write_text("IN;SP1;PU0,0;PD100,100;SP0;")
        return plt_path

    def test_add_and_get_job(self, temp_dir, sample_plt):
        """Test adding a job and getting it from queue."""
        queue = ResilientCutterQueue(temp_dir / "queue")

        # Add a job
        job = queue.add_job(
            order_id="ORD-001",
            plt_file=sample_plt,
            priority=JobPriority.NORMAL,
            fabric_length_cm=100.0,
        )

        assert job is not None
        assert job.order_id == "ORD-001"
        assert job.status == JobStatus.QUEUED

        # Get next job
        next_job = queue.get_next_job()
        assert next_job is not None
        assert next_job.job_id == job.job_id
        assert next_job.status == JobStatus.CUTTING

    def test_priority_ordering(self, temp_dir, sample_plt):
        """Test that jobs are returned in priority order."""
        queue = ResilientCutterQueue(temp_dir / "queue")

        # Add jobs in reverse priority order
        job_low = queue.add_job("ORD-LOW", sample_plt, priority=JobPriority.LOW)
        job_normal = queue.add_job(
            "ORD-NORMAL", sample_plt, priority=JobPriority.NORMAL
        )
        job_rush = queue.add_job("ORD-RUSH", sample_plt, priority=JobPriority.RUSH)

        # Should get rush first, then normal, then low
        assert queue.get_next_job().order_id == "ORD-RUSH"
        assert queue.get_next_job().order_id == "ORD-NORMAL"
        assert queue.get_next_job().order_id == "ORD-LOW"

    def test_complete_and_fail(self, temp_dir, sample_plt):
        """Test marking jobs as complete or failed."""
        queue = ResilientCutterQueue(temp_dir / "queue")

        # Add two jobs
        job1 = queue.add_job("ORD-001", sample_plt)
        job2 = queue.add_job("ORD-002", sample_plt)

        # Get and complete first job
        next_job = queue.get_next_job()
        queue.mark_complete(next_job.job_id)

        # Verify it's archived as complete
        archived = queue.archive.get_job(next_job.job_id)
        assert archived.status == JobStatus.COMPLETE

        # Get and fail second job
        next_job = queue.get_next_job()
        queue.mark_failed(next_job.job_id, "Test error")

        # Verify it's marked as error
        archived = queue.archive.get_job(next_job.job_id)
        assert archived.status == JobStatus.ERROR
        assert archived.error_message == "Test error"

    def test_recovery_after_crash(self, temp_dir, sample_plt):
        """Test that queue recovers state after crash."""
        # Create queue and add jobs
        queue1 = ResilientCutterQueue(temp_dir / "queue")
        job1 = queue1.add_job("ORD-001", sample_plt, priority=JobPriority.RUSH)
        job2 = queue1.add_job("ORD-002", sample_plt, priority=JobPriority.NORMAL)

        # Get one job (simulating it was being cut when crash happened)
        cutting_job = queue1.get_next_job()
        assert cutting_job.status == JobStatus.CUTTING

        # Simulate crash by deleting queue object and creating new one
        del queue1

        # Create new queue - should recover state
        queue2 = ResilientCutterQueue(temp_dir / "queue")

        # The cutting job should be re-queued (with incremented retry count)
        status = queue2.get_status()
        assert status["queue_depth"] == 2  # Both jobs should be queued

    def test_reprint_job(self, temp_dir, sample_plt):
        """Test reprinting a completed job."""
        queue = ResilientCutterQueue(temp_dir / "queue")

        # Add and complete a job
        job = queue.add_job("ORD-001", sample_plt)
        next_job = queue.get_next_job()
        queue.mark_complete(next_job.job_id)

        # Reprint the job
        reprint = queue.reprint_job(
            next_job.job_id,
            reason="Fabric defect",
            requested_by="operator",
        )

        assert reprint is not None
        assert reprint.is_reprint is True
        assert reprint.original_job_id == next_job.job_id
        assert reprint.order_id == "ORD-001"

        # Reprint should be in queue
        status = queue.get_status()
        assert status["queue_depth"] == 1

    def test_get_status(self, temp_dir, sample_plt):
        """Test getting queue status."""
        queue = ResilientCutterQueue(temp_dir / "queue")

        # Add some jobs
        queue.add_job("ORD-001", sample_plt, fabric_length_cm=100)
        queue.add_job("ORD-002", sample_plt, fabric_length_cm=150)

        status = queue.get_status()

        assert status["queue_depth"] == 2
        assert status["active_jobs"] == 2
        assert status["total_fabric_cm"] == 250.0
        assert status["estimated_time_min"] > 0


class TestCutterJob:
    """Tests for CutterJob dataclass."""

    def test_to_dict_and_from_dict(self):
        """Test serialization round-trip."""
        job = CutterJob(
            job_id="JOB-001",
            order_id="ORD-001",
            plt_file="/path/to/file.plt",
            priority=JobPriority.RUSH,
            status=JobStatus.QUEUED,
            piece_count=5,
        )

        # Convert to dict
        data = job.to_dict()
        assert data["priority"] == JobPriority.RUSH.value
        assert data["status"] == JobStatus.QUEUED.value

        # Convert back
        restored = CutterJob.from_dict(data)
        assert restored.job_id == "JOB-001"
        assert restored.priority == JobPriority.RUSH
        assert restored.status == JobStatus.QUEUED


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
